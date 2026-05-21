"""
Hebrew PDF report generator for vehicle data.
Premium automotive layout: reportlab + python-bidi (RTL).
Redesigned with license-document aesthetics, clear hierarchy, generous spacing.
"""

from __future__ import annotations

import io
import os
from datetime import date, datetime
from typing import Any

# ── Fonts ─────────────────────────────────────────────────────────────────────
_font_registered = False
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


def _ensure_fonts() -> tuple[str, str]:
    global _font_registered
    if _font_registered:
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

    _font_registered = True
    return regular, bold


def _b(text: Any) -> str:
    """BiDi reshape for RTL Hebrew in ReportLab."""
    s = str(text) if text is not None else ""
    try:
        from bidi.algorithm import get_display
        return get_display(s)
    except Exception:
        return s


def _hebrew_join(*parts: str, sep: str = " · ") -> str:
    return _b(sep.join(p for p in parts if p))


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


def _test_status(tokef_raw: Any) -> tuple[str, str, str]:
    if not tokef_raw:
        return "לא ידוע", "#64748B", "—"
    try:
        tokef = date.fromisoformat(str(tokef_raw)[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"פג תוקף · {abs(delta)} ימים", "#DC2626", "פג תוקף"
        if delta <= 30:
            return f"עומד לפוג · {delta} ימים", "#D97706", "דחוף"
        return f"בתוקף · {tokef.strftime('%d/%m/%Y')}", "#059669", "בתוקף"
    except Exception:
        return "לא ידוע", "#64748B", "—"


def _full_url(link: str) -> str:
    s = (link or "").strip()
    if not s:
        return ""
    if s.startswith(("http://", "https://")):
        return s
    return f"https://{s.lstrip('/')}"


# ── Layout constants ───────────────────────────────────────────────────────────
_MM = 2.8346456692913385
_MARGIN = 16 * _MM
_USABLE_W = 163 * _MM   # A4 210mm − 2×16mm margin ≈ 178mm, slight inset for elegance
_COL_LABEL = 52 * _MM
_COL_VALUE = _USABLE_W - _COL_LABEL

# ── Design tokens (RGB 0–1) ────────────────────────────────────────────────────
# Primary
C_NAVY       = (0.04, 0.09, 0.20)   # #0A1733 — deep navy
C_NAVY_CARD  = (0.08, 0.14, 0.30)   # #142650 — slightly lighter navy for card headers
C_NAVY_SOFT  = (0.12, 0.20, 0.40)   # #1F3366

# Accent
C_GOLD       = (0.83, 0.64, 0.13)   # #D4A321 — classic gold
C_GOLD_LIGHT = (0.95, 0.85, 0.55)   # #F2D98C — soft gold tint
C_GOLD_BG    = (0.99, 0.97, 0.90)   # #FCF8E5 — warm cream

# Neutrals
C_WHITE      = (1.00, 1.00, 1.00)
C_OFF_WHITE  = (0.97, 0.98, 1.00)   # #F7F8FF
C_SURFACE    = (0.95, 0.96, 0.98)   # #F2F4FA — card surface
C_ROW_ALT   = (0.92, 0.94, 0.97)   # #EBEFF8
C_BORDER     = (0.80, 0.84, 0.91)   # #CCD6E8
C_BORDER_SOFT = (0.88, 0.91, 0.96) # #E0E8F5

# Text
C_TEXT_BODY  = (0.12, 0.16, 0.26)   # #1F2942
C_TEXT_MUTED = (0.44, 0.50, 0.60)   # #708099
C_TEXT_LIGHT = (0.65, 0.70, 0.80)   # #A6B3CC

# Status
C_GREEN      = (0.04, 0.59, 0.42)   # #0A9669
C_GREEN_BG   = (0.90, 0.98, 0.94)   # #E6FAF0
C_RED        = (0.84, 0.16, 0.16)   # #D62929
C_RED_BG     = (0.99, 0.92, 0.92)   # #FCEBEB
C_AMBER      = (0.85, 0.53, 0.05)   # #D9870D
C_AMBER_BG   = (1.00, 0.96, 0.88)   # #FFF5E0

_LINK_BLUE   = "#1D4ED8"


def generate_pdf(
    record: dict,
    tg_link: str = "",
    wa_link: str = "",
    logo_path: str = "",
    cover_path: str = "",
    channel: str = "",
    car_image_url: str = "",
) -> bytes:
    """Generate a premium Hebrew vehicle-report PDF."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        Flowable,
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    TA_RTL = TA_RIGHT

    root = os.path.dirname(os.path.dirname(__file__))
    if not logo_path:
        for c in (os.path.join(root, "logo.png"), os.path.join(root, "logo.jpg")):
            if os.path.exists(c):
                logo_path = c
                break
    if not cover_path:
        for c in (os.path.join(root, "cover.png"), os.path.join(root, "cover.jpg")):
            if os.path.exists(c):
                cover_path = c
                break

    font, font_bold = _ensure_fonts()

    wltp      = record.get("_wltp") or {}
    plate     = _v(record, "mispar_rechev") or "—"
    make      = _v(record, "tozeret_nm")
    model     = _v(record, "kinuy_mishari", "degem_nm")
    year      = _v(record, "shnat_yitzur")
    now_str   = datetime.now().strftime("%d/%m/%Y %H:%M")
    tg_url    = _full_url(tg_link)
    wa_url    = _full_url(wa_link)

    # ── Color objects ──────────────────────────────────────────────────────────
    def _c(*rgb): return colors.Color(*rgb)

    navy       = _c(*C_NAVY)
    navy_card  = _c(*C_NAVY_CARD)
    navy_soft  = _c(*C_NAVY_SOFT)
    gold       = _c(*C_GOLD)
    gold_light = _c(*C_GOLD_LIGHT)
    gold_bg    = _c(*C_GOLD_BG)
    white      = colors.white
    off_white  = _c(*C_OFF_WHITE)
    surface    = _c(*C_SURFACE)
    row_alt    = _c(*C_ROW_ALT)
    border     = _c(*C_BORDER)
    border_soft = _c(*C_BORDER_SOFT)
    text_body  = _c(*C_TEXT_BODY)
    text_muted = _c(*C_TEXT_MUTED)
    text_light = _c(*C_TEXT_LIGHT)
    green      = _c(*C_GREEN)
    green_bg   = _c(*C_GREEN_BG)
    red        = _c(*C_RED)
    red_bg     = _c(*C_RED_BG)
    amber      = _c(*C_AMBER)
    amber_bg   = _c(*C_AMBER_BG)

    # ── Style factory ──────────────────────────────────────────────────────────
    def sty(name, *, size=10, bold=False, color=None, align=TA_RTL, leading=None, space_before=0, space_after=0):
        return ParagraphStyle(
            name,
            fontName=font_bold if bold else font,
            fontSize=size,
            textColor=color or text_body,
            alignment=align,
            leading=leading or round(size * 1.5),
            wordWrap="CJK",
            spaceBefore=space_before,
            spaceAfter=space_after,
        )

    def _p(text: Any, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_b(text), style)

    # Typography scale
    s_hero_brand  = sty("hero_brand",  size=20, bold=True,  color=gold,       align=TA_CENTER, leading=24)
    s_hero_sub    = sty("hero_sub",    size=9,  bold=False, color=_c(0.70, 0.78, 0.92), align=TA_CENTER)
    s_hero_date   = sty("hero_date",   size=7,  bold=False, color=_c(0.50, 0.60, 0.78), align=TA_CENTER)
    s_plate_num   = sty("plate_num",   size=28, bold=True,  color=navy,       align=TA_CENTER, leading=34)
    s_plate_label = sty("plate_lbl",   size=7,  bold=False, color=text_muted, align=TA_CENTER)
    s_plate_sub   = sty("plate_sub",   size=10, bold=False, color=navy_soft,  align=TA_CENTER)
    s_sec_title   = sty("sec_title",   size=10, bold=True,  color=navy,       align=TA_RTL,    leading=13)
    s_lbl         = sty("lbl",         size=8,  bold=False, color=text_muted, align=TA_RTL)
    s_val         = sty("val",         size=9.5,bold=False, color=text_body,  align=TA_RTL,    leading=13)
    s_val_bold    = sty("val_bold",    size=10, bold=True,  color=navy,       align=TA_RTL,    leading=14)
    s_stat_lbl    = sty("stat_lbl",    size=7,  bold=False, color=text_muted, align=TA_RTL)
    s_stat_val    = sty("stat_val",    size=11, bold=True,  color=navy,       align=TA_RTL,    leading=14)
    s_badge_ok    = sty("badge_ok",    size=8,  bold=True,  color=green,      align=TA_CENTER)
    s_badge_warn  = sty("badge_warn",  size=8,  bold=True,  color=amber,      align=TA_CENTER)
    s_badge_err   = sty("badge_err",   size=8,  bold=True,  color=red,        align=TA_CENTER)
    s_alert       = sty("alert",       size=9,  bold=True,  color=red,        align=TA_RTL)
    s_warn        = sty("warn",        size=8.5,bold=False, color=_c(0.45, 0.28, 0.02), align=TA_RTL)
    s_price_main  = sty("price_main",  size=14, bold=True,  color=navy,       align=TA_RTL,    leading=18)
    s_price_sub   = sty("price_sub",   size=9,  bold=False, color=text_muted, align=TA_RTL)
    s_footer_txt  = sty("footer_txt",  size=6.5,bold=False, color=text_muted, align=TA_CENTER)
    s_disc        = sty("disc",        size=7.5,bold=False, color=text_light, align=TA_RTL)
    s_cta_title   = sty("cta_t",       size=10.5,bold=True, color=white,      align=TA_CENTER)
    s_cta_hint    = sty("cta_h",       size=8,  bold=False, color=navy,       align=TA_CENTER)
    s_cta_sub     = sty("cta_s",       size=6.5,bold=False, color=text_muted, align=TA_CENTER)
    s_own_idx     = sty("own_idx",     size=9,  bold=True,  color=white,      align=TA_CENTER)
    s_own_type    = sty("own_type",    size=9,  bold=False, color=text_body,  align=TA_RTL)
    s_own_date    = sty("own_date",    size=8.5,bold=False, color=text_muted, align=TA_RTL)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _tbl(rows, colw, style_cmds):
        t = Table(rows, colWidths=colw)
        t.setStyle(TableStyle(style_cmds))
        return t

    def _hr(color=border, thickness=0.5, space=4):
        return HRFlowable(width=_USABLE_W, thickness=thickness, color=color,
                          spaceBefore=space, spaceAfter=space)

    def _sp(h=8):
        return Spacer(1, h)

    # ── Page chrome ────────────────────────────────────────────────────────────
    def _page_bg(canv, doc):
        canv.saveState()
        pw, ph = A4

        # Top accent bar — thin gold stripe
        canv.setFillColor(navy)
        canv.rect(0, ph - 5 * _MM, pw, 5 * _MM, fill=1, stroke=0)
        canv.setFillColor(gold)
        canv.rect(0, ph - 5.8 * _MM, pw, 0.8 * _MM, fill=1, stroke=0)

        # Bottom footer band
        canv.setFillColor(off_white)
        canv.rect(0, 0, pw, 10 * _MM, fill=1, stroke=0)
        canv.setStrokeColor(border)
        canv.setLineWidth(0.4)
        canv.line(_MARGIN, 10 * _MM, pw - _MARGIN, 10 * _MM)
        canv.setFillColor(text_muted)
        canv.setFont(font, 6.5)
        footer_txt = _b(f"CarInfo · דוח רכב {plate} · {now_str} · עמוד {canv.getPageNumber()}")
        canv.drawCentredString(pw / 2, 3.5 * _MM, footer_txt)
        canv.restoreState()

    # ── Hero header ────────────────────────────────────────────────────────────
    def _hero_header():
        """Full-width branded hero with centered plate card."""
        # Build vehicle line for RTL display.
        # BiDi logical order for a right-to-left line is: rightmost token first.
        # Desired visual: "טויוטה · COROLLA CROSS · 2025"  (right→left)
        # Logical RTL input to get_display: [make, model, year] — Hebrew anchor on right.
        vehicle_parts = [p for p in [make, model, year] if p]
        # Join in logical RTL order and let get_display produce the correct visual string.
        vehicle_line = _b(" · ".join(vehicle_parts))

        # "CARINFO" — pure Latin, no BiDi
        brand_p = Paragraph("CARINFO", s_hero_brand)
        # Hebrew-only strings — safe with _b()
        title_p = Paragraph(_b("דוח בדיקת רכב מקיף"), s_hero_sub)
        # Mixed "הופק: DD/MM/YYYY HH:MM" — draw the Hebrew label separately to avoid reorder
        date_p  = Paragraph(_b(f"הופק: {now_str}"), s_hero_date)

        header_band = _build_hero_band(brand_p, title_p, date_p)

        # Gold divider
        gold_bar = _tbl([[""]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), gold),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ])

        plate_card = _license_plate_card(plate, vehicle_line)
        return [header_band, gold_bar, _sp(14), plate_card]

    def _build_hero_band(brand_p, title_p, date_p):
        """Full-width centered hero band — no logo."""
        return _tbl(
            [[brand_p], [title_p], [date_p]],
            [_USABLE_W],
            [
                ("BACKGROUND",    (0, 0), (-1, -1), navy),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING",    (0, 0), (0, 0),   18),
                ("TOPPADDING",    (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
            ],
        )

    def _license_plate_card(plate_num: str, vehicle_line: str):
        """
        Centered card styled like an Israeli license plate document.
        White bg, navy text, gold border. Vehicle line is plain text (no BiDi
        reorder) so mixed Latin/Hebrew stays in natural reading order.
        """
        card_w   = 110 * _MM
        side_pad = (_USABLE_W - card_w) / 2

        label_p   = Paragraph(_b("מספר רכב"), s_plate_label)
        # Plate number is digits only — no BiDi needed
        plate_p   = Paragraph(str(plate_num), s_plate_num)
        # vehicle_line already passed through _b() — use Paragraph directly
        vehicle_p = Paragraph(vehicle_line, s_plate_sub) if vehicle_line else None

        inner_rows = [[label_p], [plate_p]]
        if vehicle_p:
            inner_rows.append([vehicle_p])

        inner_cmds = [
            ("BACKGROUND",    (0, 0), (-1, -1), colors.white),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (0, 0),   8),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ]
        inner = _tbl(inner_rows, [card_w], inner_cmds)

        plate_card = _tbl(
            [["", inner, ""]],
            [side_pad, card_w, side_pad],
            [
                ("BACKGROUND",    (1, 0), (1, 0), colors.white),
                ("BOX",           (1, 0), (1, 0), 2.5, gold),
                ("LINEBELOW",     (1, 0), (1, 0), 4,   gold),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (1, 0), (1, 0), 0),
                ("BOTTOMPADDING", (1, 0), (1, 0), 0),
                ("LEFTPADDING",   (1, 0), (1, 0), 0),
                ("RIGHTPADDING",  (1, 0), (1, 0), 0),
            ],
        )
        return plate_card

    # ── Cover image (static) ───────────────────────────────────────────────────
    def _cover_image():
        if not cover_path:
            return None
        try:
            from reportlab.platypus import Image as RLImage
            try:
                from PIL import Image as PILImage
                with PILImage.open(cover_path) as im:
                    pw, ph = im.size
                h = min(_USABLE_W * ph / pw, 52 * _MM)
            except ImportError:
                h = 44 * _MM
            return RLImage(cover_path, width=_USABLE_W, height=h)
        except Exception:
            return None

    # ── Car model image (fetched by URL) ──────────────────────────────────────
    def _car_image_flowable():
        """Download car_image_url and embed as an inline image below the plate card."""
        if not car_image_url:
            return None
        try:
            import io as _io
            import httpx as _httpx
            from reportlab.platypus import Image as RLImage
            _dl_headers = {"User-Agent": "CarInfoBot/1.0 (contact: gal9amar@gmail.com)"}
            resp = _httpx.get(car_image_url, timeout=15, follow_redirects=True, headers=_dl_headers)
            resp.raise_for_status()
            img_data = _io.BytesIO(resp.content)
            try:
                from PIL import Image as PILImage
                with PILImage.open(_io.BytesIO(resp.content)) as im:
                    iw, ih = im.size
                max_h = 55 * _MM
                scale = min(_USABLE_W / iw, max_h / ih)
                disp_w = iw * scale
                disp_h = ih * scale
            except ImportError:
                disp_w, disp_h = _USABLE_W, 44 * _MM
            img = RLImage(img_data, width=disp_w, height=disp_h)
            # Center the image using a single-cell table
            return _tbl([[img]], [_USABLE_W], [
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        except Exception:
            return None

    # ── Stat cards ─────────────────────────────────────────────────────────────
    def _stat_cards():
        test_txt, test_hex, badge = _test_status(record.get("tokef_dt"))
        n_own = len(record.get("_ownership") or [])
        fuel  = _v(record, "sug_delek_nm") or "—"

        test_color = {"#059669": green, "#D97706": amber, "#DC2626": red}.get(test_hex, text_muted)
        test_bg    = {"#059669": green_bg, "#D97706": amber_bg, "#DC2626": red_bg}.get(test_hex, surface)

        _card_counter = [0]

        def _card(label: str, value: Any, value_color=None, bg_color=None, sub: str = ""):
            _card_counter[0] += 1
            uid = _card_counter[0]
            vc = value_color or navy
            bc = bg_color or surface
            val_sty = ParagraphStyle(
                f"card_v_{uid}", fontName=font_bold, fontSize=12, textColor=vc,
                alignment=TA_RTL, leading=15, wordWrap="CJK",
            )
            val_p = Paragraph(_b(str(value)), val_sty)
            lbl_p = _p(label, s_stat_lbl)
            rows = [[lbl_p], [val_p]]
            if sub:
                sub_sty = ParagraphStyle(
                    f"card_s_{uid}", fontName=font, fontSize=7, textColor=text_light,
                    alignment=TA_RTL, leading=10, wordWrap="CJK",
                )
                rows.append([Paragraph(_b(sub), sub_sty)])
            cw = _USABLE_W / 2 - 2 * _MM
            return _tbl(rows, [cw], [
                ("BACKGROUND",    (0, 0), (-1, -1), bc),
                ("BOX",           (0, 0), (-1, -1), 0.6, border),
                # LINEAFTER = right physical edge (correct for RTL accent bar)
                ("LINEAFTER",     (0, 0), (0, -1), 3, gold),
                ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                ("TOPPADDING",    (0, 0), (0, 0),  10),
                ("TOPPADDING",    (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
            ])

        card_plate = _card("מספר רכב", plate)
        card_test  = _card("תוקף טסט", badge, value_color=test_color, bg_color=test_bg, sub=test_txt)
        card_own   = _card("היסטוריית בעלויות", f"{n_own} רשומות")
        card_fuel  = _card("סוג דלק", fuel)

        gap = 4 * _MM
        return _tbl(
            [[card_plate, "", card_test], [_sp(4), "", ""], [card_own, "", card_fuel]],
            [_USABLE_W / 2 - 2 * _MM, gap, _USABLE_W / 2 - 2 * _MM],
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

    # ── Section title ──────────────────────────────────────────────────────────
    def _section_title(title: str):
        """Section title with right-side gold accent bar (RTL: LINEAFTER = physical right)."""
        p = _p(title, s_sec_title)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND",    (0, 0), (-1, -1), off_white),
            # LINEAFTER = right physical edge — correct accent side for RTL reading
            ("LINEAFTER",     (0, 0), (0, -1), 4, gold),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.5, border_soft),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
        ])

    # ── KV table ───────────────────────────────────────────────────────────────
    def _kv_table(rows: list[tuple[str, str]], *, highlight: set[str] | None = None) -> Table | None:
        """
        Two-column RTL table.
        Right col: label (muted, smaller) — Left col: value (body, readable).
        Alternating row backgrounds, no heavy column color blocking.
        """
        highlight = highlight or set()
        data = []
        for label, value in rows:
            if not value:
                continue
            val_style = s_val_bold if label in highlight else s_val
            data.append([
                _p(value, val_style),   # col 0 — value (physically left)
                _p(label, s_lbl),       # col 1 — label (physically right)
            ])
        if not data:
            return None

        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (0, -1), 14),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("RIGHTPADDING", (1, 0), (1, -1), 12),
            ("LEFTPADDING", (1, 0), (1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            # Label column — soft surface, no heavy navy
            ("BACKGROUND", (1, 0), (1, -1), surface),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, border_soft),
            ("BOX", (0, 0), (-1, -1), 0.6, border),
        ]
        for i in range(len(data)):
            bg = colors.white if i % 2 == 0 else row_alt
            style.append(("BACKGROUND", (0, i), (0, i), bg))
        return _tbl(data, [_COL_VALUE, _COL_LABEL], style)

    # ── Alert / Warning boxes ──────────────────────────────────────────────────
    def _alert_box(text: str) -> Table:
        p = _p(f"רכב בוטל רשמית (גרוטאה) · {text}", s_alert)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), red_bg),
            ("BOX", (0, 0), (-1, -1), 1.5, red),
            ("LINEBEFORE", (0, 0), (0, -1), 4, red),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ])

    def _warn_box(text: str) -> Table:
        p = _p(text, s_warn)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), amber_bg),
            ("BOX", (0, 0), (-1, -1), 1, amber),
            ("LINEBEFORE", (0, 0), (0, -1), 4, amber),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ])

    # ── Price highlight ────────────────────────────────────────────────────────
    def _price_highlight(rows: list[tuple[str, str]]) -> Table | None:
        data = []
        for label, value in rows:
            if not value:
                continue
            is_main = data == []
            val_sty = s_price_main if is_main else s_price_sub
            data.append([_p(value, val_sty), _p(label, s_lbl)])
        if not data:
            return None
        return _tbl(data, [_COL_VALUE, _COL_LABEL], [
            ("BACKGROUND", (0, 0), (-1, -1), gold_bg),
            ("BACKGROUND", (1, 0), (1, -1), surface),
            ("BOX", (0, 0), (-1, -1), 1.5, gold),
            ("LINEAFTER", (0, 0), (0, -1), 4, gold),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (0, -1), 14),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("RIGHTPADDING", (1, 0), (1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, border_soft),
        ])

    # ── Ownership table ────────────────────────────────────────────────────────
    def _ownership_table(ownership: list) -> Table | None:
        if not ownership:
            return None
        data = []
        for i, o in enumerate(ownership, 1):
            dt_str    = _fmt_baalut_dt(o.get("baalut_dt", ""))
            baalut_tp = o.get("baalut", "לא ידוע")
            idx_bg    = navy if i % 2 == 1 else navy_soft
            idx_sty   = ParagraphStyle(
                f"own_{i}", fontName=font_bold, fontSize=9,
                textColor=colors.white, alignment=TA_CENTER, leading=12, wordWrap="CJK",
            )
            num_p = Paragraph(str(i), idx_sty)
            data.append([num_p, _p(baalut_tp, s_own_type), _p(dt_str, s_own_date)])

        idx_w  = 12 * _MM
        type_w = (_USABLE_W - idx_w) * 0.50
        date_w = _USABLE_W - idx_w - type_w

        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 0), (2, -1), "RIGHT"),
            ("RIGHTPADDING", (1, 0), (2, -1), 12),
            ("LEFTPADDING", (1, 0), (2, -1), 6),
            ("BOX", (0, 0), (-1, -1), 0.6, border),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, border_soft),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]
        for i in range(len(data)):
            idx_color = navy if i % 2 == 0 else navy_soft
            row_color = colors.white if i % 2 == 0 else row_alt
            style.append(("BACKGROUND", (0, i), (0, i), idx_color))
            style.append(("BACKGROUND", (1, i), (2, i), row_color))
        return _tbl(data, [idx_w, type_w, date_w], style)

    # ── Social CTA footer ──────────────────────────────────────────────────────
    class _SocialLink(Flowable):
        def __init__(self, kind: str, label_he: str, url: str, primary: bool, width: float = 0):
            super().__init__()
            self.kind = kind
            self.label_he = label_he
            self.url = url
            self.primary = primary
            self._fixed_width = width  # 0 = use availWidth
            self.h = 13 * _MM

        def wrap(self, availWidth, availHeight):
            self.width = self._fixed_width if self._fixed_width else min(availWidth, _USABLE_W)
            return self.width, self.h

        def draw(self):
            canv  = self.canv
            w     = self.width
            h     = self.h
            bg    = navy if self.primary else colors.white
            bd    = gold if self.primary else border
            txt_c = colors.white if self.primary else navy
            lw    = 1.5 if self.primary else 0.8

            canv.setFillColor(bg)
            canv.setStrokeColor(bd)
            canv.setLineWidth(lw)
            canv.roundRect(0, 0, w, h, 5, fill=1, stroke=1)

            icon_sz = 7 * _MM
            r       = icon_sz / 2
            gap     = 8
            label_v = _b(self.label_he)
            canv.setFont(font_bold, 9)
            label_w = canv.stringWidth(label_v, font_bold, 9)
            grp_w   = icon_sz + gap + label_w
            x0      = (w - grp_w) / 2
            y0      = (h - icon_sz) / 2

            if self.kind == "telegram":
                canv.setFillColor(colors.Color(0.16, 0.52, 0.78))
            else:
                canv.setFillColor(colors.Color(0.15, 0.68, 0.38))
            canv.circle(x0 + r, y0 + r, r, fill=1, stroke=0)
            canv.setFillColor(colors.white)
            canv.circle(x0 + r, y0 + r, r * 0.50, fill=1, stroke=0)

            canv.setFillColor(txt_c)
            canv.drawString(x0 + icon_sz + gap, (h - 9) / 2, label_v)

            # linkURL needs absolute page coordinates.
            # absolutePosition() gives the bottom-left corner of this Flowable on the page.
            try:
                ax, ay = canv.absolutePosition(0, 0)
                canv.linkURL(self.url, (ax, ay, ax + w, ay + h), relative=0)
            except Exception:
                # Fallback: use relative rect (works in simple layouts)
                try:
                    canv.linkURL(self.url, (0, 0, w, h), relative=1)
                except Exception:
                    pass

    def _promo_footer() -> list:
        flow: list = [_sp(10)]
        flow.append(_hr(color=border, thickness=0.5, space=0))
        flow.append(_tbl(
            [[_p("להמשך בדיקה / קבלת עדכונים", s_cta_title)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), navy),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ],
        ))
        flow.append(_tbl(
            [[_p("לחיצה על הכפתור תפתח את הבוט ישירות", s_cta_hint)]],
            [_USABLE_W],
            [("BACKGROUND", (0, 0), (-1, -1), off_white),
             ("TOPPADDING", (0, 0), (-1, -1), 5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 5)],
        ))

        ch = (channel or "").strip().lower()
        tg = ("telegram", "פתח בטלגרם", tg_url) if tg_url else None
        wa = ("whatsapp", "פתח בוואטסאפ", wa_url) if wa_url else None
        buttons: list[tuple[str, str, str, bool]] = []
        if ch in ("telegram", "tg"):
            if tg: buttons.append((*tg, True))
            if wa: buttons.append((*wa, False))
        elif ch in ("whatsapp", "wa"):
            if wa: buttons.append((*wa, True))
            if tg: buttons.append((*tg, False))
        else:
            if tg: buttons.append((*tg, True))
            if wa: buttons.append((*wa, True))

        if not buttons:
            return flow

        flow.append(_sp(6))

        if len(buttons) == 1:
            kind, label, url, primary = buttons[0]
            flow.append(_SocialLink(kind, label, url, primary, width=_USABLE_W))
        else:
            # Two buttons side-by-side with a small gap
            gap   = 4 * _MM
            btn_w = (_USABLE_W - gap) / 2
            k0, l0, u0, p0 = buttons[0]
            k1, l1, u1, p1 = buttons[1]
            btn0 = _SocialLink(k0, l0, u0, p0, width=btn_w)
            btn1 = _SocialLink(k1, l1, u1, p1, width=btn_w)
            flow.append(_tbl(
                [[btn0, "", btn1]],
                [btn_w, gap, btn_w],
                [
                    ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING",    (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                ],
            ))

        return flow

    # ── Section wrapper ────────────────────────────────────────────────────────
    def _section(block: list) -> list:
        out: list = [_sp(14)]
        out.extend(block)
        out.append(_sp(2))
        return out

    # ── Assemble story ─────────────────────────────────────────────────────────
    story: list = []

    cov = _cover_image()
    if cov:
        story.append(cov)
        story.append(_sp(6))

    story.extend(_hero_header())
    story.append(_sp(16))
    story.append(_stat_cards())
    story.append(_sp(6))

    # Scrapped alert
    scrapped_dt = record.get("_scrapped_dt")
    if scrapped_dt:
        story.append(_alert_box(_fd(scrapped_dt)))
        story.append(_sp(8))

    # Import / registry status helpers
    pi = record.get("_personal_import")
    import_txt = (_v(pi, "sug_yevu") or "יבוא אישי") if pi else ""
    if record.get("_inactive_no_degem"):
        inactive_txt = "לא פעיל (ללא קוד דגם)"
    elif record.get("_inactive_registry") or record.get("_was_rental"):
        inactive_txt = _v(record, "grira_nm") or "רשום במאגר לא פעיל"
    else:
        inactive_txt = "פעיל"

    # ── פרטים כלליים ──────────────────────────────────────────────────────────
    general = [
        ("מספר רכב",   plate),
        ("יצרן",       make),
        ("דגם",        model),
        ("שנת ייצור",  year),
        ("צבע",        _v(record, "tzeva_rechev")),
        ("יבוא אישי",  import_txt if pi else ""),
        ("בעלות נוכחית", _v(record, "baalut")),
        ("ארץ ייצור",  _v(wltp, "tozeret_eretz_nm")),
        ("מקוריות",    _v(record, "mkoriut_nm")),
        ("מסגרת",      _v(record, "misgeret")),
    ]
    tbl = _kv_table(general, highlight={"מספר רכב", "יצרן", "דגם"})
    if tbl:
        story.extend(_section([_section_title("פרטים כלליים"), tbl]))

    # ── מצב ובדיקות ───────────────────────────────────────────────────────────
    test_txt, _, _ = _test_status(record.get("tokef_dt"))
    km_val  = _v(record, "kilometer_test_aharon")
    gapam   = record.get("gapam_ind")
    status_rows = [
        ("תוקף טסט",      test_txt),
        ("ק\"מ בטסט אחרון", f"{km_val} ק\"מ" if km_val else ""),
        ("טסט אחרון",      _fd(record.get("mivchan_acharon_dt"))),
        ("רישום ראשון",    _fd(record.get("rishum_rishon_dt"))),
        ("סטטוס רישום",    inactive_txt),
        ("GAPAM",          "כן" if str(gapam) == "1" else ("לא" if gapam is not None else "")),
        ("שינוי מבנה",     "כן" if str(record.get("shinui_mivne_ind")) == "1" else (
                           "לא" if record.get("shinui_mivne_ind") is not None else "")),
        ("שינוי צבע",      "כן" if str(record.get("shnui_zeva_ind")) == "1" else (
                           "לא" if record.get("shnui_zeva_ind") is not None else "")),
    ]
    tbl = _kv_table(status_rows, highlight={"תוקף טסט"})
    if tbl:
        story.extend(_section([_section_title("מצב ובדיקות"), tbl]))

    # ── היסטוריית בעלויות ─────────────────────────────────────────────────────
    ownership = record.get("_ownership") or []
    own_block = [_section_title(f"היסטוריית בעלויות · {len(ownership)} רשומות")]
    own_tbl   = _ownership_table(ownership)
    if own_tbl:
        own_block.append(own_tbl)
    else:
        own_block.append(_p("לא נמצאו נתוני בעלות", s_val))
    story.extend(_section(own_block))

    # ── מפרט טכני ─────────────────────────────────────────────────────────────
    auto_ind  = wltp.get("automatic_ind")
    gearbox   = "אוטומטית" if str(auto_ind) == "1" else ("ידנית" if str(auto_ind) == "0" else "")
    engine_cc = _v(wltp, "nefah_manoa")
    specs = [
        ("סוג דלק",       _v(record, "sug_delek_nm")),
        ("נפח מנוע",       f"{engine_cc} סמ\"ק" if engine_cc else ""),
        ("כוח סוס",        _v(wltp, "koah_sus")),
        ("תיבת הילוכים",  gearbox),
        ("מושבים",         _v(wltp, "mispar_moshavim")),
        ("ניקוד בטיחות",  _v(wltp, "nikud_betihut")),
        ("צמיג קדמי",      _v(record, "zmig_kidmi")),
        ("צמיג אחורי",     _v(record, "zmig_ahori")),
        ("וו גרירה",       _v(record, "grira_nm")),
    ]
    tbl = _kv_table(specs)
    if tbl:
        story.extend(_section([_section_title("מפרט טכני"), tbl]))

    # ── דגלים ואזהרות ─────────────────────────────────────────────────────────
    flags: list[str] = []
    try:
        from src.formatter import _check_km_fraud
        import re as _re
        km_warn = _check_km_fraud(record)
        if km_warn:
            flags.append(_re.sub(
                r"\\([\\!\"#$%&'()*+,\-./:;<=>?@\[\]^_`{|}~])", r"\1", km_warn,
            ))
    except Exception:
        pass
    if flags:
        warn_block = [_section_title("דגלים ואזהרות")]
        for flag in flags:
            if flag:
                warn_block.append(_sp(4))
                warn_block.append(_warn_box(flag))
        story.extend(_section(warn_block))

    # ── שווי ──────────────────────────────────────────────────────────────────
    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            age       = date.today().year - int(year) if year else 0
            dep_pct   = min(age * 8, 70) if age > 0 else 0
            est_val   = int(price_int * (1 - dep_pct / 100))
            ptbl = _price_highlight([
                ("מחיר יבואן (חדש)",    f"₪{price_int:,}"),
                ("הערכת שווי משוערת", f"₪{est_val:,}  ·  ירידת ערך ~{dep_pct}%"),
            ])
            if ptbl:
                story.extend(_section([_section_title("שווי ומחיר"), ptbl]))
        except Exception:
            pass

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(_sp(14))
    story.append(_hr(color=border_soft, thickness=0.4, space=0))
    story.append(_sp(6))

    disc_title_sty = sty("disc_h", size=7.5, bold=True,  color=text_muted, align=TA_RTL, leading=11)
    disc_body_sty  = sty("disc_b", size=7,   bold=False, color=text_light, align=TA_RTL, leading=11)

    # Title line — pure Hebrew, safe with _b()
    story.append(Paragraph(_b("כתב ויתור ומגבלת אחריות"), disc_title_sty))
    story.append(_sp(3))

    # Body lines — each sentence on its own Paragraph to avoid BiDi overflow
    disc_lines = [
        "המידע המוצג בדוח זה נאסף אוטומטית ממאגרי מידע ממשלתיים וציבוריים בלבד (רשות הרישוי, משרד התחבורה ומקורות ציבוריים נוספים).",
        "CarInfo ומפעיל הבוט אינם צד ליצירת המידע, אינם מאמתים אותו ואינם אחראים לנכונותו, שלמותו, עדכניותו או התאמתו למציאות.",
        "הנתונים מוצגים כפי שהם ועשויים להכיל שגיאות, פערים או מידע שאינו מעודכן.",
        "אין לראות בדוח זה תחליף לבדיקה מקצועית, ייעוץ משפטי, הנדסי או מסחרי.",
        "כל החלטה המבוססת על מידע זה היא באחריות המשתמש בלבד.",
    ]
    for line in disc_lines:
        story.append(Paragraph(_b(line), disc_body_sty))
    story.append(_sp(6))

    story.extend(_promo_footer())

    # ── Build PDF ──────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN + 2 * _MM,
        bottomMargin=_MARGIN + 11 * _MM,
    )
    doc.build(story, onFirstPage=_page_bg, onLaterPages=_page_bg)
    return buf.getvalue()
