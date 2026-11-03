"""Levi Yitzhak price list (מחירון לוי יצחק) — login with the user's own phone.

Same API the official Levi Yitzhak app uses (`https://s.leviitzhak.xyz`): the user
receives a 6-digit SMS code from Levi Yitzhak, we validate it and keep the JWT the
API returns, so later price lookups run on the user's own account.

Stage 1: login only (send SMS → validate code → store token / logout).
`LEVI_API_BASE` overrides the base URL (e.g. an Israeli-IP proxy if the API
starts blocking foreign servers, as Yad2 does).
"""
from __future__ import annotations

import logging
import os
import re
import uuid as _uuid
from typing import Optional

import httpx

from src.db import execute

logger = logging.getLogger(__name__)

API_BASE = os.environ.get("LEVI_API_BASE", "https://s.leviitzhak.xyz").rstrip("/")
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

PHONE_RE = re.compile(r"^05[0-689]\d{7}$")   # same prefixes the Levi app accepts
CODE_RE = re.compile(r"^\d{6}$")


async def init_levi() -> None:
    await execute("""CREATE TABLE IF NOT EXISTS levi_sessions (
    user_id    INTEGER PRIMARY KEY,
    phone      TEXT NOT NULL,
    uuid       TEXT NOT NULL,
    token      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)""")


def normalize_phone(raw: str) -> Optional[str]:
    """'+972 50-123-4567' / '972501234567' / '050 1234567' → '0501234567'; None if invalid."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    elif len(digits) == 9 and digits.startswith("5"):
        digits = "0" + digits
    return digits if PHONE_RE.match(digits) else None


class LeviError(Exception):
    """A user-presentable (Hebrew) failure."""


def mask_phone(phone: str) -> str:
    return f"{phone[:3]}-•••-{phone[-4:]}" if phone and len(phone) >= 7 else "•••"


async def _post(path: str, body: dict, token: str | None = None) -> dict:
    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(f"{API_BASE}{path}", json=body, headers=headers)
    try:
        data = r.json()
    except ValueError:
        raise LeviError(f"תשובה לא תקינה מהשרת ({r.status_code})")
    if not isinstance(data, dict):
        raise LeviError(f"תשובה לא תקינה מהשרת ({r.status_code})")
    if r.status_code >= 400 and "status" not in data:
        raise LeviError(str(data.get("msg") or data.get("error") or f"שגיאה {r.status_code}"))
    return data


# ── Session storage ─────────────────────────────────────────────────────────

async def get_session(user_id: int) -> Optional[dict]:
    r = await execute("SELECT phone, uuid, token, updated_at FROM levi_sessions WHERE user_id=?", [user_id])
    if not r.rows:
        return None
    phone, uid, token, updated = r.rows[0]
    return {"phone": phone, "uuid": uid, "token": token or None, "updated_at": updated}


async def is_logged_in(user_id: int) -> bool:
    s = await get_session(user_id)
    return bool(s and s["token"])


async def get_token(user_id: int) -> Optional[str]:
    s = await get_session(user_id)
    return s["token"] if s else None


async def logout(user_id: int) -> None:
    await execute("DELETE FROM levi_sessions WHERE user_id=?", [user_id])


# ── Login flow ──────────────────────────────────────────────────────────────

async def send_sms(user_id: int, phone: str) -> None:
    """Ask Levi Yitzhak to SMS a 6-digit code to `phone` (already normalised).
    Keeps one device uuid per user, as the app keeps one per device. Raises LeviError."""
    s = await get_session(user_id)
    device = s["uuid"] if s else str(_uuid.uuid4())
    try:
        res = await _post("/users/send-validation-sms", {"phone": phone, "uuid": device})
    except httpx.HTTPError as e:
        logger.warning("Levi send-sms network error: %s", e)
        raise LeviError("אין חיבור לשרת של לוי יצחק כרגע, נסו שוב בעוד רגע")
    if res.get("status") != 1:
        if res.get("status") == 0 and res.get("data") == "phone":
            raise LeviError("מספר הטלפון לא תקין")
        raise LeviError(str(res.get("msg") or res.get("error") or "שליחת ה-SMS נכשלה"))
    # A new login replaces any previous token; the token is set only after validation.
    await execute(
        "INSERT INTO levi_sessions (user_id, phone, uuid, token) VALUES (?, ?, ?, NULL) "
        "ON CONFLICT(user_id) DO UPDATE SET phone=excluded.phone, uuid=excluded.uuid, "
        "token=NULL, updated_at=datetime('now')",
        [user_id, phone, device],
    )


# validate_sms outcomes
OK, EXPIRED, WRONG_CODE = "ok", "expired", "wrong_code"


async def validate_sms(user_id: int, code: str) -> str:
    """Validate the SMS code. Returns OK / EXPIRED (start over) / WRONG_CODE (retry).
    Raises LeviError for other failures."""
    s = await get_session(user_id)
    if not s:
        return EXPIRED
    try:
        res = await _post("/users/validate-sms", {"uuid": s["uuid"], "phone": s["phone"], "code": code})
    except httpx.HTTPError as e:
        logger.warning("Levi validate-sms network error: %s", e)
        raise LeviError("אין חיבור לשרת של לוי יצחק כרגע, נסו שוב בעוד רגע")
    status = res.get("status")
    if status == 1:
        token = res.get("data")
        if isinstance(token, dict):   # tolerate {"token": "..."} shapes
            token = token.get("token") or token.get("jwt")
        if not isinstance(token, str) or not token:
            raise LeviError("ההתחברות הצליחה אך לא התקבל אסימון גישה")
        await execute(
            "UPDATE levi_sessions SET token=?, updated_at=datetime('now') WHERE user_id=?",
            [token, user_id],
        )
        return OK
    if status == 2:
        return WRONG_CODE
    if status == 0:
        return EXPIRED
    raise LeviError(str(res.get("msg") or "התרחשה שגיאה, נסו שוב"))


# ── Price list lookup ───────────────────────────────────────────────────────

class LeviAuthError(LeviError):
    """The stored token is missing/expired — the user must log in again."""


def _first(v):
    """Levi returns many fields as 1-item arrays (XML→JSON); unwrap them."""
    if isinstance(v, list):
        v = v[0] if v else None
    if isinstance(v, str):
        v = v.strip()
    return v if v not in ("", None) else None


def _num(v) -> Optional[float]:
    v = _first(v)
    try:
        return float(str(v).replace(",", "")) if v is not None else None
    except ValueError:
        return None


def _name(v) -> Optional[str]:
    if isinstance(v, dict):
        return _first(v.get("name"))
    return _first(v)


def summarize_plate(data: dict, plate: str) -> dict:
    """Pick the display fields out of a /main/new-get-by-licence-plate/ `data` object."""
    search = data.get("search") or {}
    car = data.get("car") or {}
    return {
        "plate": plate,
        "manufacturer": _name(search.get("manufacturer")) or _first(car.get("manufacturerName")),
        "model": _name(search.get("model")),
        "trim": _first(car.get("name")) or _name(search.get("subModel")),
        "year": _first(car.get("year")) or _first(car.get("singleYear")),
        "type": _name(car.get("type")) or _name(search.get("type")),
        "trim_level": _first(car.get("ramatGimur")),
        "aliya": _first(car.get("aliyaDate")) or _first(search.get("aliya")),
        "engine_cc": _num(car.get("engineVolume")),
        "price": _num(car.get("price")) or _num(car.get("singlePrice")),
    }


async def lookup_plate(user_id: int, plate: str) -> dict:
    """Look a plate up in the Levi Yitzhak price list on the user's account.
    Returns {"summary": {...}, "raw": <response data>}. Raises LeviAuthError / LeviError."""
    token = await get_token(user_id)
    if not token:
        raise LeviAuthError("צריך להתחבר ללוי יצחק")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                f"{API_BASE}/main/new-get-by-licence-plate/",
                json={"plate": int(plate), "isMotorcycleSearch": False},
                headers={**_HEADERS, "Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as e:
        logger.warning("Levi plate lookup network error: %s", e)
        raise LeviError("אין חיבור לשרת של לוי יצחק כרגע, נסו שוב בעוד רגע")
    if r.status_code in (401, 403):
        await execute("UPDATE levi_sessions SET token=NULL WHERE user_id=?", [user_id])
        raise LeviAuthError("פג תוקף ההתחברות ללוי יצחק")
    try:
        res = r.json()
    except ValueError:
        raise LeviError(f"תשובה לא תקינה מהשרת ({r.status_code})")
    if not isinstance(res, dict) or res.get("status") != 1 or not isinstance(res.get("data"), dict):
        msg = res.get("msg") if isinstance(res, dict) else None
        raise LeviError(str(msg or "הרכב לא נמצא במחירון לוי יצחק"))
    return {"summary": summarize_plate(res["data"], plate), "raw": res["data"]}
