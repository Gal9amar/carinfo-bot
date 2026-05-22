"""
Package pricing — stored in DB, cached in memory.
Default packages are seeded on first init_packages() call.
"""

import asyncio
from src.db import execute

_DEFAULT_PACKAGES = [
    (1, "🔍 50 חיפושים",   50,  10, ""),
    (2, "🔍 100 חיפושים", 100,  20, ""),
    (3, "🔍 200 חיפושים", 200,  30, ""),
    (4, "♾️ מנוי חודשי",   -1,  25, ""),
]

_cache: list[tuple[int, str, int, int, str]] | None = None  # (id, label, searches, price, image_url)


async def init_packages() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id        INTEGER PRIMARY KEY,
            label     TEXT    NOT NULL,
            searches  INTEGER NOT NULL,
            price     INTEGER NOT NULL,
            image_url TEXT    DEFAULT ''
        )
    """)
    r = await execute("SELECT COUNT(*) FROM packages")
    count = r.rows[0][0] if r.rows else 0
    if count == 0:
        for pid, label, searches, price, image_url in _DEFAULT_PACKAGES:
            await execute(
                "INSERT OR IGNORE INTO packages (id, label, searches, price, image_url) VALUES (?, ?, ?, ?, ?)",
                [pid, label, searches, price, image_url],
            )
    await get_packages(force_reload=True)


async def get_packages(force_reload: bool = False) -> list[tuple[int, str, int, int, str]]:
    """Returns list of (id, label, searches, price, image_url) sorted by id."""
    global _cache
    if _cache is None or force_reload:
        r = await execute("SELECT id, label, searches, price, COALESCE(image_url,'') FROM packages ORDER BY id")
        _cache = [(row[0], row[1], row[2], row[3], row[4]) for row in r.rows]
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
    await execute(
        "INSERT INTO packages (id, label, searches, price, image_url) VALUES (?, ?, ?, ?, ?)",
        [next_id, label, searches, price, image_url],
    )
    await get_packages(force_reload=True)


async def delete_package(pkg_id: int) -> None:
    await execute("DELETE FROM packages WHERE id=?", [pkg_id])
    await get_packages(force_reload=True)


def invalidate_cache() -> None:
    global _cache
    _cache = None
