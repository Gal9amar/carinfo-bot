"""Activity mirror: a live copy of every private-chat interaction in one Telegram group topic.

For each user action a short header is posted (who + what they did); each bot reply is then
re-sent **exactly as the user saw it** (same HTML formatting, same buttons, same photos/files,
same tables) as a reply to that header.

* Incoming updates are described by ``describe_update`` (blocking TypeHandler in bot.py).
* Outgoing messages are captured by ``MirrorBot`` (every send/edit/delete goes through it) and by
  ``src.rich`` for table messages.
* Buttons in the copy are inert: callback / Mini App / copy buttons become a "this is only a copy"
  alert, so nobody in the group can trigger an action; plain URL buttons stay links.
* Ops are sent one per ``flush`` tick (≈3 s) to respect the group's ~20 msgs/min limit;
  messages the bot deletes before they are mirrored (e.g. progress steps) are dropped.
  The mirror never raises into the bot: failures are logged and dropped.

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
HEADER_TTL = 600          # a reply is attached to the user's last action header for this long
CONFIG_TTL = 15           # seconds a settings read is cached

_ops: deque = deque(maxlen=MAX_QUEUE)
_dropped = 0
_who: dict[int, tuple[str, str]] = {}      # uid -> (name, @username)
_hdr_enq: dict[int, float] = {}             # uid -> when a header op was last queued
_hdr_msg: dict[int, int] = {}               # uid -> message_id of that header in the mirror topic
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


def _push(op: dict) -> None:
    global _dropped
    if len(_ops) == _ops.maxlen:
        _dropped += 1
    _ops.append(op)


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


def neutral_markup(markup):
    """Same-looking inline keyboard whose buttons cannot trigger anything. None if not inline."""
    try:
        from telegram import InlineKeyboardMarkup
        if not isinstance(markup, InlineKeyboardMarkup):
            return None
        data = markup.to_dict()
        for row in data.get("inline_keyboard", []):
            for btn in row:
                if "url" in btn:
                    continue                                # plain links stay links
                for key in ("callback_data", "web_app", "copy_text", "login_url", "switch_inline_query",
                            "switch_inline_query_current_chat", "switch_inline_query_chosen_chat", "pay", "callback_game"):
                    btn.pop(key, None)
                btn["callback_data"] = "mirror|noop"        # keeps text + style, does nothing
        return InlineKeyboardMarkup.de_json(data, None)
    except Exception as exc:
        logger.warning("mirror keyboard copy failed: %s", type(exc).__name__)
        return None


def _drop_pending(uid: int, message_id) -> None:
    """Forget pending copies of a message (it was edited again or deleted before we mirrored it)."""
    if message_id is None:
        return
    keep = [o for o in _ops if not (o.get("uid") == uid and o.get("mid") == message_id and not o.get("sent"))]
    if len(keep) != len(_ops):
        _ops.clear()
        _ops.extend(keep)


def _need_header(uid: int) -> bool:
    return time.time() - _hdr_enq.get(uid, 0) > HEADER_TTL


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
        _hdr_enq[uid] = time.time()
        _push({"op": "header", "uid": uid, "name": name, "uname": uname, "text": what, "t": _clock()})
    except Exception as exc:
        logger.warning("mirror incoming failed: %s", type(exc).__name__)


async def record_outgoing(chat_id, kind: str = "text", text: str = "", parse_mode=None, reply_markup=None,
                          message_id=None, file_id=None, edited: bool = False) -> None:
    """kind: text | photo | document | rich. Queues an exact copy of what the user was shown."""
    try:
        if not isinstance(chat_id, int) or chat_id <= 0 or chat_id == ADMIN_ID:
            return                       # groups/channels and the admin's own chat are not mirrored
        cfg = await _config()
        if not cfg["enabled"] or chat_id == cfg["chat"]:
            return
        if edited:
            _drop_pending(chat_id, message_id)
        if edited or _need_header(chat_id):
            name = await _display_name(chat_id)
            _hdr_enq[chat_id] = time.time()
            _push({"op": "header", "uid": chat_id, "name": name, "uname": "", "t": _clock(),
                   "text": "✏️ עדכון הודעה" if edited else "📤 הודעה מהבוט", "push": True})
        op = {"op": kind, "uid": chat_id, "mid": message_id, "text": text, "pm": parse_mode,
              "markup": neutral_markup(reply_markup), "file_id": file_id}
        if _redact.get():
            op.update(op=("text"), text="🔒 תוכן מוסתר", pm=None, markup=None, file_id=None)
        _push(op)
    except Exception as exc:
        logger.warning("mirror outgoing failed: %s", type(exc).__name__)


def record_deleted(chat_id, message_id) -> None:
    try:
        _drop_pending(chat_id, message_id)
    except Exception:
        pass


class MirrorBot(ExtBot):
    """ExtBot that reports every message it sends, edits or deletes to the mirror."""

    async def send_message(self, chat_id, text, *args, **kwargs):
        result = await super().send_message(chat_id, text, *args, **kwargs)
        await record_outgoing(chat_id, "text", text, kwargs.get("parse_mode"), kwargs.get("reply_markup"),
                              getattr(result, "message_id", None))
        return result

    async def edit_message_text(self, text, chat_id=None, message_id=None, *args, **kwargs):
        result = await super().edit_message_text(text, chat_id, message_id, *args, **kwargs)
        await record_outgoing(chat_id, "text", text, kwargs.get("parse_mode"), kwargs.get("reply_markup"),
                              message_id, edited=True)
        return result

    async def send_photo(self, chat_id, photo, caption=None, *args, **kwargs):
        result = await super().send_photo(chat_id, photo, caption, *args, **kwargs)
        sizes = getattr(result, "photo", None) or []
        await record_outgoing(chat_id, "photo", caption or "", kwargs.get("parse_mode"), kwargs.get("reply_markup"),
                              getattr(result, "message_id", None), file_id=sizes[-1].file_id if sizes else None)
        return result

    async def send_document(self, chat_id, document, *args, **kwargs):
        result = await super().send_document(chat_id, document, *args, **kwargs)
        doc = getattr(result, "document", None)
        await record_outgoing(chat_id, "document", kwargs.get("caption") or "", kwargs.get("parse_mode"),
                              kwargs.get("reply_markup"), getattr(result, "message_id", None),
                              file_id=getattr(doc, "file_id", None))
        return result

    async def delete_message(self, chat_id, message_id, *args, **kwargs):
        result = await super().delete_message(chat_id, message_id, *args, **kwargs)
        record_deleted(chat_id, message_id)
        return result


# ── sending the copies ─────────────────────────────────────────────────────

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


def _header_html(op: dict) -> str:
    from src.messages import esc
    who = f"<b>{esc(op['name'])}</b>" + (f" {esc(op['uname'])}" if op.get("uname") else "")
    return f"{'🤖' if op.get('push') else '👤'} {who} <code>{op['uid']}</code> · {op['t']}\n{esc(op['text'])}"


async def _send_op(bot, cfg: dict, op: dict) -> None:
    """Send one queued op; raises on failure. Records header message ids for threading replies."""
    from telegram import ReplyParameters
    common = {"message_thread_id": cfg["thread"], "disable_notification": True}
    if op["op"] == "header":
        sent = await bot.send_message(cfg["chat"], _header_html(op), parse_mode="HTML", **common)
        _hdr_msg[op["uid"]] = sent.message_id
        return
    reply_to = _hdr_msg.get(op["uid"])
    if reply_to:
        common["reply_parameters"] = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)
    pm, markup = op.get("pm"), op.get("markup")
    if op["op"] == "rich":
        from src import rich
        if await rich.send_rich_message(cfg["chat"], op["text"], markup, mirror=False, message_thread_id=cfg["thread"],
                                        reply_to=reply_to, force=True):
            return
        from src.messages import strip_html
        await bot.send_message(cfg["chat"], strip_html(op["text"]) or "(טבלה)", reply_markup=markup, **common)
    elif op["op"] == "photo" and op.get("file_id"):
        await bot.send_photo(cfg["chat"], op["file_id"], caption=op["text"] or None, parse_mode=pm, reply_markup=markup, **common)
    elif op["op"] == "document" and op.get("file_id"):
        await bot.send_document(cfg["chat"], op["file_id"], caption=op["text"] or None, parse_mode=pm, reply_markup=markup, **common)
    else:
        await bot.send_message(cfg["chat"], op["text"] or "(ריק)", parse_mode=pm, reply_markup=markup, **common)


async def _disable(bot, exc) -> None:
    """The group/topic is gone or the bot lost access: stop mirroring and tell the admin once."""
    global _dropped
    from src.db import set_bot_setting
    try:
        await set_bot_setting("mirror_enabled", "0")
        invalidate()
        _ops.clear()
        _dropped = 0
        await bot.send_message(
            ADMIN_ID,
            f"🪞 מראה הפעולות כובתה: לא הצלחתי לשלוח לקבוצה ({type(exc).__name__}).\n"
            "ודא שהבוט עדיין בקבוצה ויכול לכתוב בטופיק, ואז שלח /mirror_set עם קישור לטופיק.",
        )
    except Exception as e2:
        logger.warning("mirror disable failed: %s", type(e2).__name__)


async def flush(bot) -> None:
    """Send the oldest queued op. Called by a repeating job every ~3 s."""
    global _dropped, _pause_until, _last_warn
    if not _ops or time.time() < _pause_until:
        return
    cfg = await _config()
    if not cfg["enabled"] or not cfg["chat"]:
        _ops.clear()
        _dropped = 0
        return
    if _dropped:
        n, _dropped = _dropped, 0
        _ops.appendleft({"op": "header", "uid": 0, "name": "מראה", "uname": "", "t": _clock(), "push": True,
                         "text": f"⚠️ הושמטו {n} אירועים בגלל עומס"}) if len(_ops) < (_ops.maxlen or 0) else None
    op = _ops[0]
    try:
        await _send_op(bot, cfg, op)
        _ops.popleft()
    except Exception as exc:
        from telegram.error import BadRequest, ChatMigrated, Forbidden, RetryAfter
        if isinstance(exc, RetryAfter):
            _pause_until = time.time() + float(exc.retry_after) + 1     # the op stays at the head of the queue
            return
        _ops.popleft()                                                   # drop the op that failed
        _dropped += 1
        permanent = isinstance(exc, (Forbidden, ChatMigrated)) or (
            isinstance(exc, BadRequest) and any(m in str(exc).lower() for m in ("chat not found", "thread not found", "topic"))
        )
        if permanent:
            await _disable(bot, exc)
        elif time.time() - _last_warn > 60:
            _last_warn = time.time()
            logger.warning("mirror send failed: %s %s", type(exc).__name__, str(exc)[:120])
