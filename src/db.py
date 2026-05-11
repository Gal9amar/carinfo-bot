"""
Turso (libsql) database layer.
All tables are created on first run via init_db().
"""

import os
import asyncio
import libsql_client

_URL   = os.environ.get("TURSO_DATABASE_URL", "")
_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

_client: libsql_client.Client | None = None


def get_client() -> libsql_client.Client:
    global _client
    if _client is None:
        _client = libsql_client.create_client(url=_URL, auth_token=_TOKEN)
    return _client


async def init_db() -> None:
    c = get_client()
    await c.batch([
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id        INTEGER PRIMARY KEY,
            username       TEXT DEFAULT '',
            full_name      TEXT DEFAULT '',
            searches_done  INTEGER DEFAULT 0,
            searches_quota INTEGER DEFAULT 5,
            first_seen     TEXT DEFAULT (datetime('now')),
            last_seen      TEXT DEFAULT (datetime('now')),
            last_plate     TEXT DEFAULT ''
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
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            plate      TEXT NOT NULL,
            searched_at TEXT DEFAULT (datetime('now'))
        )
        """,
    ])


async def execute(sql: str, args: list | None = None) -> libsql_client.ResultSet:
    c = get_client()
    return await c.execute(libsql_client.Statement(sql, args or []))


async def batch(statements: list) -> None:
    c = get_client()
    await c.batch(statements)
