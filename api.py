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


# ── Startup ─────────────────────────────────────────────────────────────────
@api.on_event("startup")
async def _startup():
    from src.users import load_welcome_settings
    try:
        await load_welcome_settings()
    except Exception:
        pass


# ── Health ──────────────────────────────────────────────────────────────────
@api.get("/health")
async def health():
    return {"ok": True}


# ── Public ──────────────────────────────────────────────────────────────────
@api.get("/api/packages")
async def list_packages():
    from src.packages import get_packages
    pkgs = await get_packages()
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4]} for p in pkgs]


@api.get("/api/user")
async def get_user_info(user: dict = Depends(_get_user)):
    from src.users import get_user_by_id
    from src.db import get_bot_setting
    db_user = await get_user_by_id(int(user["id"]))
    maintenance = (await get_bot_setting("maintenance")) == "1"
    left = db_user.get("searches_left", 0) if db_user else 0
    quota = db_user.get("searches_quota", 0) if db_user else 0
    return {
        "id": user["id"],
        "first_name": user.get("first_name", ""),
        "is_admin": int(user["id"]) == ADMIN_ID,
        "searches_left": left,
        "searches_quota": quota,
        "maintenance": maintenance,
    }


class PaymentInitRequest(BaseModel):
    package_id: int
    quantity: int = 1


@api.post("/api/payment/initiate")
async def initiate_payment(body: PaymentInitRequest, user: dict = Depends(_get_user)):
    from src.packages import get_packages
    import secrets as _secrets
    from src.db import execute
    pkgs = await get_packages()
    pkg = next((p for p in pkgs if p[0] == body.package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    pid, label, searches, price, _img = pkg
    qty = max(1, min(10, body.quantity))
    total_price = price * qty
    total_searches = -1 if searches == -1 else searches * qty
    qty_label = f"{label} ×{qty}" if qty > 1 else label
    ref = _secrets.token_hex(8)
    await execute(
        "INSERT OR IGNORE INTO pending_payments (ref, phone, searches, price, label) VALUES (?,?,?,?,?)",
        [ref, str(user["id"]), total_searches, total_price, qty_label],
    )
    return {"ref": ref, "paypal_url": f"{PAYPAL_ME}/{total_price}", "label": qty_label, "price": total_price, "searches": total_searches}


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
    import asyncio
    from src.users import get_search_history
    from src.api.gov_api import fetch_vehicle_data
    from src.cache import cache
    from src import yad2 as _yad2

    plates = await get_search_history(int(user["id"]), limit=20)

    async def enrich(plate: str) -> dict:
        record = cache.get(plate)
        if record is None:
            try:
                record = await fetch_vehicle_data(plate)
                if record:
                    cache.set(plate, record)
            except Exception:
                record = None
        entry: dict = {"plate": plate}
        if record:
            entry["make"]  = record.get("tozeret_nm") or ""
            entry["model"] = record.get("kinuy_mishari") or record.get("degem_nm") or ""
            entry["year"]  = str(record.get("shnat_yitzur") or "")
            entry["color"] = record.get("tzeva_rechev") or ""
            entry["yad2"]  = _yad2.build_url(record) or ""
        return entry

    results = await asyncio.gather(*[enrich(p) for p in plates])
    return list(results)


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
    uid  = int(user["id"])
    name = user.get("username") or user.get("first_name", str(uid))
    try:
        from src.activity import log as _log
        await _log("search", f"חיפוש לוחית {plate}", uid, name)
    except Exception:
        pass
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
        "maintenance":    (await get_bot_setting("maintenance")) == "1",
        "free_searches":  _u.FREE_SEARCHES,
        "referral_bonus": int((await get_bot_setting("referral_bonus")) or "10"),
        "promo_searches": _u.PROMO_SEARCHES,
        "promo_start":    _u.PROMO_START,
        "promo_end":      _u.PROMO_END,
    }


class SettingsUpdate(BaseModel):
    maintenance:    bool | None = None
    free_searches:  int  | None = None
    referral_bonus: int  | None = None
    promo_searches: int  | None = None
    promo_start:    str  | None = None
    promo_end:      str  | None = None


@api.post("/api/admin/settings")
async def admin_update_settings(body: SettingsUpdate, _: dict = Depends(_require_admin)):
    from src.db import set_bot_setting
    import src.users as _u
    if body.maintenance is not None:
        await set_bot_setting("maintenance", "1" if body.maintenance else "0")
    if body.free_searches is not None:
        _u.FREE_SEARCHES = max(0, body.free_searches)
        await set_bot_setting("free_searches", str(_u.FREE_SEARCHES))
    if body.referral_bonus is not None:
        try:
            rb = max(1, int(body.referral_bonus))
            await set_bot_setting("referral_bonus", str(rb))
        except Exception:
            pass
    if body.promo_searches is not None:
        _u.PROMO_SEARCHES = body.promo_searches
        await set_bot_setting("promo_searches", str(_u.PROMO_SEARCHES))
    if body.promo_start is not None:
        _u.PROMO_START = body.promo_start.strip()
        await set_bot_setting("promo_start", _u.PROMO_START)
    if body.promo_end is not None:
        _u.PROMO_END = body.promo_end.strip()
        await set_bot_setting("promo_end", _u.PROMO_END)
    return {"ok": True}


@api.get("/api/admin/packages")
async def admin_list_packages(_: dict = Depends(_require_admin)):
    from src.packages import get_packages
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4]} for p in pkgs]


class PackageBody(BaseModel):
    label: str
    searches: int
    price: int
    image_url: str = ""


@api.post("/api/admin/packages")
async def admin_add_package(body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import add_package, get_packages
    await add_package(body.label, body.searches, body.price, body.image_url)
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4]} for p in pkgs]


@api.put("/api/admin/packages/{pkg_id}")
async def admin_update_package(pkg_id: int, body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import update_package
    await update_package(pkg_id, body.label, body.searches, body.price, body.image_url)
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
    try:
        from src.activity import log as _log
        desc = "ללא הגבלה" if body.searches == -2 else ("מנוי חודשי" if body.searches == -1 else f"{body.searches} חיפושים")
        await _log("grant", f"הענקה למשתמש {user_id}: {desc}")
    except Exception:
        pass
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
    try:
        from src.activity import log as _log
        await _log("ticket_new", f"פנייה חדשה #{ticket_id}: {subject[:60]}", uid, name)
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
    try:
        from src.activity import log as _log
        await _log("ticket_reply", f"תגובת מנהל לפנייה #{ticket_id}", int(admin["id"]), "admin")
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
    try:
        from src.activity import log as _log
        await _log("ticket_status", f"סטטוס פנייה #{ticket_id} → {body.status}")
    except Exception:
        pass
    return {"ok": True}


@api.get("/api/admin/payments")
async def admin_list_payments(_: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute(
        "SELECT ref, phone, searches, price, label, created_at FROM pending_payments ORDER BY created_at DESC"
    )
    return [{"ref": row[0], "user_id": row[1], "searches": row[2], "price": row[3], "label": row[4], "created_at": row[5]} for row in r.rows]


@api.post("/api/admin/payments/{ref}/approve")
async def admin_approve_payment(ref: str, admin: dict = Depends(_require_admin)):
    from src.db import execute
    from src.users import admin_grant
    r = await execute("SELECT phone, searches, label FROM pending_payments WHERE ref=?", [ref])
    if not r.rows:
        raise HTTPException(status_code=404, detail="Payment not found")
    user_id, searches, label = int(r.rows[0][0]), r.rows[0][1], r.rows[0][2]
    await admin_grant(int(admin["id"]), user_id, searches)
    await execute("DELETE FROM pending_payments WHERE ref=?", [ref])
    try:
        from src.notifier import notify_user_payment_approved
        await notify_user_payment_approved(user_id, label, searches)
    except Exception:
        pass
    try:
        from src.activity import log as _log
        await _log("payment_approved", f"תשלום אושר: {label} ({searches} חיפושים) למשתמש {user_id}")
    except Exception:
        pass
    return {"ok": True}


@api.post("/api/admin/payments/{ref}/decline")
async def admin_decline_payment(ref: str, _: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute("SELECT phone, label FROM pending_payments WHERE ref=?", [ref])
    if not r.rows:
        raise HTTPException(status_code=404, detail="Payment not found")
    user_id, label = int(r.rows[0][0]), r.rows[0][1]
    await execute("DELETE FROM pending_payments WHERE ref=?", [ref])
    try:
        from src.notifier import notify_user_payment_declined
        await notify_user_payment_declined(user_id, label)
    except Exception:
        pass
    try:
        from src.activity import log as _log
        await _log("payment_declined", f"תשלום נדחה: {label} למשתמש {user_id}")
    except Exception:
        pass
    return {"ok": True}


@api.get("/api/admin/codes")
async def admin_list_codes(_: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute(
        "SELECT code, searches, unlimited, single_use, expires, used_by, used_at, created FROM codes ORDER BY created DESC"
    )
    return [{
        "code": row[0], "searches": row[1], "unlimited": bool(row[2]),
        "single_use": bool(row[3]), "expires": row[4],
        "used_by": row[5], "used_at": row[6], "created": row[7]
    } for row in r.rows]


class CodeCreateBody(BaseModel):
    searches: int = 50
    unlimited: bool = False
    single_use: bool = True
    monthly: bool = False


@api.post("/api/admin/codes")
async def admin_create_code(body: CodeCreateBody, _: dict = Depends(_require_admin)):
    from src.users import generate_code
    code = await generate_code(
        searches=body.searches,
        unlimited=body.unlimited,
        single_use=body.single_use,
        monthly=body.monthly,
    )
    try:
        from src.activity import log as _log
        desc = "ללא הגבלה" if body.unlimited else f"{body.searches} חיפושים"
        await _log("code_created", f"קוד גישה נוצר: {code} ({desc})")
    except Exception:
        pass
    return {"code": code}


@api.delete("/api/admin/codes/{code}")
async def admin_delete_code(code: str, _: dict = Depends(_require_admin)):
    from src.db import execute
    await execute("DELETE FROM codes WHERE code=?", [code])
    try:
        from src.activity import log as _log
        await _log("code_deleted", f"קוד גישה נמחק: {code}")
    except Exception:
        pass
    return {"ok": True}


class BroadcastBody(BaseModel):
    message: str


@api.post("/api/admin/broadcast")
async def admin_broadcast(body: BroadcastBody, _: dict = Depends(_require_admin)):
    from src.notifier import notify_broadcast
    msg = body.message.strip()[:2000]
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")
    result = await notify_broadcast(msg)
    try:
        from src.activity import log as _log
        await _log("broadcast", f"שידור נשלח: {msg[:80]}{'...' if len(msg) > 80 else ''}")
    except Exception:
        pass
    return result


class DirectMessageBody(BaseModel):
    message: str


@api.post("/api/admin/users/{user_id}/message")
async def admin_send_user_message(user_id: int, body: DirectMessageBody, _: dict = Depends(_require_admin)):
    from src.notifier import send_user_message
    msg = body.message.strip()[:2000]
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")
    ok = await send_user_message(user_id, msg)
    try:
        from src.activity import log as _log
        await _log("message", f"הודעה ישירה נשלחה למשתמש {user_id}: {msg[:60]}{'...' if len(msg) > 60 else ''}")
    except Exception:
        pass
    return {"ok": ok}


@api.get("/api/admin/users/{user_id}/referrals")
async def admin_user_referrals(user_id: int, _: dict = Depends(_require_admin)):
    from src.users import get_referrals
    refs = await get_referrals(user_id)
    total_bonus = sum(r["bonus"] for r in refs)
    return {"referrals": refs, "count": len(refs), "total_bonus": total_bonus}


@api.get("/api/admin/users/{user_id}/history")
async def admin_user_history(user_id: int, _: dict = Depends(_require_admin)):
    from src.users import get_search_history
    return await get_search_history(user_id)


@api.post("/api/admin/users/{user_id}/block")
async def admin_toggle_block(user_id: int, _: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute("SELECT blocked FROM users WHERE user_id=?", [user_id])
    if not r.rows:
        raise HTTPException(status_code=404, detail="User not found")
    current = r.rows[0][0]
    new_val = 0 if current else 1
    await execute("UPDATE users SET blocked=? WHERE user_id=?", [new_val, user_id])
    try:
        from src.activity import log as _log
        etype = "block" if new_val else "unblock"
        await _log(etype, f"משתמש {user_id} {'נחסם' if new_val else 'שוחרר'}")
    except Exception:
        pass
    return {"ok": True, "blocked": bool(new_val)}


class GiftAllBody(BaseModel):
    searches: int
    message: str = ""
    image_b64: str = ""


@api.post("/api/admin/gift-all")
async def admin_gift_all(body: GiftAllBody, _: dict = Depends(_require_admin)):
    if body.searches < 1:
        raise HTTPException(status_code=400, detail="searches must be >= 1")
    msg = body.message.strip()[:500]
    await execute(
        "UPDATE users SET searches_quota = searches_quota + ? WHERE searches_quota >= 0 AND blocked = 0",
        [body.searches],
    )
    notified = 0
    gift_text = f"🎁 *קיבלת {body.searches} חיפושים במתנה!*" + (f"\n\n{msg}" if msg else "")
    try:
        if body.image_b64:
            from src.notifier import notify_broadcast_photo
            result = await notify_broadcast_photo(gift_text, body.image_b64)
        else:
            from src.notifier import notify_broadcast
            result = await notify_broadcast(gift_text)
        notified = result.get("sent", 0)
    except Exception:
        pass
    try:
        from src.activity import log as _log
        await _log("grant", f"מתנה לכולם: +{body.searches} חיפושים. הודעה: {msg[:60]}")
    except Exception:
        pass
    return {"ok": True, "searches": body.searches, "notified": notified}


@api.get("/api/admin/activity")
async def admin_get_activity(limit: int = 100, _: dict = Depends(_require_admin)):
    from src.activity import get_log
    return await get_log(min(limit, 200))


@api.get("/api/admin/market-price")
async def admin_market_price(plate: str, _: dict = Depends(_require_admin)):
    from src.api.gov_api import fetch_vehicle_data
    from src.cache import cache
    from src.yad2 import get_market_price, build_url

    clean = plate.replace("-", "").replace(" ", "")
    record = cache.get(clean)
    if record is None:
        record = await fetch_vehicle_data(clean)
        if record:
            cache.set(clean, record)
    if not record:
        raise HTTPException(status_code=404, detail="רכב לא נמצא")

    make  = str(record.get("tozeret_nm") or "").strip()
    model = str(record.get("kinuy_mishari") or record.get("degem_nm") or "").strip()
    year  = record.get("shnat_yitzur")

    market = get_market_price(make, model, year)

    return {
        "plate":  clean,
        "make":   make,
        "model":  model,
        "year":   year,
        "color":  record.get("tzeva_rechev") or "",
        "yad2_url": build_url(record),
        "market": market,
    }


@api.get("/api/user/referrals")
async def user_referrals_list(user: dict = Depends(_get_user)):
    from src.users import get_referrals
    return await get_referrals(int(user["id"]))


@api.get("/api/user/referral")
async def user_referral_info(user: dict = Depends(_get_user)):
    from src.users import get_referral_count
    from src.db import get_bot_setting
    uid = int(user["id"])
    count = await get_referral_count(uid)
    bonus_str = await get_bot_setting("referral_bonus")
    bonus = int(bonus_str) if bonus_str and bonus_str.isdigit() else 10
    bot_username = os.environ.get("BOT_USERNAME", "israelcarinfobot")
    link = f"https://t.me/{bot_username}?start=ref_{uid}"
    return {"link": link, "count": count, "bonus": bonus, "total_earned": count * bonus}



# ── Yad2 proxy (Israeli IP bypass) ──────────────────────────────────────────
_YAD2_SECRET = os.environ.get("YAD2_PROXY_SECRET", "carinfo2026")
_YAD2_BASE   = "https://gw.yad2.co.il/lookalike/vehicles/cars"
_YAD2_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

@api.get("/yad2")
async def yad2_proxy(
    request: Request,
    secret: str = "",
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    year: Optional[str] = None,
    rows: int = 100,
):
    if secret != _YAD2_SECRET:
        raise HTTPException(status_code=403, detail="forbidden")

    import urllib.request as _ureq, gzip as _gzip, zlib as _zlib
    from urllib.parse import urlencode as _ue

    params: dict = {"rows": rows}
    if manufacturer: params["manufacturer"] = manufacturer
    if model:        params["model"]        = model
    if year:         params["year"]         = year

    yad2_url = f"{_YAD2_BASE}?{_ue(params)}"
    req = _ureq.Request(yad2_url, headers=_YAD2_HEADERS)
    try:
        with _ureq.urlopen(req, timeout=15) as resp:
            raw      = resp.read()
            encoding = resp.headers.get("Content-Encoding", "")
        if "gzip"    in encoding: raw = _gzip.decompress(raw)
        elif "deflate" in encoding: raw = _zlib.decompress(raw)
        return JSONResponse(content=json.loads(raw.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Serve React SPA (must be last) ──────────────────────────────────────────
_DIST = os.path.join(os.path.dirname(__file__), "webapp", "dist")

if os.path.isdir(_DIST):
    api.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @api.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
