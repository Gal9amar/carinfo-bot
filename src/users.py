"""
User management – quota, access codes, grants.
Storage: Turso (libsql) via src/db.py
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.db import execute

FREE_SEARCHES = 20


# ── Helpers ────────────────────────────────────────────────────────────────

def _row(result) -> Optional[dict]:
    if not result.rows:
        return None
    cols = [c.name for c in result.columns]
    return dict(zip(cols, result.rows[0]))


def _rows(result) -> list[dict]:
    cols = [c.name for c in result.columns]
    return [dict(zip(cols, row)) for row in result.rows]


async def _ensure_user(user_id: int, username: str = "", full_name: str = "") -> None:
    await execute(
        """
        INSERT INTO users (user_id, username, full_name, searches_quota)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username  = CASE WHEN excluded.username  != '' THEN excluded.username  ELSE users.username  END,
            full_name = CASE WHEN excluded.full_name != '' THEN excluded.full_name ELSE users.full_name END,
            last_seen = datetime('now')
        """,
        [user_id, username, full_name, FREE_SEARCHES],
    )


# ── Public API ─────────────────────────────────────────────────────────────

async def is_allowed(user_id: int, username: str = "", full_name: str = "") -> tuple[bool, int]:
    """Returns (allowed, searches_left). -1 = unlimited."""
    await _ensure_user(user_id, username, full_name)
    r = await execute(
        "SELECT searches_done, searches_quota, blocked, quota_expires FROM users WHERE user_id = ?",
        [user_id],
    )
    u = _row(r)
    if u is None:
        return False, 0
    if u.get("blocked"):
        return False, 0

    quota         = u["searches_quota"]
    done          = u["searches_done"]
    quota_expires = u.get("quota_expires")

    # If unlimited but time-limited – check expiry
    if quota == -1 and quota_expires:
        try:
            if datetime.now() > datetime.fromisoformat(quota_expires):
                # Subscription expired – revert to 0
                await execute(
                    "UPDATE users SET searches_quota = 0, quota_expires = NULL WHERE user_id = ?",
                    [user_id],
                )
                return False, 0
        except Exception:
            pass

    if quota == -1:
        return True, -1

    left = max(0, quota - done)
    return left > 0, left


async def increment_search(user_id: int, plate: str = "") -> None:
    await execute(
        "UPDATE users SET searches_done = searches_done + 1, last_seen = datetime('now') WHERE user_id = ?",
        [user_id],
    )
    if plate:
        await execute(
            "INSERT INTO search_history (user_id, plate) VALUES (?, ?)",
            [user_id, plate],
        )


async def get_last_plate(user_id: int) -> str:
    r = await execute(
        "SELECT last_plate FROM users WHERE user_id = ?",
        [user_id],
    )
    u = _row(r)
    return u["last_plate"] if u else ""


async def set_last_plate(user_id: int, plate: str) -> None:
    await execute(
        "UPDATE users SET last_plate = ? WHERE user_id = ?",
        [plate, user_id],
    )


async def apply_code(user_id: int, code: str, username: str = "") -> tuple[bool, str]:
    await _ensure_user(user_id, username)

    r = await execute("SELECT * FROM codes WHERE code = ?", [code])
    code_data = _row(r)
    if code_data is None:
        return False, "קוד לא תקין"

    uc = await execute(
        "SELECT 1 FROM user_codes WHERE user_id = ? AND code = ?",
        [user_id, code],
    )
    if uc.rows:
        return False, "קוד זה כבר נוצל על ידך"

    if code_data["single_use"] and code_data["used_by"] is not None:
        return False, "קוד זה כבר נוצל"

    if code_data["expires"]:
        try:
            if datetime.now() > datetime.fromisoformat(code_data["expires"]):
                return False, "קוד פג תוקף"
        except Exception:
            pass

    unlimited = bool(code_data["unlimited"])
    add       = code_data["searches"]
    now_iso   = datetime.now().isoformat()
    # monthly = unlimited code that carries a duration (searches field holds days)
    is_monthly = unlimited and add and add > 0

    if unlimited:
        if is_monthly:
            # add = number of days the subscription lasts
            expires_dt  = datetime.now() + timedelta(days=int(add))
            expires_iso = expires_dt.isoformat()
            await execute(
                "UPDATE users SET searches_quota = -1, quota_expires = ? WHERE user_id = ?",
                [expires_iso, user_id],
            )
            exp_str = expires_dt.strftime("%d/%m/%Y")
            result_msg = f"✅ גישה חופשית לחודש הופעלה\\!\nתוקף עד: *{exp_str}*"
        else:
            await execute(
                "UPDATE users SET searches_quota = -1, quota_expires = NULL WHERE user_id = ?",
                [user_id],
            )
            result_msg = "✅ גישה בלתי מוגבלת הופעלה"
    else:
        r2 = await execute(
            "SELECT searches_quota, searches_done FROM users WHERE user_id = ?",
            [user_id],
        )
        u = _row(r2)
        quota = u["searches_quota"]
        done  = u["searches_done"]
        if quota == -1:
            result_msg = "✅ כבר יש לך גישה בלתי מוגבלת"
        else:
            new_quota = quota + add
            await execute(
                "UPDATE users SET searches_quota = ? WHERE user_id = ?",
                [new_quota, user_id],
            )
            result_msg = f"✅ נוספו {add} בדיקות \\(סה\"כ {max(0, new_quota - done)} נותרו\\)"

    await execute(
        "UPDATE codes SET used_by = ?, used_at = ? WHERE code = ?",
        [user_id, now_iso, code],
    )
    await execute(
        "INSERT OR IGNORE INTO user_codes (user_id, code) VALUES (?, ?)",
        [user_id, code],
    )
    return True, result_msg


async def admin_grant(admin_id: int, target_id: int, searches: int, note: str = "") -> str:
    await _ensure_user(target_id)
    r = await execute(
        "SELECT searches_quota, searches_done FROM users WHERE user_id = ?",
        [target_id],
    )
    u = _row(r)
    quota = u["searches_quota"] if u else FREE_SEARCHES
    done  = u["searches_done"]  if u else 0

    if searches == -1:
        from datetime import timedelta
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        await execute(
            "UPDATE users SET searches_quota = -1, searches_done = 0, quota_expires = ? WHERE user_id = ?",
            [expires, target_id],
        )
        msg = f"מנוי חודשי עד {expires[:10]}"
    elif quota == -1:
        msg = "כבר יש לו גישה בלתי מוגבלת"
    else:
        new_q = quota + searches
        await execute(
            "UPDATE users SET searches_quota = ? WHERE user_id = ?",
            [new_q, target_id],
        )
        msg = f"נוספו {searches} בדיקות \\(סה\"כ {max(0, new_q - done)} נותרו\\)"

    await execute(
        "INSERT INTO grants (user_id, granted_by, searches, note) VALUES (?, ?, ?, ?)",
        [target_id, admin_id, searches, note],
    )
    return msg


async def generate_code(
    searches: int = 10,
    single_use: bool = True,
    unlimited: bool = False,
    monthly: bool = False,
    expires_days: int = 90,
) -> str:
    code = secrets.token_hex(4).upper()
    expires = (datetime.now() + timedelta(days=expires_days)).isoformat()
    if monthly:
        # unlimited=True, searches holds subscription duration in days (30)
        await execute(
            """
            INSERT INTO codes (code, searches, unlimited, single_use, expires)
            VALUES (?, ?, 1, ?, ?)
            """,
            [code, 30, int(single_use), expires],
        )
    else:
        await execute(
            """
            INSERT INTO codes (code, searches, unlimited, single_use, expires)
            VALUES (?, ?, ?, ?, ?)
            """,
            [code, searches, int(unlimited), int(single_use), expires],
        )
    return code


async def get_all_users() -> list[dict]:
    r = await execute(
        "SELECT user_id, username, full_name, searches_done, searches_quota, first_seen, last_seen, blocked FROM users ORDER BY searches_done DESC"
    )
    users = []
    for u in _rows(r):
        quota = u["searches_quota"]
        done  = u["searches_done"]
        u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
        users.append(u)
    return users


async def get_user_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@").lower()
    r = await execute(
        "SELECT user_id, username, full_name, searches_done, searches_quota, blocked FROM users WHERE LOWER(username) = ?",
        [username],
    )
    u = _row(r)
    if u is None:
        return None
    quota = u["searches_quota"]
    done  = u["searches_done"]
    u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
    return u


async def get_user_by_id(user_id: int) -> Optional[dict]:
    r = await execute(
        "SELECT user_id, username, full_name, searches_done, searches_quota, blocked FROM users WHERE user_id = ?",
        [user_id],
    )
    u = _row(r)
    if u is None:
        return None
    quota = u["searches_quota"]
    done  = u["searches_done"]
    u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
    return u



async def get_quota_expires(user_id: int) -> str | None:
    """Returns quota_expires ISO string or None."""
    r = await execute(
        "SELECT quota_expires FROM users WHERE user_id = ?",
        [user_id],
    )
    u = _row(r)
    return u["quota_expires"] if u else None

async def block_user(user_id: int) -> None:
    await _ensure_user(user_id)
    await execute("UPDATE users SET blocked = 1 WHERE user_id = ?", [user_id])


async def unblock_user(user_id: int) -> None:
    await execute("UPDATE users SET blocked = 0 WHERE user_id = ?", [user_id])


async def is_blocked(user_id: int) -> bool:
    r = await execute("SELECT blocked FROM users WHERE user_id = ?", [user_id])
    u = _row(r)
    return bool(u["blocked"]) if u else False


async def admin_stats() -> dict:
    total_r    = await execute("SELECT COUNT(*) as c FROM users")
    active_r   = await execute(
        "SELECT COUNT(*) as c FROM users WHERE searches_quota = -1 OR searches_quota > searches_done"
    )
    searches_r = await execute("SELECT COALESCE(SUM(searches_done), 0) as c FROM users")
    codes_r    = await execute("SELECT COUNT(*) as c FROM codes")
    used_r     = await execute("SELECT COUNT(*) as c FROM codes WHERE used_by IS NOT NULL")

    return {
        "total_users":    _row(total_r)["c"],
        "active_users":   _row(active_r)["c"],
        "total_searches": _row(searches_r)["c"],
        "total_codes":    _row(codes_r)["c"],
        "used_codes":     _row(used_r)["c"],
    }
