"""
Yad2 URL builder for vehicle market-price links.

Yad2's API is geo-blocked for non-Israeli servers, so this module uses
a static manufacturer mapping (IDs confirmed from real Yad2 URLs) and
always returns at least a year-filtered URL so the button is never hidden.

To add more manufacturer IDs: search for the car on yad2.co.il and copy
the manufacturer= value from the URL, then add it to _MAKES below.
"""

from __future__ import annotations

# Confirmed Yad2 manufacturer IDs (extracted from real yad2.co.il URLs)
_MAKES: dict[str, int] = {
    "קיה": 48,
}


def _normalize(name: str) -> str:
    return name.strip().replace("’", "'").replace("“", '"')


def _manufacturer_id(make: str) -> int | None:
    n = _normalize(make)
    if not n:
        return None
    if n in _MAKES:
        return _MAKES[n]
    for key, mid in _MAKES.items():
        if n in key or key in n:
            return mid
    return None


def _year_param(year_str: str) -> str:
    try:
        y = int(year_str)
        return f"year={y}-{y}"
    except (TypeError, ValueError):
        return ""


def build_url(record: dict) -> str:
    """
    Return a Yad2 search URL.
    Includes manufacturer filter when the make is in the known mapping.
    Always includes year filter when available.
    Never returns an empty string.
    """
    make = (record.get("tozeret_nm") or "").strip()
    year = (record.get("shnat_yitzur") or "").strip()

    base   = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []

    mid = _manufacturer_id(make)
    if mid:
        params.append(f"manufacturer={mid}")

    yr = _year_param(year)
    if yr:
        params.append(yr)

    return f"{base}?{'&'.join(params)}" if params else base
