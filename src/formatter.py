"""
Formats vehicle data into categorized Hebrew Telegram messages (MarkdownV2).
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


def _yn_always(val) -> str:
    """Always returns a value – ✅/❌ or ✖ לא קיים."""
    if val is None or str(val).strip() in ("", "None", "nan"):
        return "✖ לא קיים"
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


def _val_always(record: dict, *keys) -> str:
    """Always returns a value – raw or ✖ לא קיים."""
    for k in keys:
        v = record.get(k)
        if v is not None and str(v).strip() not in ("", "None", "nan"):
            s = str(v).strip()
            if s == "0":
                return s
            return s
    return "✖ לא קיים"


def _row(label: str, value) -> str:
    """Row only if value exists."""
    v = str(value).strip() if value else ""
    if not v or v in ("None", "nan"):
        return ""
    return f"• *{_escape(label)}:* {_escape(v)}\n"


def _row_always(label: str, value) -> str:
    """Row always shown – shows ✖ לא קיים if missing."""
    v = str(value).strip() if value is not None else ""
    if not v or v in ("None", "nan", ""):
        v = "✖ לא קיים"
    return f"• *{_escape(label)}:* {_escape(v)}\n"


# ─────────────────────────────────────────────
# Category builders
# ─────────────────────────────────────────────

def cat_general(record: dict, w: dict) -> str:
    lines = ["*📋 פרטים כלליים*\n"]
    lines.append(_row_always("יצרן", _val(record, "tozeret_nm")))
    lines.append(_row_always("דגם", _val(record, "kinuy_mishari", "degem_nm")))
    lines.append(_row_always("רמת גימור", _val(w, "ramat_gimur")))
    lines.append(_row_always("שנת ייצור", _val(record, "shnat_yitzur")))
    lines.append(_row_always("צבע", _val(record, "tzeva_rechev")))
    lines.append(_row_always("ארץ ייצור", _val(w, "tozeret_eretz_nm")))
    lines.append(_row_always("יבואן/תוצר", _val(w, "tozar")))
    lines.append(_row_always("סוג מרכב", _val(w, "merkav")))
    lines.append(_row_always("סוג רכב", _val(record, "sug_rechev_nm")))
    lines.append(_row_always("סוג תקינה", _val(w, "sug_tkina_nm")))
    lines.append(_row_always("מסגרת (שלדה)", _val(record, "misgeret")))
    lines.append(_row_always("מספר מנוע", _val(record, "mispar_manoa")))
    return "".join(lines)


def cat_specs(record: dict, w: dict) -> str:
    engine_cc   = _val(w, "nefah_manoa") or _val(record, "nefach_manoa")
    weight      = _val(w, "mishkal_kolel")
    height      = _val(w, "gova")
    wheelbase   = _val(w, "merkav")
    tow_with    = _val(w, "kosher_grira_im_blamim")
    tow_without = _val(w, "kosher_grira_bli_blamim")
    auto        = w.get("automatic_ind")
    gearbox     = "אוטומטית" if str(auto) == "1" else ("ידנית" if str(auto) == "0" else "✖ לא קיים")

    lines = ["*⚙️ מפרט טכני*\n"]
    lines.append(_row_always("סוג דלק", _val(record, "sug_delek_nm")))
    lines.append(_row_always("טכנולוגיית הנעה", _val(w, "technologiat_hanaa_nm")))
    lines.append(_row_always("סוג הנעה", _val(w, "hanaa_nm")))
    lines.append(_row_always("נפח מנוע", f"{engine_cc} סמ\"ק" if engine_cc else ""))
    lines.append(_row_always("כוח סוס", _val(w, "koah_sus")))
    lines.append(_row_always("תיבת הילוכים", gearbox))
    lines.append(_row_always("סוג ממיר", _val(w, "sug_mamir_nm")))
    lines.append(_row_always("מושבים", _val(w, "mispar_moshavim")))
    lines.append(_row_always("דלתות", _val(w, "mispar_dlatot")))
    lines.append(_row_always("משקל כולל", f"{weight} ק\"ג" if weight else ""))
    lines.append(_row_always("גובה", f"{height} מ\"מ" if height else ""))
    lines.append(_row_always("מרחק סרנים", f"{wheelbase} מ\"מ" if wheelbase else ""))
    lines.append(_row_always("גרירה עם בלמים", f"{tow_with} ק\"ג" if tow_with else ""))
    lines.append(_row_always("גרירה ללא בלמים", f"{tow_without} ק\"ג" if tow_without else ""))
    return "".join(lines)


def cat_tires(record: dict, w: dict) -> str:
    front = _val(record, "zmig_kidmi")
    rear  = _val(record, "zmig_ahori", "zmig_achori")
    lines = ["*🔧 גלגלים וצמיגים*\n"]
    lines.append(_row_always("צמיג קדמי", front))
    lines.append(_row_always("צמיג אחורי", rear))
    return "".join(lines)


def cat_equipment(record: dict, w: dict) -> str:
    power_win = _val(w, "mispar_halonot_hashmal")
    lines = ["*🛋️ ציוד ונוחות*\n"]
    lines.append(_row_always("מיזוג אוויר", _yn_always(w.get("mazgan_ind"))))
    lines.append(_row_always("הגה כוח", _yn_always(w.get("hege_koah_ind"))))
    lines.append(_row_always("חלונות חשמל", f"{power_win} חלונות" if power_win else ""))
    lines.append(_row_always("גג פנורמי/שמש", _yn_always(w.get("halon_bagg_ind"))))
    lines.append(_row_always("חישוקי סגסוגת", _yn_always(w.get("galgaley_sagsoget_kala_ind"))))
    lines.append(_row_always("ארגז/תא מטען", _yn_always(w.get("argaz_ind"))))
    return "".join(lines)


def cat_safety(record: dict, w: dict) -> str:
    co2     = _val(w, "CO2_WLTP", "kamut_CO2")
    nox     = _val(w, "NOX_WLTP", "kamut_NOX")
    hc      = _val(w, "HC_WLTP", "kamut_HC")
    pm      = _val(w, "PM_WLTP", "kamut_PM10")
    co      = _val(w, "CO_WLTP", "kamut_CO")
    co2_city  = _val(w, "kamut_CO2_city")
    co2_hway  = _val(w, "kamut_CO2_hway")
    airbags = _val(w, "mispar_kariot_avir")

    lines = ["*🛡️ בטיחות ופליטות*\n"]
    lines.append(_row_always("ניקוד בטיחות", _val(w, "nikud_betihut")))
    lines.append(_row_always("רמת ציוד בטיחותי", _val(w, "ramat_eivzur_betihuty")))
    lines.append(_row_always("כריות אוויר", f"{airbags} כריות" if airbags else ""))
    lines.append(_row_always("ABS", _yn_always(w.get("abs_ind"))))
    lines.append(_row_always("בקרת יציבות ESP", _yn_always(w.get("bakarat_yatzivut_ind"))))
    lines.append(_row_always("קבוצת זיהום", _val(record, "kvuzat_zihum")))
    lines.append(_row_always("מדד ירוק", _val(w, "madad_yarok")))
    lines.append(_row_always("CO2 (WLTP)", f"{co2} גר'/ק\"מ" if co2 else ""))
    lines.append(_row_always("CO2 בעיר", f"{co2_city} גר'/ק\"מ" if co2_city else ""))
    lines.append(_row_always("CO2 בכביש", f"{co2_hway} גר'/ק\"מ" if co2_hway else ""))
    lines.append(_row_always("NOX", f"{nox} מ\"ג/ק\"מ" if nox else ""))
    lines.append(_row_always("HC", f"{hc}" if hc else ""))
    lines.append(_row_always("PM10", f"{pm}" if pm else ""))
    lines.append(_row_always("CO", f"{co}" if co else ""))
    return "".join(lines)


def cat_adas(record: dict, w: dict) -> str:
    lines = ["*🤖 מערכות ADAS*\n"]
    lines.append(_row_always("שמירת נתיב", _yn_always(w.get("bakarat_stiya_menativ_ind"))))
    lines.append(_row_always("בקרת סטייה אקטיבית", _yn_always(w.get("bakarat_stiya_activ_s"))))
    lines.append(_row_always("ניטור מרחק קדמי", _yn_always(w.get("nitur_merhak_milfanim_ind"))))
    lines.append(_row_always("זיהוי שטח עיוור", _yn_always(w.get("zihuy_beshetah_nistar_ind"))))
    lines.append(_row_always("בקרת שיוט אדפטיבית", _yn_always(w.get("bakarat_shyut_adaptivit_ind"))))
    lines.append(_row_always("בקרת מהירות ISA", _yn_always(w.get("bakarat_mehirut_isa"))))
    lines.append(_row_always("זיהוי הולכי רגל", _yn_always(w.get("zihuy_holchey_regel_ind"))))
    lines.append(_row_always("בלימת חירום אוטומטית", _yn_always(w.get("maarechet_ezer_labalam_ind"))))
    lines.append(_row_always("בלימה לפני הולכי רגל/אופניים", _yn_always(w.get("blimat_hirum_lifnei_holhei_regel_ofanaim"))))
    lines.append(_row_always("בלימה אוטומטית לאחור", _yn_always(w.get("blima_otomatit_nesia_leahor"))))
    lines.append(_row_always("מצלמת רוורס", _yn_always(w.get("matzlemat_reverse_ind"))))
    lines.append(_row_always("חיישני לחץ צמיגים", _yn_always(w.get("hayshaney_lahatz_avir_batzmigim_ind"))))
    lines.append(_row_always("חיישן עייפות נהג", _yn_always(w.get("hayshaney_hagorot_ind"))))
    lines.append(_row_always("זיהוי תמרורים", _yn_always(w.get("zihuy_tamrurey_tnua_ind"))))
    lines.append(_row_always("שליטה אוטו' בפנסי גבוה", _yn_always(w.get("shlita_automatit_beorot_gvohim_ind"))))
    lines.append(_row_always("התראת נסיעה קדימה", _yn_always(w.get("teura_automatit_benesiya_kadima_ind"))))
    lines.append(_row_always("זיהוי מצב התקרבות מסוכנת", _yn_always(w.get("zihuy_matzav_hitkarvut_mesukenet_ind"))))
    lines.append(_row_always("זיהוי אופניים/קורקינט", _yn_always(w.get("zihuy_rechev_do_galgali"))))
    lines.append(_row_always("נעילת אלכוהול", _yn_always(w.get("alco_lock"))))
    lines.append(_row_always("מתח סולל", _val(w, "dg_metach_solela")))
    return "".join(lines)


def cat_history(record: dict, w: dict) -> str:
    km = _val(record, "kilometer_test_aharon")
    changed_body  = record.get("shinui_mivne_ind")
    changed_color = record.get("shnui_zeva_ind")
    changed_tire  = record.get("shinui_zmig_ind")
    gapam         = record.get("gapam_ind")

    lines = ["*📅 היסטוריה ורישום*\n"]
    lines.append(_row_always("תאריך רישום ראשון", _format_date(record.get("rishum_rishon_dt"))))
    lines.append(_row_always("עלייה לכביש", _format_date(record.get("moed_aliya_lakvish"))))
    lines.append(_row_always("ק\"מ בטסט אחרון", f"{km} ק\"מ" if km else ""))
    lines.append(_row_always("טסט אחרון", _format_date(record.get("mivchan_acharon_dt"))))
    lines.append(f"• *{_escape('תוקף טסט')}:* {_escape(_test_status(record.get('tokef_dt')))}\n")
    lines.append(_row_always("שינוי מבנה", _yn_always(changed_body)))
    lines.append(_row_always("שינוי צבע", _yn_always(changed_color)))
    lines.append(_row_always("שינוי צמיגים", _yn_always(changed_tire)))
    lines.append(_row_always("GAPAM", _yn_always(gapam)))
    return "".join(lines)


def cat_recalls(record: dict) -> str:
    recalls = record.get("_recalls") or []
    if not recalls:
        return "*🔔 ריקולים*\n• לא נמצאו ריקולים לדגם זה\n"
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
    "general":   ("📋 פרטים כלליים", cat_general),
    "specs":     ("⚙️ מפרט טכני",    cat_specs),
    "tires":     ("🔧 גלגלים",       cat_tires),
    "equipment": ("🛋️ ציוד",         cat_equipment),
    "safety":    ("🛡️ בטיחות",       cat_safety),
    "adas":      ("🤖 ADAS",          cat_adas),
    "history":   ("📅 היסטוריה",      cat_history),
    "recalls":   ("🔔 ריקולים",       cat_recalls),
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
    baalut       = _ownership_label(record.get("baalut")) or "✖ לא קיים"
    mkoriut      = _val(record, "mkoriut_nm") or "✖ לא קיים"

    lines = [
        f"🚗 *{_escape(manufacturer)} {_escape(model)}*\n",
        "━━━━━━━━━━━━━━━━━━\n",
        f"• *{_escape('מספר רכב')}:* {_escape(plate)}\n",
        f"• *{_escape('דגם')}:* {_escape(model)}\n",
        f"• *{_escape('שנת ייצור')}:* {_escape(year)}\n" if year else f"• *{_escape('שנת ייצור')}:* ✖ לא קיים\n",
        f"• *{_escape('גימור')}:* {_escape(trim)}\n" if trim else f"• *{_escape('גימור')}:* ✖ לא קיים\n",
        f"• *{_escape('בעלות')}:* {_escape(baalut)}\n",
        f"• *{_escape('מקוריות')}:* {_escape(mkoriut)}\n",
        f"• *{_escape('עלייה לכביש')}:* {_escape(road_entry)}\n" if road_entry else f"• *{_escape('עלייה לכביש')}:* ✖ לא קיים\n",
        f"• *{_escape('תוקף טסט')}:* {_escape(test)}\n",
        f"• *{_escape('ק\"מ אחרון שדווח')}:* {_escape(km)} ק\"מ\n" if km else f"• *{_escape('ק\"מ אחרון שדווח')}:* ✖ לא קיים\n",
        "\n_בחר קטגוריה למידע נוסף_ ⬇️",
    ]
    return "".join(lines)


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
