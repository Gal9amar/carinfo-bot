"""
Payment methods management — stored in DB.
"""
from src.db import execute



async def get_payment_methods(active_only: bool = False) -> list[dict]:
    sql = "SELECT id, name, logo_url, payment_url, active, display_order, requires_manual_approval FROM payment_methods"
    if active_only:
        sql += " WHERE active=1"
    sql += " ORDER BY display_order ASC"
    r = await execute(sql, [])
    return [
        {
            "id": row[0], "name": row[1], "logo_url": row[2], "payment_url": row[3],
            "active": bool(row[4]), "display_order": row[5],
            "requires_manual_approval": bool(row[6]),
        }
        for row in r.rows
    ]


async def add_payment_method(name: str, logo_url: str, payment_url: str, requires_manual_approval: bool = True) -> dict:
    r = await execute("SELECT COALESCE(MAX(display_order), 0) + 1 FROM payment_methods", [])
    order = r.rows[0][0] if r.rows else 1
    r2 = await execute(
        "INSERT INTO payment_methods (name, logo_url, payment_url, active, display_order, requires_manual_approval) VALUES (?,?,?,1,?,?) RETURNING id",
        [name, logo_url, payment_url, order, int(requires_manual_approval)],
    )
    new_id = r2.rows[0][0] if r2.rows else None
    return {"id": new_id, "name": name, "logo_url": logo_url, "payment_url": payment_url, "active": True, "display_order": order, "requires_manual_approval": requires_manual_approval}


async def update_payment_method(method_id: int, name: str, logo_url: str, payment_url: str, active: bool, requires_manual_approval: bool = True) -> None:
    await execute(
        "UPDATE payment_methods SET name=?, logo_url=?, payment_url=?, active=?, requires_manual_approval=? WHERE id=?",
        [name, logo_url, payment_url, int(active), int(requires_manual_approval), method_id],
    )


async def delete_payment_method(method_id: int) -> None:
    await execute("DELETE FROM payment_methods WHERE id=?", [method_id])


async def reorder_payment_methods(ordered_ids: list[int]) -> None:
    for i, mid in enumerate(ordered_ids):
        await execute("UPDATE payment_methods SET display_order=? WHERE id=?", [i + 1, mid])
