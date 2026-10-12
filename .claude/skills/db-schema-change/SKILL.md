---
name: db-schema-change
description: Safe way to add or change Turso/libsql tables, columns, indexes and bot_settings keys in carinfo-bot (no migration framework - idempotent CREATE/ALTER in init functions). Use for any new table, new column, new setting, data backfill, or when a query reads rows by tuple index.
---

# Schema & data changes

Turso is serverless SQLite. There is **no migration tool**: schema is created/evolved by idempotent statements that run at every startup (`init_db()` in `src/db.py`, plus per-module `init_*` such as `packages.py`, `products.py`, `banners.py`). Prod data already exists - a bad change breaks live users.

## Rules
1. **New table**: `CREATE TABLE IF NOT EXISTS ...` in the owning module's init (or `init_db`). Include `created_at TEXT DEFAULT (datetime('now'))`.
2. **New column** on an existing table: `ALTER TABLE t ADD COLUMN c TYPE DEFAULT x` inside `try/except: pass` (SQLite can't `IF NOT EXISTS` columns). **Always give a DEFAULT**; no `NOT NULL` without default; SQLite can't drop/reorder columns cheaply - don't plan on it.
3. **Never reorder or insert columns mid-table in `SELECT *`-by-index code.** Rows are tuples read by position (`p[6] if len(p) > 6`). Select explicit column lists for new code; append new columns at the end and extend the reader helper (`_pkg_json`, `_product_json`...) with a length guard.
4. **Idempotent**: running startup twice on the same DB must be a no-op. Test it (below).
5. **Seeding** (default packages, groups "מנויים"/"מנהלים", settings): insert only when missing (`INSERT OR IGNORE` / count check) - never overwrite admin-edited values.
6. **Settings** live in `bot_settings(key,value)` as strings; add the key's default where the others are seeded and read it via the existing getter. If a module caches it (`load_welcome_settings`), refresh after write.
7. **Backfills** run once, are guarded (`WHERE col IS NULL`), and batched; don't lock the event loop with huge loops.
8. **Always parametrise**: `await execute("... WHERE user_id=?", [uid])`. `execute` is async, auto-retries connection errors, and returns `.rows` (tuples). Never f-string user input into SQL.
9. **Destructive ops** (DROP/DELETE without WHERE/UPDATE all): not in startup code; require explicit user approval and a backup plan (`SELECT` export first).
10. Money tables (`paypal_transactions`, `pending_payments`, `grants`, `codes`) are audit data - prefer status changes over deletes.

## Test it (throwaway DB)
```bash
export TURSO_DATABASE_URL=file:/tmp/schema.db TURSO_AUTH_TOKEN=x TELEGRAM_BOT_TOKEN=1:x
rm -f /tmp/schema.db
/tmp/venv/bin/python -c "import asyncio; from src.db import init_db; asyncio.run(init_db()); asyncio.run(init_db()); print('init x2 OK')"
/tmp/venv/bin/python -c "
import asyncio; from src.db import execute
r = asyncio.run(execute('PRAGMA table_info(<table>)')); print([row[1] for row in r.rows])"
```
Also test against a DB created by the PREVIOUS commit (`git stash`/checkout old code, init, then new code, init) to prove the ALTER path works on existing data.
Then update the Database Schema section of `CLAUDE.md`.
