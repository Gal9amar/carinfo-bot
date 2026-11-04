"""Crypto payments: Binance Pay and USDT (TRC20) to a wallet address — the buyer PASTES THE TRANSACTION ID,
the server verifies it and approves the order automatically.

Flow:
* The buyer picks a method on the payment screen → `start_payment` creates a `crypto_payments` row with the
  amount to send: the order price in ₪ ÷ the admin-set rate (`crypto_fx_rate`), rounded UP to the cent (locked at
  that moment), plus the destination (Binance Pay ID / wallet address).
* After paying, the buyer pastes the transaction id: Binance Pay "Order ID / Transaction ID", or the on-chain TRC20
  transaction hash (64 hex). `verify_payment` looks that exact transaction up (Binance Pay history / TronGrid),
  checks it, claims it and approves the order through `api._approve_order` (same path as a manual admin approval).
  There is no background scanning and no unique amount: nothing is credited before the buyer pastes the id.

What is checked (all must hold, otherwise nothing is credited and the buyer gets a specific message):
* the transaction exists, is incoming to US (Binance Pay: positive amount; TRC20: to the configured address,
  confirmed, USDT contract only) and is a stable coin (USDT/USDC/FDUSD/BUSD for Binance Pay);
* amount ≥ the amount locked for this payment (−0.01 tolerance; a higher amount is accepted);
* it happened AFTER the payment request was opened (minus a 5-minute slack) — an old transfer cannot be pasted;
* it was never used before (`crypto_tx_used`, PRIMARY KEY, claimed BEFORE the order is approved);
* the order is still open (intent/created) and the buyer has attempts left (MAX_ATTEMPTS per request).
A request can be verified for 24 h after it was opened; `crypto_expiry_minutes` is only how long the locked rate
and the "send it now" window are advertised to the buyer.

Settings (bot_settings): crypto_binance_enabled, crypto_binance_id, crypto_trc20_enabled, crypto_trc20_address,
crypto_fx_rate (₪ per 1 USDT), crypto_expiry_minutes, crypto_*_name / crypto_*_logo.
Env: BINANCE_API_KEY / BINANCE_API_SECRET (read-only key with "Enable Reading"), optional TRONGRID_API_KEY.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.db import execute, get_bot_setting

logger = logging.getLogger(__name__)

METHODS = ("BINANCE_PAY", "USDT_TRC20")
MAX_ATTEMPTS = 8
_AMOUNT_TOLERANCE = 0.01
_SLACK = timedelta(minutes=5)
_VERIFY_WINDOW = timedelta(hours=24)
_STABLES = {"USDT", "USDC", "BUSD", "FDUSD"}
_USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
_BINANCE_BASE = "https://api.binance.com"
_TRONGRID = "https://api.trongrid.io"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")


def _ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


async def init_crypto() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS crypto_payments (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ref          TEXT    NOT NULL,
            user_id      INTEGER NOT NULL,
            method       TEXT    NOT NULL,
            amount_ils   REAL    NOT NULL,
            amount_usd   REAL    NOT NULL,
            fx_rate      REAL    NOT NULL,
            address      TEXT    DEFAULT '',
            status       TEXT    DEFAULT 'pending',
            tx_id        TEXT,
            created_at   TEXT    DEFAULT (datetime('now')),
            expires_at   TEXT    NOT NULL,
            confirmed_at TEXT
        )
    """)
    try:
        await execute("ALTER TABLE crypto_payments ADD COLUMN attempts INTEGER DEFAULT 0")
    except Exception:
        pass
    await execute("CREATE INDEX IF NOT EXISTS idx_crypto_payments_status ON crypto_payments(status, method)")
    await execute("CREATE INDEX IF NOT EXISTS idx_crypto_payments_ref ON crypto_payments(ref)")
    # One row per credited transaction: the PRIMARY KEY is the double-credit guard.
    await execute("""
        CREATE TABLE IF NOT EXISTS crypto_tx_used (
            tx_id      TEXT PRIMARY KEY,
            payment_id INTEGER,
            used_at    TEXT DEFAULT (datetime('now'))
        )
    """)


# ── Settings ────────────────────────────────────────────────────────────────

def valid_trc20_address(addr: str) -> bool:
    return len(addr) == 34 and addr.startswith("T") and addr.isalnum()


async def get_config() -> dict:
    """Effective configuration (what the buyer may use right now)."""
    try:
        fx = float((await get_bot_setting("crypto_fx_rate")) or "3.6")
    except ValueError:
        fx = 3.6
    try:
        expiry = int((await get_bot_setting("crypto_expiry_minutes")) or "30")
    except ValueError:
        expiry = 30
    binance_id = ((await get_bot_setting("crypto_binance_id")) or "").strip()
    address = ((await get_bot_setting("crypto_trc20_address")) or "").strip()
    api_ready = bool(os.environ.get("BINANCE_API_KEY") and os.environ.get("BINANCE_API_SECRET"))
    binance_flag = (await get_bot_setting("crypto_binance_enabled")) == "1"
    trc20_flag = (await get_bot_setting("crypto_trc20_enabled")) == "1"
    binance_ready = bool(binance_id) and api_ready
    trc20_ready = valid_trc20_address(address)
    return {
        "enabled": (binance_flag and binance_ready) or (trc20_flag and trc20_ready),
        "fx_rate": fx if fx > 0 else 3.6, "expiry_minutes": max(5, min(240, expiry)),
        "binance_pay": {"enabled": binance_flag and binance_ready, "ready": binance_ready, "flag": binance_flag, "pay_id": binance_id,
                        "name": ((await get_bot_setting("crypto_binance_name")) or "").strip() or "Binance Pay",
                        "logo": ((await get_bot_setting("crypto_binance_logo")) or "").strip()},
        "usdt_trc20": {"enabled": trc20_flag and trc20_ready, "ready": trc20_ready, "flag": trc20_flag, "address": address,
                       "name": ((await get_bot_setting("crypto_trc20_name")) or "").strip() or "USDT · כתובת ארנק (TRC20)",
                       "logo": ((await get_bot_setting("crypto_trc20_logo")) or "").strip()},
        "binance_api_configured": api_ready,
    }


# ── Creating a payment request ──────────────────────────────────────────────

class CryptoError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


_COLS = "id, ref, user_id, method, amount_ils, amount_usd, fx_rate, address, status, tx_id, created_at, expires_at, confirmed_at, COALESCE(attempts, 0)"


def _public(row: tuple) -> dict:
    (pid, ref, _uid, method, amount_ils, amount_usd, fx, address, status, tx_id, created_at, expires_at, confirmed_at) = row[:13]
    d = {
        "id": pid, "ref": ref, "method": method, "amount_ils": amount_ils, "amount_usd": round(amount_usd, 2),
        "fx_rate": fx, "status": status, "created_at": created_at, "expires_at": expires_at,
        "confirmed_at": confirmed_at, "tx_id": tx_id,
        "attempts_left": max(0, MAX_ATTEMPTS - int(row[13])) if len(row) > 13 else MAX_ATTEMPTS,
    }
    if method == "USDT_TRC20":
        d["address"] = address
        d["network"] = "TRC20"
    else:
        d["pay_id"] = address   # Binance Pay ID is stored in the `address` column
    return d


async def start_payment(user_id: int, ref: str, method: str) -> dict:
    """Create (or return the open) crypto payment request of an order. Raises CryptoError."""
    if method not in METHODS:
        raise CryptoError("bad_method")
    cfg = await get_config()
    opt = cfg["binance_pay"] if method == "BINANCE_PAY" else cfg["usdt_trc20"]
    if not opt["enabled"]:
        raise CryptoError("method_disabled")

    r = await execute("SELECT amount, status, user_id FROM paypal_transactions WHERE ref=?", [ref])
    if not r.rows or int(r.rows[0][2]) != int(user_id):
        raise CryptoError("order_not_found")
    amount_ils, order_status = float(r.rows[0][0]), r.rows[0][1]
    if order_status not in ("intent", "created"):
        raise CryptoError("order_closed")

    now = _now()
    r = await execute(f"SELECT {_COLS} FROM crypto_payments WHERE ref=? AND status='pending' ORDER BY id DESC", [ref])
    for row in r.rows:
        if row[3] == method and _parse(row[10]) > now - _VERIFY_WINDOW:
            return _public(row)
    if r.rows:
        await execute("UPDATE crypto_payments SET status='cancelled' WHERE ref=? AND status='pending'", [ref])

    fx = cfg["fx_rate"]
    amount_usd = math.ceil(round(amount_ils / fx, 6) * 100) / 100.0
    dest = opt["pay_id"] if method == "BINANCE_PAY" else opt["address"]
    expires = now + timedelta(minutes=cfg["expiry_minutes"])
    await execute(
        "INSERT INTO crypto_payments (ref, user_id, method, amount_ils, amount_usd, fx_rate, address, status, created_at, expires_at) "
        "VALUES (?,?,?,?,?,?,?, 'pending', ?, ?)",
        [ref, user_id, method, amount_ils, amount_usd, fx, dest, _iso(now), _iso(expires)],
    )
    r = await execute(f"SELECT {_COLS} FROM crypto_payments WHERE ref=? AND status='pending' ORDER BY id DESC LIMIT 1", [ref])
    return _public(r.rows[0])


async def get_payment_status(user_id: int, ref: str) -> Optional[dict]:
    """Latest crypto payment of an order (None if none); also reports the order's own status."""
    r = await execute(f"SELECT {_COLS} FROM crypto_payments WHERE ref=? AND user_id=? ORDER BY id DESC LIMIT 1", [ref, user_id])
    if not r.rows:
        return None
    d = _public(r.rows[0])
    o = await execute("SELECT status FROM paypal_transactions WHERE ref=? AND user_id=?", [ref, user_id])
    d["order_status"] = o.rows[0][0] if o.rows else None
    return d


# ── Looking a transaction up ────────────────────────────────────────────────

def _binance_sign(query: str) -> str:
    return hmac.new(os.environ["BINANCE_API_SECRET"].encode(), query.encode(), hashlib.sha256).hexdigest()


async def find_binance_pay_tx(tx_id: str, since_ms: int) -> Optional[dict] | str:
    """Binance Pay transaction whose transactionId OR orderId equals `tx_id`.
    Returns {id, amount, currency, time_ms}, None (not found) or "api_error"."""
    import httpx
    now_ms = int(time.time() * 1000)
    params = {"timestamp": now_ms, "limit": 100, "startTime": since_ms, "endTime": now_ms}
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{_BINANCE_BASE}/sapi/v1/pay/transactions?{query}&signature={_binance_sign(query)}"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url, headers={"X-MBX-APIKEY": os.environ["BINANCE_API_KEY"]})
        data = resp.json()
    except Exception as exc:
        logger.warning("crypto_pay: Binance Pay history failed: %s", type(exc).__name__)
        return "api_error"
    if not isinstance(data, dict) or data.get("code") != "000000":
        logger.warning("crypto_pay: Binance Pay history error: %s", data.get("msg") if isinstance(data, dict) else data)
        return "api_error"
    wanted = tx_id.strip()
    for tx in data.get("data", []):
        ids = {str(tx.get("transactionId") or ""), str(tx.get("orderId") or "")}
        if wanted not in ids:
            continue
        try:
            amount = float(tx.get("amount", 0))
            t_ms = int(tx.get("transactionTime", 0) or 0)
        except (TypeError, ValueError):
            return None
        return {"id": f"bp:{str(tx.get('transactionId') or tx.get('orderId'))}", "amount": amount,
                "currency": str(tx.get("currency", "")).upper(), "time_ms": t_ms}
    return None


async def find_trc20_tx(tx_hash: str, address: str, since_ms: int) -> Optional[dict] | str:
    """Confirmed incoming USDT-TRC20 transfer to `address` with this transaction hash.
    Returns {id, amount, currency, time_ms}, None (not found / not confirmed yet) or "api_error"."""
    import httpx
    headers = {"TRON-PRO-API-KEY": os.environ["TRONGRID_API_KEY"]} if os.environ.get("TRONGRID_API_KEY") else {}
    params = {"only_to": "true", "only_confirmed": "true", "limit": 200, "min_timestamp": since_ms,
              "contract_address": _USDT_TRC20_CONTRACT}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(f"{_TRONGRID}/v1/accounts/{address}/transactions/trc20", params=params, headers=headers)
        if resp.status_code != 200:
            logger.warning("crypto_pay: TronGrid HTTP %s", resp.status_code)
            return "api_error"
        data = resp.json()
    except Exception as exc:
        logger.warning("crypto_pay: TronGrid failed: %s", type(exc).__name__)
        return "api_error"
    wanted = tx_hash.strip().lower()
    for tx in data.get("data", []):
        if str(tx.get("transaction_id", "")).lower() != wanted:
            continue
        try:
            token = tx.get("token_info") or {}
            if tx.get("to") != address or token.get("address") != _USDT_TRC20_CONTRACT:
                return None
            amount = int(tx.get("value", "0")) / (10 ** int(token.get("decimals", 6)))
            t_ms = int(tx.get("block_timestamp", 0))
        except (TypeError, ValueError):
            return None
        return {"id": f"tron:{wanted}", "amount": amount, "currency": "USDT", "time_ms": t_ms}
    return None


# ── Verifying + confirming ──────────────────────────────────────────────────

async def _alert_admin(text: str) -> None:
    try:
        from src.notifier import notify_admin_text
        await notify_admin_text(text)
    except Exception:
        logger.exception("crypto_pay: admin alert failed")


async def _claim_tx(tx_id: str, payment_id: int) -> bool:
    """Atomically claim a transaction for a payment. False if it was already used by anything."""
    try:
        await execute("INSERT INTO crypto_tx_used (tx_id, payment_id) VALUES (?, ?)", [tx_id, payment_id])
        return True
    except Exception:
        return False


_TX_FORMAT = {
    "BINANCE_PAY": re.compile(r"^[A-Za-z0-9_\-]{6,80}$"),
    "USDT_TRC20": re.compile(r"^[0-9a-fA-F]{64}$"),
}


async def verify_payment(user_id: int, ref: str, tx_input: str) -> dict:
    """The buyer pasted a transaction id. Returns {"ok": True, ...} after the order was approved, otherwise
    {"ok": False, "error": <code>, ...}. Codes: bad_format, not_found, wrong_currency, amount_low, too_old,
    used, expired, order_closed, too_many_attempts, api_error, no_request, approve_failed."""
    tx_input = (tx_input or "").strip()
    r = await execute(f"SELECT {_COLS} FROM crypto_payments WHERE ref=? AND user_id=? ORDER BY id DESC LIMIT 1", [ref, user_id])
    if not r.rows:
        return {"ok": False, "error": "no_request"}
    row = r.rows[0]
    pid, method, amount_usd, status, created_at, attempts = row[0], row[3], row[5], row[8], row[10], int(row[13])
    if status == "confirmed":
        return {"ok": True, "already": True}
    if status != "pending" or _parse(created_at) <= _now() - _VERIFY_WINDOW:
        return {"ok": False, "error": "expired"}
    if not _TX_FORMAT[method].match(tx_input):
        return {"ok": False, "error": "bad_format"}
    if attempts >= MAX_ATTEMPTS:
        return {"ok": False, "error": "too_many_attempts"}
    o = await execute("SELECT status FROM paypal_transactions WHERE ref=? AND user_id=?", [ref, user_id])
    if not o.rows or o.rows[0][0] not in ("intent", "created"):
        return {"ok": False, "error": "order_closed"}

    await execute("UPDATE crypto_payments SET attempts = COALESCE(attempts, 0) + 1 WHERE id=?", [pid])
    left = MAX_ATTEMPTS - attempts - 1

    cfg = await get_config()
    since_ms = _ms(_parse(created_at) - _SLACK)
    if method == "BINANCE_PAY":
        if not cfg["binance_pay"]["ready"]:
            return {"ok": False, "error": "api_error", "attempts_left": left}
        tx = await find_binance_pay_tx(tx_input, since_ms)
    else:
        if not cfg["usdt_trc20"]["ready"]:
            return {"ok": False, "error": "api_error", "attempts_left": left}
        tx = await find_trc20_tx(tx_input, cfg["usdt_trc20"]["address"], since_ms)
    if tx == "api_error":
        return {"ok": False, "error": "api_error", "attempts_left": left}
    if tx is None:
        return {"ok": False, "error": "not_found", "attempts_left": left}
    if tx["amount"] <= 0:
        return {"ok": False, "error": "not_found", "attempts_left": left}
    if method == "BINANCE_PAY" and tx["currency"] not in _STABLES:
        return {"ok": False, "error": "wrong_currency", "currency": tx["currency"], "attempts_left": left}
    if tx["time_ms"] < since_ms:
        return {"ok": False, "error": "too_old", "attempts_left": left}
    if tx["amount"] + _AMOUNT_TOLERANCE < amount_usd:
        return {"ok": False, "error": "amount_low", "expected": round(amount_usd, 2), "got": round(tx["amount"], 2),
                "attempts_left": left}

    # Claim the transaction FIRST — if that fails it was already used (by anyone).
    if not await _claim_tx(tx["id"], pid):
        return {"ok": False, "error": "used", "attempts_left": left}
    await execute("UPDATE crypto_payments SET status='confirmed', tx_id=?, confirmed_at=? WHERE id=? AND status='pending'",
                  [tx["id"], _iso(_now()), pid])
    chk = await execute("SELECT status FROM crypto_payments WHERE id=?", [pid])
    if not chk.rows or chk.rows[0][0] != "confirmed":
        return {"ok": False, "error": "used", "attempts_left": left}
    try:
        from api import _approve_order   # same process; lazy import avoids a cycle at startup
        ok = await _approve_order(ref, completed_label="crypto_auto",
                                  note=f"קריפטו ({method}) {tx['amount']} {tx['currency']} · {tx['id']}")
    except Exception:
        logger.exception("crypto_pay: approving order %s failed", ref)
        ok = False
    if not ok:
        await _alert_admin(f"🚨 תשלום קריפטו אומת אך אישור ההזמנה {ref} נכשל. עסקה {tx['id']} ({tx['amount']} {tx['currency']}). אשר ידנית בטאב הזמנות.")
        return {"ok": False, "error": "approve_failed"}
    if tx["amount"] > amount_usd + 0.5:
        await _alert_admin(f"ℹ️ תשלום קריפטו להזמנה {ref} גבוה מהנדרש: שולם {tx['amount']} במקום {amount_usd:.2f} ({method}).")
    return {"ok": True, "amount": round(tx["amount"], 2)}


async def list_recent(limit: int = 50) -> list[dict]:
    r = await execute(f"SELECT {_COLS} FROM crypto_payments ORDER BY id DESC LIMIT ?", [limit])
    return [{**_public(row), "user_id": row[2]} for row in r.rows]
