"""
Formats vehicle data into categorized Hebrew Telegram messages (MarkdownV2).
Each category is returned separately for InlineKeyboard navigation.
"""

from datetime import datetime, date
from typing import Optional


def _escape(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def _format_date(raw: Optional[str]) -> str:
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
    except Exception:
        return raw[:10]


def _test_status(tokef_raw: Optional[str]) -> str:
    if not tokef_raw:
        return "❓ לא ידוע"
    try:
        tokef = date.fromisoformat(tokef_raw[:10])
        delta = (tokef - date.today()).days
        if delta < 0:
            return f"🔴 פג תוקף לפני {abs(delta)} ימים"
        if delta <= 30:
            return f"🟡 פג תוקף בעוד {delta} ימים"
        return f"🟢 בתוקף עד {tokef.strftime('%d/%m/%Y')}"
    except Exception:
        return "❓ לא ידוע"


def _ownership_label(baalut: Optional[str]) -> str:
    mapping = {"1": "ראשונה", "2": "שנייה", "3": "שלישית", "4": "רביעית", "5": "חמישית ומעלה"}
    if not baalut:
        return ""
    return mapping.get(str(baalut).strip(), str(baalut))


def _yn(val) -> str:
    if val is None or str(val).strip() in ("", "None", "nan"):
        return ""
    s = str(val).strip().upper()
    if s in ("1", "Y", "YES", "TRUE"):
        return "✅ כן"
    if s in ("0", "N", "NO", "FALSE"):
        return "❌ לא"
    return s


def _val(record: dict, *keys) -> str:
    for k in keys:
        v = record.get(k)
        if v is not None and str(v).strip() not in ("", "None", "nan", "0"):
            return str(v).strip()
    return ""


def _row(label: str, value) -> str:
    v = str(value).strip() if value else ""
    if not v or v in ("None", "nan", "0"):
        return ""
    return f"• *{_escape(label)}:* {_escape(v)}\n"


# ─────────────────────────────────────────────
# Category builders
# ─────────────────────────────────────────────

def cat_general(record: dict, w: dict) -> str:
    lines = ["*📋 פרטים כלליים*\n"]
    lines.append(_row("יצרן", _val(record, "tozeret_nm")))
    lines.append(_row("דגם", _val(record, "kinuy_mishari", "degem_nm")))
    lines.append(_row("רמת גימור", _val(w, "ramat_gimur")))
    lines.append(_row("שנת ייצור", _val(record, "shnat_yitzur")))
    lines.append(_row("צבע", _val(record, "tzeva_rechev")))
    lines.append(_row("סוג רכב", _val(record, "sug_rechev_nm")))
    lines.append(_row("בעלות", _ownership_label(record.get("baalut"))))
    lines.append(_row("מקוריות", _val(record, "mkoriut_nm")))
    lines.append(_row("מסגרת (שלדה)", _val(record, "misgeret")))
    lines.append(_row("מספר מנוע", _val(record, "mispar_manoa")))
    return "".join(l for l in lines if l)


def cat_specs(record: dict, w: dict) -> str:
    engine_cc  = _val(w, "nefah_manoa") or _val(record, "nefach_manoa")
    weight     = _val(w, "mishkal_kolel")
    height     = _val(w, "gova")
    wheelbase  = _val(w, "merkav")
    tow_with   = _val(w, "kosher_grira_im_blamim")
    tow_without= _val(w, "kosher_grira_bli_blamim")
    auto       = _yn(w.get("automatic_ind"))
    gearbox    = "אוטומטית" if auto == "✅ כן" else ("ידנית" if auto == "❌ לא" else "")

    lines = ["*⚙️ מפרט טכני*\n"]
    lines.append(_row("סוג דלק", _val(record, "sug_delek_nm")))
    lines.append(_row("נפח מנוע", f"{engine_cc} סמ\"ק" if engine_cc else ""))
    lines.append(_row("כוח סוס", _val(w, "koah_sus")))
    lines.append(_row("תיבת הילוכים", gearbox))
    lines.append(_row("מושבים", _val(w, "mispar_moshavim")))
    lines.append(_row("דלתות", _val(w, "mispar_dlatot")))
    lines.append(_row("משקל כולל", f"{weight} ק\"ג" if weight else ""))
    lines.append(_row("גובה", f"{height} מ\"מ" if height else ""))
    lines.append(_row("מרחק סרנים", f"{wheelbase} מ\"מ" if wheelbase else ""))
    lines.append(_row("גרירה עם בלמים", f"{tow_with} ק\"ג" if tow_with else ""))
    lines.append(_row("גרירה ללא בלמים", f"{tow_without} ק\"ג" if tow_without else ""))
    return "".join(l for l in lines if l)


def cat_tires(record: dict, w: dict) -> str:
    front = _val(record, "zmig_kidmi")
    rear  = _val(record, "zmig_ahori", "zmig_achori")
    lines = ["*🔧 גלגלים וצמיגים*\n"]
    lines.append(_row("צמיג קדמי", front))
    lines.append(_row("צמיג אחורי", rear))
    if not front and not rear:
        lines.append("_אין נתוני צמיגים במאגר_\n")
    return "".join(l for l in lines if l)


def cat_equipment(record: dict, w: dict) -> str:
    power_win = _val(w, "mispar_halonot_hashmal")
    lines = ["*🛋️ ציוד ונוחות*\n"]
    lines.append(_row("מיזוג אוויר", _yn(w.get("mazgan_ind"))))
    lines.append(_row("הגה כוח", _yn(w.get("hege_koah_ind"))))
    lines.append(_row("חלונות חשמל", f"{power_win} חלונות" if power_win else ""))
    lines.append(_row("גג פנורמי/שמש", _yn(w.get("halon_bagg_ind"))))
    lines.append(_row("חישוקי סגסוגת", _yn(w.get("galgaley_sagsoget_kala_ind"))))
    lines.append(_row("ארגז/תא מטען", _yn(w.get("argaz_ind"))))
    return "".join(l for l in lines if l)


def cat_safety(record: dict, w: dict) -> str:
    co2        = _val(w, "CO2_WLTP", "kamut_CO2")
    nox        = _val(w, "NOX_WLTP", "kamut_NOX")
    airbags    = _val(w, "mispar_kariot_avir")
    lines = ["*🛡️ בטיחות ופליטות*\n"]
    lines.append(_row("ניקוד בטיחות", _val(w, "nikud_betihut")))
    lines.append(_row("רמת ציוד בטיחותי", _val(w, "ramat_eivzur_betihuty")))
    lines.append(_row("כריות אוויר", f"{airbags} כריות" if airbags else ""))
    lines.append(_row("ABS", _yn(w.get("abs_ind"))))
    lines.append(_row("קבוצת זיהום", _val(record, "kvuzat_zihum")))
    lines.append(_row("מדד ירוק", _val(w, "madad_yarok")))
    lines.append(_row("CO2", f"{co2} גר'/ק\"מ" if co2 else ""))
    lines.append(_row("NOX", f"{nox} מ\"ג/ק\"מ" if nox else ""))
    return "".join(l for l in lines if l)


def cat_adas(record: dict, w: dict) -> str:
    rows = [
        _row("שמירת נתיב", _yn(w.get("bakarat_stiya_menativ_ind"))),
        _row("ניטור מרחק קדמי", _yn(w.get("nitur_merhak_milfanim_ind"))),
        _row("זיהוי שטח עיוור", _yn(w.get("zihuy_beshetah_nistar_ind"))),
        _row("בקרת שיוט אדפטיבית", _yn(w.get("bakarat_shyut_adaptivit_ind"))),
        _row("זיהוי הולכי רגל", _yn(w.get("zihuy_holchey_regel_ind"))),
        _row("בלימת חירום אוטומטית", _yn(w.get("maarechet_ezer_labalam_ind"))),
        _row("מצלמת רוורס", _yn(w.get("matzlemat_reverse_ind"))),
        _row("חיישני לחץ צמיגים", _yn(w.get("hayshaney_lahatz_avir_batzmigim_ind"))),
        _row("חיישן עייפות נהג", _yn(w.get("hayshaney_hagorot_ind"))),
        _row("זיהוי תמרורים", _yn(w.get("zihuy_tamrurey_tnua_ind"))),
        _row("שליטה אוטו' בפנסי גבוה", _yn(w.get("shlita_automatit_beorot_gvohim_ind"))),
        _row("התראת נסיעה קדימה", _yn(w.get("teura_automatit_benesiya_kadima_ind"))),
        _row("זיהוי אופניים/קורקינט", _yn(w.get("zihuy_rechev_do_galgali"))),
        _row("נעילת אלכוהול", _yn(w.get("alco_lock"))),
    ]
    content = "".join(r for r in rows if r)
    if not content:
        return "*🤖 מערכות ADAS*\n_אין נתוני ADAS במאגר_\n"
    return "*🤖 מערכות ADAS*\n" + content


def cat_history(record: dict, w: dict) -> str:
    km = _val(record, "kilometer_test_aharon")
    changed_body  = _yn(record.get("shinui_mivne_ind"))
    changed_color = _yn(record.get("shnui_zeva_ind"))
    changed_tire  = _yn(record.get("shinui_zmig_ind"))
    gapam         = _yn(record.get("gapam_ind"))

    lines = ["*📅 היסטוריה ורישום*\n"]
    lines.append(_row("תאריך רישום ראשון", _format_date(record.get("rishum_rishon_dt"))))
    lines.append(_row("עלייה לכביש", _format_date(record.get("moed_aliya_lakvish"))))
    lines.append(_row("ק\"מ בטסט אחרון", f"{km} ק\"מ" if km else ""))
    lines.append(_row("טסט אחרון", _format_date(record.get("mivchan_acharon_dt"))))
    lines.append(f"• *{_escape('תוקף טסט')}:* {_escape(_test_status(record.get('tokef_dt')))}\n")

    changes = []
    if changed_body  == "✅ כן": changes.append("מבנה")
    if changed_color == "✅ כן": changes.append("צבע")
    if changed_tire  == "✅ כן": changes.append("צמיגים")
    if gapam         == "✅ כן": changes.append("GAPAM")
    if changes:
        lines.append(f"• *{_escape('שינויים ברכב')}:* {_escape(', '.join(changes))}\n")

    return "".join(l for l in lines if l)


def cat_recalls(record: dict) -> str:
    recalls = record.get("_recalls") or []
    if not recalls:
        return "*🔔 ריקולים*\n_לא נמצאו ריקולים לדגם זה_\n"
    lines = [f"*🔔 ריקולים \\({_escape(str(len(recalls)))}\\)*\n"]
    for r in recalls:
        teur  = r.get("TEUR_TAKALA", "")
        ofen  = r.get("OFEN_TIKUN", "")
        shnat = r.get("SHNAT_RECALL", "")
        if teur:
            line = f"• *{_escape(str(shnat))}:* {_escape(str(teur))}"
            if ofen:
                line += f" _\\({_escape(str(ofen))}\\)_"
            lines.append(line + "\n")
    return "".join(lines)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

CATEGORIES = {
    "general":   ("📋 פרטים כלליים",  cat_general),
    "specs":     ("⚙️ מפרט טכני",     cat_specs),
    "tires":     ("🔧 גלגלים",        cat_tires),
    "equipment": ("🛋️ ציוד",          cat_equipment),
    "safety":    ("🛡️ בטיחות",        cat_safety),
    "adas":      ("🤖 ADAS",           cat_adas),
    "history":   ("📅 היסטוריה",       cat_history),
    "recalls":   ("🔔 ריקולים",        cat_recalls),
}


def get_summary(record: dict) -> str:
    plate        = _val(record, "mispar_rechev")
    manufacturer = _val(record, "tozeret_nm")
    model        = _val(record, "kinuy_mishari", "degem_nm")
    year         = _val(record, "shnat_yitzur")
    w            = record.get("_wltp") or {}
    trim         = _val(w, "ramat_gimur")
    road_entry   = _format_date(record.get("moed_aliya_lakvish"))
    test         = _test_status(record.get("tokef_dt"))
    km           = _val(record, "kilometer_test_aharon")

    lines = [
        f"🚗 *{_escape(manufacturer)} {_escape(model)}*\n",
        f"━━━━━━━━━━━━━━━━━━\n",
        f"• *{_escape('מספר רכב')}:* {_escape(plate)}\n",
        f"• *{_escape('דגם')}:* {_escape(model)}\n" if model else "",
        f"• *{_escape('שנת ייצור')}:* {_escape(year)}\n" if year else "",
        f"• *{_escape('גימור')}:* {_escape(trim)}\n" if trim else "",
        f"• *{_escape('עלייה לכביש')}:* {_escape(road_entry)}\n" if road_entry else "",
        f"• *{_escape('תוקף טסט')}:* {_escape(test)}\n",
        f"• *{_escape('ק\"מ אחרון שדווח')}:* {_escape(km)} ק\"מ\n" if km else "",
        f"\n_בחר קטגוריה למידע נוסף_ ⬇️",
    ]
    return "".join(l for l in lines if l)


def get_category_text(category: str, record: dict) -> str:
    w = record.get("_wltp") or {}
    if category == "recalls":
        return cat_recalls(record)
    fn = CATEGORIES.get(category)
    if fn:
        return fn[1](record, w)
    return "❓ קטגוריה לא נמצאה"


def format_not_found(plate: str) -> str:
    return (
        f"❌ לא נמצא מידע על מספר רכב *{_escape(plate)}*\\.\n\n"
        "ודא שהמספר תקין \\(ללא מקפים או עם מקפים\\)\\."
    )


def format_error() -> str:
    return (
        "⚠️ אירעה שגיאה בעת שליפת הנתונים\\.\n"
        "נסה שוב עוד כמה שניות\\."
    )
