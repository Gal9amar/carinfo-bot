"""Yad2 watch/alert management — per-user watches stored in DB."""
from __future__ import annotations
import json
import logging

logger = logging.getLogger(__name__)
MAX_WATCHES_PER_USER = 5  # fallback if DB unavailable


async def _get_max_for_user(user_id: int) -> int:
    """Return the effective watch limit for this user (per-user override > global setting > fallback)."""
    from src.db import execute, get_bot_setting
    # Per-user override
    r = await execute("SELECT watch_quota FROM users WHERE user_id=?", [user_id])
    if r.rows and r.rows[0][0] is not None:
        return int(r.rows[0][0])
    # Global setting
    val = await get_bot_setting("yad2_watch_max")
    if val and val.isdigit():
        return int(val)
    return MAX_WATCHES_PER_USER


async def create_watch(user_id: int, make: str, model: str, year: int | None) -> dict:
    from src.db import execute
    max_watches = await _get_max_for_user(user_id)
    existing = await get_user_watches(user_id)
    if len(existing) >= max_watches:
        raise ValueError(f"מקסימום {max_watches} התראות")
    await execute(
        "INSERT INTO yad2_watches (user_id, make, model, year) VALUES (?, ?, ?, ?)",
        [user_id, make, model, year]
    )
    r = await execute(
        "SELECT id, user_id, make, model, year, active, created_at "
        "FROM yad2_watches WHERE user_id=? ORDER BY id DESC LIMIT 1",
        [user_id]
    )
    return _row(r.rows[0])


async def delete_watch(watch_id: int, user_id: int) -> None:
    from src.db import execute
    await execute(
        "DELETE FROM yad2_watches WHERE id=? AND user_id=?",
        [watch_id, user_id]
    )


async def get_user_watches(user_id: int) -> list[dict]:
    from src.db import execute
    r = await execute(
        "SELECT id, user_id, make, model, year, active, created_at "
        "FROM yad2_watches WHERE user_id=? ORDER BY id",
        [user_id]
    )
    return [_row(row) for row in r.rows]


async def get_all_active_watches() -> list[dict]:
    from src.db import execute
    r = await execute(
        "SELECT id, user_id, make, model, year, seen_ids, active "
        "FROM yad2_watches WHERE active=1"
    )
    result = []
    for row in r.rows:
        d = {
            "id": row[0], "user_id": row[1], "make": row[2],
            "model": row[3], "year": row[4], "active": row[6],
        }
        try:
            d["seen_ids"] = json.loads(row[5] or "[]")
        except Exception:
            d["seen_ids"] = []
        result.append(d)
    return result


async def update_seen_ids(watch_id: int, seen_ids: list[str]) -> None:
    from src.db import execute
    await execute(
        "UPDATE yad2_watches SET seen_ids=? WHERE id=?",
        [json.dumps(seen_ids), watch_id]
    )


async def toggle_watch(watch_id: int, user_id: int, active: bool) -> None:
    from src.db import execute
    await execute(
        "UPDATE yad2_watches SET active=? WHERE id=? AND user_id=?",
        [1 if active else 0, watch_id, user_id]
    )


def _row(row) -> dict:
    return {
        "id": row[0], "user_id": row[1], "make": row[2],
        "model": row[3], "year": row[4], "active": bool(row[5]),
        "created_at": row[6],
    }
