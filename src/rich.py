"""
Rich messages (Bot API 10.1+: sendRichMessage) — used for table layouts that
classic HTML parse mode cannot express. python-telegram-bot 22.x predates the
method, so we call the HTTP API directly.

Opt-in via the admin setting ``rich_messages_enabled`` (admin panel → Settings,
or the bot admin menu). Callers must always keep a classic-HTML fallback:
``send_rich_message`` returns False when disabled or on any failure, never raises.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def rich_enabled() -> bool:
    from src.db import get_bot_setting
    try:
        return (await get_bot_setting("rich_messages_enabled")) == "1"
    except Exception:
        return False


async def send_rich_message(chat_id: int, html: str, reply_markup=None, is_rtl: bool = True, *, mirror: bool = True,
                            message_thread_id: int | None = None, reply_to: int | None = None, force: bool = False) -> bool:
    """Send a table message. `mirror=False` is used by the activity mirror for its own copies."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not (token and (force or await rich_enabled())):
        return False
    payload: dict = {
        "chat_id": chat_id,
        "rich_message": {"html": html, "is_rtl": is_rtl},
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.to_dict()
    if message_thread_id:
        payload["message_thread_id"] = message_thread_id
    if reply_to:
        payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    if not mirror:
        payload["disable_notification"] = True
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"https://api.telegram.org/bot{token}/sendRichMessage", json=payload)
        data = resp.json()
        if data.get("ok"):
            if mirror:
                from src import mirror as _mirror
                await _mirror.record_outgoing(
                    chat_id, "rich", html, reply_markup=reply_markup,
                    message_id=(data.get("result") or {}).get("message_id"),
                )
            return True
        logger.warning("sendRichMessage rejected: %s", data.get("description"))
    except Exception as exc:
        logger.warning("sendRichMessage failed: %s", type(exc).__name__)
    return False
