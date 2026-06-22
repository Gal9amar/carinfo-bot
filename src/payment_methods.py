"""
Payment methods management — stored in DB.
"""
from src.db import execute

_DEFAULT_METHODS = [
    ("PayPal",  "", "https://www.paypal.me/", 1, 1),
    ("PayBox",  "", "https://links.payboxapp.com/", 1, 2),
]


async def init_payment_methods() -> None:
    for name, logo_url, payment_url, active, order in _DEFAULT_METHODS:
        await execute(
            "INSERT OR IGNORE INTO payment_methods (name, logo_url, payment_url, active, display_order) VALUES (?,?,?,?,?)",
            [name, logo_url, payment_url, active, order],
        )


async def get_payment_methods(active_only: bool = False) -> list[dict]:
    sql = "SELECT id, name, logo_url, payment_url, active, display_order FROM payment_methods"
    if active_only:
        sql += " WHERE active=1"
    sql += " ORDER BY display_order ASC"
    r = await execute(sql, [])
    return [
        {"id": row[0], "name": row[1], "logo_url": row[2], "payment_url": row[3], "active": bool(row[4]), "display_order": row[5]}
        for row in r.rows
    ]


async def add_payment_method(name: str, logo_url: str, payment_url: str) -> dict:
    r = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM payment_methods", [])
    order = r.rows[0][0] if r.rows else 1
    r2 = await execute(
        "INSERT INTO payment_methods (name, logo_url, payment_url, active, display_order) VALUES (?,?,?,1,?) RETURNING id",
        [name, logo_url, payment_url, order],
    )
    new_id = r2.rows[0][0] if r2.rows else None
    return {"id": new_id, "name": name, "logo_url": logo_url, "payment_url": payment_url, "active": True, "display_order": order}


async def update_payment_method(method_id: int, name: str, logo_url: str, payment_url: str, active: bool) -> None:
    await execute(
        "UPDATE payment_methods SET name=?, logo_url=?, payment_url=?, active=? WHERE id=?",
        [name, logo_url, payment_url, int(active), method_id],
    )


async def delete_payment_method(method_id: int) -> None:
    await execute("DELETE FROM payment_methods WHERE id=?", [method_id])


async def reorder_payment_methods(ordered_ids: list[int]) -> None:
    for i, mid in enumerate(ordered_ids):
        await execute("UPDATE payment_methods SET display_order=? WHERE id=?", [i + 1, mid])
