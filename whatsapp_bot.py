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
    _phone_to_id,
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
    consume_link_code,
    admin_stats,
    admin_grant,
    get_all_users,
    block_user,
    unblock_user,
    get_user_by_phone,
    get_search_history,
    get_user_by_id,
    generate_code,
)
from src import wa_menu as menu
from src import yad2 as _yad2

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ID_INSTANCE    = os.environ.get("GREEN_API_ID_INSTANCE", "")
TOKEN_INSTANCE = os.environ.get("GREEN_API_TOKEN_INSTANCE", "")
WEBHOOK_TOKEN  = os.environ.get("GREEN_API_WEBHOOK_TOKEN", "")
ADMIN_TG_ID    = os.environ.get("TELEGRAM_ADMIN_ID", "")
ADMIN_WA_PHONE = os.environ.get("ADMIN_WA_PHONE", "")
PAYPAL_ME      = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")
PORT           = int(os.environ.get("PORT", 8081))
TG_BOT_USERNAME = "israelcarinfobot"
WA_BOT_PHONE   = os.environ.get("WA_BOT_PHONE", "972526777070")

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


async def send_wa_pdf(chat_id: str, pdf_bytes: bytes, filename: str, caption: str = "") -> None:
    """Send a PDF file via Green API sendFileByUpload (multipart/form-data)."""
    import httpx
    url = _green_url("sendFileByUpload")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                files={"file": (filename, pdf_bytes, "application/pdf")},
                data={"chatId": chat_id, "caption": caption},
            )
            logger.debug("sendFileByUpload → %s %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("sendFileByUpload failed: %s", exc)


async def notify_telegram_admin_or_user(user_id: int, text: str) -> None:
    """Send a Telegram message to a specific user_id via the bot token."""
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not tg_token or not user_id:
        return
    import urllib.request, urllib.parse
    url  = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    user_id,
        "text":       text,
        "parse_mode": "MarkdownV2",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        urllib.request.urlopen(req, timeout=8)
    except Exception as exc:
        logger.warning("notify_telegram_user(%s) failed: %s", user_id, exc)


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


# ── Admin handler ───────────────────────────────────────────────────────────

async def handle_admin(chat_id: str, phone: str, text: str) -> bool:
    """Handle admin commands. Returns True if handled."""
    logger.info("handle_admin: phone='%s' ADMIN_WA_PHONE='%s' match=%s", phone, ADMIN_WA_PHONE, phone == ADMIN_WA_PHONE)
    if not ADMIN_WA_PHONE or phone != ADMIN_WA_PHONE:
        return False

    # ensure admin has a DB row so get/set_wa_state work correctly
    await _ensure_wa_user(phone)

    lower = text.strip().lower()
    parts = text.strip().split()
    state = await get_wa_state(phone)

    # סטטיסטיקות
    ADMIN_MENU = (
        "🛠 *פאנל ניהול CarInfo*\n"
        "─────────────────\n"
        "א  סטטיסטיקות\n"
        "ב  רשימת משתמשים\n"
        "ג  הענק בדיקות\n"
        "ד  אשר תשלום\n"
        "ה  חסום משתמש\n"
        "ו  שחרר משתמש\n"
        "ז  שלח הודעה לכולם\n"
        "ח  נקה שורות זבל\n"
        "ט  צור קוד הטבה\n"
        "─────────────────\n"
        "שלח אות לבחירה\n"
        "יציאה: שלח *תפריט*"
    )

    if state == "ADMIN_CREATE_CODE":
        if lower in ("אדמין", "admin", "ביטול", "תפריט"):
            await set_wa_state(phone, "ADMIN_MENU")
            await send_message(chat_id, ADMIN_MENU)
            return True
        try:
            if lower == "חודש":
                code = await generate_code(searches=30, unlimited=True, monthly=True)
                label = "מנוי חודשי"
            elif lower == "חינם":
                code = await generate_code(searches=0, unlimited=True, monthly=False)
                label = "ללא הגבלה"
            else:
                amount = int(text.strip())
                code = await generate_code(searches=amount)
                label = f"{amount} חיפושים"
            await set_wa_state(phone, "ADMIN_MENU")
            await send_message(chat_id,
                f"✅ *קוד נוצר!*\n"
                f"─────────────────\n"
                f"🎟️ קוד: *{code}*\n"
                f"📦 סוג: {label}\n\n"
                f"─────────────────\n{ADMIN_MENU}"
            )
        except ValueError:
            await send_message(chat_id, "❌ שלח מספר, 'חודש', או 'חינם'")
        return True

    if lower in ("אדמין", "admin", "תפריט אדמין"):
        await send_message(chat_id, ADMIN_MENU)
        await set_wa_state(phone, "ADMIN_MENU")
        return True

    if state == "ADMIN_MENU":
        if lower in ("תפריט", "menu", "יציאה"):
            await set_wa_state(phone, None)
            await send_message(chat_id, menu.WELCOME)
            return True

        if text == "א":
            stats = await admin_stats()
            await send_message(chat_id,
                f"📊 *סטטיסטיקות*\n"
                f"─────────────────\n"
                f"👤 משתמשים: {stats['total_users']} | פעילים: {stats['active_users']}\n"
                f"🔍 בדיקות: {stats['total_searches']}\n"
                f"🔑 קודים: {stats['used_codes']}/{stats['total_codes']} נוצלו\n\n"
                f"─────────────────\n"
                f"{ADMIN_MENU}"
            )
            return True
        if text == "ב":
            users = await get_all_users()
            lines = [f"👥 *משתמשים ({len(users)})*\n─────────────────"]
            for u in users[:20]:
                wa    = u.get("whatsapp_phone") or ""
                tg    = u.get("username") or ""
                if wa and tg and wa != tg:
                    name = f"📱{wa} / ✈️{tg}"
                elif wa:
                    name = f"📱{wa}"
                elif tg:
                    name = f"✈️{tg}"
                else:
                    name = f"id:{u['user_id']}"
                quota = u.get("searches_quota", 0)
                done  = u.get("searches_done", 0)
                left  = u.get("searches_left", 0)
                bl    = "🔴" if u.get("blocked") else "🟢"
                qs    = "∞" if quota == -1 else str(quota)
                ls    = "∞" if left  == -1 else str(left)
                lines.append(f"{bl} {name}  {done}/{qs} (נותרו:{ls})")
            lines.append(f"\n─────────────────\n{ADMIN_MENU}")
            await send_message(chat_id, "\n".join(lines))
            return True
        if text == "ג":
            await set_wa_state(phone, None)
            await send_message(chat_id, "שלח:\ngrant 972501234567 50\n\nאו -1 למנוי חודשי, -2 לצמיתות\n\nלחזרה: שלח *אדמין*")
            return True
        if text == "ד":
            await set_wa_state(phone, None)
            await send_message(chat_id, "שלח:\napprove 972501234567 50\n\nלחזרה: שלח *אדמין*")
            return True
        if text == "ה":
            await set_wa_state(phone, None)
            await send_message(chat_id, "שלח:\nblock 972501234567\n\nלחזרה: שלח *אדמין*")
            return True
        if text == "ו":
            await set_wa_state(phone, None)
            await send_message(chat_id, "שלח:\nunblock 972501234567\n\nלחזרה: שלח *אדמין*")
            return True
        if text == "ז":
            await set_wa_state(phone, None)
            await send_message(chat_id, "שלח:\nשלח לכולם טקסט ההודעה שלך\n\nלחזרה: שלח *אדמין*")
            return True
        if text == "ח":
            from src.db import execute as _exec
            r = await _exec(
                "DELETE FROM users WHERE username = whatsapp_phone AND searches_quota = 20 AND searches_done = 0"
            )
            await send_message(chat_id,
                f"🧹 *ניקוי הושלם*\n─────────────────\n{ADMIN_MENU}"
            )
            return True
        if text == "ט":
            await set_wa_state(phone, "ADMIN_CREATE_CODE")
            await send_message(chat_id,
                "🎟️ *צור קוד הטבה*\n"
                "─────────────────\n"
                "שלח בפורמט:\n"
                "*כמות* — לדוגמה: 50\n"
                "*חודש* — מנוי חודשי\n"
                "*חינם* — ללא הגבלה\n\n"
                "לביטול: שלח *אדמין*"
            )
            return True
        # אות לא מוכרת — הצג תפריט שוב
        await send_message(chat_id, ADMIN_MENU)
        return True

    if lower in ("סטטיסטיקות", "סטט", "stats"):
        stats = await admin_stats()
        await send_message(chat_id,
            f"📊 *סטטיסטיקות*\n"
            f"─────────────────\n"
            f"👤 משתמשים: {stats['total_users']} | פעילים: {stats['active_users']}\n"
            f"🔍 בדיקות: {stats['total_searches']}\n"
            f"🔑 קודים: {stats['used_codes']}/{stats['total_codes']} נוצלו\n\n"
            f"שלח *אדמין* לתפריט ניהול"
        )
        return True

    # רשימת משתמשים
    if lower == "משתמשים":
        users = await get_all_users()
        if not users:
            await send_message(chat_id, "אין משתמשים עדיין.")
            return True
        lines = [f"👥 *משתמשים ({len(users)})*\n─────────────────"]
        for u in users[:20]:
            phone_u  = u.get("whatsapp_phone") or u.get("username") or f"id:{u['user_id']}"
            quota    = u.get("searches_quota", 0)
            done     = u.get("searches_done", 0)
            left     = u.get("searches_left", 0)
            blocked  = "🔴" if u.get("blocked") else "🟢"
            quota_s  = "∞" if quota == -1 else str(quota)
            left_s   = "∞" if left  == -1 else str(left)
            lines.append(f"{blocked} {phone_u}\n   {done}/{quota_s} | נותרו: {left_s}")
        await send_message(chat_id, "\n".join(lines))
        return True

    # חיפוש משתמש לפי טלפון
    if parts[0] == "משתמש" and len(parts) >= 2:
        target_phone = parts[1]
        u = await get_user_by_phone(target_phone)
        if not u:
            await send_message(chat_id, f"❌ משתמש {target_phone} לא נמצא")
            return True
        quota   = u.get("searches_quota", 0)
        done    = u.get("searches_done", 0)
        left    = u.get("searches_left", 0)
        blocked = "🔴 חסום" if u.get("blocked") else "🟢 פעיל"
        expires = u.get("quota_expires", "")
        exp_str = f"\nתוקף: {expires[:10]}" if expires else ""
        quota_s = "∞" if quota == -1 else str(quota)
        left_s  = "∞" if left  == -1 else str(left)
        await send_message(chat_id,
            f"👤 *{target_phone}*\n"
            f"─────────────────\n"
            f"סטטוס: {blocked}\n"
            f"בדיקות: {done}/{quota_s} | נותרו: {left_s}{exp_str}\n\n"
            f"grant {target_phone} 50 — הענק בדיקות\n"
            f"block {target_phone} — חסום"
        )
        return True

    # broadcast
    if lower.startswith("שלח לכולם "):
        broadcast_text = text[len("שלח לכולם "):].strip()
        if not broadcast_text:
            await send_message(chat_id, "שימוש: שלח לכולם טקסט ההודעה")
            return True
        users = await get_all_users()
        sent_ok = sent_fail = 0
        await send_message(chat_id, f"📤 שולח ל-{len(users)} משתמשים...")
        for u in users:
            wa_phone = u.get("whatsapp_phone")
            if not wa_phone or wa_phone == ADMIN_WA_PHONE:
                continue
            target_chat = f"{wa_phone}@c.us"
            try:
                await send_message(target_chat, f"📢 *הודעה מהמנהל:*\n\n{broadcast_text}")
                sent_ok += 1
            except Exception:
                sent_fail += 1
            await asyncio.sleep(0.3)
        await send_message(chat_id, f"✅ נשלח: {sent_ok} | ❌ נכשל: {sent_fail}")
        return True

    # אשר REF — אישור תשלום לפי קוד
    if parts[0] in ("אשר", "approve") and len(parts) == 2:
        ref = parts[1].upper()
        from src.db import execute as _exec
        r = await _exec("SELECT * FROM pending_payments WHERE ref = ?", [ref])
        cols = [c.name for c in r.columns]
        row  = dict(zip(cols, r.rows[0])) if r.rows else None
        if not row:
            await send_message(chat_id, f"❌ קוד {ref} לא נמצא או כבר טופל")
            return True
        target_phone = row["phone"]
        amount       = row["searches"]
        label        = row["label"]
        price        = row["price"]
        target_id = _phone_to_id(target_phone)
        await _ensure_wa_user(target_phone)
        msg = await admin_grant(target_id, target_id, amount, f"payment approved ref={ref}")
        msg_plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", msg)
        msg_plain = re.sub(r"[*_`]", "", msg_plain)
        await _exec("DELETE FROM pending_payments WHERE ref = ?", [ref])
        await send_message(chat_id, f"✅ אושר! {target_phone}: {msg_plain}")
        target_chat = f"{target_phone}@c.us"
        desc = "מנוי חודשי ללא הגבלה" if amount == -1 else f"{amount} בדיקות"
        await send_message(target_chat,
            f"✅ *התשלום אושר!*\n"
            f"─────────────────\n"
            f"📦 {label}\n"
            f"נוספו לך {desc} — תוכל לחפש מיד!\n\n"
            f"🔍 שלח מספר רכב לחיפוש"
        )
        return True

    # דחה REF — דחיית תשלום
    if parts[0] == "דחה" and len(parts) == 2:
        ref = parts[1].upper()
        from src.db import execute as _exec
        r = await _exec("SELECT * FROM pending_payments WHERE ref = ?", [ref])
        cols = [c.name for c in r.columns]
        row  = dict(zip(cols, r.rows[0])) if r.rows else None
        if not row:
            await send_message(chat_id, f"❌ קוד {ref} לא נמצא")
            return True
        target_phone = row["phone"]
        await _exec("DELETE FROM pending_payments WHERE ref = ?", [ref])
        await send_message(chat_id, f"🚫 בקשת {target_phone} נדחתה")
        target_chat = f"{target_phone}@c.us"
        await send_message(target_chat,
            "❌ *התשלום לא אומת*\n\n"
            "לא הצלחנו לאמת את התשלום.\n"
            "לסיוע — פנה למנהל."
        )
        return True

    # grant <phone> <amount>
    if parts[0].lower() == "grant" and len(parts) >= 3:
        target_phone = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            await send_message(chat_id, "❌ כמות חייבת להיות מספר\nשימוש: grant 972501234567 50")
            return True
        target_id = _phone_to_id(target_phone)
        await _ensure_wa_user(target_phone)
        msg = await admin_grant(target_id, target_id, amount, "granted via WA admin")
        msg_plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", msg)
        msg_plain = re.sub(r"[*_`]", "", msg_plain)
        await send_message(chat_id, f"✅ {target_phone}: {msg_plain}")
        # notify user
        target_chat = f"{target_phone}@c.us"
        desc = "מנוי חודשי" if amount == -1 else ("גישה חופשית" if amount == -2 else f"{amount} בדיקות")
        await send_message(target_chat, f"🎉 נוספו לך {desc}! תוכל לחפש רכבים עכשיו.")
        return True

    # approve <phone> <amount>  — אישור תשלום
    if parts[0].lower() == "approve" and len(parts) >= 3:
        target_phone = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            await send_message(chat_id, "❌ שימוש: approve 972501234567 50")
            return True
        target_id = _phone_to_id(target_phone)
        await _ensure_wa_user(target_phone)
        msg = await admin_grant(target_id, target_id, amount, "payment approved via WA admin")
        msg_plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", msg)
        msg_plain = re.sub(r"[*_`]", "", msg_plain)
        await send_message(chat_id, f"✅ אושר! {target_phone}: {msg_plain}")
        target_chat = f"{target_phone}@c.us"
        desc = "מנוי חודשי ללא הגבלה" if amount == -1 else f"{amount} בדיקות"
        await send_message(target_chat, f"✅ התשלום אושר! נוספו לך {desc}. תוכל לחפש מיד.")
        return True

    # block <phone>
    if parts[0].lower() == "block" and len(parts) >= 2:
        target_phone = parts[1]
        target_id = _phone_to_id(target_phone)
        await block_user(target_id)
        await send_message(chat_id, f"🚫 {target_phone} נחסם")
        target_chat = f"{target_phone}@c.us"
        await send_message(target_chat, "🚫 הגישה שלך חסומה. לפרטים פנה למנהל.")
        return True

    # unblock <phone>
    if parts[0].lower() in ("unblock", "שחרר") and len(parts) >= 2:
        target_phone = parts[1]
        target_id = _phone_to_id(target_phone)
        await unblock_user(target_id)
        await send_message(chat_id, f"✅ {target_phone} שוחרר")
        target_chat = f"{target_phone}@c.us"
        await send_message(target_chat, "✅ החסימה הוסרה. תוכל להמשיך להשתמש בבוט.")
        return True

    return False


# ── Message dispatcher ──────────────────────────────────────────────────────

def _normalize_phone(raw: str) -> str:
    """972501234567@c.us  →  972501234567"""
    return raw.split("@")[0]


def _normalize_plate(text: str) -> str:
    return text.strip().replace("-", "").replace(" ", "")


async def handle_message(chat_id: str, phone: str, body: str) -> None:
    text  = body.strip()
    lower = text.lower()

    # Admin commands (checked before anything else)
    if await handle_admin(chat_id, phone, text):
        return

    # Ensure user row exists
    user_id = await _ensure_wa_user(phone)

    # Blocked?
    if await is_blocked(user_id):
        await send_message(chat_id, menu.BLOCKED)
        return

    state = await get_wa_state(phone)
    logger.info("handle_message: phone=%s state=%s text=%s", phone, state, text[:30])

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
            await send_message(
                chat_id,
                f"❌ *הקוד שגוי או לא תקין*\n"
                f"─────────────────\n"
                f"{msg_plain}\n\n"
                f"נסה שוב — שלח את הקוד\n"
                f"⬅️ לביטול: שלח *תפריט*"
            )
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
            parts_s  = state.split("|")
            searches = parts_s[1] if len(parts_s) > 1 else "?"
            price    = parts_s[2] if len(parts_s) > 2 else "?"
            label    = parts_s[3] if len(parts_s) > 3 else "?"
            await set_wa_state(phone, None)

            # Save pending payment and generate short ref code
            import secrets as _sec
            from src.db import execute as _exec
            ref = _sec.token_hex(2).upper()  # e.g. "A1B2"
            await _exec(
                "INSERT OR REPLACE INTO pending_payments (ref, phone, searches, price, label) VALUES (?,?,?,?,?)",
                [ref, phone, int(searches) if str(searches).lstrip("-").isdigit() else -1, int(price) if str(price).isdigit() else 0, label],
            )

            # Notify Telegram admin
            await notify_telegram_admin(
                f"💰 בקשת תשלום ווטסאפ!\n\n"
                f"📱 טלפון: {phone}\n"
                f"📦 {label} — ₪{price}\n"
                f"🔑 קוד: {ref}\n\n"
                f"לאישור מהיר בוואטסאפ:\n"
                f"אשר {ref}"
            )
            # Notify WA admin with one-tap approve
            if ADMIN_WA_PHONE:
                admin_chat = f"{ADMIN_WA_PHONE}@c.us"
                await send_message(admin_chat,
                    f"💰 *בקשת תשלום חדשה!*\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"📱 {phone}\n"
                    f"📦 {label} — ₪{price}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"לאישור — שלח:\n"
                    f"*אשר {ref}*\n\n"
                    f"לדחייה — שלח:\n"
                    f"*דחה {ref}*"
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

    # ── Link code: "קשר XXXXXX" ──────────────────────────────────────────────
    if lower.startswith("קשר ") or lower.startswith("link "):
        parts = text.strip().split()
        code  = parts[1].upper() if len(parts) > 1 else ""
        if not code:
            await send_message(chat_id, "שלח: קשר XXXXXX (הקוד שקיבלת בטלגרם)")
            return
        success, result = await consume_link_code(code, phone)
        if success:
            await send_message(
                chat_id,
                "✅ *החשבונות קושרו בהצלחה!*\n"
                "─────────────────\n"
                "המכסה והחבילה שלך מטלגרם עכשיו פעילות כאן.\n\n"
                "🔍 שלח מספר רכב לחיפוש"
            )
            # Notify Telegram user
            await notify_telegram_admin_or_user(int(result),
                "💚 *ווטסאפ קושר בהצלחה\\!*\n\n"
                "החשבון שלך מחובר עכשיו גם לווטסאפ\\.\n"
                "כל הבדיקות והחבילות משותפות בין הערוצים\\."
            )
        else:
            await send_message(chat_id, f"❌ {result}\n\nלקוד חדש — לחץ 'חבר לוואטסאפ' בטלגרם")
        return

    # ── Stateless commands ───────────────────────────────────────────────────

    if lower in ("תפריט", "menu", "hi", "hello", "שלום", "הי", "start"):
        await send_message(chat_id, menu.WELCOME)
        return

    if text == "1":
        allowed, left = await is_allowed(user_id)
        expires = await get_quota_expires(user_id) if left == -1 else None
        await send_message(chat_id, menu.format_status_full(left, expires))
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

    if text == "5" or lower in ("היסטוריה", "history"):
        history = await get_search_history(user_id, limit=10)
        if not history:
            await send_message(chat_id, menu.NO_HISTORY)
        else:
            lines = ["📜 *היסטוריית החיפושים שלך:*\n─────────────────"]
            for i, plate in enumerate(history, 1):
                lines.append(f"{i}. 🚗 {plate}")
            lines.append("\n─────────────────")
            lines.append("לחיפוש חוזר — שלח את מספר הרכב")
            await send_message(chat_id, "\n".join(lines))
        return

    if text == "6" or lower == "pdf":
        last_plate = await get_last_plate(user_id)
        if not last_plate:
            await send_message(chat_id, "❌ לא נמצא חיפוש אחרון.\n\nשלח מספר רכב תחילה.")
            return
        record = cache.get(last_plate)
        if record is None:
            await send_message(chat_id, menu.SEARCHING)
            try:
                record = await fetch_vehicle_data(last_plate)
            except Exception as exc:
                logger.error("WA PDF fetch error plate=%s: %s", last_plate, exc)
                await send_message(chat_id, menu.ERROR)
                return
            if record is None:
                await send_message(chat_id, menu.NOT_FOUND.format(plate=last_plate))
                return
            cache.set(last_plate, record)
        try:
            from src.pdf_report import generate_pdf
            pdf_bytes = generate_pdf(
                record,
                tg_link=f"t.me/{TG_BOT_USERNAME}",
                wa_link=f"wa.me/{WA_BOT_PHONE}",
                logo_path=os.environ.get("LOGO_PATH", ""),
                cover_path=os.environ.get("COVER_PATH", ""),
            )
        except Exception as exc:
            logger.error("WA PDF generation failed plate=%s: %s", last_plate, exc)
            await send_message(chat_id, "❌ שגיאה ביצירת הדוח.")
            return
        await send_wa_pdf(chat_id, pdf_bytes, f"car_{last_plate}.pdf", f"📄 דוח רכב {last_plate}")
        return

    # ── Plate search ─────────────────────────────────────────────────────────
    plate = _normalize_plate(text)
    if PLATE_RE.match(plate) and len(plate) >= 5:
        allowed, left = await is_allowed(user_id)
        if not allowed:
            await send_message(chat_id, menu.EXPIRY_WARNING)
            return

        # Check repeat search (no deduction)
        last       = await get_last_plate(user_id)
        is_repeat  = (last == plate)

        if not is_repeat and left == 1:
            await send_message(chat_id, menu.LAST_FREE)

        # cache hit — no API call needed
        record = cache.get(plate)
        if record is None:
            await send_message(chat_id, menu.SEARCHING)
            try:
                record = await fetch_vehicle_data(plate)
            except Exception as exc:
                logger.error("WA fetch error plate=%s: %s", plate, exc)
                await send_message(chat_id, menu.ERROR)
                return
            if record is not None:
                cache.set(plate, record)

        if record is None:
            await send_message(chat_id, menu.NOT_FOUND.format(plate=plate))
            return

        if not is_repeat:
            await increment_search(user_id, plate)
            await set_last_plate(user_id, plate)

        expires   = await get_quota_expires(user_id) if left == -1 else None
        new_left  = left if (left == -1 or is_repeat) else max(0, left - 1)
        yad2_link = await _yad2.build_url(record)
        result_text = menu.format_result(record, new_left, expires, plate=plate, yad2_link=yad2_link)
        await send_message(chat_id, result_text)
        return

    # ── Fallback ──────────────────────────────────────────────────────────────
    await send_message(
        chat_id,
        "לא הבנתי 🤔\n\n"
        "שלח מספר רכב לחיפוש\n"
        "או שלח *תפריט* לאפשרויות.",
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

        logger.debug("POST /webhook from %s | body: %s", self.client_address, raw[:200])

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


# ── Renewal reminder background thread ──────────────────────────────────────

def _run_renewal_reminders():
    """Check daily for subscriptions expiring tomorrow and send WA reminder."""
    import time
    from datetime import datetime as _dt, timedelta
    while True:
        try:
            asyncio.run(_send_renewal_reminders())
        except Exception as exc:
            logger.warning("renewal reminder error: %s", exc)
        time.sleep(86400)  # run once per day


async def _send_renewal_reminders():
    from src.db import execute as _exec
    from datetime import datetime as _dt, timedelta
    tomorrow = (_dt.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    r = await _exec(
        "SELECT user_id, whatsapp_phone FROM users "
        "WHERE searches_quota = -1 AND quota_expires IS NOT NULL "
        "AND quota_expires LIKE ? AND whatsapp_phone IS NOT NULL",
        [f"{tomorrow}%"],
    )
    from src.db import _Result
    cols  = [c.name for c in r.columns]
    rows  = [dict(zip(cols, row)) for row in r.rows]
    for u in rows:
        wa_phone = u.get("whatsapp_phone")
        if not wa_phone:
            continue
        chat_id = f"{wa_phone}@c.us"
        await send_message(
            chat_id,
            "⏰ *תזכורת — המנוי שלך פג מחר!*\n"
            "─────────────────\n"
            "כדי להמשיך לחפש רכבים ללא הגבלה:\n\n"
            "2️⃣  שלח *2* לחידוש מנוי"
        )
        logger.info("Renewal reminder sent to %s", wa_phone)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    if not ID_INSTANCE or not TOKEN_INSTANCE:
        raise RuntimeError(
            "GREEN_API_ID_INSTANCE and GREEN_API_TOKEN_INSTANCE must be set"
        )

    asyncio.run(init_db())
    logger.info("Turso DB initialized (WA bot)")

    from threading import Thread
    Thread(target=_run_renewal_reminders, daemon=True).start()
    logger.info("Renewal reminder thread started")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    logger.info("WhatsApp webhook server listening on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
