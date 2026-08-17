"""Owned vehicles ("רכבים שקניתי") — user purchase/sale tracking."""

import json

from src.db import execute


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "plate": row[1],
        "vehicle_data": json.loads(row[2] or "{}"),
        "purchase_price": row[3],
        "purchase_km": row[4],
        "purchase_date": row[5],
        "status": row[6],
        "sale_price": row[7],
        "sale_date": row[8],
        "expenses": row[9] or 0,
        "notes": row[10] or "",
    }


_COLS = ("id, plate, vehicle_data, purchase_price, purchase_km, "
         "purchase_date, status, sale_price, sale_date, expenses, notes")

_UPDATABLE_FIELDS = ("purchase_price", "purchase_km", "expenses", "sale_price", "notes")


async def add_owned_vehicle(user_id: int, plate: str, vehicle_data: dict,
                             purchase_price: float, purchase_km: int | None,
                             notes: str = "") -> int:
    await execute(
        "INSERT INTO owned_vehicles (user_id, plate, vehicle_data, purchase_price, purchase_km, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [user_id, plate, json.dumps(vehicle_data, ensure_ascii=False), purchase_price, purchase_km, notes],
    )
    r = await execute("SELECT last_insert_rowid()")
    return r.rows[0][0]


async def get_owned_vehicles(user_id: int) -> list[dict]:
    r = await execute(
        f"SELECT {_COLS} FROM owned_vehicles WHERE user_id=? ORDER BY id DESC",
        [user_id],
    )
    return [_row_to_dict(row) for row in r.rows]


async def get_owned_vehicle(owned_id: int, user_id: int) -> dict | None:
    r = await execute(
        f"SELECT {_COLS} FROM owned_vehicles WHERE id=? AND user_id=?",
        [owned_id, user_id],
    )
    return _row_to_dict(r.rows[0]) if r.rows else None


async def get_active_owned_vehicle(user_id: int, plate: str) -> dict | None:
    r = await execute(
        f"SELECT {_COLS} FROM owned_vehicles WHERE user_id=? AND plate=? AND status='owned'",
        [user_id, plate],
    )
    return _row_to_dict(r.rows[0]) if r.rows else None


async def mark_sold(owned_id: int, user_id: int, sale_price: float) -> None:
    await execute(
        "UPDATE owned_vehicles SET status='sold', sale_price=?, sale_date=datetime('now') "
        "WHERE id=? AND user_id=? AND status='owned'",
        [sale_price, owned_id, user_id],
    )


async def update_owned_vehicle(owned_id: int, user_id: int, **fields) -> None:
    sets, vals = [], []
    for key in _UPDATABLE_FIELDS:
        if fields.get(key) is not None:
            sets.append(f"{key}=?")
            vals.append(fields[key])
    if not sets:
        return
    vals += [owned_id, user_id]
    await execute(
        f"UPDATE owned_vehicles SET {', '.join(sets)} WHERE id=? AND user_id=?",
        vals,
    )


async def delete_owned_vehicle(owned_id: int, user_id: int) -> None:
    await execute("DELETE FROM owned_vehicles WHERE id=? AND user_id=?", [owned_id, user_id])
