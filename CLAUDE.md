# carinfo-bot — Project Instructions

## Branching

**Push directly to `main`.** Do not create feature branches or PRs.
(If a session explicitly designates a working branch, use that branch instead and say so.)

> Last verified against the code: 2026-10-12. When you change behaviour, update the matching section here. **The code is the source of truth** — grep before trusting any table below.

---

## Architecture Overview

Israeli vehicle lookup service — Telegram Bot + React Mini App (WebApp), monetised by search quotas, subscriptions, alert packs and digital products.

- **Backend**: FastAPI (`api.py`) + Telegram Bot (`bot.py`, python-telegram-bot 22, polling). One process: `python bot.py` starts uvicorn in a daemon thread next to the bot.
- **Database**: Turso (libsql / serverless SQLite) via `src/db.py::execute` (async; runs on a 6-thread pool with one connection per thread, so it never blocks the event loop and `asyncio.gather` overlaps round-trips; positional `?` params, rows are **tuples**, auto-reconnect on 502/hrana). `get_bot_setting` reads a 5 s in-memory snapshot of all of `bot_settings` (invalidated by `set_bot_setting`) — never add per-key SELECTs. Query count is the cost driver: batch with scalar sub-selects / `gather`.
- **Frontend**: React 18 + Vite (JS, no TypeScript, no router, no tests), built to `webapp/dist` and served by FastAPI at `/`.
- **Deployment**: Render.com, Docker (Python 3.12 + Node 20; `npm ci && npm run build` inside the image), port 8080, health check `/health`.
- **Data sources**: data.gov.il (vehicle registry, many resources), Yad2 (market price + new-listing alerts, geo-blocked outside Israel → proxy), car images (`image_api`).
- **No automated tests / CI.** Verification is manual — see `.claude/skills/qa-verify-change`.

---

## Directory Structure

```
carinfo-bot/
├── api.py                  # FastAPI app: REST API + SPA serving (~2.5k lines)
├── bot.py                  # Telegram bot handlers + scheduled jobs (~2.75k lines)
├── requirements.txt  Dockerfile  Procfile(legacy)  render.yaml
├── cloudflare-worker.js    # Yad2 proxy worker (alt. to /yad2 endpoint)
├── data/users.json         # legacy user backup
├── uploads/                # admin-uploaded images, served at /uploads
├── .claude/                # project agents + skills (see "AI Team")
├── src/
│   ├── db.py               # connection, init_db(), core tables, bot_settings get/set
│   ├── users.py            # quota, subscribers/VIP groups, codes, referrals, admin_grant, stats, expiry
│   ├── packages.py         # packages CRUD + default seed
│   ├── products.py         # digital/physical products + stock units + delivery
│   ├── banners.py          # home/page banners
│   ├── payment_methods.py  # configurable payment methods (logo, url)
│   ├── admin_grants.py     # admin "benefit" presets (label + searches)
│   ├── garage.py           # owned vehicles, expenses, sale
│   ├── yad2.py             # Yad2 URL building + market price (cached) 
│   ├── yad2_models.json   # manufacturer→model→Yad2 ID map
│   ├── yad2_watcher.py     # new-listing alerts ("watches")
│   ├── formatter.py        # vehicle data → Telegram text (HTML)
│   ├── scheduled_broadcast.py  # broadcasts scheduled for a later date/time (table scheduled_broadcasts, atomic claim)
│   ├── reminders.py        # annual-test (טסט) reminders: table test_reminders, daily job logic
│   ├── mirror.py           # activity mirror: exact live copy of every private-chat action + bot reply (HTML, buttons, photos, tables) in one group topic (MirrorBot)
│   ├── rich.py             # sendRichMessage client (tables), gated by bot_settings.rich_messages_enabled
│   ├── messages.py         # ALL user/admin bot copy: HTML builders, personal tone, first-name greeting
│   ├── pdf_report.py       # PDF report (reportlab + python-bidi)
│   ├── tickets.py  activity.py  cache.py(1h TTL)  
│   ├── notifier.py         # callback registry: api.py ↔ bot.py decoupling
│   └── api/{gov_api.py, image_api.py}
└── webapp/
    ├── vite.config.js
    └── src/
        ├── App.jsx  main.jsx  api.js  styles.css  vehicleNames.js
        ├── pages/   HomePage ReportPage PackagesPage PaymentPage ProfilePage OrdersPage
        │            HistoryPage GaragePage GarageHowItWorksPage WatchesPage ReferralPage
        │            TicketPage HowItWorksPage PrivacyPolicyPage AdminPage(~5.3k lines, lazy)
        ├── components/ BackButton BottomNav LicensePlate PageBanners QuotaProgressBar
        │               SkeletonCard VehicleLookupLoader
        └── utils/   marketPrice.js safeHtml.js time.js
```

---

## Database Schema

Created idempotently at startup (`init_db()` in `src/db.py` plus per-module `init_*`); columns are added later with `try: ALTER TABLE … ADD COLUMN`. Rows are read **by tuple index** — only ever append columns. See `.claude/skills/db-schema-change`.

### Users & access
| Table | Key columns | Purpose |
|-------|-------------|---------|
| **users** | user_id PK, username, full_name, searches_done, searches_quota, first_seen, last_seen, last_plate, blocked, quota_expires, channel, referred_by, **member_id**, **watch_quota**, **broadcast_consent** | Accounts + quota. `member_id` = sequential public id used in order refs. `watch_quota` = per-user override of alert limit |
| **user_groups** / **user_group_members** | (group_id,user_id) | Groups: `מנויים`, `מנהלים`, `VIP` (created on demand) |
| **codes** / **user_codes** | code PK | Promo codes (`unlimited` + `searches` = days for monthly) |
| **grants** | user_id, granted_by, searches, note | Audit of admin/payment grants |
| **admin_grants** | label, searches, display_order | Preset "benefits" the admin can grant (not an audit log) |
| **referrals** | referrer_id, referee_id, bonus | Referral records |
| **search_history** | user_id, plate, searched_at | Lookup log |
| **vehicle_notes** | (user_id, plate), note | Private note per plate |

### Commerce
| Table | Key columns | Purpose |
|-------|-------------|---------|
| **packages** | id, label, searches, price, image_url, display_order, duration_months, features(JSON), chips(JSON), **package_type** (`searches`\|`alerts`\|`product`…), is_active | Plans. `searches=-1` → unlimited/monthly; `searches=0` = FREE card |
| **products** | name, description, price, delivery_type (`auto`\|manual), quantity_stock, availability_status (`available`\|`coming_soon`), features, is_active | Digital/other goods |
| **product_stock** | product_id, content, is_used, order_ref | Units for auto-delivery |
| **pending_payments** | ref UNIQUE, phone(=user_id), searches, price, label, duration_months, package_type, product_id, product_quantity | Awaiting admin approval |
| **paypal_transactions** | ref, user_id, amount, currency(ILS), label, searches, **status**, package_type, product_id, delivery_type, delivery_content, product_quantity | Order ledger. Statuses: `intent`→`created`→`completed`/`pending_delivery`/`declined`/`expired`/`user_cancelled` |
| **payment_methods** | name, logo_url, payment_url, active, requires_manual_approval | Shown in payment screen |
| **banners** | title, subtitle, icon, image_url, colors, link_type/value, placements(JSON), is_active | Promo banners per page |

### Features & support
| Table | Purpose |
|-------|---------|
| **owned_vehicles**, **owned_vehicle_expenses** | "Garage": cars the user bought (purchase/sale data, expenses) |
| **yad2_watches** | user_id, make, model, year, seen_ids, active — new-listing alerts |
| **tickets**, **ticket_replies** | Support threads |
| **activity_log** | Audit log (event_type, user, description) |
| **sent_messages**, **broadcast_history** | Outbound DM / broadcast logs |
| **bot_settings** | key/value feature flags + config |

### bot_settings keys (defaults seeded in `init_db`)
| Key | Default | Purpose |
|-----|---------|---------|
| `maintenance` | 0 | Blocks lookups for non-admins when 1 (see Maintenance) |
| `free_searches` | 10 | Welcome quota for new users |
| `referral_bonus` | 10 | Searches awarded per referral |
| `promo_searches` / `promo_duration_days` / `promo_is_subscriber` / `promo_label` / `promo_start` / `promo_end` | 0 / 30 / 0 / "" / "" / "" | Join promo (searches: 0=off, -1=unlimited, >0=count). `promo_is_subscriber=1` also adds new users to "מנויים" |
| `global_unlimited_enabled` / `_start` / `_end` / `_label` | — | Admin's "unlimited for everyone" benefit (see VIP below) |
| `yad2_market_enabled` / `_public` / `_public_start` / `_public_end` / `_public_label` / `_groups` | 0 … [] | Market-price feature gate (see Feature access) |
| `yad2_watch_enabled` / `_public*` / `_groups` / `yad2_watch_max` | 0 … / 2 | New-listing alerts feature + default per-user limit |
| `pdf_report_enabled` / `pdf_report_public*` / `pdf_report_groups` | — | PDF report feature gate |
| `order_sequence` | 0 | Counter for order refs (`{member_id}-{seq:05d}`) |
| `test_reminders_enabled` | 0 | Daily 07:00 UTC job notifies 30/7/1/0 days before the test expires (`src/reminders.py`) for users who pressed the 🔔 button. Re-checks the registry before notifying and never notifies on unverified data; blocked-bot users are deactivated |
| `test_reminders_garage_sync` | 0 | Also auto-enrol every car in users' garages (no explicit consent, so off by default); reminders for sold/deleted cars are deactivated |
| `mirror_enabled` / `mirror_chat_id` / `mirror_thread_id` / `mirror_miniapp` | 0 / — / — / 1 | Activity mirror (`src/mirror.py`). Admin sends `/mirror_here` inside the target group topic → binds chat+topic and enables; `/mirror_off` disables; also a toggle in admin Settings / bot `/admin`. Never mirrors the admin's own chat or group chats; masks typed promo codes and delivered product content (`🔒 תוכן מוסתר`) |
| `rich_messages_enabled` | 0 | Send the lookup result card as a table via `sendRichMessage` (Bot API 10.1+, `src/rich.py`). Toggle: admin panel → Settings, or bot `/admin` → settings. Any API failure falls back to the classic HTML card |

---

## API Endpoints (api.py)

Auth: header `X-Init-Data` = Telegram WebApp initData, HMAC-validated with the bot token (`_get_user`, 401 if invalid). Admin = `user.id == ADMIN_TELEGRAM_ID` (`_require_admin`, 403). Handlers use lazy `from src.x import …`. The SPA catch-all must stay the **last** route; it returns JSON 404 for unknown `/api/*`, serves real files from `webapp/dist`, and an HTML 404 page (`_NOT_FOUND_HTML`) for any other path. In the app an unknown `?page=` shows the `notFound` screen.

### Public
`GET /health` (also HEAD) · `/api/version` (APP_VERSION, no-store) · `/api/packages` · `/api/payment-methods` · `/api/banners?page=` · `/api/products` · `GET /api/payment/cancel/{ref}` · `/yad2?secret=…&manufacturer=&model=&year=` (Yad2 proxy, secret-gated)

### User
| Area | Endpoints |
|------|-----------|
| Profile | `GET /api/user` (quota, flags `show_market_price/show_pdf_report/show_watch`, `is_subscriber`, `global_unlimited_active`, `watch_max`, labels…) · `/api/user/history` · `/api/user/orders` · `/api/user/referral` · `/api/user/referrals` |
| Vehicle | `GET /api/vehicle/{plate}` (consumes quota, 403 `quota_exceeded`, 404 not found) · `/api/vehicle/{plate}/pdf` · `/api/vehicle/{plate}/market-price` · `GET/POST /api/notes/{plate}` |
| Payment | `POST /api/payment/initiate` (`package_id` XOR `product_id`, `quantity`, `intent_only`) · `POST /api/payment/promote` (intent→created + notify admin) |
| Garage | `GET/POST /api/user/garage` · `GET …/check/{plate}` · `PATCH/DELETE …/{id}` · `POST …/{id}/sell` · `POST …/{id}/expenses` · `DELETE …/{id}/expenses/{eid}` |
| Alerts | `GET /api/watches/makes`, `/api/watches/models` · `GET/POST /api/user/watches` · `DELETE …/{id}` · `PATCH …/{id}/toggle` |
| Support | `POST/GET /api/tickets` · `GET /api/tickets/{id}` · `POST …/{id}/reply` |

### Admin (`/api/admin/…`)
stats · users (+`/{id}/grant`, `/block`, `/message`, `/watch-quota`, `/revoke-subscription`, `/broadcast-consent`, `/referrals`, `/history`, `/sent-messages`) · settings (GET/POST) · groups (+members) · packages · products (+stock) · banners · payment-methods · grants (benefit presets) · payments (`/{ref}/approve|decline`) · orders (`/{ref}/approve|cancel|deliver`) · paypal/transactions · codes · broadcast (+history) · gift-all · referrals · activity · tickets (+reply/status) · watches (+makes/models/preview) · market-price · upload-logo. Lists with drag-order have `PUT …/reorder`.

---

## Frontend Navigation (App.jsx)

Screen state machine (`screen` + `screenStack`; `navigate()` / `goBack()`; Telegram BackButton wired to `goBack`). Deep links: `?plate=X` (report) and `?page=privacy|howItWorks|history|ticket|referral|garage|garageHowItWorks|profile…`.

Screens: `loading`, `error`, `home`, `report`, `packages`, `payment`, `success`, `profile`, `orders`, `history`, `garage`, `garageHowItWorks`, `watches`, `referral`, `ticket`, `howItWorks`, `privacy`, `admin` (lazy). Admin panel is reached via **Profile → "פאנל ניהול"** (only if `user.is_admin`). `BottomNav` tabs: בית / חיפושים שלי / רכבים שקניתי / אזור אישי. The client polls `/api/version` and hard-reloads on change.

---

## Key Business Logic

### Quota (`users.searches_quota`)
`> 0` fixed (left = quota − done) · `-1` unlimited · `0` exhausted. `quota_expires` applies only to `-1`; after expiry `is_allowed()` resets quota to 0 and removes from "מנויים"; hourly job `expire_subscriptions()` does the same, daily jobs send expiry reminders (30/7/1/0 days, 06:00 UTC). Blocked → never allowed. **Global unlimited** (`is_global_unlimited_active`, live from settings, date window) → everyone allowed, searches don't consume quota; switching it on from the bot admin menu (`bot.py` adm callback) puts all non-blocked users in the **VIP** group (new users join on creation); switching it off clears VIP.

### Subscriber status (group "מנויים")
`is_subscriber()` = member of "מנויים" **or "VIP"**. Granted by:
- Payment approval (`_grant_payment` → `admin_grant` + `add_to_subscribers`) for `searches`-type packages.
- `admin_grant` with `-2` (permanent unlimited) or `-1` (N-month unlimited) — **these also add to "מנויים"**; a count grant (`>0`) does not; `0` resets to free and removes.
- Join promo with `promo_is_subscriber=1`.
Revoked: quota exhausted (`increment_search`), expiry, `admin_grant(0)`, `POST /api/admin/users/{id}/revoke-subscription`. Promo **codes** and referral bonuses add searches but do not add to "מנויים".

### Payment flow (manual approval — no PayPal API/webhook)
1. `POST /api/payment/initiate` computes price/searches **server-side** from the package/product row → `pending_payments` + `paypal_transactions` (`intent` or `created`), ref = `{member_id}-{seq:05d}`; returns PayPal.me link `PAYPAL_ME/{price}ILS` (also PayBox / configured methods).
2. User pays externally; UI calls `/api/payment/promote` → status `created`, admin notified through `notifier`.
3. Admin approves (`/api/admin/payments/{ref}/approve`) → `_grant_payment` by `package_type`:
   - `searches` → `admin_grant` + subscriber
   - `alerts` → raise `users.watch_quota` (cap 10)
   - `product` → auto: claim stock unit(s) and DM content; manual (or out of stock): status `pending_delivery`, admin delivers via `/orders/{ref}/deliver`
   Then status updated, user notified, activity logged.
4. Decline → status `declined`, user notified. API startup (only) expires `created/intent` rows older than 30 minutes and deletes stale `pending_payments`.
Bot also supports Telegram invoices (`PreCheckoutQueryHandler`, `PAYMENT_PROVIDER_TOKEN`) and `paid|`, `approve|`, `decline|`, `deliver|` callbacks.

### Referral
Link `https://t.me/{BOT_USERNAME}?start=ref_{referrer_id}` → `/start ref_X` → for a **new** user `record_referral(new, referrer, bonus)` logs + adds `referral_bonus` searches to referrer. No subscriber status.

### Feature access (market price / PDF / alerts)
`/api/user` computes `show_*` via `_check_feature(prefix)`: admin ✔ · quota −1 ✔ · subscriber (incl. VIP) ✔ · quota left > 0 ✔ · else if `{prefix}_enabled != 0` and public mode active within its date window ✔. `public_label` fields are shown only while public mode is active.
`GET /api/vehicle/{plate}/market-price` uses its **own** gate: requires `yad2_market_enabled=1` (403 `disabled`), `authorized` = public-mode window **or** membership in `yad2_market_groups`; data is always returned and the UI blurs it when `authorized=false`. (These two gates differ — check both when changing access rules.)

### Alerts ("watches", Yad2)
Users watch make/model/year; `_yad2_watch_job` runs every 30 min and DMs new listings. Limit per user = `users.watch_quota` ▸ `yad2_watch_max` ▸ 5. More alerts are sold as `package_type='alerts'`.

### Vehicle lookup
`GET /api/vehicle/{plate}`: plate normalised (dashes/spaces removed) → `is_allowed` → `cache` (1h) → `gov_api.fetch_vehicle_data` (several data.gov.il resources: main, extended, history, ownership, WLTP, recalls, disability tag, inactive/scrapped, personal import, importer price list…) → `increment_search` + activity log. Quota is consumed only on success. There is currently **no stolen-vehicle lookup** in the code.

### Maintenance
`bot_settings.maintenance=1` (toggled in the bot admin menu / admin UI) blocks lookups for everyone except the admin:
- Bot: `handle_plate` replies "הבוט בתחזוקה".
- API: `_ensure_not_maintenance()` → `503 {"detail":"maintenance"}` on `GET /api/vehicle/{plate}`, `/pdf` and `/market-price` (checked **before** quota/user creation, so nothing is consumed). `/api/user` still works and returns `maintenance: true`.
- Web app: `fetchVehicle` maps 503 → `MAINTENANCE`; `ReportPage` shows "השירות בתחזוקה כרגע" with retry.
- Home screen: orange banner when `user.maintenance`; the search button is disabled for non-admins (admins see a note that search is still open for them).

---

## src/users.py — Key Functions

| Function | Purpose |
|----------|---------|
| `is_allowed(user_id, username, full_name)` | Creates user if new (welcome quota, member_id, promo/VIP), checks blocked/global-unlimited/expiry → `(bool, searches_left)` (`-1` unlimited) |
| `increment_search(user_id, plate)` | Count + history; skips quota while global unlimited; removes subscriber when exhausted |
| `admin_grant(admin_id, target_id, searches, note, duration_months)` | `0` reset · `-2` permanent unlimited · `-1` N×30-day unlimited · `>0` add count |
| `apply_code(user_id, code, username)` | Promo code |
| `add_to_subscribers` / `remove_from_subscribers` / `is_subscriber` | "מנויים" group (+VIP in `is_subscriber`) |
| `add_to_vip` / `add_all_to_vip` / `clear_vip_group` / `is_global_unlimited_active` | Global-unlimited benefit |
| `record_referral`, `get_referrals`, `get_referral_count` | Referrals |
| `expire_subscriptions`, `get_users_expiring_in_days` | Expiry jobs |
| `load_welcome_settings()` / `get_current_welcome_quota()` / `is_promo_active()` | Module-level promo/quota globals loaded from DB |
| `admin_stats()`, `get_all_users()`, block/unblock, broadcast consent, sent-message log | Admin support |

## src/packages.py — Defaults
Seeded when table empty: 🔍 50 חיפושים ₪10 · 🔍 100 חיפושים ₪20 · 🔍 200 חיפושים ₪30 · ♾️ מנוי חודשי ₪25 (`searches=-1`), plus a FREE card (`searches=0`, ₪0) with default feature/chip lists. Admin edits these live in the DB; defaults are not re-applied. Packages page colours cycle by index%3 (Silver `#1e40af→#0ea5e9`, Gold `#92400e→#f59e0b`, Platinum `#4c1d95→#a855f7`).

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | — (required) | Bot token; also the initData HMAC key |
| `ADMIN_TELEGRAM_ID` | 594206475 | Admin user id |
| `ADMIN_USERNAME` | — | Admin handle (contact links) |
| `BOT_USERNAME` | israelcarinfobot | Referral links |
| `WEBAPP_URL` / `RENDER_EXTERNAL_URL` | onrender.com URL | Frontend URL / webhook host (`render.yaml` sets `WEBAPP_URL`) |
| `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` | — | Turso (`file:` URL works locally) |
| `PAYPAL_ME`, `PAYBOX_URL` | paypal.me / PayBox link | Payment links |
| `PAYMENT_PROVIDER_TOKEN` | — | Telegram invoices |
| `YAD2_PROXY_URL`, `YAD2_PROXY_SECRET`, `YAD2_CF_WORKER_URL` | — | Israeli-IP proxy for Yad2 (secrets: set via env, don't commit) |
| `PORT` | 8080 | Server port |
| `LOGO_PATH`, `COVER_PATH` | — | PDF assets |

`APP_VERSION` in `api.py` is a **hardcoded string** (comment about `RENDER_GIT_COMMIT` is outdated): bump it to force all clients to reload.

---

## Telegram Bot (bot.py)

Commands: `/start [ref_UID]`, `/help`, `/status`, `/code` (conversation), `/admin`, `/buy`, `/compare A B`, `/mirror_here` (admin, in the topic), `/mirror_set <t.me/c/… topic link>` (admin, anywhere; sends a test message first), `/mirror_off`, `/myid`, `/optout`, `/optin`. Result card buttons: full report, `rem|add|PLATE` (test reminder), `cmp|start|PLATE` (compare), garage/alerts deep links, share.
Callbacks: `new_search`, `show_packages`, `pkg|`, `buy|`, `paid|`, `approve|`, `decline|`, `deliver|`, `history`/`hist_plate|`, `pdf_report`, `share_report`, `how_it_works`, `back_to_start`, `adm|`, `admpkg|`, `usr|`/`ugrant|`/`utoggle|`, `broadcast_optout|optin`, `chat_admin`, `admin_panel`. Telegram invoice payments handled via pre-checkout + successful-payment handlers. Any text → plate lookup (`handle_plate`).
Jobs (JobQueue): daily expiry reminders (06:00 UTC), hourly `expire_subscriptions`, every 30 min Yad2 watch alerts, daily 07:00 UTC test reminders, every 3 s `mirror_flush` (sends ONE queued mirror op per tick to respect Telegram's ~20 msgs/min group limit).
The bot is built with `mirror.MirrorBot` (an `ExtBot` subclass): every `send_message` / `edit_message_text` / `send_photo` / `send_document` (and `delete_message`) is reported to the mirror, which re-sends the same HTML/photo/file/table to the group as a reply to the user's action header; buttons in the copy are inert (`mirror|noop`), URL buttons stay links; a blocking `TypeHandler` in group -1 records incoming updates first so the feed is in order. Mini App actions are mirrored as one 📱 header line each (no copy of the screen): a pure-ASGI middleware in `api.py` (`_MiniAppMirrorMiddleware`) reports authenticated, non-admin `/api/` calls after the response; `mirror.describe_api_call` maps them (lookups, PDF, market price, payment start/promote, garage, watches, tickets, notes, app open throttled to 1/30 min); page views are not shown. Sub-toggle `mirror_miniapp` (default 1, web admin only).
Scheduled broadcasts: admin panel → שידור → "תזמן לשעה מאוחרת" (`POST /api/admin/broadcast` with `send_at`; `GET/DELETE /api/admin/broadcast/scheduled[/id]`). Job `scheduled_broadcast` (every 30 s) sweeps (`missed` if >3 h late, `interrupted` if stuck sending >30 min — never auto-resent), claims due rows atomically (token UPDATE, no double sends) and sends via `_do_broadcast[_photo]`; the admin gets a DM report. Times stored UTC; the web UI sends ISO-UTC from the device's `datetime-local`. Bot-menu broadcast stays immediate-only.
Test reminders: `test_reminders` table (unique user+plate); stop with `rem|stop|ID`. `_lookup_flow` in `bot.py` is the shared lookup path (typed plates).
**Message style:** every bot message is sent with `ParseMode.HTML` (never Markdown/MarkdownV2). Copy lives in `src/messages.py`; builders take the user's first name (`M.first_name(...)`; `_first_name(tg_user)` / `await _name_of(user_id)` in `bot.py`) and escape every dynamic value with `M.esc`. Sent-message log stores `M.strip_html(text)`. Admin notifications keep an `ID: <code>…</code>` token — `handle_admin_message` parses it to route replies.
`src/notifier.py` lets `api.py` trigger bot messages (payments, tickets, grants, broadcasts, orders, product delivery) without importing `bot.py`; callbacks are registered in `bot.py`.

## Startup Sequence

1. `bot.main()` starts uvicorn thread (`api.api`) + cache cleanup thread.
2. Bot `_post_init`: `init_db()` (tables, settings seed, groups) → `load_welcome_settings()`.
3. API `_startup()`: `load_welcome_settings()`, expire stale payment rows (>30 min), notify admin of expired orders.
4. Per-module `init_*` (packages, products, banners, …) create/migrate their tables.
5. Bot polling + JobQueue jobs start.

---

## AI Team (agents & skills) — `.claude/`

Specialised subagents (`.claude/agents/`) — delegate by area, and **always finish with `qa-agent`**:

| Agent | Owns |
|-------|------|
| `design-agent` | `webapp/` UI/UX, RTL/Hebrew, styles, screens, admin panel UI |
| `api-agent` | `api.py` routes/auth/contracts + `webapp/src/api.js` |
| `backend-agent` | `src/*`, `bot.py`: quota, payments, DB/schema, integrations, notifier |
| `sql-agent` | `src/db.py` + query code: query count, caching, indexes, migrations |
| `integration-agent` | gov.il / Yad2 / images / Telegram API specifics, mirror, rich, notifier, cache |
| `manager-agent` | Splits cross-cutting work by ownership, reviews every diff, gates to qa-agent |
| `qa-agent` | Quality gate for every change; PASS/FAIL verdict with evidence |

Skills (`.claude/skills/`): `qa-verify-change` (scripts: `local_api.py`, `sign_init_data.py`, `smoke_ui.mjs`), `add-api-endpoint`, `db-schema-change`, `add-webapp-screen`, `design-system-rtl`, `release-and-deploy`.

### Lessons / guardrails
- Never commit an emptied or truncated file: check `git diff --stat` before every push (`AdminPage.jsx` was once pushed empty → white admin screen).
- A `lazy()` page must `export default`.
