"""
Hebrew PDF — Israeli vehicle-license style layout (reportlab + python-bidi).
"""

from __future__ import annotations

import io
import os
from datetime import date, datetime
from typing import Any

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
_MARGIN = 12 * _MM
_USABLE_W = 186 * _MM
_FOOTER_H = 20 * _MM

# Israeli license-inspired palette
C_PAPER = (0.98, 0.94, 0.88)
C_PAPER_DARK = (0.94, 0.88, 0.78)
C_MINISTRY = (0.05, 0.15, 0.38)
C_MINISTRY_LT = (0.12, 0.28, 0.52)
C_PLATE_YELLOW = (1.0, 0.92, 0.35)
C_PLATE_BORDER = (0.15, 0.15, 0.15)
C_FIELD_LBL = (0.20, 0.28, 0.42)
C_FIELD_BG = (1.0, 1.0, 1.0)
C_FIELD_BD = (0.55, 0.60, 0.68)
C_ALERT = (0.75, 0.12, 0.12)
C_OK = (0.05, 0.45, 0.28)
C_WARN = (0.55, 0.35, 0.05)
C_TG = (0.16, 0.52, 0.78)
C_WA = (0.15, 0.68, 0.38)
_LINK_TG = "#2AABEE"
_LINK_WA = "#25D366"


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


def _b(text: Any) -> str:
    s = str(text) if text is not None else ""
    try:
        from bidi.algorithm import get_display
        return get_display(s)
    except Exception:
        return s


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


def _test_status(tokef_raw: Any) -> tuple[str, str]:
    if not tokef_raw:
        return "לא ידוע", "#64748B"
    try:
        tokef = date.fromisoformat(str(tokef_raw)[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"פג תוקף · {abs(delta)} ימים", "#DC2626"
        if delta <= 30:
            return f"בתוקף · {delta} ימים", "#D97706"
        return f"בתוקף · {tokef.strftime('%d/%m/%Y')}", "#059669"
    except Exception:
        return "לא ידוע", "#64748B"


def _hebrew_join(*parts: str, sep: str = " · ") -> str:
    return _b(sep.join(p for p in parts if p))


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


def _icon_png_bytes(kind: str, size: int = 28) -> bytes:
    """Minimal brand-colour icons (Telegram / WhatsApp) as PNG bytes."""
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
        d.chord(
            [size * 0.30, size * 0.30, size * 0.78, size * 0.78],
            200, 340, fill=(37, 211, 102, 255),
        )
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
    """Generate license-style vehicle report PDF (no cover image)."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        Flowable,
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
    year = _v(record, "shnat_yitzur")
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    tg_url = _full_url(tg_link)
    wa_url = _full_url(wa_link)
    ch = (channel or "").strip().lower()

    TA_RTL = TA_RIGHT
    paper = colors.Color(*C_PAPER)
    ministry = colors.Color(*C_MINISTRY)
    ministry_lt = colors.Color(*C_MINISTRY_LT)
    plate_yellow = colors.Color(*C_PLATE_YELLOW)
    lbl_c = colors.Color(*C_FIELD_LBL)
    field_bd = colors.Color(*C_FIELD_BD)
    white = colors.Color(1, 1, 1)

    def sty(name, *, size=9, bold=False, color=colors.black, align=TA_RTL, leading=None):
        return ParagraphStyle(
            name, fontName=font_bold if bold else font, fontSize=size,
            textColor=color, alignment=align, leading=leading or size * 1.4,
            wordWrap="CJK",
        )

    def _p(text: Any, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_b(text), style)

    s_hdr = sty("hdr", size=11, bold=True, color=white, align=TA_CENTER)
    s_hdr_sub = sty("hdrs", size=8, color=colors.Color(0.85, 0.90, 0.95), align=TA_CENTER)
    s_plate = sty("plate", size=26, bold=True, color=colors.Color(*C_PLATE_BORDER), align=TA_CENTER)
    s_sec = sty("sec", size=9, bold=True, color=ministry, align=TA_RTL)
    s_lbl = sty("lbl", size=7.5, bold=True, color=lbl_c, align=TA_RTL)
    s_val = sty("val", size=9, color=colors.Color(0.1, 0.1, 0.12), align=TA_RTL)
    s_val_sm = sty("vals", size=8, color=colors.Color(0.2, 0.2, 0.25), align=TA_RTL)
    s_note = sty("note", size=7, color=lbl_c, align=TA_CENTER)
    s_alert = sty("alert", size=9, bold=True, color=colors.Color(*C_ALERT), align=TA_RTL)

    def _tbl(rows, colw, cmds):
        t = Table(rows, colWidths=colw)
        t.setStyle(TableStyle(cmds))
        return t

    def _section_bar(title: str) -> Table:
        return _tbl(
            [[_p(title, s_sec)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), ministry_lt),
                ("TEXTCOLOR", (0, 0), (-1, -1), white),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ],
        )

    def _field_grid(pairs: list[tuple[str, str]], cols: int = 2) -> Table | None:
        """License-style: [value | label] cells in a 2-column grid."""
        cells: list[tuple[str, str]] = [(l, v) for l, v in pairs if v]
        if not cells:
            return None
        lbl_w = 38 * _MM
        val_w = (_USABLE_W / cols) - lbl_w - 4
        rows = []
        row_buf: list = []
        for i, (label, value) in enumerate(cells):
            cell = _tbl(
                [[_p(value, s_val)], [_p(label, s_lbl)]],
                [val_w, lbl_w],
                [
                    ("BACKGROUND", (0, 0), (0, 0), white),
                    ("BACKGROUND", (1, 0), (1, 0), colors.Color(*C_PAPER_DARK)),
                    ("BOX", (0, 0), (0, 0), 0.6, field_bd),
                    ("BOX", (1, 0), (1, 0), 0.4, field_bd),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("RIGHTPADDING", (0, 0), (0, 0), 6),
                    ("LEFTPADDING", (0, 0), (0, 0), 4),
                    ("RIGHTPADDING", (1, 0), (1, 0), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ],
            )
            row_buf.append(cell)
            if len(row_buf) == cols:
                rows.append(row_buf)
                row_buf = []
        if row_buf:
            while len(row_buf) < cols:
                row_buf.append("")
            rows.append(row_buf)
        cw = _USABLE_W / cols
        return _tbl(rows, [cw] * cols, [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])

    def _license_header() -> list:
        hdr = _tbl(
            [
                [_p("מדינת ישראל", s_hdr)],
                [_p("משרד התחבורה והבטיחות בדרכים", s_hdr)],
                [_p("תעודת נתוני רכב — עותק מידע ממוחשב", s_hdr)],
                [_p("CarInfo · לא מחליף רישיון רכב רשמי", s_hdr_sub)],
            ],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), ministry),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )
        plate_box = _tbl(
            [[_p(plate, s_plate)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), plate_yellow),
                ("BOX", (0, 0), (-1, -1), 2.5, colors.Color(*C_PLATE_BORDER)),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ],
        )
        vehicle = _hebrew_join(
            f"שנת {year}" if year else "", model, make,
        ) if (make or model or year) else "—"
        meta = _tbl(
            [
                [_p(vehicle, sty("vm", size=10, bold=True, color=ministry, align=TA_CENTER))],
                [_p(f"הופק: {now_str}", s_note)],
            ],
            [_USABLE_W],
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        )
        return [hdr, Spacer(1, 6), plate_box, meta]

    def _social_footer_flowable() -> Flowable | None:
        if not tg_url and not wa_url:
            return None

        from reportlab.platypus import Image as RLImage

        icon_sz = 9 * _MM
        btn_h = 11 * _MM

        def _social_btn(kind: str, label: str, url: str, bg: tuple) -> Table:
            png = _icon_png_bytes(kind, 56)
            icon_cell: Any = ""
            if png:
                try:
                    icon_cell = RLImage(io.BytesIO(png), width=icon_sz, height=icon_sz)
                except Exception:
                    icon_cell = ""
            label_p = Paragraph(
                f'<a href="{url}"><b><font color="#FFFFFF">{_b(label)}</font></b></a>',
                sty("soc", size=10, bold=True, color=white, align=TA_CENTER),
            )
            inner = _tbl(
                [[icon_cell, label_p]],
                [icon_sz + 4, 45 * _MM],
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*bg)),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.Color(*bg)),
                ],
            )
            return inner

        btns: list[Any] = []
        order: list[tuple[str, str, str, tuple, bool]] = []
        if tg_url:
            order.append(("telegram", "טלגרם", tg_url, C_TG, ch in ("telegram", "tg", "")))
        if wa_url:
            order.append(("whatsapp", "וואטסאפ", wa_url, C_WA, ch in ("whatsapp", "wa", "")))
        order.sort(key=lambda x: 0 if x[4] else 1)
        for kind, label, url, bg, _ in order:
            btns.append(_social_btn(kind, label, url, bg))

        if len(btns) == 1:
            row = _tbl([[btns[0]]], [_USABLE_W], [("ALIGN", (0, 0), (-1, -1), "CENTER")])
        else:
            half = _USABLE_W / 2 - 3
            row = _tbl([btns], [half, half], [("VALIGN", (0, 0), (-1, -1), "MIDDLE")])

        hint = _p("לחיצה על האייקון פותחת את הבוט", s_note)
        return _tbl(
            [[hint], [row]],
            [_USABLE_W],
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (1, 0), (1, 0), 2),
            ],
        )

    # ── Page canvas: paper + frame + footer ───────────────────────────────────
    def _page_decor(canv, doc):
        canv.saveState()
        pw, ph = A4
        canv.setFillColor(paper)
        canv.rect(0, _FOOTER_H, pw, ph - _FOOTER_H, fill=1, stroke=0)
        canv.setStrokeColor(ministry)
        canv.setLineWidth(1.2)
        canv.rect(_MARGIN - 2, _FOOTER_H + 4, pw - 2 * _MARGIN + 4, ph - _FOOTER_H - 8, fill=0, stroke=1)
        canv.setLineWidth(0.5)
        canv.setStrokeColor(ministry_lt)
        canv.rect(_MARGIN + 2, _FOOTER_H + 8, pw - 2 * _MARGIN - 4, ph - _FOOTER_H - 16, fill=0, stroke=1)

        canv.setFillColor(ministry_lt)
        canv.setFont(font, 6)
        canv.drawCentredString(pw / 2, _FOOTER_H + 1.5 * _MM, _b(f"CarInfo · {plate} · עמוד {canv.getPageNumber()}"))

        y_center = 6 * _MM
        btn_w, btn_h = 42 * _MM, 9 * _MM
        gap = 6 * _MM
        items: list[tuple[str, str, str, tuple]] = []
        if wa_url:
            items.append(("whatsapp", "וואטסאפ", wa_url, C_WA))
        if tg_url:
            items.append(("telegram", "טלגרם", tg_url, C_TG))
        if ch in ("telegram", "tg") and len(items) == 2:
            items.reverse()

        total_w = len(items) * btn_w + max(0, len(items) - 1) * gap
        x0 = (pw - total_w) / 2
        for i, (kind, label, url, bg) in enumerate(items):
            x = x0 + i * (btn_w + gap)
            canv.setFillColor(colors.Color(*bg))
            canv.roundRect(x, y_center, btn_w, btn_h, 4, fill=1, stroke=0)
            canv.linkURL(url, (x, y_center, x + btn_w, y_center + btn_h), relative=0)
            r = 3.5 * _MM
            cx = x + 7 * _MM
            cy = y_center + btn_h / 2
            if kind == "telegram":
                canv.setFillColor(colors.Color(0.16, 0.52, 0.78))
                canv.circle(cx, cy, r, fill=1, stroke=0)
                canv.setFillColor(white)
                canv.circle(cx - 0.8 * _MM, cy, 0.9 * _MM, fill=1, stroke=0)
            else:
                canv.setFillColor(colors.Color(0.15, 0.68, 0.38))
                canv.circle(cx, cy, r, fill=1, stroke=0)
                canv.setFillColor(white)
                canv.circle(cx, cy, r * 0.55, fill=1, stroke=0)
            canv.setFillColor(white)
            canv.setFont(font_bold, 8)
            canv.drawString(x + 14 * _MM, y_center + 3 * _MM, _b(label))

        canv.restoreState()

    # ── Build story ───────────────────────────────────────────────────────────
    test_txt, _ = _test_status(record.get("tokef_dt"))
    pi = record.get("_personal_import")
    import_txt = (_v(pi, "sug_yevu") or "יבוא אישי") if pi else ""
    km_val = _v(record, "kilometer_test_aharon")
    auto_ind = wltp.get("automatic_ind")
    gearbox = "אוטומטית" if str(auto_ind) == "1" else ("ידנית" if str(auto_ind) == "0" else "")

    story: list = []
    story.extend(_license_header())
    story.append(Spacer(1, 8))

    if record.get("_scrapped_dt"):
        story.append(_tbl(
            [[_p(f"אזהרה: רכב בוטל רשמית · {_fd(record.get('_scrapped_dt'))}", s_alert)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 0.92, 0.92)),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.Color(*C_ALERT)),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        ))
        story.append(Spacer(1, 6))

    identity = [
        ("מספר רכב", plate),
        ("מספר שלדה", _v(record, "misgeret")),
        ("יצרן", make),
        ("דגם מסחרי", model),
        ("דגם יצרן", _v(record, "degem_nm")),
        ("שנת ייצור", year),
        ("צבע", _v(record, "tzeva_rechev")),
        ("סוג דלק", _v(record, "sug_delek_nm")),
        ("בעלות", _v(record, "baalut")),
        ("יבוא", import_txt if pi else ""),
        ("ארץ ייצור", _v(wltp, "tozeret_eretz_nm")),
    ]
    story.append(_section_bar("פרטי זיהוי הרכב"))
    g = _field_grid(identity, 2)
    if g:
        story.append(g)

    tests = [
        ("תוקף טסט", test_txt),
        ("טסט אחרון", _fd(record.get("mivchan_acharon_dt"))),
        ("רישום ראשון", _fd(record.get("rishum_rishon_dt"))),
        ("עלייה לכביש", _v(record, "moed_aliya_lakvish")),
        ("ק\"מ בטסט", f"{km_val} ק\"מ" if km_val else ""),
        ("סטטוס רישום", _inactive_txt(record)),
        ("מקוריות", _v(record, "mkoriut_nm")),
        ("שינוי מבנה", "כן" if str(record.get("shinui_mivne_ind")) == "1" else "לא"),
        ("שינוי צבע", "כן" if str(record.get("shnui_zeva_ind")) == "1" else "לא"),
    ]
    story.append(Spacer(1, 4))
    story.append(_section_bar("רישום · בדיקות · טסט"))
    g = _field_grid(tests, 2)
    if g:
        story.append(g)

    specs = [
        ("נפח מנוע", f"{_v(wltp, 'nefah_manoa')} סמ\"ק" if _v(wltp, "nefah_manoa") else ""),
        ("כוח סוס", _v(wltp, "koah_sus")),
        ("תיבה", gearbox),
        ("מושבים", _v(wltp, "mispar_moshavim")),
        ("צמיג קדמי", _v(record, "zmig_kidmi")),
        ("צמיג אחורי", _v(record, "zmig_ahori")),
        ("וו גרירה", _v(record, "grira_nm")),
        ("ניקוד בטיחות", _v(wltp, "nikud_betihut")),
    ]
    story.append(Spacer(1, 4))
    story.append(_section_bar("מפרט טכני"))
    g = _field_grid(specs, 2)
    if g:
        story.append(g)

    ownership = record.get("_ownership") or []
    if ownership:
        own_lines = []
        for i, o in enumerate(ownership, 1):
            dt_str = _fmt_baalut_dt(o.get("baalut_dt", ""))
            baalut_type = o.get("baalut", "לא ידוע")
            own_lines.append(f"{i}. {baalut_type} — {dt_str}")
        story.append(Spacer(1, 4))
        story.append(_section_bar(f"היסטוריית בעלויות ({len(ownership)})"))
        story.append(_tbl(
            [[_p("\n".join(own_lines), s_val_sm)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), white),
                ("BOX", (0, 0), (-1, -1), 0.6, field_bd),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ],
        ))

    recalls = record.get("_recalls") or []
    if recalls:
        scope = "ללוחית" if record.get("_recalls_by_plate") else "לדגם"
        recall_txt = []
        for r in recalls[:8]:
            if record.get("_recalls_by_plate"):
                teur = r.get("TEUR_TAKALA", "")
                taarich = str(r.get("TAARICH_PTICHA", ""))[:10]
                if teur:
                    recall_txt.append(f"• {taarich}: {teur[:90]}")
            else:
                teur = r.get("TEUR_TAKALA", "")
                shnat = r.get("SHNAT_RECALL", "")
                if teur:
                    recall_txt.append(f"• {shnat}: {teur[:90]}")
        if recall_txt:
            story.append(Spacer(1, 4))
            story.append(_section_bar(f"ריקולים ({scope})"))
            story.append(_tbl(
                [[_p("\n".join(recall_txt), s_val_sm)]],
                [_USABLE_W],
                [
                    ("BACKGROUND", (0, 0), (-1, -1), white),
                    ("BOX", (0, 0), (-1, -1), 0.6, field_bd),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ],
            ))

    try:
        from src.formatter import _km_fraud_check
        import re as _re
        km_warn = _km_fraud_check(record)
        if km_warn:
            plain = _re.sub(r"\\([\\!\"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~])", r"\1", km_warn)
            story.append(Spacer(1, 4))
            story.append(_tbl(
                [[_p(f"⚠ {plain}", s_alert)]],
                [_USABLE_W],
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1, 0.97, 0.90)),
                    ("BOX", (0, 0), (-1, -1), 1, colors.Color(*C_WARN)),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ],
            ))
    except Exception:
        pass

    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            age = date.today().year - int(year) if year else 0
            dep_pct = min(age * 8, 70) if age > 0 else 0
            est_val = int(price_int * (1 - dep_pct / 100))
            story.append(Spacer(1, 4))
            story.append(_section_bar("שווי ומחיר"))
            g = _field_grid([
                ("מחיר יבואן", f"₪{price_int:,}"),
                ("הערכה משוערת", f"₪{est_val:,}"),
            ], 2)
            if g:
                story.append(g)
        except Exception:
            pass

    story.append(Spacer(1, 6))
    story.append(_p(
        "נתונים ממקורות ממשלתיים פתוחים · ללא תחליף לבדיקה מקצועית או רישיון רשמי",
        s_note,
    ))

    soc = _social_footer_flowable()
    if soc:
        story.append(Spacer(1, 8))
        story.append(soc)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN + _FOOTER_H,
    )
    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()
