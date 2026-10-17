"""
All user-facing bot copy lives here.

Every builder returns Telegram **HTML** (ParseMode.HTML) and addresses the user
by first name in a friendly, conversational tone. Dynamic values are always
passed through ``esc()`` so user-controlled text can never break the markup.

Supported tags: <b> <i> <u> <code> <pre> <a href> <blockquote>.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Optional

DEFAULT_NAME = "חבר"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def esc(value) -> str:
    """HTML-escape any value for safe use inside a Telegram HTML message."""
    return html.escape(str(value if value is not None else ""), quote=False)


def attr(value) -> str:
    """Escape a value for use inside an HTML attribute (e.g. href)."""
    return html.escape(str(value or ""), quote=True)


def b(value) -> str:
    return f"<b>{esc(value)}</b>"


def i(value) -> str:
    return f"<i>{esc(value)}</i>"


def code(value) -> str:
    return f"<code>{esc(value)}</code>"


def link(text: str, url: str) -> str:
    return f'<a href="{attr(url)}">{esc(text)}</a>'


def quote(inner_html: str) -> str:
    """Wrap already-escaped HTML in a blockquote."""
    return f"<blockquote>{inner_html}</blockquote>"


def first_name(full_name: str = "", username: str = "") -> str:
    """First name for greetings. Never raises; falls back to a neutral word."""
    for candidate in (full_name or "").split():
        token = candidate.strip()
        if any(ch.isalpha() for ch in token):
            return token[:20]
    return DEFAULT_NAME


def strip_html(text: str) -> str:
    """Plain-text version of a message, used for the sent-messages log."""
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _n(name: str) -> str:
    """Bold, escaped first name."""
    return b(name or DEFAULT_NAME)


def _count(n: int, one: str, many: str) -> str:
    return one if n == 1 else f"{n} {many}"


def fmt_date(raw: str) -> str:
    try:
        return datetime.fromisoformat(str(raw)[:10]).strftime("%d/%m/%Y")
    except Exception:
        return str(raw)[:10]


# ─────────────────────────────────────────────
# Account status
# ─────────────────────────────────────────────

def quota_line(left: int, expires: Optional[str] = None) -> str:
    """One-line account status. left: -1 unlimited, >0 remaining, 0 = full access."""
    if left == -1:
        if expires:
            return f"♾️ המנוי החודשי שלך פעיל עד {b(fmt_date(expires))}"
        return "♾️ יש לך גישה בלתי מוגבלת"
    if left > 0:
        return f"🆓 נותרו לך {b(_count(left, 'בדיקה אחת', 'בדיקות'))}"
    return "✅ הגישה שלך פעילה"


def welcome(name: str, status_html: str, is_new: bool = False) -> str:
    opener = (
        f"👋 היי {_n(name)}, שמח שהצטרפת ל-{b('CarInfo')}!"
        if is_new else
        f"👋 היי {_n(name)}, טוב לראות אותך שוב ב-{b('CarInfo')}!"
    )
    return (
        f"{opener}\n"
        f"{i('הבוט החכם לבדיקת רכבים בישראל 🇮🇱')}\n\n"
        "שלח לי מספר לוחית רישוי ותוך שניות תקבל:\n\n"
        "📋 פרטי הרכב המלאים\n"
        "👥 היסטוריית בעלויות\n"
        "⚙️ מפרט טכני מלא\n"
        "🛡️ בטיחות ו-ADAS\n"
        "🔔 ריקולים פתוחים\n"
        "💰 הערכת מחיר שוק\n\n"
        + quote(f"🔍 {b('איך מתחילים?')}\nפשוט שולחים מספר רכב, למשל: {code('1234567')}")
        + f"\n\n{status_html}"
    )


def status(name: str, left: int, expires: Optional[str] = None) -> str:
    if left == 0:
        return (
            f"🔒 {_n(name)}, הבדיקות החינמיות שלך נוצלו.\n\n"
            f"רוצה להמשיך? שלח {code('/buy')} ונפתח לך חבילה 🛒"
        )
    return f"📊 {_n(name)}, הנה מצב החשבון שלך:\n\n{quota_line(left, expires)}"


def help_text(name: str) -> str:
    return (
        f"📖 {_n(name)}, הנה מדריך קצר:\n\n"
        "שלח לי מספר רכב ← תקבל סיכום מהיר ותפריט לדוח המלא.\n\n"
        f"{b('מה יש בדוח?')}\n"
        "📋 פרטים כלליים · ⚙️ מפרט טכני\n"
        "🔧 גלגלים · 🛋️ ציוד\n"
        "🛡️ בטיחות · 🤖 ADAS\n"
        "📅 היסטוריה · 👥 בעלויות · 🔔 ריקולים\n\n"
        f"{b('פקודות שימושיות:')}\n"
        f"{code('/status')} — מצב החשבון שלך\n"
        f"{code('/buy')} — רכישת חבילות\n"
        f"{code('/compare 1234567 7654321')} — השוואה בין שני רכבים (שתי בדיקות)\n"
        f"{code('/code XXXXXXXX')} — הפעלת קוד הטבה\n\n"
        + quote("צריך עזרה? אני כאן 🙂 אפשר לפתוח פנייה לתמיכה מתוך התפריט.")
    )


def how_it_works(name: str, free: int, packages_html: str) -> str:
    return (
        f"ℹ️ {_n(name)}, ככה זה עובד:\n"
        f"{i('הבוט החכם לבדיקת רכבים בישראל')}\n\n"
        f"⚡ {b('שולחים לוחית רישוי — מקבלים דוח מלא תוך שניות')}\n\n"
        f"📋 {b('מה מוצג על כל רכב:')}\n"
        "🚗 פרטים כלליים – יצרן, דגם, שנה, צבע\n"
        "⚙️ מפרט טכני – מנוע, הנעה, דלק, כוח סוס\n"
        "🛞 גלגלים וצמיגים\n"
        "🪑 ציוד ונוחות – מיזוג, הגה כוח, חלונות\n"
        "🛡️ בטיחות – ABS, ESP, כריות אוויר, CO2\n"
        "🤖 מערכות ADAS – בלימה אוטומטית, שמירת נתיב\n"
        "📅 היסטוריה – רישום, טסט, ק\"מ, שינויי מבנה\n"
        "👥 בעלויות – כמה בעלים, פרטי/סוחר\n"
        "💰 הערכת מחיר שוק – על בסיס Yad2\n"
        "⚠️ ריקולים – תקלות ידועות של הדגם\n\n"
        f"🆓 {b('חינם:')} כל משתמש חדש מקבל {b(f'{free} חיפושים')} לניסיון\n\n"
        f"🎁 {b('רוצה חיפושים במתנה?')}\n"
        "הפנה חברים לבוט וקבל חיפושים על כל הצטרפות\n\n"
        f"📦 {b('חבילות חיפוש:')}\n{packages_html}\n\n"
        + quote(
            f"🔑 יש קוד גישה? שלח {code('/code XXXXXXXX')}\n"
            "🎫 צריך תמיכה? לחץ על כפתור התמיכה בתפריט"
        )
    )


# ─────────────────────────────────────────────
# Access: payment wall, block, promo codes
# ─────────────────────────────────────────────

def payment_required(name: str, custom_text: Optional[str] = None) -> str:
    if custom_text:
        # Admin-authored plain text: escaped, with a personal opener.
        return f"🔒 {_n(name)}\n\n{esc(custom_text)}"
    return (
        f"🔒 {b(f'{name or DEFAULT_NAME}, הבדיקות החינמיות שלך נגמרו')}\n\n"
        "כדי להמשיך לחפש רכבים אפשר לרכוש חבילת בדיקות בלחיצה על הכפתור למטה 👇\n\n"
        + quote("יש לך קוד הטבה? אפשר להפעיל אותו גם מכאן 🎟️")
    )


def blocked(name: str) -> str:
    return (
        f"🚫 {_n(name)}, הגישה שלך לבוט חסומה כרגע.\n\n"
        "לפרטים או לערעור אפשר לפנות למנהל דרך הכפתור למטה."
    )


def unblocked(name: str) -> str:
    return (
        f"✅ חדשות טובות, {_n(name)}!\n"
        "החסימה שלך הוסרה ואפשר להמשיך להשתמש בבוט 🚗"
    )


def enter_code_prompt(name: str) -> str:
    return (
        f"🎟️ {_n(name)}, שלח לי את קוד ההטבה שקיבלת\n"
        f"{i('(לא משנה אם באותיות קטנות או גדולות)')}"
    )


def code_usage() -> str:
    return f"🎟️ כדי להפעיל קוד שלח: {code('/code XXXXXXXX')}"


def code_applied(name: str, result: str) -> str:
    return (
        f"🎉 {_n(name)}, הקוד הופעל!\n\n"
        f"✅ {b(result)}\n\n"
        "אפשר להתחיל לחפש רכבים עכשיו 🚗"
    )


def code_rejected(name: str, reason: str) -> str:
    return (
        f"😕 {_n(name)}, הקוד לא עבד\n\n"
        f"{esc(reason)}\n\n"
        "אפשר לנסות שוב, או לעבור לתפריט החבילות."
    )


def search_cancelled() -> str:
    return "בסדר, ביטלתי את החיפוש 👌"


# ─────────────────────────────────────────────
# Lookup flow
# ─────────────────────────────────────────────

def search_steps(name: str) -> list[str]:
    return [
        f"🔗 {esc(name)}, מתחבר למאגר משרד התחבורה...",
        "📋 שולף נתוני רישוי ובעלות...",
        "🔧 בודק היסטוריית טסט שנתי...",
        "🔔 בודק ריקולים פתוחים...",
        "📊 מכין את הדוח שלך...",
    ]


def ask_plate(name: str) -> str:
    return f"🔢 {_n(name)}, שלח לי מספר רכב ואני על זה:"


def invalid_plate(name: str) -> str:
    return (
        f"🤔 {_n(name)}, זה לא נראה לי כמו מספר רכב.\n"
        f"שלח מספר בן 5–10 ספרות, למשל: {code('1234567')}"
    )


def maintenance(name: str) -> str:
    return (
        f"🔧 {_n(name)}, הבוט בתחזוקה כרגע\n\n"
        "נחזור לפעולה בקרוב — תודה על הסבלנות 🙏"
    )


def last_free_search(name: str) -> str:
    return (
        f"⚠️ {_n(name)}, זו הבדיקה החינמית האחרונה שלך.\n"
        f"{i('אחרי זה אפשר להמשיך עם חבילה או קוד הטבה.')}"
    )


def not_found(name: str, plate: str) -> str:
    return (
        f"🔎 {_n(name)}, לא מצאתי מידע על מספר הרכב {b(plate)}.\n\n"
        + quote("כדאי לוודא שהמספר נכון (עם או בלי מקפים) ולנסות שוב.")
    )


def lookup_error(name: str) -> str:
    return (
        f"😬 אופס {_n(name)}, משהו השתבש בשליפת הנתונים.\n"
        "נסה שוב בעוד כמה שניות — הבדיקה לא נוכתה."
    )


def result_intro(name: str, plate: str) -> str:
    return f"🔖 {_n(name)}, הנה מה שמצאתי על לוחית {code(plate)}:\n\n"


def result_quota_text(left: int, expires: Optional[str]) -> str:
    """Plain-text quota note under a result card. left = remaining AFTER this search (or -1)."""
    if left == -1:
        if expires:
            return '♾️ מנוי חודשי פעיל — תוקף עד ' + fmt_date(expires)
        return '✅ גישה בלתי מוגבלת'
    emoji = "🟢" if left > 5 else ("🟡" if left > 1 else "🔴")
    return f'{emoji} נותרו לך ' + _count(left, 'בדיקה אחת', 'בדיקות')


def result_quota_footer(left: int, expires: Optional[str]) -> str:
    return f"\n{i(result_quota_text(left, expires))}"


def result_card_rich(name: str, plate: str, summary_html: str, footer_text: str = "") -> str:
    """Result card for sendRichMessage (summary_html is already Rich HTML)."""
    footer = f"<p><i>{esc(footer_text)}</i></p>" if footer_text else ""
    return (
        f"<p>🔖 {b(name)}, הנה מה שמצאתי על לוחית {code(plate)}:</p>"
        f"{summary_html}{footer}"
    )


def _car(label: str, plate: str) -> str:
    return f"{b(label)} ({code(plate)})" if label else f"הרכב {code(plate)}"


def _when_phrase(days_left: int) -> str:
    """'היום' / 'מחר' / 'בעוד N ימים' / 'אתמול' / 'לפני N ימים'."""
    if days_left == 0:
        return "היום"
    if days_left == 1:
        return "מחר"
    if days_left > 1:
        return f"בעוד {days_left} ימים"
    if days_left == -1:
        return "אתמול"
    return f"לפני {abs(days_left)} ימים"


def reminder_set(name: str, plate: str, label: str, tokef: str, days_left: int) -> str:
    when = fmt_date(tokef)
    if days_left < 0:
        timing = f"הטסט פג {b(when)} — כדאי לחדש בהקדם. כשתחדש, אעדכן את התאריך לבד."
    elif days_left <= 1:
        timing = f"הטסט פג {_when_phrase(days_left)} ({b(when)}). כדאי לחדש בהקדם."
    elif days_left <= 7:
        timing = f"הטסט פג ב-{b(when)} ({_when_phrase(days_left)}). אזכיר לך שוב יום לפני."
    elif days_left <= 30:
        timing = f"הטסט פג ב-{b(when)} ({_when_phrase(days_left)}). אזכיר לך שוב שבוע ויום לפני."
    else:
        timing = f"הטסט בתוקף עד {b(when)}. אשלח לך תזכורת חודש, שבוע ויום לפני."
    return f"🔔 {_n(name)}, סגור! הגדרתי תזכורת טסט ל-{_car(label, plate)}\n\n{timing}"


def reminder_no_date(name: str) -> str:
    return f"🤷 {_n(name)}, אין לי תאריך תוקף טסט לרכב הזה, אז אין לי מה להזכיר לך. תוכל לבדוק את התאריך ברישיון הרכב."


def reminders_disabled(name: str) -> str:
    return f"⏸ {_n(name)}, תזכורות הטסט כבויות כרגע. נסה שוב מאוחר יותר."



def test_reminder(name: str, plate: str, label: str, tokef: str, days_left: int) -> str:
    car = _car(label, plate)
    when = b(fmt_date(tokef))
    if days_left > 7:
        head, body = f"📅 {_n(name)}, מתקרב מועד הטסט של {car}", f"תוקף הטסט עד {when} ({_when_phrase(days_left)}). כדאי לקבוע תור מראש."
    elif days_left > 1:
        head, body = f"⚠️ {_n(name)}, נשארו {days_left} ימים לטסט של {car}", f"תוקף הטסט עד {when}."
    elif days_left == 1:
        head, body = f"🔴 {_n(name)}, הטסט של {car} מסתיים מחר!", f"היום האחרון הוא {when}."
    elif days_left == 0:
        head, body = f"⏰ {_n(name)}, היום פג תוקף הטסט של {car}", "כדאי לחדש היום, כדי לא לנסוע בלי טסט בתוקף."
    else:
        head, body = f"🚫 {_n(name)}, הטסט של {car} פג {_when_phrase(days_left)}", f"התוקף הסתיים ב-{when}. כשתחדש את הטסט, אעדכן את התאריך לבד."
    return f"{head}\n\n{body}\n\n" + quote(i("אם כבר חידשת — אין צורך לעשות כלום, אעדכן את התאריך לבד."))


def compare_ask_second(name: str, plate: str) -> str:
    return f"⚖️ {_n(name)}, השוואה: הרכב הראשון הוא {code(plate)}.\nשלח עכשיו את מספר הרכב השני:"


def compare_need_two(name: str) -> str:
    return (
        f"⚖️ {_n(name)}, להשוואה צריך שני מספרי רכב.\n"
        f"שלח: {code('/compare 1234567 7654321')}"
    )


def compare_not_enough(name: str) -> str:
    return f"🔒 {_n(name)}, השוואה בודקת שני רכבים ולכן צורכת שתי בדיקות, ואין לך מספיק כרגע.\nאפשר לרכוש חבילה עם /buy."


def compare_same(name: str) -> str:
    return f"🤔 {_n(name)}, זה אותו מספר רכב. שלח מספר אחר להשוואה."


def compare_failed(name: str, plate: str) -> str:
    return f"🔎 {_n(name)}, לא מצאתי מידע על הרכב {code(plate)}, אז אי אפשר להשוות."


def history_table_intro(name: str) -> str:
    return f"📜 {_n(name)}, אלה החיפושים האחרונים שלך:"


def pdf_preparing(name: str) -> str:
    return f"📄 {esc(name)}, מכין לך את קובץ הדוח... רגע קטן."


def pdf_caption(plate: str) -> str:
    return f"📄 דוח רכב {plate}"


def pdf_failed(name: str) -> str:
    return f"😕 {esc(name)}, לא הצלחתי ליצור את הדוח. נסה שוב בעוד רגע."


def no_report_to_share(name: str) -> str:
    return f"🤷 {esc(name)}, אין דוח לשיתוף כרגע. בצע חיפוש חדש ונסה שוב."


def no_report_for_pdf(name: str) -> str:
    return f"🤷 {esc(name)}, אין רכב להפקת דוח. בצע חיפוש חדש ונסה שוב."


def history_list(name: str) -> str:
    return (
        f"📜 {_n(name)}, אלה החיפושים האחרונים שלך:\n"
        f"{i('לחץ על מספר רכב כדי לצפות שוב — בלי לנכות בדיקה')}"
    )


def history_empty(name: str) -> str:
    return f"📜 {esc(name)}, עדיין אין לך היסטוריית חיפושים. שלח מספר רכב ונתחיל! 🚗"


# ─────────────────────────────────────────────
# Commerce
# ─────────────────────────────────────────────

def packages_intro(name: str) -> str:
    return f"🛒 {_n(name)}, כאן אפשר לבחור חבילת חיפושים.\nפתח את התפריט לרכישה 👇"


def buy_intro(name: str) -> str:
    return f"💳 {_n(name)}, מוכן להמשיך? לחץ על הכפתור כדי לפתוח את חנות החבילות 👇"


def package_details(name: str, label: str, desc: str, price) -> str:
    return (
        f"💳 {_n(name)}, בחרת ב-{b(label)}\n\n"
        f"• {esc(desc)}\n"
        f"• מחיר: {b(f'₪{price}')}\n\n"
        f"{b('איך משלמים?')}\n"
        "1️⃣ לוחצים על כפתור התשלום למטה (PayPal או PayBox)\n"
        "2️⃣ משלימים את התשלום\n"
        "3️⃣ חוזרים לכאן ולוחצים <b>שילמתי</b> לשליחת אישור\n\n"
        + quote("הגישה נפתחת לאחר אישור ידני של המנהל — בדרך כלל תוך מספר דקות ⏱️")
    )


def payment_request_sent(name: str) -> str:
    return (
        f"✅ תודה {_n(name)}, הבקשה שלך נשלחה למנהל!\n\n"
        "ברגע שהתשלום יאומת הגישה תיפתח אצלך, בדרך כלל תוך כמה דקות ⏱️\n"
        f"{i('נעדכן אותך כאן בצ׳אט.')}"
    )


def purchase_request_received(name: str) -> str:
    return (
        f"✅ {_n(name)}, קיבלנו את בקשתך!\n\n"
        "ניצור איתך קשר בהקדם לאחר אישור התשלום.\n\n"
        + quote(f"📝 ציין בהודעה: {b('CarInfo')}")
    )


def payment_approved(name: str, label: str, desc: str) -> str:
    return (
        f"🎉 {_n(name)}, התשלום שלך אושר!\n\n"
        f"📦 {b(label)}\n"
        f"🔍 {esc(desc)} נוספו לחשבונך\n\n"
        "אפשר להתחיל לחפש מיד — שלח מספר רכב 🚗"
    )


def payment_approved_simple(name: str, searches: int) -> str:
    if searches == -1:
        return (
            f"🎉 {_n(name)}, המנוי החודשי שלך פעיל!\n"
            "אפשר לחפש ללא הגבלה למשך 30 יום 🚗"
        )
    return (
        f"🎉 {_n(name)}, התשלום אושר!\n"
        f"נוספו לך {b(_count(searches, 'בדיקה אחת', 'בדיקות רכב'))}. אפשר להתחיל מיד! 🚗"
    )


def payment_declined(name: str, label: str = "") -> str:
    pkg = f"📦 {esc(label)}\n" if label else ""
    return (
        f"😕 {_n(name)}, לא הצלחנו לאמת את התשלום\n"
        f"{pkg}\n"
        + quote("יש שאלה? כתוב לנו דרך צ'אט המנהל ונסדר את זה יחד 💬")
    )


def payment_received(name: str, searches: int, amount_ils) -> str:
    return (
        f"✅ {_n(name)}, התשלום התקבל!\n\n"
        f"נוספו לך {b(_count(searches, 'בדיקה אחת', 'בדיקות רכב'))}\n"
        f"סכום שחויב: {b(f'₪{amount_ils}')}\n\n"
        "תודה על הרכישה! 🙏"
    )


def grant_update(name: str, searches: int, expires: str = "") -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    head = f"🔔 {_n(name)}, המנוי שלך עודכן!\n\n"
    footer = "\n\n" + quote("לפרטים על הפיצ'רים של המנוי שלך — היכנס לתפריט <b>רכישת מנויים</b>.")
    if searches == 0:
        return f"{head}📦 מסוג: {b('מסלול FREE')}\n📅 החל מ: {today}{footer}"
    if searches == -2:
        return (
            f"{head}📦 מסוג: {b('גישה חופשית ♾️')}\n📅 החל מ: {today}\n"
            f"⏰ בתוקף: {b('ללא הגבלת זמן')}{footer}"
        )
    if searches == -1:
        end = f"\n⏰ בתוקף עד: {b(fmt_date(expires))}" if expires else ""
        return f"{head}📦 מסוג: {b('מנוי חודשי')}\n📅 החל מ: {today}{end}{footer}"
    return f"{head}📦 נוספו: {b(_count(searches, 'חיפוש אחד', 'חיפושים'))} 🔍\n📅 החל מ: {today}{footer}"


def grant_cmd(name: str, searches: int, summary: str) -> str:
    """Notification after `/admin grant`."""
    if searches == -2:
        return f"🎖️ {_n(name)}, קיבלת גישה חופשית ללא הגבלת זמן!\nאפשר לחפש רכבים בלי הגבלה 🚗"
    if searches == -1:
        return f"🎉 {_n(name)}, המנוי החודשי שלך אושר!\n\n{esc(summary)}\n\nאפשר לחפש רכבים ללא הגבלה 🚗"
    return f"🎉 {_n(name)}, נוספו לך {b(_count(searches, 'בדיקה אחת', 'בדיקות רכב'))}!\nאפשר להתחיל לחפש מיד 🚗"


def promo_welcome(name: str, label: str, duration_text: str, expires_text: str) -> str:
    return (
        f"🎉 {_n(name)}, ברוך הבא למבצע ההצטרפות!\n\n"
        "בזכות המבצע הפעיל מגיע לך:\n"
        f"✨ {b(label)}\n"
        f"⏱ {esc(duration_text)}{esc(expires_text)}"
    )


def product_delivered(name: str, label: str, ref: str, content: str) -> str:
    one_liner = "\n" not in content and len(content) <= 200 and "http" not in content
    body = code(content) if one_liner else esc(content)
    return (
        f"🎉 {_n(name)}, ההזמנה שלך מוכנה!\n\n"
        f"📦 {b(label)}\n"
        f"🔖 מס' הזמנה: {code(ref)}\n\n"
        f"{body}"
    )


# ─────────────────────────────────────────────
# Social: referrals, support, broadcasts
# ─────────────────────────────────────────────

def referral_bonus(name: str, friend: str, bonus: int) -> str:
    return (
        f"🎉 {_n(name)}, חבר חדש הצטרף דרך הלינק שלך!\n\n"
        f"👤 {esc(friend)} הצטרף לבוט\n"
        f"🎁 קיבלת {b(_count(bonus, 'חיפוש אחד', 'חיפושים'))} בונוס!"
    )


def referral_rejected(name: str, friend: str) -> str:
    return (
        f"ℹ️ {_n(name)}, הפעם לא נוכל לתת בונוס הפניה\n\n"
        f"{esc(friend)} כבר משתמש בבוט.\n"
        + quote("הבונוס ניתן רק על משתמשים חדשים שמצטרפים לראשונה.")
    )


def admin_chat_sent(name: str) -> str:
    return (
        f"💬 {_n(name)}, ההודעה שלך נשלחה למנהל!\n\n"
        "נחזור אליך בהקדם.\n\n"
        + quote("כדי להמשיך את השיחה — השב (Reply) להודעה הזו.")
    )


def admin_chat_relayed(name: str) -> str:
    return f"✅ {esc(name)}, העברתי את ההודעה שלך למנהל."


def open_admin_chat(name: str) -> str:
    return f"💬 {_n(name)}, לחץ על הכפתור כדי לפתוח שיחה עם המנהל:"


def ticket_reply(name: str, subject: str, reply: str) -> str:
    return (
        f"💬 {_n(name)}, יש תגובה חדשה לפנייה שלך\n\n"
        f"📋 {b('נושא:')} {esc(subject)}\n\n"
        + quote(esc(reply[:500]))
    )


def admin_dm(name: str, text: str) -> str:
    """A direct message from the admin to a user."""
    return f"📩 היי {_n(name)}, יש לך הודעה מהמנהל:\n\n{esc(text)}"


def broadcast(name: str, text: str) -> str:
    return f"📢 היי {_n(name)},\n\n{esc(text)}"


def optout(name: str) -> str:
    return (
        f"🔕 {_n(name)}, הסרתי אותך מרשימת השידורים\n\n"
        "לא תקבל יותר הודעות שידור.\n"
        + quote(
            "הודעות מערכת חיוניות (כמו אישורי רכישה) עדיין יישלחו.\n"
            f"לחזרה לרשימה שלח {code('/optin')}"
        )
    )


def optin(name: str) -> str:
    return (
        f"🔔 {_n(name)}, ברוך השב לרשימת השידורים!\n\n"
        "תקבל מאיתנו עדכונים ומבצעים 🎁"
    )


def expiry_reminder(name: str, days: int) -> str:
    if days == 30:
        return (
            f"📅 {_n(name)}, תזכורת קטנה: עוד חודש המנוי שלך מסתיים\n\n"
            "כדי להמשיך ליהנות מחיפושים ללא הגבלה אפשר לחדש מראש."
        )
    if days == 7:
        return (
            f"⚠️ {_n(name)}, עוד שבוע המנוי שלך מסתיים\n\n"
            "אפשר לחדש עכשיו ולהמשיך ליהנות מהשירות בלי הפסקה."
        )
    if days == 1:
        return (
            f"🔴 {_n(name)}, המנוי שלך מסתיים מחר!\n\n"
            "מחר הוא היום האחרון — אפשר לחדש עוד היום ולא לפספס."
        )
    return (
        f"⏰ {_n(name)}, המנוי שלך הסתיים היום\n\n"
        "כדי להמשיך להשתמש בשירות אפשר לרכוש חבילת חיפושים בכל רגע 🛒"
    )


# ─────────────────────────────────────────────
# Yad2 alerts
# ─────────────────────────────────────────────

def watch_started(name: str, label: str, count: int) -> str:
    return (
        f"🔍 {_n(name)}, מעקב יד2 הופעל!\n\n"
        f"🚗 {b(label)}\n"
        f"✅ נמצאו {count} מודעות תואמות קיימות.\n"
        "מעתה תקבל התראה בכל פעם שתתווסף מודעה חדשה.\n\n"
        + quote(
            "שים לב: קבלת ההתראות תלויה בזמינות השירות ועשויה להתעכב. "
            "המידע מסופק כשירות בלבד ואינו מובטח כמלא או מעודכן בזמן אמת."
        )
    )


def watch_alert(
    name: str, label: str, count: int, top_price: str, top_details: str,
    top_link: str, search_url: str,
) -> str:
    count_word = "מודעה חדשה" if count == 1 else "מודעות חדשות"
    if top_link:
        cta = link("🆕 פתח את המודעה החדשה ביותר", top_link)
        more = f"\n{link(f'ראה את כל {count} המודעות ביד2', search_url)}" if count > 1 else ""
    else:
        cta = link("🆕 ראה את המודעות החדשות ביד2", search_url)
        more = ""
    details = f"\n{esc(top_details)}" if top_details else ""
    return (
        f"👋 היי {_n(name)}! מצאתי {b(f'{count} {count_word}')} שמתאימות לחיפוש שלך.\n\n"
        f"🚗 {b(label)}\n"
        f"💰 {esc(top_price)}{details}\n\n"
        f"{cta}{more}"
    )


# ─────────────────────────────────────────────
# Admin-facing (HTML as well, for one parse mode everywhere)
# ─────────────────────────────────────────────

def admin_panel(name: str, stats: dict) -> str:
    return (
        f"🛠 {_n(name)}, זה פאנל הניהול של {b('CarInfo')}\n\n"
        f"👤 משתמשים: {b(stats['total_users'])} | פעילים השבוע: {b(stats['active_week'])}\n"
        f"🔍 בדיקות: {b(stats['total_searches'])}\n"
        f"🔑 קודים: {b(str(stats['used_codes']) + '/' + str(stats['total_codes']))} נוצלו"
    )


def admin_stats_detail(stats: dict) -> str:
    return (
        f"📊 {b('סטטיסטיקות מפורטות')}\n\n"
        f"• סה\"כ משתמשים: {b(stats['total_users'])}\n"
        f"• פעילים השבוע: {b(stats['active_week'])}\n"
        f"• פעילים החודש: {b(stats['active_month'])}\n"
        f"• סה\"כ בדיקות שבוצעו: {b(stats['total_searches'])}\n"
        f"• קודים שנוצרו: {b(stats['total_codes'])}\n"
        f"• קודים שנוצלו: {b(stats['used_codes'])}"
    )


def admin_stats_short(stats: dict) -> str:
    return (
        f"📊 {b('סטטיסטיקות')}\n\n"
        f"• משתמשים: {b(stats['total_users'])} | פעילים השבוע: {b(stats['active_week'])}\n"
        f"• בדיקות שבוצעו: {b(stats['total_searches'])}\n"
        f"• קודים: {b(str(stats['used_codes']) + '/' + str(stats['total_codes']))} נוצלו"
    )


def admin_settings(free: int, maintenance_on: bool, rich_on: bool = False,
                   reminders_on: bool = False, garage_sync_on: bool = False,
                   mirror_on: bool = False, mirror_bound: bool = False) -> str:
    maint = "🔴 פעיל" if maintenance_on else "🟢 כבוי"

    def onoff(v: bool) -> str:
        return "🟢 פעיל" if v else "⚪ כבוי"

    return (
        f"⚙️ {b('הגדרות בוט')}\n\n"
        f"• בדיקות חינמיות למשתמש חדש: {b(free)}\n"
        f"• מצב תחזוקה: {b(maint)}\n"
        f"• תוצאת חיפוש כטבלה: {b(onoff(rich_on))}\n"
        f"• תזכורות טסט: {b(onoff(reminders_on))}\n"
        f"• תזכורת אוטומטית לרכבי המוסך: {b(onoff(garage_sync_on))}\n"
        f"• מראה פעולות לקבוצה: {b(onoff(mirror_on))}"
        + ("" if mirror_bound else "\n  ↳ כדי לקשר: שלח /mirror_set עם קישור לטופיק, או /mirror_here בתוך הטופיק")
    )


ADMIN_BLOCK_LIST = (
    f"🚫 {b('חסימת משתמשים')}\n\n🔴 = חסום כעת\nלחץ על משתמש כדי לחסום / לשחרר:"
)


def admin_new_user(display: str, full_name: str, user_id: int, total: int) -> str:
    return (
        f"👋 {b('משתמש חדש הצטרף!')}\n\n"
        f"👤 {esc(display)}\n"
        f"📛 {esc(full_name)}\n"
        f"🆔 ID: {code(user_id)}\n\n"
        f"👥 סה\"כ משתמשים: {b(total)}"
    )


def admin_chat_request(display: str, full_name: str, user_id: int) -> str:
    return (
        f"💬 {b('פנייה חדשה למנהל!')}\n\n"
        f"👤 משתמש: {esc(display)}\n"
        f"📛 שם: {esc(full_name)}\n"
        f"🆔 ID: {code(user_id)}"
    )


def admin_buy_request(display: str, full_name: str, user_id: int) -> str:
    return (
        f"💰 {b('בקשת רכישה חדשה!')}\n\n"
        f"👤 משתמש: {esc(display)}\n"
        f"📛 שם: {esc(full_name)}\n"
        f"🆔 ID: {code(user_id)}\n\n"
        f"לפתיחת גישה:\n{code(f'/admin grant {display} 50')}"
    )


def admin_payment_request(who: str, user_id: int, label: str, price, ref: str = "") -> str:
    ref_line = f"\n🔑 ref: {code(ref)}" if ref else ""
    src = " (Mini App)" if ref else ""
    return (
        f"💰 {b('בקשת אישור תשלום' + src + '!')}\n\n"
        f"👤 {esc(who)}\n"
        f"🆔 ID: {code(user_id)}\n"
        f"📦 {esc(label)}\n"
        f"💵 ₪{esc(price)}{ref_line}\n\n"
        "לאחר אימות התשלום ב-PayPal לחץ אשר 👇"
    )


def admin_ticket(ticket_id: int, who: str, user_id: int, subject: str, message: str) -> str:
    return (
        f"🎫 {b(f'פנייה חדשה #{ticket_id}')}\n"
        f"👤 {esc(who)} (ID: {code(user_id)})\n"
        f"📋 {b('נושא:')} {esc(subject)}\n\n"
        + quote(esc(message[:500]))
    )


def admin_user_reply(display: str, full_name: str, user_id: int, text: str) -> str:
    return (
        f"↩️ {b('תגובה ממשתמש')}\n\n"
        f"👤 {esc(display)} | 📛 {esc(full_name)} | 🆔 ID: {code(user_id)}\n\n"
        f"{esc(text)}"
    )


def admin_payment_received(who: str, searches: int, amount_ils) -> str:
    return (
        f"💰 {b('תשלום חדש!')}\n\n"
        f"👤 {esc(who)}\n"
        f"🔍 {searches} בדיקות\n"
        f"💵 ₪{esc(amount_ils)}"
    )


def admin_order(status_txt: str, ref: str, user_txt: str, member_id, label: str, amount) -> str:
    return (
        f"{esc(status_txt)}\n"
        f"🔖 הזמנה: {code(ref)}\n"
        f"👤 משתמש: {esc(user_txt)}  #{esc(member_id or '—')}\n"
        f"📦 מוצר: {esc(label)}\n"
        f"💰 סכום: ₪{esc(amount)}"
    )


def admin_delivery_needed(ref: str, user_id: int, label: str) -> str:
    return (
        f"📦 {b('הזמנת מוצר ממתינה למשלוח ידני')}\n"
        f"🔖 הזמנה: {code(ref)}\n"
        f"👤 משתמש: {code(user_id)}\n"
        f"📦 מוצר: {esc(label)}\n\n"
        "לחץ על הכפתור כדי לשלוח את תוכן ההזמנה ללקוח."
    )


def admin_order_delivered(user_txt: str, user_id: int, label: str, price, ref: str, content: str, auto: bool) -> str:
    kind_txt = "אוטומטית" if auto else "ידנית"
    return (
        f"🔒 {b('הודעה למנהל בלבד')}\n\n"
        f"✅ {b(f'הזמנת מוצר הושלמה ({kind_txt})')}\n\n"
        f"👤 {esc(user_txt)} (ID: {code(user_id)})\n"
        f"🛒 מוצר: {esc(label)}\n"
        f"💰 מחיר: ₪{esc(price)}\n"
        f"🆔 הזמנה #{esc(ref)}\n\n"
        f"📦 {b('נשלח:')}\n{esc(content)}"
    )
