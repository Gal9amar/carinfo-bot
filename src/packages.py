"""
Package pricing — stored in DB, cached in memory.
Default packages are seeded on first init_packages() call.
"""

import asyncio
from src.db import execute

_DEFAULT_PACKAGES = [
    (1, "🔍 50 חיפושים",   50,  10, "", 1),
    (2, "🔍 100 חיפושים", 100,  20, "", 2),
    (3, "🔍 200 חיפושים", 200,  30, "", 3),
    (4, "♾️ מנוי חודשי",   -1,  25, "", 4),
]

_cache: list[tuple[int, str, int, int, str, int]] | None = None  # (id, label, searches, price, image_url, display_order)


async def init_packages() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id            INTEGER PRIMARY KEY,
            label         TEXT    NOT NULL,
            searches      INTEGER NOT NULL,
            price           INTEGER NOT NULL,
            image_url       TEXT    DEFAULT '',
            display_order   INTEGER DEFAULT 0
        )
    """)
    r = await execute("SELECT COUNT(*) FROM packages")
    count = r.rows[0][0] if r.rows else 0
    if count == 0:
        for pid, label, searches, price, image_url, display_order in _DEFAULT_PACKAGES:
            await execute(
                "INSERT OR IGNORE INTO packages (id, label, searches, price, image_url, display_order) VALUES (?, ?, ?, ?, ?, ?)",
                [pid, label, searches, price, image_url, display_order],
            )
    # Backfill display_order for rows that were created before the column existed
    await execute("UPDATE packages SET display_order = id WHERE display_order = 0 OR display_order IS NULL")
    await get_packages(force_reload=True)


async def get_packages(force_reload: bool = False) -> list[tuple[int, str, int, int, str, int]]:
    """Returns list of (id, label, searches, price, image_url, display_order) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, label, searches, price, COALESCE(image_url,''), display_order "
            "FROM packages ORDER BY display_order, id"
        )
        _cache = [(row[0], row[1], row[2], row[3], row[4], row[5]) for row in r.rows]
    return _cache


async def update_package(pkg_id: int, label: str, searches: int, price: int, image_url: str = "") -> None:
    await execute(
        "UPDATE packages SET label=?, searches=?, price=?, image_url=? WHERE id=?",
        [label, searches, price, image_url, pkg_id],
    )
    await get_packages(force_reload=True)


async def add_package(label: str, searches: int, price: int, image_url: str = "") -> None:
    r = await execute("SELECT COALESCE(MAX(id), 0) + 1 FROM packages")
    next_id = r.rows[0][0] if r.rows else 1
    r2 = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM packages")
    next_order = r2.rows[0][0] if r2.rows else 1
    await execute(
        "INSERT INTO packages (id, label, searches, price, image_url, display_order) VALUES (?, ?, ?, ?, ?, ?)",
        [next_id, label, searches, price, image_url, next_order],
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
