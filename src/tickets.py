from src.db import execute


async def create_ticket(user_id: int, username: str, full_name: str, subject: str, message: str) -> int:
    r = await execute(
        "INSERT INTO tickets (user_id, username, full_name, subject, message) VALUES (?,?,?,?,?)",
        [user_id, username, full_name, subject, message],
    )
    r2 = await execute("SELECT last_insert_rowid()")
    return r2.rows[0][0]


async def get_user_tickets(user_id: int) -> list:
    r = await execute(
        "SELECT id, subject, status, created_at, updated_at FROM tickets WHERE user_id=? ORDER BY updated_at DESC",
        [user_id],
    )
    return [{"id": row[0], "subject": row[1], "status": row[2], "created_at": row[3], "updated_at": row[4]} for row in r.rows]


async def get_ticket(ticket_id: int) -> dict | None:
    r = await execute(
        "SELECT id, user_id, username, full_name, subject, message, status, created_at, updated_at FROM tickets WHERE id=?",
        [ticket_id],
    )
    if not r.rows:
        return None
    row = r.rows[0]
    return {"id": row[0], "user_id": row[1], "username": row[2], "full_name": row[3],
            "subject": row[4], "message": row[5], "status": row[6], "created_at": row[7], "updated_at": row[8]}


async def get_ticket_replies(ticket_id: int) -> list:
    r = await execute(
        "SELECT id, sender_id, sender_name, is_admin, message, created_at FROM ticket_replies WHERE ticket_id=? ORDER BY created_at ASC",
        [ticket_id],
    )
    return [{"id": row[0], "sender_id": row[1], "sender_name": row[2], "is_admin": bool(row[3]),
             "message": row[4], "created_at": row[5]} for row in r.rows]


async def add_ticket_reply(ticket_id: int, sender_id: int, sender_name: str, is_admin: bool, message: str):
    await execute(
        "INSERT INTO ticket_replies (ticket_id, sender_id, sender_name, is_admin, message) VALUES (?,?,?,?,?)",
        [ticket_id, sender_id, sender_name, 1 if is_admin else 0, message],
    )
    new_status = "in_progress" if is_admin else "open"
    await execute(
        "UPDATE tickets SET updated_at=datetime('now'), status=? WHERE id=? AND status != 'closed'",
        [new_status, ticket_id],
    )


async def admin_get_tickets(status: str | None = None) -> list:
    if status:
        r = await execute(
            "SELECT id, user_id, username, full_name, subject, status, created_at, updated_at FROM tickets WHERE status=? ORDER BY updated_at DESC",
            [status],
        )
    else:
        r = await execute(
            "SELECT id, user_id, username, full_name, subject, status, created_at, updated_at FROM tickets ORDER BY updated_at DESC"
        )
    return [{"id": row[0], "user_id": row[1], "username": row[2], "full_name": row[3],
             "subject": row[4], "status": row[5], "created_at": row[6], "updated_at": row[7]} for row in r.rows]


async def update_ticket_status(ticket_id: int, status: str):
    await execute(
        "UPDATE tickets SET status=?, updated_at=datetime('now') WHERE id=?",
        [status, ticket_id],
    )
