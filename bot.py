"""
CarInfo Bot – Israel vehicle lookup Telegram bot.
"""

import asyncio
import logging
import os
import re
import sys
import json
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
from src.api.image_api import fetch_car_image
from src.cache import cache
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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 שלום\\! אני בוט לבדיקת פרטי רכב ישראלי\\.\n\n"
        "שלח לי מספר לוחית רישוי \\(לדוגמה: 1234567\\)\n"
        "ואחזיר לך את כל המידע הזמין על הרכב\\.",
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
        "📅 היסטוריה · 🔔 ריקולים",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = update.message.text.strip()
    plate = normalize_plate(raw)

    if not PLATE_RE.match(plate) or len(plate) < 5:
        await update.message.reply_text(
            "🔢 שלח מספר רכב תקין בלבד \\(למשל: 1234567\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

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

    # Cache the full record for callback reuse (keyed by plate)
    cache.set(f"record_{plate}", record)

    summary = get_summary(record)
    keyboard = build_keyboard(plate)

    # Try to send with car image
    manufacturer = record.get("tozeret_nm", "")
    model        = record.get("kinuy_mishari") or record.get("degem_nm") or ""
    year         = str(record.get("shnat_yitzur", ""))
    color        = record.get("tzeva_rechev", "")

    image_url = None
    try:
        image_url = await fetch_car_image(manufacturer, model, year, color)
    except Exception as exc:
        logger.warning("Image fetch failed for plate %s: %s", plate, exc)

    if image_url:
        try:
            await update.message.reply_photo(
                photo=image_url,
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
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plate))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
