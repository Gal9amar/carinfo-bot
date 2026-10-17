"""
Rich messages (Bot API 10.1+: sendRichMessage) — used for table layouts that
classic HTML parse mode cannot express. python-telegram-bot 22.x predates the
method, so we call the HTTP API directly.

Opt-in via env ``RICH_MESSAGES=1``. Callers must always keep a classic-HTML
fallback: ``send_rich_message`` returns False on any failure instead of raising.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def rich_enabled() -> bool:
    return os.environ.get("RICH_MESSAGES", "0") == "1"


async def send_rich_message(chat_id: int, html: str, reply_markup=None, is_rtl: bool = True) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not (token and rich_enabled()):
        return False
    payload: dict = {
        "chat_id": chat_id,
        "rich_message": {"html": html, "is_rtl": is_rtl},
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.to_dict()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"https://api.telegram.org/bot{token}/sendRichMessage", json=payload)
        data = resp.json()
        if data.get("ok"):
            return True
        logger.warning("sendRichMessage rejected: %s", data.get("description"))
    except Exception as exc:
        logger.warning("sendRichMessage failed: %s", type(exc).__name__)
    return False
