"""
Manual digital products — stored in DB, cached in memory.
Two stock modes:
  - delivery_type='auto'   -> pre-uploaded content units (product_stock table),
                               one claimed and auto-delivered per order.
  - delivery_type='manual' -> a plain quantity_stock counter; admin fulfills
                               each order by hand (delivered via bot.py / the
                               admin webapp, see deliver_order()).
"""

import json
from src.db import execute

_cache: list[tuple] | None = None  # (id, name, description, image_url, price, delivery_type, delivery_time_note, quantity_stock, display_order, is_active)


async def init_products() -> None:
    await execute("""
        CREATE TABLE IF NOT EXISTS products (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            name               TEXT NOT NULL,
            description        TEXT DEFAULT '',
            image_url          TEXT DEFAULT '',
            price              INTEGER NOT NULL,
            delivery_type      TEXT NOT NULL DEFAULT 'manual',
            delivery_time_note TEXT DEFAULT '',
            quantity_stock     INTEGER DEFAULT 0,
            display_order      INTEGER DEFAULT 0,
            is_active          INTEGER DEFAULT 1,
            created_at         TEXT DEFAULT (datetime('now'))
        )
    """)
    await execute("""
        CREATE TABLE IF NOT EXISTS product_stock (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            content    TEXT NOT NULL,
            is_used    INTEGER DEFAULT 0,
            order_ref  TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    try:
        await execute("CREATE INDEX IF NOT EXISTS idx_product_stock_unused ON product_stock(product_id, is_used)")
    except Exception:
        pass
    await get_products(force_reload=True)


async def get_products(force_reload: bool = False, active_only: bool = False) -> list[tuple]:
    """Returns (id, name, description, image_url, price, delivery_type, delivery_time_note,
    quantity_stock, display_order, is_active) sorted by display_order."""
    global _cache
    if _cache is None or force_reload:
        r = await execute(
            "SELECT id, name, COALESCE(description,''), COALESCE(image_url,''), price, "
            "delivery_type, COALESCE(delivery_time_note,''), COALESCE(quantity_stock,0), "
            "display_order, COALESCE(is_active,1) FROM products ORDER BY display_order, id"
        )
        _cache = [tuple(row) for row in r.rows]
    if active_only:
        return [p for p in _cache if p[9] == 1]
    return _cache


async def get_product(product_id: int) -> tuple | None:
    prods = await get_products()
    return next((p for p in prods if p[0] == product_id), None)


async def add_product(
    name: str, description: str = "", image_url: str = "", price: int = 0,
    delivery_type: str = "manual", delivery_time_note: str = "", quantity_stock: int = 0,
    is_active: int = 1,
) -> int:
    r = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM products")
    next_order = r.rows[0][0] if r.rows else 1
    r2 = await execute(
        "INSERT INTO products (name, description, image_url, price, delivery_type, delivery_time_note, "
        "quantity_stock, display_order, is_active) VALUES (?,?,?,?,?,?,?,?,?) RETURNING id",
        [name, description, image_url, price, delivery_type, delivery_time_note, quantity_stock, next_order, is_active],
    )
    await get_products(force_reload=True)
    return r2.rows[0][0] if r2.rows else 0


async def update_product(product_id: int, **kwargs) -> None:
    allowed = {"name", "description", "image_url", "price", "delivery_type",
               "delivery_time_note", "quantity_stock", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await execute(f"UPDATE products SET {set_clause} WHERE id=?", [*fields.values(), product_id])
    await get_products(force_reload=True)


async def delete_product(product_id: int) -> None:
    await execute("DELETE FROM product_stock WHERE product_id=?", [product_id])
    await execute("DELETE FROM products WHERE id=?", [product_id])
    await get_products(force_reload=True)


async def reorder_products(ordered_ids: list[int]) -> None:
    for i, pid in enumerate(ordered_ids):
        await execute("UPDATE products SET display_order=? WHERE id=?", [i + 1, pid])
    await get_products(force_reload=True)


def invalidate_cache() -> None:
    global _cache
    _cache = None


# ── Auto-delivery stock pool ────────────────────────────────────────────────

async def add_stock_units(product_id: int, lines: list[str]) -> int:
    added = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        await execute(
            "INSERT INTO product_stock (product_id, content) VALUES (?, ?)",
            [product_id, line],
        )
        added += 1
    return added


async def get_stock_units(product_id: int) -> list[dict]:
    r = await execute(
        "SELECT id, content, is_used, order_ref, created_at FROM product_stock WHERE product_id=? ORDER BY id",
        [product_id],
    )
    return [
        {"id": row[0], "content": row[1], "is_used": bool(row[2]), "order_ref": row[3], "created_at": row[4]}
        for row in r.rows
    ]


async def claim_stock_unit(product_id: int, order_ref: str) -> str | None:
    """Atomically claim one unused unit for this order. Returns its content, or
    None if none was available (caller should degrade to manual-delivery)."""
    try:
        r = await execute(
            "UPDATE product_stock SET is_used=1, order_ref=? "
            "WHERE id=(SELECT id FROM product_stock WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1) "
            "AND is_used=0 RETURNING content",
            [order_ref, product_id],
        )
        if r.rows:
            return r.rows[0][0]
        return None
    except Exception:
        # RETURNING not supported by this libsql build — fall back to update-then-read.
        await execute(
            "UPDATE product_stock SET is_used=1, order_ref=? "
            "WHERE id=(SELECT id FROM product_stock WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1) "
            "AND is_used=0",
            [order_ref, product_id],
        )
        r = await execute(
            "SELECT content FROM product_stock WHERE product_id=? AND order_ref=? AND is_used=1 LIMIT 1",
            [product_id, order_ref],
        )
        return r.rows[0][0] if r.rows else None


async def restore_stock_unit(order_ref: str) -> None:
    await execute(
        "UPDATE product_stock SET is_used=0, order_ref='' WHERE order_ref=? AND is_used=1",
        [order_ref],
    )


async def available_stock_count(product_id: int, delivery_type: str) -> int:
    if delivery_type == "auto":
        r = await execute(
            "SELECT COUNT(*) FROM product_stock WHERE product_id=? AND is_used=0", [product_id]
        )
        return r.rows[0][0] if r.rows else 0
    r = await execute("SELECT COALESCE(quantity_stock,0) FROM products WHERE id=?", [product_id])
    return r.rows[0][0] if r.rows else 0


async def decrement_manual_stock(product_id: int) -> None:
    await execute(
        "UPDATE products SET quantity_stock = quantity_stock - 1 WHERE id=? AND quantity_stock > 0",
        [product_id],
    )
    await get_products(force_reload=True)


async def restore_manual_stock(product_id: int) -> None:
    await execute(
        "UPDATE products SET quantity_stock = quantity_stock + 1 WHERE id=?",
        [product_id],
    )
    await get_products(force_reload=True)


# ── Manual-delivery fulfillment ─────────────────────────────────────────────

async def deliver_order(ref: str, content: str) -> bool:
    """Shared fulfillment logic — called from both the admin webapp endpoint
    and the bot.py admin-reply flow, so both converge on identical behavior."""
    r = await execute(
        "SELECT user_id, label, status FROM paypal_transactions WHERE ref=?", [ref]
    )
    if not r.rows:
        return False
    user_id, label, status = r.rows[0]
    if status != "pending_delivery":
        return False
    await execute(
        "UPDATE paypal_transactions SET status='completed', delivery_content=?, updated_at=datetime('now') WHERE ref=?",
        [content, ref],
    )
    try:
        from src.notifier import notify_user_product_delivered
        await notify_user_product_delivered(int(user_id), label, ref, content)
    except Exception:
        pass
    try:
        from src.activity import log as _log
        await _log("product_order_delivered", f"מוצר נשלח ידנית: {label} להזמנה {ref}", int(user_id))
    except Exception:
        pass
    return True
