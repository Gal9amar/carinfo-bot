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

_cache: list[tuple] | None = None  # (id, label, searches, price, image_url, display_order, duration_months, features)


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
    await get_packages(force_reload=True)


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


async def get_packages(force_reload: bool = False) -> list[tuple]:
    """Returns list of (id, label, searches, price, image_url, display_order, duration_months, features) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, label, searches, price, COALESCE(image_url,''), display_order, COALESCE(duration_months,1), COALESCE(features,'[]') "
            "FROM packages ORDER BY display_order, id"
        )
        _cache = [tuple(row[:7]) + (_normalize_features(row[7]),) for row in r.rows]
    return _cache


async def update_package(pkg_id: int, label: str, searches: int, price: int, image_url: str = "", duration_months: int = 1, features: list | None = None) -> None:
    features_json = json.dumps(_normalize_features(features), ensure_ascii=False)
    await execute(
        "UPDATE packages SET label=?, searches=?, price=?, image_url=?, duration_months=?, features=? WHERE id=?",
        [label, searches, price, image_url, duration_months, features_json, pkg_id],
    )
    await get_packages(force_reload=True)


async def add_package(label: str, searches: int, price: int, image_url: str = "", duration_months: int = 1, features: list | None = None) -> None:
    features_json = json.dumps(_normalize_features(features), ensure_ascii=False)
    r = await execute("SELECT COALESCE(MAX(id), 0) + 1 FROM packages")
    next_id = r.rows[0][0] if r.rows else 1
    r2 = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM packages")
    next_order = r2.rows[0][0] if r2.rows else 1
    await execute(
        "INSERT INTO packages (id, label, searches, price, image_url, display_order, duration_months, features) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [next_id, label, searches, price, image_url, next_order, duration_months, features_json],
    )
    await get_packages(force_reload=True)


async def delete_package(pkg_id: int) -> None:
    await execute("DELETE FROM packages WHERE id=?", [pkg_id])
    await get_packages(force_reload=True)


async def reorder_packages(ordered_ids: list[int]) -> None:
    for i, pkg_id in enumerate(ordered_ids):
        await execute("UPDATE packages SET display_order=? WHERE id=?", [i + 1, pkg_id])
    await get_packages(force_reload=True)


def invalidate_cache() -> None:
    global _cache
    _cache = None
