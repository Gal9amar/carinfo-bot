"""
CarInfo WhatsApp Bot — Green API webhook bridge.

Environment variables required:
  GREEN_API_ID_INSTANCE     — idInstance from console.green-api.com
  GREEN_API_TOKEN_INSTANCE  — apiTokenInstance
  GREEN_API_WEBHOOK_TOKEN   — secret token for webhook verification (set in GreenAPI settings)
  TELEGRAM_ADMIN_ID         — Telegram admin user_id (for purchase notifications, optional)
  PAYPAL_ME                 — e.g. https://www.paypal.me/G9ST
  TURSO_DATABASE_URL        — shared with bot.py
  TURSO_AUTH_TOKEN          — shared with bot.py
  PORT                      — HTTP port (default 8081)

Webhook URL to set in Green API console:
  https://<your-render-url>/webhook
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.gov_api import fetch_vehicle_data
from src.cache import cache
from src.db import init_db
from src.users import (
    _ensure_wa_user,
    is_allowed,
    increment_search,
    apply_code,
    get_last_plate,
    set_last_plate,
    get_wa_state,
    set_wa_state,
    get_quota_expires,
    is_blocked,
    link_wa_to_telegram,
)
from src import wa_menu as menu

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ID_INSTANCE    = os.environ.get("GREEN_API_ID_INSTANCE", "")
TOKEN_INSTANCE = os.environ.get("GREEN_API_TOKEN_INSTANCE", "")
WEBHOOK_TOKEN  = os.environ.get("GREEN_API_WEBHOOK_TOKEN", "")
ADMIN_TG_ID    = os.environ.get("TELEGRAM_ADMIN_ID", "")
PAYPAL_ME      = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")
PORT           = int(os.environ.get("PORT", 8081))

PLATE_RE = re.compile(r"^[\d\-]{5,10}$")

# ── Green API HTTP helpers ──────────────────────────────────────────────────

API_URL = os.environ.get("GREEN_API_URL", "https://api.green-api.com")

def _green_url(method: str) -> str:
    return (
        f"{API_URL}/waInstance{ID_INSTANCE}"
        f"/{method}/{TOKEN_INSTANCE}"
    )


async def send_message(chat_id: str, text: str) -> None:
    import urllib.request, urllib.error
    payload = json.dumps({"chatId": chat_id, "message": text}).encode()
    req = urllib.request.Request(
        _green_url("sendMessage"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.debug("sendMessage → %s", resp.status)
    except urllib.error.URLError as exc:
        logger.warning("sendMessage failed: %s", exc)


async def notify_telegram_admin(text: str) -> None:
    """Forward a plain-text notification to the Telegram admin via sendMessage.
    Works only if the Telegram bot is also running — uses its token directly."""
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not tg_token or not ADMIN_TG_ID:
        return
    import urllib.request, urllib.parse
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": ADMIN_TG_ID, "text": text}).encode()
    req  = urllib.request.Request(url, data=data, method="POST")
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception as exc:
        logger.warning("notify_telegram_admin failed: %s", exc)


# ── Message dispatcher ──────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> str:
    """972501234567@c.us  →  972501234567"""
    return raw.split("@")[0]


def _normalize_plate(text: str) -> str:
    return text.strip().replace("-", "").replace(" ", "")


async def handle_message(chat_id: str, phone: str, body: str) -> None:
    text  = body.strip()
    lower = text.lower()

    # Ensure user row exists
    user_id = await _ensure_wa_user(phone)

    # Blocked?
    if await is_blocked(user_id):
        await send_message(chat_id, menu.BLOCKED)
        return

    state = await get_wa_state(phone)

    # ── State: waiting for discount code ────────────────────────────────────
    if state == "WAITING_CODE":
        if lower in ("תפריט", "menu", "cancel", "ביטול"):
            await set_wa_state(phone, None)
            await send_message(chat_id, menu.WELCOME)
            return
        code = text.upper()
        success, msg = await apply_code(user_id, code)
        # Strip MarkdownV2 escapes from msg
        msg_plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", msg)
        msg_plain = re.sub(r"[*_`]", "", msg_plain)
        if success:
            await set_wa_state(phone, None)
            await send_message(chat_id, f"✅ {msg_plain}\n\nתוכל לחפש רכבים עכשיו.")
        else:
            await send_message(chat_id, f"❌ {msg_plain}\n\nנסה שוב או שלח 'תפריט' לחזרה.")
        return

    # ── State: waiting for package selection ────────────────────────────────
    if state == "WAITING_PACKAGE":
        if lower in ("תפריט", "menu", "cancel", "ביטול"):
            await set_wa_state(phone, None)
            await send_message(chat_id, menu.WELCOME)
            return
        pkg = menu.PACKAGE_DETAILS.get(text.strip())
        if not pkg:
            await send_message(chat_id, "שלח מספר 1-4 לבחירת חבילה, או 'תפריט' לחזרה.")
            return
        label, searches, price = pkg
        paypal_url = f"{PAYPAL_ME}/{price}"
        await set_wa_state(phone, f"WAITING_PAID|{searches}|{price}|{label}")
        await send_message(
            chat_id,
            menu.PAYMENT_REQUEST.format(label=label, price=price, paypal_url=paypal_url),
        )
        return

    # ── State: waiting for "שילמתי" confirmation ───────────────────────────
    if state and state.startswith("WAITING_PAID"):
        if lower in ("תפריט", "menu", "cancel", "ביטול"):
            await set_wa_state(phone, None)
            await send_message(chat_id, menu.WELCOME)
            return
        if "שילמתי" in text:
            parts  = state.split("|")
            searches = parts[1] if len(parts) > 1 else "?"
            price    = parts[2] if len(parts) > 2 else "?"
            label    = parts[3] if len(parts) > 3 else "?"
            await set_wa_state(phone, None)
            # Notify Telegram admin
            await notify_telegram_admin(
                f"💰 בקשת תשלום ווטסאפ!\n\n"
                f"📱 טלפון: {phone}\n"
                f"📦 {label}\n"
                f"💵 ₪{price}\n\n"
                f"לאחר אימות ב-PayPal הענק גישה דרך פאנל הניהול בטלגרם:\n"
                f"/admin grant {phone} {searches}"
            )
            await send_message(
                chat_id,
                "✅ קיבלנו את בקשתך!\n\nהגישה תיפתח לאחר אימות התשלום. בדרך כלל תוך מספר דקות.",
            )
            return
        await send_message(chat_id, "כשתסיים לשלם שלח: שילמתי\nלביטול שלח: תפריט")
        return

    # ── State: waiting for link code (WA ↔ Telegram) ───────────────────────
    if state == "WAITING_LINK_CODE":
        if lower in ("תפריט", "menu", "cancel", "ביטול"):
            await set_wa_state(phone, None)
            await send_message(chat_id, menu.WELCOME)
            return
        code = text.strip().upper()
        success, msg = await apply_code(user_id, code)
        msg_plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", msg)
        msg_plain = re.sub(r"[*_`]", "", msg_plain)
        if success:
            await set_wa_state(phone, None)
            await send_message(chat_id, f"✅ {msg_plain}\n\nהחשבונות קושרו בהצלחה!")
        else:
            await send_message(chat_id, f"❌ {msg_plain}\n\nנסה שוב או שלח 'תפריט' לחזרה.")
        return

    # ── Stateless commands ───────────────────────────────────────────────────

    if lower in ("תפריט", "menu", "hi", "hello", "שלום", "הי", "start"):
        await send_message(chat_id, menu.WELCOME)
        return

    if text == "1":
        allowed, left = await is_allowed(user_id)
        expires = await get_quota_expires(user_id) if left == -1 else None
        status  = menu.format_status(left, expires)
        await send_message(chat_id, f"📊 סטטוס חשבון:\n\n{status}")
        return

    if text == "2":
        await set_wa_state(phone, "WAITING_PACKAGE")
        await send_message(chat_id, menu.PACKAGES)
        return

    if text == "3":
        await set_wa_state(phone, "WAITING_CODE")
        await send_message(chat_id, menu.ENTER_CODE)
        return

    if text == "4":
        await send_message(chat_id, menu.HELP)
        return

    # ── Plate search ─────────────────────────────────────────────────────────
    plate = _normalize_plate(text)
    if PLATE_RE.match(plate) and len(plate) >= 5:
        allowed, left = await is_allowed(user_id)
        if not allowed:
            await send_message(chat_id, menu.NO_QUOTA)
            return

        if left == 1:
            await send_message(chat_id, menu.LAST_FREE)

        await send_message(chat_id, menu.SEARCHING)

        try:
            record = await fetch_vehicle_data(plate)
        except Exception as exc:
            logger.error("WA fetch error plate=%s: %s", plate, exc)
            await send_message(chat_id, menu.ERROR)
            return

        if record is None:
            await send_message(chat_id, menu.NOT_FOUND.format(plate=plate))
            return

        last = await get_last_plate(user_id)
        if last != plate:
            await increment_search(user_id, plate)
            await set_last_plate(user_id, plate)

        expires = await get_quota_expires(user_id) if left == -1 else None
        new_left = left if left == -1 else max(0, left - 1)
        result_text = menu.format_result(record, new_left, expires)
        await send_message(chat_id, result_text)
        return

    # ── Fallback ──────────────────────────────────────────────────────────────
    await send_message(
        chat_id,
        "לא הבנתי 🤔\n\nשלח מספר רכב לחיפוש, או 'תפריט' לאפשרויות.",
    )


# ── Webhook HTTP server ─────────────────────────────────────────────────────

class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("HTTP %s", format % args)

    def _send(self, code: int, body: bytes = b"OK") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, b"CarInfo WA Bot running")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)

        logger.info("POST /webhook from %s | headers: %s | body: %s",
                    self.client_address,
                    dict(self.headers),
                    raw[:300])

        self._send(200)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("JSON decode error: %s | raw: %s", e, raw[:200])
            return

        asyncio.run(_dispatch(data))


async def _dispatch(data: dict) -> None:
    try:
        # Green API wraps the payload in a "body" key when using receiveNotification
        # but sends it flat when using webhook endpoint — handle both
        payload = data.get("body", data)

        type_webhook = payload.get("typeWebhook", "")
        if type_webhook != "incomingMessageReceived":
            logger.debug("Ignoring webhook type: %s", type_webhook)
            return

        msg_data = payload.get("messageData", {})
        if msg_data.get("typeMessage") not in ("textMessage", "extendedTextMessage"):
            return

        # Extract body
        body = (
            msg_data.get("textMessageData", {}).get("textMessage")
            or msg_data.get("extendedTextMessageData", {}).get("text")
            or ""
        ).strip()
        if not body:
            return

        sender  = payload.get("senderData", {})
        chat_id = sender.get("chatId", "")
        phone   = _normalize_phone(chat_id)

        if not phone or not chat_id:
            return

        logger.info("Incoming WA message from %s: %s", phone, body[:50])
        await handle_message(chat_id, phone, body)

    except Exception as exc:
        logger.error("_dispatch error: %s", exc)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    if not ID_INSTANCE or not TOKEN_INSTANCE:
        raise RuntimeError(
            "GREEN_API_ID_INSTANCE and GREEN_API_TOKEN_INSTANCE must be set"
        )

    asyncio.run(init_db())
    logger.info("Turso DB initialized (WA bot)")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info("WhatsApp webhook server listening on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
