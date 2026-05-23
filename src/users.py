"""
User management – quota, access codes, grants.
Storage: Turso (libsql) via src/db.py
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.db import execute

FREE_SEARCHES   = 10   # base welcome quota (loaded from DB at startup)
PROMO_SEARCHES  = 0    # 0 = inactive, -1 = unlimited, >0 = specific count
PROMO_START     = ''   # 'YYYY-MM-DD' or '' (no restriction)
PROMO_END       = ''   # 'YYYY-MM-DD' or '' (no expiry)

_SUBSCRIBERS_GROUP = "מנויים"


async def _get_subscribers_group_id() -> int | None:
    """Return the id of the subscribers group, creating it if missing."""
    r = await execute("SELECT id FROM user_groups WHERE name=?", [_SUBSCRIBERS_GROUP])
    if r.rows:
        return r.rows[0][0]
    await execute("INSERT OR IGNORE INTO user_groups (name) VALUES (?)", [_SUBSCRIBERS_GROUP])
    r2 = await execute("SELECT id FROM user_groups WHERE name=?", [_SUBSCRIBERS_GROUP])
    return r2.rows[0][0] if r2.rows else None


async def add_to_subscribers(user_id: int) -> None:
    gid = await _get_subscribers_group_id()
    if gid:
        await execute(
            "INSERT OR IGNORE INTO user_group_members (group_id, user_id) VALUES (?, ?)",
            [gid, user_id],
        )


async def remove_from_subscribers(user_id: int) -> None:
    gid = await _get_subscribers_group_id()
    if gid:
        await execute(
            "DELETE FROM user_group_members WHERE group_id=? AND user_id=?",
            [gid, user_id],
        )


def get_current_welcome_quota() -> int:
    """Returns the quota a new user should receive right now."""
    from datetime import date
    if PROMO_SEARCHES != 0:
        today = date.today().isoformat()
        start_ok = (not PROMO_START) or (today >= PROMO_START)
        end_ok   = (not PROMO_END)   or (today <= PROMO_END)
        if start_ok and end_ok:
            return PROMO_SEARCHES
    return FREE_SEARCHES


async def load_welcome_settings() -> None:
    """Load welcome/promo settings from DB into module-level vars."""
    global FREE_SEARCHES, PROMO_SEARCHES, PROMO_START, PROMO_END
    from src.db import get_bot_setting
    try:
        fs = await get_bot_setting("free_searches")
        if fs:
            FREE_SEARCHES = int(fs)
        ps = await get_bot_setting("promo_searches")
        PROMO_SEARCHES = int(ps) if ps else 0
        PROMO_START = (await get_bot_setting("promo_start")) or ''
        PROMO_END   = (await get_bot_setting("promo_end"))   or ''
    except Exception:
        pass


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
        [user_id, username, full_name, get_current_welcome_quota()],
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
                # Subscription expired – revert to 0 and remove from subscribers
                await execute(
                    "UPDATE users SET searches_quota = 0, quota_expires = NULL WHERE user_id = ?",
                    [user_id],
                )
                await remove_from_subscribers(user_id)
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
    # Remove from subscribers group when quota is fully exhausted
    r = await execute(
        "SELECT searches_quota, searches_done FROM users WHERE user_id = ?",
        [user_id],
    )
    u = _row(r)
    if u and u["searches_quota"] != -1 and u["searches_quota"] <= u["searches_done"]:
        await remove_from_subscribers(user_id)


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
    # Auto-join subscribers group on successful code redemption
    await add_to_subscribers(user_id)
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

    if searches == -2:  # permanent unlimited
        await execute(
            "UPDATE users SET searches_quota = -1, searches_done = 0, quota_expires = NULL WHERE user_id = ?",
            [target_id],
        )
        msg = "גישה חופשית ללא הגבלת זמן"
    elif searches == -1:
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
    # Auto-join subscribers group on any positive grant
    await add_to_subscribers(target_id)
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


async def check_new_user(user_id: int) -> bool:
    """Returns True if user_id is not yet in the database (before _ensure_user runs)."""
    r = await execute("SELECT 1 FROM users WHERE user_id=?", [user_id])
    return not bool(r.rows)


async def record_referral(new_user_id: int, referrer_id: int, bonus: int = 10) -> None:
    """Record that new_user_id was referred by referrer_id (only if not already set)."""
    r = await execute("SELECT referred_by FROM users WHERE user_id=?", [new_user_id])
    if r.rows and r.rows[0][0] is None:
        await execute("UPDATE users SET referred_by=? WHERE user_id=?", [referrer_id, new_user_id])
        await execute(
            "INSERT INTO referrals (referrer_id, referee_id, bonus) VALUES (?, ?, ?)",
            [referrer_id, new_user_id, bonus],
        )


async def get_referral_count(user_id: int) -> int:
    """Count how many users this user has successfully referred."""
    r = await execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", [user_id])
    return r.rows[0][0] if r.rows else 0


async def get_referrals(referrer_id: int) -> list[dict]:
    """Return all referrals made by referrer_id with the referred user's info."""
    r = await execute(
        """SELECT rf.id, rf.referee_id, rf.bonus, rf.joined_at,
                  u.username, u.full_name
           FROM referrals rf
           LEFT JOIN users u ON u.user_id = rf.referee_id
           WHERE rf.referrer_id = ?
           ORDER BY rf.joined_at DESC""",
        [referrer_id],
    )
    result = []
    for row in r.rows:
        username  = row[4] or ""
        full_name = row[5] or ""
        name = f"@{username}" if username else (full_name or f"id:{row[1]}")
        result.append({
            "id":        row[0],
            "referee_id": row[1],
            "bonus":     row[2],
            "joined_at": row[3],
            "name":      name,
        })
    return result


async def get_all_users() -> list[dict]:
    r = await execute(
        "SELECT user_id, username, full_name, searches_done, searches_quota, first_seen, last_seen, blocked, channel FROM users ORDER BY searches_done DESC"
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




async def get_search_history(user_id: int, limit: int = 10) -> list[str]:
    """Returns last N unique plates searched by user, most recent first."""
    r = await execute(
        "SELECT plate FROM search_history WHERE user_id = ? "
        "GROUP BY plate ORDER BY MAX(searched_at) DESC LIMIT ?",
        [user_id, limit],
    )
    return [row[0] for row in r.rows]

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
