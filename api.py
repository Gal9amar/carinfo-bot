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
PAYBOX_URL = os.environ.get("PAYBOX_URL", "https://links.payboxapp.com/xjZpYBP2n3b")

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
    from src.db import execute as _dbexec
    try:
        await load_welcome_settings()
    except Exception:
        pass
    try:
        # Mark stale 'created' transactions (> 2 hours) as expired
        await _dbexec(
            "UPDATE paypal_transactions SET status='expired', updated_at=datetime('now') "
            "WHERE status='created' AND created_at < datetime('now', '-30 minutes')"
        )
        # Delete matching stale pending_payments
        await _dbexec(
            "DELETE FROM pending_payments WHERE created_at < datetime('now', '-30 minutes')"
        )
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
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4], "display_order": p[5], "duration_months": p[6] if len(p) > 6 else 1} for p in pkgs]


@api.get("/api/user")
async def get_user_info(user: dict = Depends(_get_user)):
    from src.users import get_user_by_id
    from src.db import get_bot_setting, execute
    user_id = int(user["id"])
    db_user = await get_user_by_id(user_id)
    maintenance = (await get_bot_setting("maintenance")) == "1"
    left = db_user.get("searches_left", 0) if db_user else 0
    quota = db_user.get("searches_quota", 0) if db_user else 0

    # Determine show_market_price based on feature flag, public mode, and group membership
    yad2_enabled = (await get_bot_setting("yad2_market_enabled")) == "1"
    show_market = False
    if yad2_enabled:
        # Check public (open-to-all) mode with optional date window
        public_on    = (await get_bot_setting("yad2_market_public")) == "1"
        public_start = (await get_bot_setting("yad2_market_public_start")) or ""
        public_end   = (await get_bot_setting("yad2_market_public_end"))   or ""
        if public_on:
            from datetime import date as _date
            today = str(_date.today())
            in_window = (not public_start or today >= public_start) and \
                        (not public_end   or today <= public_end)
            show_market = in_window

        # If not shown via public, check group membership
        if not show_market:
            groups_json = (await get_bot_setting("yad2_market_groups")) or "[]"
            allowed_groups = json.loads(groups_json)
            if not allowed_groups:
                pass  # no groups configured = groups mode inactive
            else:
                r = await execute(
                    f"SELECT 1 FROM user_group_members WHERE user_id=? AND group_id IN ({','.join('?' * len(allowed_groups))})",
                    [user_id, *allowed_groups]
                )
                show_market = len(r.rows) > 0

    # Check if user is in the 'מנויים' group
    sub_r = await execute(
        "SELECT 1 FROM user_group_members ugm "
        "JOIN user_groups ug ON ug.id = ugm.group_id "
        "WHERE ugm.user_id=? AND ug.name='מנויים'",
        [user_id]
    )
    is_subscriber = len(sub_r.rows) > 0

    # Find matching package label by searches count
    subscription_label = None
    if is_subscriber or quota == -1:
        pkg_r = await execute(
            "SELECT label FROM packages WHERE searches=? ORDER BY price DESC LIMIT 1",
            [quota]
        )
        if pkg_r.rows:
            subscription_label = pkg_r.rows[0][0]
        elif quota == -1:
            subscription_label = 'הטבת מנהל'

    # Get quota expiry date
    from src.users import get_quota_expires
    quota_expires = await get_quota_expires(user_id)

    return {
        "id": user["id"],
        "first_name": user.get("first_name", ""),
        "is_admin": user_id == ADMIN_ID,
        "searches_left": left,
        "searches_quota": quota,
        "quota_expires": quota_expires,
        "maintenance": maintenance,
        "show_market_price": show_market,
        "is_subscriber": is_subscriber,
        "subscription_label": subscription_label,
    }


class PaymentInitRequest(BaseModel):
    package_id: int
    quantity: int = 1


@api.post("/api/payment/initiate")
async def initiate_payment(body: PaymentInitRequest, user: dict = Depends(_get_user)):
    import os as _os
    from src.packages import get_packages
    from src.db import execute, set_bot_setting, get_bot_setting, execute as _dbexec
    pkgs = await get_packages()
    pkg = next((p for p in pkgs if p[0] == body.package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    pid, label, searches, price, _img, _order = pkg[:6]
    duration_months = pkg[6] if len(pkg) > 6 else 1
    qty = max(1, min(10, body.quantity))
    total_price = price * qty
    total_searches = -1 if searches == -1 else searches * qty
    qty_label = f"{label} ×{qty}" if qty > 1 else label
    uid = int(user["id"])
    mid_r = await _dbexec("SELECT member_id FROM users WHERE user_id=?", [uid])
    member_id = mid_r.rows[0][0] if mid_r.rows and mid_r.rows[0][0] else uid
    seq_str = await get_bot_setting("order_sequence")
    seq = int(seq_str) + 1 if seq_str else 1
    await set_bot_setting("order_sequence", str(seq))
    ref = f"{member_id}-{seq:05d}"

    paypal_client_id = _os.environ.get("PAYPAL_CLIENT_ID", "")
    paypal_client_secret = _os.environ.get("PAYPAL_CLIENT_SECRET", "")
    use_api = bool(paypal_client_id and paypal_client_secret)

    if use_api:
        from src.paypal import create_order
        try:
            order = await create_order(
                amount=f"{total_price:.2f}",
                currency="ILS",
                custom_id=ref,
                description=qty_label,
            )
            approval_url = next(
                (lnk["href"] for lnk in order.get("links", []) if lnk.get("rel") == "approve"),
                None,
            )
            paypal_order_id = order.get("id", "")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"PayPal error: {e}")
    else:
        # Fallback to PayPal.me link when API credentials are not configured
        approval_url = f"{PAYPAL_ME}/{total_price:.0f}ILS"
        paypal_order_id = ""

    await execute(
        "INSERT OR IGNORE INTO pending_payments (ref, phone, searches, price, label, paypal_order_id, duration_months) VALUES (?,?,?,?,?,?,?)",
        [ref, str(uid), total_searches, total_price, qty_label, paypal_order_id, duration_months],
    )
    await execute(
        "INSERT INTO paypal_transactions (ref, paypal_order_id, user_id, amount, currency, label, searches, status, duration_months) VALUES (?,?,?,?,?,?,?,?,?)",
        [ref, paypal_order_id, uid, total_price, "ILS", qty_label, total_searches, "created", duration_months],
    )
    try:
        from src.notifier import notify_admin_order
        username = user.get("username", "") or ""
        await notify_admin_order(ref, "created", qty_label, total_price, username, member_id)
    except Exception:
        pass
    return {"ref": ref, "approval_url": approval_url, "label": qty_label, "price": total_price, "searches": total_searches}


class PaymentConfirmRequest(BaseModel):
    ref: str
    package_id: int


@api.post("/api/webhooks/paypal")
async def paypal_webhook(request: Request):
    """PayPal webhook — auto-approve payments on CHECKOUT.ORDER.APPROVED."""
    from src.paypal import verify_webhook, capture_order
    from src.db import execute
    import logging as _logging
    _log = _logging.getLogger("paypal_webhook")

    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    headers_lc = {k.lower(): v for k, v in request.headers.items()}
    if not await verify_webhook(headers_lc, body_json):
        raise HTTPException(status_code=400, detail="Webhook verification failed")

    event_type = body_json.get("event_type", "")
    resource   = body_json.get("resource", {})

    if event_type == "CHECKOUT.ORDER.APPROVED":
        order_id = resource.get("id")
        custom_id = (resource.get("purchase_units") or [{}])[0].get("custom_id", "")
        if not order_id:
            return {"ok": True}
        await execute(
            "UPDATE paypal_transactions SET status='approved', updated_at=datetime('now') WHERE paypal_order_id=?",
            [order_id],
        )
        if custom_id:
            await _order_notify(custom_id, "approved")
        try:
            capture = await capture_order(order_id)
            if not custom_id:
                custom_id = (capture.get("purchase_units") or [{}])[0].get("custom_id", "")
            await execute(
                "UPDATE paypal_transactions SET status='captured', updated_at=datetime('now') WHERE paypal_order_id=?",
                [order_id],
            )
            if custom_id:
                await _order_notify(custom_id, "captured")
        except Exception as e:
            _log.warning("Failed to capture order %s: %s", order_id, e)
            await execute(
                "UPDATE paypal_transactions SET status='failed', error=?, updated_at=datetime('now') WHERE paypal_order_id=?",
                [str(e), order_id],
            )
            if custom_id:
                await _order_notify(custom_id, "failed")
            return {"ok": True}
        if custom_id:
            await _auto_approve_payment(custom_id)

    elif event_type == "PAYMENT.CAPTURE.COMPLETED":
        order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id", "")
        if order_id:
            r = await execute("SELECT ref FROM pending_payments WHERE paypal_order_id=?", [order_id])
            if r.rows:
                await _auto_approve_payment(r.rows[0][0])

    return {"ok": True}


async def _order_notify(ref: str, status: str, label: str = "", amount=None) -> None:
    """Lookup user info and send admin order notification."""
    try:
        from src.notifier import notify_admin_order
        from src.db import execute as _dbexec
        r = await _dbexec(
            "SELECT pt.user_id, pt.label, pt.amount, u.username, u.member_id "
            "FROM paypal_transactions pt LEFT JOIN users u ON u.user_id=pt.user_id "
            "WHERE pt.ref=?", [ref]
        )
        if r.rows:
            uid, lbl, amt, username, member_id = r.rows[0]
            await notify_admin_order(ref, status, label or lbl, amount if amount is not None else amt,
                                     username or "", member_id)
    except Exception:
        pass


async def _auto_approve_payment(ref: str) -> None:
    from src.db import execute
    from src.users import admin_grant, add_to_subscribers
    r = await execute("SELECT phone, searches, label, COALESCE(duration_months,1) FROM pending_payments WHERE ref=?", [ref])
    if not r.rows:
        return  # already processed
    user_id, searches, label, duration_months = int(r.rows[0][0]), r.rows[0][1], r.rows[0][2], int(r.rows[0][3])
    await admin_grant(0, user_id, searches, duration_months=duration_months)
    await add_to_subscribers(user_id)
    await execute("DELETE FROM pending_payments WHERE ref=?", [ref])
    await execute(
        "UPDATE paypal_transactions SET status='completed', updated_at=datetime('now') WHERE ref=?",
        [ref],
    )
    await _order_notify(ref, "completed")
    try:
        from src.notifier import notify_user_payment_approved
        await notify_user_payment_approved(user_id, label, searches)
    except Exception:
        pass
    try:
        from src.activity import log as _alog
        await _alog("payment_approved", f"PayPal אוטומטי: {label} ({searches} חיפושים) למשתמש {user_id}")
    except Exception:
        pass


# ── User history ─────────────────────────────────────────────────────────────
@api.get("/api/user/orders")
async def get_user_orders(user: dict = Depends(_get_user)):
    from src.db import execute as _dbexec
    uid = int(user["id"])
    r = await _dbexec(
        "SELECT id, ref, amount, currency, label, searches, status, created_at "
        "FROM paypal_transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        [uid],
    )
    orders = []
    for row in r.rows:
        orders.append({
            "id": row[0], "ref": row[1], "amount": row[2], "currency": row[3],
            "label": row[4], "searches": row[5], "status": row[6], "created_at": row[7],
        })
    return orders


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
        "maintenance":         (await get_bot_setting("maintenance")) == "1",
        "free_searches":       _u.FREE_SEARCHES,
        "referral_bonus":      int((await get_bot_setting("referral_bonus")) or "10"),
        "promo_searches":      _u.PROMO_SEARCHES,
        "promo_start":         _u.PROMO_START,
        "promo_end":           _u.PROMO_END,
        "promo_duration_days": _u.PROMO_DURATION_DAYS,
        "promo_is_subscriber": _u.PROMO_IS_SUBSCRIBER,
        "promo_label":         _u.PROMO_LABEL,
        "yad2_market_enabled":       (await get_bot_setting("yad2_market_enabled")) == "1",
        "yad2_market_groups":        json.loads((await get_bot_setting("yad2_market_groups")) or "[]"),
        "yad2_market_public":        (await get_bot_setting("yad2_market_public")) == "1",
        "yad2_market_public_start":  (await get_bot_setting("yad2_market_public_start")) or "",
        "yad2_market_public_end":    (await get_bot_setting("yad2_market_public_end"))   or "",
        "yad2_market_public_label":  (await get_bot_setting("yad2_market_public_label")) or "",
    }


class SettingsUpdate(BaseModel):
    maintenance:         bool         | None = None
    free_searches:       int          | None = None
    referral_bonus:      int          | None = None
    promo_searches:      int          | None = None
    promo_start:         str          | None = None
    promo_end:           str          | None = None
    promo_duration_days: int          | None = None
    promo_is_subscriber: bool         | None = None
    promo_label:         str          | None = None
    yad2_market_enabled:       bool         | None = None
    yad2_market_groups:        Optional[list]      = None
    yad2_market_public:        bool         | None = None
    yad2_market_public_start:  str          | None = None
    yad2_market_public_end:    str          | None = None
    yad2_market_public_label:  str          | None = None


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
    if body.promo_duration_days is not None:
        _u.PROMO_DURATION_DAYS = max(0, body.promo_duration_days)
        await set_bot_setting("promo_duration_days", str(_u.PROMO_DURATION_DAYS))
    if body.promo_is_subscriber is not None:
        _u.PROMO_IS_SUBSCRIBER = body.promo_is_subscriber
        await set_bot_setting("promo_is_subscriber", "1" if _u.PROMO_IS_SUBSCRIBER else "0")
    if body.promo_label is not None:
        _u.PROMO_LABEL = body.promo_label.strip()
        await set_bot_setting("promo_label", _u.PROMO_LABEL)
    if body.yad2_market_enabled is not None:
        await set_bot_setting("yad2_market_enabled", "1" if body.yad2_market_enabled else "0")
    if body.yad2_market_groups is not None:
        await set_bot_setting("yad2_market_groups", json.dumps(body.yad2_market_groups))
    if body.yad2_market_public is not None:
        await set_bot_setting("yad2_market_public", "1" if body.yad2_market_public else "0")
    if body.yad2_market_public_start is not None:
        await set_bot_setting("yad2_market_public_start", body.yad2_market_public_start.strip())
    if body.yad2_market_public_end is not None:
        await set_bot_setting("yad2_market_public_end", body.yad2_market_public_end.strip())
    if body.yad2_market_public_label is not None:
        await set_bot_setting("yad2_market_public_label", body.yad2_market_public_label.strip())
    return {"ok": True}


@api.get("/api/admin/groups")
async def admin_list_groups(_: dict = Depends(_require_admin)):
    from src.db import execute
    groups_r = await execute(
        "SELECT id, name, created_at FROM user_groups ORDER BY created_at ASC"
    )
    result = []
    for row in groups_r.rows:
        group_id, name, created_at = row[0], row[1], row[2]
        members_r = await execute(
            "SELECT user_id FROM user_group_members WHERE group_id=?", [group_id]
        )
        member_ids = [m[0] for m in members_r.rows]
        result.append({
            "id": group_id,
            "name": name,
            "created_at": created_at,
            "member_ids": member_ids,
        })
    return result


class GroupCreateBody(BaseModel):
    name: str


@api.post("/api/admin/groups")
async def admin_create_group(body: GroupCreateBody, _: dict = Depends(_require_admin)):
    from src.db import execute
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    try:
        await execute(
            "INSERT INTO user_groups (name) VALUES (?)", [name]
        )
    except Exception as e:
        if "UNIQUE" in str(e).upper() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Group name already exists")
        raise
    r = await execute("SELECT id, name, created_at FROM user_groups WHERE name=?", [name])
    if not r.rows:
        raise HTTPException(status_code=500, detail="Failed to create group")
    row = r.rows[0]
    return {"id": row[0], "name": row[1], "created_at": row[2], "member_ids": []}


@api.delete("/api/admin/groups/{group_id}")
async def admin_delete_group(group_id: int, _: dict = Depends(_require_admin)):
    from src.db import execute
    await execute("DELETE FROM user_group_members WHERE group_id=?", [group_id])
    await execute("DELETE FROM user_groups WHERE id=?", [group_id])
    return {"ok": True}


class GroupMemberBody(BaseModel):
    user_id: int


@api.post("/api/admin/groups/{group_id}/members")
async def admin_add_group_member(group_id: int, body: GroupMemberBody, _: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute("SELECT id FROM user_groups WHERE id=?", [group_id])
    if not r.rows:
        raise HTTPException(status_code=404, detail="Group not found")
    await execute(
        "INSERT OR IGNORE INTO user_group_members (group_id, user_id) VALUES (?, ?)",
        [group_id, body.user_id]
    )
    return {"ok": True}


@api.delete("/api/admin/groups/{group_id}/members/{user_id}")
async def admin_remove_group_member(group_id: int, user_id: int, _: dict = Depends(_require_admin)):
    from src.db import execute
    await execute(
        "DELETE FROM user_group_members WHERE group_id=? AND user_id=?",
        [group_id, user_id]
    )
    return {"ok": True}


@api.get("/api/admin/packages")
async def admin_list_packages(_: dict = Depends(_require_admin)):
    from src.packages import get_packages
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4], "display_order": p[5], "duration_months": p[6] if len(p) > 6 else 1} for p in pkgs]


class PackageBody(BaseModel):
    label: str
    searches: int
    price: int
    image_url: str = ""
    duration_months: int = 1


class PackageReorderBody(BaseModel):
    order: list[int]


@api.put("/api/admin/packages/reorder")
async def admin_reorder_packages(body: PackageReorderBody, _: dict = Depends(_require_admin)):
    from src.packages import reorder_packages, get_packages
    if not body.order:
        raise HTTPException(status_code=400, detail="Order list required")
    await reorder_packages(body.order)
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4], "display_order": p[5], "duration_months": p[6] if len(p) > 6 else 1} for p in pkgs]


@api.post("/api/admin/packages")
async def admin_add_package(body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import add_package, get_packages
    await add_package(body.label, body.searches, body.price, body.image_url, body.duration_months)
    pkgs = await get_packages(force_reload=True)
    return [{"id": p[0], "label": p[1], "searches": p[2], "price": p[3], "image_url": p[4], "display_order": p[5], "duration_months": p[6] if len(p) > 6 else 1} for p in pkgs]


@api.put("/api/admin/packages/{pkg_id}")
async def admin_update_package(pkg_id: int, body: PackageBody, _: dict = Depends(_require_admin)):
    from src.packages import update_package
    await update_package(pkg_id, body.label, body.searches, body.price, body.image_url, body.duration_months)
    return {"ok": True}


@api.delete("/api/admin/packages/{pkg_id}")
async def admin_delete_package(pkg_id: int, _: dict = Depends(_require_admin)):
    from src.packages import delete_package
    await delete_package(pkg_id)
    return {"ok": True}


def _grants_json(pkgs):
    return [{"id": g[0], "label": g[1], "searches": g[2], "display_order": g[3]} for g in pkgs]


class AdminGrantBody(BaseModel):
    label: str
    searches: int


class AdminGrantReorderBody(BaseModel):
    order: list[int]


@api.get("/api/admin/grants")
async def admin_list_grants(_: dict = Depends(_require_admin)):
    from src.admin_grants import get_admin_grants
    grants = await get_admin_grants(force_reload=True)
    return _grants_json(grants)


@api.put("/api/admin/grants/reorder")
async def admin_reorder_grants(body: AdminGrantReorderBody, _: dict = Depends(_require_admin)):
    from src.admin_grants import reorder_admin_grants, get_admin_grants
    if not body.order:
        raise HTTPException(status_code=400, detail="Order list required")
    await reorder_admin_grants(body.order)
    return _grants_json(await get_admin_grants(force_reload=True))


@api.post("/api/admin/grants")
async def admin_add_grant(body: AdminGrantBody, _: dict = Depends(_require_admin)):
    from src.admin_grants import add_admin_grant, get_admin_grants
    await add_admin_grant(body.label, body.searches)
    return _grants_json(await get_admin_grants(force_reload=True))


@api.put("/api/admin/grants/{grant_id}")
async def admin_update_grant(grant_id: int, body: AdminGrantBody, _: dict = Depends(_require_admin)):
    from src.admin_grants import update_admin_grant
    await update_admin_grant(grant_id, body.label, body.searches)
    return {"ok": True}


@api.delete("/api/admin/grants/{grant_id}")
async def admin_delete_grant(grant_id: int, _: dict = Depends(_require_admin)):
    from src.admin_grants import delete_admin_grant
    await delete_admin_grant(grant_id)
    return {"ok": True}


class GrantBody(BaseModel):
    searches: int


@api.post("/api/admin/users/{user_id}/grant")
async def admin_grant_user(user_id: int, body: GrantBody, admin: dict = Depends(_require_admin)):
    from src.users import admin_grant
    msg = await admin_grant(int(admin["id"]), user_id, body.searches)
    try:
        from src.activity import log as _log
        desc = (
            "מנוי חינם" if body.searches == 0 else
            "ללא הגבלה" if body.searches == -2 else
            ("מנוי חודשי" if body.searches == -1 else f"{body.searches} חיפושים")
        )
        await _log("grant", f"הענקה למשתמש {user_id}: {desc}")
    except Exception:
        pass
    try:
        from src.notifier import notify_user_admin_grant
        await notify_user_admin_grant(user_id, body.searches)
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
    from src.users import add_to_subscribers
    await add_to_subscribers(user_id)
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


@api.post("/api/admin/users/{user_id}/revoke-subscription")
async def admin_revoke_subscription(user_id: int, _: dict = Depends(_require_admin)):
    from src.db import execute
    from src.users import remove_from_subscribers
    await remove_from_subscribers(user_id)
    await execute(
        "UPDATE users SET searches_quota = 0, searches_done = 0, quota_expires = NULL WHERE user_id = ?",
        [user_id]
    )
    try:
        from src.activity import log as _log
        await _log("subscription_revoked", f"מנוי הוסר ידנית למשתמש {user_id}")
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


@api.get("/api/admin/paypal/transactions")
async def admin_paypal_transactions(_: dict = Depends(_require_admin)):
    from src.db import execute
    r = await execute(
        "SELECT pt.id, pt.ref, pt.paypal_order_id, pt.user_id, "
        "COALESCE(u.username, ''), COALESCE(u.full_name, ''), "
        "pt.amount, pt.currency, pt.label, pt.searches, pt.status, pt.error, pt.created_at, pt.updated_at "
        "FROM paypal_transactions pt "
        "LEFT JOIN users u ON u.user_id = pt.user_id "
        "ORDER BY pt.created_at DESC LIMIT 200"
    )
    results = []
    for row in r.rows:
        results.append({
            "id": row[0], "ref": row[1], "paypal_order_id": row[2], "user_id": row[3],
            "username": row[4], "full_name": row[5],
            "amount": row[6], "currency": row[7], "label": row[8], "searches": row[9],
            "status": row[10], "error": row[11], "created_at": row[12], "updated_at": row[13],
        })
    return results


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
    image_b64: str = ""


@api.post("/api/admin/broadcast")
async def admin_broadcast(body: BroadcastBody, _: dict = Depends(_require_admin)):
    from src.db import execute as _db_execute
    msg = body.message.strip()[:2000]
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")
    if body.image_b64:
        from src.notifier import notify_broadcast_photo
        result = await notify_broadcast_photo(msg, body.image_b64)
    else:
        from src.notifier import notify_broadcast
        result = await notify_broadcast(msg)
    try:
        await _db_execute(
            "INSERT INTO broadcast_history (message, has_image, sent, failed) VALUES (?, ?, ?, ?)",
            [msg, 1 if body.image_b64 else 0, result.get("sent", 0), result.get("failed", 0)],
        )
    except Exception:
        pass
    try:
        from src.activity import log as _log
        await _log("broadcast", f"שידור נשלח: {msg[:80]}{'...' if len(msg) > 80 else ''}")
    except Exception:
        pass
    return result


@api.get("/api/admin/broadcast/history")
async def admin_broadcast_history(_: dict = Depends(_require_admin)):
    from src.db import execute as _db_execute
    r = await _db_execute(
        "SELECT id, message, has_image, sent, failed, sent_at FROM broadcast_history ORDER BY sent_at DESC LIMIT 50"
    )
    return [
        {"id": row[0], "message": row[1], "has_image": bool(row[2]),
         "sent": row[3], "failed": row[4], "sent_at": row[5]}
        for row in r.rows
    ]


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
    searches: int = 0
    message: str = ""
    image_b64: str = ""
    gift_type: str = "searches"  # "searches" | "monthly"


@api.post("/api/admin/gift-all")
async def admin_gift_all(body: GiftAllBody, _: dict = Depends(_require_admin)):
    import datetime
    from src.db import execute
    msg = body.message.strip()[:500]

    if body.gift_type == "monthly":
        expires = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
        await execute(
            "UPDATE users SET searches_quota = -1, quota_expires = ? WHERE blocked = 0",
            [expires],
        )
        # Add all non-blocked users to מנויים group
        grp = await execute("SELECT id FROM user_groups WHERE name='מנויים' LIMIT 1")
        if grp.rows:
            group_id = grp.rows[0][0]
            await execute(
                "INSERT OR IGNORE INTO user_group_members (group_id, user_id) "
                "SELECT ?, user_id FROM users WHERE blocked = 0",
                [group_id],
            )
        gift_text = "🎁 *קיבלת מנוי חופשי חודשי!*\n\nגישה ללא הגבלת חיפושים ל\\-30 ימים 🎉" + (f"\n\n{msg}" if msg else "")
        log_desc = f"מתנה לכולם: מנוי חופשי חודשי. הודעה: {msg[:60]}"
    else:
        if body.searches < 1:
            raise HTTPException(status_code=400, detail="searches must be >= 1")
        await execute(
            "UPDATE users SET searches_quota = searches_quota + ? WHERE searches_quota >= 0 AND blocked = 0",
            [body.searches],
        )
        gift_text = f"🎁 *קיבלת {body.searches} חיפושים במתנה!*" + (f"\n\n{msg}" if msg else "")
        log_desc = f"מתנה לכולם: +{body.searches} חיפושים. הודעה: {msg[:60]}"

    notified = 0
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
        await _log("grant", log_desc)
    except Exception:
        pass
    return {"ok": True, "gift_type": body.gift_type, "searches": body.searches, "notified": notified}


@api.get("/api/admin/activity")
async def admin_get_activity(limit: int = 100, _: dict = Depends(_require_admin)):
    from src.activity import get_log
    return await get_log(min(limit, 200))


@api.get("/api/vehicle/{plate}/market-price")
async def vehicle_market_price(plate: str, user: dict = Depends(_get_user)):
    from src.api.gov_api import fetch_vehicle_data
    from src.cache import cache
    from src.yad2 import get_market_price, build_url
    from src.db import get_bot_setting, execute

    # Check feature flag
    yad2_enabled = (await get_bot_setting("yad2_market_enabled")) == "1"
    if not yad2_enabled:
        raise HTTPException(status_code=403, detail="disabled")

    user_id = int(user["id"])
    allowed = False

    # Check public (open-to-all) mode with optional date window
    public_on    = (await get_bot_setting("yad2_market_public")) == "1"
    public_start = (await get_bot_setting("yad2_market_public_start")) or ""
    public_end   = (await get_bot_setting("yad2_market_public_end"))   or ""
    if public_on:
        from datetime import date as _date
        today = str(_date.today())
        in_window = (not public_start or today >= public_start) and \
                    (not public_end   or today <= public_end)
        allowed = in_window

    # If not allowed via public, check group membership
    if not allowed:
        groups_json = (await get_bot_setting("yad2_market_groups")) or "[]"
        allowed_groups = json.loads(groups_json)
        if allowed_groups:
            r = await execute(
                f"SELECT 1 FROM user_group_members WHERE user_id=? AND group_id IN ({','.join('?' * len(allowed_groups))})",
                [user_id, *allowed_groups]
            )
            allowed = len(r.rows) > 0

    # Always fetch data — unauthorized users see a blurred teaser
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

    public_label = (await get_bot_setting("yad2_market_public_label")) or "" if public_on else ""
    return {
        "authorized":   allowed,
        "public_label": public_label,
        "year":         year,
        "yad2_url":     build_url(record) if allowed else None,
        "market":       market,
    }


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
