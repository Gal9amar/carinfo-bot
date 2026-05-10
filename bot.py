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

import httpx

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
from src.api.image_api import fetch_car_image
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

PLATE_RE = re.compile(r"^[\d\-]{5,10}$")
ADMIN_ID  = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

PAYMENT_MSG = (
    "🔒 *ניצלת את 5 הבדיקות החינמיות שלך*\n\n"
    "לרכישת גישה מלאה:\n"
    "💳 שלח תשלום לביט: *053\\-388\\-8381*\n"
    "📝 ציין בהודעה: *קוד גישה CarInfo*\n\n"
    "לאחר התשלום תקבל קוד גישה\\.\n"
    "הזן אותו עם הפקודה:\n"
    "`/code XXXXXXXX`"
)


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
    await update.message.reply_text(f"Your Telegram ID: `{update.effective_user.id}`", parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    allowed, left = is_allowed(user_id)
    searches_info = f"נותרו לך *{left}* בדיקות חינמיות\\." if left >= 0 else "גישה מלאה פעילה ✅"

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


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin only – stats / generate code / grant searches / list users."""
    user_id = update.effective_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        return

    args = context.args

    # /admin  →  stats dashboard
    if not args:
        stats = admin_stats()
        await update.message.reply_text(
            f"📊 *סטטיסטיקות*\n"
            f"• משתמשים: {stats['total_users']}\n"
            f"• פעילים: {stats['active_users']}\n"
            f"• סה\"כ בדיקות: {stats['total_searches']}\n"
            f"• קודים שנוצרו: {stats['total_codes']}\n"
            f"• קודים שנוצלו: {stats['used_codes']}\n\n"
            f"`/admin gen 50` ← קוד עם 50 בדיקות\n"
            f"`/admin gen 50 multi` ← קוד לשימוש מרובה\n"
            f"`/admin grant @user 30` ← הענק 30 בדיקות\n"
            f"`/admin grant @user -1` ← גישה בלתי מוגבלת\n"
            f"`/admin users` ← רשימת משתמשים",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # /admin gen [count] [multi]  →  generate a code
    if args[0] == "gen":
        try:
            count = int(args[1]) if len(args) > 1 and args[1] != "multi" else 10
        except ValueError:
            count = 10
        single = "multi" not in args
        unlimited = count == -1
        code = generate_code(searches=count, single_use=single, unlimited=unlimited)
        kind = "בלתי מוגבל" if unlimited else f"{count} בדיקות"
        use_str = "שימוש חד פעמי" if single else "שימוש מרובה"
        await update.message.reply_text(
            f"✅ קוד חדש \\({kind}, {use_str}\\):\n`{code}`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # /admin grant @username [searches]  →  grant searches to user
    if args[0] == "grant":
        if len(args) < 3:
            await update.message.reply_text(
                "שימוש: `/admin grant @username 50`",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return
        username = args[1].lstrip("@")
        try:
            amount = int(args[2])
        except ValueError:
            await update.message.reply_text("כמות חייבת להיות מספר \\(\\-1 לבלתי מוגבל\\)", parse_mode=ParseMode.MARKDOWN_V2)
            return
        target = get_user_by_username(username)
        if not target:
            await update.message.reply_text(f"משתמש @{username} לא נמצא\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return
        note = " ".join(args[3:]) if len(args) > 3 else ""
        msg = admin_grant(user_id, target["user_id"], amount, note)
        await update.message.reply_text(
            f"✅ @{username}: {msg}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    # /admin users  →  list all users
    if args[0] == "users":
        users = get_all_users()
        if not users:
            await update.message.reply_text("אין משתמשים עדיין\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return
        lines = ["👥 *משתמשים*\n"]
        for u in users[:30]:  # cap at 30 to avoid message size limit
            uname = f"@{u['username']}" if u.get("username") else f"id:{u['user_id']}"
            done = u.get("searches_done", 0)
            quota = u.get("searches_quota", 0)
            left = u.get("searches_left", 0)
            quota_str = "∞" if quota == -1 else str(quota)
            left_str = "∞" if left == -1 else str(left)
            lines.append(f"• {uname}: {done}/{quota_str} \\(נותרו: {left_str}\\)")
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    await update.message.reply_text(
        "פקודה לא מוכרת\\. נסה `/admin` לעזרה\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


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
        await update.message.reply_text(PAYMENT_MSG, parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Warn if last free search
    if left == 1:
        await update.message.reply_text(
            "⚠️ זוהי הבדיקה החינמית האחרונה שלך\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    increment_search(user_id)

    await update.message.reply_text("🔍 מחפש נתונים\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)

    try:
        record = await fetch_vehicle_data(plate)
    except Exception as exc:
        logger.error("Error fetching data for plate %s: %s", plate, exc)
        await update.message.reply_text(format_error(), parse_mode=ParseMode.MARKDOWN_V2)
        return

    if record is None:
        await update.message.reply_text(format_not_found(plate), parse_mode=ParseMode.MARKDOWN_V2)
        return

    cache.set(f"record_{plate}", record)

    summary = get_summary(record)
    keyboard = build_keyboard(plate)

    # Add remaining searches note for free users
    if left > 0 and left != -1:
        remaining = left - 1
        if remaining > 0:
            summary += f"\n\n_נותרו לך {remaining} בדיקות חינמיות_"

    manufacturer = record.get("tozeret_nm", "")
    model        = record.get("kinuy_mishari") or record.get("degem_nm") or ""
    year         = str(record.get("shnat_yitzur", ""))
    color        = record.get("tzeva_rechev", "")

    image_bytes = None
    try:
        image_url = await fetch_car_image(manufacturer, model, year, color)
        if image_url:
            async with httpx.AsyncClient(timeout=10, headers={
                "User-Agent": "CarInfoBot/1.0 (Telegram bot; educational use)"
            }) as http:
                r = await http.get(image_url)
                if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                    image_bytes = r.content
    except Exception as exc:
        logger.warning("Image fetch failed for plate %s: %s", plate, exc)

    if image_bytes:
        try:
            await update.message.reply_photo(
                photo=image_bytes,
                caption=summary,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
            )
            return
        except Exception as exc:
            logger.warning("Failed to send photo for plate %s: %s", plate, exc)

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

    await query.message.reply_text(
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
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
