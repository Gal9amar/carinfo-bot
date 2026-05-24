"""
Turso (libsql) database layer.
All tables are created on first run via init_db().
Uses libsql-experimental (libsql package).
"""

import os
import asyncio
import libsql_experimental as libsql

_URL   = os.environ.get("TURSO_DATABASE_URL", "")
_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        _conn = libsql.connect(database=_URL, auth_token=_TOKEN)
    return _conn


def _reset_conn():
    global _conn
    _conn = None


class _Result:
    """Wraps libsql cursor to match the interface used in users.py."""
    def __init__(self, rows, columns):
        self.rows    = rows
        self.columns = [type("Col", (), {"name": c})() for c in columns]


async def init_db() -> None:
    conn = _get_conn()
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id        INTEGER PRIMARY KEY,
            username       TEXT DEFAULT '',
            full_name      TEXT DEFAULT '',
            searches_done  INTEGER DEFAULT 0,
            searches_quota INTEGER DEFAULT 20,
            first_seen     TEXT DEFAULT (datetime('now')),
            last_seen      TEXT DEFAULT (datetime('now')),
            last_plate     TEXT DEFAULT '',
            blocked        INTEGER DEFAULT 0,
            quota_expires  TEXT DEFAULT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS codes (
            code        TEXT PRIMARY KEY,
            searches    INTEGER DEFAULT 0,
            unlimited   INTEGER DEFAULT 0,
            single_use  INTEGER DEFAULT 1,
            expires     TEXT,
            used_by     INTEGER,
            used_at     TEXT,
            created     TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS grants (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            granted_by  INTEGER NOT NULL,
            searches    INTEGER NOT NULL,
            note        TEXT DEFAULT '',
            granted_at  TEXT DEFAULT (datetime('now'))
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_codes (
            user_id INTEGER NOT NULL,
            code    TEXT NOT NULL,
            PRIMARY KEY (user_id, code)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS search_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            plate       TEXT NOT NULL,
            searched_at TEXT DEFAULT (datetime('now'))
        )
        """,
    ]
    migrations = [
        "ALTER TABLE users ADD COLUMN quota_expires TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN channel TEXT DEFAULT 'telegram'",
        """CREATE TABLE IF NOT EXISTS pending_payments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ref         TEXT NOT NULL UNIQUE,
            phone       TEXT NOT NULL,
            searches    INTEGER NOT NULL,
            price       INTEGER NOT NULL,
            label       TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )""",
        "ALTER TABLE packages ADD COLUMN image_url TEXT DEFAULT ''",
        "ALTER TABLE packages ADD COLUMN display_order INTEGER DEFAULT 0",
        """CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    username    TEXT    DEFAULT '',
    full_name   TEXT    DEFAULT '',
    subject     TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    status      TEXT    DEFAULT 'open',
    created_at  TEXT    DEFAULT (datetime('now')),
    updated_at  TEXT    DEFAULT (datetime('now'))
)""",
        """CREATE TABLE IF NOT EXISTS ticket_replies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL,
    sender_id   INTEGER NOT NULL,
    sender_name TEXT    DEFAULT '',
    is_admin    INTEGER DEFAULT 0,
    message     TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now'))
)""",
        """CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT    NOT NULL,
    user_id     INTEGER DEFAULT 0,
    username    TEXT    DEFAULT '',
    description TEXT    NOT NULL,
    created_at  TEXT    DEFAULT (datetime('now'))
)""",
        "ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT NULL",
        """CREATE TABLE IF NOT EXISTS referrals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referee_id  INTEGER NOT NULL,
    bonus       INTEGER NOT NULL DEFAULT 10,
    joined_at   TEXT    DEFAULT (datetime('now'))
)""",
        """CREATE TABLE IF NOT EXISTS user_groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
)""",
        """CREATE TABLE IF NOT EXISTS user_group_members (
    group_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    PRIMARY KEY (group_id, user_id)
)""",
        """CREATE TABLE IF NOT EXISTS broadcast_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    message   TEXT    NOT NULL,
    has_image INTEGER DEFAULT 0,
    sent      INTEGER DEFAULT 0,
    failed    INTEGER DEFAULT 0,
    sent_at   TEXT    DEFAULT (datetime('now'))
)""",
    ]
    for sql in statements:
        conn.execute(sql)
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_ugm_user   ON user_group_members(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ugm_group  ON user_group_members(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_sh_user    ON search_history(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_exp  ON users(quota_expires) WHERE quota_expires IS NOT NULL",
    ]
    for sql in indexes:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute(
        "INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('maintenance', '0')"
    )
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('referral_bonus', '10')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('free_searches', '10')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_searches', '0')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_duration_days', '30')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_is_subscriber', '0')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_label', '')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_start', '')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('promo_end', '')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_enabled', '0')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_groups', '[]')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_public', '0')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_public_start', '')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_public_end', '')")
    conn.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('yad2_market_public_label', '')")
    conn.commit()

    # Seed the "מנהלים" group and add admin as member
    admin_id = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))
    if admin_id:
        conn.execute("INSERT OR IGNORE INTO user_groups (name) VALUES ('מנהלים')")
        r = conn.execute("SELECT id FROM user_groups WHERE name='מנהלים'").fetchone()
        if r:
            conn.execute("INSERT OR IGNORE INTO user_group_members (group_id, user_id) VALUES (?, ?)", (r[0], admin_id))
    # Seed the "מנויים" group (members managed automatically)
    conn.execute("INSERT OR IGNORE INTO user_groups (name) VALUES ('מנויים')")
    conn.commit()

    from src.packages import init_packages
    await init_packages()
    from src.admin_grants import init_admin_grants
    await init_admin_grants()


async def get_bot_setting(key: str) -> str:
    r = await execute("SELECT value FROM bot_settings WHERE key=?", [key])
    return r.rows[0][0] if r.rows else ""


async def set_bot_setting(key: str, value: str) -> None:
    await execute(
        "INSERT INTO bot_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        [key, value],
    )


async def execute(sql: str, args: list | None = None) -> _Result:
    """Execute with automatic reconnect on 502/connection errors."""
    for attempt in range(3):
        try:
            conn = _get_conn()
            cur  = conn.execute(sql, tuple(args) if args else ())
            conn.commit()
            rows    = cur.fetchall()
            columns = [desc[0] for desc in (cur.description or [])]
            return _Result(rows, columns)
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ("502", "bad gateway", "hrana", "connection", "timeout")):
                _reset_conn()
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
            raise
    raise RuntimeError("DB execute failed after 3 attempts")


async def batch(statements: list) -> None:
    """Batch execute with automatic reconnect."""
    for attempt in range(3):
        try:
            conn = _get_conn()
            for stmt in statements:
                if isinstance(stmt, tuple):
                    conn.execute(stmt[0], stmt[1])
                else:
                    conn.execute(stmt)
            conn.commit()
            return
        except Exception as e:
            err = str(e).lower()
            if any(x in err for x in ("502", "bad gateway", "hrana", "connection", "timeout")):
                _reset_conn()
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
            raise
