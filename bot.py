"""
CarInfo Bot – Israel vehicle lookup Telegram bot.
"""

import asyncio
import logging
import os
import re
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, LabeledPrice
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    PreCheckoutQueryHandler,
    ContextTypes, filters,
)

from src.api.gov_api import fetch_vehicle_data
from src.cache import cache
from src.db import init_db
from src.users import (
    is_allowed, increment_search, apply_code, generate_code,
    admin_stats, admin_grant, get_all_users, get_user_by_username, get_user_by_id,
    block_user, unblock_user, is_blocked,
    get_last_plate, set_last_plate,
)
from src.formatter import (
    format_error,
    format_not_found,
    get_summary,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PLATE_RE  = re.compile(r"^[\d\-]{5,10}$")
ADMIN_ID  = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))
BOT_USERNAME = "israelcarinfobot"
PAYMENT_PROVIDER_TOKEN = os.environ.get("PAYMENT_PROVIDER_TOKEN", "6073714100:TEST:TG_2ZwhGNC5yAq7J6bMbZfUti0A")
PAYPAL_ME = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")

# Payment packages: (label, searches, price_ILS)
# searches=-1 means monthly unlimited
PAYMENT_PACKAGES = [
    ("🔍 50 חיפושים",   50,  10),
    ("🔍 100 חיפושים", 100,  20),
    ("🔍 200 חיפושים", 200,  30),
    ("♾️ מנוי חודשי",   -1,  25),
]

_MD_SPECIAL = r"\_*[]()~`>#+-=|{}.!"
def _escape_md(text: str) -> str:
    return "".join(f"\\{c}" if c in _MD_SPECIAL else c for c in str(text))

logger.info("ADMIN_ID loaded: %s", ADMIN_ID)

PAYMENT_MSG = (
    "🔒 *נגמרו הבדיקות החינמיות שלך*\n\n"
    "לרכישת בדיקות נוספות לחץ על הכפתור למטה\\.\n"
    "נחזור אליך בהקדם\\!"
)

WAITING_CODE = 1
WAITING_FREE_COUNT = 2
WAITING_PAYMENT_MSG = 3

def _persistent_rows(is_admin: bool = False) -> list:
    """Bottom rows always shown on every screen."""
    rows = [
        [InlineKeyboardButton("🔍 חיפוש רכב חדש",        callback_data="new_search"),
         InlineKeyboardButton("ℹ️ איך זה עובד?",          callback_data="how_it_works")],
        [InlineKeyboardButton("🛒 רכישת חבילת חיפושים",  callback_data="show_packages")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("🛠 פאנל מנהל", callback_data="admin_panel")])
    return rows


def _persistent_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_persistent_rows(is_admin))


def _payment_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for label, searches, price in PAYMENT_PACKAGES:
        buttons.append([InlineKeyboardButton(
            f"{label} — {searches} בדיקות ב-₪{price}",
            callback_data=f"buy|{searches}|{price}"
        )])
    buttons.append([InlineKeyboardButton("🔑 יש לי קוד גישה", callback_data="enter_code")])
    return InlineKeyboardMarkup(buttons)


def _welcome_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return _persistent_keyboard(is_admin)


def _blocked_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 צ'אט עם מנהל", callback_data="chat_admin")],
    ])


def _admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 סטטיסטיקות"), KeyboardButton("👥 משתמשים")],
        [KeyboardButton("🔑 צור קוד"),    KeyboardButton("💳 הענק גישה")],
        [KeyboardButton("🚫 חסום/שחרר"),  KeyboardButton("⚙️ הגדרות בוט")],
        [KeyboardButton("📢 שלח הודעה לכולם")],
        [KeyboardButton("🔍 חזור לחיפוש")],
    ], resize_keyboard=True, one_time_keyboard=False)


def _cancel_search_keyboard() -> ReplyKeyboardMarkup:
    """Minimal keyboard shown while waiting for plate — just a cancel button."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ ביטול")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def normalize_plate(text: str) -> str:
    return text.strip().replace("-", "").replace(" ", "")


def build_result_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return _persistent_keyboard(is_admin)


def _packages_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for label, searches, price in PAYMENT_PACKAGES:
        desc = "ללא הגבלה — 30 יום" if searches == -1 else f"{searches} בדיקות"
        buttons.append([InlineKeyboardButton(
            f"{label} — {desc} ב-₪{price}",
            callback_data=f"buy|{searches}|{price}"
        )])
    buttons.append([InlineKeyboardButton("🎟️ יש לי קוד הטבה", callback_data="enter_code")])
    return InlineKeyboardMarkup(buttons)


def _paypal_keyboard(searches: int, price: int) -> InlineKeyboardMarkup:
    paypal_url = f"{PAYPAL_ME}/{price}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 שלם ₪{price} ב-PayPal", url=paypal_url)],
        [InlineKeyboardButton("✅ שילמתי — שלח אישור", callback_data=f"paid|{searches}|{price}")],
        [InlineKeyboardButton("🔙 חזרה לחבילות", callback_data="show_packages")],
    ])


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    is_admin = uid == ADMIN_ID
    await update.message.reply_text(
        f"🆔 Your ID: `{uid}`\n👑 Admin: `{is_admin}`\n⚙️ ADMIN\\_ID set to: `{ADMIN_ID}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user    = update.effective_user
    args    = context.args

    if args and args[0] == "admin_chat":
        uname    = f"@{user.username}" if user.username else f"id:{user_id}"
        fullname = user.full_name or ""
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"💬 *פנייה חדשה למנהל\\!*\n\n"
                    f"👤 משתמש: {uname}\n"
                    f"📛 שם: {fullname}\n"
                    f"🆔 ID: `{user_id}`",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            except Exception as e:
                logger.warning("Failed to notify admin: %s", e)
        sent = await update.message.reply_text(
            "💬 *הודעתך נשלחה למנהל\\!*\n\n"
            "ניצור איתך קשר בהקדם\\.\n\n"
            "_כדי להמשיך את השיחה — השב \\(Reply\\) להודעה זו_\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.bot_data.setdefault("admin_chat_msg_ids", set()).add(sent.message_id)
        return

    if args and args[0] == "buy":
        uname    = f"@{user.username}" if user.username else f"id:{user_id}"
        fullname = user.full_name or ""
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"💰 *בקשת רכישה חדשה\\!*\n\n"
                    f"👤 משתמש: {uname}\n"
                    f"📛 שם: {fullname}\n"
                    f"🆔 ID: `{user_id}`\n\n"
                    f"לפתיחת גישה:\n`/admin grant {uname} 50`",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            except Exception as e:
                logger.warning("Failed to notify admin: %s", e)
        await update.message.reply_text(
            "✅ *קיבלנו את בקשתך\\!*\n\n"
            "ניצור איתך קשר בהקדם לאחר אישור התשלום\\.\n\n"
            "📝 ציין בהודעה: *CarInfo*",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if user_id == ADMIN_ID:
        stats = await admin_stats()
        await update.message.reply_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_reply_keyboard(),
        )
        return

    allowed, left = await is_allowed(user_id, user.username or "", user.full_name or "")

    if not allowed:
        if await is_blocked(user_id):
            await update.message.reply_text(
                "🚫 *הגישה שלך לבוט חסומה\\.*\n\nלפרטים או לערעור פנה למנהל דרך הכפתור למטה\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_blocked_keyboard(),
            )
        else:
            await update.message.reply_text(
                PAYMENT_MSG,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_payment_keyboard(),
            )
        return

    if left == -1:
        from src.users import get_quota_expires
        expires = await get_quota_expires(user_id)
        if expires:
            try:
                from datetime import datetime as _dt
                exp_str = _dt.fromisoformat(expires[:10]).strftime("%d/%m/%Y")
            except Exception:
                exp_str = expires[:10]
            searches_info = f"♾️ מנוי חודשי פעיל עד {exp_str}"
        else:
            searches_info = "✅ גישה בלתי מוגבלת"
    elif left > 0:
        searches_info = f"נותרו לך *{left}* בדיקות\\."
    else:
        searches_info = "גישה מלאה פעילה ✅"

    await update.message.reply_text(
        "👋 *ברוך הבא ל\\-CarInfo\\!*\n\n"
        "🔍 שלח מספר לוחית רישוי \\(לדוגמה: 1234567\\)\n"
        "ותקבל דוח מלא על הרכב תוך שניות\\.\n\n"
        f"🆓 {searches_info}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_welcome_keyboard(False),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *שימוש בבוט*\n\n"
        "שלח מספר רכב → קבל סיכום \\+ תפריט קטגוריות\\.\n\n"
        "*קטגוריות:*\n"
        "📋 פרטים כלליים · ⚙️ מפרט טכני\n"
        "🔧 גלגלים · 🛋️ ציוד\n"
        "🛡️ בטיחות · 🤖 ADAS\n"
        "📅 היסטוריה · 👥 בעלויות · 🔔 ריקולים\n\n"
        "*פקודות:*\n"
        "`/code XXXXXXXX` \\– הזן קוד גישה\n"
        "`/status` \\– בדוק את מצב חשבונך",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    allowed, left = await is_allowed(user_id)
    if left == -1:
        msg = "✅ גישה מלאה פעילה"
    elif left > 0:
        msg = f"🆓 נותרו לך *{left}* בדיקות חינמיות"
    else:
        msg = "🔒 הבדיקות החינמיות שלך נוצלו\n\nשלח `/help` לפרטי רכישה"
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text(
            "הזן קוד גישה: `/code XXXXXXXX`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    code = args[0].strip().upper()
    success, msg = await apply_code(user_id, code)
    await update.message.reply_text(
        f"{'✅' if success else '❌'} {msg}",
        parse_mode=ParseMode.MARKDOWN_V2 if not success else None,
    )


async def cb_enter_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()
    await query.edit_message_text(
        "🎟️ *הזן קוד הטבה*\n\n"
        "שלח את הקוד שקיבלת \\(לא תלוי רישיות\\):",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 חזרה", callback_data="show_packages")],
        ]),
    )
    context.user_data["code_is_admin"] = is_admin
    return WAITING_CODE


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    is_admin = context.user_data.pop("code_is_admin", user_id == ADMIN_ID)
    code     = update.message.text.strip().upper()
    success, msg = await apply_code(user_id, code)
    if success:
        await update.message.reply_text(
            f"✅ *{_escape_md(msg)}*\n\nתוכל להתחיל לחפש רכבים עכשיו\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persistent_keyboard(is_admin),
        )
    else:
        await update.message.reply_text(
            f"❌ *קוד לא תקין*\n\n{_escape_md(msg)}\n\nנסה שוב או חזור לתפריט החבילות\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 חזרה לחבילות", callback_data="show_packages")],
                *_persistent_rows(is_admin),
            ]),
        )
    return ConversationHandler.END


async def cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=_admin_reply_keyboard())
    else:
        await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=False))
    return ConversationHandler.END


def _admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 סטטיסטיקות",       callback_data="adm|stats")],
        [InlineKeyboardButton("👥 משתמשים",           callback_data="adm|users"),
         InlineKeyboardButton("🔑 צור קוד",           callback_data="adm|gen_menu")],
        [InlineKeyboardButton("💳 הענק גישה",         callback_data="adm|grant_info"),
         InlineKeyboardButton("🚫 חסום/שחרר",         callback_data="adm|block_menu")],
        [InlineKeyboardButton("⚙️ הגדרות בוט",        callback_data="adm|settings")],
    ])


def _admin_gen_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 בדיקות",  callback_data="adm|gen|10|single"),
         InlineKeyboardButton("25 בדיקות",  callback_data="adm|gen|25|single")],
        [InlineKeyboardButton("50 בדיקות",  callback_data="adm|gen|50|single"),
         InlineKeyboardButton("100 בדיקות", callback_data="adm|gen|100|single")],
        [InlineKeyboardButton("📅 חודש – חיפושים חופשיים", callback_data="adm|gen|monthly|single")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")],
    ])


def _admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ שנה הודעת תשלום",         callback_data="adm|set_payment")],
        [InlineKeyboardButton("🆓 שנה מספר בדיקות חינמיות", callback_data="adm|set_free")],
        [InlineKeyboardButton("🔙 חזרה",                     callback_data="adm|main")],
    ])


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        return

    args = context.args

    if args:
        if args[0] == "grant" and len(args) >= 3:
            username = args[1].lstrip("@")
            try:
                amount = int(args[2])
            except ValueError:
                await update.message.reply_text("כמות חייבת להיות מספר", parse_mode=ParseMode.MARKDOWN_V2)
                return
            target = await get_user_by_username(username)
            if not target and username.isdigit():
                target = await get_user_by_id(int(username))
            if not target:
                await update.message.reply_text(
                    f"משתמש לא נמצא\\. נסה עם ה\\-ID המספרי במקום ה\\-username\\.",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return
            note = " ".join(args[3:]) if len(args) > 3 else ""
            msg = await admin_grant(user_id, target["user_id"], amount, note)
            await update.message.reply_text(f"✅ {username}: {msg}")
            # Notify user
            try:
                if amount == -2:
                    user_msg = "🎖️ קיבלת גישה חופשית ללא הגבלת זמן! תוכל לחפש רכבים ללא הגבלה."
                elif amount == -1:
                    user_msg = f"🎉 המנוי החודשי שלך אושר!\n\n{msg}\n\nתוכל לחפש רכבים ללא הגבלה!"
                else:
                    user_msg = f"🎉 נוספו לך {amount} בדיקות רכב!\n\nתוכל להתחיל לחפש מיד."
                await context.bot.send_message(target["user_id"], user_msg)
            except Exception as e:
                logger.warning("Failed to notify user after grant: %s", e)
            return

        if args[0] == "gen":
            single = "multi" not in args
            if len(args) > 1 and args[1] == "monthly":
                code = await generate_code(monthly=True, single_use=single)
                kind = "חודש חיפושים חופשיים"
            else:
                try:
                    count = int(args[1]) if len(args) > 1 else 10
                except ValueError:
                    count = 10
                unlimited = count == -1
                code = await generate_code(searches=count, single_use=single, unlimited=unlimited)
                kind = f"{count} בדיקות"
            use_str = "חד פעמי" if single else "רב פעמי"
            await update.message.reply_text(
                f"✅ קוד חדש \\({_escape_md(kind)}, {use_str}\\):\n`{code}`",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

    stats = await admin_stats()
    await update.message.reply_text(
        f"🛠 *פאנל ניהול CarInfo*\n\n"
        f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
        f"🔍 בדיקות: *{stats['total_searches']}*\n"
        f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_admin_reply_keyboard(),
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    user_id = query.from_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await query.answer("אין הרשאה", show_alert=True)
        return
    await query.answer()

    parts  = query.data.split("|")
    action = parts[1] if len(parts) > 1 else ""

    if action == "main":
        stats = await admin_stats()
        await query.edit_message_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_main_keyboard(),
        )
        return

    if action == "stats":
        stats = await admin_stats()
        await query.edit_message_text(
            f"📊 *סטטיסטיקות מפורטות*\n\n"
            f"• סה\"כ משתמשים: *{stats['total_users']}*\n"
            f"• פעילים \\(יש להם מכסה\\): *{stats['active_users']}*\n"
            f"• סה\"כ בדיקות שבוצעו: *{stats['total_searches']}*\n"
            f"• קודים שנוצרו: *{stats['total_codes']}*\n"
            f"• קודים שנוצלו: *{stats['used_codes']}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    if action == "users":
        users = await get_all_users()
        if not users:
            await query.edit_message_text(
                "אין משתמשים עדיין\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
            )
            return
        lines = ["👥 *משתמשים* \\(מסודר לפי בדיקות\\)\n"]
        for u in users[:25]:
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{u['user_id']}"
            done     = u.get("searches_done", 0)
            quota    = u.get("searches_quota", 0)
            left     = u.get("searches_left", 0)
            quota_str = "∞" if quota == -1 else str(quota)
            left_str  = "∞" if left  == -1 else str(left)
            from src.formatter import _escape
            lines.append(f"• {_escape(display)}: {done}/{quota_str} \\(נותרו: {left_str}\\)\n")
        await query.edit_message_text(
            "".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    if action == "gen_menu":
        await query.edit_message_text(
            "🔑 *יצירת קוד גישה*\n\nבחר כמות בדיקות לקוד:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_gen_keyboard(),
        )
        return

    if action == "gen":
        count_str = parts[2] if len(parts) > 2 else "10"
        use_type  = parts[3] if len(parts) > 3 else "single"
        single    = use_type == "single"
        is_monthly = count_str == "monthly"

        if is_monthly:
            code = await generate_code(monthly=True, single_use=single)
            kind = "📅 חודש – חיפושים חופשיים"
        else:
            count     = int(count_str)
            unlimited = count == -1
            code = await generate_code(searches=count, single_use=single, unlimited=unlimited)
            kind = f"{count} בדיקות"

        use_str = "חד פעמי" if single else "רב פעמי"
        await query.edit_message_text(
            f"✅ *קוד חדש נוצר*\n\n"
            f"סוג: {_escape_md(kind)} \\| {use_str}\n\n"
            f"`{code}`\n\n"
            f"_העתק את הקוד ושלח ללקוח_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 צור קוד נוסף", callback_data="adm|gen_menu")],
                [InlineKeyboardButton("🔙 ראשי",          callback_data="adm|main")],
            ]),
        )
        return

    if action == "grant_info":
        await query.edit_message_text(
            "💳 *הענקת גישה למשתמש*\n\n"
            "שלח פקודה בפורמט:\n"
            "`/admin grant @username 50`\n\n"
            "לגישה בלתי מוגבלת:\n"
            "`/admin grant @username \\-1`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    if action == "settings":
        import src.users as _u
        free = _u.FREE_SEARCHES
        await query.edit_message_text(
            f"⚙️ *הגדרות בוט*\n\n"
            f"• בדיקות חינמיות למשתמש חדש: *{free}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_settings_keyboard(),
        )
        return

    if action == "set_payment":
        await query.message.reply_text(
            "✏️ *שינוי הודעת תשלום*\n\nשלח את הטקסט החדש \\(פשוט, ללא Markdown\\):",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.user_data["admin_setting"] = "payment_msg"
        return

    if action == "set_free":
        import src.users as _u
        await query.message.reply_text(
            f"🆓 *שינוי בדיקות חינמיות*\n\nהערך הנוכחי: *{_u.FREE_SEARCHES}*\n\nשלח את המספר החדש:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.user_data["admin_setting"] = "free_count"
        return

    if action == "block_menu":
        users = await get_all_users()
        if not users:
            await query.edit_message_text(
                "אין משתמשים עדיין\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
            )
            return
        buttons = []
        for u in users[:20]:
            uid      = u["user_id"]
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
            blocked  = bool(u.get("blocked"))
            label    = f"{'🔴 ' if blocked else ''}{display}"
            action_cb = f"adm|unblock|{uid}" if blocked else f"adm|block|{uid}"
            buttons.append([InlineKeyboardButton(label, callback_data=action_cb)])
        buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")])
        await query.edit_message_text(
            "🚫 *חסימת משתמשים*\n\n🔴 \\= חסום כעת\nלחץ על משתמש לחסום / שחרר:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action == "block":
        target_id = int(parts[2])
        await block_user(target_id)
        try:
            await context.bot.send_message(
                target_id,
                "🚫 הגישה שלך לבוט נחסמה\\. לפרטים פנה למנהל\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:
            pass
        users = await get_all_users()
        buttons = []
        for u in users[:20]:
            uid      = u["user_id"]
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
            bl       = bool(u.get("blocked"))
            label    = f"{'🔴 ' if bl else ''}{display}"
            cb       = f"adm|unblock|{uid}" if bl else f"adm|block|{uid}"
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")])
        await query.edit_message_text(
            "🚫 *חסימת משתמשים*\n\n🔴 \\= חסום כעת\nלחץ על משתמש לחסום / שחרר:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action == "unblock":
        target_id = int(parts[2])
        await unblock_user(target_id)
        try:
            await context.bot.send_message(
                target_id,
                "✅ החסימה שלך הוסרה\\. תוכל להמשיך להשתמש בבוט\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:
            pass
        users = await get_all_users()
        buttons = []
        for u in users[:20]:
            uid      = u["user_id"]
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
            bl       = bool(u.get("blocked"))
            label    = f"{'🔴 ' if bl else ''}{display}"
            cb       = f"adm|unblock|{uid}" if bl else f"adm|block|{uid}"
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")])
        await query.edit_message_text(
            "🚫 *חסימת משתמשים*\n\n🔴 \\= חסום כעת\nלחץ על משתמש לחסום / שחרר:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return


async def handle_back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()
    await query.edit_message_text(
        "👋 *ברוך הבא ל\\-CarInfo\\!*\n\n"
        "🔍 שלח מספר לוחית רישוי \\(לדוגמה: 1234567\\)\n"
        "ותקבל דוח מלא על הרכב תוך שניות\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_welcome_keyboard(is_admin),
    )


async def handle_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()
    await query.edit_message_text(
        "ℹ️ *איך CarInfo עובד?*\n\n"
        "🔍 *מה המערכת מציגה לך על כל רכב:*\n"
        "• פרטים כלליים – יצרן, דגם, שנה, צבע, מסגרת\n"
        "• מפרט טכני – מנוע, הנעה, הילוכים, דלק, כוח סוס\n"
        "• גלגלים וצמיגים\n"
        "• ציוד ונוחות – מיזוג, הגה כוח, חלונות חשמל\n"
        "• בטיחות ופליטות – ABS, ESP, כריות אוויר, CO2\n"
        "• מערכות ADAS – בלימה אוטומטית, שמירת נתיב ועוד\n"
        "• היסטוריה – רישום, טסט, ק\"מ, שינויי מבנה\n"
        "• היסטוריית בעלויות – כמה בעלים, פרטי/סוחר\n"
        "• ריקולים – תקלות ידועות של הדגם\n\n"
        "🆓 *חיפושים חינמיים:*\n"
        "כל משתמש חדש מקבל *20 חיפושים חינמיים* לניסיון\n\n"
        "📦 *חבילות חיפוש:*\n"
        "• 50 חיפושים – ₪10\n"
        "• 100 חיפושים – ₪20\n"
        "• 200 חיפושים – ₪30\n"
        "• ♾️ מנוי חודשי \\(ללא הגבלה\\) – ₪25\n\n"
        "💡 *איך משתמשים?*\n"
        "פשוט שלח מספר לוחית רישוי \\(לדוגמה: 1234567\\)\n"
        "והמערכת תחזיר לך דוח מלא תוך שניות\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_persistent_keyboard(is_admin),
    )


async def handle_package_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    user_id  = query.from_user.id
    user     = query.from_user
    is_admin = user_id == ADMIN_ID
    await query.answer()

    data = query.data
    if data == "show_packages":
        await query.edit_message_text(
            "🛒 *בחר חבילת חיפושים:*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_packages_keyboard(is_admin),
        )
        return

    # buy| handled by handle_buy_callback

async def handle_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin clicked on a user — show options."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    parts = query.data.split("|")


    # ugrant|UID|AMOUNT    # usr|UID — show user options
    if parts[0] == "usr" and len(parts) == 2 and parts[1] != "back":
        uid = int(parts[1])
        users = await get_all_users()
        u = next((x for x in users if x["user_id"] == uid), None)
        if not u:
            await query.edit_message_text("משתמש לא נמצא.")
            return
        uname    = f"@{u['username']}" if u.get("username") else ""
        fullname = u.get("full_name", "")
        display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
        quota    = u.get("searches_quota", 0)
        done     = u.get("searches_done", 0)
        left     = u.get("searches_left", 0)
        blocked  = u.get("blocked", False)
        expires  = u.get("quota_expires", "")
        quota_str = "ללא הגבלה" if quota == -1 else str(quota)
        left_str  = "ללא הגבלה" if left  == -1 else str(left)
        exp_str   = f" (עד {expires[:10]})" if expires else ""

        info = (
            f"👤 {display}\n"
            f"🆔 {uid}\n"
            f"📊 בדיקות: {done}/{quota_str}{exp_str}\n"
            f"📌 נותרו: {left_str}\n"
            f"{'🔴 חסום' if blocked else '🟢 פעיל'}"
        )
        buttons = [
            [InlineKeyboardButton("➕ 50 בדיקות",  callback_data=f"ugrant|{uid}|50"),
             InlineKeyboardButton("➕ 100 בדיקות", callback_data=f"ugrant|{uid}|100")],
            [InlineKeyboardButton("➕ 200 בדיקות", callback_data=f"ugrant|{uid}|200"),
             InlineKeyboardButton("♾️ מנוי חודשי", callback_data=f"ugrant|{uid}|-1")],
            [InlineKeyboardButton("🎖️ גישה חופשית", callback_data=f"ugrant|{uid}|-2")],
            [InlineKeyboardButton("🚫 חסום" if not blocked else "✅ שחרר", callback_data=f"utoggle|{uid}")],
            [InlineKeyboardButton("🔙 חזור למשתמשים", callback_data="usr|back")],
        ]
        await query.edit_message_text(info, reply_markup=InlineKeyboardMarkup(buttons))
        return


    # ugrant|UID|AMOUNT    # ugrant|UID|AMOUNT — grant searches
    if parts[0] == "ugrant":
        uid     = int(parts[1])
        amount  = int(parts[2])
        msg     = await admin_grant(ADMIN_ID, uid, amount, "granted via admin panel")
        desc    = "גישה חופשית" if amount == -2 else ("מנוי חודשי" if amount == -1 else f"{amount} בדיקות")
        await query.answer(f"✅ הוענקו {desc}", show_alert=True)
        # Notify user
        try:
            user_msg = (
                "🎖️ קיבלת גישה חופשית ללא הגבלת זמן! תוכל לחפש רכבים ללא הגבלה."
                if amount == -2 else
                f"🎉 המנוי החודשי שלך אושר!\n{msg}\n\nתוכל לחפש ללא הגבלה!"
                if amount == -1 else
                f"🎉 נוספו לך {amount} בדיקות רכב!"
            )
            await context.bot.send_message(uid, user_msg)
        except Exception:
            pass
        # Refresh user view
        users = await get_all_users()
        u = next((x for x in users if x["user_id"] == uid), None)
        if not u:
            await query.edit_message_text("✅ עודכן.")
            return
        uname    = f"@{u['username']}" if u.get("username") else ""
        fullname = u.get("full_name", "")
        display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
        quota    = u.get("searches_quota", 0)
        done     = u.get("searches_done", 0)
        left     = u.get("searches_left", 0)
        blocked  = u.get("blocked", False)
        expires  = u.get("quota_expires", "")
        quota_str = "ללא הגבלה" if quota == -1 else str(quota)
        left_str  = "ללא הגבלה" if left  == -1 else str(left)
        exp_str   = f" (עד {expires[:10]})" if expires else ""
        info = (
            f"👤 {display}\n"
            f"🆔 {uid}\n"
            f"📊 בדיקות: {done}/{quota_str}{exp_str}\n"
            f"📌 נותרו: {left_str}\n"
            f"{'🔴 חסום' if blocked else '🟢 פעיל'}"
        )
        buttons = [
            [InlineKeyboardButton("➕ 50 בדיקות",  callback_data=f"ugrant|{uid}|50"),
             InlineKeyboardButton("➕ 100 בדיקות", callback_data=f"ugrant|{uid}|100")],
            [InlineKeyboardButton("➕ 200 בדיקות", callback_data=f"ugrant|{uid}|200"),
             InlineKeyboardButton("♾️ מנוי חודשי", callback_data=f"ugrant|{uid}|-1")],
            [InlineKeyboardButton("🎖️ גישה חופשית", callback_data=f"ugrant|{uid}|-2")],
            [InlineKeyboardButton("🚫 חסום" if not blocked else "✅ שחרר", callback_data=f"utoggle|{uid}")],
            [InlineKeyboardButton("🔙 חזור למשתמשים", callback_data="usr|back")],
        ]
        await query.edit_message_text(info, reply_markup=InlineKeyboardMarkup(buttons))
        return

    # utoggle|UID — block/unblock
    if parts[0] == "utoggle":
        uid = int(parts[1])
        users = await get_all_users()
        u = next((x for x in users if x["user_id"] == uid), None)
        currently_blocked = u.get("blocked", False) if u else False
        if currently_blocked:
            await unblock_user(uid)
            await query.answer("✅ שוחרר", show_alert=True)
            try:
                await context.bot.send_message(uid, "✅ החסימה שלך הוסרה. תוכל להמשיך להשתמש בבוט.")
            except Exception:
                pass
        else:
            await block_user(uid)
            await query.answer("🚫 נחסם", show_alert=True)
            try:
                await context.bot.send_message(uid, "🚫 הגישה שלך לבוט נחסמה. לפרטים פנה למנהל.")
            except Exception:
                pass
        # Refresh
        users = await get_all_users()
        u = next((x for x in users if x["user_id"] == uid), {})
        uname    = f"@{u.get('username', '')}" if u.get("username") else ""
        fullname = u.get("full_name", "")
        display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
        quota    = u.get("searches_quota", 0)
        done     = u.get("searches_done", 0)
        left     = u.get("searches_left", 0)
        blocked  = u.get("blocked", False)
        expires  = u.get("quota_expires", "")
        quota_str = "ללא הגבלה" if quota == -1 else str(quota)
        left_str  = "ללא הגבלה" if left  == -1 else str(left)
        exp_str   = f" (עד {expires[:10]})" if expires else ""
        info = (
            f"👤 {display}\n"
            f"🆔 {uid}\n"
            f"📊 בדיקות: {done}/{quota_str}{exp_str}\n"
            f"📌 נותרו: {left_str}\n"
            f"{'🔴 חסום' if blocked else '🟢 פעיל'}"
        )
        buttons = [
            [InlineKeyboardButton("➕ 50 בדיקות",  callback_data=f"ugrant|{uid}|50"),
             InlineKeyboardButton("➕ 100 בדיקות", callback_data=f"ugrant|{uid}|100")],
            [InlineKeyboardButton("➕ 200 בדיקות", callback_data=f"ugrant|{uid}|200"),
             InlineKeyboardButton("♾️ מנוי חודשי", callback_data=f"ugrant|{uid}|-1")],
            [InlineKeyboardButton("🎖️ גישה חופשית", callback_data=f"ugrant|{uid}|-2")],
            [InlineKeyboardButton("🚫 חסום" if not blocked else "✅ שחרר", callback_data=f"utoggle|{uid}")],
            [InlineKeyboardButton("🔙 חזור למשתמשים", callback_data="usr|back")],
        ]
        await query.edit_message_text(info, reply_markup=InlineKeyboardMarkup(buttons))
        return


async def handle_admin_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id  = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    text_msg = update.message.text.strip()

    async def send_stats():
        stats = await admin_stats()
        await update.message.reply_text(
            f"📊 *סטטיסטיקות*\n\n"
            f"• משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"• בדיקות שבוצעו: *{stats['total_searches']}*\n"
            f"• קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    async def send_users():
        users = await get_all_users()
        if not users:
            await update.message.reply_text("אין משתמשים עדיין.")
            return
        buttons = []
        for u in users[:25]:
            uid      = u["user_id"]
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
            blocked  = "🔴 " if u.get("blocked") else ""
            quota    = u.get("searches_quota", 0)
            done     = u.get("searches_done", 0)
            left     = u.get("searches_left", 0)
            quota_str = "∞" if quota == -1 else str(quota)
            left_str  = "∞" if left == -1 else str(left)
            label    = f"{blocked}{display} ({done}/{quota_str}, נותרו:{left_str})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"usr|{uid}")])
        await update.message.reply_text(
            "👥 בחר משתמש:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def send_block_list():
        users = await get_all_users()
        if not users:
            await update.message.reply_text("אין משתמשים\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return
        buttons = []
        for u in users[:20]:
            uid      = u["user_id"]
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{uid}"
            bl       = bool(u.get("blocked"))
            label    = f"{'🔴 ' if bl else ''}{display}"
            cb       = f"adm|unblock|{uid}" if bl else f"adm|block|{uid}"
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        await update.message.reply_text(
            "🚫 *חסום / שחרר משתמש*\n\n🔴 \\= חסום כעת\\:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def send_gen_menu():
        await update.message.reply_text(
            "🔑 *יצירת קוד גישה*\n\nבחר כמות:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_gen_keyboard(),
        )

    async def send_grant_info():
        await update.message.reply_text(
            "💳 *הענקת גישה*\n\nשלח:\n`/admin grant @username 50`\n\nלגישה בלתי מוגבלת:\n`/admin grant @username \\-1`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    async def send_settings():
        import src.users as _u
        await update.message.reply_text(
            f"⚙️ *הגדרות בוט*\n\n• בדיקות חינמיות למשתמש חדש: *{_u.FREE_SEARCHES}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆓 שנה בדיקות חינמיות", callback_data="adm|set_free")],
                [InlineKeyboardButton("✏️ שנה הודעת תשלום",    callback_data="adm|set_payment")],
            ]),
        )

    async def send_broadcast_prompt():
        await update.message.reply_text(
            "📢 *שליחת הודעה לכולם*\n\nשלח את ההודעה שתרצה להפיץ לכל המשתמשים:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.user_data["admin_setting"] = "broadcast"

    dispatch = {
        "📊 סטטיסטיקות":      send_stats,
        "👥 משתמשים":         send_users,
        "🔑 צור קוד":         send_gen_menu,
        "💳 הענק גישה":       send_grant_info,
        "🚫 חסום/שחרר":       send_block_list,
        "⚙️ הגדרות בוט":      send_settings,
        "📢 שלח הודעה לכולם": send_broadcast_prompt,
    }
    if text_msg == "🛠 פאנל מנהל":
        await update.message.reply_text(
            "🛠 *פאנל מנהל*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_reply_keyboard(),
        )
        return
    if text_msg == "🔍 חזור לחיפוש":
        await update.message.reply_text(
            "🔍 שלח מספר לוחית לחיפוש:",
            reply_markup=_cancel_search_keyboard(),
        )
        return
    if text_msg == "❌ ביטול":
        await update.message.reply_text(
            "בסדר, חיפוש בוטל.",
            reply_markup=_admin_reply_keyboard(),
        )
        return
    fn = dispatch.get(text_msg)
    if fn:
        await fn()


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show payment packages."""
    buttons = []
    for label, searches, price in PAYMENT_PACKAGES:
        cb = f"buy|{searches}|{price}"
        buttons.append([InlineKeyboardButton(f"{label} — {searches} בדיקות ב-₪{price}", callback_data=cb)])
    await update.message.reply_text(
        "💳 *רכישת בדיקות*\n\nבחר חבילה:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show PayPal payment link for selected package."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    searches = int(parts[1])
    price    = int(parts[2])
    label = next((l for l, s, p in PAYMENT_PACKAGES if s == searches and p == price), f"{searches} בדיקות")

    desc = "ללא הגבלה למשך 30 יום" if searches == -1 else f"{searches} בדיקות רכב"
    await query.message.reply_text(
        f"💳 *{label}*\n\n"
        f"• {desc}\n"
        f"• מחיר: *₪{price}*\n\n"
        f"1\. לחץ על כפתור התשלום למטה\n"
        f"2\. השלם את התשלום ב\-PayPal\n"
        f"3\. חזור לכאן ולחץ *שילמתי* לשליחת אישור\n\n"
        f"_הגישה תיפתח לאחר אישור ידני על ידי המנהל_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_paypal_keyboard(searches, price),
    )


async def handle_paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """User clicked 'I paid' — notify admin for manual approval."""
    query = update.callback_query
    await query.answer()
    parts    = query.data.split("|")
    searches = int(parts[1])
    price    = int(parts[2])
    user     = query.from_user
    user_id  = user.id
    uname    = f"@{user.username}" if user.username else f"id:{user_id}"
    fullname = user.full_name or ""
    label    = next((l for l, s, p in PAYMENT_PACKAGES if s == searches and p == price), f"{searches} בדיקות")

    # Notify admin with approve button
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💰 *בקשת אישור תשלום!*\n\n"
                f"👤 {uname} | {fullname}\n"
                f"🆔 {user_id}\n"
                f"📦 {label}\n"
                f"💵 {price} שח\n\n"
                f"לאחר אימות התשלום ב-PayPal לחץ אשר:",
                parse_mode=None,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ אשר ופתח גישה", callback_data=f"approve|{user_id}|{searches}"),
                    InlineKeyboardButton("❌ דחה", callback_data=f"decline|{user_id}"),
                ]]),
            )
        except Exception as e:
            logger.warning("Failed to notify admin of payment: %s", e)

    await query.edit_message_text(
        "✅ *בקשתך נשלחה למנהל\!*\n\n"
        "הגישה תיפתח לאחר אימות התשלום\. בדרך כלל תוך מספר דקות\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin approves payment — grant searches."""
    query = update.callback_query
    await query.answer()  # always answer first
    if query.from_user.id != ADMIN_ID:
        await query.answer("אין הרשאה", show_alert=True)
        return
    try:
        parts    = query.data.split("|")
        target   = int(parts[1])
        searches = int(parts[2])

        admin_grant(ADMIN_ID, target, searches, note="PayPal payment approved")

        desc = "מנוי חודשי ללא הגבלה" if searches == -1 else f"{searches} בדיקות"
        await query.edit_message_text(f"✅ אושר! {desc} למשתמש {target}")
        try:
            user_msg = (
                "🎉 המנוי החודשי שלך פעיל! תוכל לבצע חיפושים ללא הגבלה למשך 30 יום."
                if searches == -1 else
                f"🎉 התשלום אושר! נוספו לך {searches} בדיקות רכב. תוכל להתחיל מיד!"
            )
            await context.bot.send_message(target, user_msg)
        except Exception:
            pass
    except Exception as e:
        logger.error("approve_callback error: %s", e)
        await context.bot.send_message(ADMIN_ID, f"❌ שגיאה באישור: {e}")


async def handle_decline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin declines payment."""
    query = update.callback_query
    await query.answer()  # always answer first
    if query.from_user.id != ADMIN_ID:
        return
    parts  = query.data.split("|")
    target = int(parts[1])

    await query.edit_message_text("❌ הבקשה נדחתה.")
    try:
        await context.bot.send_message(
            target,
            "❌ *התשלום לא אומת\.*\n\nלשאלות פנה למנהל דרך צ'אט המנהל\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception:
        pass


async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve all valid checkout queries."""
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith("searches:"):
        await query.answer(ok=False, error_message="תשלום לא תקין")
        return
    await query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Grant searches after successful payment."""
    payment = update.message.successful_payment
    payload = payment.invoice_payload  # e.g. "searches:50"
    user_id = update.effective_user.id

    try:
        searches = int(payload.split(":")[1])
    except Exception:
        return

    admin_grant(user_id, searches)

    amount_ils = payment.total_amount // 100
    await update.message.reply_text(
        f"✅ *תשלום התקבל\!*\n\n"
        f"נוספו לך *{searches}* בדיקות רכב\.\n"
        f"סכום שחויב: ₪{amount_ils}\n\n"
        f"תודה על הרכישה\! 🙏",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Notify admin
    uname = f"@{update.effective_user.username}" if update.effective_user.username else f"id:{user_id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💰 *תשלום חדש\!*\n\n"
            f"👤 {uname}\n"
            f"🔍 {searches} בדיקות\n"
            f"💵 ₪{amount_ils}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception:
        pass



async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    msg = update.message
    if not msg.reply_to_message:
        await msg.reply_text(
            "↩️ כדי לשלוח הודעה למשתמש — השב \\(Reply\\) להודעת ההתראה שלו\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    import re as _re
    original_text = msg.reply_to_message.text or ""
    match = _re.search(r"ID[:\s`]+?(\d+)", original_text)
    if not match:
        await msg.reply_text("לא הצלחתי לזהות את ה\\-ID של המשתמש מהודעת ההתראה\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    target_id = int(match.group(1))
    try:
        await context.bot.send_message(
            target_id,
            f"📩 *הודעה מהמנהל:*\n\n{msg.text}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        await msg.reply_text(f"✅ נשלח למשתמש `{target_id}`\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        await msg.reply_text(f"❌ שגיאה בשליחה: `{e}`", parse_mode=ParseMode.MARKDOWN_V2)


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw     = update.message.text.strip()

    # Cancel search
    if raw == "❌ ביטול":
        if user_id == ADMIN_ID:
            await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=_admin_reply_keyboard())
        else:
            await update.message.reply_text("בסדר, חיפוש בוטל. בחר פעולה:", reply_markup=ReplyKeyboardRemove())
            await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=False))
        return

    # Admin settings input
    if user_id == ADMIN_ID:
        setting = context.user_data.get("admin_setting")
        if setting == "free_count":
            if not raw.isdigit() or int(raw) < 0:
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            new_val = int(raw)
            import src.users as _u
            _u.FREE_SEARCHES = new_val
            context.user_data.pop("admin_setting", None)
            await update.message.reply_text(f"✅ עודכן\\! בדיקות חינמיות: *{new_val}*", parse_mode=ParseMode.MARKDOWN_V2)
            return
        if setting == "payment_msg":
            global PAYMENT_MSG
            PAYMENT_MSG = raw
            context.user_data.pop("admin_setting", None)
            await update.message.reply_text("✅ הודעת תשלום עודכנה\\!\n\n" + raw, parse_mode=ParseMode.MARKDOWN_V2)
            return
        if setting == "broadcast":
            users = await get_all_users()
            context.user_data.pop("admin_setting", None)
            sent_ok = sent_fail = 0
            await update.message.reply_text(
                f"📤 שולח ל\\-*{len(users)}* משתמשים\\.\\.\\.".replace("-", "\\-"),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            for u in users:
                uid = u["user_id"]
                if uid == ADMIN_ID:
                    continue
                try:
                    await context.bot.send_message(
                        uid,
                        f"📢 *הודעה מהמנהל:*\n\n{raw}",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                    sent_ok += 1
                except Exception:
                    sent_fail += 1
                await asyncio.sleep(0.05)
            await update.message.reply_text(
                f"✅ נשלח בהצלחה: *{sent_ok}*\n❌ נכשל: *{sent_fail}*",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

    # User reply relay to admin
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        admin_msg_ids = context.bot_data.get("admin_chat_msg_ids", set())
        if msg.reply_to_message.message_id in admin_msg_ids:
            uname    = f"@{update.effective_user.username}" if update.effective_user.username else f"id:{user_id}"
            fullname = update.effective_user.full_name or ""
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"↩️ *תגובה ממשתמש:*\n\n"
                    f"👤 {uname} \\| 📛 {fullname} \\| 🆔 `{user_id}`\n\n"
                    f"{raw}",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                sent = await msg.reply_text("✅ הודעתך נשלחה למנהל\\.", parse_mode=ParseMode.MARKDOWN_V2)
                context.bot_data.setdefault("admin_chat_msg_ids", set()).add(sent.message_id)
            except Exception as e:
                logger.warning("Failed to relay user message to admin: %s", e)
            return

    plate = normalize_plate(raw)

    if not PLATE_RE.match(plate) or len(plate) < 5:
        await update.message.reply_text(
            "🔢 שלח מספר רכב תקין בלבד \\(למשל: 1234567\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    tg_user  = update.effective_user
    is_admin = user_id == ADMIN_ID
    allowed, left = await is_allowed(user_id, tg_user.username or "", tg_user.full_name or "")
    if not allowed:
        if await is_blocked(user_id):
            await update.message.reply_text(
                "🚫 *הגישה שלך לבוט חסומה\\.*\n\nלפרטים או לערעור פנה למנהל דרך הכפתור למטה\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_blocked_keyboard(),
            )
        else:
            await update.message.reply_text(
                PAYMENT_MSG,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_payment_keyboard(is_admin),
            )
        return

    if left == 1:
        await update.message.reply_text(
            "⚠️ זוהי הבדיקה החינמית האחרונה שלך\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    searching_msg = await update.message.reply_text(
        "🔍 מחפש נתונים\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2
    )

    try:
        record = await fetch_vehicle_data(plate)
    except Exception as exc:
        logger.error("Error fetching data for plate %s: %s", plate, exc)
        await searching_msg.delete()
        await update.message.reply_text(
            format_error(), parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persistent_keyboard(is_admin),
        )
        return

    if record is None:
        await searching_msg.delete()
        await update.message.reply_text(
            format_not_found(plate), parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persistent_keyboard(is_admin),
        )
        return

    # Only count if this is a NEW plate (not a repeat search for same plate)
    last_plate = await get_last_plate(user_id)
    is_repeat  = (last_plate == plate)
    if not is_repeat:
        await increment_search(user_id, plate)
        await set_last_plate(user_id, plate)

    summary = get_summary(record)

    if not is_repeat:
        if left == -1:
            # Check expiry date for monthly subscription
            from src.users import get_quota_expires
            expires = await get_quota_expires(user_id)
            if expires:
                expires_str = expires[:10]  # YYYY-MM-DD
                # Convert to DD/MM/YYYY
                try:
                    from datetime import datetime as _dt
                    expires_str = _dt.fromisoformat(expires[:10]).strftime("%d/%m/%Y")
                except Exception:
                    pass
                summary += f"\n\n_♾️ מנוי חודשי פעיל — תוקף עד {expires_str}_"
            else:
                summary += "\n\n_✅ גישה בלתי מוגבלת_"
        elif left > 0:
            remaining = left - 1
            label = "בדיקות" if remaining != 1 else "בדיקה"
            emoji = "🟢" if remaining > 5 else ("🟡" if remaining > 1 else "🔴")
            summary += f"\n\n_{emoji} נותרו לך {remaining} {label}_"

    await searching_msg.delete()

    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=build_result_keyboard(is_admin=(user_id == ADMIN_ID)),
    )


async def handle_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    user_id  = query.from_user.id
    is_admin = user_id == ADMIN_ID
    await query.answer()

    if query.data == "new_search":
        await query.message.reply_text(
            "🔢 שלח מספר רכב לחיפוש:",
            reply_markup=_cancel_search_keyboard(),
        )
        return

    if query.data == "chat_admin":
        admin_username = os.environ.get("ADMIN_USERNAME", "")
        url = f"https://t.me/{admin_username}" if admin_username else f"https://t.me/{BOT_USERNAME}?start=admin_chat"
        await query.message.reply_text(
            "💬 *לחץ לפתיחת שיחה עם המנהל:*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 פתח שיחה עם מנהל", url=url)]
            ]),
        )
        return

    if query.data == "admin_panel" and user_id == ADMIN_ID:
        stats = await admin_stats()
        await query.message.reply_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_reply_keyboard(),
        )
        return


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


def run_self_ping():
    import time, urllib.request as _req
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not url:
        logger.info("RENDER_EXTERNAL_URL not set — self-ping disabled")
        return
    url = url.rstrip("/") + "/health"
    while True:
        time.sleep(600)
        try:
            _req.urlopen(url, timeout=10)
            logger.debug("Self-ping OK: %s", url)
        except Exception as e:
            logger.warning("Self-ping failed: %s", e)


async def _post_init(app) -> None:
    await init_db()
    logger.info("Turso DB initialized")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    Thread(target=run_health_server, daemon=True).start()
    Thread(target=run_self_ping,     daemon=True).start()
    logger.info("Health server started")

    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("myid",   cmd_myid))
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("help",   cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("code",   cmd_code))
    app.add_handler(CommandHandler("admin",  cmd_admin))
    app.add_handler(CallbackQueryHandler(handle_user_callback,   pattern=r"^(usr|ugrant|utoggle)\|"))
    app.add_handler(CallbackQueryHandler(handle_admin_callback,  pattern=r"^adm\|"))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CallbackQueryHandler(handle_buy_callback,     pattern=r"^buy\|"))
    app.add_handler(CallbackQueryHandler(handle_paid_callback,    pattern=r"^paid\|"))
    app.add_handler(CallbackQueryHandler(handle_approve_callback, pattern=r"^approve\|"))
    app.add_handler(CallbackQueryHandler(handle_decline_callback, pattern=r"^decline\|"))
    app.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))
    app.add_handler(CallbackQueryHandler(handle_package_callback, pattern=r"^show_packages$|^pkg\|"))
    app.add_handler(CallbackQueryHandler(handle_how_it_works,    pattern=r"^how_it_works$"))
    app.add_handler(CallbackQueryHandler(handle_back_to_start,   pattern=r"^back_to_start$"))
    app.add_handler(CallbackQueryHandler(handle_result_callback,  pattern=r"^(new_search|chat_admin|admin_panel)$"))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_enter_code, pattern="^enter_code$")],
        states={WAITING_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_code)]},
        fallbacks=[
            CommandHandler("cancel", cancel_code),
            CallbackQueryHandler(handle_package_callback, pattern=r"^show_packages$"),
            MessageHandler(filters.Regex("^❌ ביטול$"), cancel_code),
        ],
        per_message=False,
    ))

    admin_kb_labels = [
        "📊 סטטיסטיקות", "👥 משתמשים", "🔑 צור קוד", "💳 הענק גישה",
        "🚫 חסום/שחרר", "⚙️ הגדרות בוט", "📢 שלח הודעה לכולם",
        "🛠 פאנל מנהל", "🔍 חזור לחיפוש", "❌ ביטול",
    ]
    import re as _re_main
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) &
        filters.Regex("^(" + "|".join(_re_main.escape(l) for l in admin_kb_labels) + ")$"),
        handle_admin_keyboard,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.REPLY,
        handle_admin_message,
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plate))

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
