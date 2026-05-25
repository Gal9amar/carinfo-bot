"""
PayPal Orders API v2 + Webhook verification.
Env vars: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID, PAYPAL_MODE (live|sandbox)
"""
import os
import logging as _logging
_log = _logging.getLogger("paypal")
import httpx

_MODE   = os.environ.get("PAYPAL_MODE", "live")
_BASE   = "https://api-m.paypal.com" if _MODE == "live" else "https://api-m.sandbox.paypal.com"
_ID     = os.environ.get("PAYPAL_CLIENT_ID", "")
_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")


async def get_access_token() -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(_ID, _SECRET),
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()["access_token"]


async def create_order(amount: str, currency: str, custom_id: str, description: str) -> dict:
    webapp_url = os.environ.get("WEBAPP_URL", "https://carinfo-bot.onrender.com")
    token = await get_access_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": currency, "value": amount},
                    "description": description,
                    "custom_id": custom_id,
                }],
                "application_context": {
                    "brand_name": "CarInfo",
                    "user_action": "PAY_NOW",
                    "return_url": f"{webapp_url}/",
                    "cancel_url": f"{webapp_url}/",
                },
            },
        )
        if not r.is_success:
            _log.error("PayPal create_order %s: %s", r.status_code, r.text)
            raise Exception(f"PayPal {r.status_code}: {r.text}")
        return r.json()


async def capture_order(order_id: str) -> dict:
    token = await get_access_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        r.raise_for_status()
        return r.json()


async def verify_webhook(headers: dict, body_json: dict) -> bool:
    """Returns True if signature is valid (or PAYPAL_WEBHOOK_ID not configured)."""
    if not WEBHOOK_ID:
        return True
    token = await get_access_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_BASE}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "auth_algo":       headers.get("paypal-auth-algo", ""),
                "cert_url":        headers.get("paypal-cert-url", ""),
                "transmission_id": headers.get("paypal-transmission-id", ""),
                "transmission_sig":headers.get("paypal-transmission-sig", ""),
                "transmission_time":headers.get("paypal-transmission-time", ""),
                "webhook_id":      WEBHOOK_ID,
                "webhook_event":   body_json,
            },
        )
        if not r.is_success:
            return False
        return r.json().get("verification_status") == "SUCCESS"
