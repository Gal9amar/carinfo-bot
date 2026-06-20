# מעבר מ-Render ל-Oracle Cloud — מסקנות וצעדים עתידיים

## מה עשינו

- יצרנו VM על Oracle Cloud Free Tier (Ubuntu 22.04, ARM, IP: `82.70.210.54`)
- הגדרנו SSH access דרך `~/.ssh/car-info-bot/ssh-key-2026-06-20.key`
- SSH config alias: `carinfo-oracle` → `ubuntu@82.70.210.54`
- התקנו Docker על השרת (oracle-setup.sh רץ בהצלחה)
- העברנו את קבצי הפרויקט ל-`/opt/carinfo-bot/`
- נתקענו ב-build של Docker

---

## הבעיה שנתקלנו בה

`libsql-experimental` (ו-`libsql`) לא נבנות על ARM64 כי הן דורשות קומפילציית Rust של `libsql-ffi`.
השגיאה: `failed to run custom build command for libsql-ffi v0.9.10`

הוספת Rust ל-Dockerfile לא פתרה כי `maturin` עצמו נכשל על ARM.

---

## הפתרון — מה צריך לעשות בפעם הבאה

### אפשרות א׳ — מעבר ל-Turso HTTP API (מומלץ)

במקום `libsql_experimental` שמשתמשת ב-native driver, לעבור לקריאות HTTP ישירות ל-Turso.

Turso חושפת REST API על:
```
https://<db-name>.turso.io/v2/pipeline
Authorization: Bearer <TURSO_AUTH_TOKEN>
```

**שינויים נדרשים:**
1. `requirements.txt` — להסיר `libsql-experimental`, להוסיף `httpx` (כבר קיים)
2. `src/db.py` — לשכתב את `_get_conn` / `execute` / `batch` להשתמש ב-`httpx` במקום `libsql`

הממשק של `execute` ו-`batch` נשאר זהה — רק הslayer הפנימי משתנה. שאר הקוד לא נוגעים בו.

### אפשרות ב׳ — x86_64 Docker image

להוסיף ל-`docker-compose.yml`:
```yaml
platform: linux/amd64
```
יריץ emulation — עובד אבל איטי יותר בבניה.

---

## בעיית HTTPS

Telegram Mini App חייב HTTPS. ה-VM עולה עם IP בלבד, אין domain.

**פתרון: Cloudflare Tunnel**
- חינמי, ללא domain
- נותן URL מסוג `https://xxx.trycloudflare.com`
- מגדירים `cloudflared` כ-container נוסף ב-docker-compose

```yaml
  cloudflared:
    image: cloudflare/cloudflared:latest
    restart: always
    command: tunnel --no-autoupdate run --token <TUNNEL_TOKEN>
```

ה-`WEBAPP_URL` ב-.env יהיה ה-URL שמקבלים מ-Cloudflare.

---

## מצב השרת כרגע

- VM פעיל ב-`82.70.210.54`
- Docker מותקן
- קבצי הפרויקט ב-`/opt/carinfo-bot/` (כולל `.env` עם כל הסודות)
- **לא רץ כלום** — הפרויקט עדיין על Render

## צעדים לפעם הבאה

1. לשכתב `src/db.py` להשתמש ב-Turso HTTP API
2. לעדכן `requirements.txt` (הסרת `libsql-experimental`)
3. לאפס את הקבצים בשרת (`scp` מחדש)
4. להגדיר Cloudflare Tunnel
5. להריץ `docker compose up -d`
6. להתקין systemd service
7. לעדכן `WEBAPP_URL` בשרת ל-Cloudflare URL
8. לבדוק `/health` ושה-bot עונה
9. לכבות את Render
