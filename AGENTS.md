# CarInfo — זיכרון פרויקט (AGENTS.md)

עדכון אחרון: 2026-05-22

## מה הפרויקט

בוטים לבדיקת רכב ישראלי לפי מספר רישוי: **טלגרם** (`bot.py`) ו-**וואטסאפ** (`whatsapp_bot.py` via Green API).  
מקורות: data.gov.il (פרטי רכב, טסט), מאגר גנבה, קישור **Yad2** למחירי שוק, דוח **PDF**.

Repo ראשי: `Gal9amar/carinfo-bot` (GitHub `origin`). פריסה: **Render** (`render.yaml`), גם **JustRunMy** (`justrunmy/deploy`).

---

## מבנה קבצים

```
carinfo/
├── bot.py                 # בוט טלגרם — נקודת כניסה ראשית (Render startCommand)
├── whatsapp_bot.py        # webhook Green API, פורט ברירת מחדל 8081
├── requirements.txt
├── Dockerfile, Procfile, render.yaml
├── data/users.json        # גיבוי/סנכרון משתמשים (GitHub path ב-Render env)
└── src/
    ├── api/
    │   ├── gov_api.py     # data.gov.il
    │   ├── stolen_api.py  # גנבה
    │   └── image_api.py
    ├── yad2.py            # בניית URL ל-Yad2
    ├── yad2_models.json   # מיפוי יצרן→דגמים→ID (~8.4K שורות)
    ├── formatter.py       # הודעות טלגרם/וואטסאפ
    ├── pdf_report.py      # דוח PDF (reportlab + python-bidi)
    ├── cache.py           # TTL cache בזיכרון
    ├── db.py              # Turso (libsql-experimental)
    ├── users.py           # מכסות, קודים, חסימות, אדמין
    └── wa_menu.py         # תפריט וואטסאפ
```

---

## זרימת נתונים

1. משתמש שולח מספר רכב (7–8 ספרות).
2. `gov_api.fetch_vehicle_data` — שדות עברית: `tozeret_nm`, `kinuy_mishari` / `degem_nm`, `shnat_yitzur`, וכו'.
3. `stolen_api` — סטטוס גנבה.
4. `yad2.build_url(record)` — קישור חיפוש ב-Yad2 (תמיד מחזיר URL, לפחות עם שנה).
5. `formatter` / `pdf_report` — פלט למשתמש.

**חשוב — Yad2:** API של Yad2 חסום מחוץ לישראל. אין קריאות live ל-Yad2 מהשרת; רק מיפויים סטטיים ב-`yad2.py` + `yad2_models.json`.

---

## Yad2 — לוגיקה ומלכודות

| רכיב | תפקיד |
|------|--------|
| `_MAKES` / `_ALIASES` | ID יצרן (קיה=48, רנו=51 — יש `assert` sanity) |
| `yad2_models.json` | `{manufacturers: {"48": {models: {...}}}}` |
| `_manufacturer_id` | exact → substring (מיון לפי אורך מפתח) |
| `_model_id` | exact → substring → prefix 5 תווים |
| `build_url` | `manufacturer`, `model`, `year=Y-Y` |

**באג שתוקן (2026-05-21):** בלבול Renault↔Kia ב-substring matching — תוקן בסידור לפי אורך + aliases לרנו (`רנו `, `רנו.`, `ריניה`).

שדות רשומה ל-URL: `tozeret_nm`, `kinuy_mishari` / `_wltp`, `shnat_yitzur`.

---

## משתני סביבה

| משתנה | שימוש |
|--------|--------|
| `TELEGRAM_BOT_TOKEN` | חובה לטלגרם |
| `ADMIN_TELEGRAM_ID` | אדמין (ברירת מחדל בקוד: 594206475) |
| `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` | DB משתמשים/קודים |
| `PAYMENT_PROVIDER_TOKEN`, `PAYPAL_ME` | תשלומים |
| `GREEN_API_*` | וואטסאפ בלבד |
| `TELEGRAM_ADMIN_ID` | התראות רכישה מ-WA |
| `PORT` | 8080 (טלגרם), 8081 (WA) |
| `RENDER_EXTERNAL_URL` | webhook / health |
| `LOGO_PATH`, `COVER_PATH` | PDF |
| `GITHUB_PAT`, `GITHUB_REPO`, `GITHUB_DATA_PATH` | סנכרון `data/users.json` (Render) |

`.env.example` מינימלי — רוב ה-vars רק בפריסה.

---

## מסד נתונים (Turso)

`init_db()` ב-`db.py`: טבלאות `users`, `codes`, ועוד (ראה קובץ).  
`users.py` — מכסת חיפושים, קודי הפעלה, חסימה, היסטוריה, קישור TG↔WA.

---

## Git ופריסה

- **ענף פעיל:** `main` (מסונכרן עם `origin/main` נכון ל-2026-05-22).
- **ענף מקומי:** `agents/project-status-update` (worktree — לא production).
- **קומיט אחרון:** תיקון `_manufacturer_id` / Yad2 (Renault→Kia).
- **Render:** `python bot.py`, health `/`.
- **אל תכלול בקומיטים:** `.env`, סיסמאות, tokens ב-remotes.

---

## קונבנציות פיתוח

- Python 3.11+ (union types `int | None`).
- עברית RTL בהודעות; נרמול שמות: `_normalize` / `_norm_model` (רווחים, גרש, מקף).
- לוגים: `logging` ב-`yad2.py` ברמת debug/info לדיבוג התאמות יצרן.
- שינוי מיפוי Yad2: עדכן `_MAKES`/`_ALIASES` ב-`yad2.py` ו/או `yad2_models.json` — בדוק קיה=48, רנו=51 אחרי שינוי.
- README בעברית — עדכן רק אם המשתמש מבקש.

---

## מה לא לשבור

- כפתור Yad2 לא אמור להיעלם — `build_url` תמיד מחזיר URL.
- התאמת שמות ממשל (עברית/רווחים) לשמות Yad2 דורשת aliases.
- שני תהליכים נפרדים: `bot.py` ו-`whatsapp_bot.py` (לא לאחד בלי תכנון).

---

## סטטוס / המשך אפשרי

- [ ] בדיקות ידניות ליצרנים בעייתיים (רנו, מזדה/מאזדה, מרצדס).
- [ ] עדכון `yad2_models.json` כשמוסיפים דגמים חדשים ב-Yad2.
- [ ] סנכרון README עם מבנה WA + Turso (README מיושן חלקית).

---

## קישורים

- GitHub: `https://github.com/Gal9amar/carinfo-bot`
- Yad2 base: `https://www.yad2.co.il/vehicles/cars`
