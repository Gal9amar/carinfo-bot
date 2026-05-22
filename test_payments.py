import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot


class PaymentGrantTests(unittest.IsolatedAsyncioTestCase):
    async def test_paypal_approval_awaits_quota_grant(self):
        query = SimpleNamespace(
            data="approve|123456|50",
            from_user=SimpleNamespace(id=bot.ADMIN_ID),
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        update = SimpleNamespace(callback_query=query)

        with patch("bot.admin_grant", new_callable=AsyncMock) as grant:
            await bot.handle_approve_callback(update, context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            123456,
            50,
            note="PayPal payment approved",
        )
        query.edit_message_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()

    async def test_successful_telegram_payment_awaits_quota_grant(self):
        message = SimpleNamespace(
            successful_payment=SimpleNamespace(
                invoice_payload="searches:25",
                total_amount=1000,
            ),
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=987654, username="buyer"),
            message=message,
        )
        context = SimpleNamespace(
            bot=SimpleNamespace(send_message=AsyncMock()),
        )

        with patch("bot.admin_grant", new_callable=AsyncMock) as grant:
            await bot.handle_successful_payment(update, context)

        grant.assert_awaited_once_with(
            bot.ADMIN_ID,
            987654,
            25,
            note="Telegram payment",
        )
        message.reply_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
