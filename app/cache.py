"""
app/cache.py
Simple in-memory TTL cache for recommendation results.

Keyed by (user_id, occasion, temp_bucket) where temp_bucket rounds
temperature to the nearest 5 degrees. Expires after 1 hour.
"""

from __future__ import annotations

import threading
import time
from typing import Any

_DEFAULT_TTL = 3600  # 1 hour
_MAX_ENTRIES = 500


class TTLCache:
    """Thread-safe in-memory cache with per-entry TTL."""

    def __init__(self, ttl: int = _DEFAULT_TTL, max_entries: int = _MAX_ENTRIES):
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max = max_entries

    def _make_key(self, user_id: int, occasion: str, temp_celsius: float) -> str:
        bucket = round(temp_celsius / 5) * 5
        return f"{user_id}:{occasion}:{bucket}"

    def get(self, user_id: int, occasion: str, temp_celsius: float) -> Any | None:
        key = self._make_key(user_id, occasion, temp_celsius)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def put(self, user_id: int, occasion: str, temp_celsius: float, value: Any) -> None:
        key = self._make_key(user_id, occasion, temp_celsius)
        with self._lock:
            if len(self._store) >= self._max:
                self._evict()
            self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate_user(self, user_id: int) -> None:
        prefix = f"{user_id}:"
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        if len(self._store) >= self._max:
            oldest_key = min(self._store, key=lambda k: self._store[k][0])
            del self._store[oldest_key]


recommendation_cache = TTLCache()
