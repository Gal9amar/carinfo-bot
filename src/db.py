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
        "ALTER TABLE users ADD COLUMN whatsapp_phone TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN channel TEXT DEFAULT 'telegram'",
        "ALTER TABLE users ADD COLUMN wa_state TEXT DEFAULT NULL",
    ]
    for sql in statements:
        conn.execute(sql)
    for sql in migrations:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()


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
