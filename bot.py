"""
CarInfo Bot – Israel vehicle lookup Telegram bot.
"""

import asyncio
import io
import logging
import os
import re
import sys
import time
from threading import Thread


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, WebAppInfo
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, TypeHandler,
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
    load_welcome_settings, get_promo_welcome_info, get_users_expiring_in_days,
    expire_subscriptions,
    log_sent_message,
    set_broadcast_consent, get_broadcast_consent,
)
from src.rich import send_rich_message, rich_enabled
from src import reminders as _rem
from src import mirror
from src.formatter import (
    quick_summary_rich,
    compare_rich,
    compare_classic,
    get_share_text,
    quick_summary,
)
from src import messages as M
from src.pdf_report import generate_pdf
from src import yad2 as _yad2

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
# httpx logs every request URL at INFO, which includes the Telegram bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

PLATE_RE  = re.compile(r"^[\d\-]{5,10}$")
COMPARE_TTL = 600  # seconds the "second plate" prompt stays armed
MAX_REMINDERS_PER_USER = 20
ADMIN_ID  = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))
BOT_USERNAME = "israelcarinfobot"
PAYMENT_PROVIDER_TOKEN = os.environ.get("PAYMENT_PROVIDER_TOKEN", "6073714100:TEST:TG_2ZwhGNC5yAq7J6bMbZfUti0A")
PAYPAL_ME  = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")
PAYBOX_URL = os.environ.get("PAYBOX_URL", "https://links.payboxapp.com/xjZpYBP2n3b")

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

HTML = ParseMode.HTML

logger.info("ADMIN_ID loaded: %s", ADMIN_ID)

# Optional admin-authored (plain text) replacement for the default payment wall copy.
PAYMENT_MSG: str | None = None


def _first_name(user) -> str:
    """First name of a Telegram user object, for personal greetings."""
    return M.first_name(getattr(user, "first_name", None) or getattr(user, "full_name", "") or "")


async def _name_of(user_id: int) -> str:
    """First name of any user by id (for notifications that only carry a user_id)."""
    try:
        u = await get_user_by_id(user_id)
    except Exception:
        u = None
    return M.first_name((u or {}).get("full_name", ""))


def _log_text(html_text: str) -> str:
    return M.strip_html(html_text)

WAITING_CODE = 1

def _persistent_rows(is_admin: bool = False) -> list:
    """Bottom row shown in every chat keyboard — search + mini-app shortcut."""
    webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
    return [
        [
            InlineKeyboardButton("🔍 חיפוש רכב חדש", callback_data="new_search", style="success"),
            InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=webapp_url), style="primary"),
        ],
    ]


def _persistent_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(_persistent_rows(is_admin))


def _payment_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
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
    webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
    plate = record.get("mispar_rechev", "") if record else ""
    first_row = []
    if plate:
        first_row.append(InlineKeyboardButton(
            "📊 צפה בדוח המלא והורדה",
            web_app=WebAppInfo(url=f"{webapp_url}/?plate={plate}"),
        ))
    rows = [first_row] if first_row else []
    if plate:
        rows.append([
            InlineKeyboardButton("🔔 תזכורת טסט", callback_data=f"rem|add|{plate}"),
            InlineKeyboardButton("⚖️ השוואה", callback_data=f"cmp|start|{plate}"),
        ])
        rows.append([
            InlineKeyboardButton("👀 מעקב מודעות", web_app=WebAppInfo(url=f"{webapp_url}/?page=watches")),
            InlineKeyboardButton("📤 שתף", callback_data="share_report"),
        ])
    rows.extend(_persistent_rows(is_admin))
    return InlineKeyboardMarkup(rows)



def _paypal_keyboard(searches: int, price: int) -> InlineKeyboardMarkup:
    paypal_url = f"{PAYPAL_ME}/{price}"
    webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
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
        f"🆔 Your ID: {M.code(uid)}\n👑 Admin: {M.code(is_admin)}\n⚙️ ADMIN_ID set to: {M.code(ADMIN_ID)}",
        parse_mode=HTML,
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
                    M.admin_chat_request(uname, fullname, user_id),
                    parse_mode=HTML,
                )
            except Exception as e:
                logger.warning("Failed to notify admin: %s", e)
        sent = await update.message.reply_text(
            M.admin_chat_sent(_first_name(user)),
            parse_mode=HTML,
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
                    M.admin_buy_request(uname, fullname, user_id),
                    parse_mode=HTML,
                )
            except Exception as e:
                logger.warning("Failed to notify admin: %s", e)
        await update.message.reply_text(
            M.purchase_request_received(_first_name(user)),
            parse_mode=HTML,
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
            stats = await admin_stats()
            uname = f"@{user.username}" if user.username else f"id:{user_id}"
            await context.bot.send_message(
                ADMIN_ID,
                M.admin_new_user(uname, user.full_name or "", user_id, stats["total_users"]),
                parse_mode=HTML,
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
                duration     = promo_info['duration_days']
                expires_str  = promo_info.get('expires_str', '')
                if duration and duration > 0:
                    duration_text = f"לתקופה של {duration} ימים"
                else:
                    duration_text = "ללא הגבלת זמן"
                expires_text = f" (עד {expires_str})" if expires_str else ""
                promo_msg = M.promo_welcome(_first_name(user), promo_info['label'], duration_text, expires_text)
                await context.bot.send_message(user_id, promo_msg, parse_mode=HTML)
                await log_sent_message(user_id, _log_text(promo_msg), kind="promo_welcome")
            except Exception as e:
                logger.warning("Failed to send promo welcome: %s", e)

    if not is_new and referrer_id:
        try:
            ref_uname = f"@{user.username}" if user.username else str(user_id)
            ref_info_msg = M.referral_rejected(await _name_of(referrer_id), ref_uname)
            await context.bot.send_message(referrer_id, ref_info_msg, parse_mode=HTML)
            await log_sent_message(referrer_id, _log_text(ref_info_msg), kind="referral_info")
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
            referral_msg = M.referral_bonus(await _name_of(referrer_id), ref_uname, bonus)
            try:
                await context.bot.send_message(referrer_id, referral_msg, parse_mode=HTML)
                await log_sent_message(referrer_id, _log_text(referral_msg), kind="referral_bonus")
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
                M.blocked(_first_name(user)),
                parse_mode=HTML,
                reply_markup=_blocked_keyboard(),
            )
        else:
            await update.message.reply_text(
                M.payment_required(_first_name(user), PAYMENT_MSG),
                parse_mode=HTML,
                reply_markup=_payment_keyboard(),
            )
        return

    expires = None
    if left == -1:
        from src.users import get_quota_expires
        expires = await get_quota_expires(user_id)

    welcome_text = M.welcome(_first_name(user), M.quota_line(left, expires), is_new=is_new)
    await update.message.reply_text(
        welcome_text,
        parse_mode=HTML,
        reply_markup=_welcome_keyboard(is_admin),
    )
    await log_sent_message(user_id, _log_text(welcome_text), kind="welcome")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        M.help_text(_first_name(update.effective_user)),
        parse_mode=HTML,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    allowed, left = await is_allowed(user.id)
    expires = None
    if left == -1:
        from src.users import get_quota_expires
        expires = await get_quota_expires(user.id)
    await update.message.reply_text(
        M.status(_first_name(user), left if allowed else 0, expires),
        parse_mode=HTML,
    )


async def cmd_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text(M.code_usage(), parse_mode=HTML)
        return
    code = args[0].strip().upper()
    success, result = await apply_code(user.id, code)
    name = _first_name(user)
    await update.message.reply_text(
        M.code_applied(name, result) if success else M.code_rejected(name, result),
        parse_mode=HTML,
    )


async def cb_enter_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()
    await query.edit_message_text(
        M.enter_code_prompt(_first_name(query.from_user)),
        parse_mode=HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 פתח תפריט", web_app=WebAppInfo(url=os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")))],
        ]),
    )
    context.user_data["code_is_admin"] = is_admin
    return WAITING_CODE


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user     = update.effective_user
    user_id  = user.id
    is_admin = context.user_data.pop("code_is_admin", user_id == ADMIN_ID)
    code     = update.message.text.strip().upper()
    success, result = await apply_code(user_id, code)
    name = _first_name(user)
    if success:
        await update.message.reply_text(
            M.code_applied(name, result),
            parse_mode=HTML,
            reply_markup=_persistent_keyboard(is_admin),
        )
        await log_sent_message(user_id, f"✅ קוד הופעל: {result}", kind="code_applied")
    else:
        await update.message.reply_text(
            M.code_rejected(name, result),
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                *_persistent_rows(is_admin),
            ]),
        )
    return ConversationHandler.END


async def cancel_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    context.user_data.pop("code_is_admin", None)
    await update.message.reply_text(M.search_cancelled(), reply_markup=ReplyKeyboardRemove())
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


def _admin_settings_keyboard(maintenance_on: bool = False, rich_on: bool = False,
                             reminders_on: bool = False, garage_sync_on: bool = False,
                             mirror_on: bool = False) -> InlineKeyboardMarkup:
    maint_label = "🔴 בטל תחזוקה" if maintenance_on else "🔧 הפעל תחזוקה"
    maint_style = "danger" if maintenance_on else None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ שנה הודעת תשלום",         callback_data="adm|set_payment")],
        [InlineKeyboardButton("🆓 שנה מספר בדיקות חינמיות", callback_data="adm|set_free")],
        [InlineKeyboardButton(maint_label,                   callback_data="adm|toggle_maintenance", style=maint_style)],
        [InlineKeyboardButton("📊 כבה תוצאה כטבלה" if rich_on else "📊 הפעל תוצאה כטבלה", callback_data="adm|toggle_rich")],
        [InlineKeyboardButton("🔔 כבה תזכורות טסט" if reminders_on else "🔔 הפעל תזכורות טסט", callback_data="adm|toggle_reminders")],
        [InlineKeyboardButton("🚗 כבה תזכורת אוטומטית למוסך" if garage_sync_on else "🚗 הפעל תזכורת אוטומטית למוסך", callback_data="adm|toggle_garage_sync")],
        [InlineKeyboardButton("🪞 כבה מראה פעולות" if mirror_on else "🪞 הפעל מראה פעולות", callback_data="adm|toggle_mirror")],
        [InlineKeyboardButton("🔙 חזרה",                     callback_data="adm|main")],
    ])


async def _settings_view() -> tuple[str, InlineKeyboardMarkup]:
    import src.users as _u
    maintenance = (await get_bot_setting("maintenance")) == "1"
    rich_on     = (await get_bot_setting("rich_messages_enabled")) == "1"
    reminders   = (await get_bot_setting("test_reminders_enabled")) == "1"
    garage_sync = (await get_bot_setting("test_reminders_garage_sync")) == "1"
    mirror_on   = (await get_bot_setting("mirror_enabled")) == "1"
    mirror_bound = bool(await get_bot_setting("mirror_chat_id"))
    return (
        M.admin_settings(_u.FREE_SEARCHES, maintenance, rich_on, reminders, garage_sync, mirror_on, mirror_bound),
        _admin_settings_keyboard(maintenance, rich_on, reminders, garage_sync, mirror_on),
    )


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
                await update.message.reply_text("🔢 הכמות חייבת להיות מספר.")
                return
            target = await get_user_by_username(username)
            if not target and username.isdigit():
                target = await get_user_by_id(int(username))
            if not target:
                await update.message.reply_text("🔍 משתמש לא נמצא. נסה עם ה-ID המספרי במקום ה-username.")
                return
            note = " ".join(args[3:]) if len(args) > 3 else ""
            msg = await admin_grant(user_id, target["user_id"], amount, note)
            await update.message.reply_text(f"✅ {username}: {msg}")
            # Notify user
            try:
                user_msg = M.grant_cmd(M.first_name(target.get("full_name", "")), amount, msg)
                await context.bot.send_message(target["user_id"], user_msg, parse_mode=HTML)
                await log_sent_message(target["user_id"], _log_text(user_msg), kind="grant")
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
                f"✅ קוד חדש ({M.esc(kind)}, {use_str}):\n{M.code(code)}",
                parse_mode=HTML,
            )
            return

    stats = await admin_stats()
    await update.message.reply_text(
        M.admin_panel(_first_name(update.effective_user), stats),
        parse_mode=HTML,
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
            M.admin_panel(_first_name(query.from_user), stats),
            parse_mode=HTML,
            reply_markup=_admin_main_keyboard(),
        )
        return

    if action == "stats":
        stats = await admin_stats()
        await query.edit_message_text(
            M.admin_stats_detail(stats),
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    if action == "users":
        users = await get_all_users()
        if not users:
            await query.edit_message_text(
                "👥 אין משתמשים עדיין.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
            )
            return
        lines = [f"👥 {M.b('משתמשים')} (מסודר לפי בדיקות)\n\n"]
        for u in users[:25]:
            uname    = f"@{u['username']}" if u.get("username") else ""
            fullname = u.get("full_name", "")
            display  = " | ".join(filter(None, [uname, fullname])) or f"id:{u['user_id']}"
            done     = u.get("searches_done", 0)
            quota    = u.get("searches_quota", 0)
            left     = u.get("searches_left", 0)
            quota_str = "∞" if quota == -1 else str(quota)
            left_str  = "∞" if left  == -1 else str(left)
            lines.append(f"• {M.esc(display)}: {done}/{quota_str} (נותרו: {left_str})\n")
        await query.edit_message_text(
            "".join(lines),
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    if action == "gen_menu":
        await query.edit_message_text(
            f"🔑 {M.b('יצירת קוד גישה')}\n\nבחר כמות בדיקות לקוד:",
            parse_mode=HTML,
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
            f"✅ {M.b('קוד חדש נוצר')}\n\n"
            f"סוג: {M.esc(kind)} | {use_str}\n\n"
            f"{M.code(code)}\n\n"
            f"{M.i('העתק את הקוד ושלח ללקוח')}",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 צור קוד נוסף", callback_data="adm|gen_menu")],
                [InlineKeyboardButton("🔙 ראשי",          callback_data="adm|main")],
            ]),
        )
        return

    if action == "grant_info":
        await query.edit_message_text(
            f"💳 {M.b('הענקת גישה למשתמש')}\n\n"
            "שלח פקודה בפורמט:\n"
            f"{M.code('/admin grant @username 50')}\n\n"
            "לגישה בלתי מוגבלת:\n"
            f"{M.code('/admin grant @username -1')}",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    toggles = {
        "toggle_maintenance": "maintenance",
        "toggle_rich": "rich_messages_enabled",
        "toggle_reminders": "test_reminders_enabled",
        "toggle_garage_sync": "test_reminders_garage_sync",
        "toggle_mirror": "mirror_enabled",
    }
    if action == "settings" or action in toggles:
        if action in toggles:
            key = toggles[action]
            cur = await get_bot_setting(key)
            await set_bot_setting(key, "0" if cur == "1" else "1")
            mirror.invalidate()
        text, kb = await _settings_view()
        await query.edit_message_text(text, parse_mode=HTML, reply_markup=kb)
        return

    if action == "set_payment":
        await query.message.reply_text(
            f"✏️ {M.b('שינוי הודעת תשלום')}\n\nשלח את הטקסט החדש (טקסט פשוט — אני אוסיף ברכה אישית עם שם המשתמש):",
            parse_mode=HTML,
        )
        context.user_data["admin_setting"] = "payment_msg"
        return

    if action == "set_free":
        import src.users as _u
        await query.message.reply_text(
            f"🆓 {M.b('שינוי בדיקות חינמיות')}\n\nהערך הנוכחי: {M.b(_u.FREE_SEARCHES)}\n\nשלח את המספר החדש:",
            parse_mode=HTML,
        )
        context.user_data["admin_setting"] = "free_count"
        return

    if action == "block_menu":
        users = await get_all_users()
        if not users:
            await query.edit_message_text(
                "👥 אין משתמשים עדיין.",
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
            M.ADMIN_BLOCK_LIST,
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action == "block":
        target_id = int(parts[2])
        await block_user(target_id)
        try:
            block_msg = M.blocked(await _name_of(target_id))
            await context.bot.send_message(target_id, block_msg, parse_mode=HTML)
            await log_sent_message(target_id, _log_text(block_msg), kind="block")
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
            M.ADMIN_BLOCK_LIST,
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action == "unblock":
        target_id = int(parts[2])
        await unblock_user(target_id)
        try:
            unblock_msg = M.unblocked(await _name_of(target_id))
            await context.bot.send_message(target_id, unblock_msg, parse_mode=HTML)
            await log_sent_message(target_id, _log_text(unblock_msg), kind="unblock")
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
            M.ADMIN_BLOCK_LIST,
            parse_mode=HTML,
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
        name = _first_name(query.from_user)
        searching_msg = await query.message.reply_text(f"🔍 {M.esc(name)}, מחפש נתונים...")
        try:
            record = await fetch_vehicle_data(plate)
        except Exception as exc:
            await searching_msg.delete()
            await query.message.reply_text(M.lookup_error(name), parse_mode=HTML)
            return
        await searching_msg.delete()
        if not record:
            await query.message.reply_text(M.not_found(name, plate), parse_mode=HTML)
            return
        context.user_data["last_record"] = record
        context.user_data["last_share_text"] = get_share_text(record)
        card = M.result_intro(name, plate) + quick_summary(record)
        yad2_link = _yad2.build_url(record)
        await query.message.reply_text(
            card,
            parse_mode=HTML,
            reply_markup=build_result_keyboard(is_admin=is_admin, record=record, yad2_link=yad2_link),
        )
        return

    # Show history list
    history = await get_search_history(user_id, limit=10)
    if not history:
        await query.edit_message_text(
            M.history_empty(_first_name(query.from_user)),
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 חזרה", callback_data="back_to_start")
            ]])
        )
        return

    buttons = []
    for plate in history:
        buttons.append([InlineKeyboardButton(f"🚗 {plate}", callback_data=f"hist_plate|{plate}")])
    buttons.append([InlineKeyboardButton("🔙 חזרה", callback_data="back_to_start")])

    if await rich_enabled():
        from src.users import get_search_history_rows
        rows = await get_search_history_rows(user_id, limit=10)
        body = "".join(
            f"<tr><td>{M.esc(plate)}</td><td>{M.esc(M.fmt_date(when))}</td></tr>" for plate, when in rows
        )
        html = (
            f"<p>{M.history_table_intro(_first_name(query.from_user))}</p>"
            f"<table bordered striped><tr><th>לוחית</th><th>חיפוש אחרון</th></tr>{body}</table>"
            f"<p><i>לחץ על מספר רכב כדי לצפות שוב — בלי לנכות בדיקה</i></p>"
        )
        if await send_rich_message(query.message.chat_id, html, reply_markup=InlineKeyboardMarkup(buttons)):
            try:
                await query.message.delete()   # the table message replaces the menu
            except Exception:
                pass
            return

    await query.edit_message_text(
        M.history_list(_first_name(query.from_user)),
        parse_mode=HTML,
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
    expires = None
    if quota == -1:
        left = -1
        try:
            expires = await get_quota_expires(user_id)
        except Exception:
            expires = None

    await query.edit_message_text(
        M.welcome(_first_name(query.from_user), M.quota_line(left, expires)),
        parse_mode=HTML,
        reply_markup=_welcome_keyboard(is_admin),
    )


async def handle_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import src.users as _u
    query    = update.callback_query
    is_admin = query.from_user.id == ADMIN_ID
    await query.answer()

    pkg_lines = [f"• {M.esc(label)} – ₪{price}" for label, _searches, price in _pkgs()]
    pkg_text = "\n".join(pkg_lines) if pkg_lines else "אין חבילות זמינות כרגע"
    await query.edit_message_text(
        M.how_it_works(_first_name(query.from_user), _u.FREE_SEARCHES, pkg_text),
        parse_mode=HTML,
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
        webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
        await query.edit_message_text(
            M.packages_intro(_first_name(user)),
            parse_mode=HTML,
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
            msg = M.grant_update(await _name_of(uid), amount, expires)
            await context.bot.send_message(uid, msg, parse_mode=HTML)
            await log_sent_message(uid, _log_text(msg), kind="grant")
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
                unblock_msg = M.unblocked(await _name_of(uid))
                await context.bot.send_message(uid, unblock_msg, parse_mode=HTML)
                await log_sent_message(uid, _log_text(unblock_msg), kind="block")
            except Exception:
                pass
        else:
            await block_user(uid)
            await query.answer("🚫 נחסם", show_alert=True)
            try:
                block_msg = M.blocked(await _name_of(uid))
                await context.bot.send_message(uid, block_msg, parse_mode=HTML)
                await log_sent_message(uid, _log_text(block_msg), kind="block")
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
        await update.message.reply_text(M.admin_stats_short(stats), parse_mode=HTML)

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
            await update.message.reply_text("👥 אין משתמשים עדיין.")
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
            M.ADMIN_BLOCK_LIST,
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    async def send_gen_menu():
        await update.message.reply_text(
            f"🔑 {M.b('יצירת קוד גישה')}\n\nבחר כמות:",
            parse_mode=HTML,
            reply_markup=_admin_gen_keyboard(),
        )

    async def send_grant_info():
        await update.message.reply_text(
            f"💳 {M.b('הענקת גישה')}\n\nשלח:\n{M.code('/admin grant @username 50')}\n\nלגישה בלתי מוגבלת:\n{M.code('/admin grant @username -1')}",
            parse_mode=HTML,
        )

    async def send_settings():
        text, kb = await _settings_view()
        await update.message.reply_text(text, parse_mode=HTML, reply_markup=kb)

    async def send_broadcast_prompt():
        await update.message.reply_text(
            f"📢 {M.b('שליחת הודעה לכולם')}\n\nשלח את ההודעה שתרצה להפיץ (טקסט פשוט — כל משתמש יקבל אותה עם ברכה אישית בשמו):",
            parse_mode=HTML,
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
            f"💰 {M.b('עריכת מחירי חבילות')}\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=HTML,
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
            M.admin_panel(_first_name(update.effective_user), stats),
            parse_mode=HTML,
            reply_markup=_admin_main_keyboard(),
        )
        return
    if text_msg == "🔍 חזור לחיפוש":
        await update.message.reply_text(
            M.ask_plate(_first_name(update.effective_user)),
            parse_mode=HTML,
            reply_markup=_cancel_search_keyboard(),
        )
        return
    if text_msg == "❌ ביטול":
        await update.message.reply_text(M.search_cancelled(), reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=True))
        return
    fn = dispatch.get(text_msg)
    if fn:
        await fn()


async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the Mini App for purchasing packages."""
    webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
    from telegram import WebAppInfo
    await update.message.reply_text(
        M.buy_intro(_first_name(update.effective_user)),
        parse_mode=HTML,
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
        M.package_details(_first_name(query.from_user), label, desc, price),
        parse_mode=HTML,
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
                M.admin_payment_request(f"{uname} | {fullname}", user_id, label, price),
                parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ אשר ופתח גישה", callback_data=f"approve|{user_id}|{searches}", style="success"),
                    InlineKeyboardButton("❌ דחה", callback_data=f"decline|{user_id}", style="danger"),
                ]]),
            )
        except Exception as e:
            logger.warning("Failed to notify admin of payment: %s", e)

    await query.edit_message_text(
        M.payment_request_sent(_first_name(user)),
        parse_mode=HTML,
    )


_bot_instance = None  # set in main(), used by API server


async def _notify_admin_ticket(ticket_id: int, user_id: int, name: str, subject: str, message: str):
    try:
        text = M.admin_ticket(ticket_id, name, user_id, subject, message)
        webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
        from telegram import WebAppInfo
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎫 פתח טיקט", web_app=WebAppInfo(url=f"{webapp_url}/?page=admin_ticket&id={ticket_id}"))
        ]])
        await _bot_instance.send_message(ADMIN_ID, text, parse_mode=HTML, reply_markup=kb)
    except Exception:
        pass


async def _notify_user_ticket_reply(user_id: int, ticket_id: int, subject: str, reply: str):
    try:
        webapp_url = os.environ.get("WEBAPP_URL") or os.environ.get("RENDER_EXTERNAL_URL", "https://carinfo-bot.onrender.com")
        from telegram import WebAppInfo
        text = M.ticket_reply(await _name_of(user_id), subject, reply)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📂 פתח פנייה", web_app=WebAppInfo(url=f"{webapp_url}/?page=ticket&id={ticket_id}"))
        ]])
        await _bot_instance.send_message(user_id, text, parse_mode=HTML, reply_markup=kb)
        await log_sent_message(user_id, _log_text(text), kind="ticket_reply")
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
            user_msg = M.payment_approved_simple(await _name_of(target), searches)
            await context.bot.send_message(target, user_msg, parse_mode=HTML)
            await log_sent_message(target, _log_text(user_msg), kind="payment")
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
        decline_msg = M.payment_declined(await _name_of(target))
        await context.bot.send_message(target, decline_msg, parse_mode=HTML)
        await log_sent_message(target, _log_text(decline_msg), kind="payment")
    except Exception:
        pass


async def handle_deliver_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin taps 'שלח תוכן משלוח' on a pending-delivery product order — prompt
    for the content, then handle_plate's admin_setting=='deliver_content' branch
    picks up the reply and calls src.products.deliver_order()."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    ref = query.data.split("|", 1)[1]
    context.user_data["admin_setting"] = "deliver_content"
    context.user_data["admin_deliver_ref"] = ref
    await query.message.reply_text(f"✍️ שלח את תוכן המשלוח עבור הזמנה {M.code(ref)}:", parse_mode=HTML)


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
    paid_msg = M.payment_received(_first_name(update.effective_user), searches, amount_ils)
    await update.message.reply_text(paid_msg, parse_mode=HTML, reply_markup=ReplyKeyboardRemove())
    await log_sent_message(user_id, _log_text(paid_msg), kind="payment")

    # Notify admin
    uname = f"@{update.effective_user.username}" if update.effective_user.username else f"id:{user_id}"
    try:
        await context.bot.send_message(
            ADMIN_ID,
            M.admin_payment_received(uname, searches, amount_ils),
            parse_mode=HTML,
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
            f"💰 {M.b('עריכת מחירי חבילות')}\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup(_pkg_buttons(pkgs)),
        )

    elif action == "pick":
        pkg_id = int(parts[2])
        pkgs   = await get_packages()
        pkg    = next((p for p in pkgs if p[0] == pkg_id), None)
        if not pkg:
            await query.edit_message_text("❌ חבילה לא נמצאה.")
            return
        pid, label, searches, price = pkg
        desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
        await query.edit_message_text(
            f"📦 {M.b(label)}\n\n{M.esc(desc)} · ₪{price}\n\nמה לעשות?",
            parse_mode=HTML,
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
            f"✅ {M.b('החבילה נמחקה')}\n\nבחר חבילה לעריכה או הוסף חדשה:",
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup(_pkg_buttons(pkgs)),
        )

    elif action == "startedit":
        pkg_id = int(parts[2])
        context.user_data["admin_setting"]  = "pkg_edit_searches"
        context.user_data["admin_pkg_id"]   = pkg_id
        await query.edit_message_text(
            f"✏️ {M.b('עריכת חבילה')}\n\nכמה חיפושים? (שלח {M.code('-1')} לבלתי מוגבל)",
            parse_mode=HTML,
        )

    elif action == "add":
        context.user_data["admin_setting"] = "pkg_add_label"
        await query.edit_message_text(
            f"➕ {M.b('הוספת חבילה חדשה')}\n\nשלח את שם החבילה:",
            parse_mode=HTML,
        )


async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    msg = update.message
    if not msg.reply_to_message:
        await msg.reply_text("↩️ כדי לשלוח הודעה למשתמש — השב (Reply) להודעת ההתראה שלו.")
        return
    import re as _re
    original_text = msg.reply_to_message.text or ""
    match = _re.search(r"ID[:\s`]+?(\d+)", original_text)
    if not match:
        await msg.reply_text("🤔 לא הצלחתי לזהות את ה-ID של המשתמש מהודעת ההתראה.")
        return
    target_id = int(match.group(1))
    try:
        dm_html = M.admin_dm(await _name_of(target_id), msg.text)
        await context.bot.send_message(target_id, dm_html, parse_mode=HTML)
        await log_sent_message(target_id, _log_text(dm_html), kind="admin_dm")
        await msg.reply_text(f"✅ נשלח למשתמש {M.code(target_id)}.", parse_mode=HTML)
    except Exception as e:
        await msg.reply_text(f"❌ שגיאה בשליחה: {M.code(e)}", parse_mode=HTML)



async def _cycle_searching_message(msg, steps: list[str]) -> None:
    """Advance the 'searching' message through progress steps while the lookup runs."""
    try:
        for text in steps[1:]:
            await asyncio.sleep(1.1)
            await msg.edit_text(text, parse_mode=HTML)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global PAYMENT_MSG
    user_id = update.effective_user.id
    name    = _first_name(update.effective_user)
    raw     = update.message.text.strip()

    # Maintenance mode — block non-admins
    if user_id != ADMIN_ID and (await get_bot_setting("maintenance")) == "1":
        await update.message.reply_text(M.maintenance(name), parse_mode=HTML)
        return

    # Cancel search
    if raw == "❌ ביטול":
        context.user_data.pop("compare_first", None)
        context.user_data.pop("compare_ts", None)
        await update.message.reply_text(M.search_cancelled(), reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text("👇", reply_markup=_persistent_keyboard(is_admin=(user_id == ADMIN_ID)))
        return

    # Admin settings input
    if user_id == ADMIN_ID:
        setting = context.user_data.get("admin_setting")
        if setting == "deliver_content":
            ref = context.user_data.pop("admin_deliver_ref", None)
            context.user_data.pop("admin_setting", None)
            if not ref:
                await update.message.reply_text("❌ שגיאה — הזמנה לא נמצאה.")
                return
            from src.products import deliver_order
            ok = await deliver_order(ref, raw)
            await update.message.reply_text("✅ נשלח ללקוח!" if ok else "❌ שגיאה — ייתכן שההזמנה כבר טופלה.")
            return
        if setting == "free_count":
            if not raw.isdigit() or int(raw) < 0:
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד.")
                return
            new_val = int(raw)
            import src.users as _u
            _u.FREE_SEARCHES = new_val
            context.user_data.pop("admin_setting", None)
            await update.message.reply_text(f"✅ עודכן! בדיקות חינמיות: {M.b(new_val)}", parse_mode=HTML)
            return
        if setting == "payment_msg":
            PAYMENT_MSG = raw
            context.user_data.pop("admin_setting", None)
            await update.message.reply_text(
                f"✅ הודעת התשלום עודכנה! כך המשתמשים יראו אותה:\n\n{M.payment_required(name, raw)}",
                parse_mode=HTML,
            )
            return
        if setting == "pkg_add_label":
            context.user_data["admin_pkg_label"] = raw
            context.user_data["admin_setting"] = "pkg_add_searches"
            await update.message.reply_text(
                f"כמה חיפושים? (שלח {M.code('-1')} לבלתי מוגבל)",
                parse_mode=HTML,
            )
            return
        if setting == "pkg_add_searches":
            if not raw.lstrip("-").isdigit():
                await update.message.reply_text("❌ שלח מספר שלם בלבד.")
                return
            context.user_data["admin_pkg_searches"] = int(raw)
            context.user_data["admin_setting"] = "pkg_add_price"
            await update.message.reply_text("מה המחיר ב-₪?")
            return
        if setting == "pkg_add_price":
            if not raw.isdigit():
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד.")
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
                f"✅ {M.b('החבילה נוספה')}\n\nבחר חבילה לעריכה או הוסף חדשה:",
                parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return
        if setting == "pkg_edit_searches":
            if not raw.lstrip("-").isdigit():
                await update.message.reply_text("❌ שלח מספר שלם בלבד.")
                return
            context.user_data["admin_pkg_searches"] = int(raw)
            context.user_data["admin_setting"] = "pkg_edit_price"
            await update.message.reply_text("מה המחיר ב-₪?")
            return
        if setting == "pkg_edit_price":
            if not raw.isdigit():
                await update.message.reply_text("❌ שלח מספר שלם חיובי בלבד.")
                return
            from src.packages import get_packages, update_package
            pkg_id   = context.user_data.pop("admin_pkg_id", None)
            searches = context.user_data.pop("admin_pkg_searches", 10)
            price    = int(raw)
            context.user_data.pop("admin_setting", None)
            if pkg_id is None:
                await update.message.reply_text("❌ שגיאה פנימית.")
                return
            pkgs    = await get_packages()
            pkg_row = next((p for p in pkgs if p[0] == pkg_id), None)
            if pkg_row is None:
                await update.message.reply_text("❌ חבילה לא נמצאה.")
                return
            await update_package(pkg_id, pkg_row[1], searches, price)
            pkgs = await get_packages()
            buttons = []
            for pid, lbl, srch, prc in pkgs:
                desc = "ללא הגבלה" if srch == -1 else f"{srch} חיפושים"
                buttons.append([InlineKeyboardButton(f"📦 {lbl} — {desc} · ₪{prc}", callback_data=f"admpkg|pick|{pid}")])
            buttons.append([InlineKeyboardButton("➕ הוסף חבילה", callback_data="admpkg|add")])
            await update.message.reply_text(
                f"✅ {M.b('החבילה עודכנה')}\n\nבחר חבילה לעריכה או הוסף חדשה:",
                parse_mode=HTML,
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
                f"📤 שולח ל-{M.b(len(tg_users))} משתמשי טלגרם...",
                parse_mode=HTML,
            )
            broadcast_log_text = f"📢 הודעה מהמנהל: {raw}"
            _bc_optout_kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔕 הסר אותי מהתפוצה", callback_data="broadcast_optout"),
            ]])
            for u in tg_users:
                uid = u["user_id"]
                if uid == ADMIN_ID:
                    continue
                if not u.get("broadcast_consent", 1):
                    continue
                try:
                    await context.bot.send_message(
                        uid,
                        M.broadcast(M.first_name(u.get("full_name", "")), raw),
                        parse_mode=HTML,
                        reply_markup=_bc_optout_kb,
                    )
                    await log_sent_message(uid, broadcast_log_text, kind="broadcast")
                    sent_ok += 1
                except Exception as e:
                    logger.warning("Broadcast failed for uid=%s: %s", uid, e)
                    sent_fail += 1
                await asyncio.sleep(0.05)
            await update.message.reply_text(
                f"✅ נשלח בהצלחה: {M.b(sent_ok)}\n❌ נכשל: {M.b(sent_fail)}",
                parse_mode=HTML,
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
                    M.admin_user_reply(uname, fullname, user_id, raw),
                    parse_mode=HTML,
                )
                sent = await msg.reply_text(M.admin_chat_relayed(name), parse_mode=HTML)
                context.bot_data.setdefault("admin_chat_msg_ids", set()).add(sent.message_id)
            except Exception as e:
                logger.warning("Failed to relay user message to admin: %s", e)
            return

    plate = normalize_plate(raw)

    if not PLATE_RE.match(plate) or len(plate) < 5:
        await update.message.reply_text(M.invalid_plate(name), parse_mode=HTML)
        return

    first = context.user_data.pop("compare_first", None)
    if first and time.time() - context.user_data.pop("compare_ts", 0) > COMPARE_TTL:
        first = None   # stale: the user wandered off, treat this as a normal lookup
    if first:
        await _compare_flow(update.message, update.effective_user, update.effective_chat.id, context, first, plate)
        return

    await _lookup_flow(update.message, update.effective_user, update.effective_chat.id, context, plate)


async def handle_mirror_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Buttons in the mirror group are inert copies."""
    await update.callback_query.answer("זה רק העתק של מה שהמשתמש ראה — הכפתור לא פעיל", show_alert=True)


async def _mirror_incoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await mirror.record_incoming(update, context.user_data)


async def cmd_mirror_here(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin, inside the target group topic: start mirroring every user interaction here."""
    msg = update.effective_message
    if update.effective_user.id != ADMIN_ID or update.effective_chat.type == "private":
        if update.effective_user.id == ADMIN_ID:
            await msg.reply_text("שלח את /mirror_here בתוך הקבוצה, בטופיק שבו תרצה לראות את הפעולות.")
        return
    thread = msg.message_thread_id if getattr(msg, "is_topic_message", False) else None
    await set_bot_setting("mirror_chat_id", str(update.effective_chat.id))
    await set_bot_setting("mirror_thread_id", str(thread) if thread else "")
    await set_bot_setting("mirror_enabled", "1")
    mirror.invalidate()
    await msg.reply_text(
        "🪞 מראה הפעולות פעילה בטופיק הזה.\nכל פעולה של משתמש בבוט, והתשובה שקיבל, יופיעו כאן. "
        "לכיבוי: /mirror_off",
        message_thread_id=thread,
    )


async def cmd_mirror_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: /mirror_set <topic link>. Sends a test message first; enables the mirror only if it arrived."""
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.effective_message
    target = mirror.parse_topic_link(" ".join(context.args or []))
    if not target:
        await msg.reply_text("שלח: /mirror_set ואחריו קישור לטופיק, למשל:\nhttps://t.me/c/1234567890/2")
        return
    chat_id, thread = target
    try:
        await context.bot.send_message(
            chat_id, "🪞 מראה הפעולות מחוברת לטופיק הזה. כל פעולה של משתמש בבוט, והתשובה שקיבל, יופיעו כאן.",
            message_thread_id=thread,
        )
    except Exception as exc:
        await msg.reply_text(
            f"❌ לא הצלחתי לשלוח לטופיק: {type(exc).__name__}\n"
            "ודא שהבוט חבר בקבוצה, שמותר לו לכתוב בטופיק, ושהקישור הוא של הטופיק עצמו."
        )
        return
    await set_bot_setting("mirror_chat_id", str(chat_id))
    await set_bot_setting("mirror_thread_id", str(thread) if thread else "")
    await set_bot_setting("mirror_enabled", "1")
    mirror.invalidate()
    await msg.reply_text("✅ מראה הפעולות פעילה. שלחתי הודעת בדיקה לטופיק. לכיבוי: /mirror_off")


async def cmd_mirror_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    await set_bot_setting("mirror_enabled", "0")
    mirror.invalidate()
    await update.effective_message.reply_text("🪞 מראה הפעולות כבויה.")


async def _maintenance_blocks(user_id: int) -> bool:
    return user_id != ADMIN_ID and (await get_bot_setting("maintenance")) == "1"


async def _get_record(plate: str):
    record = cache.get(plate)
    if record is None:
        record = await fetch_vehicle_data(plate)
        if record is not None:
            cache.set(plate, record)
    return record


async def _compare_flow(message, tg_user, chat_id: int, context, plate_a: str, plate_b: str) -> None:
    """Side-by-side comparison of two plates. Costs two searches (unless unlimited)."""
    name = _first_name(tg_user)
    user_id = tg_user.id
    is_admin = user_id == ADMIN_ID
    if await _maintenance_blocks(user_id):
        await message.reply_text(M.maintenance(name), parse_mode=HTML)
        return
    if plate_a == plate_b:
        await message.reply_text(M.compare_same(name), parse_mode=HTML)
        return
    allowed, left = await is_allowed(user_id, tg_user.username or "", tg_user.full_name or "")
    if not allowed:
        if await is_blocked(user_id):
            await message.reply_text(M.blocked(name), parse_mode=HTML, reply_markup=_blocked_keyboard())
        else:
            await message.reply_text(
                M.payment_required(name, PAYMENT_MSG), parse_mode=HTML, reply_markup=_payment_keyboard(is_admin),
            )
        return
    last_plate = await get_last_plate(user_id)
    to_charge = [p for p in (plate_a, plate_b) if p != last_plate]   # a plate paid for just now is free, as in a normal lookup
    if left != -1 and left < len(to_charge):
        await message.reply_text(M.compare_not_enough(name), parse_mode=HTML, reply_markup=_payment_keyboard(is_admin))
        return
    try:
        rec_a, rec_b = await asyncio.gather(_get_record(plate_a), _get_record(plate_b))
    except Exception as exc:
        logger.error("compare fetch failed: %s", type(exc).__name__)
        await message.reply_text(M.lookup_error(name), parse_mode=HTML, reply_markup=_persistent_keyboard(is_admin))
        return
    for plate, rec in ((plate_a, rec_a), (plate_b, rec_b)):
        if rec is None:
            await message.reply_text(M.compare_failed(name, plate), parse_mode=HTML, reply_markup=_persistent_keyboard(is_admin))
            return
    try:
        rich_html, classic = compare_rich(rec_a, rec_b), compare_classic(rec_a, rec_b)
    except Exception as exc:
        logger.error("compare render failed: %s", type(exc).__name__)
        await message.reply_text(M.lookup_error(name), parse_mode=HTML, reply_markup=_persistent_keyboard(is_admin))
        return
    kb = _persistent_keyboard(is_admin)
    delivered = await send_rich_message(chat_id, rich_html, reply_markup=kb)
    if not delivered:
        await message.reply_text(classic, parse_mode=HTML, reply_markup=kb)
    for plate in to_charge:   # charge only once the user actually got the comparison
        await increment_search(user_id, plate)
    await set_last_plate(user_id, plate_b)


async def cmd_compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = _first_name(update.effective_user)
    plates = [normalize_plate(a) for a in (context.args or [])]
    if len(plates) != 2 or not all(PLATE_RE.match(p) and len(p) >= 5 for p in plates):
        await update.message.reply_text(M.compare_need_two(name), parse_mode=HTML)
        return
    await _compare_flow(update.message, update.effective_user, update.effective_chat.id, context, plates[0], plates[1])


async def handle_reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """rem|add|PLATE -> arm a test reminder; rem|stop|ID -> stop it."""
    query = update.callback_query
    user = query.from_user
    name = _first_name(user)
    parts = query.data.split("|")
    if parts[1] == "stop":
        ok = await _rem.stop_reminder(int(parts[2]), user.id)
        await query.answer("🔕 הופסק" if ok else "לא נמצא")
        if ok:
            await query.edit_message_reply_markup(reply_markup=None)
        return
    plate = parts[2]
    if (await get_bot_setting("test_reminders_enabled")) != "1":
        await query.answer()
        await query.message.reply_text(M.reminders_disabled(name), parse_mode=HTML)
        return
    if await is_blocked(user.id) or await _maintenance_blocks(user.id):
        await query.answer()
        return
    if not await _rem.get_reminder(user.id, plate) and await _rem.count_for_user(user.id) >= MAX_REMINDERS_PER_USER:
        await query.answer("הגעת למספר התזכורות המקסימלי", show_alert=True)
        return
    record = context.user_data.get("last_record")
    if not record or str(record.get("mispar_rechev")) != plate:
        record = cache.get(plate)
    if not record:
        try:
            record = await _get_record(plate)
        except Exception:
            record = None
    tokef = _rem.parse_date((record or {}).get("tokef_dt"))
    await query.answer()
    if not tokef:
        await query.message.reply_text(M.reminder_no_date(name), parse_mode=HTML)
        return
    rem = await _rem.add_reminder(user.id, plate, tokef.isoformat(), _rem.label_for(record))
    days = (tokef - _rem.date.today()).days
    await query.message.reply_text(
        M.reminder_set(name, plate, rem["label"], tokef.isoformat(), days),
        parse_mode=HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔕 הפסק תזכורות", callback_data=f"rem|stop|{rem['id']}")]]),
    )


async def handle_compare_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    plate = query.data.split("|")[2]
    context.user_data["compare_first"] = plate
    context.user_data["compare_ts"] = time.time()
    await query.message.reply_text(
        M.compare_ask_second(_first_name(query.from_user), plate),
        parse_mode=HTML,
        reply_markup=_cancel_search_keyboard(),
    )


async def _lookup_flow(message, tg_user, chat_id: int, context: ContextTypes.DEFAULT_TYPE, plate: str) -> None:
    """Quota check -> registry lookup -> result card. Used by typed plates."""
    user_id = tg_user.id
    name    = _first_name(tg_user)
    is_admin = user_id == ADMIN_ID
    if await _maintenance_blocks(user_id):
        await message.reply_text(M.maintenance(name), parse_mode=HTML)
        return
    allowed, left = await is_allowed(user_id, tg_user.username or "", tg_user.full_name or "")
    if not allowed:
        if await is_blocked(user_id):
            await message.reply_text(
                M.blocked(name),
                parse_mode=HTML,
                reply_markup=_blocked_keyboard(),
            )
        else:
            await message.reply_text(
                M.payment_required(name, PAYMENT_MSG),
                parse_mode=HTML,
                reply_markup=_payment_keyboard(is_admin),
            )
        return

    if left == 1:
        await message.reply_text(M.last_free_search(name), parse_mode=HTML)

    # cache hit — skip API call
    record = cache.get(plate)
    if record is None:
        steps = M.search_steps(name)
        searching_msg = await message.reply_text(steps[0], parse_mode=HTML)
        cycler = asyncio.create_task(_cycle_searching_message(searching_msg, steps))
        try:
            record = await fetch_vehicle_data(plate)
        except Exception as exc:
            cycler.cancel()
            logger.error("Error fetching data for plate %s: %s", plate, exc)
            await searching_msg.delete()
            await message.reply_text(
                M.lookup_error(name), parse_mode=HTML,
                reply_markup=_persistent_keyboard(is_admin),
            )
            return
        cycler.cancel()
        if record is not None:
            cache.set(plate, record)
        await searching_msg.delete()
    else:
        searching_msg = None

    if record is None:
        await message.reply_text(
            M.not_found(name, plate), parse_mode=HTML,
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
            from src.activity import log as _log
            uname = tg_user.username or ""
            await _log("search", f"חיפוש לוחית {plate}", user_id, uname)
        except Exception:
            pass

    try:
        card = M.result_intro(name, plate) + quick_summary(record)
        context.user_data["last_share_text"] = get_share_text(record)
    except Exception as exc:
        logger.error("quick_summary failed for plate %s: %s", plate, exc)
        if searching_msg:
            try:
                await searching_msg.delete()
            except Exception:
                pass
        await message.reply_text(
            M.lookup_error(name), parse_mode=HTML,
            reply_markup=_persistent_keyboard(is_admin),
        )
        return

    footer_text = ""
    if not is_repeat:
        if left == -1:
            from src.users import get_quota_expires
            expires = await get_quota_expires(user_id)
            card += M.result_quota_footer(-1, expires)
            footer_text = M.result_quota_text(-1, expires)
        elif left > 0:
            card += M.result_quota_footer(left - 1, None)
            footer_text = M.result_quota_text(left - 1, None)

    if searching_msg:
        try:
            await searching_msg.delete()
        except Exception:
            pass

    yad2_link = _yad2.build_url(record)
    result_kb = build_result_keyboard(
        is_admin=(user_id == ADMIN_ID), record=record, yad2_link=yad2_link,
    )
    # Table layout via sendRichMessage (admin setting rich_messages_enabled); any failure falls through to classic HTML.
    if await send_rich_message(
        chat_id,
        M.result_card_rich(name, plate, quick_summary_rich(record), footer_text),
        reply_markup=result_kb,
    ):
        return
    try:
        await message.reply_text(
            card,
            parse_mode=HTML,
            reply_markup=build_result_keyboard(
                is_admin=(user_id == ADMIN_ID),
                record=record,
                yad2_link=yad2_link,
            ),
        )
    except Exception as exc:
        logger.error("reply_text HTML failed for plate %s: %s", plate, exc)
        try:
            plain = M.strip_html(card)
            await message.reply_text(
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
        await query.message.reply_text(M.no_report_to_share(_first_name(query.from_user)), parse_mode=HTML)
        return
    await query.message.reply_text(share_text)


async def handle_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query    = update.callback_query
    user_id  = query.from_user.id
    is_admin = user_id == ADMIN_ID
    await query.answer()

    if query.data == "new_search":
        await query.message.reply_text(
            M.ask_plate(_first_name(query.from_user)),
            parse_mode=HTML,
            reply_markup=_cancel_search_keyboard(),
        )
        return

    if query.data == "chat_admin":
        admin_username = os.environ.get("ADMIN_USERNAME", "")
        url = f"https://t.me/{admin_username}" if admin_username else f"https://t.me/{BOT_USERNAME}?start=admin_chat"
        await query.message.reply_text(
            M.open_admin_chat(_first_name(query.from_user)),
            parse_mode=HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 פתח שיחה עם מנהל", url=url)]
            ]),
        )
        return

    if query.data == "admin_panel" and user_id == ADMIN_ID:
        stats = await admin_stats()
        await query.message.reply_text(
            M.admin_panel(_first_name(query.from_user), stats),
            parse_mode=HTML,
            reply_markup=_admin_main_keyboard(),
        )
        return


async def handle_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    record = context.user_data.get("last_record")
    if not record:
        await query.message.reply_text(M.no_report_for_pdf(_first_name(query.from_user)), parse_mode=HTML)
        return
    plate = record.get("mispar_rechev", "vehicle")
    name = _first_name(query.from_user)
    status_msg = await query.message.reply_text(M.pdf_preparing(name), parse_mode=HTML)

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
        await query.message.reply_text(M.pdf_failed(name), parse_mode=HTML)
        return
    try:
        await status_msg.delete()
    except Exception:
        pass
    await query.message.reply_document(
        document=io.BytesIO(pdf_bytes),
        filename=f"car_{plate}.pdf",
        caption=M.pdf_caption(plate),
    )




async def handle_broadcast_consent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast opt-out / opt-in inline buttons."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    name = _first_name(query.from_user)
    action = query.data  # "broadcast_optout" or "broadcast_optin"

    if action == "broadcast_optout":
        await set_broadcast_consent(user_id, False)
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔔 חזור לרשימת התפוצה", callback_data="broadcast_optin"),
            ]])
        )
        await context.bot.send_message(user_id, M.optout(name), parse_mode=HTML)
    elif action == "broadcast_optin":
        await set_broadcast_consent(user_id, True)
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔕 הסר אותי מהתפוצה", callback_data="broadcast_optout"),
            ]])
        )
        await context.bot.send_message(user_id, M.optin(name), parse_mode=HTML)


async def cmd_optout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await set_broadcast_consent(user.id, False)
    await update.message.reply_text(M.optout(_first_name(user)), parse_mode=HTML)


async def cmd_optin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await set_broadcast_consent(user.id, True)
    await update.message.reply_text(M.optin(_first_name(user)), parse_mode=HTML)


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

    _alerts_sent = 0
    try:
        watches = await get_all_active_watches()
        if not watches:
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
                    try:
                        await context.bot.send_message(
                            w["user_id"],
                            M.watch_started(await _name_of(w["user_id"]), label, len(current_ids)),
                            parse_mode=HTML,
                        )
                    except Exception as e:
                        logger.warning("Watch start notify failed user=%s: %s", w["user_id"], e)
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
                    top_price = f"₪{int(top['price']):,}" if top and top.get("price") else "מחיר לא צוין"
                    top_details = "  ".join(filter(None, [
                        f"🛣️ {int(top['km']):,} ק\"מ" if top and top.get("km") else None,
                        f"📍 {top['city']}" if top and top.get("city") else None,
                    ])) if top else ""
                    top_link = top.get("link", "") if top else ""

                    text = M.watch_alert(
                        await _name_of(w["user_id"]), label, count, top_price, top_details,
                        top_link, search_url,
                    )
                    try:
                        with mirror.quiet():   # automatic alerts are summarised, not copied one by one
                            await context.bot.send_message(
                                w["user_id"], text,
                                parse_mode=HTML,
                            )
                        _alerts_sent += 1
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
                        f"⚠️ {M.b('שגיאה בבדיקת מעקב')} id={w['id']}: {M.esc(e)}",
                        parse_mode=HTML,
                    )
                except Exception:
                    pass
        if _alerts_sent:
            mirror.note(f"👀 התראות מעקב יד2: נשלחו {_alerts_sent}")
    except Exception as e:
        logger.error("Yad2 watcher job error: %s", e)


async def _post_init(app) -> None:
    await init_db()
    await load_welcome_settings()
    # Menu button (text + web app URL) is managed manually via BotFather —
    # not set here, so it doesn't get overwritten on every restart.
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

    app = Application.builder().bot(mirror.MirrorBot(token)).post_init(_post_init).build()
    global _bot_instance
    _bot_instance = app.bot
    # Register the payment notifier so api.py can notify admin without importing bot
    from src.notifier import register_ticket_notifiers
    register_ticket_notifiers(_notify_admin_ticket, _notify_user_ticket_reply)

    async def _notify_payment_approved(user_id: int, label: str, searches: int):
        try:
            desc = "ללא הגבלה" if searches == -1 else f"{searches} חיפושים"
            approved_msg = M.payment_approved(await _name_of(user_id), label, desc)
            await app.bot.send_message(user_id, approved_msg, parse_mode=HTML)
            await log_sent_message(user_id, _log_text(approved_msg), kind="payment")
        except Exception:
            pass

    async def _notify_payment_declined(user_id: int, label: str):
        try:
            declined_msg = M.payment_declined(await _name_of(user_id), label)
            await app.bot.send_message(user_id, declined_msg, parse_mode=HTML)
            await log_sent_message(user_id, _log_text(declined_msg), kind="payment")
        except Exception:
            pass

    from src.notifier import register_payment_result_notifiers
    register_payment_result_notifiers(_notify_payment_approved, _notify_payment_declined)

    _optout_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔕 הסר אותי מהתפוצה", callback_data="broadcast_optout"),
    ]])

    async def _do_broadcast(message: str) -> dict:
        from src.users import get_all_users
        users = await get_all_users()
        sent = failed = 0
        with mirror.quiet():   # one summary line instead of a copy per recipient
            for u in users:
                uid = u.get("user_id")
                if not uid or uid == ADMIN_ID:
                    continue
                if not u.get("broadcast_consent", 1):
                    continue
                try:
                    text = M.broadcast(M.first_name(u.get("full_name", "")), message)
                    await app.bot.send_message(uid, text, parse_mode=HTML, reply_markup=_optout_kb)
                    await log_sent_message(uid, _log_text(text), kind="broadcast")
                    sent += 1
                except Exception:
                    failed += 1
        mirror.note(f"📢 שידור נשלח ל-{sent} משתמשים" + (f" ({failed} נכשלו)" if failed else "") + f"\n{message[:300]}")
        return {"ok": True, "sent": sent, "failed": failed}

    async def _notify_admin_grant(user_id: int, searches: int, expires: str = ""):
        try:
            msg = M.grant_update(await _name_of(user_id), searches, expires)
            await app.bot.send_message(user_id, msg, parse_mode=HTML)
            await log_sent_message(user_id, _log_text(msg), kind="grant")
        except Exception:
            pass

    from src.notifier import register_admin_grant_notifier
    register_admin_grant_notifier(_notify_admin_grant)

    from src.notifier import register_broadcast_notifier
    register_broadcast_notifier(_do_broadcast)

    async def _send_message_to_user(user_id: int, message: str) -> bool:
        try:
            text = M.admin_dm(await _name_of(user_id), message)
            await app.bot.send_message(user_id, text, parse_mode=HTML)
            await log_sent_message(user_id, _log_text(text), kind="admin_dm")
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
        with mirror.quiet():
            for u in users:
                uid = u.get("user_id")
                if not uid or uid == ADMIN_ID or u.get("blocked"):
                    continue
                if not u.get("broadcast_consent", 1):
                    continue
                try:
                    text = M.broadcast(M.first_name(u.get("full_name", "")), message)
                    if photo_bytes and len(text) <= 1024:
                        await app.bot.send_photo(
                            uid,
                            photo=_io.BytesIO(photo_bytes),
                            caption=text,
                            parse_mode=HTML,
                            reply_markup=_optout_kb,
                        )
                    elif photo_bytes:
                        # Telegram limits photo captions to 1024 chars: send the image, then the full text
                        await app.bot.send_photo(uid, photo=_io.BytesIO(photo_bytes))
                        await app.bot.send_message(uid, text, parse_mode=HTML, reply_markup=_optout_kb)
                    else:
                        await app.bot.send_message(uid, text, parse_mode=HTML, reply_markup=_optout_kb)
                    await log_sent_message(uid, _log_text(text), kind="broadcast")
                    sent += 1
                except Exception:
                    failed += 1
        mirror.note(f"📢 שידור עם תמונה נשלח ל-{sent} משתמשים" + (f" ({failed} נכשלו)" if failed else "") + f"\n{message[:300]}")
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
        'pending_delivery': '📦 ממתין למשלוח ידני',
    }

    async def _notify_admin_order(ref, status, label, amount, username, member_id):
        if not ADMIN_ID:
            return
        status_txt = STATUS_HE.get(status, status)
        user_txt = f"@{username}" if username else f"חבר #{member_id}" if member_id else ref.split('-')[0]
        text = M.admin_order(status_txt, ref, user_txt, member_id, label, amount)
        try:
            await app.bot.send_message(ADMIN_ID, text, parse_mode=HTML)
        except Exception:
            pass

    from src.notifier import register_admin_order_notifier
    register_admin_order_notifier(_notify_admin_order)

    async def _notify_admin_product_delivery(ref, user_id, label):
        if not ADMIN_ID:
            return
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 שלח תוכן משלוח", callback_data=f"deliver|{ref}"),
        ]])
        text = M.admin_delivery_needed(ref, user_id, label)
        try:
            await app.bot.send_message(ADMIN_ID, text, parse_mode=HTML, reply_markup=kb)
        except Exception:
            pass

    from src.notifier import register_admin_product_delivery_notifier
    register_admin_product_delivery_notifier(_notify_admin_product_delivery)

    async def _notify_user_product_delivered(user_id, label, ref, content):
        try:
            msg = M.product_delivered(await _name_of(user_id), label, ref, content)
            with mirror.redacted():   # keys/credentials must not appear in the mirror group
                await app.bot.send_message(user_id, msg, parse_mode=HTML)
            await log_sent_message(user_id, _log_text(msg), kind="product_delivery")
        except Exception:
            pass

    from src.notifier import register_user_product_delivered_notifier
    register_user_product_delivered_notifier(_notify_user_product_delivered)

    async def _notify_admin_order_delivered(ref, user_id, username, label, price, content, auto):
        if not ADMIN_ID:
            return
        user_txt = f"@{username}" if username else str(user_id)
        text = M.admin_order_delivered(user_txt, user_id, label, price, ref, content, auto)
        try:
            await app.bot.send_message(ADMIN_ID, text, parse_mode=HTML)
        except Exception:
            try:
                # Plain-text fallback if Telegram rejects the markup for any reason
                await app.bot.send_message(ADMIN_ID, M.strip_html(text))
            except Exception:
                pass

    from src.notifier import register_admin_order_delivered_notifier
    register_admin_order_delivered_notifier(_notify_admin_order_delivered)

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
    app.add_handler(TypeHandler(Update, _mirror_incoming), group=-1)   # blocking: the user action must be queued before the bot reacts
    app.add_handler(CallbackQueryHandler(handle_mirror_noop, pattern=r"^mirror\|noop$"))
    app.add_handler(CommandHandler("mirror_here", cmd_mirror_here))
    app.add_handler(CommandHandler("mirror_off", cmd_mirror_off))
    app.add_handler(CommandHandler("mirror_set", cmd_mirror_set))
    app.add_handler(CommandHandler("compare", cmd_compare))
    app.add_handler(CommandHandler("optout", cmd_optout))
    app.add_handler(CommandHandler("optin",  cmd_optin))
    app.add_handler(CallbackQueryHandler(handle_reminder_callback, pattern=r"^rem\|"))
    app.add_handler(CallbackQueryHandler(handle_compare_callback,  pattern=r"^cmp\|start\|"))
    app.add_handler(CallbackQueryHandler(handle_broadcast_consent_callback, pattern=r"^broadcast_(optout|optin)$"))
    app.add_handler(CallbackQueryHandler(handle_user_callback,   pattern=r"^(usr|ugrant|utoggle)\|"))
    app.add_handler(CallbackQueryHandler(handle_admin_callback,  pattern=r"^adm\|"))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CallbackQueryHandler(handle_buy_callback,     pattern=r"^buy\|"))
    app.add_handler(CallbackQueryHandler(handle_paid_callback,    pattern=r"^paid\|"))
    app.add_handler(CallbackQueryHandler(handle_approve_callback, pattern=r"^approve\|"))
    app.add_handler(CallbackQueryHandler(handle_decline_callback, pattern=r"^decline\|"))
    app.add_handler(CallbackQueryHandler(handle_deliver_callback, pattern=r"^deliver\|"))
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
        try:
            user_ids = await get_users_expiring_in_days(days)
            delivered = 0
            with mirror.quiet():
                for uid in user_ids:
                    try:
                        text = M.expiry_reminder(await _name_of(uid), days)
                        await context.bot.send_message(uid, text, parse_mode=HTML)
                        await log_sent_message(uid, _log_text(text), kind="expiry_reminder")
                        delivered += 1
                    except Exception:
                        pass
            if delivered:
                mirror.note(f"⏰ תזכורות מנוי ({days} ימים): נשלחו {delivered}")
        except Exception as e:
            logger.warning("Expiry reminder job (days=%d) error: %s", days, e)

    async def _send_test_reminder(rem: dict, days_left: int, milestone: int):
        if await is_blocked(rem["user_id"]):
            return None
        text = M.test_reminder(await _name_of(rem["user_id"]), rem["plate"], rem["label"], rem["tokef_dt"], days_left)
        try:
            await app.bot.send_message(
                rem["user_id"], text, parse_mode=HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔍 בדוק את הרכב", callback_data=f"hist_plate|{rem['plate']}"),
                    InlineKeyboardButton("🔕 הפסק תזכורות", callback_data=f"rem|stop|{rem['id']}"),
                ]]),
            )
        except Forbidden:
            return None   # the user blocked the bot: stop reminding them
        await log_sent_message(rem["user_id"], _log_text(text), kind="test_reminder")
        return True

    async def _fetch_tokef(plate: str):
        record = await fetch_vehicle_data(plate)
        return (record or {}).get("tokef_dt")

    async def _test_reminders_job(context):
        if (await get_bot_setting("test_reminders_enabled")) != "1":
            return
        try:
            added = 0
            if (await get_bot_setting("test_reminders_garage_sync")) == "1":
                added = await _rem.sync_garage()
            else:
                await _rem.deactivate_orphans()
            with mirror.quiet():
                sent = await _rem.run_due(_send_test_reminder, _fetch_tokef)
            if sent:
                mirror.note(f"🔔 תזכורות טסט: נשלחו {sent}")
            logger.info("test reminders: garage_added=%s sent=%s", added, sent)
        except Exception as e:
            logger.warning("Test reminders job error: %s", e)

    async def _scheduled_broadcast_job(context):
        """Send broadcasts whose scheduled time has come; tell the admin how they went."""
        from src import scheduled_broadcast as sb
        try:
            for row in await sb.sweep():
                why = "עבר יותר מדי זמן מהמועד (הבוט היה כבוי) ולכן לא נשלח" if row["status"] == "missed" else "הבוט נעצר באמצע השליחה ולכן לא נשלח שוב אוטומטית"
                await context.bot.send_message(
                    ADMIN_ID, f"⚠️ שידור מתוזמן #{row['id']} לא נשלח: {why}.\n\n{M.esc(row['message'][:200])}", parse_mode=HTML,
                )
            for row in await sb.claim_due():
                try:
                    if row["image_b64"]:
                        result = await _do_broadcast_photo(row["message"], row["image_b64"])
                    else:
                        result = await _do_broadcast(row["message"])
                    await sb.finish(row["id"], "sent", result.get("sent", 0), result.get("failed", 0))
                    from src.db import execute as _exec
                    await _exec(
                        "INSERT INTO broadcast_history (message, has_image, sent, failed) VALUES (?, ?, ?, ?)",
                        [row["message"], 1 if row["image_b64"] else 0, result.get("sent", 0), result.get("failed", 0)],
                    )
                    try:
                        from src.activity import log as _log
                        await _log("broadcast", f"שידור מתוזמן נשלח: {row['message'][:80]}")
                    except Exception:
                        pass
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"📢 השידור המתוזמן #{row['id']} נשלח: {result.get('sent', 0)} משתמשים"
                        + (f", נכשל: {result.get('failed', 0)}" if result.get("failed") else ""),
                    )
                except Exception as exc:
                    logger.error("scheduled broadcast %s failed: %s", row["id"], exc)
                    await sb.finish(row["id"], "failed")
                    await context.bot.send_message(ADMIN_ID, f"❌ השידור המתוזמן #{row['id']} נכשל: {type(exc).__name__}")
        except Exception as exc:
            logger.warning("Scheduled broadcast job error: %s", exc)

    async def _expire_subscriptions_job(context):
        try:
            expired = await expire_subscriptions()
            if expired:
                logger.info("Expired subscriptions downgraded: %s", expired)
        except Exception as e:
            logger.warning("Expire subscriptions job error: %s", e)

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
        # Run at startup and then every hour to downgrade expired subscriptions promptly
        async def _mirror_flush_job(context):
            await mirror.flush(context.bot)

        app.job_queue.run_repeating(_mirror_flush_job, interval=3, first=6, name="mirror_flush")
        app.job_queue.run_repeating(_scheduled_broadcast_job, interval=30, first=20, name="scheduled_broadcast")
        app.job_queue.run_daily(
            _test_reminders_job,
            time=_dt.time(hour=7, minute=0, tzinfo=_dt.timezone.utc),   # 10:00 Israel (summer)
            name="test_reminders",
        )
        app.job_queue.run_repeating(
            _expire_subscriptions_job,
            interval=3600,
            first=10,
            name="expire_subscriptions",
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
