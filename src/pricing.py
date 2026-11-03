"""Levi Yitzhak list price vs. the Yad2 market, and the premium extras shared by the PDF / bot / Mini App.

Market data = Yad2 listing statistics (src.yad2.get_market_price_cached). It is only ever shown to users who
may see it in the Mini App (feature enabled + public window / group, or admin) — see features.market_visible.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def market_for_record(record: dict) -> Optional[dict]:
    from src.yad2 import get_market_price_cached
    make = str(record.get("tozeret_nm") or "").strip()
    model = str(record.get("kinuy_mishari") or record.get("degem_nm") or "").strip()
    year = record.get("shnat_yitzur") or ""
    if not make:
        return None
    return await get_market_price_cached(make, model, year)


def market_median(market: Optional[dict]) -> Optional[int]:
    if not market:
        return None
    v = market.get("median") or market.get("avg")
    try:
        return int(float(v)) if v else None
    except (TypeError, ValueError):
        return None


def compare(levi_price, market: Optional[dict]) -> Optional[dict]:
    """{"pct", "levi", "market", "count"}: pct < 0 → the Levi list price is BELOW the Yad2 median."""
    med = market_median(market)
    try:
        levi = int(float(levi_price)) if levi_price else None
    except (TypeError, ValueError):
        levi = None
    if not levi or not med:
        return None
    return {
        "pct": round((levi - med) / med * 100, 1),
        "levi": levi,
        "market": med,
        "count": (market or {}).get("count") or (market or {}).get("total"),
    }


def compare_text(c: dict) -> str:
    """Short Hebrew line, e.g. 'נמוך ב־8% מחציון המודעות ביד2 (₪68,500 · 14 מודעות)'."""
    pct = abs(round(c["pct"]))
    where = f"₪{c['market']:,}" + (f" · {c['count']} מודעות" if c.get("count") else "")
    if pct < 1:
        return f"בקירוב כמו חציון המודעות ביד2 ({where})"
    return f"{'נמוך' if c['pct'] < 0 else 'גבוה'} ב־{pct}% מחציון המודעות ביד2 ({where})"


async def market_for_plate(user_id: int, plate: str, record: Optional[dict] = None) -> Optional[dict]:
    """Yad2 market stats for `plate`, or None when the user may not see market data / nothing was found."""
    from src.features import market_visible
    if not await market_visible(user_id):
        return None
    if record is None:
        from src.api.gov_api import fetch_vehicle_data
        from src.cache import cache
        record = cache.get(plate)
        if record is None:
            record = await fetch_vehicle_data(plate)
            if record:
                cache.set(plate, record)
    if not record:
        return None
    return await market_for_record(record)


async def premium_extras(user_id: int, plate: str, record: dict) -> dict:
    """Everything the PDF report adds for an entitled user: Levi list price, registered insurer and the
    Levi-vs-Yad2 comparison. Each part is independent, time-boxed and silently omitted on any problem."""
    from src import insurance as ins
    from src import levi
    from src.features import insurance_open, levi_open

    async def _levi():
        if not await levi_open(user_id) or not await levi.is_logged_in(user_id):
            return None
        try:
            return (await asyncio.wait_for(levi.lookup_plate(user_id, plate), timeout=8))["summary"]
        except Exception as exc:
            logger.info("PDF extras: Levi skipped for %s: %s", plate, exc)
            return None

    async def _ins():
        if not await insurance_open(user_id):
            return None
        try:
            return await asyncio.wait_for(ins.check_plate(plate), timeout=10)
        except Exception as exc:
            logger.info("PDF extras: insurance skipped for %s: %s", plate, exc)
            return None

    async def _market():
        try:
            return await asyncio.wait_for(market_for_plate(user_id, plate, record), timeout=10)
        except Exception as exc:
            logger.info("PDF extras: market skipped for %s: %s", plate, exc)
            return None

    levi_summary, insurance, market = await asyncio.gather(_levi(), _ins(), _market())
    cmp = compare(levi_summary.get("price") if levi_summary else None, market)
    return {"levi": levi_summary, "insurance": insurance, "market": market, "compare": cmp}
