import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot


class PaymentGrantTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_paypal_approval_grants_searches(self):
        query = SimpleNamespace(
            from_user=SimpleNamespace(id=bot.ADMIN_ID),
            data="approve|777|50",
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch("bot.admin_grant", new=AsyncMock(return_value="ok")) as grant:
            await bot.handle_approve_callback(update, context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            777,
            50,
            note="PayPal payment approved",
        )
        query.edit_message_text.assert_awaited_once()

    async def test_successful_telegram_payment_grants_searches(self):
        message = SimpleNamespace(
            successful_payment=SimpleNamespace(
                invoice_payload="searches:100",
                total_amount=2000,
            ),
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=333, username="buyer"),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch("bot.admin_grant", new=AsyncMock(return_value="ok")) as grant:
            await bot.handle_successful_payment(update, context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            333,
            100,
            note="Telegram payment",
        )
        message.reply_text.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
