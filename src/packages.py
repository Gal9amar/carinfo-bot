"""
Package pricing — stored in DB, cached in memory.
Default packages are seeded on first init_packages() call.
"""

import asyncio
import json
from src.db import execute

_DEFAULT_PACKAGES = [
    (1, "🔍 50 חיפושים",   50,  10, "", 1, 1),
    (2, "🔍 100 חיפושים", 100,  20, "", 2, 1),
    (3, "🔍 200 חיפושים", 200,  30, "", 3, 1),
    (4, "♾️ מנוי חודשי",   -1,  25, "", 4, 1),
]

def _f(text: str, included: bool = True) -> dict:
    return {"text": text, "included": included}


# Feature lists shown on the plan cards. Keep in sync with the fallbacks in
# webapp/src/pages/PackagesPage.jsx and DEFAULT_PKG_FEATURES in AdminPage.jsx.
_DEFAULT_FREE_FEATURES = [
    _f("נתוני רכב בסיסיים — שנה, דגם, בעלות, טסט, ק״מ"),
    _f("היסטוריית חיפושים אישית"),
    _f("השוואת רכבים — חיפוש אחד לכל השוואה"),
    _f("תזכורת טסט וניהול ״רכבים שקניתי״"),
    _f("חיפושים ללא הגבלה", False),
    _f("מחיר שוק Yad2", False),
    _f("התראות על מודעות חדשות ב-Yad2", False),
    _f("הורדת דוח PDF מפורט", False),
]

_DEFAULT_PREMIUM_FEATURES = [
    _f("חיפושים ללא הגבלה למשך חודש"),
    _f("מחיר שוק Yad2 — השוואת מחירים עדכנית"),
    _f("התראות על מודעות חדשות ב-Yad2"),
    _f("הורדת דוח PDF מפורט"),
    _f("השוואת רכבים ללא עלות חיפוש נוספת"),
    _f("נתוני רכב מלאים, היסטוריית חיפושים, תזכורת טסט ו״רכבים שקניתי״"),
    _f("גישה לכל פיצ׳רי הפרימיום הקיימים והעתידיים"),
]

# Wording of the previous defaults: a stored list made only of these lines was never customised
# by the admin and is upgraded automatically (see _upgrade_default_features).
_LEGACY_FEATURE_TEXTS = {
    "נתוני רכב בסיסיים — שנה, דגם, בעלות, טסט, ק״מ", "היסטוריית חיפושים אישית", "מחיר שוק Yad2",
    "הורדת דוח PDF מפורט", "העתקת דוח לשיתוף", "הערות אישיות לכל רכב",
    "נתוני רכב מלאים — שנה, דגם, בעלות, טסט, ק״מ", "מחיר שוק Yad2 — השוואת מחירים עדכנית",
    "הערות אישיות לכל רכב — נשמרות ומופיעות בדוח", "גישה לכל תכונות המנוי הקיימות והעתידיות",
}

_cache: list[tuple] | None = None  # (id, label, searches, price, image_url, display_order, duration_months, features, chips, package_type, is_active)


async def init_packages() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id              INTEGER PRIMARY KEY,
            label           TEXT    NOT NULL,
            searches        INTEGER NOT NULL,
            price           INTEGER NOT NULL,
            image_url       TEXT    DEFAULT '',
            display_order   INTEGER DEFAULT 0,
            duration_months INTEGER DEFAULT 1
        )
    """)
    # Migrations: add columns if missing
    for migration in [
        "ALTER TABLE packages ADD COLUMN duration_months INTEGER DEFAULT 1",
        "ALTER TABLE packages ADD COLUMN features TEXT DEFAULT '[]'",
        "ALTER TABLE packages ADD COLUMN chips TEXT DEFAULT '[]'",
        "ALTER TABLE packages ADD COLUMN package_type TEXT DEFAULT 'searches'",
        "ALTER TABLE pending_payments ADD COLUMN package_type TEXT DEFAULT 'searches'",
        "ALTER TABLE packages ADD COLUMN is_active INTEGER DEFAULT 1",
    ]:
        try:
            await execute(migration)
        except Exception:
            pass
    r = await execute("SELECT COUNT(*) FROM packages")
    count = r.rows[0][0] if r.rows else 0
    if count == 0:
        for pid, label, searches, price, image_url, display_order, duration_months in _DEFAULT_PACKAGES:
            await execute(
                "INSERT OR IGNORE INTO packages (id, label, searches, price, image_url, display_order, duration_months) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [pid, label, searches, price, image_url, display_order, duration_months],
            )
    await execute("UPDATE packages SET display_order = id WHERE display_order = 0 OR display_order IS NULL")
    # Seed the FREE card (searches=0) if not present
    r_free = await execute("SELECT COUNT(*) FROM packages WHERE searches=0 AND COALESCE(package_type,'searches')='searches'")
    if (r_free.rows[0][0] if r_free.rows else 0) == 0:
        default_free_chips = json.dumps(["🤝 +חיפושים על הפניות", "🔓 ללא תפוגה"], ensure_ascii=False)
        await execute(
            "INSERT INTO packages (label, searches, price, image_url, display_order, duration_months, features, chips) VALUES (?,?,?,?,?,?,?,?)",
            ["🆓 מסלול FREE", 0, 0, "", 0, 1, json.dumps(_DEFAULT_FREE_FEATURES, ensure_ascii=False), default_free_chips],
        )
    await _upgrade_default_features()
    await get_packages(force_reload=True)


async def _upgrade_default_features() -> None:
    """Replace never-customised (empty / old-default) feature lists of the FREE and the unlimited
    (Premium) cards with the current ones, so new features such as compare and Yad2 alerts show up."""
    for searches, new_list in ((0, _DEFAULT_FREE_FEATURES), (-1, _DEFAULT_PREMIUM_FEATURES)):
        r = await execute(
            "SELECT id, COALESCE(features,'[]') FROM packages WHERE searches=? AND COALESCE(package_type,'searches')='searches'",
            [searches],
        )
        for pid, raw in r.rows:
            texts = {f["text"] for f in _normalize_features(raw)}
            if not texts or texts <= _LEGACY_FEATURE_TEXTS:
                await execute("UPDATE packages SET features=? WHERE id=?",
                              [json.dumps(new_list, ensure_ascii=False), pid])


def _normalize_features(raw) -> list:
    """Normalize features — handles old string[] and new {text,included}[] formats.
    Accepts a JSON string (from DB) or a Python list (from API body)."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or [])
        result = []
        for item in data:
            if isinstance(item, str):
                result.append({"text": item, "included": True})
            elif isinstance(item, dict) and "text" in item:
                result.append({"text": item["text"], "included": bool(item.get("included", True))})
        return result
    except Exception:
        return []


async def get_packages(force_reload: bool = False, active_only: bool = False) -> list[tuple]:
    """Returns (id, label, searches, price, image_url, display_order, duration_months, features, chips, package_type, is_active) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, label, searches, price, COALESCE(image_url,''), display_order, COALESCE(duration_months,1), "
            "COALESCE(features,'[]'), COALESCE(chips,'[]'), COALESCE(package_type,'searches'), COALESCE(is_active,1) "
            "FROM packages ORDER BY display_order, id"
        )
        _cache = [
            tuple(row[:7]) + (_normalize_features(row[7]), _parse_chips(row[8]), str(row[9]), int(row[10]))
            for row in r.rows
        ]
    if active_only:
        return [p for p in _cache if p[10] == 1]
    return _cache


def _parse_chips(raw) -> list:
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or [])
        return [str(c) for c in data if isinstance(c, str)]
    except Exception:
        return []


async def update_package(pkg_id: int, label: str, searches: int, price: int, image_url: str = "", duration_months: int = 1, features: list | None = None, chips: list | None = None, package_type: str = "searches", is_active: int = 1) -> None:
    features_json = json.dumps(_normalize_features(features), ensure_ascii=False)
    chips_json = json.dumps(_parse_chips(chips) if chips is not None else [], ensure_ascii=False)
    await execute(
        "UPDATE packages SET label=?, searches=?, price=?, image_url=?, duration_months=?, features=?, chips=?, package_type=?, is_active=? WHERE id=?",
        [label, searches, price, image_url, duration_months, features_json, chips_json, package_type, is_active, pkg_id],
    )
    await get_packages(force_reload=True)


async def add_package(label: str, searches: int, price: int, image_url: str = "", duration_months: int = 1, features: list | None = None, chips: list | None = None, package_type: str = "searches", is_active: int = 1) -> None:
    features_json = json.dumps(_normalize_features(features), ensure_ascii=False)
    chips_json = json.dumps(_parse_chips(chips) if chips is not None else [], ensure_ascii=False)
    r = await execute("SELECT COALESCE(MAX(id), 0) + 1 FROM packages")
    next_id = r.rows[0][0] if r.rows else 1
    r2 = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM packages")
    next_order = r2.rows[0][0] if r2.rows else 1
    await execute(
        "INSERT INTO packages (id, label, searches, price, image_url, display_order, duration_months, features, chips, package_type, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [next_id, label, searches, price, image_url, next_order, duration_months, features_json, chips_json, package_type, is_active],
    )
    await get_packages(force_reload=True)


async def delete_package(pkg_id: int) -> None:
    await execute("DELETE FROM packages WHERE id=?", [pkg_id])
    await get_packages(force_reload=True)


async def reorder_packages(ordered_ids: list[int]) -> None:
    for i, pkg_id in enumerate(ordered_ids):
        await execute("UPDATE packages SET display_order=? WHERE id=?", [i + 1, pkg_id])
    await get_packages(force_reload=True)


