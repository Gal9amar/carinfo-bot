import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
