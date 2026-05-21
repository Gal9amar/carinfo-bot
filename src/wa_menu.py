"""
WhatsApp text menus and response formatters.
All output is plain text — no Markdown, no inline keyboards.
"""

from src.formatter import get_summary as _tg_summary

WELCOME = (
    "👋 ברוך הבא ל-CarInfo!\n\n"
    "שלח מספר לוחית רישוי לחיפוש רכב (למשל: 1234567)\n\n"
    "או בחר פעולה:\n"
    "1 - סטטוס חשבון\n"
    "2 - רכישת חבילה\n"
    "3 - הזן קוד הטבה\n"
    "4 - איך זה עובד?"
)

HELP = (
    "ℹ️ איך CarInfo עובד?\n\n"
    "שלח מספר לוחית רישוי ותקבל דוח מלא:\n"
    "• פרטים כלליים\n"
    "• מפרט טכני\n"
    "• גלגלים\n"
    "• ציוד ובטיחות\n"
    "• ADAS\n"
    "• היסטוריה ובעלויות\n"
    "• ריקולים\n\n"
    "כל משתמש חדש מקבל 20 חיפושים חינמיים.\n\n"
    "חבילות:\n"
    "• 50 חיפושים — ₪10\n"
    "• 100 חיפושים — ₪20\n"
    "• 200 חיפושים — ₪30\n"
    "• מנוי חודשי ללא הגבלה — ₪25\n\n"
    "לתפריט הראשי שלח: תפריט"
)

PACKAGES = (
    "🛒 חבילות חיפוש:\n\n"
    "1 - 50 חיפושים — ₪10\n"
    "2 - 100 חיפושים — ₪20\n"
    "3 - 200 חיפושים — ₪30\n"
    "4 - מנוי חודשי ללא הגבלה — ₪25\n\n"
    "שלח את מספר החבילה הרצויה\n"
    "או שלח 'תפריט' לחזרה."
)

PACKAGE_DETAILS = {
    "1": ("50 חיפושים", 50,  10),
    "2": ("100 חיפושים", 100, 20),
    "3": ("200 חיפושים", 200, 30),
    "4": ("מנוי חודשי ללא הגבלה", -1, 25),
}

PAYMENT_REQUEST = (
    "💳 לרכישת חבילה *{label}* במחיר ₪{price}:\n\n"
    "שלם דרך PayPal:\n"
    "{paypal_url}\n\n"
    "לאחר התשלום שלח:\n"
    "שילמתי {label}\n\n"
    "הגישה תיפתח לאחר אישור ידני. בדרך כלל תוך מספר דקות.\n\n"
    "לחזרה לתפריט שלח: תפריט"
)

ENTER_CODE = (
    "🎟️ שלח את קוד ההטבה שקיבלת.\n"
    "לביטול שלח: תפריט"
)

BLOCKED = (
    "🚫 הגישה שלך חסומה.\n"
    "לפרטים פנה למנהל."
)

NO_QUOTA = (
    "🔒 נגמרו הבדיקות החינמיות שלך.\n\n"
    "לרכישת חבילה שלח: 2\n"
    "יש לך קוד הטבה? שלח: 3"
)

LAST_FREE = "⚠️ זוהי הבדיקה החינמית האחרונה שלך."

SEARCHING = "🔍 מחפש נתונים..."

NOT_FOUND = "❌ לא נמצאו נתונים עבור לוחית {plate}. בדוק את המספר ונסה שוב."

ERROR = "⚠️ שגיאה בשליפת הנתונים. נסה שוב עוד רגע."

INVALID_PLATE = "🔢 שלח מספר רכב תקין (למשל: 1234567)"

CANCEL = "בסדר, בוטל. לתפריט הראשי שלח: תפריט"


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
        return "🔒 אין בדיקות זמינות. שלח 2 לרכישה."
    emoji = "🟢" if left > 5 else ("🟡" if left > 1 else "🔴")
    return f"{emoji} נותרו לך {left} בדיקות."


def format_result(record: dict, left: int, expires: str | None = None) -> str:
    """Plain-text version of the vehicle summary (strips Markdown escaping)."""
    raw = _tg_summary(record)
    # Strip MarkdownV2 escapes: \X → X  (keep actual newlines)
    import re
    plain = re.sub(r"\\([_\*\[\]()~`>#+=|{}.!\-])", r"\1", raw)
    # Strip bold/italic markers
    plain = re.sub(r"[*_`]", "", plain)
    status = format_status(left, expires)
    return f"{plain}\n\n{status}"
