import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot
from src import wa_menu


class PackageCacheTests(unittest.TestCase):
    def test_telegram_empty_package_cache_does_not_fall_back_to_defaults(self):
        with patch("src.packages._cache", []):
            self.assertEqual(bot._pkgs(), [])

    def test_whatsapp_empty_package_cache_does_not_fall_back_to_defaults(self):
        with patch("src.packages._cache", []):
            self.assertEqual(wa_menu._get_pkgs(), [])


class AdminPackageStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_package_list_callback_clears_pending_edit_state(self):
        query = SimpleNamespace(
            from_user=SimpleNamespace(id=bot.ADMIN_ID),
            data="admpkg|list",
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            user_data={
                "admin_setting": "pkg_edit_searches",
                "admin_pkg_id": 1,
                "admin_pkg_searches": 1234567,
            }
        )

        with patch("src.packages.get_packages", new=AsyncMock(return_value=[])):
            await bot.handle_admpkg_callback(update, context)

        self.assertNotIn("admin_setting", context.user_data)
        self.assertNotIn("admin_pkg_id", context.user_data)
        self.assertNotIn("admin_pkg_searches", context.user_data)
        query.edit_message_text.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
