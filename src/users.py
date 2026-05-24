"""
User management – quota, access codes, grants.
Storage: Turso (libsql) via src/db.py
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.db import execute

FREE_SEARCHES       = 10   # base welcome quota (loaded from DB at startup)
PROMO_SEARCHES      = 0    # 0 = inactive, -1 = unlimited, >0 = specific count
PROMO_START         = ''   # 'YYYY-MM-DD' or '' (no restriction)
PROMO_END           = ''   # 'YYYY-MM-DD' or '' (no expiry)
PROMO_DURATION_DAYS = 30   # days from join date (0 = no expiry)
PROMO_IS_SUBSCRIBER = False
PROMO_LABEL         = ''   # display label for welcome message

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


def is_promo_active() -> bool:
    """Returns True if the join promo is currently active."""
    if PROMO_SEARCHES == 0:
        return False
    from datetime import date
    today = date.today().isoformat()
    start_ok = (not PROMO_START) or (today >= PROMO_START)
    end_ok   = (not PROMO_END)   or (today <= PROMO_END)
    return start_ok and end_ok


def get_current_welcome_quota() -> int:
    """Returns the quota a new user should receive right now."""
    if is_promo_active():
        return PROMO_SEARCHES
    return FREE_SEARCHES


def get_promo_welcome_info() -> dict | None:
    """Returns promo info dict for welcome message, or None if no active promo."""
    if not is_promo_active():
        return None
    expires_str = None
    if PROMO_DURATION_DAYS > 0:
        from datetime import date, timedelta
        exp = date.today() + timedelta(days=PROMO_DURATION_DAYS)
        expires_str = exp.strftime("%d/%m/%Y")
    searches = PROMO_SEARCHES
    label = PROMO_LABEL or (
        "גישה ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
    )
    return {
        "label": label,
        "searches": searches,
        "duration_days": PROMO_DURATION_DAYS,
        "expires_str": expires_str,
        "is_subscriber": PROMO_IS_SUBSCRIBER,
    }


async def load_welcome_settings() -> None:
    """Load welcome/promo settings from DB into module-level vars."""
    global FREE_SEARCHES, PROMO_SEARCHES, PROMO_START, PROMO_END
    global PROMO_DURATION_DAYS, PROMO_IS_SUBSCRIBER, PROMO_LABEL
    from src.db import get_bot_setting
    try:
        fs = await get_bot_setting("free_searches")
        if fs:
            FREE_SEARCHES = int(fs)
        ps = await get_bot_setting("promo_searches")
        PROMO_SEARCHES = int(ps) if ps else 0
        PROMO_START = (await get_bot_setting("promo_start")) or ''
        PROMO_END   = (await get_bot_setting("promo_end"))   or ''
        pd = await get_bot_setting("promo_duration_days")
        PROMO_DURATION_DAYS = int(pd) if pd else 30
        pi = await get_bot_setting("promo_is_subscriber")
        PROMO_IS_SUBSCRIBER = pi == "1"
        PROMO_LABEL = (await get_bot_setting("promo_label")) or ''
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
    exists = await execute("SELECT 1 FROM users WHERE user_id=?", [user_id])
    is_new = not bool(exists.rows)

    if is_new:
        quota = get_current_welcome_quota()
        expires = None
        if is_promo_active() and PROMO_SEARCHES != 0 and PROMO_DURATION_DAYS > 0:
            expires = (datetime.now() + timedelta(days=PROMO_DURATION_DAYS)).isoformat()
        await execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, searches_quota, quota_expires) VALUES (?, ?, ?, ?, ?)",
            [user_id, username, full_name, quota, expires],
        )
        if is_promo_active() and PROMO_IS_SUBSCRIBER:
            await add_to_subscribers(user_id)

    await execute(
        """UPDATE users SET
            username  = CASE WHEN ? != '' THEN ? ELSE username  END,
            full_name = CASE WHEN ? != '' THEN ? ELSE full_name END,
            last_seen = datetime('now')
           WHERE user_id=?""",
        [username, username, full_name, full_name, user_id],
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

    if searches == 0:  # reset to free tier — 0 searches
        await remove_from_subscribers(target_id)
        await execute(
            "UPDATE users SET searches_quota = 0, searches_done = 0, quota_expires = NULL WHERE user_id = ?",
            [target_id],
        )
        msg = "מנוי חינם — 0 חיפושים"
    elif searches == -2:  # permanent unlimited
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
        "SELECT u.user_id, u.username, u.full_name, u.searches_done, u.searches_quota, "
        "u.first_seen, u.last_seen, u.blocked, u.channel, u.quota_expires, "
        "CASE WHEN ugm.user_id IS NOT NULL THEN 1 ELSE 0 END as is_subscriber "
        "FROM users u "
        "LEFT JOIN user_group_members ugm ON ugm.user_id = u.user_id "
        "  AND ugm.group_id = (SELECT id FROM user_groups WHERE name='מנויים' LIMIT 1) "
        "ORDER BY u.last_seen DESC"
    )
    users = []
    for u in _rows(r):
        quota = u["searches_quota"]
        done  = u["searches_done"]
        u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
        u["is_subscriber"] = bool(u.get("is_subscriber", 0))
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
    from datetime import date, timedelta
    today     = date.today().isoformat()
    week_ago  = (date.today() - timedelta(days=7)).isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()

    total_r         = await execute("SELECT COUNT(*) as c FROM users")
    blocked_r       = await execute("SELECT COUNT(*) as c FROM users WHERE blocked=1")
    new_today_r     = await execute("SELECT COUNT(*) as c FROM users WHERE first_seen >= ?", [today])
    new_week_r      = await execute("SELECT COUNT(*) as c FROM users WHERE first_seen >= ?", [week_ago])
    active_week_r   = await execute("SELECT COUNT(*) as c FROM users WHERE last_seen >= ?", [week_ago])
    active_month_r  = await execute("SELECT COUNT(*) as c FROM users WHERE last_seen >= ?", [month_ago])

    subscribers_r   = await execute(
        "SELECT COUNT(*) as c FROM user_group_members ugm "
        "JOIN user_groups ug ON ug.id = ugm.group_id WHERE ug.name='מנויים'"
    )
    unlimited_r     = await execute(
        "SELECT COUNT(*) as c FROM users WHERE searches_quota=-1 AND (quota_expires IS NULL OR quota_expires > datetime('now'))"
    )
    expiring_soon_r = await execute(
        "SELECT COUNT(*) as c FROM users WHERE searches_quota=-1 AND quota_expires IS NOT NULL "
        "AND quota_expires <= datetime('now', '+7 days') AND quota_expires > datetime('now')"
    )

    searches_r       = await execute("SELECT COUNT(*) as c FROM search_history")
    searches_today_r = await execute(
        "SELECT COUNT(*) as c FROM search_history WHERE searched_at >= ?", [today]
    )
    searches_week_r  = await execute(
        "SELECT COUNT(*) as c FROM search_history WHERE searched_at >= ?", [week_ago]
    )

    pending_payments_r = await execute("SELECT COUNT(*) as c FROM pending_payments")
    approved_revenue_r = await execute(
        "SELECT COALESCE(SUM(price), 0) as c FROM pending_payments WHERE 1=0"  # approved are deleted
    )

    codes_r    = await execute("SELECT COUNT(*) as c FROM codes")
    used_r     = await execute("SELECT COUNT(*) as c FROM codes WHERE used_by IS NOT NULL")
    active_codes_r = await execute(
        "SELECT COUNT(*) as c FROM codes WHERE used_by IS NULL "
        "AND (expires IS NULL OR expires > datetime('now'))"
    )

    tickets_open_r = await execute(
        "SELECT COUNT(*) as c FROM tickets WHERE status='open'"
    )

    top_users_r = await execute(
        "SELECT username, full_name, searches_done FROM users "
        "ORDER BY searches_done DESC LIMIT 5"
    )
    top_users = [
        {"name": (r[0] and f"@{r[0]}") or r[1] or "?", "searches": r[2]}
        for r in top_users_r.rows
    ]

    return {
        "total_users":      _row(total_r)["c"],
        "blocked_users":    _row(blocked_r)["c"],
        "new_today":        _row(new_today_r)["c"],
        "new_week":         _row(new_week_r)["c"],
        "active_week":      _row(active_week_r)["c"],
        "active_month":     _row(active_month_r)["c"],
        "subscribers":      _row(subscribers_r)["c"],
        "unlimited":        _row(unlimited_r)["c"],
        "expiring_soon":    _row(expiring_soon_r)["c"],
        "total_searches":   _row(searches_r)["c"],
        "searches_today":   _row(searches_today_r)["c"],
        "searches_week":    _row(searches_week_r)["c"],
        "pending_payments": _row(pending_payments_r)["c"],
        "total_codes":      _row(codes_r)["c"],
        "used_codes":       _row(used_r)["c"],
        "active_codes":     _row(active_codes_r)["c"],
        "tickets_open":     _row(tickets_open_r)["c"],
        "top_users":        top_users,
    }


async def get_users_expiring_today() -> list[int]:
    """Returns user_ids whose promo expires today (for last-day notification)."""
    r = await execute(
        "SELECT user_id FROM users WHERE date(quota_expires) = date('now') AND searches_quota = -1",
        [],
    )
    return [row[0] for row in r.rows]
