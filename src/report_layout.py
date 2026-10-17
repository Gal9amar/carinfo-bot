"""Order / visibility of the components of the vehicle report (Mini App), editable by the admin.

Two tabs: `summary` and `full`. Stored in bot_settings.report_layout as
{"summary": [{"id": ..., "visible": true}, ...], "full": [...]}. Ids unknown to the code are dropped and
components missing from the stored value are appended in their default position, so adding a new
component never breaks an old saved layout. The footer buttons of the full tab are not configurable.
"""
import json

from src.db import get_bot_setting, set_bot_setting

# (id, admin label, short description) in the DEFAULT order
COMPONENTS: dict[str, list[tuple[str, str, str]]] = {
    "summary": [
        ("score",        "כרטיס ציון ומצב הרכב",        "ציון כללי, דגלים ונתונים עיקריים בקצרה"),
        ("test",         "תוקף טסט",                      "תאריך תוקף הטסט והסטטוס שלו"),
        ("model_count",  "מספר רכבים מהדגם על הכביש",     "כמה רכבים מאותו דגם רשומים בישראל"),
        ("ownership",    "היסטוריית בעלויות",             "רשימת הבעלים לפי תאריך"),
        ("main_details", "פרטים עיקריים",                 "יצרן, דגם, שנה, צבע, דלק ועוד"),
        ("recalls",      "ריקולים",                       "ריקולים פתוחים לרכב או לדגם"),
        ("notes",        "הערות אישיות",                  "הערה פרטית של המשתמש על הרכב"),
        ("garage",       "קניתי את הרכב הזה",             "הוספת הרכב ל״רכבים שקניתי״"),
        ("market",       "מחיר שוק Yad2 (פרימיום)",       "הערכת מחיר שוק לפי מודעות"),
        ("alerts",       "התראות יד2 (פרימיום)",          "התראה על מודעות חדשות לדגם"),
        ("pdf",          "דוח PDF (פרימיום)",             "שליחת דוח PDF לצ׳אט"),
        ("compare",      "השוואת רכבים",                  "השוואה מול רכב נוסף"),
    ],
    "full": [
        ("general",   "פרטים כלליים",     "זיהוי הרכב ורישום"),
        ("technical", "מפרט טכני",         "מנוע, הנעה, מידות ומשקלים"),
        ("wheels",    "גלגלים",            "צמיגים וגלגלים"),
        ("equipment", "ציוד",              "ציוד ורמת גימור"),
        ("safety",    "בטיחות",            "דירוג ורכיבי בטיחות"),
        ("adas",      "ADAS",              "מערכות סיוע לנהג"),
        ("history",   "היסטוריה ורישום",   "שינויים, עלייה לכביש וקילומטראז׳"),
        ("recalls",   "ריקולים",           "ריקולים פתוחים"),
    ],
}


def default_layout() -> dict:
    return {tab: [{"id": cid, "visible": True} for cid, _, _ in comps] for tab, comps in COMPONENTS.items()}


def normalize(raw) -> dict:
    """Merge a stored/received layout with the known components (see module docstring)."""
    out = {}
    for tab, comps in COMPONENTS.items():
        known = {cid for cid, _, _ in comps}
        seen, items = set(), []
        src = raw.get(tab) if isinstance(raw, dict) else None
        for it in (src if isinstance(src, list) else []):
            cid = it.get("id") if isinstance(it, dict) else it
            if cid in known and cid not in seen:
                seen.add(cid)
                items.append({"id": cid, "visible": bool(it.get("visible", True)) if isinstance(it, dict) else True})
        for cid, _, _ in comps:          # components added later / missing → default spot (end)
            if cid not in seen:
                items.append({"id": cid, "visible": True})
        out[tab] = items
    return out


async def get_layout() -> dict:
    try:
        raw = json.loads((await get_bot_setting("report_layout")) or "null")
    except ValueError:
        raw = None
    return normalize(raw)


async def save_layout(raw) -> dict:
    layout = normalize(raw)
    await set_bot_setting("report_layout", json.dumps(layout, ensure_ascii=False))
    return layout


async def reset_layout() -> dict:
    await set_bot_setting("report_layout", "")
    return default_layout()


def catalog() -> dict:
    return {tab: [{"id": c, "label": l, "description": d} for c, l, d in comps] for tab, comps in COMPONENTS.items()}
