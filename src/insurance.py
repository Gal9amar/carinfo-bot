"""Registered-insurer lookup (ביטוח צד ג׳ / מקיף) — via the operator's own Car check API.

Car check (car-check-il.netlify.app) already queries the public "policy status" pages of 9 insurers in
parallel from its server (plate + event date) and lists 5 more that need manual verification (captcha / SMS).
We call that endpoint with today's date (Israel time) = "where is the car insured right now", instead of
re-implementing 14 insurer integrations. `INSURANCE_API_BASE` overrides the base URL.
"""
from __future__ import annotations

import logging
import os
import re

import httpx

from src.cache import cache
from src.reminders import today

logger = logging.getLogger(__name__)

API_BASE = os.environ.get("INSURANCE_API_BASE", "https://car-check-il.netlify.app").rstrip("/")


class InsuranceError(Exception):
    pass


async def check_plate(plate: str) -> dict:
    """{"date", "insured": [name], "no": [name], "failed": [{"name","url"}], "manual": [{"name","url","reason"}]}.
    Cached for an hour per plate+day. Raises InsuranceError on any failure."""
    plate = re.sub(r"\D", "", plate or "")
    if not plate:
        raise InsuranceError("מספר רכב לא תקין")
    day = str(today())
    key = f"ins:{plate}:{day}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(f"{API_BASE}/api/property-insurance-check",
                                 params={"plate": plate, "date": day}, headers={"Accept": "application/json"})
        data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("insurance check failed for %s: %s", plate, type(e).__name__)
        raise InsuranceError("בדיקת הביטוח לא זמינה כרגע")
    if r.status_code != 200 or not isinstance(data, dict) or not isinstance(data.get("auto"), list):
        raise InsuranceError(str(data.get("error") if isinstance(data, dict) and data.get("error") else "בדיקת הביטוח נכשלה"))
    out = {"date": day, "insured": [], "no": [], "failed": [], "manual": []}
    for row in data["auto"]:
        name, status = row.get("nameHe") or "", row.get("status")
        if status == "yes":
            out["insured"].append(name)
        elif status == "no":
            out["no"].append(name)
        else:
            out["failed"].append({"name": name, "url": row.get("officialUrl") or ""})
    for row in data.get("manual") or []:
        out["manual"].append({"name": row.get("nameHe") or "", "url": row.get("officialUrl") or "",
                              "reason": row.get("reasonHe") or ""})
    cache.set(key, out)
    return out
