# Mini App — תכנית עבודה

## סטטוס נוכחי ✅
- [x] FastAPI backend (`api.py`) — REST API + HMAC validation
- [x] React app (`webapp/`) — packages, payment, admin dashboard  
- [x] `bot.py` — כפתור web_app, uvicorn thread, `_notify_admin_payment`
- [x] `Dockerfile` — Node 20 build step
- [x] `render.yaml` — runtime: docker

---

## ארכיטקטורה

```
Telegram user
  → לוחץ "🛒 רכישת חבילה"
  → Mini App נפתח (https://carinfo-bot.onrender.com)
  → React app
  → FastAPI /api/*
  → Turso DB (משותף עם bot.py)
```

**תהליך תשלום:**
1. משתמש בוחר חבילה → `POST /api/payment/initiate`
2. מקבל PayPal URL → לוחץ ומשלם
3. לוחץ "שילמתי" → `POST /api/payment/confirm`
4. `_notify_admin_payment()` שולח הודעה לאדמין בטלגרם עם כפתורי אישור/דחייה
5. אדמין לוחץ אשר → המשתמש מקבל את החיפושים

---

## בדיקות — Mini App

| בדיקה | תוצאה |
|-------|--------|
| שינויים ב-DB schema (`bot_settings`) — backwards compatible | ✅ `INSERT OR IGNORE` |
| `get_packages(force_reload=True)` — לא שובר | ✅ כבר קיים |
| `_notify_admin_payment` — נקרא רק מ-api.py | ✅ |

**אימות ידני מומלץ לאחר deploy:**
- [ ] פתח Mini App בטלגרם → נטען
- [ ] בחר חבילה → מגיע ל-PayPal
- [ ] לחץ "שילמתי" → אדמין מקבל הודעה בטלגרם
- [ ] אדמין לוחץ "⚙️ הגדרות בוט" → רואה כפתור תחזוקה
- [ ] Admin Mini App → 4 טאבים עובדים

---

## משתני סביבה נדרשים ב-Render

| משתנה | ערך |
|-------|-----|
| `TELEGRAM_BOT_TOKEN` | הטוקן מ-BotFather |
| `ADMIN_TELEGRAM_ID` | 594206475 |
| `WEBAPP_URL` | https://carinfo-bot.onrender.com |
| `PAYPAL_ME` | https://www.paypal.me/G9ST |
| `TURSO_DATABASE_URL` | מ-Turso console |
| `TURSO_AUTH_TOKEN` | מ-Turso console |
| `PORT` | 8080 (ברירת מחדל) |

---

## שלבים עתידיים (Phase 2)

- [ ] היסטוריית חיפושים במסך Admin
- [ ] דוח רכב גרפי ב-Mini App (לאחר חיפוש)
- [ ] ניהול קודי הנחה
- [ ] push notifications דרך Telegram
