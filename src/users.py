"""
User management – free quota + access code system.
Supports:
  - Free searches per new user (FREE_SEARCHES)
  - Codes with fixed search quota OR unlimited days
  - Admin can grant searches directly to any user
  - Full per-user tracking
"""

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

_data_dir = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
DATA_FILE = os.path.join(_data_dir, "users.json")
FREE_SEARCHES = 5


def _load() -> dict:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ukey(user_id: int) -> str:
    return str(user_id)


def _ensure_user(data: dict, user_id: int, username: str = "") -> dict:
    key = _ukey(user_id)
    if key not in data:
        data[key] = {
            "user_id": user_id,
            "username": username,
            "searches_done": 0,
            "searches_quota": FREE_SEARCHES,  # total allowed
            "codes_used": [],
            "grants": [],  # log of admin grants
            "first_seen": datetime.now().isoformat(),
        }
    elif username and not data[key].get("username"):
        data[key]["username"] = username
    return data


def get_user(user_id: int, username: str = "") -> dict:
    data = _load()
    data = _ensure_user(data, user_id, username)
    _save(data)
    return data[_ukey(user_id)]


def is_allowed(user_id: int, username: str = "") -> tuple[bool, int]:
    """
    Returns (allowed, searches_left).
    searches_left = -1 means unlimited.
    """
    data = _load()
    data = _ensure_user(data, user_id, username)
    u = data[_ukey(user_id)]

    quota = u.get("searches_quota", FREE_SEARCHES)
    done  = u.get("searches_done", 0)

    if quota == -1:
        return True, -1

    left = max(0, quota - done)
    return left > 0, left


def increment_search(user_id: int) -> None:
    data = _load()
    data = _ensure_user(data, user_id)
    data[_ukey(user_id)]["searches_done"] = data[_ukey(user_id)].get("searches_done", 0) + 1
    _save(data)


def apply_code(user_id: int, code: str, username: str = "") -> tuple[bool, str]:
    data = _load()
    codes = data.get("_codes", {})

    if code not in codes:
        return False, "קוד לא תקין"

    code_data = codes[code]

    data = _ensure_user(data, user_id, username)
    u = data[_ukey(user_id)]

    if code in u.get("codes_used", []):
        return False, "קוד זה כבר נוצל על ידך"

    if code_data.get("single_use") and code_data.get("used_by"):
        return False, "קוד זה כבר נוצל"

    code_exp = code_data.get("expires")
    if code_exp:
        try:
            if datetime.now() > datetime.fromisoformat(code_exp):
                return False, "קוד פג תוקף"
        except Exception:
            pass

    # Add searches from code
    add_searches = code_data.get("searches", 0)
    unlimited = code_data.get("unlimited", False)

    if unlimited:
        data[_ukey(user_id)]["searches_quota"] = -1
        result_msg = "✅ גישה בלתי מוגבלת הופעלה"
    else:
        current = data[_ukey(user_id)].get("searches_quota", FREE_SEARCHES)
        if current == -1:
            result_msg = "✅ כבר יש לך גישה בלתי מוגבלת"
        else:
            new_quota = current + add_searches
            data[_ukey(user_id)]["searches_quota"] = new_quota
            done = data[_ukey(user_id)].get("searches_done", 0)
            result_msg = f"✅ נוספו {add_searches} בדיקות \\(סה\"כ {max(0, new_quota - done)} בדיקות נותרו\\)"

    data[_ukey(user_id)].setdefault("codes_used", []).append(code)
    codes[code]["used_by"] = _ukey(user_id)
    codes[code]["used_at"] = datetime.now().isoformat()
    data["_codes"] = codes
    _save(data)

    return True, result_msg


def admin_grant(user_id: int, target_id: int, searches: int, note: str = "") -> str:
    """Admin grants X searches to a user directly."""
    data = _load()
    data = _ensure_user(data, target_id)
    u = data[_ukey(target_id)]

    if searches == -1:
        data[_ukey(target_id)]["searches_quota"] = -1
        msg = "גישה בלתי מוגבלת"
    else:
        current = u.get("searches_quota", FREE_SEARCHES)
        if current == -1:
            msg = "כבר יש לו גישה בלתי מוגבלת"
        else:
            new_q = current + searches
            data[_ukey(target_id)]["searches_quota"] = new_q
            done = u.get("searches_done", 0)
            msg = f"נוספו {searches} בדיקות \\(סה\"כ {max(0,new_q-done)} נותרו\\)"

    data[_ukey(target_id)].setdefault("grants", []).append({
        "by": user_id,
        "searches": searches,
        "note": note,
        "at": datetime.now().isoformat(),
    })
    _save(data)
    return msg


def generate_code(searches: int = 10, single_use: bool = True,
                  unlimited: bool = False, expires_days: int = 90) -> str:
    code = secrets.token_hex(4).upper()
    data = _load()
    data.setdefault("_codes", {})[code] = {
        "searches": searches,
        "unlimited": unlimited,
        "single_use": single_use,
        "expires": (datetime.now() + timedelta(days=expires_days)).isoformat(),
        "used_by": None,
        "used_at": None,
        "created": datetime.now().isoformat(),
    }
    _save(data)
    return code


def get_all_users() -> list[dict]:
    data = _load()
    users = []
    for key, val in data.items():
        if key.startswith("_"):
            continue
        u = dict(val)
        quota = u.get("searches_quota", FREE_SEARCHES)
        done  = u.get("searches_done", 0)
        u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
        users.append(u)
    users.sort(key=lambda x: x.get("searches_done", 0), reverse=True)
    return users


def get_user_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@").lower()
    data = _load()
    for key, val in data.items():
        if key.startswith("_"):
            continue
        if str(val.get("username", "")).lower() == username:
            u = dict(val)
            quota = u.get("searches_quota", FREE_SEARCHES)
            done  = u.get("searches_done", 0)
            u["searches_left"] = -1 if quota == -1 else max(0, quota - done)
            return u
    return None


def admin_stats() -> dict:
    data = _load()
    users = [v for k, v in data.items() if not k.startswith("_")]
    codes = data.get("_codes", {})
    active = sum(1 for u in users if u.get("searches_quota") == -1 or
                 u.get("searches_quota", 0) > u.get("searches_done", 0))
    return {
        "total_users": len(users),
        "active_users": active,
        "total_searches": sum(u.get("searches_done", 0) for u in users),
        "total_codes": len(codes),
        "used_codes": sum(1 for c in codes.values() if c.get("used_by")),
    }
