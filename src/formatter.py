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

# אגרת רישוי לפי קבוצה (1-15) וגיל רכב: 0-3 / 4-7 / 8-11 / 12+
# אגרת רישוי 2024 — 7 קבוצות × 3 טווחי גיל
# (עד 3 שנים, 4–10 שנים, 11+ שנים)
# רכבי 2000 ומטה — 25% מהאגרה הרגילה
_AGRA_TABLE = {
    1: (1_012,   759,   506),
    2: (1_417,  1_063,   709),
    3: (1_822,  1_367,   911),
    4: (2_480,  1_860,  1_240),
    5: (3_290,  2_468,  1_645),
    6: (4_352,  3_264,  2_176),
    7: (5_771,  4_328,  2_886),
}
_AGRA_ELECTRIC = 177   # אגרה סמלית לרכב חשמלי (כל קבוצה/גיל)


def _agra_from_group(code, shnat_yitzur=None, sug_delek_nm=None) -> str:
    try:
        grp = int(code)
        row = _AGRA_TABLE.get(grp)
        if not row:
            return ""

        # חשמלי — אגרה סמלית
        fuel = (sug_delek_nm or "").strip()
        if any(w in fuel for w in ("חשמל", "electric", "ELECTRIC", "חשמלי")):
            return f"₪{_AGRA_ELECTRIC:,} \\(חשמלי — אגרה מופחתת\\)"

        year = int(shnat_yitzur) if shnat_yitzur else date.today().year
        age  = date.today().year - year

        # רכב 2000 ומטה — 25% מהאגרה הרגילה
        if year <= 2000:
            amount = round(row[2] * 0.25)
            note   = "ייצור 2000 ומטה"
        elif age <= 3:
            amount = row[0]
            note   = f"גיל {age} שנים"
        elif age <= 10:
            amount = row[1]
            note   = f"גיל {age} שנים"
        else:
            amount = row[2]
            note   = f"גיל {age} שנים"

        return f"₪{amount:,} \\(קבוצה {grp}, {note}\\)"
    except Exception:
        return ""


def cat_general(record: dict, w: dict) -> str:
    lines = ["*📋 פרטים כלליים*\n"]
    lines.append(_row_always("יצרן", _val(record, "tozeret_nm")))
    lines.append(_row_always("דגם", _val(record, "kinuy_mishari", "degem_nm")))
    lines.append(_row_always("רמת גימור", _val(w, "ramat_gimur")))
    lines.append(_row_always("שנת ייצור", _val(record, "shnat_yitzur")))
    lines.append(_row_always("צבע", _val(record, "tzeva_rechev")))
    lines.append(_row_always("בעלות נוכחית", _val(record, "baalut")))
    lines.append(_row_always("ארץ ייצור", _val(w, "tozeret_eretz_nm")))
    lines.append(_row_always("יבואן/תוצר", _val(w, "tozar")))
    lines.append(_row_always("סוג מרכב", _val(w, "merkav")))
    lines.append(_row_always("סוג תקינה", _val(w, "sug_tkina_nm")))
    lines.append(_row_always("מסגרת (שלדה)", _val(record, "misgeret")))
    lines.append(_row_always("דגם מנוע", _val(record, "degem_manoa")))
    lines.append(_row_always("מספר מנוע", _val(record, "mispar_manoa")))
    lines.append(_row_always("מקוריות", _val(record, "mkoriut_nm")))
    agra_group = _val(w, "kvuzat_agra_cd")
    shnat      = _val(record, "shnat_yitzur")
    sug_delek  = _val(record, "sug_delek_nm") or _val(w, "sug_delek_nm")
    agra_str   = _agra_from_group(agra_group, shnat, sug_delek) if agra_group else ""
    if agra_str:
        lines.append(_row_always("אגרת רישוי שנתית", agra_str))
        lines.append(f"  _\\* מחיר משוער לפי קבוצת אגרה וגיל הרכב_\n")

    importer_price = record.get("_importer_price")
    if importer_price:
        try:
            price_int = int(float(importer_price))
            lines.append(_row_always("מחיר יבואן (חדש)", f"₪{price_int:,}"))
            shnat = record.get("shnat_yitzur")
            if shnat:
                from datetime import date as _date
                age = _date.today().year - int(shnat)
                if age > 0:
                    dep_pct = min(age * 8, 70)
                    est = int(price_int * (1 - dep_pct / 100))
                    lines.append(_row_always("הערכת שווי יד\\-2", f"~₪{est:,} \\(ירידת ערך ≈{dep_pct}%\\)"))
        except Exception:
            pass

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
    lines.append(_row_always("קבוצת זיהום", _val(record, "kvutzat_zihum", "kvuzat_zihum")))
    lines.append(_row_always("מדד ירוק", _val(w, "madad_yarok")))
    co2_nedc = _val(w, "CO2_WLTP_NEDC")
    lines.append(_row_always("CO2 (WLTP)", f"{co2} גר'/ק\"מ" if co2 else ""))
    lines.append(_row_always("CO2 (NEDC)", f"{co2_nedc} גר'/ק\"מ" if co2_nedc else ""))
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
    lines.append(_row_always("התנגשות קרקע מת", _yn_always(w.get("hitnagshut_cad_shetah_met"))))
    lines.append(_row_always("מתח סולל", _val(w, "dg_metach_solela")))
    return "".join(lines)


def _format_tag_nache_date(raw) -> str:
    try:
        s = str(int(raw))
        if len(s) == 8:
            return f"{s[6:8]}/{s[4:6]}/{s[:4]}"
    except Exception:
        pass
    return str(raw) if raw else ""


def cat_history(record: dict, w: dict) -> str:
    km = _val(record, "kilometer_test_aharon")
    changed_body  = record.get("shinui_mivne_ind")
    changed_color = record.get("shnui_zeva_ind")
    changed_tire  = record.get("shinui_zmig_ind")
    gapam         = record.get("gapam_ind")
    tag_nache     = record.get("_tag_nache")
    was_rental    = record.get("_was_rental", False)

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

    if tag_nache:
        hafakat = _format_tag_nache_date(tag_nache.get("hafakat"))
        lines.append(f"• *{_escape('תו נכה')}:* ✅ כן \\(הופק: {_escape(hafakat)}\\)\n" if hafakat else f"• *{_escape('תו נכה')}:* ✅ כן\n")
    else:
        lines.append(f"• *{_escape('תו נכה')}:* ❌ לא\n")

    lines.append(_row_always("רכב שכור בעבר", "✅ כן" if was_rental else "❌ לא"))
    return "".join(lines)


def cat_ownership(record: dict, w: dict) -> str:
    ownership = record.get("_ownership") or []

    if not ownership:
        return "*👥 היסטוריית בעלויות*\n• לא נמצא מידע על בעלויות קודמות\n"

    # Count unique owners (private transitions)
    private_count = sum(1 for o in ownership if o.get("baalut") == "פרטי")
    dealer_count  = sum(1 for o in ownership if o.get("baalut") == "סוחר")
    total         = len(ownership)

    def _fmt_baalut_dt(dt: str) -> str:
        try:
            y, m = str(dt)[:4], str(dt)[4:6]
            months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                      "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
            return f"{months[int(m)]} {y}"
        except Exception:
            return str(dt)

    lines = [f"*👥 היסטוריית בעלויות*\n"]
    lines.append(f"• *{_escape('סה\"כ רשומות')}:* {_escape(str(total))}\n")
    lines.append(f"• *{_escape('בעלויות פרטיות')}:* {_escape(str(private_count))}\n")
    lines.append(f"• *{_escape('עברו דרך סוחר')}:* {_escape(str(dealer_count))}\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    for i, o in enumerate(ownership, 1):
        dt      = _fmt_baalut_dt(o.get("baalut_dt", ""))
        baalut  = o.get("baalut", "לא ידוע")
        emoji   = "👤" if baalut == "פרטי" else "🏢" if baalut == "סוחר" else "❓"
        lines.append(f"*{_escape(str(i))}\\.* {emoji} {_escape(baalut)} — {_escape(dt)}\n")

    return "".join(lines)


def _check_km_fraud(record: dict) -> str:
    """
    Basic km fraud detection using last reported km vs ownership timeline.
    Returns a warning string or empty string if ok.
    """
    km = record.get("kilometer_test_aharon")
    if not km:
        return ""
    try:
        km_val = int(float(str(km)))
    except Exception:
        return ""

    ownership = record.get("_ownership") or []
    first_dt = ownership[0].get("baalut_dt", "") if ownership else ""
    try:
        year_start = int(str(first_dt)[:4])
        from datetime import date
        years = date.today().year - year_start
        if years > 0:
            avg_km_per_year = km_val / years
            if avg_km_per_year < 3000:
                return f"⚠️ ק\"מ נמוך מאוד \\({_escape(str(km_val))} ב\\-{_escape(str(years))} שנים\\) — בדוק זיוף"
            if avg_km_per_year > 50000:
                return f"⚠️ ק\"מ גבוה מאוד \\({_escape(str(km_val))} ב\\-{_escape(str(years))} שנים\\)"
    except Exception:
        pass
    return ""


def cat_recalls(record: dict) -> str:
    recalls = record.get("_recalls") or []
    by_plate = record.get("_recalls_by_plate", False)

    if not recalls:
        label = "לרכב זה" if by_plate else "לדגם זה"
        return f"*🔔 ריקולים*\n• לא נמצאו ריקולים {_escape(label)}\n"

    lines = [f"*🔔 ריקולים \\({_escape(str(len(recalls)))}\\)*\n"]

    if by_plate:
        # hagbalat_recall fields: SUG_RECALL, SUG_TAKALA, TEUR_TAKALA, TAARICH_PTICHA
        for r in recalls:
            teur     = r.get("TEUR_TAKALA", "")
            kategory = r.get("SUG_TAKALA", "")
            sug      = r.get("SUG_RECALL", "")
            taarich  = str(r.get("TAARICH_PTICHA", ""))[:10]
            if teur:
                line = f"• *{_escape(taarich)}*"
                if kategory:
                    line += f" \\| {_escape(kategory)}"
                line += f"\n  {_escape(str(teur)[:120])}"
                if sug:
                    line += f"\n  _סוג: {_escape(sug)}_"
                lines.append(line + "\n")
    else:
        # legacy RES_RECALL fields: SHNAT_RECALL, TEUR_TAKALA, OFEN_TIKUN
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
    "ownership": ("👥 בעלויות",       cat_ownership),
    "recalls":   ("🔔 ריקולים",       cat_recalls),
}


def get_summary(record: dict) -> str:
    """Returns full vehicle report – all categories combined."""
    w = record.get("_wltp") or {}

    plate        = _val(record, "mispar_rechev")
    manufacturer = _val(record, "tozeret_nm")
    model        = _val(record, "kinuy_mishari", "degem_nm")
    km_fraud_warning = _check_km_fraud(record)

    scrapped_dt  = record.get("_scrapped_dt", "")
    scrapped_warning = ""
    if scrapped_dt:
        dt_str = _format_date(scrapped_dt)
        scrapped_warning = (
            f"🚨 *אזהרה\\: רכב זה בוטל רשמית \\(גרוטאה\\)*\n"
            f"• תאריך ביטול: *{_escape(dt_str)}*\n"
            f"• רכב זה אינו רשאי לנסוע על הכביש\\!\n"
            "━━━━━━━━━━━━━━━━━━\n"
        )

    sections = [
        f"🚗 *{_escape(manufacturer)} {_escape(model)}*\n",
        "━━━━━━━━━━━━━━━━━━\n",
        f"• *{_escape('מספר רכב')}:* {_escape(plate)}\n\n",
        scrapped_warning,
        cat_general(record, w) + "\n",
        cat_specs(record, w) + "\n",
        cat_tires(record, w) + "\n",
        cat_equipment(record, w) + "\n",
        cat_safety(record, w) + "\n",
        cat_adas(record, w) + "\n",
        cat_history(record, w) + "\n",
        cat_ownership(record, w) + "\n",
        cat_recalls(record),
    ]

    if km_fraud_warning:
        sections.append(f"\n{km_fraud_warning}\n")

    return "".join(s for s in sections if s)


def get_category_text(category: str, record: dict) -> str:
    w = record.get("_wltp") or {}
    if category == "recalls":
        return cat_recalls(record)
    if category == "ownership":
        return cat_ownership(record, w)
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
