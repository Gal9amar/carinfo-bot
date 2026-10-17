"""Annual-test (טסט) reminders — one row per (user, plate).

A reminder stores the test expiry date seen at subscription time. The daily job
re-checks the registry right before notifying, so a renewed test silently resets
the reminder instead of sending a stale warning.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable, Optional

from src.db import execute

logger = logging.getLogger(__name__)

MILESTONES = (30, 7, 1, 0)   # days before expiry at which we notify
STALE_AFTER_DAYS = 365       # stop tracking a plate whose test lapsed a year ago
_COLS = "id, user_id, plate, label, tokef_dt, notified, last_refresh, active, source"


def today() -> date:
    """Today in Israel (reminders are written for Israeli users)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=3)).date()


def parse_date(raw) -> Optional[date]:
    try:
        return date.fromisoformat(str(raw)[:10])
    except Exception:
        return None


def pick_milestone(days_left: int, notified: Optional[int]) -> Optional[int]:
    """Next milestone to notify for, or None when nothing new is due."""
    due = [m for m in MILESTONES if days_left <= m]
    if not due:
        return None
    smallest = min(due)
    if notified is None or smallest < notified:
        return smallest
    return None


def _row(r) -> dict:
    return {
        "id": r[0], "user_id": r[1], "plate": r[2], "label": r[3], "tokef_dt": r[4],
        "notified": r[5], "last_refresh": r[6], "active": bool(r[7]), "source": r[8],
    }


def label_for(record: dict) -> str:
    make = record.get("tozeret_nm") or ""
    model = record.get("kinuy_mishari") or record.get("degem_nm") or ""
    year = record.get("shnat_yitzur") or ""
    return " ".join(str(p) for p in (make, model, year) if p).strip()


async def add_reminder(user_id: int, plate: str, tokef_dt: str, label: str = "", source: str = "manual") -> dict:
    """Create or re-arm a reminder. Returns the stored row."""
    tokef = str(tokef_dt)[:10]
    await execute(
        "INSERT INTO test_reminders (user_id, plate, label, tokef_dt, source) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, plate) DO UPDATE SET tokef_dt=excluded.tokef_dt, label=excluded.label, "
        "source=excluded.source, active=1, "
        "notified=CASE WHEN test_reminders.tokef_dt<>excluded.tokef_dt THEN NULL ELSE test_reminders.notified END",
        [user_id, plate, label, tokef, source],
    )
    r = await execute(f"SELECT {_COLS} FROM test_reminders WHERE user_id=? AND plate=?", [user_id, plate])
    return _row(r.rows[0])


async def get_reminder(user_id: int, plate: str) -> Optional[dict]:
    r = await execute(f"SELECT {_COLS} FROM test_reminders WHERE user_id=? AND plate=?", [user_id, plate])
    return _row(r.rows[0]) if r.rows else None


async def stop_reminder(reminder_id: int, user_id: int) -> bool:
    r = await execute("SELECT 1 FROM test_reminders WHERE id=? AND user_id=?", [reminder_id, user_id])
    if not r.rows:
        return False
    await execute("UPDATE test_reminders SET active=0 WHERE id=? AND user_id=?", [reminder_id, user_id])
    return True


async def deactivate_orphans() -> None:
    """Stop garage-sourced reminders whose car was sold or removed from the garage."""
    await execute(
        "UPDATE test_reminders SET active=0 WHERE active=1 AND source='garage' AND NOT EXISTS ("
        "SELECT 1 FROM owned_vehicles o WHERE o.user_id=test_reminders.user_id "
        "AND o.plate=test_reminders.plate AND o.status='owned')"
    )


async def sync_garage() -> int:
    """Create reminders for cars currently in users' garages (never re-arms stopped ones)."""
    await deactivate_orphans()
    r = await execute(
        "SELECT user_id, plate, vehicle_data FROM owned_vehicles WHERE status='owned'"
    )
    added = 0
    for user_id, plate, raw in r.rows:
        if await get_reminder(user_id, plate):
            continue
        try:
            data = json.loads(raw or "{}")
        except Exception:
            data = {}
        if not parse_date(data.get("tokef_dt")):
            continue
        await add_reminder(user_id, plate, data["tokef_dt"], label_for(data), source="garage")
        added += 1
    return added


async def _update_tokef(rid: int, tokef: str) -> None:
    await execute(
        "UPDATE test_reminders SET tokef_dt=?, notified=NULL, last_refresh=? WHERE id=?",
        [tokef, today().isoformat(), rid],
    )


async def count_for_user(user_id: int) -> int:
    r = await execute("SELECT COUNT(*) FROM test_reminders WHERE user_id=? AND active=1", [user_id])
    return int(r.rows[0][0])


async def _process(rem: dict, send, fetch_tokef, today_d: date) -> bool:
    """Handle one reminder. Returns True if a message was delivered."""
    tokef = parse_date(rem["tokef_dt"])
    if not tokef:
        return False
    days = (tokef - today_d).days
    if days < -STALE_AFTER_DAYS:
        await execute("UPDATE test_reminders SET active=0 WHERE id=?", [rem["id"]])
        return False
    milestone = pick_milestone(days, rem["notified"]) if days <= 30 else None
    last_refresh = parse_date(rem["last_refresh"])
    overdue_recheck = (
        days < 0 and rem["notified"] == 0
        and (last_refresh is None or (today_d - last_refresh).days >= 7)
    )
    if milestone is None and not overdue_recheck:
        return False
    # Never notify on unverified data: the owner may have renewed the test since we stored the date.
    try:
        fresh_d = parse_date(await fetch_tokef(rem["plate"]))
    except Exception as exc:
        logger.warning("reminder refresh failed id=%s: %s", rem["id"], type(exc).__name__)
        fresh_d = None
    if fresh_d is None:
        return False   # registry unavailable or no date: try again tomorrow
    if fresh_d != tokef:
        await _update_tokef(rem["id"], fresh_d.isoformat())
        tokef, rem["notified"] = fresh_d, None
        days = (tokef - today_d).days
        milestone = pick_milestone(days, None) if days <= 30 else None
    elif overdue_recheck:
        await execute("UPDATE test_reminders SET last_refresh=? WHERE id=?", [today_d.isoformat(), rem["id"]])
    if milestone is None:
        return False
    # Claim the milestone before sending so a crash or a second instance cannot double-send.
    await execute("UPDATE test_reminders SET notified=? WHERE id=?", [milestone, rem["id"]])
    try:
        ok = await send({**rem, "tokef_dt": tokef.isoformat()}, days, milestone)
    except Exception as exc:
        logger.warning("reminder send failed id=%s: %s", rem["id"], type(exc).__name__)
        ok = False
    if ok:
        return True
    if ok is None:
        await execute("UPDATE test_reminders SET active=0 WHERE id=?", [rem["id"]])
    else:   # temporary failure: release the claim so tomorrow's run retries
        await execute("UPDATE test_reminders SET notified=? WHERE id=?", [rem["notified"], rem["id"]])
    return False


async def run_due(
    send: Callable[[dict, int, int], Awaitable[Optional[bool]]],
    fetch_tokef: Callable[[str], Awaitable[Optional[str]]],
) -> int:
    """Notify due reminders. `send(reminder, days_left, milestone)` -> True delivered,
    False temporary failure (retry tomorrow), None permanent failure (user blocked the bot -> stop).
    `fetch_tokef(plate)` -> current registry expiry or None. Returns messages sent."""
    today_d = today()
    r = await execute(f"SELECT {_COLS} FROM test_reminders WHERE active=1")
    sent = 0
    for rem in (_row(x) for x in r.rows):
        try:
            if await _process(rem, send, fetch_tokef, today_d):
                sent += 1
        except Exception as exc:   # one bad row must not abort the whole job
            logger.warning("reminder row failed id=%s: %s", rem["id"], type(exc).__name__)
    return sent
