"""
Hebrew PDF — Israeli vehicle license (רישיון רכב) layout.
ReportLab Paragraphs: logical Hebrew + TA_RIGHT (no python-bidi).
Canvas strings: get_display via _cb() only.
"""

from __future__ import annotations

import io
import os
import re
from datetime import date, datetime
from typing import Any

from reportlab.lib.pagesizes import landscape, A4

_PAGE = landscape(A4)
_PW, _PH = _PAGE

_FONT_REGISTERED = False
_FONT = "DejaVuSans"
_FONT_BOLD = "DejaVuSans-Bold"
_FONT_PATHS = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
    (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    (r"C:\Windows\Fonts\david.ttf", r"C:\Windows\Fonts\davidbd.ttf"),
]

_MM = 2.8346456692913385
_MARGIN = 10 * _MM
_USABLE_W = _PW - 2 * _MARGIN
_FOOTER_H = 18 * _MM

# License palette (from official slip)
C_BG = (0.90, 0.94, 0.98)
C_TITLE = (0.45, 0.05, 0.22)
C_BAR = (0.04, 0.12, 0.36)
C_BAR_LT = (0.10, 0.24, 0.48)
C_LBL_RED = (0.55, 0.05, 0.12)
C_LBL_BLUE = (0.08, 0.22, 0.48)
C_VAL = (0.05, 0.05, 0.08)
C_LINE = (0.72, 0.78, 0.86)
C_WHITE = (1.0, 1.0, 1.0)
C_FOOT = (0.88, 0.92, 0.96)
C_ALERT = (0.75, 0.12, 0.12)
C_WARN = (0.55, 0.35, 0.05)
C_TG = (0.16, 0.52, 0.78)
C_WA = (0.15, 0.68, 0.38)

_HEB_RE = re.compile(r"[\u0590-\u05FF]")


def _ensure_fonts() -> tuple[str, str]:
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return _FONT, _FONT_BOLD
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    regular, bold = "Helvetica", "Helvetica-Bold"
    for reg_path, bold_path in _FONT_PATHS:
        if not os.path.isfile(reg_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(_FONT, reg_path))
            bold_file = bold_path if os.path.isfile(bold_path) else reg_path
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, bold_file))
            regular, bold = _FONT, _FONT_BOLD
            break
        except Exception:
            continue
    _FONT_REGISTERED = True
    return regular, bold


def _cb(text: Any) -> str:
    """Visual-order Hebrew for canvas drawString (LTR pipeline)."""
    s = str(text) if text is not None else ""
    if not s or not _HEB_RE.search(s):
        return s
    try:
        from bidi.algorithm import get_display
        return get_display(s)
    except Exception:
        return s


def _t(text: Any) -> str:
    """Logical-order text for ReportLab Paragraph + TA_RIGHT."""
    return str(text) if text is not None else ""


def _v(record: dict, *keys: str) -> str:
    for k in keys:
        v = record.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s not in ("", "None", "nan", "0"):
            return s
    return ""


def _fd(raw: Any) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    try:
        return datetime.fromisoformat(s[:10]).strftime("%d/%m/%Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def _fmt_baalut_dt(raw: Any) -> str:
    months = [
        "", "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
        "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
    ]
    try:
        s = str(int(raw))
        return f"{months[int(s[4:6])]} {s[:4]}"
    except Exception:
        return str(raw) if raw else ""


def _test_status(tokef_raw: Any) -> str:
    if not tokef_raw:
        return "—"
    try:
        tokef = date.fromisoformat(str(tokef_raw)[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"{tokef.strftime('%d/%m/%Y')} (פג)"
        return tokef.strftime("%d/%m/%Y")
    except Exception:
        return "—"


def _full_url(link: str) -> str:
    s = (link or "").strip()
    if not s:
        return ""
    if s.startswith(("http://", "https://")):
        return s
    return f"https://{s.lstrip('/')}"


def _inactive_txt(record: dict) -> str:
    if record.get("_inactive_no_degem"):
        return "לא פעיל (ללא קוד דגם)"
    if record.get("_inactive_registry") or record.get("_was_rental"):
        return _v(record, "grira_nm") or "רשום במאגר לא פעיל"
    return "פעיל"


def _vehicle_type(record: dict, wltp: dict) -> str:
    parts = [
        _v(wltp, "sug_tkina_nm"),
        _v(record, "baalut"),
        _v(wltp, "ramat_gimur"),
    ]
    return " · ".join(p for p in parts if p) or "—"


def _icon_png_bytes(kind: str, size: int = 28) -> bytes:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return b""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if kind == "telegram":
        d.ellipse([1, 1, size - 2, size - 2], fill=(42, 171, 238, 255))
        d.polygon(
            [(size * 0.28, size * 0.48), (size * 0.72, size * 0.32),
             (size * 0.48, size * 0.52), (size * 0.62, size * 0.72)],
            fill=(255, 255, 255, 255),
        )
    else:
        d.ellipse([1, 1, size - 2, size - 2], fill=(37, 211, 102, 255))
        d.ellipse([size * 0.28, size * 0.26, size * 0.74, size * 0.68], fill=(255, 255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_pdf(
    record: dict,
    tg_link: str = "",
    wa_link: str = "",
    logo_path: str = "",
    cover_path: str = "",
    channel: str = "",
) -> bytes:
    """Generate landscape license-style vehicle report (no cover image)."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    font, font_bold = _ensure_fonts()
    wltp = record.get("_wltp") or {}
    plate = _v(record, "mispar_rechev") or "—"
    make = _v(record, "tozeret_nm")
    model = _v(record, "kinuy_mishari", "degem_nm")
    degem = _v(record, "degem_nm")
    year = _v(record, "shnat_yitzur")
    merkav = _v(wltp, "merkav")
    now_str = datetime.now().strftime("%d/%m/%Y")
    tg_url = _full_url(tg_link)
    wa_url = _full_url(wa_link)
    ch = (channel or "").strip().lower()

    TA_RTL = TA_RIGHT
    bg = colors.Color(*C_BG)
    bar = colors.Color(*C_BAR)
    title_c = colors.Color(*C_TITLE)
    lbl_red = colors.Color(*C_LBL_RED)
    lbl_blue = colors.Color(*C_LBL_BLUE)
    val_c = colors.Color(*C_VAL)
    line_c = colors.Color(*C_LINE)
    white = colors.Color(*C_WHITE)

    def sty(name, *, size=9, bold=False, color=colors.black, align=TA_RTL, leading=None):
        return ParagraphStyle(
            name, fontName=font_bold if bold else font, fontSize=size,
            textColor=color, alignment=align, leading=leading or size * 1.35,
            wordWrap="CJK",
        )

    def _p(text: Any, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_t(text), style)

    s_title = sty("title", size=22, bold=True, color=title_c, align=TA_CENTER)
    s_ministry = sty("min", size=7.5, bold=True, color=bar, align=TA_RIGHT)
    s_sub = sty("sub", size=6.5, color=lbl_blue, align=TA_CENTER)
    s_bar_lbl = sty("bl", size=7, bold=True, color=white, align=TA_CENTER)
    s_bar_val = sty("bv", size=11, bold=True, color=white, align=TA_CENTER)
    s_lbl_r = sty("lr", size=6.5, bold=True, color=lbl_red, align=TA_RTL)
    s_lbl_b = sty("lb", size=6.5, bold=True, color=lbl_blue, align=TA_RTL)
    s_val = sty("val", size=9, bold=True, color=val_c, align=TA_RTL)
    s_val_sm = sty("vs", size=8, color=val_c, align=TA_RTL)
    s_note = sty("note", size=6.5, color=lbl_blue, align=TA_CENTER)
    s_alert = sty("alert", size=8.5, bold=True, color=colors.Color(*C_ALERT), align=TA_RTL)

    def _tbl(rows, colw, cmds):
        t = Table(rows, colWidths=colw)
        t.setStyle(TableStyle(cmds))
        return t

    def _dash_below():
        return ("LINEBELOW", (0, 0), (-1, -1), 0.4, line_c, None, (1, 2))

    def _field(label: str, value: str, *, red_label: bool = False, size: int = 9) -> Table:
        """License cell: value on top, label below (RTL)."""
        if not value:
            value = "—"
        vs = sty("v", size=size, bold=True, color=val_c, align=TA_RTL)
        ls = s_lbl_r if red_label else s_lbl_b
        return _tbl(
            [[_p(value, vs)], [_p(label, ls)]],
            [_USABLE_W],
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (0, 0), 3),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                _dash_below(),
            ],
        )

    def _field_col(label: str, value: str, width: float, *, red_label: bool = False) -> Table:
        if not value:
            value = "—"
        vs = sty("vc", size=9, bold=True, color=val_c, align=TA_RTL)
        ls = s_lbl_r if red_label else s_lbl_b
        return _tbl(
            [[_p(value, vs)], [_p(label, ls)]],
            [width],
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (0, 0), 3),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("LINEAFTER", (0, 0), (0, -1), 0.5, line_c),
                _dash_below(),
            ],
        )

    def _bar_cell(label: str, value: str, width: float) -> Table:
        return _tbl(
            [
                [_p("»", s_bar_lbl)],
                [_p(label, s_bar_lbl)],
                [_p(value, s_bar_val)],
            ],
            [width],
            [
                ("BACKGROUND", (0, 0), (-1, -1), bar),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (0, 0), 2),
                ("TOPPADDING", (0, 1), (0, 1), 1),
                ("BOTTOMPADDING", (0, 2), (0, 2), 6),
                ("LINEAFTER", (0, 0), (0, -1), 0.8, white),
            ],
        )

    def _license_row(cells: list[tuple[str, str, bool]], widths: list[float] | None = None) -> Table:
        """Multi-column row; cells = (label, value, red_label?)."""
        n = len(cells)
        if widths is None:
            widths = [_USABLE_W / n] * n
        parts = [
            _field_col(lbl, val, widths[i], red_label=red)
            for i, (lbl, val, red) in enumerate(cells)
        ]
        return _tbl(
            [parts],
            widths,
            [("VALIGN", (0, 0), (-1, -1), "TOP")],
        )

    def _page_decor(canv, doc):
        canv.saveState()
        canv.setFillColor(bg)
        canv.rect(0, _FOOTER_H, _PW, _PH - _FOOTER_H, fill=1, stroke=0)
        canv.setStrokeColor(colors.Color(*C_BAR))
        canv.setLineWidth(1)
        canv.rect(_MARGIN - 3, _FOOTER_H + 3, _USABLE_W + 6, _PH - _FOOTER_H - 6, fill=0, stroke=1)

        canv.setFillColor(colors.Color(*C_BAR_LT))
        canv.setFont(font, 5.5)
        canv.drawCentredString(_PW / 2, _FOOTER_H + 1.2 * _MM, _cb(f"CarInfo · {plate} · עמוד {canv.getPageNumber()}"))

        y_center = 5.5 * _MM
        btn_w, btn_h = 40 * _MM, 8 * _MM
        gap = 5 * _MM
        items: list[tuple[str, str, str, tuple]] = []
        if wa_url:
            items.append(("whatsapp", "וואטסאפ", wa_url, C_WA))
        if tg_url:
            items.append(("telegram", "טלגרם", tg_url, C_TG))
        if ch in ("telegram", "tg") and len(items) == 2:
            items.reverse()

        total_w = len(items) * btn_w + max(0, len(items) - 1) * gap
        x0 = (_PW - total_w) / 2
        for i, (kind, label, url, bgc) in enumerate(items):
            x = x0 + i * (btn_w + gap)
            canv.setFillColor(colors.Color(*bgc))
            canv.roundRect(x, y_center, btn_w, btn_h, 3, fill=1, stroke=0)
            canv.linkURL(url, (x, y_center, x + btn_w, y_center + btn_h), relative=0)
            r = 3 * _MM
            cx = x + 6 * _MM
            cy = y_center + btn_h / 2
            if kind == "telegram":
                canv.setFillColor(colors.Color(*C_TG))
                canv.circle(cx, cy, r, fill=1, stroke=0)
                canv.setFillColor(white)
                canv.circle(cx - 0.7 * _MM, cy, 0.8 * _MM, fill=1, stroke=0)
            else:
                canv.setFillColor(colors.Color(*C_WA))
                canv.circle(cx, cy, r, fill=1, stroke=0)
                canv.setFillColor(white)
                canv.circle(cx, cy, r * 0.5, fill=1, stroke=0)
            canv.setFillColor(white)
            canv.setFont(font_bold, 7.5)
            canv.drawString(x + 13 * _MM, y_center + 2.5 * _MM, _cb(label))

        canv.restoreState()

    # ── Data ──────────────────────────────────────────────────────────────────
    test_txt = _test_status(record.get("tokef_dt"))
    vtype = _vehicle_type(record, wltp)
    km_val = _v(record, "kilometer_test_aharon")
    km_date = _fd(record.get("mivchan_acharon_dt"))
    auto_ind = wltp.get("automatic_ind")
    gearbox = "אוטומטית" if str(auto_ind) == "1" else ("ידנית" if str(auto_ind) == "0" else "")
    nefah = _v(wltp, "nefah_manoa")
    pi = record.get("_personal_import")
    import_txt = (_v(pi, "sug_yevu") or "יבוא אישי") if pi else ""
    tozeret_full = _hebrew_join_parts(
        make, _v(wltp, "tozeret_eretz_nm"),
    )

    third = _USABLE_W / 3
    half = _USABLE_W / 2

    story: list = []

    # Header: ministry (right) | title (center) | note (left)
    story.append(_tbl(
        [
            [
                _p("CarInfo\nעותק מידע", sty("ci", size=6.5, color=lbl_blue, align=TA_RTL)),
                _p("רישיון רכב", s_title),
                _p("משרד התחבורה והבטיחות בדרכים\nמדינת ישראל", s_ministry),
            ],
        ],
        [55 * _MM, _USABLE_W - 110 * _MM, 55 * _MM],
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (0, 1), (0, 1), "CENTER"),
            ("ALIGN", (0, 2), (0, 2), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ],
    ))
    story.append(_p("תעודת נתוני רכב ממוחשבת — אינה מחליפה רישיון רכב רשמי", s_sub))
    story.append(Spacer(1, 4))

    # Blue bar: בתוקף עד | סוג | מספר רכב  (LTR columns → plate on right)
    story.append(_tbl(
        [
            [
                _bar_cell("בתוקף עד", test_txt, third),
                _bar_cell("סוג", vtype[:40], third),
                _bar_cell("מספר רכב", plate, third),
            ],
        ],
        [third, third, third],
        [("VALIGN", (0, 0), (-1, -1), "TOP")],
    ))

    if record.get("_scrapped_dt"):
        story.append(Spacer(1, 3))
        story.append(_tbl(
            [[_p(f"אזהרה: רכב בוטל · {_fd(record.get('_scrapped_dt'))}", s_alert)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 0.93, 0.93)),
                ("BOX", (0, 0), (-1, -1), 1, colors.Color(*C_ALERT)),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ],
        ))

    story.append(Spacer(1, 2))

    # Row: בעלות | מקוריות
    story.append(_license_row([
        ("סוג בעלות", _v(record, "baalut"), False),
        ("מקוריות", _v(record, "mkoriut_nm"), False),
    ], [half, half]))

    # Row: תאריך רישום | הדפסה | תוקף טסט
    story.append(_license_row([
        ("תאריך רישום", _fd(record.get("rishum_rishon_dt")), False),
        ("תאריך הדפסה", now_str, False),
        ("תוקף טסט", test_txt, False),
    ], [third, third, third]))

    # Full-width chassis (red label)
    story.append(_field("מספר שלדה", _v(record, "misgeret"), red_label=True, size=10))

    # Row: שנת ייצור | צבע | סוג דלק
    story.append(_license_row([
        ("שנת ייצור", year, False),
        ("צבע", _v(record, "tzeva_rechev"), False),
        ("סוג דלק", _v(record, "sug_delek_nm"), False),
    ], [third, third, third]))

    # Row: תוצר | דגם מסחרי | דגם יצרן
    story.append(_license_row([
        ("תוצר", make, False),
        ("דגם", model, False),
        ("דגם יצרן", degem, False),
    ], [third, third, third]))

    # Row: נפח | תיבה | מושבים
    story.append(_license_row([
        ("נפח", f'{nefah} סמ"ק' if nefah else "", False),
        ("תיבת הילוכים", gearbox, False),
        ("מקומות ישיבה", _v(wltp, "mispar_moshavim"), False),
    ], [third, third, third]))

    # Row: צמיגים | גרירה | הנעה
    heina = _v(wltp, "hanaa_nm") or _v(wltp, "hanaa_cd")
    story.append(_license_row([
        ("צמיג קדמי", _v(record, "zmig_kidmi"), False),
        ("צמיג אחורי", _v(record, "zmig_ahori"), False),
        ("הנעה", heina, False),
    ], [third, third, third]))

    # Row: משקל | כוח | ניקוד
    story.append(_license_row([
        ("משקל כולל", _v(wltp, "mishkal_kolel"), False),
        ("כוח סוס", _v(wltp, "koah_sus"), False),
        ("ניקוד בטיחות", _v(wltp, "nikud_betihut"), False),
    ], [third, third, third]))

    # Row: טסט | ק"מ | סטטוס
    km_line = f'{km_val} ק"מ' if km_val else ""
    if km_date and km_line:
        km_line = f"ב- {km_date}  {km_line}"
    story.append(_license_row([
        ("טסט אחרון", _fd(record.get("mivchan_acharon_dt")), False),
        ("קילומטראז' בטסט", km_line, False),
        ("סטטוס רישום", _inactive_txt(record), False),
    ], [third, third, third]))

    if import_txt:
        story.append(_license_row([
            ("יבוא", import_txt, False),
            ("עלייה לכביש", _v(record, "moed_aliya_lakvish"), False),
            ("שינוי מבנה", "כן" if str(record.get("shinui_mivne_ind")) == "1" else "לא", False),
        ], [third, third, third]))

    # Bottom strip (like license footer): תוצר | דגם | מרכב
    story.append(Spacer(1, 4))
    story.append(_tbl(
        [
            [
                _field_col("תוצר", tozeret_full or make, third, red_label=False),
                _field_col("דגם", degem or model, third),
                _field_col("מרכב", merkav, third),
            ],
        ],
        [third, third, third],
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*C_FOOT)),
            ("BOX", (0, 0), (-1, -1), 0.8, line_c),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ],
    ))

    ownership = record.get("_ownership") or []
    if ownership:
        own_lines = []
        for i, o in enumerate(ownership[:6], 1):
            dt_str = _fmt_baalut_dt(o.get("baalut_dt", ""))
            own_lines.append(f"{i}. {o.get('baalut', '—')} — {dt_str}")
        story.append(Spacer(1, 3))
        story.append(_field(f"בעלים קודמים ({len(ownership)})", "\n".join(own_lines), red_label=False, size=8))

    recalls = record.get("_recalls") or []
    if recalls:
        scope = "ללוחית" if record.get("_recalls_by_plate") else "לדגם"
        lines = []
        for r in recalls[:5]:
            teur = (r.get("TEUR_TAKALA") or "")[:85]
            if not teur:
                continue
            if record.get("_recalls_by_plate"):
                lines.append(f"• {_fd(r.get('TAARICH_PTICHA'))}: {teur}")
            else:
                lines.append(f"• {r.get('SHNAT_RECALL', '')}: {teur}")
        if lines:
            story.append(Spacer(1, 3))
            story.append(_field(f"ריקולים ({scope})", "\n".join(lines), size=8))

    try:
        from src.formatter import _km_fraud_check
        km_warn = _km_fraud_check(record)
        if km_warn:
            story.append(Spacer(1, 3))
            story.append(_tbl(
                [[_p(km_warn, s_alert)]],
                [_USABLE_W],
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 0.97, 0.90)),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.Color(*C_WARN)),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ],
            ))
    except Exception:
        pass

    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            age = date.today().year - int(year) if year else 0
            dep = min(age * 8, 70) if age > 0 else 0
            est = int(price_int * (1 - dep / 100))
            story.append(Spacer(1, 3))
            story.append(_license_row([
                ("מחיר יבואן", f"₪{price_int:,}", False),
                ("הערכה משוערת", f"₪{est:,}", False),
            ], [half, half]))
        except Exception:
            pass

    story.append(Spacer(1, 4))
    story.append(_p(
        "נתונים ממקורות ממשלתיים פתוחים · CarInfo",
        s_note,
    ))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=_PAGE,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN + _FOOTER_H,
    )
    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()


def _hebrew_join_parts(*parts: str, sep: str = " ") -> str:
    return sep.join(p for p in parts if p)
