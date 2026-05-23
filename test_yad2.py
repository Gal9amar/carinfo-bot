"""
Yad2 market price fetcher — נתוני שוק אמיתיים לפי יצרן/דגם/שנה
הרץ: python test_yad2.py
"""
import urllib.request
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from src.yad2 import _manufacturer_id, _model_id

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "he-IL,he;q=0.9",
    "Referer": "https://www.yad2.co.il/",
}


def fetch_page(manufacturer_id, model_id, year, page=1, rows=40):
    params = [f"manufacturer={manufacturer_id}"]
    if model_id:
        params.append(f"model={model_id}")
    if year:
        params.append(f"year={year}-{year}")
    params.append(f"page={page}&rows={rows}")
    url = f"https://gw.yad2.co.il/feed-search-legacy/vehicles/cars?{'&'.join(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_market_data(make: str, model: str, year: int):
    mid = _manufacturer_id(make)
    if not mid:
        print(f"❌ יצרן לא נמצא: {make}")
        return

    mod_id = _model_id(mid, model) if model else None

    print(f"\n🔍 מחפש: {make} {model} {year}")
    print(f"   Yad2 IDs: manufacturer={mid}, model={mod_id}, year={year}")
    print("   שולח בקשה...\n")

    try:
        data = fetch_page(mid, mod_id, year, rows=40)
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")
        return
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return

    items = data.get("data", {}).get("feed", {}).get("feed_items", [])
    total = data.get("data", {}).get("feed", {}).get("total_items", 0)
    cars  = [i for i in items if i.get("type") == "ad"]

    if not cars:
        print("⚠️  לא נמצאו מודעות")
        print("Raw keys:", list(data.get("data", {}).keys()))
        return

    # ── מחירים ─────────────────────────────────────────
    prices = [int(c["price"]) for c in cars if c.get("price") and str(c["price"]).isdigit()]
    kms    = [int(c["kilometers"]) for c in cars if c.get("kilometers") and str(c["kilometers"]).isdigit()]

    prices.sort()
    avg    = int(sum(prices) / len(prices)) if prices else 0
    median = prices[len(prices) // 2] if prices else 0

    print(f"{'='*45}")
    print(f"  {make} {model} {year}")
    print(f"{'='*45}")
    print(f"  📊 סה\"כ מודעות פעילות : {total}")
    print(f"  📋 בדף זה             : {len(cars)}")
    print(f"")
    print(f"  💰 מחיר מינימום       : ₪{min(prices):,}" if prices else "  💰 אין מחירים")
    print(f"  💰 מחיר מקסימום       : ₪{max(prices):,}" if prices else "")
    print(f"  💰 ממוצע              : ₪{avg:,}" if prices else "")
    print(f"  💰 חציון              : ₪{median:,}" if prices else "")
    print(f"")
    if kms:
        avg_km = int(sum(kms) / len(kms))
        print(f"  🛞 ק\"מ ממוצע          : {avg_km:,}")
    print(f"{'='*45}")

    # ── פירוט מודעות ────────────────────────────────────
    print(f"\n  {'מחיר':<12} {'ק\"מ':<10} {'עיר':<14} {'יד':<5} {'תיאור'}")
    print(f"  {'-'*60}")
    for c in cars[:10]:
        price = f"₪{int(c['price']):,}" if c.get("price") else "—"
        km    = f"{int(c['kilometers']):,}" if c.get("kilometers") else "—"
        city  = (c.get("city") or "")[:12]
        hand  = str(c.get("hand", ""))
        title = (c.get("title") or c.get("subtitle") or "")[:30]
        print(f"  {price:<12} {km:<10} {city:<14} {hand:<5} {title}")

    return {
        "total": total,
        "count": len(prices),
        "min": min(prices) if prices else None,
        "max": max(prices) if prices else None,
        "avg": avg,
        "median": median,
        "avg_km": int(sum(kms)/len(kms)) if kms else None,
    }


if __name__ == "__main__":
    # ── בדיקות ──────────────────────────────────────────
    tests = [
        ("טויוטה", "קורולה קרוס", 2023),
        ("קיה",    "ספורטאז",     2022),
        ("יונדאי", "טוסון",       2021),
    ]

    for make, model, year in tests:
        get_market_data(make, model, year)
        print()
