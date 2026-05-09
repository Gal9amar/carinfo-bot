"""
Car image lookup via DuckDuckGo image search (unofficial endpoint).
Builds a query from manufacturer + model + year + color and returns the first image URL.
"""

import httpx
import re
from typing import Optional

DDG_URL = "https://duckduckgo.com/"
DDG_IMG_URL = "https://duckduckgo.com/i.js"

# Map Hebrew colors to English for better search results
COLOR_MAP = {
    "לבן": "white", "שחור": "black", "אפור": "gray", "כסוף": "silver",
    "אדום": "red", "כחול": "blue", "ירוק": "green", "צהוב": "yellow",
    "כתום": "orange", "חום": "brown", "בז'": "beige", "זהב": "gold",
    "סגול": "purple", "ורוד": "pink", "תכלת": "light blue",
    "בורדו": "burgundy", "חאקי": "khaki",
}


def _translate_color(color_he: str) -> str:
    for heb, eng in COLOR_MAP.items():
        if heb in color_he:
            return eng
    return ""


def _build_query(manufacturer: str, model: str, year: str, color_he: str) -> str:
    color_en = _translate_color(color_he)
    parts = [manufacturer, model, year, color_en]
    return " ".join(p for p in parts if p).strip()


async def fetch_car_image(manufacturer: str, model: str, year: str, color: str) -> Optional[str]:
    """
    Returns a direct image URL or None if not found.
    Uses DuckDuckGo's unofficial image search endpoint.
    """
    query = _build_query(manufacturer, model, year, color)
    if not query:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Referer": "https://duckduckgo.com/",
    }

    try:
        async with httpx.AsyncClient(timeout=10, headers=headers, follow_redirects=True) as client:
            # Step 1: get vqd token
            resp = await client.get(DDG_URL, params={"q": query})
            vqd_match = re.search(r'vqd=([\d-]+)', resp.text)
            if not vqd_match:
                return None
            vqd = vqd_match.group(1)

            # Step 2: image search
            resp2 = await client.get(DDG_IMG_URL, params={
                "q": query,
                "o": "json",
                "vqd": vqd,
                "f": ",,,,,",
                "p": "1",
            })
            data = resp2.json()
            results = data.get("results", [])
            if not results:
                return None

            # Return first image URL
            return results[0].get("image")

    except Exception:
        return None
