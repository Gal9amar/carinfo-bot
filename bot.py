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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.api.gov_api import fetch_vehicle_data
from src.cache import cache
from src.users import (
    is_allowed, increment_search, apply_code, generate_code,
    admin_stats, admin_grant, get_all_users, get_user_by_username,
)
from src.formatter import (
    CATEGORIES,
    format_error,
    format_not_found,
    get_category_text,
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

logger.info("ADMIN_ID loaded: %s", ADMIN_ID)

PAYMENT_MSG = (
    "🔒 *נגמרו הבדיקות החינמיות שלך*\n\n"
    "לרכישת בדיקות נוספות לחץ על הכפתור למטה\\.\n"
    "נחזור אליך בהקדם\\!"
)

def _payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "💳 רכישת בדיקות נוספות",
            url=f"https://t.me/{BOT_USERNAME}?start=buy"
        )
    ]])


def normalize_plate(text: str) -> str:
    return text.strip().replace("-", "").replace(" ", "")


def build_keyboard(plate: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for key, (label, _) in CATEGORIES.items():
        row.append(InlineKeyboardButton(label, callback_data=f"{plate}|{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    is_admin = uid == ADMIN_ID
    await update.message.reply_text(
        f"🆔 Your ID: `{uid}`\n👑 Admin: `{is_admin}`\n⚙️ ADMIN\\_ID set to: `{ADMIN_ID}`",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id   = update.effective_user.id
    user      = update.effective_user
    args      = context.args

    # /start buy  →  purchase flow
    if args and args[0] == "buy":
        uname    = f"@{user.username}" if user.username else f"id:{user_id}"
        fullname = user.full_name or ""
        # Notify admin
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
        # Reply to user
        await update.message.reply_text(
            "✅ *קיבלנו את בקשתך\\!*\n\n"
            "ניצור איתך קשר בהקדם לאחר אישור התשלום\\.\n\n"
            "💳 לתשלום מהיר דרך ביט:\n*053\\-388\\-8381*\n"
            "📝 ציין בהודעה: *CarInfo*",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Admin gets the management panel on start
    if user_id == ADMIN_ID:
        stats = admin_stats()
        await update.message.reply_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_main_keyboard(),
        )
        return

    allowed, left = is_allowed(user_id)

    if not allowed:
        await update.message.reply_text(
            PAYMENT_MSG,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_payment_keyboard(),
        )
        return

    searches_info = f"נותרו לך *{left}* בדיקות חינמיות\\." if left > 0 else "גישה מלאה פעילה ✅"

    await update.message.reply_text(
        "👋 שלום\\! אני בוט לבדיקת פרטי רכב ישראלי\\.\n\n"
        "שלח לי מספר לוחית רישוי \\(לדוגמה: 1234567\\)\n"
        "ואחזיר לך את כל המידע הזמין על הרכב\\.\n\n"
        f"{searches_info}",
        parse_mode=ParseMode.MARKDOWN_V2,
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
    allowed, left = is_allowed(user_id)
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
    success, msg = apply_code(user_id, code)
    await update.message.reply_text(
        f"{'✅' if success else '❌'} {msg}",
        parse_mode=ParseMode.MARKDOWN_V2 if not success else None,
    )


def _admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 סטטיסטיקות",      callback_data="adm|stats")],
        [InlineKeyboardButton("👥 משתמשים",          callback_data="adm|users"),
         InlineKeyboardButton("🔑 צור קוד",          callback_data="adm|gen_menu")],
        [InlineKeyboardButton("💳 הענק גישה",        callback_data="adm|grant_info")],
        [InlineKeyboardButton("⚙️ הגדרות בוט",       callback_data="adm|settings")],
    ])


def _admin_gen_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 בדיקות",  callback_data="adm|gen|10|single"),
         InlineKeyboardButton("25 בדיקות",  callback_data="adm|gen|25|single")],
        [InlineKeyboardButton("50 בדיקות",  callback_data="adm|gen|50|single"),
         InlineKeyboardButton("100 בדיקות", callback_data="adm|gen|100|single")],
        [InlineKeyboardButton("♾️ בלתי מוגבל (חד פעמי)",  callback_data="adm|gen|-1|single")],
        [InlineKeyboardButton("♾️ בלתי מוגבל (רב פעמי)", callback_data="adm|gen|-1|multi")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")],
    ])


def _admin_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ שנה הודעת תשלום",  callback_data="adm|set_payment")],
        [InlineKeyboardButton("🆓 שנה מספר בדיקות חינמיות", callback_data="adm|set_free")],
        [InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")],
    ])


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin only – interactive admin panel."""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        return

    args = context.args

    # Legacy text sub-commands still work
    if args:
        if args[0] == "grant" and len(args) >= 3:
            username = args[1].lstrip("@")
            try:
                amount = int(args[2])
            except ValueError:
                await update.message.reply_text("כמות חייבת להיות מספר", parse_mode=ParseMode.MARKDOWN_V2)
                return
            target = get_user_by_username(username)
            if not target:
                await update.message.reply_text(f"משתמש @{username} לא נמצא\\.", parse_mode=ParseMode.MARKDOWN_V2)
                return
            note = " ".join(args[3:]) if len(args) > 3 else ""
            msg = admin_grant(user_id, target["user_id"], amount, note)
            await update.message.reply_text(f"✅ @{username}: {msg}", parse_mode=ParseMode.MARKDOWN_V2)
            return

        if args[0] == "gen":
            try:
                count = int(args[1]) if len(args) > 1 and args[1] != "multi" else 10
            except ValueError:
                count = 10
            single = "multi" not in args
            unlimited = count == -1
            code = generate_code(searches=count, single_use=single, unlimited=unlimited)
            kind = "בלתי מוגבל" if unlimited else f"{count} בדיקות"
            use_str = "חד פעמי" if single else "רב פעמי"
            await update.message.reply_text(
                f"✅ קוד חדש \\({kind}, {use_str}\\):\n`{code}`",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

    # /admin  → show main panel
    stats = admin_stats()
    await update.message.reply_text(
        f"🛠 *פאנל ניהול CarInfo*\n\n"
        f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
        f"🔍 בדיקות: *{stats['total_searches']}*\n"
        f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=_admin_main_keyboard(),
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all adm|... callback buttons."""
    query = update.callback_query
    user_id = query.from_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        await query.answer("אין הרשאה", show_alert=True)
        return
    await query.answer()

    parts = query.data.split("|")
    action = parts[1] if len(parts) > 1 else ""

    # ── Main panel ──
    if action == "main":
        stats = admin_stats()
        await query.edit_message_text(
            f"🛠 *פאנל ניהול CarInfo*\n\n"
            f"👤 משתמשים: *{stats['total_users']}* \\| פעילים: *{stats['active_users']}*\n"
            f"🔍 בדיקות: *{stats['total_searches']}*\n"
            f"🔑 קודים: *{stats['used_codes']}/{stats['total_codes']}* נוצלו",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_main_keyboard(),
        )
        return

    # ── Stats ──
    if action == "stats":
        stats = admin_stats()
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

    # ── Users list ──
    if action == "users":
        users = get_all_users()
        if not users:
            await query.edit_message_text(
                "אין משתמשים עדיין\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
            )
            return
        lines = ["👥 *משתמשים* \\(מסודר לפי בדיקות\\)\n"]
        for u in users[:25]:
            uname = f"@{u['username']}" if u.get("username") else f"id:{u['user_id']}"
            done  = u.get("searches_done", 0)
            quota = u.get("searches_quota", 0)
            left  = u.get("searches_left", 0)
            quota_str = "∞" if quota == -1 else str(quota)
            left_str  = "∞" if left  == -1 else str(left)
            from src.formatter import _escape
            lines.append(f"• {_escape(uname)}: {done}/{quota_str} \\(נותרו: {left_str}\\)\n")
        await query.edit_message_text(
            "".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|main")]]),
        )
        return

    # ── Gen menu ──
    if action == "gen_menu":
        await query.edit_message_text(
            "🔑 *יצירת קוד גישה*\n\nבחר כמות בדיקות לקוד:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_gen_keyboard(),
        )
        return

    # ── Gen code ──
    if action == "gen":
        count_str = parts[2] if len(parts) > 2 else "10"
        use_type  = parts[3] if len(parts) > 3 else "single"
        count     = int(count_str)
        single    = use_type == "single"
        unlimited = count == -1
        code = generate_code(searches=count, single_use=single, unlimited=unlimited)
        kind     = "♾️ בלתי מוגבל" if unlimited else f"{count} בדיקות"
        use_str  = "חד פעמי" if single else "רב פעמי"
        await query.edit_message_text(
            f"✅ *קוד חדש נוצר*\n\n"
            f"סוג: {kind} \\| {use_str}\n\n"
            f"`{code}`\n\n"
            f"_העתק את הקוד ושלח ללקוח_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 צור קוד נוסף", callback_data="adm|gen_menu")],
                [InlineKeyboardButton("🔙 ראשי",          callback_data="adm|main")],
            ]),
        )
        return

    # ── Grant info ──
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

    # ── Settings ──
    if action == "settings":
        import src.users as _u
        free = _u.FREE_SEARCHES
        await query.edit_message_text(
            f"⚙️ *הגדרות בוט*\n\n"
            f"• בדיקות חינמיות למשתמש חדש: *{free}*\n"
            f"• הודעת תשלום: מוגדרת\n\n"
            f"לשינוי מספר הבדיקות החינמיות, ערוך את המשתנה `FREE_SEARCHES` ב\\-`src/users\\.py`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_admin_settings_keyboard(),
        )
        return

    if action == "set_payment":
        await query.edit_message_text(
            "✏️ *שינוי הודעת תשלום*\n\n"
            "ערוך את המשתנה `PAYMENT_MSG` ב\\-`bot\\.py` ודחוף לגיטהאב\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|settings")]]),
        )
        return

    if action == "set_free":
        await query.edit_message_text(
            "🆓 *שינוי מספר בדיקות חינמיות*\n\n"
            "ערוך את השורה `FREE_SEARCHES = 5` ב\\-`src/users\\.py` לכל ערך שתרצה ודחוף לגיטהאב\\.\n\n"
            "_שים לב: משפיע רק על משתמשים חדשים_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 חזרה", callback_data="adm|settings")]]),
        )
        return


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    raw = update.message.text.strip()
    plate = normalize_plate(raw)

    if not PLATE_RE.match(plate) or len(plate) < 5:
        await update.message.reply_text(
            "🔢 שלח מספר רכב תקין בלבד \\(למשל: 1234567\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # Check access
    allowed, left = is_allowed(user_id)
    if not allowed:
        await update.message.reply_text(
            PAYMENT_MSG,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_payment_keyboard(),
        )
        return

    # Warn if last free search
    if left == 1:
        await update.message.reply_text(
            "⚠️ זוהי הבדיקה החינמית האחרונה שלך\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    # Send "searching..." and keep the message object so we can delete it later
    searching_msg = await update.message.reply_text(
        "🔍 מחפש נתונים\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2
    )

    try:
        record = await fetch_vehicle_data(plate)
    except Exception as exc:
        logger.error("Error fetching data for plate %s: %s", plate, exc)
        await searching_msg.delete()
        await update.message.reply_text(format_error(), parse_mode=ParseMode.MARKDOWN_V2)
        return

    if record is None:
        await searching_msg.delete()
        await update.message.reply_text(format_not_found(plate), parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Count the search only after confirming the vehicle exists
    increment_search(user_id)

    cache.set(f"record_{plate}", record)

    summary = get_summary(record)
    keyboard = build_keyboard(plate)

    # Add remaining searches note for free users
    if left > 0 and left != -1:
        remaining = left - 1
        if remaining > 0:
            summary += f"\n\n_נותרו לך {remaining} בדיקות חינמיות_"

    await searching_msg.delete()

    await update.message.reply_text(
        summary,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        plate, category = query.data.split("|", 1)
    except ValueError:
        return

    record = cache.get(f"record_{plate}")
    if record is None:
        await query.message.reply_text(
            "⏰ פג תוקף הנתונים\\. שלח את מספר הרכב שוב\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    text = get_category_text(category, record)
    keyboard = build_keyboard(plate)

    await query.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


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


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    Thread(target=run_health_server, daemon=True).start()
    logger.info("Health server started")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("code", cmd_code))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plate))
    app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern=r"^adm\|"))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
