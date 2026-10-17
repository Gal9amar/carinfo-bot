"""Annual-test (טסט) reminders — one row per (user, plate).

A reminder stores the test expiry date seen at subscription time. The daily job
re-checks the registry right before notifying, so a renewed test silently resets
the reminder instead of sending a stale warning.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Awaitable, Callable, Optional

from src.db import execute

logger = logging.getLogger(__name__)

MILESTONES = (30, 7, 1, 0)   # days before expiry at which we notify
STALE_AFTER_DAYS = 365       # stop tracking a plate whose test lapsed a year ago
_COLS = "id, user_id, plate, label, tokef_dt, notified, last_refresh, active, source"


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
        "notified=NULL, active=1",
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


async def sync_garage() -> int:
    """Create reminders for cars currently in users' garages (never re-arms stopped ones)."""
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
        [tokef, date.today().isoformat(), rid],
    )


async def run_due(
    send: Callable[[dict, int, int], Awaitable[bool]],
    fetch_tokef: Callable[[str], Awaitable[Optional[str]]],
) -> int:
    """Notify due reminders. `send(reminder, days_left, milestone)` -> delivered?
    `fetch_tokef(plate)` -> current registry expiry or None. Returns messages sent."""
    today = date.today()
    r = await execute(f"SELECT {_COLS} FROM test_reminders WHERE active=1")
    sent = 0
    for rem in (_row(x) for x in r.rows):
        tokef = parse_date(rem["tokef_dt"])
        if not tokef:
            continue
        days = (tokef - today).days
        if days < -STALE_AFTER_DAYS:
            await execute("UPDATE test_reminders SET active=0 WHERE id=?", [rem["id"]])
            continue
        milestone = pick_milestone(days, rem["notified"]) if days <= 30 else None
        overdue_recheck = (
            days < 0 and rem["notified"] == 0
            and (parse_date(rem["last_refresh"]) is None or (today - parse_date(rem["last_refresh"])).days >= 7)
        )
        if milestone is None and not overdue_recheck:
            continue
        # Re-check the registry: the owner may already have renewed the test.
        fresh = None
        try:
            fresh = await fetch_tokef(rem["plate"])
        except Exception as exc:
            logger.warning("reminder refresh failed plate=%s: %s", rem["plate"], type(exc).__name__)
        fresh_d = parse_date(fresh)
        if fresh_d and fresh_d != tokef:
            await _update_tokef(rem["id"], fresh_d.isoformat())
            tokef, rem["notified"] = fresh_d, None
            days = (tokef - today).days
            milestone = pick_milestone(days, None) if days <= 30 else None
        elif overdue_recheck:
            await execute("UPDATE test_reminders SET last_refresh=? WHERE id=?", [today.isoformat(), rem["id"]])
        if milestone is None:
            continue
        try:
            ok = await send({**rem, "tokef_dt": tokef.isoformat()}, days, milestone)
        except Exception as exc:
            logger.warning("reminder send failed user=%s: %s", rem["user_id"], type(exc).__name__)
            ok = False
        if ok:
            await execute("UPDATE test_reminders SET notified=? WHERE id=?", [milestone, rem["id"]])
            sent += 1
    return sent
