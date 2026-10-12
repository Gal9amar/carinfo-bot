---
name: release-and-deploy
description: How carinfo-bot is built, deployed (Render, Docker) and force-refreshed on clients, plus the pre-push release checklist and rollback steps. Use when pushing to main, bumping APP_VERSION to bust stale caches, diagnosing "the Mini App doesn't load after deploy", changing Dockerfile/render.yaml/env vars, or reverting a bad commit.
---

# Release & deploy

## Pipeline facts
- **Branching**: per `CLAUDE.md`, push straight to `main` (no PRs) unless the session/user says otherwise. Render auto-deploys `main`.
- **Build** (`Dockerfile`): python:3.12-slim + Node 20; `pip install -r requirements.txt`; `cd webapp && npm ci && npm run build` -> `webapp/dist`. **A webapp build error = deploy fails** (old version keeps serving).
- **Run**: `CMD python bot.py` -> Telegram bot (polling) + uvicorn thread serving API and `webapp/dist` on `$PORT` (8080). Health check `GET /health` (`render.yaml`). `Procfile` is a legacy `worker`.
- **Env** (Render dashboard; `sync:false` ones are secrets): `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `WEBAPP_URL`, `PAYPAL_ME`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`, optional `PAYBOX_URL`, `BOT_USERNAME`, `YAD2_PROXY_URL/SECRET`. `render.yaml`'s `WEBAPP_URL` and the code default differ - confirm which host is live before touching links.
- **Free-tier sleep**: first request after idle can take ~1 min; not a bug.
- **Cache busting**: `GET /api/version` returns `APP_VERSION` (**hardcoded string** in `api.py`, despite the comment that mentions `RENDER_GIT_COMMIT`). `App.jsx` polls it and `window.location.reload()`s when it differs from what the client has. If users are stuck on an old bundle, bump `APP_VERSION` (e.g. to `str(int(time.time()))` literal) in the same commit as the fix. `index.html` is served `no-store`; `/assets/*` are content-hashed.

## Pre-push checklist (run `qa-agent` / skill `qa-verify-change`)
1. `git diff --stat origin/main...HEAD` - nothing emptied/unexpectedly large, no `.env`, tokens, `*.db`, `uploads/` junk, `__pycache__`.
2. `py_compile` + `import api/bot`; `cd webapp && npm run build` green.
3. Local API boot + UI smoke (home -> profile -> admin) PASS.
4. Schema changes idempotent (`db-schema-change`).
5. New env var? add to Render + document in `CLAUDE.md`; code must tolerate it being unset.
6. Commit message says what/why; end with the attribution lines the session requires.
7. `git push origin HEAD:main` (or the designated branch if told). Never force-push `main`.

## After pushing
- Watch Render deploy logs for: Docker build (npm/pip errors), `Turso DB initialized`, `API server starting on port`.
- `curl -s https://<host>/health` -> `{"ok":true}`; `curl -s https://<host>/api/version`.
- Open the Mini App from Telegram (close & reopen to drop WebView cache); check home + admin.

## Rollback
```bash
git revert <bad_sha>            # creates a new commit; safe on shared main
git push origin HEAD:main
```
Restoring a damaged file from a good commit: `git checkout <good_sha> -- path/to/file && git commit`. (Used to fix the emptied `AdminPage.jsx`: good = `a00b52d`, bad = `07ae327`.) DB changes are not rolled back by git - additive columns are harmless; for data repair write an explicit, reviewed SQL and take a `SELECT` backup first.

## Incident triage: "Mini App won't open"
1. `/health` reachable? No -> Render build/boot failure (read logs; usually webapp build, pip, or missing env like `TURSO_DATABASE_URL`).
2. Home blank but API fine -> JS error: reproduce with `qa-verify-change` smoke; check recent diffs of the screen's file (`git log --stat -5 -- <file>`).
3. Works for some users -> stale cache: bump `APP_VERSION`.
4. 401s everywhere -> `TELEGRAM_BOT_TOKEN` env wrong/changed (initData HMAC fails).
