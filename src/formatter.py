"""
Formats vehicle data into a clean Hebrew Telegram message (MarkdownV2).
"""

from datetime import datetime, date
from typing import Optional


def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


def _format_date(raw: Optional[str]) -> str:
    if not raw:
        return "לא ידוע"
    try:
        dt = datetime.fromisoformat(raw[:10])
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return raw[:10] if raw else "לא ידוע"


def _test_status(tokef_raw: Optional[str]) -> str:
    """Return emoji + text describing test (טסט) validity."""
    if not tokef_raw:
        return "❓ לא ידוע"
    try:
        tokef = date.fromisoformat(tokef_raw[:10])
        today = date.today()
        delta = (tokef - today).days
        if delta < 0:
            return f"🔴 פג תוקף לפני {abs(delta)} ימים"
        if delta <= 30:
            return f"🟡 פג תוקף בעוד {delta} ימים"
        return f"🟢 בתוקף עד {tokef.strftime('%d/%m/%Y')}"
    except Exception:
        return "❓ לא ידוע"


def _ownership_label(baalut: Optional[str]) -> str:
    mapping = {
        "1": "ראשונה",
        "2": "שנייה",
        "3": "שלישית",
        "4": "רביעית",
        "5": "חמישית ומעלה",
    }
    if not baalut:
        return "לא ידוע"
    return mapping.get(str(baalut).strip(), str(baalut))


def format_vehicle_message(record: dict, stolen: Optional[bool]) -> str:
    """Build the full Telegram MarkdownV2 message for a vehicle."""

    plate = str(record.get("mispar_rechev", "")).strip()
    manufacturer = record.get("tozeret_nm", "לא ידוע")
    model = record.get("kinuy_mishari") or record.get("degem_nm") or "לא ידוע"
    year = record.get("shnat_yitzur", "לא ידוע")
    color = record.get("tzeva_rechev", "לא ידוע")
    fuel = record.get("sug_delek_nm", "לא ידוע")
    tokef_raw = record.get("tokef_dt")
    last_test = _format_date(record.get("mivchan_acharon_dt"))
    ownership = _ownership_label(record.get("baalut"))
    first_reg = _format_date(record.get("rishum_rishon_dt"))
    road_entry = _format_date(record.get("moed_aliya_lakvish"))
    engine_cc = record.get("nefach_manoa", "")
    horse_power = record.get("koah_sus", "")
    seats = record.get("mispar_moshavim", "")
    doors = record.get("mispar_dlatot", "")
    weight = record.get("mishkal_kolel", "")
    pollution = record.get("kvuzat_zihum", "")
    vehicle_type = record.get("sug_rechev_nm", "")
    chassis = record.get("misgeret", "")
    front_tire = record.get("zmig_kidmi", "")
    rear_tire = record.get("zmig_achori", "")

    test_line = _test_status(tokef_raw)

    # Stolen status
    if stolen is True:
        stolen_line = "🚨 *רכב זה מדווח כגנוב במשטרה\\!*"
    elif stolen is False:
        stolen_line = "✅ לא מדווח כגנוב"
    else:
        stolen_line = "❓ בדיקת גנבה לא זמינה"

    def row(label: str, value) -> str:
        if not value or str(value).strip() in ("", "None", "nan"):
            return ""
        return f"• *{_escape(label)}:* {_escape(str(value))}\n"

    lines = []
    lines.append(f"🚗 *מידע על רכב {_escape(plate)}*\n")
    lines.append(f"{stolen_line}\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("*📋 פרטים כלליים*\n")
    lines.append(row("יצרן", manufacturer))
    lines.append(row("דגם", model))
    lines.append(row("שנת ייצור", year))
    lines.append(row("צבע", color))
    lines.append(row("סוג רכב", vehicle_type))
    lines.append(row("בעלות", ownership))

    lines.append("\n*⛽ מנוע ומפרט*\n")
    lines.append(row("סוג דלק", fuel))
    lines.append(row("נפח מנוע", f"{engine_cc} סמ\"ק" if engine_cc else ""))
    lines.append(row("כוח סוס", horse_power))
    lines.append(row("מספר מושבים", seats))
    lines.append(row("מספר דלתות", doors))
    lines.append(row("משקל כולל", f"{weight} ק\"ג" if weight else ""))
    lines.append(row("קבוצת זיהום", pollution))

    lines.append("\n*🔧 גלגלים ומסגרת*\n")
    lines.append(row("מסגרת (שלדה)", chassis))
    lines.append(row("צמיג קדמי", front_tire))
    lines.append(row("צמיג אחורי", rear_tire))

    lines.append("\n*📅 תאריכים ורישום*\n")
    lines.append(row("תאריך רישום ראשון", first_reg))
    lines.append(row("עלייה לכביש", road_entry))
    lines.append(row("טסט אחרון", last_test))
    lines.append(f"• *{_escape('תוקף טסט')}:* {_escape(test_line)}\n")

    # Filter empty rows
    result = "".join(l for l in lines if l)
    return result


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
