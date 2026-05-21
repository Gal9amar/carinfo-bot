"""
Yad2 URL builder — resolves manufacturer + model IDs from Yad2's API (cached 24h).
Year format: year=YYYY-YYYY  (not yearFrom/yearTo).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 86_400  # 24 h

_mfr_cache: dict[str, int] = {}
_mfr_ts: float = -_CACHE_TTL   # force fetch on first use

_model_cache: dict[int, dict[str, int]] = {}
_model_ts: dict[int, float] = {}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
}

_MFR_URLS = [
    "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/getManufacturers",
    "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/manufacturer",
    "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/getFeedFilters",
]

_MODEL_URLS = [
    "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/getModels?manufacturer={mid}",
    "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/model?manufacturer={mid}",
]


async def _get(url: str) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=2, headers=_HEADERS, follow_redirects=True) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.json()


def _extract_list(data: dict) -> list:
    """Try common shapes Yad2 uses for list responses."""
    d = data.get("data") or data
    if isinstance(d, dict):
        for key in ("manufacturer", "manufacturers", "model", "models", "items"):
            if isinstance(d.get(key), list):
                return d[key]
    if isinstance(d, list):
        return d
    return []


def _parse_pairs(items: list) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = (
            item.get("text") or item.get("name") or
            item.get("label") or item.get("manufacturerName") or ""
        ).strip()
        val = (
            item.get("value") or item.get("id") or
            item.get("manufacturerId") or item.get("modelId") or 0
        )
        if name and val:
            try:
                result[name] = int(val)
            except (TypeError, ValueError):
                pass
    return result


async def _fetch_manufacturers() -> dict[str, int]:
    for url in _MFR_URLS:
        try:
            data = await _get(url)
            pairs = _parse_pairs(_extract_list(data))
            if pairs:
                logger.info("Yad2: loaded %d manufacturers from %s", len(pairs), url)
                return pairs
        except Exception as exc:
            logger.debug("Yad2 mfr fetch failed (%s): %s", url, exc)
    return {}


async def _fetch_models(mid: int) -> dict[str, int]:
    for tmpl in _MODEL_URLS:
        url = tmpl.format(mid=mid)
        try:
            data = await _get(url)
            pairs = _parse_pairs(_extract_list(data))
            if pairs:
                logger.info("Yad2: loaded %d models for mfr %d", len(pairs), mid)
                return pairs
        except Exception as exc:
            logger.debug("Yad2 model fetch failed (%s): %s", url, exc)
    return {}


async def manufacturers() -> dict[str, int]:
    global _mfr_cache, _mfr_ts
    if time.monotonic() - _mfr_ts > _CACHE_TTL:
        fresh = await _fetch_manufacturers()
        if fresh:
            _mfr_cache = fresh
            _mfr_ts = time.monotonic()
    return _mfr_cache


async def models(mid: int) -> dict[str, int]:
    if time.monotonic() - _model_ts.get(mid, 0) > _CACHE_TTL:
        fresh = await _fetch_models(mid)
        if fresh:
            _model_cache[mid] = fresh
            _model_ts[mid] = time.monotonic()
    return _model_cache.get(mid, {})


def _best(name: str, mapping: dict[str, int]) -> Optional[int]:
    n = name.strip()
    if n in mapping:
        return mapping[n]
    for key, val in mapping.items():
        if key in n or n in key:
            return val
    return None


def _year_param(year_str: str) -> str:
    """Return 'year=YYYY-YYYY' or empty string."""
    try:
        y = int(year_str)
        return f"year={y}-{y}"
    except (TypeError, ValueError):
        return ""


async def build_url(record: dict) -> str:
    """
    Build a Yad2 search URL with manufacturer + model + year filters.
    Falls back gracefully: year-only if manufacturer lookup fails.
    """
    make  = (record.get("tozeret_nm") or "").strip()
    model_name = (record.get("kinuy_mishari") or record.get("degem_nm") or "").strip()
    year  = (record.get("shnat_yitzur") or "").strip()

    base   = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []

    if make:
        mfrs = await manufacturers()
        mid  = _best(make, mfrs)
        if mid:
            params.append(f"manufacturer={mid}")
            if model_name:
                mdls   = await models(mid)
                mod_id = _best(model_name, mdls)
                if mod_id:
                    params.append(f"model={mod_id}")

    yr = _year_param(year)
    if yr:
        params.append(yr)

    return f"{base}?{'&'.join(params)}" if params else base
