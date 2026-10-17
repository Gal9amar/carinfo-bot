"""Single source of truth for premium-feature access (compare, PDF report, Yad2 alerts…).

Used by BOTH the Mini App API (api.py) and the Telegram bot (bot.py): a user entitled to a
feature gets it in both places, a user who isn't is blocked in both.

Rule for feature `prefix` (settings `{prefix}_enabled / _public / _public_start / _public_end / _groups`):
admin ✔ · unlimited plan (quota -1) ✔ · subscriber (מנויים / VIP) ✔ · member of one of `{prefix}_groups` ✔ ·
free user with searches left ✔ · otherwise only while `{prefix}_enabled != "0"` and the public window is open.
"""
import json
import os
from datetime import date
from typing import Optional

ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))


async def feature_open(user_id: int, prefix: str, *, quota: Optional[int] = None,
                       left: Optional[int] = None, subscriber: Optional[bool] = None) -> bool:
    """`quota`/`left`/`subscriber` may be passed when the caller already loaded them."""
    import asyncio
    from src.db import get_bot_setting, execute
    from src.users import get_user_by_id, is_subscriber, is_global_unlimited_active
    if user_id == ADMIN_ID:
        return True
    if quota is None or left is None:
        db_user, global_unlimited = await asyncio.gather(get_user_by_id(user_id), is_global_unlimited_active())
        quota = db_user.get("searches_quota", 0) if db_user else 0
        left = -1 if global_unlimited else (db_user.get("searches_left", 0) if db_user else 0)
    if quota == -1 or left != 0:
        return True
    if subscriber is None:
        subscriber = await is_subscriber(user_id)
    if subscriber:
        return True
    try:
        groups = [int(g) for g in json.loads((await get_bot_setting(f"{prefix}_groups")) or "[]")]
    except (ValueError, TypeError):
        groups = []
    if groups:
        r = await execute(
            f"SELECT 1 FROM user_group_members WHERE user_id=? AND group_id IN ({','.join('?' * len(groups))})",
            [user_id, *groups],
        )
        if r.rows:
            return True
    if (await get_bot_setting(f"{prefix}_enabled")) == "0":
        return False
    if (await get_bot_setting(f"{prefix}_public")) == "1":
        today = str(date.today())
        ps = (await get_bot_setting(f"{prefix}_public_start")) or ""
        pe = (await get_bot_setting(f"{prefix}_public_end")) or ""
        return (not ps or today >= ps) and (not pe or today <= pe)
    return False
