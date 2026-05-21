"""
Hebrew PDF report generator for vehicle data.
Uses reportlab + python-bidi to render RTL Hebrew text.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

# ── Font registration (done once) ────────────────────────────────────────────
_font_registered: bool = False
_FONT_NAME = "DejaVuSans"
_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]


def _ensure_font() -> str:
    """Register DejaVuSans once; fall back to Helvetica if not found."""
    global _font_registered
    if _font_registered:
        return _FONT_NAME

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for path in _FONT_PATHS:
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME, path))
            _font_registered = True
            return _FONT_NAME
        except Exception:
            continue

    # Fallback
    _font_registered = True
    return "Helvetica"


# ── BiDi helper ───────────────────────────────────────────────────────────────

def _b(text: Any) -> str:
    """Apply Unicode BiDi algorithm so Hebrew renders correctly in PDFs."""
    s = str(text) if text is not None else ""
    try:
        from bidi.algorithm import get_display
        return get_display(s)
    except Exception:
        return s


# ── Value helpers ─────────────────────────────────────────────────────────────

def _v(record: dict, *keys: str) -> str:
    """Return first non-empty/None/nan/0 value from record keys."""
    for k in keys:
        v = record.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s not in ("", "None", "nan", "0"):
            return s
    return ""


def _fd(raw: Any) -> str:
    """Format YYYY-MM-DD (or ISO) date string as DD/MM/YYYY."""
    if not raw:
        return ""
    s = str(raw).strip()
    try:
        return datetime.fromisoformat(s[:10]).strftime("%d/%m/%Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def _fmt_baalut_dt(raw: Any) -> str:
    """Convert YYYYMM integer/string to Hebrew month name + year."""
    months = [
        "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
    ]
    try:
        s = str(int(raw))
        y, m = s[:4], s[4:6]
        return f"{months[int(m)]} {y}"
    except Exception:
        return str(raw) if raw else ""


def _test_status_str(tokef_raw: Any) -> tuple[str, str]:
    """Return (status_text, color_hex) for test validity."""
    if not tokef_raw:
        return "לא ידוע", "#888888"
    try:
        tokef = date.fromisoformat(str(tokef_raw)[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"פג תוקף לפני {abs(delta)} ימים", "#CC0000"
        if delta <= 30:
            return f"פג תוקף בעוד {delta} ימים", "#E07800"
        return f"בתוקף עד {tokef.strftime('%d/%m/%Y')}", "#008800"
    except Exception:
        return "לא ידוע", "#888888"


# ── Colours & sizes ───────────────────────────────────────────────────────────

_A4_W = 210 * 2.8346456692913385   # 595.28 pt
_A4_H = 297 * 2.8346456692913385   # 841.89 pt
_MM = 2.8346456692913385           # 1 mm in points
_MARGIN = 15 * _MM
_USABLE_W = 180 * _MM
_COL_VALUE = 120 * _MM
_COL_LABEL = 60 * _MM

_DARK_BLUE = (0.10, 0.22, 0.45)
_LIGHT_BLUE = (0.18, 0.38, 0.72)
_SECTION_BG = (0.88, 0.93, 1.00)
_SECTION_TEXT = (0.10, 0.22, 0.45)
_ROW_ALT = (0.95, 0.95, 0.95)
_ROW_WHITE = (1.0, 1.0, 1.0)
_GRAY_GRID = (0.70, 0.70, 0.70)
_WARN_BG = (1.0, 0.97, 0.80)
_WARN_BORDER = (0.85, 0.65, 0.00)
_ALERT_BG = (1.0, 0.88, 0.88)
_ALERT_BORDER = (0.80, 0.10, 0.10)
_GRAY_TEXT = (0.50, 0.50, 0.50)


# ── PDF builder ───────────────────────────────────────────────────────────────

def generate_pdf(record: dict) -> bytes:
    """Generate a full Hebrew vehicle-report PDF and return raw bytes."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    font = _ensure_font()

    # ── Paragraph styles ──────────────────────────────────────────────────────
    def _style(name, size=10, bold=False, color=colors.black, align=0, leading=None):
        """align: 0=LEFT (used for bidi text), 1=CENTER, 2=RIGHT"""
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
        alignment = [TA_LEFT, TA_CENTER, TA_RIGHT][align]
        return ParagraphStyle(
            name,
            fontName=font,
            fontSize=size,
            textColor=color,
            alignment=alignment,
            leading=leading or (size * 1.4),
            wordWrap="CJK",
        )

    s_header = _style("header", 16, color=colors.white, align=1)
    s_sub_header = _style("sub_header", 12, color=colors.white, align=1)
    s_section = _style("section", 11, color=colors.Color(*_SECTION_TEXT), align=1)
    s_label = _style("label", 9, color=colors.Color(0.3, 0.3, 0.3), align=0)
    s_value = _style("value", 9, color=colors.black, align=0)
    s_warn = _style("warn", 9, color=colors.Color(0.50, 0.30, 0.00), align=0)
    s_alert = _style("alert", 9, color=colors.Color(0.70, 0.00, 0.00), align=0)
    s_footer = _style("footer", 7, color=colors.Color(*_GRAY_TEXT), align=1)

    # ── Helpers ───────────────────────────────────────────────────────────────
    w = record.get("_wltp") or {}

    plate = _v(record, "mispar_rechev") or "---"
    make = _v(record, "tozeret_nm")
    model = _v(record, "kinuy_mishari", "degem_nm")
    year = _v(record, "shnat_yitzur")

    def _header_bar(text: str, bg: tuple) -> Table:
        p = Paragraph(_b(text), s_header)
        tbl = Table([[p]], colWidths=[_USABLE_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*bg)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        return tbl

    def _sub_bar(text: str) -> Table:
        p = Paragraph(_b(text), s_sub_header)
        tbl = Table([[p]], colWidths=[_USABLE_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*_LIGHT_BLUE)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tbl

    def _section_header(title: str) -> Table:
        p = Paragraph(_b(title), s_section)
        tbl = Table([[p]], colWidths=[_USABLE_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*_SECTION_BG)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return tbl

    def kv_table(rows: list[tuple[str, str]]) -> Table | None:
        """Build alternating-row key-value table. Skips empty values."""
        data = []
        for label, value in rows:
            if not value:
                continue
            data.append([
                Paragraph(_b(value), s_value),
                Paragraph(_b(label), s_label),
            ])
        if not data:
            return None
        style = [
            ("GRID",         (0, 0), (-1, -1), 0.3, colors.Color(*_GRAY_GRID)),
            ("LEFTPADDING",  (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i, _ in enumerate(data):
            bg = _ROW_WHITE if i % 2 == 0 else _ROW_ALT
            style.append(("BACKGROUND", (0, i), (-1, i), colors.Color(*bg)))
        tbl = Table(data, colWidths=[_COL_VALUE, _COL_LABEL])
        tbl.setStyle(TableStyle(style))
        return tbl

    def _alert_box(text: str) -> Table:
        p = Paragraph(_b(text), s_alert)
        tbl = Table([[p]], colWidths=[_USABLE_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), colors.Color(*_ALERT_BG)),
            ("BOX",          (0, 0), (-1, -1), 1.0, colors.Color(*_ALERT_BORDER)),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ]))
        return tbl

    def _warn_box(text: str) -> Table:
        p = Paragraph(_b(text), s_warn)
        tbl = Table([[p]], colWidths=[_USABLE_W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), colors.Color(*_WARN_BG)),
            ("BOX",          (0, 0), (-1, -1), 1.0, colors.Color(*_WARN_BORDER)),
            ("LEFTPADDING",  (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ]))
        return tbl

    # ── Story ─────────────────────────────────────────────────────────────────
    story = []

    # 1. Dark-blue header
    story.append(_header_bar(f"דוח בדיקת רכב — {plate}", _DARK_BLUE))

    # 2. Sub-bar with make/model/year
    sub_parts = " ".join(x for x in [make, model, year] if x)
    story.append(_sub_bar(sub_parts or plate))
    story.append(Spacer(1, 4))

    # 3. Red alert if scrapped
    scrapped_dt = record.get("_scrapped_dt")
    if scrapped_dt:
        dt_str = _fd(scrapped_dt)
        story.append(_alert_box(
            f"אזהרה: רכב זה בוטל רשמית (גרוטאה) — תאריך ביטול: {dt_str}"
        ))
        story.append(Spacer(1, 4))

    # 4. Section: פרטים כלליים
    story.append(_section_header("פרטים כלליים"))
    general_rows = [
        ("מספר רכב",     plate),
        ("יצרן",          make),
        ("דגם",           model),
        ("שנת ייצור",     year),
        ("צבע",           _v(record, "tzeva_rechev")),
        ("בעלות נוכחית",  _v(record, "baalut")),
        ("ארץ ייצור",     _v(w, "tozeret_eretz_nm")),
        ("מקוריות",       _v(record, "mkoriut_nm")),
        ("מסגרת",         _v(record, "misgeret")),
    ]
    tbl = kv_table(general_rows)
    if tbl:
        story.append(tbl)
    story.append(Spacer(1, 6))

    # 5. Section: מצב ובדיקות
    story.append(_section_header("מצב ובדיקות"))
    tokef_raw = record.get("tokef_dt")
    test_txt, test_color = _test_status_str(tokef_raw)
    km_val = _v(record, "kilometer_test_aharon")
    was_rental = record.get("_was_rental", False)
    gapam = record.get("gapam_ind")
    body_change = record.get("shinui_mivne_ind")
    color_change = record.get("shnui_zeva_ind")

    status_rows = [
        ("תוקף טסט",              test_txt),
        ("ק\"מ בטסט אחרון",       f"{km_val} ק\"מ" if km_val else ""),
        ("טסט אחרון",              _fd(record.get("mivchan_acharon_dt"))),
        ("רישום ראשון",            _fd(record.get("rishum_rishon_dt"))),
        ("רכב שכור בעבר",          "כן" if was_rental else "לא"),
        ("GAPAM",                  "כן" if str(gapam) == "1" else ("לא" if gapam is not None else "")),
        ("שינוי מבנה",             "כן" if str(body_change) == "1" else ("לא" if body_change is not None else "")),
        ("שינוי צבע",              "כן" if str(color_change) == "1" else ("לא" if color_change is not None else "")),
    ]
    tbl = kv_table(status_rows)
    if tbl:
        story.append(tbl)
    story.append(Spacer(1, 6))

    # 6. Section: היסטוריית בעלויות
    ownership = record.get("_ownership") or []
    n_own = len(ownership)
    story.append(_section_header(f"היסטוריית בעלויות ({n_own} רשומות)"))
    if ownership:
        own_data = []
        for i, o in enumerate(ownership, 1):
            dt_str = _fmt_baalut_dt(o.get("baalut_dt", ""))
            baalut_type = o.get("baalut", "לא ידוע")
            own_data.append([
                Paragraph(_b(f"{i}. {dt_str}"), s_value),
                Paragraph(_b(baalut_type), s_label),
            ])
        if own_data:
            own_style = [
                ("GRID",         (0, 0), (-1, -1), 0.3, colors.Color(*_GRAY_GRID)),
                ("LEFTPADDING",  (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING",   (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ]
            for i in range(len(own_data)):
                bg = _ROW_WHITE if i % 2 == 0 else _ROW_ALT
                own_style.append(("BACKGROUND", (0, i), (-1, i), colors.Color(*bg)))
            own_tbl = Table(own_data, colWidths=[_COL_VALUE, _COL_LABEL])
            own_tbl.setStyle(TableStyle(own_style))
            story.append(own_tbl)
    else:
        story.append(Paragraph(_b("לא נמצאו נתוני בעלות"), s_value))
    story.append(Spacer(1, 6))

    # 7. Section: מפרט טכני
    story.append(_section_header("מפרט טכני"))
    auto_ind = w.get("automatic_ind")
    gearbox = "אוטומטית" if str(auto_ind) == "1" else ("ידנית" if str(auto_ind) == "0" else "")
    engine_cc = _v(w, "nefah_manoa")
    specs_rows = [
        ("סוג דלק",      _v(record, "sug_delek_nm")),
        ("נפח מנוע",     f"{engine_cc} סמ\"ק" if engine_cc else ""),
        ("כוח סוס",      _v(w, "koah_sus")),
        ("תיבת הילוכים", gearbox),
        ("מושבים",       _v(w, "mispar_moshavim")),
        ("ניקוד בטיחות", _v(w, "nikud_betihut")),
    ]
    tbl = kv_table(specs_rows)
    if tbl:
        story.append(tbl)
    story.append(Spacer(1, 6))

    # 8. Section: דגלים ואזהרות
    try:
        from src.formatter import _check_km_fraud
        flags = []
        km_warn = _check_km_fraud(record)
        if km_warn:
            # Strip MarkdownV2 escapes for PDF
            import re as _re
            plain = _re.sub(r"\\([\\!\"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~])", r"\1", km_warn)
            flags.append(plain)
    except Exception:
        flags = []

    if flags:
        story.append(_section_header("דגלים ואזהרות"))
        for flag in flags:
            if flag:
                story.append(_warn_box(flag))
                story.append(Spacer(1, 2))
        story.append(Spacer(1, 4))

    # 9. Section: שווי ומחיר
    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            age = 0
            if year:
                age = date.today().year - int(year)
            dep_pct = min(age * 8, 70) if age > 0 else 0
            est_val = int(price_int * (1 - dep_pct / 100))
            story.append(_section_header("שווי ומחיר"))
            price_rows = [
                ("מחיר יבואן (חדש)",   f"₪{price_int:,}"),
                ("הערכת שווי",          f"₪{est_val:,} (ירידת ערך ≈{dep_pct}%)"),
            ]
            tbl = kv_table(price_rows)
            if tbl:
                story.append(tbl)
            story.append(Spacer(1, 6))
        except Exception:
            pass

    # 10. Footer
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(HRFlowable(width=_USABLE_W, thickness=0.5, color=colors.Color(*_GRAY_TEXT)))
    story.append(Spacer(1, 2))
    story.append(Paragraph(_b(f"מופק על ידי @israelcarinfobot | {now_str}"), s_footer))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
    )
    doc.build(story)
    return buf.getvalue()
