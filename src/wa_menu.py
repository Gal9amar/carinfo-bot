"""
WhatsApp text menus and response formatters.
All output is plain text — no Markdown, no inline keyboards.
"""

from src.formatter import get_summary as _tg_summary, yad2_label

WELCOME = (
    "👋 *ברוך הבא ל-CarInfo!*\n"
    "─────────────────\n"
    "🔍 שלח מספר רכב לחיפוש\n"
    "     _לדוגמה: 1234567_\n\n"
    "📋 *תפריט:*\n"
    "1️⃣  סטטוס חשבון\n"
    "2️⃣  רכישת חבילה\n"
    "3️⃣  קוד הטבה\n"
    "4️⃣  איך זה עובד?\n"
    "5️⃣  היסטוריית חיפושים\n"
    "6️⃣  הורדת דוח PDF"
)

NO_HISTORY = (
    "📜 אין היסטוריית חיפושים עדיין.\n\n"
    "שלח מספר רכב לחיפוש ראשון!"
)

EXPIRY_WARNING = (
    "⚠️ *המנוי שלך פג!*\n"
    "─────────────────\n"
    "נגמרו הבדיקות הזמינות.\n\n"
    "2️⃣  שלח *2* לרכישת חבילה\n"
    "3️⃣  שלח *3* אם יש לך קוד הטבה"
)

HELP = (
    "ℹ️ *איך CarInfo עובד?*\n"
    "─────────────────\n"
    "שלח מספר לוחית → קבל דוח מיידי:\n\n"
    "📋 פרטים כלליים\n"
    "⚙️ מפרט טכני\n"
    "🔧 גלגלים וצמיגים\n"
    "🛡️ בטיחות ו-ADAS\n"
    "📅 היסטוריה ובעלויות\n"
    "🔔 ריקולים\n\n"
    "─────────────────\n"
    "🆓 *20 חיפושים חינמיים* למשתמש חדש\n\n"
    "💰 *חבילות:*\n"
    "• 50 חיפושים ← ₪10\n"
    "• 100 חיפושים ← ₪20\n"
    "• 200 חיפושים ← ₪30\n"
    "• ♾️ מנוי חודשי ← ₪25\n\n"
    "⬅️ לתפריט: שלח *תפריט*"
)

PACKAGES = (
    "🛒 *בחר חבילת חיפושים:*\n"
    "─────────────────\n"
    "1️⃣  50 חיפושים — ₪10\n"
    "2️⃣  100 חיפושים — ₪20\n"
    "3️⃣  200 חיפושים — ₪30\n"
    "4️⃣  ♾️ מנוי חודשי — ₪25\n"
    "─────────────────\n"
    "שלח מספר 1-4 לבחירה\n"
    "⬅️ ביטול: שלח *תפריט*"
)

PACKAGE_DETAILS = {
    "1": ("50 חיפושים", 50,  10),
    "2": ("100 חיפושים", 100, 20),
    "3": ("200 חיפושים", 200, 30),
    "4": ("מנוי חודשי ללא הגבלה", -1, 25),
}

PAYMENT_REQUEST = (
    "💳 *{label} — ₪{price}*\n"
    "─────────────────\n"
    "1. לחץ על הקישור לתשלום:\n"
    "{paypal_url}\n\n"
    "2. השלם את התשלום ב-PayPal\n\n"
    "3. חזור לכאן ושלח:\n"
    "    ✅ *שילמתי*\n\n"
    "─────────────────\n"
    "_הגישה תיפתח תוך מספר דקות לאחר אישור_\n\n"
    "⬅️ ביטול: שלח *תפריט*"
)

ENTER_CODE = (
    "🎟️ *הזן קוד הטבה*\n"
    "─────────────────\n"
    "שלח את הקוד שקיבלת\n\n"
    "⬅️ ביטול: שלח *תפריט*"
)

BLOCKED = (
    "🚫 *הגישה שלך חסומה*\n\n"
    "לפרטים או ערעור — פנה למנהל."
)

NO_QUOTA = (
    "🔒 *נגמרו הבדיקות שלך*\n"
    "─────────────────\n"
    "2️⃣  שלח *2* לרכישת חבילה\n"
    "3️⃣  שלח *3* אם יש לך קוד הטבה"
)

LAST_FREE = "⚠️ _זוהי הבדיקה החינמית האחרונה שלך_"

SEARCHING = "🔍 _מחפש נתונים..._"

PDF_PREPARING = "📄 _מכין את קובץ הדוח... אנא המתן._"

NOT_FOUND = "❌ לא נמצאו נתונים עבור *{plate}*\n\nבדוק את המספר ונסה שוב."

ERROR = "⚠️ שגיאה בשליפת הנתונים. נסה שוב עוד רגע."

INVALID_PLATE = "🔢 שלח מספר רכב תקין\n_לדוגמה: 1234567_"

CANCEL = "✅ בוטל.\n\n⬅️ לתפריט: שלח *תפריט*"


def format_status(left: int, expires: str | None = None) -> str:
    if left == -1:
        if expires:
            try:
                from datetime import datetime as _dt
                exp_str = _dt.fromisoformat(expires[:10]).strftime("%d/%m/%Y")
            except Exception:
                exp_str = expires[:10]
            return f"♾️ מנוי חודשי פעיל עד {exp_str}"
        return "✅ גישה בלתי מוגבלת"
    if left == 0:
        return "🔒 אין בדיקות זמינות\nשלח *2* לרכישה"
    emoji = "🟢" if left > 5 else ("🟡" if left > 1 else "🔴")
    label = "בדיקות" if left != 1 else "בדיקה"
    return f"{emoji} נותרו לך *{left}* {label}"


def format_status_full(left: int, expires: str | None = None) -> str:
    """Full status message with menu hint."""
    status = format_status(left, expires)
    return (
        f"📊 *סטטוס חשבון*\n"
        f"─────────────────\n"
        f"{status}\n\n"
        f"─────────────────\n"
        f"2️⃣  שלח *2* לרכישת חבילה\n"
        f"3️⃣  שלח *3* להזנת קוד הטבה"
    )


def _strip_md(text: str) -> str:
    import re
    text = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", text)
    text = re.sub(r"[*_`]", "", text)
    return text


def format_result(
    record: dict,
    left: int,
    expires: str | None = None,
    plate: str = "",
    yad2_link: str = "",
) -> str:
    """Plain-text WhatsApp vehicle report."""
    raw    = _tg_summary(record)
    plain  = _strip_md(raw)
    status = format_status(left, expires)

    yad2_block = ""
    if yad2_link:
        label = yad2_label(record)
        yad2_block = f"🔍 *מחירים ב-Yad2* ({label}):\n{yad2_link}\n\n"

    return (
        f"{plain}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{status}\n\n"
        f"{yad2_block}"
        f"📄 לדוח PDF — שלח *6*\n"
        f"🔁 לחיפוש נוסף — שלח מספר רכב\n"
        f"📋 לתפריט — שלח *תפריט*\n\n"
        f"⚠️ המידע נאסף ממאגרים ממשלתיים וציבוריים. CarInfo ומפעיל הבוט אינם אחראים לנכונות הנתונים. אין להסתמך על כך כתחליף לבדיקה מקצועית."
    )
