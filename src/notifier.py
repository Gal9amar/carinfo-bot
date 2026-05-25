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


_notify_user_payment_approved_fn: Optional[Callable[..., Awaitable[None]]] = None
_notify_user_payment_declined_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_payment_result_notifiers(
    approved_fn: Callable[..., Awaitable[None]],
    declined_fn: Callable[..., Awaitable[None]],
) -> None:
    global _notify_user_payment_approved_fn, _notify_user_payment_declined_fn
    _notify_user_payment_approved_fn = approved_fn
    _notify_user_payment_declined_fn = declined_fn


async def notify_user_payment_approved(user_id: int, label: str, searches: int) -> None:
    if _notify_user_payment_approved_fn:
        await _notify_user_payment_approved_fn(user_id, label, searches)


async def notify_user_payment_declined(user_id: int, label: str) -> None:
    if _notify_user_payment_declined_fn:
        await _notify_user_payment_declined_fn(user_id, label)


_notify_user_admin_grant_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_admin_grant_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    global _notify_user_admin_grant_fn
    _notify_user_admin_grant_fn = fn


async def notify_user_admin_grant(user_id: int, searches: int) -> None:
    if _notify_user_admin_grant_fn:
        await _notify_user_admin_grant_fn(user_id, searches)


_broadcast_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_broadcast_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    global _broadcast_fn
    _broadcast_fn = fn


async def notify_broadcast(message: str) -> dict:
    if _broadcast_fn is None:
        return {"ok": False, "sent": 0, "failed": 0}
    return await _broadcast_fn(message)


_send_user_message_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_user_message_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    global _send_user_message_fn
    _send_user_message_fn = fn


async def send_user_message(user_id: int, message: str) -> bool:
    if _send_user_message_fn is None:
        return False
    return await _send_user_message_fn(user_id, message)


_broadcast_photo_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_broadcast_photo_notifier(fn: Callable[..., Awaitable[None]]) -> None:
    global _broadcast_photo_fn
    _broadcast_photo_fn = fn


async def notify_broadcast_photo(message: str, image_b64: str) -> dict:
    if _broadcast_photo_fn is None:
        return {"ok": False, "sent": 0, "failed": 0}
    return await _broadcast_photo_fn(message, image_b64)


_notify_admin_order_fn = None


def register_admin_order_notifier(fn) -> None:
    global _notify_admin_order_fn
    _notify_admin_order_fn = fn


async def notify_admin_order(ref: str, status: str, label: str, amount, username: str, member_id) -> None:
    if _notify_admin_order_fn:
        await _notify_admin_order_fn(ref, status, label, amount, username, member_id)


_send_user_document_fn: Optional[Callable[..., Awaitable[None]]] = None


def register_user_document_sender(fn: Callable[..., Awaitable[None]]) -> None:
    global _send_user_document_fn
    _send_user_document_fn = fn


async def send_user_document(user_id: int, pdf_bytes: bytes, filename: str, caption: str = "") -> bool:
    if _send_user_document_fn is None:
        return False
    return await _send_user_document_fn(user_id, pdf_bytes, filename, caption)
