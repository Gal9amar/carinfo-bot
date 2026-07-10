"""Activity log — records key system events for admin review."""

from src.db import execute

ICONS = {
    "new_user":          "👋",
    "search":            "🔍",
    "payment_pending":   "💰",
    "payment_approved":  "✅",
    "payment_declined":  "❌",
    "ticket_new":        "🎫",
    "ticket_reply":      "💬",
    "ticket_status":     "🔒",
    "code_used":         "🔑",
    "code_created":      "➕",
    "code_deleted":      "🗑️",
    "grant":             "🎁",
    "block":             "🚫",
    "unblock":           "🔓",
    "broadcast":         "📢",
    "message":           "💌",
    "product_created":         "📦",
    "product_updated":         "✏️",
    "product_deleted":         "🗑️",
    "product_stock_added":     "📤",
    "product_order_delivered": "🎉",
}


async def log(event_type: str, description: str, user_id: int = 0, username: str = "") -> None:
    try:
        await execute(
            "INSERT INTO activity_log (event_type, user_id, username, description) VALUES (?, ?, ?, ?)",
            [event_type, user_id, username or "", description],
        )
    except Exception:
        pass


async def get_log(limit: int = 100) -> list[dict]:
    r = await execute(
        "SELECT id, event_type, user_id, username, description, created_at "
        "FROM activity_log ORDER BY id DESC LIMIT ?",
        [limit],
    )
    rows = []
    for row in r.rows:
        etype = row[1]
        rows.append({
            "id":          row[0],
            "event_type":  etype,
            "icon":        ICONS.get(etype, "📌"),
            "user_id":     row[2],
            "username":    row[3],
            "description": row[4],
            "created_at":  row[5],
        })
    return rows
