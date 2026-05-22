import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


class MiniAppPaymentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
        os.environ["ADMIN_TELEGRAM_ID"] = "594206475"
        import api

        self.api = importlib.reload(api)

    async def test_confirm_payment_notifies_admin(self):
        with (
            patch("src.packages.get_packages", new=AsyncMock(return_value=[(7, "Test package", 50, 10)])),
            patch.object(self.api, "_notify_admin_payment", new=AsyncMock()) as notify,
        ):
            result = await self.api.confirm_payment(
                self.api.PaymentConfirmRequest(ref="abc123", package_id=7),
                user={"id": 12345, "first_name": "Buyer_Name"},
            )

        self.assertEqual(result, {"ok": True})
        notify.assert_awaited_once_with(12345, "Buyer_Name", "Test package", 50, 10, "abc123")

    async def test_confirm_payment_fails_if_admin_notification_fails(self):
        with (
            patch("src.packages.get_packages", new=AsyncMock(return_value=[(7, "Test package", 50, 10)])),
            patch.object(
                self.api,
                "_notify_admin_payment",
                new=AsyncMock(side_effect=RuntimeError("telegram down")),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await self.api.confirm_payment(
                    self.api.PaymentConfirmRequest(ref="abc123", package_id=7),
                    user={"id": 12345, "first_name": "Buyer_Name"},
                )

        self.assertEqual(raised.exception.status_code, 502)


class BotPaymentGrantTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "test-token"
        os.environ["ADMIN_TELEGRAM_ID"] = "594206475"
        import bot

        self.bot = importlib.reload(bot)

    async def test_approve_callback_awaits_admin_grant(self):
        query = SimpleNamespace(
            data="approve|12345|50",
            from_user=SimpleNamespace(id=self.bot.ADMIN_ID),
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch.object(self.bot, "admin_grant", new=AsyncMock(return_value="ok")) as grant:
            await self.bot.handle_approve_callback(update, context)

        grant.assert_awaited_once_with(
            self.bot.ADMIN_ID,
            12345,
            50,
            note="PayPal payment approved",
        )
        context.bot.send_message.assert_awaited_once()

    async def test_successful_payment_grants_paid_user(self):
        payment = SimpleNamespace(invoice_payload="searches:50", total_amount=1000)
        message = SimpleNamespace(successful_payment=payment, reply_text=AsyncMock())
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=12345, username="buyer"),
        )
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with patch.object(self.bot, "admin_grant", new=AsyncMock(return_value="ok")) as grant:
            await self.bot.handle_successful_payment(update, context)

        grant.assert_awaited_once_with(
            self.bot.ADMIN_ID,
            12345,
            50,
            note="Telegram payment",
        )
        message.reply_text.assert_awaited_once()
        context.bot.send_message.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
