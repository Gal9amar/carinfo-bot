import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def _install_import_stubs() -> None:
    telegram = types.ModuleType("telegram")

    class _TelegramObject:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    for name in (
        "Update",
        "InlineKeyboardButton",
        "InlineKeyboardMarkup",
        "ReplyKeyboardMarkup",
        "ReplyKeyboardRemove",
        "KeyboardButton",
        "LabeledPrice",
    ):
        setattr(telegram, name, _TelegramObject)
    sys.modules.setdefault("telegram", telegram)

    constants = types.ModuleType("telegram.constants")
    constants.ParseMode = SimpleNamespace(MARKDOWN_V2="MarkdownV2")
    sys.modules.setdefault("telegram.constants", constants)

    ext = types.ModuleType("telegram.ext")
    ext.Application = _TelegramObject
    ext.CommandHandler = _TelegramObject
    ext.MessageHandler = _TelegramObject
    ext.CallbackQueryHandler = _TelegramObject
    ext.PreCheckoutQueryHandler = _TelegramObject
    ext.ConversationHandler = type("ConversationHandler", (), {"END": -1})
    ext.ContextTypes = SimpleNamespace(DEFAULT_TYPE=object)
    ext.filters = SimpleNamespace(
        TEXT=object(),
        COMMAND=object(),
        SUCCESSFUL_PAYMENT=object(),
        Regex=lambda *_args, **_kwargs: object(),
    )
    sys.modules.setdefault("telegram.ext", ext)

    libsql = types.ModuleType("libsql_experimental")
    libsql.connect = lambda *args, **kwargs: None
    sys.modules.setdefault("libsql_experimental", libsql)

    gov_api = types.ModuleType("src.api.gov_api")
    gov_api.fetch_vehicle_data = AsyncMock()
    sys.modules.setdefault("src.api.gov_api", gov_api)

    pdf_report = types.ModuleType("src.pdf_report")
    pdf_report.generate_pdf = lambda *args, **kwargs: b""
    sys.modules.setdefault("src.pdf_report", pdf_report)


_install_import_stubs()

import bot


class PaymentGrantTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_paypal_approval_awaits_quota_grant(self):
        query = SimpleNamespace(
            data="approve|12345|50",
            from_user=SimpleNamespace(id=bot.ADMIN_ID),
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch.object(bot, "admin_grant", AsyncMock(return_value="ok")) as grant:
            await bot.handle_approve_callback(SimpleNamespace(callback_query=query), context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            12345,
            50,
            note="PayPal payment approved",
        )
        query.edit_message_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()

    async def test_successful_telegram_payment_grants_purchaser_quota(self):
        payment = SimpleNamespace(invoice_payload="searches:100", total_amount=2000)
        message = SimpleNamespace(successful_payment=payment, reply_text=AsyncMock())
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=67890, username="buyer"),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch.object(bot, "admin_grant", AsyncMock(return_value="ok")) as grant:
            await bot.handle_successful_payment(update, context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            67890,
            100,
            note="Telegram payment approved",
        )
        message.reply_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
