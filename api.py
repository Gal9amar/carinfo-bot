"""
FastAPI app — serves REST API + React static files.
Replaces the simple health server. Runs on the same PORT as before.
"""
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID   = int(os.environ.get("ADMIN_TELEGRAM_ID", "594206475"))
PAYPAL_ME  = os.environ.get("PAYPAL_ME", "https://www.paypal.me/G9ST")

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_init_data(init_data: str) -> dict | None:
    """Validate Telegram WebApp initData HMAC. Returns user dict or None."""
    if not init_data or not BOT_TOKEN:
        return None
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_val = parsed.pop("hash", None)
    if not hash_val:
        return None
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, hash_val):
        return None
    user_str = parsed.get("user")
    return json.loads(user_str) if user_str else {}


async def _get_user(request: Request) -> dict:
    init_data = request.headers.get("X-Init-Data", "")
    user = _validate_init_data(init_data)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid init data")
    return user


async def _require_admin(user: dict = Depends(_get_user)) -> dict:
    if user.get("id") != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ── Health ──────────────────────────────────────────────────────────────────
@api.get("/health")
async def health():
    return {"ok": True}


# ── Public ──────────────────────────────────────────────────────────────────
@api.get("/api/packages")
async def list_packages():
    from src.packages import get_packages
    pkgs = await get_packages()
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3]} for p in pkgs]


@api.get("/api/user")
async def get_user_info(user: dict = Depends(_get_user)):
    from src.users import get_user_by_id
    from src.db import get_bot_setting
    db_user = await get_user_by_id(int(user["id"]))
    maintenance = (await get_bot_setting("maintenance")) == "1"
    left = db_user.get("searches_left", 0) if db_user else 0
    return {
        "id": user["id"],
        "first_name": user.get("first_name", ""),
        "is_admin": int(user["id"]) == ADMIN_ID,
        "searches_left": left,
        "maintenance": maintenance,
    }


class PaymentInitRequest(BaseModel):
    package_id: int


@api.post("/api/payment/initiate")
async def initiate_payment(body: PaymentInitRequest, user: dict = Depends(_get_user)):
    from src.packages import get_packages
    import secrets as _secrets
    from src.db import execute
    pkgs = await get_packages()
    pkg = next((p for p in pkgs if p[0] == body.package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    pid, label, searches, price = pkg
    ref = _secrets.token_hex(8)
    await execute(
        "INSERT OR IGNORE INTO pending_payments (ref, phone, searches, price, label) VALUES (?,?,?,?,?)",
        [ref, str(user["id"]), searches, price, label],
    )
    return {"ref": ref, "paypal_url": f"{PAYPAL_ME}/{price}", "label": label, "price": price, "searches": searches}


class PaymentConfirmRequest(BaseModel):
    ref: str
    package_id: int


@api.post("/api/payment/confirm")
async def confirm_payment(body: PaymentConfirmRequest, user: dict = Depends(_get_user)):
    """User clicked 'I paid' — notify admin via bot."""
    from src.packages import get_packages
    pkgs = await get_packages()
    pkg = next((p for p in pkgs if p[0] == body.package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    pid, label, searches, price = pkg
    # Trigger admin notification via shared notifier (avoids circular import with bot.py)
    try:
        from src.notifier import notify_admin_payment
        uid  = int(user["id"])
        name = user.get("first_name", str(uid))
        await notify_admin_payment(uid, name, label, searches, price, body.ref)
    except Exception:
        pass
    return {"ok": True}


# ── User history ─────────────────────────────────────────────────────────────
@api.get("/api/user/history")
async def get_user_history(user: dict = Depends(_get_user)):
    from src.users import get_search_history
    plates = await get_search_history(int(user["id"]), limit=20)
    return plates


# ── Vehicle report ───────────────────────────────────────────────────────────
@api.get("/api/vehicle/{plate}")
async def get_vehicle(plate: str, user: dict = Depends(_get_user)):
    from src.api.gov_api import fetch_vehicle_data
    from src.cache import cache
    plate = plate.replace("-", "").replace(" ", "")
    record = cache.get(plate)
    if record is None:
        record = await fetch_vehicle_data(plate)
        if record:
            cache.set(plate, record)
    if not record:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return record


# ── Admin ────────────────────────────────────────────────────────────────────
@api.get("/api/admin/stats")
async def admin_stats_api(_: dict = Depends(_require_admin)):
    from src.users import admin_stats
    return await admin_stats()


@api.get("/api/admin/users")
async def admin_users_api(_: dict = Depends(_require_admin)):
    from src.users import get_all_users
    return await get_all_users()


@api.get("/api/admin/settings")
async def admin_get_settings(_: dict = Depends(_require_admin)):
    from src.db import get_bot_setting
    import src.users as _u
    return {
        "maintenance": (await get_bot_setting("maintenance")) == "1",
        "free_searches": _u.FREE_SEARCHES,
    }


class SettingsUpdate(BaseModel):
    maintenance: bool | None = None
    free_searches: int | None = None


@api.post("/api/admin/settings")
async def admin_update_settings(body: SettingsUpdate, _: dict = Depends(_require_admin)):
    from src.db import set_bot_setting
    import src.users as _u
    if body.maintenance is not None:
        await set_bot_setting("maintenance", "1" if body.maintenance else "0")
    if body.free_searches is not None:
        _u.FREE_SEARCHES = body.free_searches
    return {"ok": True}


@api.get("/api/admin/packages")
async def admin_list_packages(_: dict = Depends(_require_admin)):
    from src.packages import get_packages
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3]} for p in pkgs]


class PackageBody(BaseModel):
    label: str
    searches: int
    price: int


@api.post("/api/admin/packages")
async def admin_add_package(body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import add_package, get_packages
    await add_package(body.label, body.searches, body.price)
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3]} for p in pkgs]


@api.put("/api/admin/packages/{pkg_id}")
async def admin_update_package(pkg_id: int, body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import update_package
    await update_package(pkg_id, body.label, body.searches, body.price)
    return {"ok": True}


@api.delete("/api/admin/packages/{pkg_id}")
async def admin_delete_package(pkg_id: int, _: dict = Depends(_require_admin)):
    from src.packages import delete_package
    await delete_package(pkg_id)
    return {"ok": True}


class GrantBody(BaseModel):
    searches: int


@api.post("/api/admin/users/{user_id}/grant")
async def admin_grant_user(user_id: int, body: GrantBody, admin: dict = Depends(_require_admin)):
    from src.users import admin_grant
    msg = await admin_grant(int(admin["id"]), user_id, body.searches)
    return {"ok": True, "msg": msg}


# ── Tickets (user) ────────────────────────────────────────────────────────────
class TicketCreateBody(BaseModel):
    subject: str
    message: str


class TicketReplyBody(BaseModel):
    message: str


@api.post("/api/tickets")
async def create_ticket_api(body: TicketCreateBody, user: dict = Depends(_get_user)):
    from src.tickets import create_ticket
    subject = body.subject.strip()[:120]
    message = body.message.strip()[:2000]
    if not subject or not message:
        raise HTTPException(status_code=400, detail="Subject and message required")
    uid      = int(user["id"])
    username = user.get("username", "")
    name     = user.get("first_name", str(uid))
    ticket_id = await create_ticket(uid, username, name, subject, message)
    try:
        from src.notifier import notify_admin_ticket
        await notify_admin_ticket(ticket_id, uid, name, subject, message)
    except Exception:
        pass
    return {"id": ticket_id, "ok": True}


@api.get("/api/tickets")
async def list_tickets_api(user: dict = Depends(_get_user)):
    from src.tickets import get_user_tickets
    return await get_user_tickets(int(user["id"]))


@api.get("/api/tickets/{ticket_id}")
async def get_ticket_api(ticket_id: int, user: dict = Depends(_get_user)):
    from src.tickets import get_ticket, get_ticket_replies
    ticket = await get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["user_id"] != int(user["id"]) and int(user["id"]) != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Forbidden")
    replies = await get_ticket_replies(ticket_id)
    return {**ticket, "replies": replies}


@api.post("/api/tickets/{ticket_id}/reply")
async def user_reply_ticket(ticket_id: int, body: TicketReplyBody, user: dict = Depends(_get_user)):
    from src.tickets import get_ticket, add_ticket_reply
    ticket = await get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["user_id"] != int(user["id"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    if ticket["status"] == "closed":
        raise HTTPException(status_code=400, detail="Ticket is closed")
    msg  = body.message.strip()[:2000]
    name = user.get("first_name", str(user["id"]))
    await add_ticket_reply(ticket_id, int(user["id"]), name, False, msg)
    return {"ok": True}


# ── Tickets (admin) ───────────────────────────────────────────────────────────
@api.get("/api/admin/tickets")
async def admin_list_tickets(status: Optional[str] = None, _: dict = Depends(_require_admin)):
    from src.tickets import admin_get_tickets
    return await admin_get_tickets(status)


@api.get("/api/admin/tickets/{ticket_id}")
async def admin_get_ticket(ticket_id: int, _: dict = Depends(_require_admin)):
    from src.tickets import get_ticket, get_ticket_replies
    ticket = await get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    replies = await get_ticket_replies(ticket_id)
    return {**ticket, "replies": replies}


@api.post("/api/admin/tickets/{ticket_id}/reply")
async def admin_reply_ticket(ticket_id: int, body: TicketReplyBody, admin: dict = Depends(_require_admin)):
    from src.tickets import get_ticket, add_ticket_reply
    ticket = await get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    msg = body.message.strip()[:2000]
    await add_ticket_reply(ticket_id, int(admin["id"]), "תמיכה", True, msg)
    try:
        from src.notifier import notify_user_ticket_reply
        await notify_user_ticket_reply(ticket["user_id"], ticket_id, ticket["subject"], msg)
    except Exception:
        pass
    return {"ok": True}


class TicketStatusBody(BaseModel):
    status: str


@api.patch("/api/admin/tickets/{ticket_id}/status")
async def admin_update_ticket_status(ticket_id: int, body: TicketStatusBody, _: dict = Depends(_require_admin)):
    from src.tickets import update_ticket_status
    if body.status not in ("open", "in_progress", "closed"):
        raise HTTPException(status_code=400, detail="Invalid status")
    await update_ticket_status(ticket_id, body.status)
    return {"ok": True}


# ── Serve React SPA (must be last) ──────────────────────────────────────────
_DIST = os.path.join(os.path.dirname(__file__), "webapp", "dist")

if os.path.isdir(_DIST):
    api.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @api.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
