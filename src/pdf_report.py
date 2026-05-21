"""
Hebrew PDF report generator for vehicle data.
Premium layout: reportlab + python-bidi (RTL).
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
    # Windows — Hebrew-capable system fonts
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
    """BiDi reshape for RTL Hebrew in ReportLab (always pair with TA_RIGHT)."""
    s = str(text) if text is not None else ""
    try:
        from bidi.algorithm import get_display
        return get_display(s)
    except Exception:
        return s


def _hebrew_join(*parts: str, sep: str = " · ") -> str:
    """Join mixed Hebrew/Latin fragments in logical RTL reading order."""
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
    """(text, hex_color, badge_label)"""
    if not tokef_raw:
        return "לא ידוע", "#64748B", "—"
    try:
        tokef = date.fromisoformat(str(tokef_raw)[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"פג תוקף · {abs(delta)} ימים", "#DC2626", "פג"
        if delta <= 30:
            return f"עומד לפוג · {delta} ימים", "#D97706", "דחוף"
        return f"בתוקף · {tokef.strftime('%d/%m/%Y')}", "#059669", "תקין"
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
# More whitespace + narrower content for a calmer, professional look
_MARGIN = 18 * _MM
_USABLE_W = 160 * _MM
_COL_VALUE = 104 * _MM
_COL_LABEL = 56 * _MM

# Premium palette (RGB 0–1)
C_NAVY      = (0.06, 0.11, 0.24)      # #0F1C3D
C_NAVY_MID  = (0.10, 0.18, 0.38)      # #1A2E61
C_ACCENT    = (0.85, 0.65, 0.13)      # gold #D9A621
C_SKY       = (0.91, 0.95, 0.99)
C_CARD      = (0.97, 0.98, 1.00)
C_ROW_ALT   = (0.94, 0.96, 0.99)
C_TEXT_MUTED = (0.42, 0.47, 0.55)
C_BORDER    = (0.82, 0.86, 0.92)
C_ALERT_BG  = (1.0, 0.94, 0.94)
C_ALERT_BD  = (0.86, 0.20, 0.20)
C_WARN_BG   = (1.0, 0.97, 0.88)
C_WARN_BD   = (0.85, 0.55, 0.05)
_LINK_BLUE  = "#1D4ED8"
_LINK_WHITE = "#FFFFFF"


def generate_pdf(
    record: dict,
    tg_link: str = "",
    wa_link: str = "",
    logo_path: str = "",
    cover_path: str = "",
    channel: str = "",
) -> bytes:
    """Generate a premium Hebrew vehicle-report PDF."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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

    TA_RTL = TA_RIGHT  # Hebrew + get_display() → align to physical right

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
    wltp = record.get("_wltp") or {}
    plate = _v(record, "mispar_rechev") or "—"
    make = _v(record, "tozeret_nm")
    model = _v(record, "kinuy_mishari", "degem_nm")
    year = _v(record, "shnat_yitzur")
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    tg_url = _full_url(tg_link)
    wa_url = _full_url(wa_link)

    def sty(name, *, size=10, bold=False, color=colors.black, align=TA_RTL, leading=None):
        return ParagraphStyle(
            name,
            fontName=font_bold if bold else font,
            fontSize=size,
            textColor=color,
            alignment=align,
            leading=leading or size * 1.45,
            wordWrap="CJK",
        )

    def _p(text: Any, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_b(text), style)

    navy = colors.Color(*C_NAVY)
    navy_mid = colors.Color(*C_NAVY_MID)
    accent = colors.Color(*C_ACCENT)
    sky = colors.Color(*C_SKY)
    card = colors.Color(*C_CARD)
    muted = colors.Color(*C_TEXT_MUTED)
    border_c = colors.Color(*C_BORDER)

    # Slightly smaller typography overall
    s_brand = sty("brand", size=18, bold=True, color=accent, align=TA_CENTER, leading=22)
    s_title = sty("title", size=11, bold=True, color=colors.white, align=TA_CENTER, leading=14)
    s_plate = sty("plate", size=22, bold=True, color=colors.white, align=TA_CENTER, leading=26)
    s_subhero = sty("subhero", size=9, color=colors.Color(0.75, 0.82, 0.95), align=TA_CENTER)
    s_meta = sty("meta", size=7, color=muted, align=TA_CENTER)
    s_sec = sty("sec", size=10, bold=True, color=navy, align=TA_RTL, leading=12)
    s_lbl = sty("lbl", size=8, bold=True, color=colors.white, align=TA_RTL)
    s_val = sty("val", size=9, color=colors.Color(*C_NAVY), align=TA_RTL)
    s_val_big = sty("val_big", size=10.5, bold=True, color=navy, align=TA_RTL)
    s_stat_lbl = sty("stat_lbl", size=7, color=muted, align=TA_RTL)
    s_stat_val = sty("stat_val", size=9.5, bold=True, color=navy, align=TA_RTL)
    s_alert = sty("alert", size=9, bold=True, color=colors.Color(*C_ALERT_BD), align=TA_RTL)
    s_warn = sty("warn", size=8, color=colors.Color(0.45, 0.30, 0.05), align=TA_RTL)
    s_price = sty("price", size=12, bold=True, color=navy, align=TA_RTL)
    s_footer = sty("footer", size=6.5, color=muted, align=TA_CENTER)
    s_cta_title = sty("cta_t", size=10.5, bold=True, color=colors.white, align=TA_CENTER)
    s_cta_hint = sty("cta_h", size=8, color=navy, align=TA_CENTER)
    s_cta_sub = sty("cta_s", size=6.5, color=muted, align=TA_CENTER)

    # ── Page chrome (header strip + footer on every page) ─────────────────────
    def _page_bg(canv, doc):
        canv.saveState()
        pw, ph = A4
        # Top brand strip
        canv.setFillColor(navy)
        canv.rect(0, ph - 6 * _MM, pw, 6 * _MM, fill=1, stroke=0)
        canv.setFillColor(accent)
        canv.rect(0, ph - 6.8 * _MM, pw, 0.8 * _MM, fill=1, stroke=0)
        # Bottom footer band
        canv.setFillColor(sky)
        canv.rect(0, 0, pw, 11 * _MM, fill=1, stroke=0)
        canv.setStrokeColor(border_c)
        canv.setLineWidth(0.4)
        canv.line(_MARGIN, 11 * _MM, pw - _MARGIN, 11 * _MM)
        canv.setFillColor(muted)
        canv.setFont(font, 7)
        footer_txt = _b(f"CarInfo · דוח רכב {plate} · {now_str} · עמוד {canv.getPageNumber()}")
        canv.drawCentredString(pw / 2, 4 * _MM, footer_txt)
        canv.restoreState()

    # ── Building blocks ───────────────────────────────────────────────────────
    def _tbl(rows, colw, style_cmds):
        t = Table(rows, colWidths=colw)
        t.setStyle(TableStyle(style_cmds))
        return t

    def _hero_header():
        """Branded hero: logo + title + giant plate + vehicle line."""
        title_para = _p("דוח בדיקת רכב מקיף", s_title)
        vehicle_line = _hebrew_join(
            f"שנת {year}" if year else "",
            model,
            make,
        ) if (make or model or year) else _b("—")
        plate_para = _p(plate, s_plate)
        brand_para = Paragraph("CARINFO", s_brand)  # Latin — no BiDi
        sub_para = Paragraph(vehicle_line, s_subhero)
        date_para = _p(f"הופק: {now_str}", s_meta)

        if logo_path:
            try:
                from reportlab.platypus import Image as RLImage
                logo_h = 16 * _MM
                logo_img = RLImage(logo_path, height=logo_h, width=logo_h, kind="proportional")
                text_w = _USABLE_W - logo_h - 6 * _MM
                # RTL: טקסט מימין, לוגו משמאל
                top = _tbl(
                    [[brand_para, logo_img], [title_para, ""]],
                    [text_w, logo_h + 4 * _MM],
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("SPAN", (0, 1), (0, 1)),
                        ("BACKGROUND", (0, 0), (-1, -1), navy),
                        ("TOPPADDING", (0, 0), (-1, -1), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (0, -1), 10),
                        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ],
                )
            except Exception:
                top = _tbl([[brand_para], [title_para]], [_USABLE_W], [
                    ("BACKGROUND", (0, 0), (-1, -1), navy),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ])
        else:
            top = _tbl([[brand_para], [title_para]], [_USABLE_W], [
                ("BACKGROUND", (0, 0), (-1, -1), navy),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])

        plate_band = _tbl([[plate_para]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), navy_mid),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
        sub_band = _tbl([[sub_para], [date_para]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), navy),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
        gold = HRFlowable(width=_USABLE_W, thickness=3, color=accent, spaceBefore=0, spaceAfter=0)
        return [top, plate_band, sub_band, gold]

    def _cover_image():
        if not cover_path:
            return None
        try:
            from reportlab.platypus import Image as RLImage
            try:
                from PIL import Image as PILImage
                with PILImage.open(cover_path) as im:
                    pw, ph = im.size
                h = min(_USABLE_W * ph / pw, 55 * _MM)
            except ImportError:
                h = 45 * _MM
            return RLImage(cover_path, width=_USABLE_W, height=h)
        except Exception:
            return None

    def _stat_cards():
        test_txt, test_hex, badge = _test_status(record.get("tokef_dt"))
        n_own = len(record.get("_ownership") or [])
        fuel = _v(record, "sug_delek_nm") or "—"
        cw = _USABLE_W / 4
        # RTL: מימין לשמאל — רכב, טסט, בעלויות, דלק
        row_data: list[tuple[Any, str]] = [
            (_b(fuel), "דלק"),
            (_b(str(n_own)), "בעלויות"),
            (Paragraph(
                f'<font color="{test_hex}"><b>{_b(badge)}</b></font><br/>{_b(test_txt)}',
                s_stat_val,
            ), "תוקף טסט"),
            (_b(plate), "מספר רכב"),
        ]
        row_cells = []
        for val, lbl in row_data:
            val_p = val if not isinstance(val, str) else Paragraph(val, s_stat_val)
            row_cells.append(_tbl(
                [[_p(lbl, s_stat_lbl)], [val_p]],
                [cw - 6],
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ],
            ))
        return _tbl([row_cells], [cw] * 4, [
            ("BACKGROUND", (0, 0), (-1, -1), card),
            ("BOX", (0, 0), (-1, -1), 0.5, border_c),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ])

    def _section_title(title: str, icon: str = "◆"):
        p = _p(f"{title}  {icon}", s_sec)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), sky),
            ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, border_c),
        ])

    def _kv_table(rows: list[tuple[str, str]], *, highlight: set[str] | None = None) -> Table | None:
        """RTL table: עמודת תווית מימין (col 1), ערך משמאל (col 0)."""
        highlight = highlight or set()
        data = []
        for label, value in rows:
            if not value:
                continue
            val_style = s_val_big if label in highlight else s_val
            data.append([
                _p(value, val_style),
                _p(label, s_lbl),
            ])
        if not data:
            return None
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (0, -1), 12),
            ("LEFTPADDING", (0, 0), (0, -1), 6),
            ("RIGHTPADDING", (1, 0), (1, -1), 10),
            ("LEFTPADDING", (1, 0), (1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("BACKGROUND", (1, 0), (1, -1), navy_mid),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, border_c),
            ("BOX", (0, 0), (-1, -1), 0.6, border_c),
        ]
        for i in range(len(data)):
            style.append(("BACKGROUND", (0, i), (0, i), card if i % 2 == 0 else colors.Color(*C_ROW_ALT)))
        return _tbl(data, [_COL_VALUE, _COL_LABEL], style)

    def _alert_box(text: str) -> Table:
        p = _p(f"⚠  {text}", s_alert)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*C_ALERT_BG)),
            ("BOX", (0, 0), (-1, -1), 1.5, colors.Color(*C_ALERT_BD)),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ])

    def _warn_box(text: str) -> Table:
        p = _p(f"⚡  {text}", s_warn)
        return _tbl([[p]], [_USABLE_W], [
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(*C_WARN_BG)),
            ("BOX", (0, 0), (-1, -1), 1, colors.Color(*C_WARN_BD)),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])

    def _price_highlight(rows: list[tuple[str, str]]) -> Table | None:
        data = []
        for label, value in rows:
            if not value:
                continue
            data.append([_p(value, s_price), _p(label, s_lbl)])
        if not data:
            return None
        return _tbl(data, [_COL_VALUE, _COL_LABEL], [
            ("BACKGROUND", (0, 0), (-1, -1), colors.Color(1.0, 0.98, 0.92)),
            ("BACKGROUND", (1, 0), (1, -1), navy),
            ("BOX", (0, 0), (-1, -1), 1.2, accent),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("RIGHTPADDING", (0, 0), (0, -1), 12),
            ("LEFTPADDING", (0, 0), (0, -1), 6),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, border_c),
        ])

    def _ownership_table(ownership: list) -> Table | None:
        if not ownership:
            return None
        data = []
        for i, o in enumerate(ownership, 1):
            dt_str = _fmt_baalut_dt(o.get("baalut_dt", ""))
            baalut_type = o.get("baalut", "לא ידוע")
            num = _p(str(i), sty("own_n", size=10, bold=True, color=colors.white, align=TA_CENTER))
            # RTL: מספר מימין → סוג → תאריך
            data.append([num, _p(baalut_type, s_val), _p(dt_str, s_val)])
        idx_w = 14 * _MM
        mid_w = (_USABLE_W - idx_w) * 0.42
        date_w = (_USABLE_W - idx_w) - mid_w
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (0, -1), accent),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (1, 0), (2, -1), "RIGHT"),
            ("RIGHTPADDING", (1, 0), (2, -1), 10),
            ("BOX", (0, 0), (-1, -1), 0.6, border_c),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, border_c),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
        for i in range(len(data)):
            style.append(("BACKGROUND", (1, i), (2, i), card if i % 2 == 0 else colors.Color(*C_ROW_ALT)))
        return _tbl(data, [idx_w, mid_w, date_w], style)

    class _SocialLink(Flowable):
        """Clickable row: platform icon + label text."""

        def __init__(self, kind: str, label_he: str, url: str, primary: bool):
            super().__init__()
            self.kind = kind
            self.label_he = label_he
            self.url = url
            self.primary = primary
            self.h = 12 * _MM

        def wrap(self, availWidth, availHeight):
            self.width = min(availWidth, _USABLE_W)
            return self.width, self.h

        def draw(self):
            canv = self.canv
            w = getattr(self, "width", _USABLE_W)
            h = self.h

            bg = navy if self.primary else colors.Color(1, 1, 1)
            bd = accent if self.primary else border_c
            txt = colors.white if self.primary else navy

            # Subtle card
            canv.setFillColor(bg)
            canv.setStrokeColor(bd)
            canv.setLineWidth(0.8 if self.primary else 0.5)
            canv.roundRect(0, 0, w, h, 5, fill=1, stroke=1)

            # Icon (simple vector)
            icon_sz = 7.5 * _MM
            r = icon_sz / 2
            gap = 6
            label_vis = _b(self.label_he)
            canv.setFont(font_bold, 9)
            label_w = canv.stringWidth(label_vis, font_bold, 9)
            group_w = icon_sz + gap + label_w
            x0 = (w - group_w) / 2
            y0 = (h - icon_sz) / 2

            if self.kind == "telegram":
                canv.setFillColor(colors.Color(0.16, 0.52, 0.78))
                canv.circle(x0 + r, y0 + r, r, fill=1, stroke=0)
                canv.setFillColor(colors.white)
                canv.circle(x0 + r - 0.6 * _MM, y0 + r, 0.7 * _MM, fill=1, stroke=0)
            else:
                canv.setFillColor(colors.Color(0.15, 0.68, 0.38))
                canv.circle(x0 + r, y0 + r, r, fill=1, stroke=0)
                canv.setFillColor(colors.white)
                canv.circle(x0 + r, y0 + r, r * 0.52, fill=1, stroke=0)

            canv.setFillColor(txt)
            canv.drawString(x0 + icon_sz + gap, (h - 9) / 2, label_vis)

            # Clickable area over icon + text (actually entire row)
            try:
                canv.linkURL(self.url, (0, 0, w, h), relative=0)
            except Exception:
                pass

    def _promo_footer() -> list:
        flow: list = [Spacer(1, 8)]
        flow.append(_tbl(
            [[_p("להמשך בדיקה / קבלת עדכונים", s_cta_title)]],
            [_USABLE_W],
            [
                ("BACKGROUND", (0, 0), (-1, -1), navy),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ],
        ))
        flow.append(_tbl(
            [[_p("לחיצה על האייקון או הטקסט פותחת את הבוט", s_cta_hint)]],
            [_USABLE_W],
            [("BACKGROUND", (0, 0), (-1, -1), sky), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)],
        ))
        ch = (channel or "").strip().lower()
        tg = ("telegram", "פתח בטלגרם", tg_url) if tg_url else None
        wa = ("whatsapp", "פתח בוואטסאפ", wa_url) if wa_url else None
        buttons: list[tuple[str, str, str, bool]] = []
        if ch in ("telegram", "tg"):
            if tg:
                buttons.append((*tg, True))
            if wa:
                buttons.append((*wa, False))
        elif ch in ("whatsapp", "wa"):
            if wa:
                buttons.append((*wa, True))
            if tg:
                buttons.append((*tg, False))
        else:
            if tg:
                buttons.append((*tg, True))
            if wa:
                buttons.append((*wa, True))
        if not buttons:
            return flow
        # Primary first, secondary second — stacked and subtle
        kind, label, url, primary = buttons[0]
        flow.append(_SocialLink(kind, label, url, primary))
        if len(buttons) > 1:
            kind, label, url, primary = buttons[1]
            flow.append(Spacer(1, 4))
            flow.append(_SocialLink(kind, label, url, primary))
        urls = "  |  ".join(
            f'<a href="{u}" color="{_LINK_BLUE}"><font size="6.5">{u}</font></a>'
            for _, _, u, _ in buttons
        )
        flow.append(Spacer(1, 4))
        flow.append(Paragraph(urls, s_cta_sub))
        return flow

    def _section(block: list) -> list:
        """Wrap section pieces with consistent spacing."""
        out: list = [Spacer(1, 8)]
        out.extend(block)
        out.append(Spacer(1, 4))
        return out

    # ── Assemble story ──────────────────────────────────────────────────────────
    story: list = []

    cov = _cover_image()
    if cov:
        story.append(cov)
        story.append(Spacer(1, 4))
    story.extend(_hero_header())
    story.append(Spacer(1, 8))
    story.append(_stat_cards())
    story.append(Spacer(1, 10))

    scrapped_dt = record.get("_scrapped_dt")
    if scrapped_dt:
        story.append(_alert_box(f"רכב בוטל רשמית (גרוטאה) · {_fd(scrapped_dt)}"))
        story.append(Spacer(1, 8))

    pi = record.get("_personal_import")
    import_txt = (_v(pi, "sug_yevu") or "יבוא אישי") if pi else ""
    if record.get("_inactive_no_degem"):
        inactive_txt = "לא פעיל (ללא קוד דגם)"
    elif record.get("_inactive_registry") or record.get("_was_rental"):
        inactive_txt = _v(record, "grira_nm") or "רשום במאגר לא פעיל"
    else:
        inactive_txt = "פעיל"

    # ── פרטים כלליים ──
    general = [
        ("מספר רכב", plate),
        ("יצרן", make),
        ("דגם", model),
        ("שנת ייצור", year),
        ("צבע", _v(record, "tzeva_rechev")),
        ("יבוא אישי", import_txt if pi else ""),
        ("בעלות נוכחית", _v(record, "baalut")),
        ("ארץ ייצור", _v(wltp, "tozeret_eretz_nm")),
        ("מקוריות", _v(record, "mkoriut_nm")),
        ("מסגרת", _v(record, "misgeret")),
    ]
    tbl = _kv_table(general, highlight={"מספר רכב", "יצרן", "דגם"})
    if tbl:
        story.extend(_section([_section_title("פרטים כלליים"), tbl]))

    # ── מצב ובדיקות ──
    test_txt, _, _ = _test_status(record.get("tokef_dt"))
    km_val = _v(record, "kilometer_test_aharon")
    gapam = record.get("gapam_ind")
    status_rows = [
        ("תוקף טסט", test_txt),
        ("ק\"מ בטסט אחרון", f"{km_val} ק\"מ" if km_val else ""),
        ("טסט אחרון", _fd(record.get("mivchan_acharon_dt"))),
        ("רישום ראשון", _fd(record.get("rishum_rishon_dt"))),
        ("סטטוס רישום", inactive_txt),
        ("GAPAM", "כן" if str(gapam) == "1" else ("לא" if gapam is not None else "")),
        ("שינוי מבנה", "כן" if str(record.get("shinui_mivne_ind")) == "1" else (
            "לא" if record.get("shinui_mivne_ind") is not None else "")),
        ("שינוי צבע", "כן" if str(record.get("shnui_zeva_ind")) == "1" else (
            "לא" if record.get("shnui_zeva_ind") is not None else "")),
    ]
    tbl = _kv_table(status_rows, highlight={"תוקף טסט"})
    if tbl:
        story.extend(_section([_section_title("מצב ובדיקות"), tbl]))

    # ── בעלויות ──
    ownership = record.get("_ownership") or []
    own_block = [_section_title(f"היסטוריית בעלויות · {len(ownership)} רשומות")]
    own_tbl = _ownership_table(ownership)
    if own_tbl:
        own_block.append(own_tbl)
    else:
        own_block.append(_p("לא נמצאו נתוני בעלות", s_val))
    story.extend(_section(own_block))

    # ── מפרט טכני ──
    auto_ind = wltp.get("automatic_ind")
    gearbox = "אוטומטית" if str(auto_ind) == "1" else ("ידנית" if str(auto_ind) == "0" else "")
    engine_cc = _v(wltp, "nefah_manoa")
    specs = [
        ("סוג דלק", _v(record, "sug_delek_nm")),
        ("נפח מנוע", f"{engine_cc} סמ\"ק" if engine_cc else ""),
        ("כוח סוס", _v(wltp, "koah_sus")),
        ("תיבת הילוכים", gearbox),
        ("מושבים", _v(wltp, "mispar_moshavim")),
        ("ניקוד בטיחות", _v(wltp, "nikud_betihut")),
        ("צמיג קדמי", _v(record, "zmig_kidmi")),
        ("צמיג אחורי", _v(record, "zmig_ahori")),
        ("וו גרירה", _v(record, "grira_nm")),
    ]
    tbl = _kv_table(specs)
    if tbl:
        story.extend(_section([_section_title("מפרט טכני"), tbl]))

    # ── דגלים ──
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
        warn_block = [_section_title("דגלים ואזהרות", "⚡")]
        for flag in flags:
            if flag:
                warn_block.append(_warn_box(flag))
        story.extend(_section(warn_block))

    # ── שווי ──
    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            age = date.today().year - int(year) if year else 0
            dep_pct = min(age * 8, 70) if age > 0 else 0
            est_val = int(price_int * (1 - dep_pct / 100))
            ptbl = _price_highlight([
                ("מחיר יבואן (חדש)", f"₪{price_int:,}"),
                ("הערכת שווי משוערת", f"₪{est_val:,}  ·  ירידת ערך ~{dep_pct}%"),
            ])
            if ptbl:
                story.extend(_section([_section_title("שווי ומחיר", "₪"), ptbl]))
        except Exception:
            pass

    # Disclaimer
    story.append(Spacer(1, 6))
    story.append(_p(
        "הדוח מבוסס על נתונים ציבוריים · אין להסתמך עליו כייעוץ משפטי או מסחרי בלבד",
        sty("disc", size=8, color=muted, align=TA_RTL),
    ))

    story.extend(_promo_footer())

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN + 4 * _MM,
        bottomMargin=_MARGIN + 12 * _MM,
    )
    doc.build(story, onFirstPage=_page_bg, onLaterPages=_page_bg)
    return buf.getvalue()
