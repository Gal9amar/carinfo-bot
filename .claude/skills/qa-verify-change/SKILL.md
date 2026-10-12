---
name: qa-verify-change
description: How to verify ANY change to carinfo-bot before it is pushed - static gates, boot the real API against a throwaway local DB, call endpoints with signed Telegram initData, and run a real-browser smoke test of the Mini App at phone width. Use before every push to main, after every feature/fix, or whenever asked "does it work?". Includes ready-made scripts (local_api.py, sign_init_data.py, smoke_ui.mjs).
---

# Verify a change (the project has no unit tests and no CI - this is the gate)

All commands run from the repo root. Never point tests at the production Turso DB.

## 0. Setup (once per session)
```bash
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -q -r requirements.txt
cd webapp && npm ci && npm i --no-save playwright-core && cd ..     # playwright-core only drives the preinstalled Chromium
```
Chromium lives at `/opt/pw-browsers/chromium` (override with `CHROMIUM=...`). Do **not** run `playwright install`.

## 1. Look at the diff first
```bash
git status --short && git diff --stat origin/main...HEAD
```
RED FLAGS = automatic FAIL: a file whose line count collapses or becomes empty (that is exactly how AdminPage.jsx got emptied: 5,270 lines deleted), a `lazy()`-imported page without `export default`, unrelated files changed, secrets/`.env`/`*.db` staged.

## 2. Static gates
```bash
/tmp/venv/bin/python -m py_compile api.py bot.py src/*.py src/api/*.py && echo PY_OK
(cd webapp && npm run build)        # must end with "built in ..." and no errors
```

## 3. Boot gate (Python changes)
```bash
export TELEGRAM_BOT_TOKEN=123456:TESTTOKEN ADMIN_TELEGRAM_ID=1 TURSO_DATABASE_URL=file:/tmp/imp.db TURSO_AUTH_TOKEN=x
/tmp/venv/bin/python -c "import api; print('api OK')"
/tmp/venv/bin/python -c "import bot; print('bot OK')"
```

## 4. Run the real app locally + call it as user / admin / anonymous
```bash
/tmp/venv/bin/python .claude/skills/qa-verify-change/local_api.py 8099 &     # temp libsql file DB, fake token, admin id = 1; serves webapp/dist at /
sleep 6; curl -s localhost:8099/health
H1="X-Init-Data: $(python3 .claude/skills/qa-verify-change/sign_init_data.py 1)"   # admin
H2="X-Init-Data: $(python3 .claude/skills/qa-verify-change/sign_init_data.py 2)"   # regular user
curl -s -H "$H2" localhost:8099/api/user
curl -s -o /dev/null -w "%{http_code}\n" -H "$H2" localhost:8099/api/admin/stats   # expect 403
curl -s -o /dev/null -w "%{http_code}\n" -H "$H1" localhost:8099/api/admin/stats   # expect 200
curl -s -o /dev/null -w "%{http_code}\n" localhost:8099/api/user                   # expect 401
```
For the endpoint under test always check: anon -> 401, non-admin on admin route -> 403, bad body -> 400/422, unknown id -> 404, **user 2 cannot read/modify user 1's resource**, happy path JSON shape, and the DB side effect (query via a one-off python snippet using `src.db.execute` with the same `TURSO_DATABASE_URL`). Gov.il / Yad2 / Telegram are unreachable in the sandbox: external calls will fail or time out - test that the app degrades gracefully, don't treat that as a regression.

## 5. UI smoke test (webapp changes, and always for the baseline path)
```bash
cd webapp && npm run build && cd ..
node .claude/skills/qa-verify-change/smoke_ui.mjs --shot /tmp/ui.png "אזור אישי" "פאנל ניהול"      # admin user
node .claude/skills/qa-verify-change/smoke_ui.mjs --user 2 "אזור אישי"                              # regular user
```
Each quoted arg is a visible text clicked in order. Use `--path "/?plate=1234567"` to open the report screen directly and `--allow 503` when a 5xx is the expected result (e.g. maintenance). Exit code 1 + `FAIL` lines on page error, console error, HTTP 5xx, text not found, or blank screen. Verified to catch the empty-AdminPage bug (React error #306 + blank screen). Open the PNG (Read tool) and inspect RTL, overflow, clipped text, bottom-nav overlap. Add the click path of your new screen as extra args. Kill the server after: `kill %1` / `pkill -f local_api.py`.

## 6. Regression checklist (tick what the diff could touch)
- [ ] home loads; profile -> every tile opens (orders, history, garage, watches, referral, packages, ticket, admin)
- [ ] admin panel opens and each tab renders (lazy chunk loads)
- [ ] quota rules (`>0` / `-1` / `0`), subscriber only via payment approval
- [ ] payment initiate -> confirm -> approve/decline idempotent, no double grant
- [ ] DB migrations idempotent: start the app twice on the same `file:` DB
- [ ] new API field is additive; `api.js` and the screens read the same names
- [ ] Hebrew RTL, numbers/plates LTR-isolated, 390px width, no horizontal scroll
- [ ] `index.html` still `no-store`; `/api/version` works

## 7. Report
Use the verdict block from `qa-agent` (VERDICT, Ran, Findings with owner, Not verified). "Not verified" must list anything needing real Telegram, real Turso, or live Render.
