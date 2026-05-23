# הגדרת שרת Oracle Cloud — CarInfo Bot

## פרטי השרת
- **OS:** Ubuntu 22.04 (ARM / Ampere)
- **משתמש:** `ubuntu`
- **IP:** להשלים אחרי הקצאה

---

## שלב 1 — התחברות SSH מהמחשב שלך

### Windows (PowerShell):
```powershell
ssh -i C:\path\to\your-key.key ubuntu@YOUR_IP
```

### Mac / Linux:
```bash
chmod 400 ~/Downloads/your-key.key
ssh -i ~/Downloads/your-key.key ubuntu@YOUR_IP
```

---

## שלב 2 — פתיחת פורטים בחומת האש של Oracle

בממשק Oracle Cloud:
1. לך ל **Networking → Virtual Cloud Networks**
2. לחץ על ה-VCN של ה-VM
3. לחץ על **Security Lists → Default Security List**
4. לחץ **Add Ingress Rules** והוסף:

| Source CIDR | Protocol | Port |
|---|---|---|
| 0.0.0.0/0 | TCP | 8000 |
| 0.0.0.0/0 | TCP | 443 |
| 0.0.0.0/0 | TCP | 80 |

---

## שלב 3 — עדכון השרת והתקנת תלויות

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git curl nginx certbot python3-certbot-nginx
```

---

## שלב 4 — פתיחת פורטים בחומת האש של Ubuntu

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw enable
```

---

## שלב 5 — שכפול הפרויקט

```bash
cd /home/ubuntu
git clone https://github.com/Gal9amar/carinfo-bot.git
cd carinfo-bot
```

---

## שלב 6 — סביבה וירטואלית והתקנת חבילות Python

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## שלב 7 — קובץ משתני סביבה

```bash
nano .env
```

הכנס את הפרטים הבאים:
```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_telegram_id
WEBAPP_URL=https://YOUR_DOMAIN_OR_IP
PAYPAL_ME=your_paypal_me
ADMIN_USERNAME=your_telegram_username
```

שמור: `Ctrl+X` → `Y` → `Enter`

---

## שלב 8 — בניית ה-webapp

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
cd webapp
npm install
npm run build
cd ..
```

---

## שלב 9 — הפעלה כ-service (systemd)

```bash
sudo nano /etc/systemd/system/carinfo.service
```

הכנס:
```ini
[Unit]
Description=CarInfo Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/carinfo-bot
EnvironmentFile=/home/ubuntu/carinfo-bot/.env
ExecStart=/home/ubuntu/carinfo-bot/venv/bin/python -m uvicorn api:api --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

שמור ואתחל:
```bash
sudo systemctl daemon-reload
sudo systemctl enable carinfo
sudo systemctl start carinfo
sudo systemctl status carinfo
```

---

## שלב 10 — בדיקה

```bash
curl http://localhost:8000/api/health
```

אם מחזיר תגובה — הבוט עובד ✅

---

## הערות
- לוגים: `sudo journalctl -u carinfo -f`
- הפעלה מחדש: `sudo systemctl restart carinfo`
- עצירה: `sudo systemctl stop carinfo`
