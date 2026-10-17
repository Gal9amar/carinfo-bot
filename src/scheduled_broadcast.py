"""Broadcasts scheduled for a later date/time.

Rows live in ``scheduled_broadcasts`` (times stored as UTC ``YYYY-MM-DD HH:MM:SS``). A job in
bot.py calls ``sweep`` then ``claim_due`` every 30 s and sends what is due through the same
broadcast functions used for immediate sends. Claiming is a conditional UPDATE that stamps a unique token (read back to see who won), so a
broadcast can never be sent twice, even if two instances overlap during a deploy.

Statuses: pending → sending → sent | cancelled | missed (too late to be useful) |
interrupted (the process died while sending; never auto-resent) | failed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.db import execute

MAX_LATE = timedelta(hours=3)          # if the bot was down this long past the schedule, don't send stale news
SENDING_TIMEOUT = timedelta(hours=2)    # a very large broadcast sends sequentially and can take a while
MAX_IMAGE_CHARS = 6_000_000            # base64 string stored in the row
MAX_AHEAD = timedelta(days=365)
MIN_AHEAD = timedelta(seconds=15)

_FMT = "%Y-%m-%d %H:%M:%S"
_COLS = "id, message, image_b64, send_at, status, sent, failed, created_at, sent_at"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_when(raw: str) -> datetime:
    """ISO timestamp -> aware UTC datetime. Naive values are read as Israel time. Raises ValueError."""
    text = (raw or "").strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Jerusalem"))
        except Exception:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=3)))
    return dt.astimezone(timezone.utc)


def validate_when(when: datetime) -> Optional[str]:
    now = _now()
    if when < now + MIN_AHEAD:
        return "זמן השידור חייב להיות בעתיד"
    if when > now + MAX_AHEAD:
        return "אפשר לתזמן עד שנה קדימה"
    return None


def _row(r) -> dict:
    return {
        "id": r[0], "message": r[1], "image_b64": r[2] or "", "send_at": r[3], "status": r[4],
        "sent": r[5] or 0, "failed": r[6] or 0, "created_at": r[7], "sent_at": r[8],
    }


def public(row: dict) -> dict:
    """API shape: no image bytes, times as ISO-8601 UTC."""
    def iso(v):
        return (str(v).replace(" ", "T") + "Z") if v else None
    return {
        "id": row["id"], "message": row["message"], "has_image": bool(row["image_b64"]),
        "send_at": iso(row["send_at"]), "status": row["status"], "sent": row["sent"],
        "failed": row["failed"], "sent_at": iso(row["sent_at"]),
    }


def _token() -> str:
    return uuid.uuid4().hex


async def _by_token(token: str) -> Optional[dict]:
    r = await execute(f"SELECT {_COLS} FROM scheduled_broadcasts WHERE claim_token=?", [token])
    return _row(r.rows[0]) if r.rows else None


async def _transition(sid: int, old: str, new: str, claimed_at: Optional[str] = None) -> Optional[dict]:
    """Move a row old -> new only if it is still in `old`. The unique token written by this UPDATE
    tells us whether *we* won (the DB layer does not expose affected-row counts)."""
    token = _token()
    await execute(
        "UPDATE scheduled_broadcasts SET status=?, claim_token=?, claimed_at=COALESCE(?, claimed_at) WHERE id=? AND status=?",
        [new, token, claimed_at, sid, old],
    )
    return await _by_token(token)


async def create(message: str, image_b64: str, when_utc: datetime, created_by: int = 0) -> dict:
    token = _token()
    await execute(
        "INSERT INTO scheduled_broadcasts (message, image_b64, send_at, created_by, claim_token) VALUES (?, ?, ?, ?, ?)",
        [message, image_b64, when_utc.strftime(_FMT), created_by, token],
    )
    return await _by_token(token)


async def is_duplicate(message: str, when_utc: datetime) -> bool:
    """Same text already pending for the same minute (double tap / retry)."""
    minute = when_utc.strftime("%Y-%m-%d %H:%M")
    r = await execute(
        "SELECT 1 FROM scheduled_broadcasts WHERE status='pending' AND message=? AND substr(send_at,1,16)=? LIMIT 1",
        [message, minute],
    )
    return bool(r.rows)


async def list_recent(finished: int = 10) -> list[dict]:
    pending = await execute(
        f"SELECT {_COLS} FROM scheduled_broadcasts WHERE status IN ('pending','sending') ORDER BY send_at ASC LIMIT 100"
    )
    done = await execute(
        f"SELECT {_COLS} FROM scheduled_broadcasts WHERE status NOT IN ('pending','sending') ORDER BY id DESC LIMIT ?",
        [finished],
    )
    return [_row(r) for r in pending.rows] + [_row(r) for r in done.rows]


async def cancel(sid: int) -> bool:
    return await _transition(sid, "pending", "cancelled") is not None


async def claim_due() -> list[dict]:
    """Atomically claim every pending broadcast whose time has come."""
    now = _now().strftime(_FMT)
    due = await execute(
        "SELECT id FROM scheduled_broadcasts WHERE status='pending' AND send_at <= ? ORDER BY send_at ASC", [now]
    )
    claimed = []
    for (sid,) in due.rows:
        row = await _transition(sid, "pending", "sending", claimed_at=now)
        if row:                          # None = someone else (or a cancel) got there first
            claimed.append(row)
    return claimed


async def finish(sid: int, status: str, sent: int = 0, failed: int = 0) -> None:
    await execute(
        "UPDATE scheduled_broadcasts SET status=?, sent=?, failed=?, sent_at=? WHERE id=?",
        [status, sent, failed, _now().strftime(_FMT), sid],
    )


async def sweep() -> list[dict]:
    """Mark broadcasts that can no longer be sent. Returns them so the admin can be told."""
    now = _now()
    out: list[dict] = []
    late = await execute(
        "SELECT id FROM scheduled_broadcasts WHERE status='pending' AND send_at <= ?",
        [(now - MAX_LATE).strftime(_FMT)],
    )
    for (sid,) in late.rows:
        row = await _transition(sid, "pending", "missed")
        if row:
            out.append(row)
    stuck = await execute(
        "SELECT id FROM scheduled_broadcasts WHERE status='sending' AND claimed_at <= ?",
        [(now - SENDING_TIMEOUT).strftime(_FMT)],
    )
    for (sid,) in stuck.rows:
        row = await _transition(sid, "sending", "interrupted")
        if row:
            out.append(row)
    return out
