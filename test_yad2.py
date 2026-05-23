"""
בדיקה פשוטה: האם אפשר לגשת ל-Yad2 ולקבל מחירים?
הרץ: python test_yad2.py
"""
import urllib.request
import json

# חיפוש לדוגמה: טויוטה קורולה 2022
URL = "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars?manufacturer=19&model=51&year=2022-2022&page=1&rows=5"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "he-IL,he;q=0.9",
    "Referer": "https://www.yad2.co.il/",
}

print(f"שולח בקשה ל-Yad2...")
print(f"URL: {URL}\n")

try:
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        status = resp.status
        body = resp.read().decode("utf-8")
        data = json.loads(body)

        print(f"✅ סטטוס: {status}")

        items = data.get("data", {}).get("feed", {}).get("feed_items", [])
        cars = [i for i in items if i.get("type") == "ad"]

        print(f"✅ מודעות שנמצאו: {len(cars)}")

        if cars:
            print("\n--- 3 מודעות ראשונות ---")
            for car in cars[:3]:
                price = car.get("price", "?")
                year  = car.get("year", "?")
                km    = car.get("kilometers", "?")
                city  = car.get("city", "?")
                print(f"  ₪{price:,} | {year} | {km:,} ק\"מ | {city}")
        else:
            print("\nתשובה מ-Yad2 (raw):")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500])

except urllib.error.HTTPError as e:
    print(f"❌ HTTP Error: {e.code} {e.reason}")
    print(f"תוכן: {e.read().decode()[:300]}")
except urllib.error.URLError as e:
    print(f"❌ חסום / אין גישה: {e.reason}")
except Exception as e:
    print(f"❌ שגיאה: {e}")
