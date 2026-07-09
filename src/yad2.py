""" 
Yad2 URL builder for vehicle market-price links.

Yad2's API is geo-blocked for non-Israeli servers, so this module uses
static mappings (IDs from yad2_models.json, confirmed from real Yad2 URLs)
and always returns at least a year-filtered URL so the button is never hidden.
"""

from __future__ import annotations
import json
import os
import re

# ── Manufacturer mapping ─────────────────────────────────────────────────────
# Confirmed Yad2 manufacturer IDs (from yoelzeitoun/car-scrapper yad2_mapping.json)
_MAKES: dict[str, int] = {
    "אאודי": 1,           # Audi
    "אופל": 2,            # Opel
    "אינפיניטי": 3,       # Infiniti
    "איסוזו": 4,          # Isuzu
    "אלפא רומיאו": 5,     # Alfa Romeo
    "אם ג'י": 6,          # MG
    "ב מ וו": 7,          # BMW
    "ג'יפ": 10,           # Jeep
    "גרייט וול": 11,      # Great Wall
    "דאצ'יה": 12,         # Dacia
    "הונדה": 17,          # Honda
    "וולוו": 18,          # Volvo
    "טויוטה": 19,         # Toyota
    "יגואר": 20,          # Jaguar
    "יונדאי": 21,         # Hyundai
    "לנד רובר": 24,       # Land Rover
    "לקסוס": 26,          # Lexus
    "מאזדה": 27,          # Mazda
    "מיני": 29,           # Mini
    "מיצובישי": 30,       # Mitsubishi
    "מרצדס-בנץ": 31,      # Mercedes-Benz
    "ניסאן": 32,          # Nissan
    "סאנגיונג": 34,       # SsangYong
    "סובארו": 35,         # Subaru
    "סוזוקי": 36,         # Suzuki
    "סיאט": 37,           # SEAT
    "סיטרואן": 38,        # Citroën
    "סמארט": 39,          # Smart
    "סקודה": 40,          # Škoda
    "פולקסווגן": 41,      # Volkswagen
    "פורד": 43,           # Ford
    "פורשה": 44,          # Porsche
    "פיאט": 45,           # Fiat
    "פיג'ו": 46,          # Peugeot
    "קיה": 48,            # Kia
    "רנו": 51,            # Renault
    "שברולט": 52,         # Chevrolet
    "טסלה": 62,           # Tesla
    "לאדה": 80,           # Lada
    "דונגפנג": 88,        # Dongfeng
    "מקסוס": 89,          # Maxus
    "ראם": 91,            # Ram
    "קופרה": 92,          # Cupra
    "ג'נסיס": 93,         # Genesis
    "בי.ווי.די": 141,     # BYD
    "ניאו": 289,          # NIO
}

# Sanity check: Ensure Kia != Renault
assert _MAKES["קיה"] == 48, f"Expected Kia (קיה)=48, got {_MAKES.get('קיה')}"
assert _MAKES["רנו"] == 51, f"Expected Renault (רנו)=51, got {_MAKES.get('רנו')}"

_ALIASES: dict[str, int] = {
    "מזדה":        27,   # govt: מזדה, Yad2: מאזדה
    "מרצדס בנץ":   31,   # govt: space, Yad2: hyphen
    "יונדאי":      21,   # alt spelling
    "סיט":         37,   # alt for סיאט
    "מג":           6,   # alt for MG
    "ב י ד":       141,  # alt for BYD
    # Renault variants - handle govt API quirks
    "רנו ": 51,         # trailing space
    "רנו.": 51,         # trailing period  
    "ריניה": 51,        # typo/OCR variant
}


def _normalize(name: str) -> str:
    s = str(name).strip().lower()   # lowercase for case-insensitive Latin matching
    for src, dst in [("'", "'"), ("׳", "'"), ("-", " "), (".", " ")]:
        s = s.replace(src, dst)
    return re.sub(r"\s+", " ", s).strip()


def _norm_model(name: str) -> str:
    """Aggressively normalize model name: lowercase + remove apostrophes."""
    s = _normalize(name)
    s = re.sub(r"['׳]", "", s)   # strip apostrophes / Hebrew geresh
    return re.sub(r"\s+", " ", s).strip()


_NORM: dict[str, int] = {_normalize(k): v for k, v in _MAKES.items()}
_NORM.update({_normalize(k): v for k, v in _ALIASES.items()})

# Debug: log the normalized mapping
import logging as _logging
_logger = _logging.getLogger(__name__)
_logger.debug(f"Yad2 _NORM mapping ({len(_NORM)} entries): {list(_NORM.items())[:5]}...")


def _manufacturer_id(make: str) -> int | None:
    """
    Lookup manufacturer ID. Handles:
    - Exact matches (e.g., "קיה" -> 48)
    - Normalized matches (handles spaces, periods, hyphens)
    - Substring fallback (but prefer exact over substring)
    - Returns None if no match found
    """
    n = _normalize(make)
    _logger.debug(f"_manufacturer_id: input='{make}' (repr={repr(make)}) normalized='{n}'")
    
    if not n:
        _logger.debug(f"_manufacturer_id: empty normalized name")
        return None
    
    # Exact match: "קיה" -> 48
    if n in _NORM:
        result = _NORM[n]
        _logger.debug(f"_manufacturer_id: exact match found '{n}' -> {result}")
        return result
    
    # Substring match as fallback (be careful of ambiguity)
    # Sort by length desc to prefer longer/more specific matches
    best_matches = []
    for key, mid in _NORM.items():
        if n in key or key in n:
            best_matches.append((len(key), key, mid))
    
    if best_matches:
        best_matches.sort(reverse=True)  # Longest key first
        len_key, key, mid = best_matches[0]
        _logger.info(f"_manufacturer_id: substring match for '{n}' found '{key}' -> {mid} (len={len_key})")
        return mid
    
    _logger.debug(f"_manufacturer_id: no match found for '{n}' (input: '{make}')")
    return None


# ── Model mapping ────────────────────────────────────────────────────────────
# Loaded once from yad2_models.json: {manufacturer_id: {normalized_model: model_id}}
_MODEL_LOOKUP: dict[int, dict[str, int]] = {}

def _load_models() -> None:
    path = os.path.join(os.path.dirname(__file__), "yad2_models.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for mfr_id_str, mfr in data.get("manufacturers", {}).items():
            mfr_id = int(mfr_id_str)
            _MODEL_LOOKUP[mfr_id] = {}
            for model in mfr.get("models", {}).values():
                model_id = int(model["id"])
                for field in ("name_he", "name_en"):
                    n = model.get(field, "")
                    if n:
                        _MODEL_LOOKUP[mfr_id][_normalize(n)]    = model_id
                        _MODEL_LOOKUP[mfr_id][_norm_model(n)]   = model_id
    except Exception:
        pass

_load_models()


def _model_id(manufacturer_id: int, model_name: str) -> int | None:
    models = _MODEL_LOOKUP.get(manufacturer_id, {})
    if not models or not model_name:
        return None
    # Pass 1: exact / substring on both normalisation variants
    for norm_fn in (_normalize, _norm_model):
        n = norm_fn(model_name)
        if not n:
            continue
        if n in models:
            return models[n]
        for key, mid in models.items():
            if n in key or key in n:
                return mid
    # Pass 2: prefix match — first 5 chars (handles ספורטאז' vs ספורטז' etc.)
    n5 = _norm_model(model_name)
    if len(n5) >= 4:
        prefix = n5[:5]
        best: tuple[int, int] | None = None  # (len_diff, model_id)
        for key, mid in models.items():
            if key.startswith(prefix) or n5.startswith(key[:5] if len(key) >= 5 else key):
                diff = abs(len(key) - len(n5))
                if diff <= 3 and (best is None or diff < best[0]):
                    best = (diff, mid)
        if best:
            return best[1]
    return None


# ── URL builder ──────────────────────────────────────────────────────────────

def _year_param(year_str: str) -> str:
    try:
        y = int(year_str)
        return f"year={y}-{y}"
    except (TypeError, ValueError):
        return ""


_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.yad2.co.il/vehicles/cars",
    "Origin": "https://www.yad2.co.il",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

_LOOKALIKE_BASE = "https://gw.yad2.co.il/lookalike/vehicles/cars"
_ORACLE_PROXY  = os.environ.get("YAD2_PROXY_URL", "http://151.145.86.13:8080/yad2")
_CF_WORKER_URL = os.environ.get("YAD2_CF_WORKER_URL", "")


def get_market_price(make: str, model: str, year: int | str) -> dict | None:
    """
    Fetch live market price data from Yad2 for a given make/model/year.

    Returns a dict with keys: total, count, min, max, avg, median, avg_km, items
    Returns None if no data found or on error.

    Set YAD2_PROXY env var to route through a proxy:
      YAD2_PROXY=http://user:pass@host:port
    """
    import urllib.request
    import zlib

    mid = _manufacturer_id(make)
    if not mid:
        _logger.warning(f"get_market_price: unknown make '{make}'")
        return None

    mod_id = _model_id(mid, model) if model else None
    if not mod_id:
        _logger.warning(f"get_market_price: unknown model '{model}' for '{make}'")
        return None

    url = f"{_LOOKALIKE_BASE}?model={mod_id}"
    try:
        y = int(year)
        url += f"&year={y}-{y}"
    except (TypeError, ValueError):
        y = None

    # Build Oracle proxy URL (Israeli IP, bypasses Yad2 geo-block)
    proxy_secret = os.environ.get("YAD2_PROXY_SECRET", "carinfo2026")

    def _fetch(extra_params: str, include_year: bool = True) -> list:
        url = f"{_ORACLE_PROXY}?manufacturer={mid}{extra_params}&rows=100"
        if y and include_year:
            url += f"&year={y}-{y}"
        url += f"&secret={proxy_secret}"
        _logger.info(f"get_market_price: {url}")
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = json.loads(zlib.decompress(raw, 16 + zlib.MAX_WBITS).decode("utf-8"))
        return data.get("data") or []

    try:
        all_items = _fetch(f"&model={mod_id}")
    except Exception as e:
        _logger.error(f"get_market_price fetch error: {e}")
        return None

    # If too few results, retry with a broader year window (model stays required by the proxy)
    if len(all_items) <= 3:
        _logger.info(f"get_market_price: few results ({len(all_items)}), retrying without year filter")
        try:
            broader = _fetch(f"&model={mod_id}", include_year=False)
            if len(broader) > len(all_items):
                all_items = broader
        except Exception as e:
            _logger.warning(f"get_market_price broader fetch failed, keeping initial results: {e}")
    if y:
        filtered = [
            c for c in all_items
            if int(c.get("vehicleDates", {}).get("yearOfProduction") or 0) == y
        ]
        items = filtered if filtered else all_items
    else:
        items = all_items

    if not items:
        return None

    prices = sorted([int(c["price"]) for c in items if c.get("price")])
    kms    = [int(c["km"]) for c in items if c.get("km")]

    return {
        "total":   len(all_items),
        "count":   len(prices),
        "min":     min(prices) if prices else None,
        "max":     max(prices) if prices else None,
        "avg":     int(sum(prices) / len(prices)) if prices else None,
        "median":  prices[len(prices) // 2] if prices else None,
        "avg_km":  int(sum(kms) / len(kms)) if kms else None,
        "items":   items,
    }


def build_url(record: dict) -> str:
    """Return a Yad2 search URL with manufacturer, model, and year when available."""
    wltp  = record.get("_wltp") or {}
    make  = str(record.get("tozeret_nm") or "").strip()
    model = str(
        record.get("kinuy_mishari") or wltp.get("kinuy_mishari") or
        record.get("degem_nm")      or wltp.get("degem_nm")      or ""
    ).strip()
    year  = str(record.get("shnat_yitzur") or "").strip()

    base   = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []

    mid = _manufacturer_id(make)
    if mid:
        params.append(f"manufacturer={mid}")
        mod_id = _model_id(mid, model)
        if mod_id:
            params.append(f"model={mod_id}")
        _logger.info(f"Yad2 URL: make='{make}' (id={mid}), model='{model}' (id={mod_id}), year={year}")

    yr = _year_param(year)
    if yr:
        params.append(yr)

    url = f"{base}?{'&'.join(params)}" if params else base
    _logger.debug(f"build_url returning: {url}")
    return url


def build_search_url(make: str, model: str, year: int | str | None) -> str:
    """Return a Yad2 search URL filtered by make/model/year."""
    base = "https://www.yad2.co.il/vehicles/cars"
    params: list[str] = []
    mid = _manufacturer_id(make)
    if mid:
        params.append(f"manufacturer={mid}")
        mod_id = _model_id(mid, model) if model else None
        if mod_id:
            params.append(f"model={mod_id}")
    yr = _year_param(str(year)) if year else ""
    if yr:
        params.append(yr)
    return f"{base}?{'&'.join(params)}" if params else base


def fetch_listings(make: str, model: str, year: int | str | None) -> list[dict]:
    """
    Fetch current Yad2 listings for given make/model/year.

    Uses the Cloudflare Worker (type=feed) when YAD2_CF_WORKER_URL is set —
    this calls the full search/feed endpoint and returns all listings.
    Falls back to the Oracle proxy (lookalike/market-price sample) otherwise.

    Returns list of dicts: {id, price, km, year, city}
    """
    import urllib.request
    import zlib

    mid = _manufacturer_id(make)
    if not mid:
        _logger.warning(f"fetch_listings: unknown make '{make}'")
        return []

    mod_id = _model_id(mid, model) if model else None

    try:
        y = int(year) if year else None
    except (TypeError, ValueError):
        y = None

    def _parse_response(raw: bytes) -> list:
        import zlib as _zlib
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            data = json.loads(_zlib.decompress(raw, 16 + _zlib.MAX_WBITS).decode("utf-8"))
        data_val = data.get("data") if isinstance(data, dict) else None
        _logger.info(f"fetch_listings response: top_keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__} data_type={type(data_val).__name__} data={list(data_val.keys()) if isinstance(data_val, dict) else (len(data_val) if isinstance(data_val, list) else data_val)}")
        if isinstance(data_val, list):
            return data_val
        if isinstance(data_val, dict):
            for key in ("feed_items", "items", "feed"):
                candidate = data_val.get(key)
                if isinstance(candidate, list) and candidate:
                    _logger.info(f"fetch_listings: found items under data.{key} ({len(candidate)})")
                    return candidate
        return []

    def _fetch_oracle(model_param: str) -> list:
        proxy_secret = os.environ.get("YAD2_PROXY_SECRET", "carinfo2026")
        url = f"{_ORACLE_PROXY}?manufacturer={mid}{model_param}&rows=100&type=feed"
        if y:
            url += f"&year={y}-{y}"
        url += f"&secret={proxy_secret}"
        _logger.info(f"fetch_listings (oracle/feed): {url}")
        import urllib.request as _ur
        with _ur.urlopen(_ur.Request(url), timeout=15) as resp:
            return _parse_response(resp.read())

    def _do_fetch(model_param: str) -> list:
        if _CF_WORKER_URL:
            url = f"{_CF_WORKER_URL}?type=feed&manufacturer={mid}{model_param}&rows=100"
            if y:
                url += f"&year={y}-{y}"
            _logger.info(f"fetch_listings (cf): {url}")
            import urllib.request as _ur
            import urllib.error as _ue
            try:
                with _ur.urlopen(_ur.Request(url), timeout=15) as resp:
                    items = _parse_response(resp.read())
                if items:
                    return items
                _logger.warning("fetch_listings: CF Worker returned empty, falling back to oracle")
            except _ue.HTTPError as e:
                _logger.warning(f"fetch_listings: CF Worker {e.code}, falling back to oracle")
            except Exception as e:
                _logger.warning(f"fetch_listings: CF Worker error ({e}), falling back to oracle")
        return _fetch_oracle(model_param)

    try:
        items = _do_fetch(f"&model={mod_id}") if mod_id else _do_fetch("")
        if mod_id and len(items) <= 2:
            broader = _do_fetch("") or items
            # Keep only items whose year matches when a year was requested
            if y and broader:
                broader_filtered = [
                    c for c in broader
                    if int(c.get("vehicleDates", {}).get("yearOfProduction") or 0) == y
                ]
                broader = broader_filtered if broader_filtered else broader
            items = broader
    except Exception as e:
        _logger.error(f"fetch_listings error: {e}")
        return []

    # Filter by year — the proxy does not always honour the year= param reliably.
    if y and items:
        year_filtered = [
            c for c in items
            if int(c.get("vehicleDates", {}).get("yearOfProduction") or 0) == y
        ]
        if year_filtered:
            items = year_filtered

    result = []
    seen_ids: set[str] = set()
    has_tokens = False
    for item in items:
        token = str(item.get("token") or "")
        oid = str(item.get("orderId") or token or item.get("id") or "")
        if not oid or oid in seen_ids:
            continue
        seen_ids.add(oid)
        if token:
            has_tokens = True
        link = f"https://www.yad2.co.il/item/{token}" if token else ""
        result.append({
            "id": oid,
            "price": item.get("price"),
            "km": item.get("km"),
            "year": item.get("vehicleDates", {}).get("yearOfProduction"),
            "city": item.get("city") or "",
            "link": link,
        })
    _logger.info(f"fetch_listings: {len(result)} results, has_tokens={has_tokens}")
    return result