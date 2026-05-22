"""
FastAPI app — serves REST API + React static files.
Replaces the simple health server. Runs on the same PORT as before.
"""
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

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


async def _notify_admin_payment(user_id: int, name: str, label: str, searches: int, price: int, ref: str) -> None:
    """Notify the Telegram admin without importing bot.py as a second module."""
    if not BOT_TOKEN or not ADMIN_ID:
        raise RuntimeError("Telegram bot token/admin id is not configured")

    import httpx

    text = (
        "💰 בקשת אישור תשלום (Mini App)!\n\n"
        f"👤 {name}\n"
        f"🆔 {user_id}\n"
        f"📦 {label}\n"
        f"💵 {price} שח\n"
        f"🔑 ref: {ref}\n\n"
        "לאחר אימות התשלום ב-PayPal לחץ אשר:"
    )
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ אשר ופתח גישה", "callback_data": f"approve|{user_id}|{searches}"},
            {"text": "❌ דחה", "callback_data": f"decline|{user_id}"},
        ]]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": text, "reply_markup": reply_markup},
        )
    data = response.json()
    if response.status_code >= 400 or not data.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {response.status_code} {data}")


@api.post("/api/payment/confirm")
async def confirm_payment(body: PaymentConfirmRequest, user: dict = Depends(_get_user)):
    """User clicked 'I paid' — notify admin via bot."""
    from src.packages import get_packages
    pkgs = await get_packages()
    pkg = next((p for p in pkgs if p[0] == body.package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    pid, label, searches, price = pkg
    try:
        uid  = int(user["id"])
        name = user.get("first_name", str(uid))
        await _notify_admin_payment(uid, name, label, searches, price, body.ref)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Failed to notify admin") from exc
    return {"ok": True}


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


# ── Serve React SPA (must be last) ──────────────────────────────────────────
_DIST = os.path.join(os.path.dirname(__file__), "webapp", "dist")

if os.path.isdir(_DIST):
    api.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @api.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
