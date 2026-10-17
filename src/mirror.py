"""Activity mirror: copy every private-chat interaction (what the user did and what the bot
answered) into one Telegram group topic, as a live feed for the admin.

* Incoming updates are described by ``describe_update`` (TypeHandler in bot.py).
* Outgoing messages are captured by ``MirrorBot`` (every send/edit goes through it) and by
  ``src.rich`` for table messages.
* Events are queued and flushed in batches (``flush``) so the group's ~20 msgs/min limit
  is never hit. The mirror never raises into the bot: failures are logged and dropped.

Bind it by sending ``/mirror_here`` (admin only) inside the target topic; toggle with the
``mirror_enabled`` setting. The admin's own chat is never mirrored. Secrets are masked:
promo codes the user types and delivered product content (see ``redacted``).
"""

from __future__ import annotations

import contextlib
import contextvars
import logging
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone

from telegram.ext import ExtBot

logger = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))
MAX_QUEUE = 400
MAX_TEXT = 600            # characters of a bot reply shown in the mirror
BATCH_CHARS = 3800        # stay below Telegram's 4096 limit
CONFIG_TTL = 15           # seconds a settings read is cached

_events: deque = deque(maxlen=MAX_QUEUE)
_dropped = 0
_who: dict[int, tuple[str, str]] = {}      # uid -> (name, @username)
_cfg = {"at": 0.0, "enabled": False, "chat": None, "thread": None}
_pause_until = 0.0
_redact: contextvars.ContextVar[bool] = contextvars.ContextVar("mirror_redact", default=False)
_last_warn = 0.0


# ── configuration ──────────────────────────────────────────────────────────

def invalidate() -> None:
    _cfg["at"] = 0.0


async def _config() -> dict:
    if time.time() - _cfg["at"] < CONFIG_TTL:
        return _cfg
    from src.db import get_bot_setting
    try:
        chat = (await get_bot_setting("mirror_chat_id")) or ""
        thread = (await get_bot_setting("mirror_thread_id")) or ""
        _cfg.update(
            enabled=(await get_bot_setting("mirror_enabled")) == "1" and bool(chat),
            chat=int(chat) if chat.lstrip("-").isdigit() else None,
            thread=int(thread) if thread.isdigit() else None,
            at=time.time(),
        )
    except Exception as exc:
        logger.warning("mirror config read failed: %s", type(exc).__name__)
        _cfg["at"] = time.time()
    return _cfg


@contextlib.contextmanager
def redacted():
    """Mirror what happens inside this block, but hide message bodies (e.g. delivered keys)."""
    token = _redact.set(True)
    try:
        yield
    finally:
        _redact.reset(token)


def parse_topic_link(text: str) -> tuple[int, int | None] | None:
    """'https://t.me/c/4467084312/2[/15]' -> (-1004467084312, 2). Private-group links only."""
    import re
    m = re.search(r"t\.me/c/(\d+)(?:/(\d+))?", text or "")
    if not m:
        return None
    chat = int(f"-100{m.group(1)}")
    topic = int(m.group(2)) if m.group(2) else None
    return chat, (topic if topic and topic > 1 else None)   # topic id 1 is the General topic


# ── capturing events ───────────────────────────────────────────────────────

def _clock() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Jerusalem")).strftime("%H:%M:%S")
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(hours=3)).strftime("%H:%M:%S")


def _push(event: dict) -> None:
    global _dropped
    if len(_events) == _events.maxlen:
        _dropped += 1
    _events.append(event)


def _button_labels(markup) -> list[str]:
    labels: list[str] = []
    try:
        for row in getattr(markup, "inline_keyboard", None) or []:
            for b in row:
                if getattr(b, "text", None):
                    labels.append(b.text)
    except Exception:
        pass
    return labels[:10]


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


def describe_update(update, user_data=None) -> tuple[int, str, str, str] | None:
    """-> (uid, full_name, @username, what-they-did) for a private-chat update, else None."""
    user, chat = update.effective_user, update.effective_chat
    if user is None or chat is None or chat.type != "private" or user.id == ADMIN_ID:
        return None
    name = user.full_name or user.first_name or str(user.id)
    uname = f"@{user.username}" if user.username else ""
    q = update.callback_query
    msg = update.message
    if q is not None:
        label = q.data or ""
        try:
            for row in getattr(q.message.reply_markup, "inline_keyboard", []) or []:
                for b in row:
                    if getattr(b, "callback_data", None) == q.data:
                        label = b.text
        except Exception:
            pass
        what = f"🔘 לחץ על: {label}"
    elif msg is not None:
        text = msg.text or ""
        if msg.successful_payment:
            what = "💳 תשלום הושלם"
        elif text.startswith("/"):
            cmd, _, arg = text.partition(" ")
            what = f"⌨️ פקודה: {cmd}" + (" ●●●" if cmd.lower().startswith("/code") and arg else (f" {arg}" if arg else ""))
        elif user_data is not None and "code_is_admin" in user_data:
            what = "🔑 הזין קוד הטבה (הוסתר)"
        elif text:
            what = f"💬 שלח: {text}"
        elif msg.photo:
            what = "📷 שלח תמונה"
        elif msg.document:
            what = "📎 שלח קובץ"
        elif msg.location:
            what = "📍 שלח מיקום"
        elif msg.contact:
            what = "👤 שלח איש קשר"
        else:
            what = "📨 שלח הודעה (ללא טקסט)"
    elif update.pre_checkout_query is not None:
        what = "💳 אישור תשלום (pre-checkout)"
    else:
        return None
    return user.id, name, uname, _clip(what, 400)


async def record_incoming(update, user_data=None) -> None:
    try:
        cfg = await _config()
        if not cfg["enabled"]:
            return
        d = describe_update(update, user_data)
        if not d:
            return
        uid, name, uname, what = d
        _who[uid] = (name, uname)
        _push({"kind": "in", "uid": uid, "name": name, "uname": uname, "text": what, "t": _clock()})
    except Exception as exc:
        logger.warning("mirror incoming failed: %s", type(exc).__name__)


async def record_outgoing(chat_id, text: str, reply_markup=None, edited: bool = False, kind: str = "") -> None:
    try:
        if not isinstance(chat_id, int) or chat_id <= 0 or chat_id == ADMIN_ID:
            return                       # groups/channels and the admin's own chat are not mirrored
        cfg = await _config()
        if not cfg["enabled"] or chat_id == cfg["chat"]:
            return
        from src.messages import strip_html
        body = "🔒 תוכן מוסתר" if _redact.get() else _clip(strip_html(text or ""), MAX_TEXT)
        _push({
            "kind": "out", "uid": chat_id, "text": body, "edited": edited,
            "buttons": [] if _redact.get() else _button_labels(reply_markup), "t": _clock(), "label": kind,
        })
    except Exception as exc:
        logger.warning("mirror outgoing failed: %s", type(exc).__name__)


class MirrorBot(ExtBot):
    """ExtBot that reports every message it sends or edits to the mirror."""

    async def send_message(self, chat_id, text, *args, **kwargs):
        result = await super().send_message(chat_id, text, *args, **kwargs)
        await record_outgoing(chat_id, text, kwargs.get("reply_markup"))
        return result

    async def edit_message_text(self, text, chat_id=None, message_id=None, *args, **kwargs):
        result = await super().edit_message_text(text, chat_id, message_id, *args, **kwargs)
        await record_outgoing(chat_id, text, kwargs.get("reply_markup"), edited=True)
        return result

    async def send_photo(self, chat_id, photo, caption=None, *args, **kwargs):
        result = await super().send_photo(chat_id, photo, caption, *args, **kwargs)
        await record_outgoing(chat_id, f"📷 {caption or '(תמונה)'}", kwargs.get("reply_markup"))
        return result

    async def send_document(self, chat_id, document, *args, **kwargs):
        result = await super().send_document(chat_id, document, *args, **kwargs)
        await record_outgoing(chat_id, f"📎 {kwargs.get('caption') or kwargs.get('filename') or '(קובץ)'}", kwargs.get("reply_markup"))
        return result


# ── rendering + flushing ───────────────────────────────────────────────────

async def _display_name(uid: int) -> str:
    if uid in _who:
        return _who[uid][0]
    try:
        from src.users import get_user_by_id
        u = await get_user_by_id(uid)
        if u:
            _who[uid] = (u.get("full_name") or str(uid), f"@{u['username']}" if u.get("username") else "")
            return _who[uid][0]
    except Exception:
        pass
    return str(uid)


async def _render(ev: dict) -> str:
    from src.messages import esc
    if ev["kind"] == "in":
        who = f"<b>{esc(ev['name'])}</b>" + (f" {esc(ev['uname'])}" if ev["uname"] else "")
        return f"👤 {who} <code>{ev['uid']}</code> · {ev['t']}\n{esc(ev['text'])}"
    name = await _display_name(ev["uid"])
    verb = "✏️ עדכן הודעה אצל " if ev.get("edited") else "🤖 ענה ל"
    body = f"<blockquote expandable>{esc(ev['text'])}</blockquote>" if ev["text"] else ""
    buttons = f"\n🔘 {esc(' · '.join(ev['buttons']))}" if ev.get("buttons") else ""
    return f"{verb}<b>{esc(name)}</b> · {ev['t']}\n{body}{buttons}"


async def _disable(bot, exc) -> None:
    """The group/topic is gone or the bot lost access: stop mirroring and tell the admin once."""
    global _dropped
    from src.db import set_bot_setting
    try:
        await set_bot_setting("mirror_enabled", "0")
        invalidate()
        _events.clear()
        _dropped = 0
        await bot.send_message(
            ADMIN_ID,
            f"🪞 מראה הפעולות כובתה: לא הצלחתי לשלוח לקבוצה ({type(exc).__name__}).\n"
            "ודא שהבוט עדיין בקבוצה ויכול לכתוב בטופיק, ואז שלח /mirror_set עם קישור לטופיק.",
        )
    except Exception as e2:
        logger.warning("mirror disable failed: %s", type(e2).__name__)


async def flush(bot) -> None:
    """Send queued events as one message. Called by a repeating job every few seconds."""
    global _dropped, _pause_until, _last_warn
    if not _events or time.time() < _pause_until:
        return
    cfg = await _config()
    if not cfg["enabled"] or not cfg["chat"]:
        _events.clear()
        _dropped = 0
        return
    parts: list[str] = []
    size = 0
    taken: list[dict] = []
    if _dropped:
        parts.append(f"⚠️ הושמטו {_dropped} אירועים בגלל עומס")
        size += len(parts[0])
    while _events:
        text = await _render(_events[0])
        if parts and size + len(text) > BATCH_CHARS:
            break
        taken.append(_events.popleft())
        parts.append(text)
        size += len(text) + 2
    try:
        await bot.send_message(
            cfg["chat"], "\n\n".join(parts), parse_mode="HTML",
            message_thread_id=cfg["thread"], disable_notification=True,
        )
        _dropped = 0
    except Exception as exc:
        from telegram.error import BadRequest, ChatMigrated, Forbidden, RetryAfter
        if isinstance(exc, RetryAfter):
            _pause_until = time.time() + float(exc.retry_after) + 1
            room = (_events.maxlen or 0) - len(_events)
            for ev in reversed(taken[-room:] if room > 0 else []):
                _events.appendleft(ev)
            _dropped += max(0, len(taken) - max(room, 0))
        else:
            _dropped += len(taken)    # the next batch reports how many events were lost
            permanent = isinstance(exc, (Forbidden, ChatMigrated)) or (
                isinstance(exc, BadRequest) and any(s in str(exc).lower() for s in ("chat not found", "thread not found", "topic"))
            )
            if permanent:
                await _disable(bot, exc)
            elif time.time() - _last_warn > 60:
                _last_warn = time.time()
                logger.warning("mirror send failed: %s %s", type(exc).__name__, str(exc)[:120])
