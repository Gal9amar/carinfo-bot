"""
CarInfo Bot – Israel vehicle lookup Telegram bot.
Sends vehicle plate → returns all available data from data.gov.il + police stolen check.
"""

import asyncio
import logging
import os
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.api.gov_api import fetch_vehicle_data
from src.api.stolen_api import check_stolen
from src.cache import cache
from src.formatter import format_error, format_not_found, format_vehicle_message

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PLATE_RE = re.compile(r"^[\d\-]{5,10}$")


def normalize_plate(text: str) -> str:
    return text.strip().replace("-", "").replace(" ", "")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 שלום! אני בוט לבדיקת פרטי רכב ישראלי.\n\n"
        "שלח לי מספר לוחית רישוי (לדוגמה: 1234567 או 123-45-678)\n"
        "ואחזיר לך את כל המידע הזמין על הרכב מממשלת ישראל."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *שימוש בבוט*\n\n"
        "פשוט שלח מספר רכב כהודעה\\.\n\n"
        "*מה הבוט בודק:*\n"
        "• פרטי רישוי \\(data\\.gov\\.il\\)\n"
        "• יצרן, דגם, שנה, צבע, דלק\n"
        "• תוקף טסט \\+ האם פג תוקף\n"
        "• בעלות \\(ראשונה/שנייה\\.\\.\\.\n"
        "• מפרט מנוע \\(נפח, כ\"ס, זיהום\\)\n"
        "• בדיקת גנבה \\(מאגר משטרה\\)\n\n"
        "המידע מגיע ממאגרי ממשלת ישראל בזמן אמת\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


async def handle_plate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = update.message.text.strip()
    plate = normalize_plate(raw)

    if not PLATE_RE.match(plate) or len(plate) < 5:
        await update.message.reply_text(
            "🔢 שלח מספר רכב תקין בלבד (למשל: 1234567 או 12-345-67)"
        )
        return

    # Check cache
    cached = cache.get(plate)
    if cached:
        logger.info("Cache hit for plate %s", plate)
        await update.message.reply_text(
            cached, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
        )
        return

    # Show typing indicator
    await update.message.reply_text("🔍 מחפש נתונים...")

    try:
        record, stolen = await asyncio.gather(
            fetch_vehicle_data(plate),
            check_stolen(plate),
        )
    except Exception as exc:
        logger.error("Error fetching data for plate %s: %s", plate, exc)
        await update.message.reply_text(format_error(), parse_mode=ParseMode.MARKDOWN_V2)
        return

    if record is None:
        msg = format_not_found(plate)
    else:
        msg = format_vehicle_message(record, stolen)

    cache.set(plate, msg)

    await update.message.reply_text(
        msg, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True
    )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_plate))

    logger.info("Bot is starting (polling mode)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
