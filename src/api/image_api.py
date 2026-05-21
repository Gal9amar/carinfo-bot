"""
Car image lookup.
Strategy:
  1. Wikimedia Commons API (with proper User-Agent)
  2. Wikipedia REST API page summary thumbnail (fallback)
  3. Wikipedia search → first article thumbnail (last resort)
"""

import httpx
import re
from typing import Optional

_UA = "CarInfoBot/1.0 (vehicle-report-bot; https://t.me/israelcarinfobot)"

COLOR_MAP = {
    "לבן": "white", "שחור": "black", "אפור": "gray", "כסוף": "silver",
    "אדום": "red", "כחול": "blue", "ירוק": "green", "צהוב": "yellow",
    "כתום": "orange", "חום": "brown", "בז'": "beige", "זהב": "gold",
    "סגול": "purple", "ורוד": "pink", "תכלת": "light blue",
    "בורדו": "burgundy", "חאקי": "khaki",
}

MFR_MAP = {
    "טויוטה": "Toyota", "יונדאי": "Hyundai", "קיה": "Kia", "מזדה": "Mazda",
    "סוזוקי": "Suzuki", "ניסן": "Nissan", "מיצובישי": "Mitsubishi",
    "הונדה": "Honda", "סובארו": "Subaru", "מרצדס": "Mercedes-Benz",
    "ב.מ.וו": "BMW", "אאודי": "Audi", "פולקסווגן": "Volkswagen",
    "סקודה": "Skoda", "סיאט": "SEAT", "פיג'ו": "Peugeot",
    "רנו": "Renault", "סיטרואן": "Citroen", "פורד": "Ford",
    "אופל": "Opel", "שברולט": "Chevrolet", "ג'יפ": "Jeep",
    "וולוו": "Volvo", "פיאט": "Fiat", "אלפא רומאו": "Alfa Romeo",
    "לקסוס": "Lexus", "אינפיניטי": "Infiniti", "לנד רובר": "Land Rover",
    "יגואר": "Jaguar", "פורשה": "Porsche", "טסלה": "Tesla",
    "בי.וואי.די": "BYD", "גילי": "Geely", "מג'": "MG",
    "דאצ'יה": "Dacia", "סאנגיונג": "SsangYong", "מיני": "MINI",
    "סיאיק": "SAIC", "חאוול": "Haval", "אומדה": "Omoda",
}

# Wikipedia article title overrides for models that need exact titles
_WIKI_TITLE_MAP = {
    "Toyota Corolla Cross": "Toyota_Corolla_Cross",
    "Toyota Yaris": "Toyota_Yaris",
    "Toyota RAV4": "Toyota_RAV4",
    "Toyota C-HR": "Toyota_C-HR",
    "Toyota Camry": "Toyota_Camry",
    "Toyota Hilux": "Toyota_Hilux",
    "Hyundai Tucson": "Hyundai_Tucson",
    "Hyundai i10": "Hyundai_i10",
    "Hyundai i20": "Hyundai_i20",
    "Hyundai i30": "Hyundai_i30",
    "Kia Sportage": "Kia_Sportage",
    "Kia Picanto": "Kia_Picanto",
    "Kia Stonic": "Kia_Stonic",
    "Mazda CX-5": "Mazda_CX-5",
    "Mazda3": "Mazda3",
    "Skoda Octavia": "Škoda_Octavia",
    "Skoda Karoq": "Škoda_Karoq",
    "BMW 3 Series": "BMW_3_Series",
    "Mercedes-Benz A-Class": "Mercedes-Benz_A-Class",
    "Volkswagen Golf": "Volkswagen_Golf",
    "Volkswagen Polo": "Volkswagen_Polo",
    "Ford Focus": "Ford_Focus",
    "Nissan Qashqai": "Nissan_Qashqai",
    "Mitsubishi Outlander": "Mitsubishi_Outlander",
    "Tesla Model 3": "Tesla_Model_3",
    "Tesla Model Y": "Tesla_Model_Y",
}


def _translate(text: str, mapping: dict) -> str:
    return mapping.get(text.strip(), text.strip())


def _build_query(manufacturer: str, model: str, year: str) -> str:
    mfr_en = _translate(manufacturer, MFR_MAP)
    parts = [p for p in [mfr_en, model] if p]
    return " ".join(parts).strip()


def _wiki_title(mfr_en: str, model: str) -> str:
    """Return a Wikipedia article title to try directly."""
    key = f"{mfr_en} {model}".strip()
    if key in _WIKI_TITLE_MAP:
        return _WIKI_TITLE_MAP[key]
    # Generic: "Toyota_Corolla_Cross"
    return key.replace(" ", "_")


async def _wikimedia_commons(query: str) -> Optional[str]:
    """Wikimedia Commons search — requires User-Agent to avoid 403."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": f"{query} car",
        "gsrlimit": "8",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": "960",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=12, headers={"User-Agent": _UA}) as client:
            resp = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            mime = info.get("mime", "")
            img_url = info.get("thumburl") or info.get("url", "")
            if mime == "image/jpeg" and img_url:
                return img_url
    except Exception:
        pass
    return None


async def _wikipedia_summary(title: str) -> Optional[str]:
    """Wikipedia REST summary endpoint — returns page thumbnail."""
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": _UA}) as client:
            resp = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                follow_redirects=True,
            )
            if resp.status_code == 200:
                thumb = resp.json().get("thumbnail", {})
                src = thumb.get("source", "")
                # Prefer larger image: replace /320px- with /800px-
                if src:
                    src = re.sub(r"/\d+px-", "/800px-", src)
                    return src
    except Exception:
        pass
    return None


async def _wikipedia_search(query: str) -> Optional[str]:
    """Wikipedia search → fetch summary of first result → thumbnail."""
    try:
        async with httpx.AsyncClient(timeout=12, headers={"User-Agent": _UA}) as client:
            r = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "opensearch", "search": query, "limit": "3", "format": "json"},
            )
            data = r.json()
            titles = data[1] if len(data) > 1 else []
            for title in titles:
                slug = title.replace(" ", "_")
                img = await _wikipedia_summary(slug)
                if img:
                    return img
    except Exception:
        pass
    return None


async def fetch_car_image(manufacturer: str, model: str, year: str, color: str) -> Optional[str]:
    """Returns a direct image URL or None."""
    mfr_en = _translate(manufacturer, MFR_MAP)
    query  = _build_query(manufacturer, model, year)
    if not query:
        return None

    # 1. Wikimedia Commons (JPEG photos, reliable)
    img = await _wikimedia_commons(query)
    if img:
        return img

    # 2. Wikipedia direct article summary (known titles)
    title = _wiki_title(mfr_en, model)
    img = await _wikipedia_summary(title)
    if img:
        return img

    # 3. Wikipedia search fallback
    img = await _wikipedia_search(f"{mfr_en} {model} car")
    return img
