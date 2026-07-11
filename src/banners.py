"""
Promotional banners — stored in DB, cached in memory. Shown on whichever
pages the admin picks (placements, e.g. ["home","report"]). Each banner
links either to an internal page (link_type='page', link_value=<screen id>,
e.g. 'packages', 'referral', 'history') or to a specific digital product
(link_type='product', link_value=<product id>).
"""

import json
from src.db import execute

_cache: list[tuple] | None = None  # (id, title, subtitle, icon, image_url, color_from, color_to, link_type, link_value, placements, display_order, is_active)


def _normalize_placements(raw) -> list:
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or [])
        result = [p for p in data if isinstance(p, str) and p.strip()]
        return result or ["home"]
    except Exception:
        return ["home"]


async def init_banners() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS banners (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            subtitle      TEXT DEFAULT '',
            icon          TEXT DEFAULT '🎁',
            image_url     TEXT DEFAULT '',
            color_from    TEXT DEFAULT '#38a169',
            color_to      TEXT DEFAULT '#276749',
            link_type     TEXT NOT NULL DEFAULT 'page',
            link_value    TEXT NOT NULL DEFAULT 'packages',
            display_order INTEGER DEFAULT 0,
            is_active     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)
    try:
        await execute("ALTER TABLE banners ADD COLUMN placements TEXT DEFAULT '[\"home\"]'")
    except Exception:
        pass
    r = await execute("SELECT COUNT(*) FROM banners")
    if r.rows and r.rows[0][0] == 0:
        await execute(
            "INSERT INTO banners (title, subtitle, icon, color_from, color_to, link_type, link_value, placements, display_order) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ["קבל חיפושים בחינם!", "הפנה חברים וקבל חיפושים על כל הצטרפות ←", "🎁",
             "#38a169", "#276749", "page", "referral", json.dumps(["home"]), 1],
        )
        await execute(
            "INSERT INTO banners (title, subtitle, icon, color_from, color_to, link_type, link_value, placements, display_order) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            ["Gemini Pro AI", "מוצר דיגיטלי חדש בחנות — לרכישה ←", "🤖",
             "#1e40af", "#0ea5e9", "page", "packages", json.dumps(["home"]), 2],
        )

    # Backfill: banners that used to be hardcoded in the frontend. Each is
    # inserted once (matched by title) so they become admin-editable even on
    # databases that already ran the seed above before this existed.
    await _backfill_banner(
        "הפנה חברים — קבל חיפושים על כל הצטרפות",
        "כל חבר שמצטרף לבוט דרך הלינק שלך מוסיף לך חיפושים אוטומטית", "🎁",
        "#2481cc", "#1a5fa8", "page", "packages", ["referral"],
    )
    await _backfill_banner(
        "רוצה חיפושים בחינם?",
        "הפנה חברים וקבל חיפושים על כל הצטרפות ←", "🎁",
        "#38a169", "#276749", "page", "referral", ["packages"],
    )

    await get_banners(force_reload=True)


async def _backfill_banner(
    title: str, subtitle: str, icon: str, color_from: str, color_to: str,
    link_type: str, link_value: str, placements: list,
) -> None:
    check = await execute("SELECT COUNT(*) FROM banners WHERE title=?", [title])
    if check.rows and check.rows[0][0] > 0:
        return
    r = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM banners")
    next_order = r.rows[0][0] if r.rows else 1
    await execute(
        "INSERT INTO banners (title, subtitle, icon, color_from, color_to, link_type, link_value, placements, display_order) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        [title, subtitle, icon, color_from, color_to, link_type, link_value, json.dumps(placements), next_order],
    )


async def get_banners(force_reload: bool = False, active_only: bool = False, page: str | None = None) -> list[tuple]:
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, title, COALESCE(subtitle,''), COALESCE(icon,'🎁'), COALESCE(image_url,''), "
            "COALESCE(color_from,'#38a169'), COALESCE(color_to,'#276749'), link_type, link_value, "
            "COALESCE(placements,'[\"home\"]'), display_order, COALESCE(is_active,1) "
            "FROM banners ORDER BY display_order, id"
        )
        _cache = [tuple(row[:9]) + (_normalize_placements(row[9]), row[10], row[11]) for row in r.rows]
    result = _cache
    if active_only:
        result = [b for b in result if b[11] == 1]
    if page:
        result = [b for b in result if page in b[9]]
    return result


async def get_banner(banner_id: int) -> tuple | None:
    banners = await get_banners()
    return next((b for b in banners if b[0] == banner_id), None)


async def add_banner(
    title: str, subtitle: str = "", icon: str = "🎁", image_url: str = "",
    color_from: str = "#38a169", color_to: str = "#276749",
    link_type: str = "page", link_value: str = "packages",
    placements: list | None = None, is_active: int = 1,
) -> int:
    r = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM banners")
    next_order = r.rows[0][0] if r.rows else 1
    placements_json = json.dumps(_normalize_placements(placements), ensure_ascii=False)
    r2 = await execute(
        "INSERT INTO banners (title, subtitle, icon, image_url, color_from, color_to, link_type, link_value, "
        "placements, display_order, is_active) VALUES (?,?,?,?,?,?,?,?,?,?,?) RETURNING id",
        [title, subtitle, icon, image_url, color_from, color_to, link_type, link_value,
         placements_json, next_order, is_active],
    )
    await get_banners(force_reload=True)
    return r2.rows[0][0] if r2.rows else 0


async def update_banner(banner_id: int, **kwargs) -> None:
    allowed = {"title", "subtitle", "icon", "image_url", "color_from", "color_to",
               "link_type", "link_value", "placements", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    if "placements" in fields:
        fields["placements"] = json.dumps(_normalize_placements(fields["placements"]), ensure_ascii=False)
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(f"UPDATE banners SET {set_clause} WHERE id=?", [*fields.values(), banner_id])
    await get_banners(force_reload=True)


async def delete_banner(banner_id: int) -> None:
    await execute("DELETE FROM banners WHERE id=?", [banner_id])
    await get_banners(force_reload=True)


async def reorder_banners(ordered_ids: list[int]) -> None:
    for i, bid in enumerate(ordered_ids):
        await execute("UPDATE banners SET display_order=? WHERE id=?", [i + 1, bid])
    await get_banners(force_reload=True)
