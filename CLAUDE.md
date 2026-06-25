# carinfo-bot — Project Instructions

## Branching

**Push directly to `main`.** Do not create feature branches or PRs.

---

## Architecture Overview

Israeli vehicle lookup service — Telegram Bot + React Mini App (WebApp).

- **Backend**: FastAPI (Python) + Telegram Bot (`python-telegram-bot`)
- **Database**: Turso (libsql / serverless SQLite)
- **Frontend**: React 18 + Vite, served statically by FastAPI at `/`
- **Deployment**: Render.com (single service, port 8080)

---

## Directory Structure

```
carinfo-bot/
├── api.py              # FastAPI REST API (986 lines)
├── bot.py              # Telegram bot handlers (2246 lines)
├── requirements.txt
├── Dockerfile
├── Procfile
├── render.yaml
├── cloudflare-worker.js
├── src/
│   ├── db.py           # DB layer (Turso/libsql)
│   ├── users.py        # User quota, referrals, subscriber management
│   ├── packages.py     # Package pricing CRUD
│   ├── formatter.py    # Vehicle data formatting
│   ├── pdf_report.py   # PDF generation (reportlab)
│   ├── yad2.py         # Yad2 market price integration
│   ├── tickets.py      # Support ticket system
│   ├── activity.py     # Activity/audit logging
│   ├── cache.py        # In-memory TTL cache (1h)
│   ├── notifier.py     # Callback registry (api.py ↔ bot.py decoupling)
│   └── api/
│       ├── gov_api.py  # data.gov.il vehicle registry
│       ├── image_api.py
│       └── stolen_api.py
└── webapp/
    ├── vite.config.js
    └── src/
        ├── App.jsx     # Screen router
        ├── api.js      # All frontend API calls
        ├── main.jsx
        ├── styles.css
        ├── pages/
        │   ├── HomePage.jsx
        │   ├── ReportPage.jsx
        │   ├── PackagesPage.jsx
        │   ├── PaymentPage.jsx
        │   ├── AdminPage.jsx
        │   ├── HistoryPage.jsx
        │   ├── TicketPage.jsx
        │   ├── ReferralPage.jsx
        │   ├── HowItWorksPage.jsx
        │   └── PrivacyPolicyPage.jsx
        └── components/
            ├── BottomNav.jsx
            ├── BackButton.jsx
            ├── LicensePlate.jsx
            └── SkeletonCard.jsx
```

---

## Database Schema (src/db.py)

### Core

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| **users** | user_id PK, username, full_name, searches_done, searches_quota, first_seen, last_seen, last_plate, blocked, quota_expires, referred_by, channel | User accounts + quota tracking |
| **codes** | code PK, searches, unlimited, single_use, expires, used_by, used_at, created | Promo codes |
| **user_codes** | (user_id, code) PK | Codes applied per user |
| **grants** | id, user_id, granted_by, searches, note, granted_at | Admin grant log |
| **search_history** | id, user_id, plate, searched_at | Per-user lookup log |
| **packages** | id PK, label, searches, price, image_url | Purchase packages |
| **bot_settings** | key PK, value | Feature flags + config |

### Payments & Tickets

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| **pending_payments** | id, ref UNIQUE, phone, searches, price, label, created_at | Awaiting admin approval |
| **tickets** | id, user_id, username, full_name, subject, message, status, created_at, updated_at | Support tickets |
| **ticket_replies** | id, ticket_id, sender_id, sender_name, is_admin, message, created_at | Ticket thread |

### Groups & Social

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| **referrals** | id, referrer_id, referee_id, bonus, joined_at | Referral records |
| **user_groups** | id PK, name UNIQUE, created_at | Groups: "מנויים", "מנהלים" |
| **user_group_members** | (group_id, user_id) PK | Group membership |
| **activity_log** | id, event_type, user_id, username, description, created_at | Audit log |

### bot_settings Keys

| Key | Default | Purpose |
|-----|---------|---------|
| `maintenance` | 0 | Disable service when 1 |
| `free_searches` | 10 | Welcome quota for new users |
| `referral_bonus` | 10 | Searches awarded per referral |
| `promo_searches` | 0 | Promo quota (0=off, -1=unlimited, >0=count) |
| `promo_start` | "" | Promo start date (YYYY-MM-DD) |
| `promo_end` | "" | Promo end date (YYYY-MM-DD) |
| `yad2_market_enabled` | 0 | Enable market price feature |
| `yad2_market_public` | 0 | Public access mode (all users) |
| `yad2_market_public_start` | "" | Public mode start date |
| `yad2_market_public_end` | "" | Public mode end date |
| `yad2_market_public_label` | "" | Label shown in public mode (empty = hidden) |
| `yad2_market_groups` | [] | JSON list of group IDs with market price access |

---

## API Endpoints (api.py)

### Public
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/packages` | List packages (no auth) |

### User (Telegram WebApp auth)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/user` | User info, quotas, is_subscriber, is_admin |
| GET | `/api/user/history` | Last 20 unique plates |
| GET | `/api/user/referral` | Referral link + stats |
| GET | `/api/user/referrals` | List of referred users |
| GET | `/api/vehicle/{plate}` | Lookup vehicle (decrements quota) |
| GET | `/api/vehicle/{plate}/market-price` | Yad2 market price (authorized flag) |
| POST | `/api/payment/initiate` | Create pending payment |
| POST | `/api/payment/confirm` | "I paid" — notify admin |
| POST | `/api/tickets` | Create support ticket |
| GET | `/api/tickets` | List user's tickets |
| GET | `/api/tickets/{id}` | Ticket + replies |
| POST | `/api/tickets/{id}/reply` | User reply |

### Admin (ADMIN_TELEGRAM_ID only)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/stats` | Aggregate stats |
| GET/POST | `/api/admin/settings` | Read/update bot_settings |
| GET | `/api/admin/users` | All users |
| POST | `/api/admin/users/{id}/grant` | Grant searches |
| POST | `/api/admin/users/{id}/block` | Toggle block |
| POST | `/api/admin/users/{id}/message` | Send DM |
| GET | `/api/admin/users/{id}/referrals` | User's referrals |
| GET | `/api/admin/users/{id}/history` | User's search history |
| GET/POST | `/api/admin/packages` | List/add packages |
| PUT/DELETE | `/api/admin/packages/{id}` | Update/delete package |
| GET | `/api/admin/payments` | Pending payments |
| POST | `/api/admin/payments/{ref}/approve` | Approve + add to "מנויים" |
| POST | `/api/admin/payments/{ref}/decline` | Decline + notify user |
| GET/POST | `/api/admin/codes` | List/create promo codes |
| DELETE | `/api/admin/codes/{code}` | Delete code |
| POST | `/api/admin/broadcast` | Message all users |
| POST | `/api/admin/gift-all` | Gift searches + optional broadcast photo |
| GET | `/api/admin/activity` | Activity log |
| GET/POST | `/api/admin/groups` | List/create groups |
| DELETE | `/api/admin/groups/{id}` | Delete group |
| POST | `/api/admin/groups/{id}/members` | Add member |
| DELETE | `/api/admin/groups/{id}/members/{uid}` | Remove member |
| GET/POST/PATCH | `/api/admin/tickets[/{id}[/reply|/status]]` | Ticket management |
| GET | `/api/admin/market-price?plate=X` | Admin market price view |

### Yad2 Proxy
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/yad2?secret=X&manufacturer=X&model=X&year=X` | Bypass geo-block for Yad2 API |

---

## Frontend Navigation (App.jsx)

Screen state machine (URL params: `?plate=X`, `?page=privacy|ticket|history|howItWorks|referral`):

```
loading → error
       → home ⇄ packages → payment → success
              ⇄ report
              ⇄ admin
              ⇄ ticket
              ⇄ history
              ⇄ referral
              ⇄ howItWorks
              ⇄ privacy
```

`<BottomNav>` visible on: home, packages, history, ticket, referral.

---

## Key Business Logic

### Subscriber Management

**Group**: "מנויים" in `user_groups` — membership via `user_group_members`.

`is_subscriber` in `/api/user` = membership in "מנויים" group.

**Grant subscriber status** — ONLY via:
- Payment approval: `POST /api/admin/payments/{ref}/approve` → calls `add_to_subscribers(user_id)`

**Revoke subscriber status** — automatically:
- Quota exhausted: `increment_search()` detects `searches_done >= searches_quota` → `remove_from_subscribers()`
- Monthly subscription expired: `is_allowed()` detects `quota_expires < now` → `remove_from_subscribers()`

**Does NOT grant subscriber status**: admin grants, promo codes, referral bonuses, welcome quota.

### Payment Flow

1. User picks package → `POST /api/payment/initiate` → `pending_payments` row (unique ref)
2. Returns PayPal.me URL
3. User pays externally, clicks "שילמתי" → `POST /api/payment/confirm` → admin notified via bot
4. Admin approves → searches granted + user added to "מנויים" + pending row deleted + user notified
5. Admin declines → pending row deleted + user notified

### Referral Flow

1. Referral link: `https://t.me/{BOT_USERNAME}?start=ref_{referrer_id}`
2. New user opens link → `/start ref_X` handler
3. If user is new: `record_referral(new_id, referrer_id, bonus)` → log in `referrals`, set `referred_by`, add `referral_bonus` searches to referrer
4. Referrals do NOT grant subscriber status

### Market Price Access (Yad2)

Feature gate: `yad2_market_enabled=1` required.

**Public mode**: `yad2_market_public=1` + optional date window → all users authorized.

**Group mode**: `yad2_market_groups=[group_id, ...]` → only group members authorized.

Response always returned (no 403). `authorized` flag controls frontend display:
- `authorized=true` → full data + Yad2 link
- `authorized=false` → data present but values blurred in UI, Yad2 button disabled

`public_label` in response: shown only when public mode is active and label is set.

### Quota Types

| searches_quota | Meaning |
|----------------|---------|
| `> 0` | Fixed count; searches_left = quota - done |
| `-1` | Unlimited (monthly sub or permanent grant) |
| `0` | Exhausted |

`quota_expires` (ISO datetime): only applies when `searches_quota = -1`. After expiry, quota reset to 0 and subscriber removed.

---

## src/users.py — Key Functions

| Function | Purpose |
|----------|---------|
| `is_allowed(user_id, username, full_name)` | Check quota + blocked + expiry. Returns (bool, searches_left) |
| `increment_search(user_id, plate)` | Increment done, log history, remove subscriber if exhausted |
| `apply_code(user_id, code, username)` | Apply promo code (no subscriber grant) |
| `admin_grant(admin_id, target_id, searches, note)` | Grant searches (-2=unlimited, -1=30-day, >0=count). No subscriber grant |
| `add_to_subscribers(user_id)` | Add to "מנויים" group |
| `remove_from_subscribers(user_id)` | Remove from "מנויים" group |
| `record_referral(new_user_id, referrer_id, bonus)` | Log referral + award referrer |
| `load_welcome_settings()` | Load FREE_SEARCHES, PROMO_* from DB into module globals |
| `get_current_welcome_quota()` | Calculate new user quota (promo or free) |

---

## src/packages.py — Default Packages

Seeded on `init_packages()`:

| Label | Searches | Price |
|-------|----------|-------|
| 🔍 50 חיפושים | 50 | ₪10 |
| 🔍 100 חיפושים | 100 | ₪20 |
| 🔍 200 חיפושים | 200 | ₪30 |
| ♾️ מנוי חודשי | -1 (unlimited) | ₪25 |

Packages page uses tier colors cycling by index:
- Silver (idx%3=0): `#1e40af→#0ea5e9`, accent `#38bdf8`
- Gold (idx%3=1): `#92400e→#f59e0b`, accent `#fbbf24`
- Platinum (idx%3=2): `#4c1d95→#a855f7`, accent `#c084fc`

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token |
| `ADMIN_TELEGRAM_ID` | 594206475 | Admin user ID |
| `BOT_USERNAME` | israelcarinfobot | For referral links |
| `WEBAPP_URL` | https://carinfo-bot.onrender.com | Frontend URL |
| `TURSO_DATABASE_URL` | — | Turso DB URL |
| `TURSO_AUTH_TOKEN` | — | Turso auth token |
| `PAYPAL_ME` | https://www.paypal.me/G9ST | Payment link |
| `YAD2_PROXY_URL` | http://151.145.86.13:8080/yad2 | Israeli IP proxy |
| `YAD2_PROXY_SECRET` | carinfo2026 | Proxy auth secret |
| `PORT` | 8080 | Server port |
| `RENDER_EXTERNAL_URL` | — | Webhook URL on Render |
| `LOGO_PATH` / `COVER_PATH` | — | PDF assets |

---

## Telegram Bot Commands (bot.py)

| Command / Callback | Purpose |
|--------------------|---------|
| `/start [ref_UID]` | Welcome + referral tracking |
| `/help` | Help message |
| `/status` | User quota info |
| `/code` | Apply promo code (conversation) |
| `/admin` | Admin menu (admin only) |
| `/buy` | Package shortcut |
| `/myid` | Echo user ID |
| `new_search` | Prompt for plate |
| `show_packages` | Package list |
| `pkg\|{id}` | Package details |
| `paid\|{searches}\|{price}` | "I paid" → admin notify |
| `approve\|{ref}` | Admin approves payment |
| `decline\|{ref}` | Admin declines payment |
| `history` / `hist_plate\|{plate}` | View recent plates |
| `pdf_report` | Generate PDF |
| Vehicle plate text | Lookup + display report |

---

## Startup Sequence

1. `init_db()` — create all tables, seed bot_settings, seed "מנויים"/"מנהלים" groups
2. `init_packages()` — create packages table, seed defaults
3. `load_welcome_settings()` — populate module-level quota globals
4. FastAPI `_startup()` event — register notifier callbacks
5. Bot polling starts alongside uvicorn server
