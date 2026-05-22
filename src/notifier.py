"""
Shared notifier module to decouple api.py from bot.py.

bot.py registers callbacks here; api.py calls them.
This avoids a circular import between bot.py and api.py.
"""

from typing import Callable, Awaitable, Optional

_notify_admin_payment_fn: Optional[Callable[..., Awaitable[None]]] = None
_notify_admin_ticket_fn:  Optional[Callable[..., Awaitable[None]]] = None
_notify_user_ticket_fn:   Optional[Callable[..., Awaitable[None]]] = None


def register_payment_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    global _notify_admin_payment_fn
    _notify_admin_payment_fn = fn


def register_ticket_notifiers(
    admin_fn: Callable[..., Awaitable[None]],
    user_fn:  Callable[..., Awaitable[None]],
) -> None:
    global _notify_admin_ticket_fn, _notify_user_ticket_fn
    _notify_admin_ticket_fn = admin_fn
    _notify_user_ticket_fn  = user_fn


async def notify_admin_payment(
    user_id: int, name: str, label: str, searches: int, price: int, ref: str
) -> None:
    if _notify_admin_payment_fn is None:
        return
    await _notify_admin_payment_fn(user_id, name, label, searches, price, ref)


async def notify_admin_ticket(ticket_id: int, user_id: int, name: str, subject: str, message: str) -> None:
    if _notify_admin_ticket_fn is None:
        return
    await _notify_admin_ticket_fn(ticket_id, user_id, name, subject, message)


async def notify_user_ticket_reply(user_id: int, ticket_id: int, subject: str, reply: str) -> None:
    if _notify_user_ticket_fn is None:
        return
    await _notify_user_ticket_fn(user_id, ticket_id, subject, reply)
