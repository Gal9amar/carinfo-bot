# 🚗 CarInfo Bot – בוט טלגרם לבדיקת רכב ישראלי

בוט טלגרם שמקבל מספר רכב ומחזיר את כל המידע הזמין ממאגרי ממשלת ישראל.

## מה הבוט בודק

| מקור | נתונים |
|------|---------|
| data.gov.il | יצרן, דגם, שנה, צבע, דלק, מנוע, כוח סוס, מושבים, דלתות, משקל, זיהום, שלדה, צמיגים, תאריכי רישום |
| data.gov.il | תוקף טסט + האם פג תוקף (ירוק/צהוב/אדום) |
| מאגר משטרה | האם הרכב מדווח כגנוב |

## מבנה הפרויקט

```
carinfo/
├── bot.py                  ← נקודת כניסה ראשית
├── requirements.txt
├── Dockerfile
├── .env.example
└── src/
    ├── api/
    │   ├── gov_api.py      ← data.gov.il client
    │   └── stolen_api.py   ← בדיקת גנבה
    ├── cache.py            ← TTL cache בזיכרון
    └── formatter.py        ← עיצוב הודעת טלגרם
```

## התקנה והרצה מקומית

### 1. צור Bot Token

1. פתח טלגרם → חפש `@BotFather`
2. שלח `/newbot` → עקוב אחר ההוראות
3. שמור את ה-Token שקיבלת

### 2. הגדר env

```bash
cp .env.example .env
# ערוך את .env והכנס את ה-Token
```

### 3. התקן תלויות והרץ

```bash
pip install -r requirements.txt
python bot.py
```

## פריסה ל-JustRunMy.App

### שיטה 1: ZIP Upload (הכי פשוט)

1. צור ZIP של כל הפרויקט (ללא תיקיית `.git`)
2. כנס ל-[JustRunMy.App](https://justrunmy.app)
3. צור שירות חדש → בחר **Zip Upload**
4. העלה את ה-ZIP
5. הוסף Environment Variable: `TELEGRAM_BOT_TOKEN=your_token`
6. לחץ Deploy

### שיטה 2: Docker

1. בנה image:
   ```bash
   docker build -t carinfo-bot .
   ```
2. ב-JustRunMy.App בחר **Docker Image**
3. הגדר את ה-env variable ופרוס

## Environment Variables

| שם | חובה | תיאור |
|----|------|-------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token מ-BotFather |

## שימוש בבוט

- `/start` – הודעת פתיחה
- `/help` – עזרה
- כל מספר רכב (עם מקפים או בלי) → מידע מלא
