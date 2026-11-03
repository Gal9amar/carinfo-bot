"""
Admin grant options — benefits an admin can give users (not for purchase).
Stored in DB, cached in memory.
"""

from src.db import execute

# `searches` keeps its column name but is now a PLAN amount: >0 = days, -1 = 30 days, -2 = permanent, 0 = reset to free.
_DEFAULT_GRANTS = [
    (1, "➕ 7 ימי מנוי",    7, 1),
    (2, "➕ 14 ימי מנוי",  14, 2),
    (3, "➕ 30 ימי מנוי",  30, 3),
    (4, "♾️ מנוי חודשי",   -1, 4),
    (5, "🎖️ גישה חופשית", -2, 5),
    (6, "🆓 מנוי חינם",     0, 0),
]

_cache: list[tuple[int, str, int, int, int]] | None = None  # (id, label, searches(days), display_order, plan_id)


async def init_admin_grants() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS admin_grants (
            id            INTEGER PRIMARY KEY,
            label         TEXT    NOT NULL,
            searches      INTEGER NOT NULL,
            display_order INTEGER DEFAULT 0
        )
    """)
    try:
        await execute("ALTER TABLE admin_grants ADD COLUMN plan_id INTEGER DEFAULT NULL")
    except Exception:
        pass
    await _retire_search_counts()
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


async def _retire_search_counts() -> None:
    """One-time: there is no search counter any more, so old "+N searches" presets and unused
    searches-count promo codes (whose number would now be read as DAYS) are removed."""
    from src.db import get_bot_setting, set_bot_setting
    if (await get_bot_setting("search_counts_retired")) == "1":
        return
    await execute("DELETE FROM admin_grants WHERE searches > 0")
    await execute("DELETE FROM codes WHERE unlimited = 0 AND used_by IS NULL")
    await set_bot_setting("search_counts_retired", "1")


async def get_admin_grants(force_reload: bool = False) -> list[tuple[int, str, int, int, int]]:
    """Returns (id, label, searches(days), display_order, plan_id) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, label, searches, display_order, COALESCE(plan_id, 0) FROM admin_grants ORDER BY display_order, id"
        )
        _cache = [(row[0], row[1], row[2], row[3], row[4]) for row in r.rows]
    return _cache


async def add_admin_grant(label: str, searches: int, plan_id: int | None = None) -> None:
    r = await execute("SELECT COALESCE(MAX(id), 0) + 1 FROM admin_grants")
    next_id = r.rows[0][0] if r.rows else 1
    r2 = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM admin_grants")
    next_order = r2.rows[0][0] if r2.rows else 1
    await execute(
        "INSERT INTO admin_grants (id, label, searches, display_order, plan_id) VALUES (?, ?, ?, ?, ?)",
        [next_id, label, searches, next_order, plan_id or None],
    )
    await get_admin_grants(force_reload=True)


async def update_admin_grant(grant_id: int, label: str, searches: int, plan_id: int | None = None) -> None:
    await execute(
        "UPDATE admin_grants SET label=?, searches=?, plan_id=? WHERE id=?",
        [label, searches, plan_id or None, grant_id],
    )
    await get_admin_grants(force_reload=True)


async def delete_admin_grant(grant_id: int) -> None:
    await execute("DELETE FROM admin_grants WHERE id=?", [grant_id])
    await get_admin_grants(force_reload=True)


async def reorder_admin_grants(ordered_ids: list[int]) -> None:
    for i, grant_id in enumerate(ordered_ids):
        await execute("UPDATE admin_grants SET display_order=? WHERE id=?", [i + 1, grant_id])
    await get_admin_grants(force_reload=True)
