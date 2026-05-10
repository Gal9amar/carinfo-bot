"""
User management – free quota + access code system.
Storage: GitHub API for persistence, in-memory cache to minimize API calls.
"""

import base64
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import httpx

# ── GitHub storage config ──────────────────────────────────────────────────
_GH_TOKEN  = os.environ.get("GITHUB_PAT", "")
_GH_REPO   = os.environ.get("GITHUB_REPO", "Gal9amar/carinfo-bot")
_GH_PATH   = os.environ.get("GITHUB_DATA_PATH", "data/users.json")
_GH_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
_GH_API    = f"https://api.github.com/repos/{_GH_REPO}/contents/{_GH_PATH}"
_GH_HEADERS = {
    "Authorization": f"token {_GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}

# Local fallback
_LOCAL_DIR  = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
_LOCAL_FILE = os.path.join(_LOCAL_DIR, "users.json")

FREE_SEARCHES = 5

# ── In-memory cache ────────────────────────────────────────────────────────
_cache: Optional[dict] = None   # the data dict
_cache_sha: Optional[str] = None  # GitHub file SHA (needed for updates)


def _gh_available() -> bool:
    return bool(_GH_TOKEN)


def _load() -> dict:
    global _cache, _cache_sha
    if _cache is not None:
        return _cache

    if _gh_available():
        try:
            r = httpx.get(_GH_API, headers=_GH_HEADERS, params={"ref": _GH_BRANCH}, timeout=10)
            if r.status_code == 200:
                body = r.json()
                _cache_sha = body.get("sha")
                _cache = json.loads(base64.b64decode(body["content"]).decode("utf-8"))
                return _cache
            if r.status_code == 404:
                _cache = {}
                return _cache
        except Exception:
            pass

    # Local fallback
    os.makedirs(_LOCAL_DIR, exist_ok=True)
    if os.path.exists(_LOCAL_FILE):
        try:
            with open(_LOCAL_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
                return _cache
        except Exception:
            pass
    _cache = {}
    return _cache


def _save(data: dict) -> None:
    global _cache, _cache_sha
    _cache = data  # always update in-memory cache

    if _gh_available():
        try:
            content = base64.b64encode(
                json.dumps(data, ensure_ascii=False, indent=2).encode()
            ).decode()
            payload: dict = {
                "message": "update users data",
                "content": content,
                "branch": _GH_BRANCH,
            }
            if _cache_sha:
                payload["sha"] = _cache_sha
            r = httpx.put(_GH_API, headers=_GH_HEADERS, json=payload, timeout=15)
            if r.status_code in (200, 201):
                _cache_sha = r.json().get("content", {}).get("sha", _cache_sha)
            return
        except Exception:
            pass

    # Local fallback
    os.makedirs(_LOCAL_DIR, exist_ok=True)
    with open(_LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Helpers ────────────────────────────────────────────────────────────────

def _ukey(user_id: int) -> str:
    return str(user_id)


def _ensure_user(data: dict, user_id: int, username: str = "") -> dict:
    key = _ukey(user_id)
    if key not in data:
        data[key] = {
            "user_id": user_id,
            "username": username,
            "searches_done": 0,
            "searches_quota": FREE_SEARCHES,
            "codes_used": [],
            "grants": [],
            "first_seen": datetime.now().isoformat(),
        }
    elif username and not data[key].get("username"):
        data[key]["username"] = username
    return data


# ── Public API ─────────────────────────────────────────────────────────────

def is_allowed(user_id: int, username: str = "") -> tuple[bool, int]:
    """Returns (allowed, searches_left). -1 = unlimited."""
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
    add_searches = code_data.get("searches", 0)
    unlimited    = code_data.get("unlimited", False)
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
            result_msg = f"✅ נוספו {add_searches} בדיקות \\(סה\"כ {max(0, new_quota - done)} נותרו\\)"
    data[_ukey(user_id)].setdefault("codes_used", []).append(code)
    codes[code]["used_by"] = _ukey(user_id)
    codes[code]["used_at"] = datetime.now().isoformat()
    data["_codes"] = codes
    _save(data)
    return True, result_msg


def admin_grant(user_id: int, target_id: int, searches: int, note: str = "") -> str:
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
            msg = f"נוספו {searches} בדיקות \\(סה\"כ {max(0, new_q - done)} נותרו\\)"
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
