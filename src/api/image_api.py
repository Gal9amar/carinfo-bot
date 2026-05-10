"""
Car image lookup.
Strategy:
  1. Wikimedia Commons API – searches for manufacturer + model + year image
  2. DuckDuckGo image search (fallback, may break)
"""

import httpx
import re
from typing import Optional

COLOR_MAP = {
    "לבן": "white", "שחור": "black", "אפור": "gray", "כסוף": "silver",
    "אדום": "red", "כחול": "blue", "ירוק": "green", "צהוב": "yellow",
    "כתום": "orange", "חום": "brown", "בז'": "beige", "זהב": "gold",
    "סגול": "purple", "ורוד": "pink", "תכלת": "light blue",
    "בורדו": "burgundy", "חאקי": "khaki",
}

# Translate common Hebrew manufacturer names to English for better search
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
}


def _translate(text: str, mapping: dict) -> str:
    return mapping.get(text.strip(), text.strip())


def _build_query(manufacturer: str, model: str, year: str) -> str:
    mfr_en = _translate(manufacturer, MFR_MAP)
    parts = [mfr_en, model, year]
    return " ".join(p for p in parts if p).strip()


async def _wikimedia_image(query: str) -> Optional[str]:
    """Search Wikimedia Commons for a car image."""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrnamespace": "6",  # File namespace
        "gsrsearch": f"{query} car",
        "gsrlimit": "5",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": "800",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])[0]
            mime = info.get("mime", "")
            img_url = info.get("thumburl") or info.get("url", "")
            # Only return actual photos (not SVG/PNG icons)
            if mime in ("image/jpeg", "image/png") and img_url:
                return img_url
    except Exception:
        pass
    return None


async def _ddg_image(query: str) -> Optional[str]:
    """DuckDuckGo image search fallback."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
    }
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
            resp = await client.get("https://duckduckgo.com/", params={"q": query})
            # Try multiple vqd patterns
            vqd = None
            for pattern in [r'vqd="([\d-]+)"', r"vqd=([\d-]+)[&'\"]", r'"vqd"\s*:\s*"([\d-]+)"']:
                m = re.search(pattern, resp.text)
                if m:
                    vqd = m.group(1)
                    break
            if not vqd:
                return None

            resp2 = await client.get("https://duckduckgo.com/i.js", params={
                "q": query, "o": "json", "vqd": vqd, "f": ",,,,,", "p": "1",
            })
            results = resp2.json().get("results", [])
            if results:
                return results[0].get("image")
    except Exception:
        pass
    return None


async def fetch_car_image(manufacturer: str, model: str, year: str, color: str) -> Optional[str]:
    """Returns a direct image URL or None. Tries Wikimedia first, then DDG."""
    query = _build_query(manufacturer, model, year)
    if not query:
        return None

    # Try Wikimedia first (reliable, no scraping)
    img = await _wikimedia_image(query)
    if img:
        return img

    # Fallback to DDG
    img = await _ddg_image(query)
    return img
