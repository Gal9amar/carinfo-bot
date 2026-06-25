"""
CarInfo Bot – Israel vehicle lookup Telegram bot.
"""

import asyncio
import io
import logging
import os
import re
import sys
from threading import Thread


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, LabeledPrice, MenuButtonWebApp, WebAppInfo
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
    get_last_plate, set_last_plate, get_search_history,
    check_new_user, record_referral, get_referral_count, get_referrals,
    load_welcome_settings, get_promo_welcome_info, get_users_expiring_today, get_users_expiring_in_days,
    log_sent_message,
)
from src.formatter import (
    format_error,
    format_not_found,
    get_summary,
    get_share_text,
    yad2_label,
    quick_summary,
)
from src.pdf_report import generate_pdf
from src import yad2 as _yad2

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PLATE_RE  = re.compile(r"^[\d\-]{5,10}$")
ADMIN_ID  = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))
BOT_USERNAME = "israelcarinfobot"
PAYMENT_PROVIDER_TOKEN = os.environ.get("PAYMENT_PROVIDER_TOKEN", "6073714100:TEST:TG_2ZwhGNC5yAq7J6bMbZfUti0A")
PAYPAL_ME  = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")
PAYBOX_URL = os.environ.get("PAYBOX_URL", "https://links.payboxapp.com/xjZpYBP2n3b")

from src.packages import get_packages as _get_packages
from src.db import get_bot_setting, set_bot_setting

def _pkgs() -> list[tuple[str, int, int]]:
    """Returns (label, searches, price) from DB cache. Falls back to defaults."""
    from src.packages import _cache
    if _cache:
        return [(p[1], p[2], p[3]) for p in _cache]
    return [
        ("🔍 50 חיפושים",  50,  10),
        ("🔍 100 חיפושים", 100, 20),
        ("🔍 200 חיפושים", 200, 30),
        ("♾️ מנוי חודשי",  -1,  25),
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
    """Bottom row shown in every chat keyboard — search + mini-app shortcut."""
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    return [
        [
            InlineKeyboardButton("🔍 חיפוש רכב חדש", callback_data="new_search", style="success"),
            InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=webapp_url), style="primary"),
        ],
    ]


def _persistent_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_persistent_rows(is_admin))


def _payment_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 רכישת חבילה", web_app=WebAppInfo(url=webapp_url), style="primary")],
        [InlineKeyboardButton("🔑 יש לי קוד גישה", callback_data="enter_code")],
    ])


def _welcome_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return _persistent_keyboard(is_admin)


def _blocked_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 צ'אט עם מנהל", callback_data="chat_admin", style="primary")],
    ])


def _admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 סטטיסטיקות"), KeyboardButton("👥 משתמשים"),          KeyboardButton("🔑 צור קוד")],
        [KeyboardButton("💳 הענק גישה"),  KeyboardButton("🚫 חסום/שחרר"),        KeyboardButton("⚙️ הגדרות בוט")],
        [KeyboardButton("📢 שלח הודעה לכולם"), KeyboardButton("💰 מחירי חבילות"), KeyboardButton("🔍 חזור לחיפוש")],
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


def build_result_keyboard(
    is_admin: bool = False,
    record: dict | None = None,
    yad2_link: str = "",
) -> InlineKeyboardMarkup:
    from telegram import WebAppInfo
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    plate = record.get("mispar_rechev", "") if record else ""
    first_row = []
    if plate:
        first_row.append(InlineKeyboardButton(
            "📊 צפה בדוח המלא והורדה",
            web_app=WebAppInfo(url=f"{webapp_url}/?plate={plate}"),
        ))
    rows = [first_row] if first_row else []
    rows.extend(_persistent_rows(is_admin))
    return InlineKeyboardMarkup(rows)


def _packages_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for label, searches, price in _pkgs():
        buttons.append([InlineKeyboardButton(
            f"{label} — ₪{price}",
            callback_data=f"buy|{searches}|{price}",
            style="primary",
        )])
    buttons.append([InlineKeyboardButton("🎟️ יש לי קוד הטבה", callback_data="enter_code")])
    buttons.append([InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")))])
    return InlineKeyboardMarkup(buttons)


def _paypal_keyboard(searches: int, price: int) -> InlineKeyboardMarkup:
    paypal_url = f"{PAYPAL_ME}/{price}"
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💳 שלם ₪{price} ב-PayPal", url=paypal_url, style="primary")],
        [InlineKeyboardButton(f"💚 שלם ₪{price} ב-PayBox", url=PAYBOX_URL, style="success")],
        [InlineKeyboardButton("✅ שילמתי — שלח אישור", callback_data=f"paid|{searches}|{price}", style="success")],
        [InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=webapp_url))],
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

    referrer_id = None
    if args and args[0].startswith('ref_'):
        try:
            rid = int(args[0][4:])
            if rid != user_id:
                referrer_id = rid
        except Exception:
            pass

    is_new = await check_new_user(user_id)
    allowed, left = await is_allowed(user_id, user.username or "", user.full_name or "")

    if is_new and ADMIN_ID:
        try:
            from telegram.helpers import escape_markdown
            stats = await admin_stats()
            uname = f"@{user.username}" if user.username else f"id:{user_id}"
            uname_esc    = escape_markdown(uname, version=2)
            fullname_esc = escape_markdown(user.full_name or '', version=2)
            await context.bot.send_message(
                ADMIN_ID,
                f"👋 *משתמש חדש הצטרף\\!*\n\n"
                f"👤 {uname_esc}\n"
                f"📛 {fullname_esc}\n"
                f"🆔 `{user_id}`\n\n"
                f"👥 סה\"כ משתמשים: *{stats['total_users']}*",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception as e:
            logger.warning("Failed to notify admin of new user: %s", e)
        try:
            from src.activity import log as _log
            uname = f"@{user.username}" if user.username else str(user_id)
            await _log("new_user", f"משתמש חדש: {uname} ({user.full_name or ''})", user_id, uname)
        except Exception:
            pass

    if is_new:
        from src.users import get_promo_welcome_info
        promo_info = get_promo_welcome_info()
        if promo_info:
            try:
                from telegram.helpers import escape_markdown as _esc
                label_esc    = _esc(promo_info['label'], version=2)
                duration     = promo_info['duration_days']
                expires_str  = promo_info.get('expires_str', '')
                if duration and duration > 0:
                    duration_text = f"לתקופה של {duration} ימים"
                else:
                    duration_text = "ללא הגבלת זמן"
                expires_text = f" \\(עד {_esc(expires_str, version=2)}\\)" if expires_str else ""
                promo_text = f"🎉 ברוכים הבאים למבצע! {promo_info['label']} — {duration_text}"
                await context.bot.send_message(
                    user_id,
                    f"🎉 *ברוכים הבאים למבצע ההצטרפות\\!*\n\n"
                    f"בהתאם למבצע הצטרפות הפעיל — מגיע לך:\n"
                    f"✨ *{label_esc}*\n"
                    f"⏱ {duration_text}{expires_text}",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                await log_sent_message(user_id, promo_text, kind="promo_welcome")
            except Exception as e:
                logger.warning("Failed to send promo welcome: %s", e)

    if not is_new and referrer_id:
        try:
            ref_uname = f"@{user.username}" if user.username else str(user_id)
            ref_info_msg = f"ℹ️ לא ניתן לקבל בונוס הפניה — {ref_uname} כבר קיים בבוט"
            await context.bot.send_message(
                referrer_id,
                f"ℹ️ *לא ניתן לקבל בונוס הפניה*\n\n"
                f"המשתמש {ref_uname} כבר קיים בבוט\\.\n"
                f"הבונוס ניתן רק עבור משתמשים חדשים שמצטרפים לראשונה\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            await log_sent_message(referrer_id, ref_info_msg, kind="referral_info")
        except Exception:
            pass

    if is_new and referrer_id:
        try:
            from src.db import get_bot_setting, execute as _db_execute
            bonus_str = await get_bot_setting("referral_bonus")
            bonus = int(bonus_str) if bonus_str and bonus_str.isdigit() else 10
            await record_referral(user_id, referrer_id, bonus)
            await _db_execute(
                "UPDATE users SET searches_quota = searches_quota + ? WHERE user_id = ? AND searches_quota >= 0",
                [bonus, referrer_id],
            )
            ref_uname = f"@{user.username}" if user.username else str(user_id)
            referral_msg = (
                f"🎉 *חבר חדש הצטרף דרך הלינק שלך!*\n\n"
                f"👤 {ref_uname} הצטרף לבוט\n"
                f"🎁 קיבלת *{bonus} חיפושים* בונוס!"
            )
            try:
                await context.bot.send_message(
                    referrer_id,
                    referral_msg,
                    parse_mode="Markdown",
                )
                await log_sent_message(referrer_id, referral_msg, kind="referral_bonus")
            except Exception:
                pass
            try:
                from src.activity import log as _log
                await _log("grant", f"בונוס הפניה: +{bonus} חיפושים (הצטרף: {ref_uname})", referrer_id, "")
            except Exception:
                pass
        except Exception as e:
            logger.warning("Referral processing error: %s", e)

    is_admin = (user_id == ADMIN_ID)

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

    welcome_text = f"🚗 ברוך הבא ל-CarInfo! {searches_info}"
    await update.message.reply_text(
        "🚗 *ברוך הבא ל\\-CarInfo\\!*\n"
        "_הבוט החכם לבדיקת רכבים בישראל_\n\n"
        "⚡ שלח מספר לוחית רישוי ותקבל תוך שניות:\n\n"
        "📋 פרטי הרכב המלאים\n"
        "👥 היסטוריית בעלויות\n"
        "⚙️ מפרט טכני מלא\n"
        "🛡️ בטיחות ו\\-ADAS\n"
        "🔔 ריקולים פתוחים\n"
        "💰 הערכת מחיר שוק\n\n"
        "🔍 *כיצד להתחיל?*\n"
        "פשוט שלח מספר לוחית רישוי\n"
        "לדוגמה: _1234567_\n\n"
        f"🆓 {searches_info}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_welcome_keyboard(is_admin),
    )
    await log_sent_message(user_id, welcome_text, kind="welcome")


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
            [InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")))],
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
        await log_sent_message(user_id, f"✅ קוד הופעל: {msg}", kind="code_applied")
    else:
        await update.message.reply_text(
            f"❌ *קוד לא תקין*\n\n{_escape_md(msg)}\n\nנסה שוב או חזור לתפריט החבילות\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                *_persistent_rows(is_admin),
            ]),
        )
    return ConversationHandler.END


async def cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=(user_id == ADMIN_ID)))
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
        [InlineKeyboardButton("🎫 10 בדיקות",  callback_data="adm|gen|10|single"),
         InlineKeyboardButton("🎫 25 בדיקות",  callback_data="adm|gen|25|single")],
        [InlineKeyboardButton("🎫 50 בדיקות",  callback_data="adm|gen|50|single"),
         InlineKeyboardButton("🎫 100 בדיקות", callback_data="adm|gen|100|single")],
        [InlineKeyboardButton("📅 חודש – חיפושים חופשיים", callback_data="adm|gen|monthly|single")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")],
    ])


def _admin_settings_keyboard(maintenance_on: bool = False) -> InlineKeyboardMarkup:
    maint_label = "🔴 בטל תחזוקה" if maintenance_on else "🔧 הפעל תחזוקה"
    maint_style = "danger" if maintenance_on else None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ שנה הודעת תשלום",         callback_data="adm|set_payment")],
        [InlineKeyboardButton("🆓 שנה מספר בדיקות חינמיות", callback_data="adm|set_free")],
        [InlineKeyboardButton(maint_label,                   callback_data="adm|toggle_maintenance", style=maint_style)],
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
                await log_sent_message(target["user_id"], user_msg, kind="grant")
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
        reply_markup=_admin_main_keyboard(),
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
        free        = _u.FREE_SEARCHES
        maintenance = (await get_bot_setting("maintenance")) == "1"
        maint_str   = "🔴 פעיל" if maintenance else "🟢 כבוי"
        await query.edit_message_text(
            f"⚙️ *הגדרות בוט*\n\n"
            f"• בדיקות חינמיות למשתמש חדש: *{free}*\n"
            f"• מצב תחזוקה: *{maint_str}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_settings_keyboard(maintenance),
        )
        return

    if action == "toggle_maintenance":
        maintenance = (await get_bot_setting("maintenance")) == "1"
        new_val     = "0" if maintenance else "1"
        await set_bot_setting("maintenance", new_val)
        maintenance = new_val == "1"
        maint_str   = "🔴 פעיל" if maintenance else "🟢 כבוי"
        import src.users as _u
        free = _u.FREE_SEARCHES
        await query.edit_message_text(
            f"⚙️ *הגדרות בוט*\n\n"
            f"• בדיקות חינמיות למשתמש חדש: *{free}*\n"
            f"• מצב תחזוקה: *{maint_str}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_settings_keyboard(maintenance),
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
            block_msg = "🚫 הגישה שלך לבוט נחסמה. לפרטים פנה למנהל."
            await context.bot.send_message(
                target_id,
                "🚫 הגישה שלך לבוט נחסמה\\. לפרטים פנה למנהל\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            await log_sent_message(target_id, block_msg, kind="block")
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
            unblock_msg = "✅ החסימה שלך הוסרה. תוכל להמשיך להשתמש בבוט."
            await context.bot.send_message(
                target_id,
                "✅ החסימה שלך הוסרה\\. תוכל להמשיך להשתמש בבוט\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            await log_sent_message(target_id, unblock_msg, kind="unblock")
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


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's search history as clickable plate buttons."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id == ADMIN_ID

    # Check if it's a specific plate from history
    if query.data.startswith("hist_plate|"):
        plate = query.data.split("|")[1]
        searching_msg = await query.message.reply_text("🔍 מחפש נתונים\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
        try:
            record = await fetch_vehicle_data(plate)
        except Exception as exc:
            await searching_msg.delete()
            await query.message.reply_text(format_error(), parse_mode=ParseMode.MARKDOWN_V2)
            return
        await searching_msg.delete()
        if not record:
            await query.message.reply_text(format_not_found(plate), parse_mode=ParseMode.MARKDOWN_V2)
            return
        context.user_data["last_record"] = record
        context.user_data["last_share_text"] = get_share_text(record)
        card = f"🔖 לוחית: `{plate}`\n" + quick_summary(record)
        yad2_link = _yad2.build_url(record)
        await query.message.reply_text(
            card,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_result_keyboard(is_admin=is_admin, record=record, yad2_link=yad2_link),
        )
        return

    # Show history list
    history = await get_search_history(user_id, limit=10)
    if not history:
        await query.edit_message_text(
            "📜 אין היסטוריית חיפושים עדיין.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 חזרה", callback_data="back_to_start")
            ]])
        )
        return

    buttons = []
    for plate in history:
        buttons.append([InlineKeyboardButton(f"🚗 {plate}", callback_data=f"hist_plate|{plate}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="back_to_start")])

    await query.edit_message_text(
        "📜 *היסטוריית החיפושים שלך:*\n_לחץ על מספר רכב לצפייה חוזרת \\(לא מנכה בדיקה\\)_",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    user_id  = query.from_user.id
    is_admin = user_id == ADMIN_ID
    await query.answer()

    from src.users import get_user_by_id, get_quota_expires
    u    = await get_user_by_id(user_id)
    left  = u.get("searches_left", 0) if u else 0
    quota = u.get("searches_quota", 0) if u else 0
    if quota == -1:
        try:
            expires = await get_quota_expires(user_id)
            if expires:
                from datetime import datetime as _dt
                exp_str = _dt.strptime(expires, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                _si = f"♾️ מנוי חודשי פעיל עד {_escape_md(exp_str)}"
            else:
                _si = "✅ גישה בלתי מוגבלת"
        except Exception:
            _si = "✅ גישה בלתי מוגבלת"
    elif left > 0:
        _si = f"נותרו לך *{left}* בדיקות\\."
    else:
        _si = "גישה מלאה פעילה ✅"

    await query.edit_message_text(
        "🚗 *ברוך הבא ל\\-CarInfo\\!*\n"
        "_הבוט החכם לבדיקת רכבים בישראל_\n\n"
        "⚡ שלח מספר לוחית רישוי ותקבל תוך שניות:\n\n"
        "📋 פרטי הרכב המלאים\n"
        "👥 היסטוריית בעלויות\n"
        "⚙️ מפרט טכני מלא\n"
        "🛡️ בטיחות ו\\-ADAS\n"
        "🔔 ריקולים פתוחים\n"
        "💰 הערכת מחיר שוק\n\n"
        "🔍 *כיצד להתחיל?*\n"
        "פשוט שלח מספר לוחית רישוי\n"
        "לדוגמה: _1234567_\n\n"
        f"🆓 {_si}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_welcome_keyboard(is_admin),
    )


async def handle_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import src.users as _u
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()

    free = _u.FREE_SEARCHES
    pkg_lines = []
    for label, searches, price in _pkgs():
        desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
        pkg_lines.append(f"• {_escape_md(label)} – ₪{price}")

    pkg_text = "\n".join(pkg_lines) if pkg_lines else "אין חבילות זמינות כרגע"
    await query.edit_message_text(
        "ℹ️ *איך CarInfo עובד?*\n"
        "_הבוט החכם לבדיקת רכבים בישראל_\n\n"
        "⚡ *שלח לוחית רישוי — קבל דוח מלא תוך שניות*\n\n"
        "📋 *מה מוצג על כל רכב:*\n"
        "🚗 פרטים כלליים – יצרן, דגם, שנה, צבע\n"
        "⚙️ מפרט טכני – מנוע, הנעה, דלק, כוח סוס\n"
        "🛞 גלגלים וצמיגים\n"
        "🪑 ציוד ונוחות – מיזוג, הגה כוח, חלונות\n"
        "🛡️ בטיחות – ABS, ESP, כריות אוויר, CO2\n"
        "🤖 מערכות ADAS – בלימה אוטומטית, שמירת נתיב\n"
        "📅 היסטוריה – רישום, טסט, ק\"מ, שינויי מבנה\n"
        "👥 בעלויות – כמה בעלים, פרטי/סוחר\n"
        "💰 הערכת מחיר שוק – על בסיס Yad2\n"
        "🚨 בדיקת גנבה – מאגר המשטרה\n"
        "⚠️ ריקולים – תקלות ידועות של הדגם\n\n"
        f"🆓 *חינמי:* כל משתמש חדש מקבל *{free} חיפושים* לניסיון\n\n"
        "🎁 *קבל חיפושים במתנה:*\n"
        "הפנה חברים לבוט וקבל חיפושים על כל הצטרפות\n\n"
        "📦 *חבילות חיפוש:*\n"
        f"{pkg_text}\n\n"
        "🔑 *קוד גישה?* שלח `/code XXXXXXXX`\n"
        "🎫 *תמיכה?* לחץ על כפתור התמיכה בתפריט",
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
        webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
        await query.edit_message_text(
            "🛒 *רכישת חבילת חיפושים*\n\nפתח את התפריט לרכישה:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=webapp_url))
            ]]),
        )
        return

    # buy| handled by handle_buy_callback

async def _build_user_grant_keyboard(uid: int, blocked: bool) -> InlineKeyboardMarkup:
    from src.admin_grants import get_admin_grants
    grants = await get_admin_grants()
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for _gid, label, searches, _order in grants:
        row.append(InlineKeyboardButton(label, callback_data=f"ugrant|{uid}|{searches}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🚫 חסום" if not blocked else "✅ שחרר", callback_data=f"utoggle|{uid}")])
    rows.append([InlineKeyboardButton("🔙 חזור למשתמשים", callback_data="usr|back")])
    return InlineKeyboardMarkup(rows)


def _grant_description(amount: int) -> str:
    if amount == -2:
        return "גישה חופשית"
    if amount == -1:
        return "מנוי חודשי"
    if amount == 0:
        return "מסלול FREE"
    return f"{amount} בדיקות"


def _format_grant_message(searches: int, expires: str = "") -> str:
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")
    footer = "\n\nלפרטים המלאים אודות הפיצרים למנוי שלך ניתן להיכנס לתפריט *רכישת מנויים*."

    if searches == 0:
        return f"🔔 *המנוי שלך עודכן!*\n\n📦 מסוג: מסלול FREE\n📅 החל מ: {today}{footer}"
    if searches == -2:
        return f"🔔 *המנוי שלך עודכן!*\n\n📦 מסוג: גישה חופשית ♾️\n📅 החל מ: {today}\n⏰ בתוקף: ללא הגבלת זמן{footer}"
    if searches == -1:
        end_str = ""
        if expires:
            try:
                end_str = f"\n⏰ בתוקף עד: {datetime.fromisoformat(expires).strftime('%d/%m/%Y')}"
            except Exception:
                pass
        return f"🔔 *המנוי שלך עודכן!*\n\n📦 מסוג: מנוי חודשי\n📅 החל מ: {today}{end_str}{footer}"
    return f"🔔 *המנוי שלך עודכן!*\n\n📦 נוספו: {searches} חיפושים 🔍\n📅 החל מ: {today}{footer}"


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
        buttons = await _build_user_grant_keyboard(uid, blocked)
        await query.edit_message_text(info, reply_markup=buttons)
        return


    # ugrant|UID|AMOUNT    # ugrant|UID|AMOUNT — grant searches
    if parts[0] == "ugrant":
        uid     = int(parts[1])
        amount  = int(parts[2])
        await admin_grant(ADMIN_ID, uid, amount, "granted via admin panel")
        desc    = _grant_description(amount)
        await query.answer(f"✅ הוענקו {desc}", show_alert=True)
        # Notify user with rich subscription update message
        try:
            from src.users import get_quota_expires
            expires = await get_quota_expires(uid) or ""
            msg = _format_grant_message(amount, expires)
            await context.bot.send_message(uid, msg, parse_mode="Markdown")
            await log_sent_message(uid, msg, kind="grant")
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
        await query.edit_message_text(info, reply_markup=await _build_user_grant_keyboard(uid, blocked))
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
                unblock_msg = "✅ החסימה שלך הוסרה. תוכל להמשיך להשתמש בבוט."
                await context.bot.send_message(uid, unblock_msg)
                await log_sent_message(uid, unblock_msg, kind="block")
            except Exception:
                pass
        else:
            await block_user(uid)
            await query.answer("🚫 נחסם", show_alert=True)
            try:
                block_msg = "🚫 הגישה שלך לבוט נחסמה. לפרטים פנה למנהל."
                await context.bot.send_message(uid, block_msg)
                await log_sent_message(uid, block_msg, kind="block")
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
        await query.edit_message_text(info, reply_markup=await _build_user_grant_keyboard(uid, blocked))
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
        maintenance = (await get_bot_setting("maintenance")) == "1"
        maint_str   = "🔴 פעיל" if maintenance else "🟢 כבוי"
        await update.message.reply_text(
            f"⚙️ *הגדרות בוט*\n\n"
            f"• בדיקות חינמיות למשתמש חדש: *{_u.FREE_SEARCHES}*\n"
            f"• מצב תחזוקה: *{maint_str}*",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_settings_keyboard(maintenance),
        )

    async def send_broadcast_prompt():
        await update.message.reply_text(
            "📢 *שליחת הודעה לכולם*\n\nשלח את ההודעה שתרצה להפיץ לכל המשתמשים:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        context.user_data["admin_setting"] = "broadcast"

    async def send_packages_editor():
        from src.packages import get_packages
        pkgs = await get_packages()
        buttons = []
        for pid, label, searches, price in pkgs:
            desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
            buttons.append([InlineKeyboardButton(
                f"📦 {label} — {desc} · ₪{price}",
                callback_data=f"admpkg|pick|{pid}",
            )])
        buttons.append([InlineKeyboardButton("➕ הוסף חבילה", callback_data="admpkg|add")])
        await update.message.reply_text(
            "💰 *עריכת מחירי חבילות*\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    dispatch = {
        "📊 סטטיסטיקות":      send_stats,
        "👥 משתמשים":         send_users,
        "🔑 צור קוד":         send_gen_menu,
        "💳 הענק גישה":       send_grant_info,
        "🚫 חסום/שחרר":       send_block_list,
        "⚙️ הגדרות בוט":      send_settings,
        "📢 שלח הודעה לכולם": send_broadcast_prompt,
        "💰 מחירי חבילות":    send_packages_editor,
    }
    if text_msg == "🛠 פאנל מנהל":
        stats = await admin_stats()
        await update.message.reply_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_main_keyboard(),
        )
        return
    if text_msg == "🔍 חזור לחיפוש":
        await update.message.reply_text(
            "🔍 שלח מספר לוחית לחיפוש:",
            reply_markup=_cancel_search_keyboard(),
        )
        return
    if text_msg == "❌ ביטול":
        await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=True))
        return
    fn = dispatch.get(text_msg)
    if fn:
        await fn()


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the Mini App for purchasing packages."""
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    from telegram import WebAppInfo
    await update.message.reply_text(
        "💳 *רכישת בדיקות*\n\nלחץ על הכפתור למטה לפתיחת חנות החבילות:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 רכישת חבילה", web_app=WebAppInfo(url=webapp_url))],
        ]),
    )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show PayPal payment link for selected package."""
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    searches = int(parts[1])
    price    = int(parts[2])
    label = next((l for l, s, p in _pkgs() if s == searches and p == price), f"{searches} בדיקות")

    desc = "ללא הגבלה למשך 30 יום" if searches == -1 else f"{searches} בדיקות רכב"
    await query.message.reply_text(
        f"💳 *{label}*\n\n"
        f"• {desc}\n"
        f"• מחיר: *₪{price}*\n\n"
        f"1\\. לחץ על כפתור התשלום למטה \\(PayPal או PayBox\\)\n"
        f"2\\. השלם את התשלום\n"
        f"3\\. חזור לכאן ולחץ *שילמתי* לשליחת אישור\n\n"
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
    label    = next((l for l, s, p in _pkgs() if s == searches and p == price), f"{searches} בדיקות")

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
                    InlineKeyboardButton("✅ אשר ופתח גישה", callback_data=f"approve|{user_id}|{searches}", style="success"),
                    InlineKeyboardButton("❌ דחה", callback_data=f"decline|{user_id}", style="danger"),
                ]]),
            )
        except Exception as e:
            logger.warning("Failed to notify admin of payment: %s", e)

    await query.edit_message_text(
        "✅ *בקשתך נשלחה למנהל\\!*\n\n"
        "הגישה תיפתח לאחר אימות התשלום\\. בדרך כלל תוך מספר דקות\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


_bot_instance = None  # set in main(), used by API server

async def _notify_admin_payment(user_id: int, name: str, label: str, searches: int, price: int, ref: str) -> None:
    """Called from api.py when user confirms payment via Mini App."""
    if not _bot_instance or not ADMIN_ID:
        return
    await _bot_instance.send_message(
        ADMIN_ID,
        f"💰 *בקשת אישור תשלום \\(Mini App\\)!*\n\n"
        f"👤 {name}\n🆔 {user_id}\n📦 {label}\n💵 {price} שח\n🔑 ref: {ref}\n\n"
        f"לאחר אימות התשלום ב\\-PayPal לחץ אשר:",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ אשר ופתח גישה", callback_data=f"approve|{user_id}|{searches}", style="success"),
            InlineKeyboardButton("❌ דחה",             callback_data=f"decline|{user_id}", style="danger"),
        ]]),
    )


async def _notify_admin_ticket(ticket_id: int, user_id: int, name: str, subject: str, message: str):
    try:
        text = (
            f"🎫 *פנייה חדשה #{ticket_id}*\n"
            f"👤 {name} (`{user_id}`)\n"
            f"📋 *נושא:* {subject}\n\n"
            f"{message[:500]}"
        )
        webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
        from telegram import WebAppInfo
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎫 פתח טיקט", web_app=WebAppInfo(url=f"{webapp_url}/?page=admin_ticket&id={ticket_id}"))
        ]])
        await _bot_instance.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass


async def _notify_user_ticket_reply(user_id: int, ticket_id: int, subject: str, reply: str):
    try:
        webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
        from telegram import WebAppInfo
        text = (
            f"💬 *תגובה חדשה לפנייה שלך*\n"
            f"📋 *נושא:* {subject}\n\n"
            f"{reply[:500]}"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📂 פתח פנייה", web_app=WebAppInfo(url=f"{webapp_url}/?page=ticket&id={ticket_id}"))
        ]])
        await _bot_instance.send_message(user_id, text, parse_mode="Markdown", reply_markup=kb)
        await log_sent_message(user_id, text, kind="ticket_reply")
    except Exception:
        pass


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

        await admin_grant(ADMIN_ID, target, searches, note="PayPal payment approved")

        desc = "מנוי חודשי ללא הגבלה" if searches == -1 else f"{searches} בדיקות"
        await query.edit_message_text(f"✅ אושר! {desc} למשתמש {target}")
        try:
            user_msg = (
                "🎉 המנוי החודשי שלך פעיל! תוכל לבצע חיפושים ללא הגבלה למשך 30 יום."
                if searches == -1 else
                f"🎉 התשלום אושר! נוספו לך {searches} בדיקות רכב. תוכל להתחיל מיד!"
            )
            await context.bot.send_message(target, user_msg)
            await log_sent_message(target, user_msg, kind="payment")
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
        decline_msg = "❌ *התשלום לא אומת\\.*\n\nלשאלות פנה למנהל דרך צ'אט המנהל\\."
        await context.bot.send_message(target, decline_msg, parse_mode=ParseMode.MARKDOWN_V2)
        await log_sent_message(target, decline_msg, kind="payment")
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

    await admin_grant(ADMIN_ID, user_id, searches, note="Telegram Stars payment")

    amount_ils = payment.total_amount // 100
    await update.message.reply_text(
        f"✅ *תשלום התקבל\\!*\n\n"
        f"נוספו לך *{searches}* בדיקות רכב\\.\n"
        f"סכום שחויב: ₪{amount_ils}\n\n"
        f"תודה על הרכישה\\! 🙏",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    await log_sent_message(user_id, f"✅ תשלום התקבל! נוספו {searches} בדיקות — ₪{amount_ils}", kind="payment")

    # Notify admin
    uname = f"@{update.effective_user.username}" if update.effective_user.username else f"id:{user_id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💰 *תשלום חדש\\!*\n\n"
            f"👤 {uname}\n"
            f"🔍 {searches} בדיקות\n"
            f"💵 ₪{amount_ils}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception:
        pass



async def handle_admpkg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("אין הרשאה.")
        return
    await query.answer()
    from src.packages import get_packages, update_package, add_package, delete_package

    parts  = query.data.split("|")
    action = parts[1]

    def _pkg_buttons(pkgs):
        btns = []
        for pid, lbl, srch, prc in pkgs:
            desc = "ללא הגבלה" if srch == -1 else f"{srch} חיפושים"
            btns.append([InlineKeyboardButton(f"📦 {lbl} — {desc} · ₪{prc}", callback_data=f"admpkg|pick|{pid}")])
        btns.append([InlineKeyboardButton("➕ הוסף חבילה", callback_data="admpkg|add")])
        return btns

    if action == "list":
        pkgs = await get_packages()
        await query.edit_message_text(
            "💰 *עריכת מחירי חבילות*\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(_pkg_buttons(pkgs)),
        )

    elif action == "pick":
        pkg_id = int(parts[2])
        pkgs   = await get_packages()
        pkg    = next((p for p in pkgs if p[0] == pkg_id), None)
        if not pkg:
            await query.edit_message_text("❌ חבילה לא נמצאה\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return
        pid, label, searches, price = pkg
        desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
        await query.edit_message_text(
            f"📦 *{_escape_md(label)}*\n\n{_escape_md(desc)} · ₪{price}\n\nמה לעשות?",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ ערוך", callback_data=f"admpkg|startedit|{pid}"),
                 InlineKeyboardButton("🗑 מחק",  callback_data=f"admpkg|del|{pid}")],
                [InlineKeyboardButton("🔙 חזרה", callback_data="admpkg|list")],
            ]),
        )

    elif action == "del":
        pkg_id = int(parts[2])
        await delete_package(pkg_id)
        pkgs = await get_packages()
        await query.edit_message_text(
            "✅ *חבילה נמחקה\\!*\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(_pkg_buttons(pkgs)),
        )

    elif action == "startedit":
        pkg_id = int(parts[2])
        context.user_data["admin_setting"]  = "pkg_edit_searches"
        context.user_data["admin_pkg_id"]   = pkg_id
        await query.edit_message_text(
            "✏️ *עריכת חבילה*\n\nכמה חיפושים? \\(שלח `\\-1` לבלתי מוגבל\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    elif action == "add":
        context.user_data["admin_setting"] = "pkg_add_label"
        await query.edit_message_text(
            "➕ *הוספת חבילה חדשה*\n\nשלח את שם החבילה:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


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
        dm_text = f"📩 הודעה מהמנהל: {msg.text}"
        await context.bot.send_message(
            target_id,
            f"📩 *הודעה מהמנהל:*\n\n{msg.text}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        await log_sent_message(target_id, dm_text, kind="admin_dm")
        await msg.reply_text(f"✅ נשלח למשתמש `{target_id}`\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        await msg.reply_text(f"❌ שגיאה בשליחה: `{e}`", parse_mode=ParseMode.MARKDOWN_V2)


async def _send_car_photo(message, record: dict) -> None:
    """Download a car image and send it as a photo reply. Logs errors at WARNING level."""
    import httpx as _httpx, io as _io
    from src.api.image_api import fetch_car_image
    make  = record.get("tozeret_nm", "")
    model = record.get("kinuy_mishari") or record.get("degem_nm", "")
    year  = str(record.get("shnat_yitzur", ""))
    color = record.get("tzeva_rechev", "")
    if not (make or model):
        return
    try:
        img_url = await fetch_car_image(make, model, year, color)
        logger.info("car_photo: make=%r model=%r img_url=%s", make, model, img_url)
        if not img_url:
            return
        _ua = {"User-Agent": "CarInfoBot/1.0 (contact: gal9amar@gmail.com)"}
        async with _httpx.AsyncClient(timeout=15, follow_redirects=True, headers=_ua) as _cl:
            _r = await _cl.get(img_url)
        logger.info("car_photo download: status=%s bytes=%d", _r.status_code, len(_r.content))
        if _r.status_code != 200:
            return
        caption = " · ".join(p for p in [make, model, year] if p)
        await message.reply_photo(photo=_io.BytesIO(_r.content), caption=caption)
        logger.info("car_photo sent ok")
    except Exception as exc:
        logger.warning("car_photo failed: %s", exc)


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw     = update.message.text.strip()

    # Maintenance mode — block non-admins
    if user_id != ADMIN_ID and (await get_bot_setting("maintenance")) == "1":
        await update.message.reply_text(
            "🔧 *הבוט בתחזוקה כרגע*\n\nנחזור בקרוב\\!",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Cancel search
    if raw == "❌ ביטול":
        await update.message.reply_text("בסדר, חיפוש בוטל.", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=(user_id == ADMIN_ID)))
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
        if setting == "pkg_add_label":
            context.user_data["admin_pkg_label"] = raw
            context.user_data["admin_setting"] = "pkg_add_searches"
            await update.message.reply_text(
                "כמה חיפושים? \\(שלח `\\-1` לבלתי מוגבל\\)",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        if setting == "pkg_add_searches":
            if not raw.lstrip("-").isdigit():
                await update.message.reply_text("❌ שלח מספר שלם בלבד\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            context.user_data["admin_pkg_searches"] = int(raw)
            context.user_data["admin_setting"] = "pkg_add_price"
            await update.message.reply_text("מה המחיר ב\\-₪?", parse_mode=ParseMode.MARKDOWN_V2)
            return
        if setting == "pkg_add_price":
            if not raw.isdigit():
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            from src.packages import get_packages, add_package
            label    = context.user_data.pop("admin_pkg_label", "חבילה חדשה")
            searches = context.user_data.pop("admin_pkg_searches", 10)
            price    = int(raw)
            context.user_data.pop("admin_setting", None)
            await add_package(label, searches, price)
            pkgs = await get_packages()
            buttons = []
            for pid, lbl, srch, prc in pkgs:
                desc = "ללא הגבלה" if srch == -1 else f"{srch} חיפושים"
                buttons.append([InlineKeyboardButton(f"📦 {lbl} — {desc} · ₪{prc}", callback_data=f"admpkg|pick|{pid}")])
            buttons.append([InlineKeyboardButton("➕ הוסף חבילה", callback_data="admpkg|add")])
            await update.message.reply_text(
                "✅ *חבילה נוספה\\!*\n\nבחר חבילה לעריכה או הוסף חדשה:",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        if setting == "pkg_edit_searches":
            if not raw.lstrip("-").isdigit():
                await update.message.reply_text("❌ שלח מספר שלם בלבד\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            context.user_data["admin_pkg_searches"] = int(raw)
            context.user_data["admin_setting"] = "pkg_edit_price"
            await update.message.reply_text("מה המחיר ב\\-₪?", parse_mode=ParseMode.MARKDOWN_V2)
            return
        if setting == "pkg_edit_price":
            if not raw.isdigit():
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            from src.packages import get_packages, update_package
            pkg_id   = context.user_data.pop("admin_pkg_id", None)
            searches = context.user_data.pop("admin_pkg_searches", 10)
            price    = int(raw)
            context.user_data.pop("admin_setting", None)
            if pkg_id is None:
                await update.message.reply_text("❌ שגיאה פנימית\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            pkgs    = await get_packages()
            pkg_row = next((p for p in pkgs if p[0] == pkg_id), None)
            if pkg_row is None:
                await update.message.reply_text("❌ חבילה לא נמצאה\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            await update_package(pkg_id, pkg_row[1], searches, price)
            pkgs = await get_packages()
            buttons = []
            for pid, lbl, srch, prc in pkgs:
                desc = "ללא הגבלה" if srch == -1 else f"{srch} חיפושים"
                buttons.append([InlineKeyboardButton(f"📦 {lbl} — {desc} · ₪{prc}", callback_data=f"admpkg|pick|{pid}")])
            buttons.append([InlineKeyboardButton("➕ הוסף חבילה", callback_data="admpkg|add")])
            await update.message.reply_text(
                "✅ *חבילה עודכנה\\!*\n\nבחר חבילה לעריכה או הוסף חדשה:",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        if setting == "broadcast":
            all_users = await get_all_users()
            tg_users = all_users
            context.user_data.pop("admin_setting", None)
            logger.info("Broadcast: total_users=%d tg_users=%d msg=%r", len(all_users), len(tg_users), raw[:50])
            sent_ok = sent_fail = 0
            await update.message.reply_text(
                f"📤 שולח ל\\-*{len(tg_users)}* משתמשי טלגרם\\.\\.\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            from telegram.helpers import escape_markdown
            escaped_msg = escape_markdown(raw, version=2)
            broadcast_log_text = f"📢 הודעה מהמנהל: {raw}"
            for u in tg_users:
                uid = u["user_id"]
                if uid == ADMIN_ID:
                    continue
                try:
                    await context.bot.send_message(
                        uid,
                        f"📢 *הודעה מהמנהל:*\n\n{escaped_msg}",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                    await log_sent_message(uid, broadcast_log_text, kind="broadcast")
                    sent_ok += 1
                except Exception as e:
                    logger.warning("Broadcast failed for uid=%s: %s", uid, e)
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

    # cache hit — skip API call
    record = cache.get(plate)
    if record is None:
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
        if record is not None:
            cache.set(plate, record)
        await searching_msg.delete()
    else:
        searching_msg = None

    if record is None:
        await update.message.reply_text(
            format_not_found(plate), parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persistent_keyboard(is_admin),
        )
        return

    context.user_data["last_record"] = record

    # Only count if this is a NEW plate (not a repeat search for same plate)
    last_plate = await get_last_plate(user_id)
    is_repeat  = (last_plate == plate)
    if not is_repeat:
        await increment_search(user_id, plate)
        await set_last_plate(user_id, plate)

    try:
        card = f"🔖 לוחית: `{plate}`\n" + quick_summary(record)
        context.user_data["last_share_text"] = get_share_text(record)
    except Exception as exc:
        logger.error("quick_summary failed for plate %s: %s", plate, exc)
        if searching_msg:
            try:
                await searching_msg.delete()
            except Exception:
                pass
        await update.message.reply_text(
            format_error(), parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_persistent_keyboard(is_admin),
        )
        return

    if not is_repeat:
        if left == -1:
            from src.users import get_quota_expires
            expires = await get_quota_expires(user_id)
            if expires:
                try:
                    from datetime import datetime as _dt
                    expires_str = _dt.fromisoformat(expires[:10]).strftime("%d/%m/%Y")
                except Exception:
                    expires_str = expires[:10].replace("-", "\\-")
                card += f"\n\n_♾️ מנוי חודשי פעיל — תוקף עד {expires_str}_"
            else:
                card += "\n\n_✅ גישה בלתי מוגבלת_"
        elif left > 0:
            remaining = left - 1
            label = "בדיקות" if remaining != 1 else "בדיקה"
            emoji = "🟢" if remaining > 5 else ("🟡" if remaining > 1 else "🔴")
            card += f"\n\n_{emoji} נותרו לך {remaining} {label}_"

    if searching_msg:
        try:
            await searching_msg.delete()
        except Exception:
            pass

    yad2_link = _yad2.build_url(record)
    try:
        await update.message.reply_text(
            card,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=build_result_keyboard(
                is_admin=(user_id == ADMIN_ID),
                record=record,
                yad2_link=yad2_link,
            ),
        )
    except Exception as exc:
        logger.error("reply_text MarkdownV2 failed for plate %s: %s", plate, exc)
        try:
            plain = card.replace("\\", "")
            await update.message.reply_text(
                plain,
                reply_markup=build_result_keyboard(
                    is_admin=(user_id == ADMIN_ID),
                    record=record,
                    yad2_link=yad2_link,
                ),
            )
        except Exception as exc2:
            logger.error("plain fallback also failed for plate %s: %s", plate, exc2)





async def handle_share_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    share_text = context.user_data.get("last_share_text")
    if not share_text:
        await query.message.reply_text("❌ לא נמצא דוח לשיתוף. בצע חיפוש חדש.")
        return
    await query.message.reply_text(share_text)


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
            reply_markup=_admin_main_keyboard(),
        )
        return


_PDF_PREPARING = "📄 מכין את קובץ הדוח... אנא המתן."


async def handle_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    record = context.user_data.get("last_record")
    if not record:
        await query.message.reply_text("❌ לא נמצא רכב לדוח. בצע חיפוש חדש.")
        return
    plate = record.get("mispar_rechev", "vehicle")
    status_msg = await query.message.reply_text(_PDF_PREPARING)

    try:
        pdf_bytes = await asyncio.to_thread(
            generate_pdf,
            record,
            tg_link=f"t.me/{BOT_USERNAME}",
            wa_link="",
            logo_path=os.environ.get("LOGO_PATH", ""),
            cover_path=os.environ.get("COVER_PATH", ""),
            channel="telegram",
        )
    except Exception as e:
        logger.error("PDF generation failed for plate %s: %s", plate, e)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await query.message.reply_text("❌ שגיאה ביצירת הדוח.")
        return
    try:
        await status_msg.delete()
    except Exception:
        pass
    await query.message.reply_document(
        document=io.BytesIO(pdf_bytes),
        filename=f"car_{plate}.pdf",
        caption=f"📄 דוח רכב {plate}",
    )




async def _cache_cleanup_job():
    """Clear expired cache entries every 10 minutes."""
    while True:
        await asyncio.sleep(600)
        cache.clear_expired()


async def _yad2_watch_job(context) -> None:
    """Job-queue callback: check Yad2 for new listings matching active watches."""
    from src import yad2 as _yad2
    from src.yad2_watcher import get_all_active_watches, update_seen_ids
    from src.db import get_bot_setting

    if (await get_bot_setting("yad2_watch_enabled")) != "1":
        return

    try:
        watches = await get_all_active_watches()
        if not watches:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    "🔍 *בדיקת מעקב יד2 בוצעה* — אין מעקבים פעילים",
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            except Exception:
                pass
            return

        for w in watches:
            try:
                listings = _yad2.fetch_listings(w["make"], w.get("model", ""), w.get("year"))

                label = w["make"]
                if w.get("model"):
                    label += f" {w['model']}"
                if w.get("year"):
                    label += f" {w['year']}"

                if not listings:
                    logger.warning("yad2_watch: no results for watch id=%s (%s)", w["id"], label)
                    continue

                current_ids = {item["id"] for item in listings}
                seen = set(w["seen_ids"])

                # First run: seed seen_ids so we don't flood with old listings
                if not seen:
                    await update_seen_ids(w["id"], list(current_ids)[-500:])
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"🔍 *מעקב יד2 הופעל בהצלחה\\!*\n\n"
                        f"🚗 *{_escape_md(label)}*\n"
                        f"✅ נמצאו {len(current_ids)} מודעות תואמות קיימות\\.\n"
                        f"מעתה תקבל התראה בכל פעם שתתווסף מודעה חדשה\\.\n\n"
                        f"_שים לב: קבלת ההתראות תלויה בזמינות השירות ועשויה להתעכב\\. "
                        f"המידע מסופק כשירות בלבד ואינו מובטח כמלא או מעודכן בזמן אמת\\._",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                    continue

                new_ids = current_ids - seen
                search_url = _yad2.build_search_url(w["make"], w.get("model", ""), w.get("year"))

                if not new_ids:
                    pass  # nothing new — stay silent
                else:
                    new_listings = [item for item in listings if item["id"] in new_ids]
                    # Yad2 returns listings newest-first; take the first new item
                    top = new_listings[0] if new_listings else None
                    count = len(new_listings)
                    prices = sorted([int(x["price"]) for x in new_listings if x.get("price")])
                    if prices:
                        price_range = f"₪{prices[0]:,}" if len(prices) == 1 else f"₪{prices[0]:,} – ₪{prices[-1]:,}"
                    else:
                        price_range = "מחיר לא צוין"

                    count_word = "מודעה חדשה" if count == 1 else "מודעות חדשות"

                    top_price = f"₪{int(top['price']):,}" if top and top.get("price") else "מחיר לא צוין"
                    top_details = "  ".join(filter(None, [
                        f"🛣️ {int(top['km']):,} ק\"מ" if top and top.get("km") else None,
                        f"📍 {top['city']}" if top and top.get("city") else None,
                    ])) if top else ""
                    top_link = top.get("link", "") if top else ""

                    # Primary CTA: direct link to newest item if token available, else search page
                    if top_link:
                        cta = f"[🆕 פתח את המודעה החדשה ביותר]({top_link})"
                        all_link = f"\n[ראה את כל {count} המודעות ביד2]({search_url})" if count > 1 else ""
                    else:
                        cta = f"[🆕 ראה את המודעות החדשות ביד2]({search_url})"
                        all_link = ""

                    text = (
                        f"👋 היי\\! מצאנו *{count} {_escape_md(count_word)}* שמתאימות לחיפוש שלך\\.\n\n"
                        f"🚗 *{_escape_md(label)}*\n"
                        f"💰 {_escape_md(top_price)}"
                        + (f"\n{_escape_md(top_details)}" if top_details else "")
                        + f"\n\n{cta}{all_link}"
                    )
                    try:
                        await context.bot.send_message(
                            w["user_id"], text,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        await log_sent_message(w["user_id"], f"🔔 התראת מעקב יד2: {label} — {count} מודעות חדשות", kind="watch_alert")
                    except Exception as e:
                        logger.warning("Watch notify failed user=%s: %s", w["user_id"], e)

                    all_seen = list(seen | current_ids)[-500:]
                    await update_seen_ids(w["id"], all_seen)

            except Exception as e:
                logger.error("Watch check error id=%s: %s", w["id"], e)
                try:
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"⚠️ *שגיאה בבדיקת מעקב* id={w['id']}: {_escape_md(str(e))}",
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
                except Exception:
                    pass
    except Exception as e:
        logger.error("Yad2 watcher job error: %s", e)


async def _post_init(app) -> None:
    await init_db()
    await load_welcome_settings()
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    try:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="פתח אפליקציה",
                web_app=WebAppInfo(url=webapp_url),
            )
        )
        logger.info("Menu button set to %s", webapp_url)
    except Exception as e:
        logger.warning("Could not set menu button: %s", e)
    logger.info("Turso DB initialized")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    def _start_api():
        import uvicorn
        from api import api as fastapi_app
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(fastapi_app, host="0.0.0.0", port=port, log_level="warning")

    Thread(target=_start_api, daemon=True).start()
    Thread(target=lambda: asyncio.run(_cache_cleanup_job()), daemon=True).start()
    logger.info("API server starting on port %s", os.environ.get("PORT", 8080))

    app = Application.builder().token(token).post_init(_post_init).build()
    global _bot_instance
    _bot_instance = app.bot
    # Register the payment notifier so api.py can notify admin without importing bot
    from src.notifier import register_payment_notifier
    register_payment_notifier(_notify_admin_payment)
    from src.notifier import register_ticket_notifiers
    register_ticket_notifiers(_notify_admin_ticket, _notify_user_ticket_reply)

    async def _notify_payment_approved(user_id: int, label: str, searches: int):
        try:
            desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
            approved_msg = f"✅ תשלומך אושר! {label} — {desc} נוספו לחשבונך"
            await app.bot.send_message(
                user_id,
                f"✅ *תשלומך אושר!*\n📦 {label}\n🔍 {desc} נוספו לחשבונך",
                parse_mode="Markdown"
            )
            await log_sent_message(user_id, approved_msg, kind="payment")
        except Exception:
            pass

    async def _notify_payment_declined(user_id: int, label: str):
        try:
            declined_msg = f"❌ בקשת התשלום נדחתה — {label}"
            await app.bot.send_message(
                user_id,
                f"❌ *בקשת התשלום נדחתה*\n📦 {label}\nלפרטים פנה לתמיכה.",
                parse_mode="Markdown"
            )
            await log_sent_message(user_id, declined_msg, kind="payment")
        except Exception:
            pass

    from src.notifier import register_payment_result_notifiers
    register_payment_result_notifiers(_notify_payment_approved, _notify_payment_declined)

    async def _do_broadcast(message: str) -> dict:
        from src.users import get_all_users
        users = await get_all_users()
        sent = failed = 0
        for u in users:
            uid = u.get("user_id")
            if not uid or uid == ADMIN_ID:
                continue
            try:
                await app.bot.send_message(uid, message)
                await log_sent_message(uid, message, kind="broadcast")
                sent += 1
            except Exception:
                failed += 1
        return {"ok": True, "sent": sent, "failed": failed}

    async def _notify_admin_grant(user_id: int, searches: int, expires: str = ""):
        try:
            msg = _format_grant_message(searches, expires)
            await app.bot.send_message(user_id, msg, parse_mode="Markdown")
            await log_sent_message(user_id, msg, kind="grant")
        except Exception:
            pass

    from src.notifier import register_admin_grant_notifier
    register_admin_grant_notifier(_notify_admin_grant)

    from src.notifier import register_broadcast_notifier
    register_broadcast_notifier(_do_broadcast)

    async def _send_message_to_user(user_id: int, message: str) -> bool:
        try:
            await app.bot.send_message(user_id, message)
            await log_sent_message(user_id, message, kind="admin_dm")
            return True
        except Exception as e:
            logger.warning("Failed to send message to user %s: %s", user_id, e)
            return False

    from src.notifier import register_user_message_notifier
    register_user_message_notifier(_send_message_to_user)

    async def _do_broadcast_photo(message: str, image_b64: str) -> dict:
        import base64, io as _io
        from src.users import get_all_users
        users = await get_all_users()
        sent = failed = 0
        try:
            header, _, data = image_b64.partition(",")
            photo_bytes = base64.b64decode(data if data else image_b64)
        except Exception:
            photo_bytes = None
        for u in users:
            uid = u.get("user_id")
            if not uid or uid == ADMIN_ID or u.get("blocked"):
                continue
            try:
                if photo_bytes:
                    await app.bot.send_photo(
                        uid,
                        photo=_io.BytesIO(photo_bytes),
                        caption=message,
                        parse_mode="Markdown",
                    )
                else:
                    await app.bot.send_message(uid, message, parse_mode="Markdown")
                await log_sent_message(uid, message, kind="broadcast")
                sent += 1
            except Exception:
                failed += 1
        return {"ok": True, "sent": sent, "failed": failed}

    from src.notifier import register_broadcast_photo_notifier
    register_broadcast_photo_notifier(_do_broadcast_photo)

    STATUS_HE = {
        'created':   '🆕 הזמנה חדשה',
        'approved':  '✅ אושר בפייפאל',
        'captured':  '💳 חיוב בוצע',
        'completed': '🎉 הושלם',
        'failed':    '❌ נכשל',
        'expired':   '🚫 פג תוקף',
        'declined':  '🚫 נדחה',
        'cancelled':        '↩️ בוטל',
        'user_cancelled':   '↩️ בוטל על ידי המשתמש',
        'admin_approved':   '✅ אושר ע״י מנהל',
        'admin_cancelled':  '🚫 בוטל ע״י מנהל',
    }

    async def _notify_admin_order(ref, status, label, amount, username, member_id):
        if not ADMIN_ID:
            return
        status_txt = STATUS_HE.get(status, status)
        user_txt = f"@{username}" if username else f"חבר #{member_id}" if member_id else ref.split('-')[0]
        text = (
            f"{status_txt}\n"
            f"🔖 הזמנה: `{ref}`\n"
            f"👤 משתמש: {user_txt}  #{member_id or '—'}\n"
            f"📦 מוצר: {label}\n"
            f"💰 סכום: ₪{amount}"
        )
        try:
            await app.bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
        except Exception:
            pass

    from src.notifier import register_admin_order_notifier
    register_admin_order_notifier(_notify_admin_order)

    async def _send_user_document(user_id: int, pdf_bytes: bytes, filename: str, caption: str = "") -> bool:
        import io as _io
        try:
            await app.bot.send_document(
                chat_id=user_id,
                document=_io.BytesIO(pdf_bytes),
                filename=filename,
                caption=caption,
            )
            return True
        except Exception:
            return False

    from src.notifier import register_user_document_sender
    register_user_document_sender(_send_user_document)

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
    app.add_handler(CallbackQueryHandler(handle_admpkg_callback,  pattern=r"^admpkg\|"))
    app.add_handler(CallbackQueryHandler(handle_how_it_works,    pattern=r"^how_it_works$"))
    app.add_handler(CallbackQueryHandler(handle_back_to_start,   pattern=r"^back_to_start$"))
    app.add_handler(CallbackQueryHandler(handle_history,         pattern=r"^(history|hist_plate\|.*)$"))
    app.add_handler(CallbackQueryHandler(handle_pdf_callback,      pattern=r"^pdf_report$"))
    app.add_handler(CallbackQueryHandler(handle_share_callback,   pattern=r"^share_report$"))
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
        "🛠 פאנל מנהל", "🔍 חזור לחיפוש", "❌ ביטול", "💰 מחירי חבילות",
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

    async def _send_expiry_reminders(context, days: int):
        messages = {
            30: (
                "📅 *תזכורת: חודש להתחדשות המנוי*\n\n"
                "המנוי שלך יפוג בעוד חודש\\. "
                "כדי להמשיך ליהנות מחיפושים ללא הגבלה, ניתן לחדש את המנוי מראש\\."
            ),
            7: (
                "⚠️ *תזכורת: שבוע להתחדשות המנוי*\n\n"
                "המנוי שלך יפוג בעוד שבוע\\. "
                "ניתן לחדש את המנוי כדי להמשיך ליהנות מהשירות ללא הפסקה\\."
            ),
            1: (
                "🔴 *תזכורת: המנוי שלך יפוג מחר\\!*\n\n"
                "מחר הוא היום האחרון של המנוי שלך\\. "
                "ניתן לחדש את המנוי עוד היום\\."
            ),
            0: (
                "⏰ *המנוי שלך פג היום\\!*\n\n"
                "המנוי שלך פג\\. "
                "כדי להמשיך ליהנות מהשירות, ניתן לרכוש חבילת חיפושים\\."
            ),
        }
        text = messages[days]
        try:
            user_ids = await get_users_expiring_in_days(days)
            for uid in user_ids:
                try:
                    await context.bot.send_message(uid, text, parse_mode=ParseMode.MARKDOWN_V2)
                    await log_sent_message(uid, text, kind="expiry_reminder")
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Expiry reminder job (days=%d) error: %s", days, e)

    if app.job_queue:
        import datetime as _dt
        # 9:00 Israel time = 06:00 UTC (UTC+3 in summer)
        _notify_time = _dt.time(hour=6, minute=0, tzinfo=_dt.timezone.utc)
        for _days in (30, 7, 1, 0):
            _d = _days
            app.job_queue.run_daily(
                lambda ctx, d=_d: _send_expiry_reminders(ctx, d),
                time=_notify_time,
                name=f"expiry_notify_{_days}d",
            )
        app.job_queue.run_repeating(
            _yad2_watch_job,
            interval=30 * 60,
            first=90,
            name="yad2_watch",
        )

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
