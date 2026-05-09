"""
Simple in-memory TTL cache – no Redis dependency needed.
Caches vehicle lookups for CACHE_TTL seconds to avoid hammering APIs.
"""

import time
from typing import Any, Optional

CACHE_TTL = 3600  # 1 hour


class TTLCache:
    def __init__(self, ttl: int = CACHE_TTL):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def clear_expired(self) -> None:
        now = time.monotonic()
        self._store = {k: v for k, v in self._store.items() if v[1] > now}


cache = TTLCache()
