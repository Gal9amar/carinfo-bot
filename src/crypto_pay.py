"""Crypto payments with AUTOMATIC detection: Binance Pay and USDT (TRC20) to a wallet address.

How it works (same idea as the TG-Store-Bot Binance Pay auto-deposit):
* The buyer picks a method on the payment screen → `start_payment` creates a `crypto_payments` row with an
  EXACT, unique USDT amount: the order price in ₪ ÷ the admin-set rate (`crypto_fx_rate`), rounded up to the cent,
  plus 1–60 "tag" cents that no other open payment of the same method uses. The buyer must send exactly that amount.
* `scan_once` (bot job, every 30 s) reads the incoming Binance Pay history / the TRC20 transfers of the wallet,
  and when an incoming transfer matches an open payment's amount (±0.005) AND arrived after the payment was
  created, it confirms the payment and approves the order automatically (api._approve_order).

Safety:
* a transfer id can only ever be used once (`crypto_tx_used`, PRIMARY KEY) — claimed BEFORE the order is approved;
* a transfer that is older than the payment, in a different coin, or matches more than one open payment/transfer is
  never auto-used (ambiguous → the admin is alerted);
* a transfer that arrives after the payment expired is NOT auto-approved: the admin is alerted ("late payment");
* only incoming stablecoin transfers (USDT/USDC/FDUSD…) count for Binance Pay; TRC20 only counts the USDT contract.

Settings (bot_settings): crypto_enabled, crypto_binance_enabled, crypto_binance_id (the Pay ID buyers send to),
crypto_trc20_enabled, crypto_trc20_address, crypto_fx_rate (₪ per 1 USDT), crypto_expiry_minutes.
Env: BINANCE_API_KEY / BINANCE_API_SECRET (read-only key with "Enable Reading"), optional TRONGRID_API_KEY.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.db import execute, get_bot_setting

logger = logging.getLogger(__name__)

METHODS = ("BINANCE_PAY", "USDT_TRC20")
_AMOUNT_TOLERANCE = 0.005
_MAX_TAG_CENTS = 60
_STABLES = {"USDT", "USDC", "BUSD", "FDUSD"}
_USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
_BINANCE_BASE = "https://api.binance.com"
_TRONGRID = "https://api.trongrid.io"
_LATE_WINDOW_HOURS = 6        # an expired payment still triggers an admin alert if its money shows up late
_scan_lock = asyncio.Lock()
_late_alerted: set[int] = set()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")


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
    await execute("CREATE INDEX IF NOT EXISTS idx_crypto_payments_status ON crypto_payments(status, method)")
    await execute("CREATE INDEX IF NOT EXISTS idx_crypto_payments_ref ON crypto_payments(ref)")
    # One row per credited transfer: the PRIMARY KEY is the double-credit guard.
    await execute("""
        CREATE TABLE IF NOT EXISTS crypto_tx_used (
            tx_id      TEXT PRIMARY KEY,
            payment_id INTEGER,
            used_at    TEXT DEFAULT (datetime('now'))
        )
    """)


# ── Settings ────────────────────────────────────────────────────────────────

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
    binance_ready = bool(binance_id) and api_ready          # can be scanned (even if just switched off)
    trc20_ready = valid_trc20_address(address)
    binance_on = binance_flag and binance_ready             # offered to buyers
    trc20_on = trc20_flag and trc20_ready
    return {
        "enabled": binance_on or trc20_on, "fx_rate": fx if fx > 0 else 3.6, "expiry_minutes": max(5, min(240, expiry)),
        "binance_pay": {"enabled": binance_on, "ready": binance_ready, "flag": binance_flag, "pay_id": binance_id,
                        "name": ((await get_bot_setting("crypto_binance_name")) or "").strip() or "Binance Pay",
                        "logo": ((await get_bot_setting("crypto_binance_logo")) or "").strip()},
        "usdt_trc20": {"enabled": trc20_on, "ready": trc20_ready, "flag": trc20_flag, "address": address,
                       "name": ((await get_bot_setting("crypto_trc20_name")) or "").strip() or "USDT · כתובת ארנק (TRC20)",
                       "logo": ((await get_bot_setting("crypto_trc20_logo")) or "").strip()},
        "binance_api_configured": api_ready,
    }


def valid_trc20_address(addr: str) -> bool:
    return len(addr) == 34 and addr.startswith("T") and addr.isalnum()


# ── Creating a payment ──────────────────────────────────────────────────────

class CryptoError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _public(row: tuple, cfg: dict | None = None) -> dict:
    (pid, ref, _uid, method, amount_ils, amount_usd, fx, address, status, tx_id, created_at, expires_at, confirmed_at) = row[:13]
    d = {
        "id": pid, "ref": ref, "method": method, "amount_ils": amount_ils, "amount_usd": round(amount_usd, 2),
        "fx_rate": fx, "status": status, "created_at": created_at, "expires_at": expires_at,
        "confirmed_at": confirmed_at, "tx_id": tx_id,
    }
    if method == "USDT_TRC20":
        d["address"] = address
        d["network"] = "TRC20"
    else:
        d["pay_id"] = address   # Binance Pay ID is stored in the `address` column
    return d


_COLS = "id, ref, user_id, method, amount_ils, amount_usd, fx_rate, address, status, tx_id, created_at, expires_at, confirmed_at"


async def start_payment(user_id: int, ref: str, method: str) -> dict:
    """Create (or return the open) crypto payment of an order. Raises CryptoError."""
    if method not in METHODS:
        raise CryptoError("bad_method")
    cfg = await get_config()
    opt = cfg["binance_pay"] if method == "BINANCE_PAY" else cfg["usdt_trc20"]
    if not opt["enabled"]:
        raise CryptoError("method_disabled")

    r = await execute(
        "SELECT amount, status, user_id FROM paypal_transactions WHERE ref=?", [ref])
    if not r.rows or int(r.rows[0][2]) != int(user_id):
        raise CryptoError("order_not_found")
    amount_ils, order_status = float(r.rows[0][0]), r.rows[0][1]
    if order_status not in ("intent", "created"):
        raise CryptoError("order_closed")

    now = _now()
    # Expire stale ones first (cheap, keeps the unique-amount pool small).
    await execute("UPDATE crypto_payments SET status='expired' WHERE status='pending' AND expires_at <= ?", [_iso(now)])

    # Reuse this order's open payment for the same method (idempotent) — a different method cancels the old one.
    r = await execute(f"SELECT {_COLS} FROM crypto_payments WHERE ref=? AND status='pending' ORDER BY id DESC", [ref])
    for row in r.rows:
        if row[3] == method:
            return _public(row)
    if r.rows:
        await execute("UPDATE crypto_payments SET status='cancelled' WHERE ref=? AND status='pending'", [ref])

    fx = cfg["fx_rate"]
    base = math.ceil(round(amount_ils / fx, 6) * 100) / 100.0
    taken = {round(float(a[0]), 2) for a in (await execute(
        "SELECT amount_usd FROM crypto_payments WHERE status='pending' AND method=?", [method])).rows}
    amount_usd = None
    for tag in range(1, _MAX_TAG_CENTS + 1):
        candidate = round(base + tag / 100.0, 2)
        if candidate not in taken:
            amount_usd = candidate
            break
    if amount_usd is None:
        raise CryptoError("busy")

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
    row = list(r.rows[0])
    d = _public(tuple(row))
    if d["status"] == "pending" and _parse(d["expires_at"]) <= _now():
        await execute("UPDATE crypto_payments SET status='expired' WHERE id=? AND status='pending'", [d["id"]])
        d["status"] = "expired"
    o = await execute("SELECT status FROM paypal_transactions WHERE ref=? AND user_id=?", [ref, user_id])
    d["order_status"] = o.rows[0][0] if o.rows else None
    return d


# ── Reading the incoming transfers ──────────────────────────────────────────

def _binance_sign(query: str) -> str:
    return hmac.new(os.environ["BINANCE_API_SECRET"].encode(), query.encode(), hashlib.sha256).hexdigest()


async def fetch_binance_incoming(since_ms: int) -> Optional[list[dict]]:
    """Incoming Binance Pay transfers since `since_ms` as [{id, amount, currency, time_ms}]; None on API error."""
    import httpx
    params = {"timestamp": int(time.time() * 1000), "limit": 100, "startTime": since_ms, "endTime": int(time.time() * 1000)}
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{_BINANCE_BASE}/sapi/v1/pay/transactions?{query}&signature={_binance_sign(query)}"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(url, headers={"X-MBX-APIKEY": os.environ["BINANCE_API_KEY"]})
        data = resp.json()
    except Exception as exc:
        logger.warning("crypto_pay: Binance Pay history failed: %s", type(exc).__name__)
        return None
    if not isinstance(data, dict) or data.get("code") != "000000":
        logger.warning("crypto_pay: Binance Pay history error: %s", (data or {}).get("msg") if isinstance(data, dict) else data)
        return None
    out = []
    for tx in data.get("data", []):
        try:
            amount = float(tx.get("amount", 0))
            t_ms = int(tx.get("transactionTime", 0) or 0)
        except (TypeError, ValueError):
            continue
        tid = str(tx.get("transactionId") or tx.get("orderId") or "")
        if amount > 0 and tid and t_ms >= since_ms and str(tx.get("currency", "")).upper() in _STABLES:
            out.append({"id": f"bp:{tid}", "amount": amount, "currency": str(tx.get("currency", "")).upper(), "time_ms": t_ms})
    return out


async def fetch_trc20_incoming(address: str, since_ms: int) -> Optional[list[dict]]:
    """Confirmed incoming USDT-TRC20 transfers to `address` since `since_ms`; None on API error."""
    import httpx
    headers = {"TRON-PRO-API-KEY": os.environ["TRONGRID_API_KEY"]} if os.environ.get("TRONGRID_API_KEY") else {}
    params = {"only_to": "true", "only_confirmed": "true", "limit": 100, "min_timestamp": since_ms,
              "contract_address": _USDT_TRC20_CONTRACT}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            resp = await c.get(f"{_TRONGRID}/v1/accounts/{address}/transactions/trc20", params=params, headers=headers)
        if resp.status_code != 200:
            logger.warning("crypto_pay: TronGrid HTTP %s", resp.status_code)
            return None
        data = resp.json()
    except Exception as exc:
        logger.warning("crypto_pay: TronGrid failed: %s", type(exc).__name__)
        return None
    out = []
    for tx in data.get("data", []):
        try:
            if tx.get("to") != address or (tx.get("token_info") or {}).get("address") != _USDT_TRC20_CONTRACT:
                continue
            decimals = int((tx.get("token_info") or {}).get("decimals", 6))
            amount = int(tx.get("value", "0")) / (10 ** decimals)
            t_ms = int(tx.get("block_timestamp", 0))
        except (TypeError, ValueError):
            continue
        if tx.get("transaction_id") and t_ms >= since_ms:
            out.append({"id": f"tron:{tx['transaction_id']}", "amount": amount, "currency": "USDT", "time_ms": t_ms})
    return out


# ── Matching + confirming ───────────────────────────────────────────────────

async def _claim_tx(tx_id: str, payment_id: int) -> bool:
    """Atomically claim a transfer for a payment. False if it was already used by anything."""
    try:
        await execute("INSERT INTO crypto_tx_used (tx_id, payment_id) VALUES (?, ?)", [tx_id, payment_id])
        return True
    except Exception:
        return False


async def _tx_used(tx_id: str) -> bool:
    return bool((await execute("SELECT 1 FROM crypto_tx_used WHERE tx_id=?", [tx_id])).rows)


async def _alert_admin(text: str) -> None:
    try:
        from src.notifier import notify_admin_text
        await notify_admin_text(text)
    except Exception:
        logger.exception("crypto_pay: admin alert failed")


async def scan_once() -> int:
    """One detection pass; returns the number of orders auto-approved."""
    if _scan_lock.locked():
        return 0
    async with _scan_lock:
        cfg = await get_config()
        now = _now()
        await execute("UPDATE crypto_payments SET status='expired' WHERE status='pending' AND expires_at <= ?", [_iso(now)])
        horizon = _iso(now - timedelta(hours=_LATE_WINDOW_HOURS))
        r = await execute(
            f"SELECT {_COLS} FROM crypto_payments WHERE status='pending' OR (status='expired' AND expires_at > ?)", [horizon])
        rows = [row for row in r.rows]
        if not rows:
            return 0

        approved = 0
        for method in METHODS:
            mine = [row for row in rows if row[3] == method]
            if not mine:
                continue
            opt = cfg["binance_pay"] if method == "BINANCE_PAY" else cfg["usdt_trc20"]
            if not opt["ready"]:          # a method switched OFF still gets its already-open payments detected
                continue
            since = min(_parse(row[10]) for row in mine) - timedelta(minutes=2)
            since_ms = int(since.replace(tzinfo=timezone.utc).timestamp() * 1000)
            txs = (await fetch_binance_incoming(since_ms)) if method == "BINANCE_PAY" else (await fetch_trc20_incoming(opt["address"], since_ms))
            if txs is None:
                continue                      # API trouble: never treat as "nothing arrived"
            for row in mine:
                approved += await _try_match(row, txs, now)
        return approved


async def _try_match(row: tuple, txs: list[dict], now: datetime) -> int:
    pid, ref, user_id, method, amount_ils, amount_usd, _fx, _addr, status, _tx, created_at, expires_at, _c = row[:13]
    created_ms = int(_parse(created_at).replace(tzinfo=timezone.utc).timestamp() * 1000) - 5000
    cands = [t for t in txs
             if abs(t["amount"] - amount_usd) <= _AMOUNT_TOLERANCE and t["time_ms"] >= created_ms]
    fresh = []
    for t in cands:
        if not await _tx_used(t["id"]):
            fresh.append(t)
    if not fresh:
        return 0
    if len(fresh) > 1:
        if pid not in _late_alerted:
            _late_alerted.add(pid)
            lines = "\n".join(f"• {t['id']} — {t['amount']} {t['currency']}" for t in fresh)
            await _alert_admin(f"⚠️ תשלום קריפטו דורש בדיקה ידנית\nהזמנה {ref}: {amount_usd:.2f}$ ({method}) מתאימה ליותר מהעברה אחת:\n{lines}\nלא אושר אוטומטית.")
        return 0
    tx = fresh[0]

    if status == "expired":
        # Money arrived after the payment window: never auto-approve, but tell the admin once.
        if pid not in _late_alerted:
            _late_alerted.add(pid)
            await _alert_admin(
                f"⏰ תשלום קריפטו הגיע באיחור\nהזמנה {ref} (משתמש {user_id}): התקבלו {tx['amount']} {tx['currency']} "
                f"({method}) אחרי שפג התוקף. מזהה: {tx['id']}\nאפשר לאשר ידנית בטאב הזמנות.")
        return 0

    # The order must still be open (an admin may have approved/cancelled it manually meanwhile).
    o = await execute("SELECT status FROM paypal_transactions WHERE ref=?", [ref])
    if not o.rows or o.rows[0][0] not in ("intent", "created"):
        await execute("UPDATE crypto_payments SET status='order_closed' WHERE id=? AND status='pending'", [pid])
        if pid not in _late_alerted:
            _late_alerted.add(pid)
            await _alert_admin(f"⚠️ התקבל תשלום קריפטו להזמנה {ref} שכבר נסגרה (סטטוס {o.rows[0][0] if o.rows else 'לא קיימת'}). "
                               f"{tx['amount']} {tx['currency']} · {tx['id']} — בדוק אם צריך להחזיר.")
        return 0

    # Claim the transfer FIRST — if this fails someone else already used it.
    if not await _claim_tx(tx["id"], pid):
        return 0
    await execute("UPDATE crypto_payments SET status='confirmed', tx_id=?, confirmed_at=? WHERE id=? AND status='pending'",
                  [tx["id"], _iso(now), pid])
    chk = await execute("SELECT status FROM crypto_payments WHERE id=?", [pid])
    if not chk.rows or chk.rows[0][0] != "confirmed":
        return 0
    try:
        from api import _approve_order   # same process; lazy import avoids a cycle at startup
        ok = await _approve_order(ref, completed_label="crypto_auto", note=f"קריפטו ({method}) {tx['amount']} {tx['currency']} · {tx['id']}")
    except Exception:
        logger.exception("crypto_pay: approving order %s failed", ref)
        ok = False
    if not ok:
        await _alert_admin(f"🚨 תשלום קריפטו התקבל אך אישור ההזמנה {ref} נכשל. העברה {tx['id']} ({tx['amount']} {tx['currency']}). אשר ידנית בטאב הזמנות.")
        return 0
    return 1


async def list_recent(limit: int = 50) -> list[dict]:
    r = await execute(f"SELECT {_COLS} FROM crypto_payments ORDER BY id DESC LIMIT ?", [limit])
    return [{**_public(row), "user_id": row[2]} for row in r.rows]
