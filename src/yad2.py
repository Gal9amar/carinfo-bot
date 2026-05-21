"""
Yad2 URL builder for vehicle market-price links.

Tries to resolve the manufacturer ID from Yad2's own API (cached 24h).
Falls back to a hardcoded mapping of the most common Israeli-market makes.
"""

from __future__ import annotations

import time
from typing import Optional

# ── Static fallback mapping ───────────────────────────────────────────────────
# Hebrew names as returned by the Israeli transport-ministry API → Yad2 mfr ID
_STATIC_MAKES: dict[str, int] = {
    "טויוטה":          2,
    "שברולט":          3,
    "סיטרואן":         4,
    "פיאט":            6,
    "פורד":            7,
    "הונדה":          11,
    "יונדאי":         12,
    "אאודי":          13,
    "ג'יפ":           14,
    "ב.מ.וו":         15,
    "לנד רובר":       17,
    "קיה":            18,
    "מרצדס בנץ":      19,
    "מזדה":           20,
    "מיצובישי":       21,
    "ניסאן":          22,
    "מיני":           23,
    "אופל":           25,
    "פיג'ו":          26,
    "פיג׳ו":          26,
    "רנו":            28,
    "סיאט":           33,
    "סקודה":          34,
    "סובארו":         36,
    "סוזוקי":         37,
    "פולקסווגן":      38,
    "וולוו":          41,
    "טסלה":           45,
    "לקסוס":          47,
    "דאצ'יה":         48,
    "דאציה":          48,
    "אלפא רומיאו":     1,
}

# ── Dynamic cache ─────────────────────────────────────────────────────────────
_CACHE_TTL = 86_400  # 24 hours
_cache: dict[str, int] = {}
_cache_ts: float = 0.0


async def _fetch_manufacturers() -> dict[str, int]:
    """Fetch manufacturer list from Yad2 API. Returns {} on any failure."""
    endpoints = [
        "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/getManufacturers",
        "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars/getFeedFilters",
    ]
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.yad2.co.il/",
        }
        async with httpx.AsyncClient(timeout=5, headers=headers) as client:
            for url in endpoints:
                try:
                    r = await client.get(url)
                    if r.status_code != 200:
                        continue
                    data = r.json()
                    # Try common response shapes
                    items = (
                        data.get("data", {}).get("manufacturer")
                        or data.get("data", {}).get("manufacturers")
                        or data.get("manufacturers")
                        or []
                    )
                    if items:
                        return {
                            item.get("text", item.get("name", "")): int(item.get("value", item.get("id", 0)))
                            for item in items
                            if item.get("text") or item.get("name")
                        }
                except Exception:
                    continue
    except Exception:
        pass
    return {}


async def _get_makes() -> dict[str, int]:
    """Return manufacturer map: dynamic (cached) merged over static fallback."""
    global _cache, _cache_ts
    if time.monotonic() - _cache_ts > _CACHE_TTL:
        fresh = await _fetch_manufacturers()
        if fresh:
            _cache = fresh
            _cache_ts = time.monotonic()
    return {**_STATIC_MAKES, **_cache}


def _normalize(name: str) -> str:
    return name.strip().replace("'", "'").replace('"', '"')


async def resolve_manufacturer_id(make: str) -> Optional[int]:
    makes = await _get_makes()
    n = _normalize(make)
    if n in makes:
        return makes[n]
    # Partial match for names like "מרצדס בנץ ישראל"
    for key, mid in makes.items():
        if key in n or n in key:
            return mid
    return None


async def build_url(record: dict) -> str:
    """Return a Yad2 search URL with manufacturer + year filters."""
    make  = (record.get("tozeret_nm") or "").strip()
    year  = (record.get("shnat_yitzur") or "")

    base  = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []

    if make:
        mid = await resolve_manufacturer_id(make)
        if mid:
            params.append(f"manufacturer={mid}")

    if year:
        try:
            y = int(year)
            params.append(f"yearFrom={y}&yearTo={y}")
        except ValueError:
            pass

    return f"{base}?{'&'.join(params)}" if params else base


def build_url_sync(record: dict) -> str:
    """Synchronous fallback using static mapping only (no API call)."""
    make  = (record.get("tozeret_nm") or "").strip()
    year  = (record.get("shnat_yitzur") or "")

    base   = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []

    n = _normalize(make)
    mid = _STATIC_MAKES.get(n)
    if mid is None:
        for key, val in _STATIC_MAKES.items():
            if key in n or n in key:
                mid = val
                break
    if mid:
        params.append(f"manufacturer={mid}")

    if year:
        try:
            y = int(year)
            params.append(f"yearFrom={y}&yearTo={y}")
        except ValueError:
            pass

    return f"{base}?{'&'.join(params)}" if params else base
