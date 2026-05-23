"""
Admin grant options — benefits an admin can give users (not for purchase).
Stored in DB, cached in memory.
"""

from src.db import execute

_DEFAULT_GRANTS = [
    (1, "➕ 50 בדיקות",    50, 1),
    (2, "➕ 100 בדיקות",  100, 2),
    (3, "➕ 200 בדיקות",  200, 3),
    (4, "♾️ מנוי חודשי",   -1, 4),
    (5, "🎖️ גישה חופשית", -2, 5),
    (6, "🆓 מנוי חינם",     0, 0),
]

_cache: list[tuple[int, str, int, int]] | None = None  # (id, label, searches, display_order)


async def init_admin_grants() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS admin_grants (
            id            INTEGER PRIMARY KEY,
            label         TEXT    NOT NULL,
            searches      INTEGER NOT NULL,
            display_order INTEGER DEFAULT 0
        )
    """)
    r = await execute("SELECT COUNT(*) FROM admin_grants")
    count = r.rows[0][0] if r.rows else 0
    if count == 0:
        for gid, label, searches, display_order in _DEFAULT_GRANTS:
            await execute(
                "INSERT OR IGNORE INTO admin_grants (id, label, searches, display_order) VALUES (?, ?, ?, ?)",
                [gid, label, searches, display_order],
            )
    await execute("UPDATE admin_grants SET display_order = id WHERE display_order = 0 OR display_order IS NULL")
    await get_admin_grants(force_reload=True)


async def get_admin_grants(force_reload: bool = False) -> list[tuple[int, str, int, int]]:
    """Returns (id, label, searches, display_order) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, label, searches, display_order FROM admin_grants ORDER BY display_order, id"
        )
        _cache = [(row[0], row[1], row[2], row[3]) for row in r.rows]
    return _cache


async def add_admin_grant(label: str, searches: int) -> None:
    r = await execute("SELECT COALESCE(MAX(id), 0) + 1 FROM admin_grants")
    next_id = r.rows[0][0] if r.rows else 1
    r2 = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM admin_grants")
    next_order = r2.rows[0][0] if r2.rows else 1
    await execute(
        "INSERT INTO admin_grants (id, label, searches, display_order) VALUES (?, ?, ?, ?)",
        [next_id, label, searches, next_order],
    )
    await get_admin_grants(force_reload=True)


async def update_admin_grant(grant_id: int, label: str, searches: int) -> None:
    await execute(
        "UPDATE admin_grants SET label=?, searches=? WHERE id=?",
        [label, searches, grant_id],
    )
    await get_admin_grants(force_reload=True)


async def delete_admin_grant(grant_id: int) -> None:
    await execute("DELETE FROM admin_grants WHERE id=?", [grant_id])
    await get_admin_grants(force_reload=True)


async def reorder_admin_grants(ordered_ids: list[int]) -> None:
    for i, grant_id in enumerate(ordered_ids):
        await execute("UPDATE admin_grants SET display_order=? WHERE id=?", [i + 1, grant_id])
    await get_admin_grants(force_reload=True)
