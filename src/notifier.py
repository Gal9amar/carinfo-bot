"""
Shared notifier module to decouple api.py from bot.py.

bot.py registers a callback here; api.py calls it.
This avoids a circular import between bot.py and api.py.
"""

from typing import Callable, Awaitable, Optional

# Registered by bot.py after the bot instance is ready
_notify_admin_payment_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_payment_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    """Called by bot.py to register the admin notification function."""
    global _notify_admin_payment_fn
    _notify_admin_payment_fn = fn


async def notify_admin_payment(
    user_id: int, name: str, label: str, searches: int, price: int, ref: str
) -> None:
    """Called by api.py when a user confirms payment via the Mini App."""
    if _notify_admin_payment_fn is None:
        return
    await _notify_admin_payment_fn(user_id, name, label, searches, price, ref)
