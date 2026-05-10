"""
Formats vehicle data into a clean Hebrew Telegram message (MarkdownV2).
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
    """Convert 1/0/True/False/Y/N to readable Hebrew."""
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


def row(label: str, value) -> str:
    v = str(value).strip() if value else ""
    if not v or v in ("None", "nan", "0"):
        return ""
    return f"• *{_escape(label)}:* {_escape(v)}\n"


def format_vehicle_message(record: dict) -> str:
    plate        = _val(record, "mispar_rechev")
    manufacturer = _val(record, "tozeret_nm")
    model        = _val(record, "kinuy_mishari", "degem_nm")
    year         = _val(record, "shnat_yitzur")
    color        = _val(record, "tzeva_rechev")
    fuel         = _val(record, "sug_delek_nm")
    tokef_raw    = record.get("tokef_dt")
    last_test    = _format_date(record.get("mivchan_acharon_dt"))
    ownership    = _ownership_label(record.get("baalut"))
    first_reg    = _format_date(record.get("rishum_rishon_dt"))
    road_entry   = _format_date(record.get("moed_aliya_lakvish"))
    chassis      = _val(record, "misgeret")
    front_tire   = _val(record, "zmig_kidmi")
    rear_tire    = _val(record, "zmig_ahori", "zmig_achori")
    pollution    = _val(record, "kvuzat_zihum")
    vehicle_type = _val(record, "sug_rechev_nm")

    # History fields
    engine_num   = _val(record, "mispar_manoa")
    km           = _val(record, "kilometer_test_aharon")
    originality  = _val(record, "mkoriut_nm")
    changed_body = _yn(record.get("shinui_mivne_ind"))
    changed_color= _yn(record.get("shnui_zeva_ind"))
    changed_tire = _yn(record.get("shinui_zmig_ind"))
    gapam        = _yn(record.get("gapam_ind"))

    # WLTP fields
    w = record.get("_wltp") or {}
    engine_cc    = _val(w, "nefah_manoa") or _val(record, "nefach_manoa")
    horse_power  = _val(w, "koah_sus")
    seats        = _val(w, "mispar_moshavim")
    doors        = _val(w, "mispar_dlatot")
    weight       = _val(w, "mishkal_kolel")
    height       = _val(w, "gova")
    wheelbase    = _val(w, "merkav")
    tow_with     = _val(w, "kosher_grira_im_blamim")
    tow_without  = _val(w, "kosher_grira_bli_blamim")
    trim         = _val(w, "ramat_gimur")
    transmission = _yn(w.get("automatic_ind")) if w.get("automatic_ind") is not None else ""
    airbags      = _val(w, "mispar_kariot_avir")
    abs_sys      = _yn(w.get("abs_ind"))
    ac           = _yn(w.get("mazgan_ind"))
    power_win    = _val(w, "mispar_halonot_hashmal")
    sunroof      = _yn(w.get("halon_bagg_ind"))
    power_steer  = _yn(w.get("hege_koah_ind"))
    alloy_wheels = _yn(w.get("galgaley_sagsoget_kala_ind"))
    trunk        = _yn(w.get("argaz_ind"))
    safety_score = _val(w, "nikud_betihut")
    safety_level = _val(w, "ramat_eivzur_betihuty")
    co2          = _val(w, "CO2_WLTP", "kamut_CO2")
    nox          = _val(w, "NOX_WLTP", "kamut_NOX")
    green_index  = _val(w, "madad_yarok")
    # ADAS
    adas_lane    = _yn(w.get("bakarat_stiya_menativ_ind"))
    adas_dist    = _yn(w.get("nitur_merhak_milfanim_ind"))
    adas_blind   = _yn(w.get("zihuy_beshetah_nistar_ind"))
    adas_acc     = _yn(w.get("bakarat_shyut_adaptivit_ind"))
    adas_ped     = _yn(w.get("zihuy_holchey_regel_ind"))
    adas_aeb     = _yn(w.get("maarechet_ezer_labalam_ind"))
    adas_cam     = _yn(w.get("matzlemat_reverse_ind"))
    adas_tpms    = _yn(w.get("hayshaney_lahatz_avir_batzmigim_ind"))
    adas_fatigue = _yn(w.get("hayshaney_hagorot_ind"))
    adas_sign    = _yn(w.get("zihuy_tamrurey_tnua_ind"))
    adas_hbeam   = _yn(w.get("shlita_automatit_beorot_gvohim_ind"))
    adas_fwd_warn= _yn(w.get("teura_automatit_benesiya_kadima_ind"))
    adas_cyclist = _yn(w.get("zihuy_rechev_do_galgali"))
    alco_lock    = _yn(w.get("alco_lock"))

    # Recalls
    recalls = record.get("_recalls") or []

    lines = []
    lines.append(f"🚗 *מידע על רכב {_escape(plate)}*\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    # --- פרטים כלליים ---
    lines.append("*📋 פרטים כלליים*\n")
    lines.append(row("יצרן", manufacturer))
    lines.append(row("דגם", model))
    lines.append(row("רמת גימור", trim))
    lines.append(row("שנת ייצור", year))
    lines.append(row("צבע", color))
    lines.append(row("סוג רכב", vehicle_type))
    lines.append(row("בעלות", ownership))
    lines.append(row("מקוריות", originality))
    lines.append(row("מסגרת (שלדה)", chassis))
    lines.append(row("מספר מנוע", engine_num))

    # --- מפרט טכני ---
    lines.append("\n*⚙️ מפרט טכני*\n")
    lines.append(row("סוג דלק", fuel))
    lines.append(row("נפח מנוע", f"{engine_cc} סמ\"ק" if engine_cc else ""))
    lines.append(row("כוח סוס", horse_power))
    lines.append(row("תיבת הילוכים", "אוטומטית" if transmission == "✅ כן" else ("ידנית" if transmission == "❌ לא" else "")))
    lines.append(row("מושבים", seats))
    lines.append(row("דלתות", doors))
    lines.append(row("משקל כולל", f"{weight} ק\"ג" if weight else ""))
    lines.append(row("גובה", f"{height} מ\"מ" if height else ""))
    lines.append(row("מרחק סרנים", f"{wheelbase} מ\"מ" if wheelbase else ""))
    lines.append(row("גרירה עם בלמים", f"{tow_with} ק\"ג" if tow_with else ""))
    lines.append(row("גרירה ללא בלמים", f"{tow_without} ק\"ג" if tow_without else ""))

    # --- גלגלים ---
    lines.append("\n*🔧 גלגלים*\n")
    lines.append(row("צמיג קדמי", front_tire))
    lines.append(row("צמיג אחורי", rear_tire))

    # --- ציוד ונוחות ---
    lines.append("\n*🛋️ ציוד ונוחות*\n")
    lines.append(row("מיזוג אוויר", ac))
    lines.append(row("הגה כוח", power_steer))
    lines.append(row("חלונות חשמל", f"{power_win} חלונות" if power_win else ""))
    lines.append(row("גג פנורמי/שמש", sunroof))
    lines.append(row("חישוקי סגסוגת", alloy_wheels))
    lines.append(row("ארגז (SUV/קומבי)", trunk))

    # --- בטיחות ---
    lines.append("\n*🛡️ בטיחות*\n")
    lines.append(row("ניקוד בטיחות", safety_score))
    lines.append(row("רמת ציוד בטיחותי", safety_level))
    lines.append(row("כריות אוויר", f"{airbags} כריות" if airbags else ""))
    lines.append(row("ABS", abs_sys))
    lines.append(row("קבוצת זיהום", pollution))
    lines.append(row("מדד ירוק", green_index))
    lines.append(row("CO2", f"{co2} גר'/ק\"מ" if co2 else ""))
    lines.append(row("NOX", f"{nox} מ\"ג/ק\"מ" if nox else ""))

    # --- מערכות ADAS ---
    adas_rows = [
        row("שמירת נתיב", adas_lane),
        row("ניטור מרחק קדמי", adas_dist),
        row("זיהוי שטח עיוור", adas_blind),
        row("בקרת שיוט אדפטיבית", adas_acc),
        row("זיהוי הולכי רגל", adas_ped),
        row("בלימת חירום אוטומטית", adas_aeb),
        row("מצלמת רוורס", adas_cam),
        row("חיישני לחץ צמיגים", adas_tpms),
        row("חיישן עייפות נהג", adas_fatigue),
        row("זיהוי תמרורים", adas_sign),
        row("שליטה אוטומטית פנסי גבוהים", adas_hbeam),
        row("התראת נסיעה קדימה", adas_fwd_warn),
        row("זיהוי אופניים/קורקינט", adas_cyclist),
        row("נעילת אלכוהול", alco_lock),
    ]
    adas_content = "".join(r for r in adas_rows if r)
    if adas_content:
        lines.append("\n*🤖 מערכות ADAS*\n")
        lines.append(adas_content)

    # --- שינויים ---
    changes = [
        row("שינוי מבנה", changed_body),
        row("שינוי צבע", changed_color),
        row("שינוי צמיגים", changed_tire),
        row("GAPAM", gapam),
    ]
    changes_content = "".join(r for r in changes if r and "לא" not in r)
    if changes_content:
        lines.append("\n*⚠️ שינויים ברכב*\n")
        lines.append(changes_content)

    # --- היסטוריה ---
    lines.append("\n*📅 היסטוריה ורישום*\n")
    lines.append(row("תאריך רישום ראשון", first_reg))
    lines.append(row("עלייה לכביש", road_entry))
    lines.append(row("ק\"מ בטסט אחרון", f"{km} ק\"מ" if km else ""))
    lines.append(row("טסט אחרון", last_test))
    lines.append(f"• *{_escape('תוקף טסט')}:* {_escape(_test_status(tokef_raw))}\n")

    # --- ריקולים ---
    if recalls:
        lines.append(f"\n*🔔 ריקולים \\({_escape(str(len(recalls)))}\\)*\n")
        for r_item in recalls[:3]:
            teur = r_item.get("TEUR_TAKALA", "")
            ofen = r_item.get("OFEN_TIKUN", "")
            shnat = r_item.get("SHNAT_RECALL", "")
            if teur:
                lines.append(f"• {_escape(str(shnat))}: {_escape(str(teur))}")
                if ofen:
                    lines.append(f" \\({_escape(str(ofen))}\\)")
                lines.append("\n")
        if len(recalls) > 3:
            lines.append(f"_ועוד {_escape(str(len(recalls)-3))} ריקולים נוספים_\n")

    return "".join(l for l in lines if l)


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
