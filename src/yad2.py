"""
Yad2 URL builder for vehicle market-price links.

Yad2's API is geo-blocked for non-Israeli servers, so this module uses
a static manufacturer mapping (IDs confirmed from real Yad2 URLs) and
always returns at least a year-filtered URL so the button is never hidden.

To add more manufacturer IDs: search for the car on yad2.co.il and copy
the manufacturer= value from the URL, then add it to _MAKES below.
"""

from __future__ import annotations

# Confirmed Yad2 manufacturer IDs (extracted from real yad2.co.il /vehicles/cars?manufacturer= URLs)
# Each entry verified by checking the Hebrew page title returned for that manufacturer= value.
_MAKES: dict[str, int] = {
    "אאודי": 1,       # Audi
    "אופל": 2,        # Opel
    "ב מ וו": 7,      # BMW (also written ב.מ.וו)
    "ג'יפ": 10,       # Jeep
    "דאצ'יה": 12,     # Dacia
    "הונדה": 17,      # Honda
    "וולוו": 18,      # Volvo
    "טויוטה": 19,     # Toyota
    "יונדאי": 21,     # Hyundai
    "לנד רובר": 24,   # Land Rover
    "לקסוס": 26,      # Lexus
    "מאזדה": 27,      # Mazda
    "מיני": 29,       # Mini
    "מיצובישי": 30,   # Mitsubishi
    "מרצדס-בנץ": 31,  # Mercedes-Benz
    "ניסאן": 32,      # Nissan
    "סאנגיונג": 34,   # SsangYong
    "סובארו": 35,     # Subaru
    "סוזוקי": 36,     # Suzuki
    "סיאט": 37,       # SEAT
    "סיטרואן": 38,    # Citroën
    "סקודה": 40,      # Škoda
    "פולקסווגן": 41,  # Volkswagen
    "פורד": 43,       # Ford
    "פיאט": 45,       # Fiat
    "פיג'ו": 46,      # Peugeot
    "קיה": 48,        # Kia
    "רנו": 51,        # Renault
    "שברולט": 52,     # Chevrolet
    "טסלה": 62,       # Tesla
}


def _normalize(name: str) -> str:
    """Collapse dots/hyphens to spaces and normalise apostrophes so govt-API
    spellings (e.g. 'ב.מ.וו', 'מרצדס בנץ') match Yad2 keys."""
    import re
    s = name.strip()
    for src, dst in [("'", "'"), ("׳", "'"), ("-", " "), (".", " ")]:
        s = s.replace(src, dst)
    return re.sub(r"\s+", " ", s).strip()


# Normalised lookup built once at import time
_NORM: dict[str, int] = {_normalize(k): v for k, v in _MAKES.items()}

# Extra aliases: govt-API spellings that differ from Yad2's Hebrew names
_ALIASES: dict[str, int] = {
    "מזדה":       27,   # govt returns מזדה, Yad2 page says מאזדה
    "מרצדס בנץ":  31,   # govt uses space; Yad2 key normalises hyphen → same
}
_NORM.update({_normalize(k): v for k, v in _ALIASES.items()})


def _manufacturer_id(make: str) -> int | None:
    n = _normalize(make)
    if not n:
        return None
    if n in _NORM:
        return _NORM[n]
    for key, mid in _NORM.items():
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
