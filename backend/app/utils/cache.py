"""
SMS-064 — Lightweight in-process TTL cache for expensive read aggregations
(e.g. the admin KPI dashboard).

This is a simple per-worker dict cache, matching the sprint's "Redis or simple
dict cache" allowance. Keys are namespaced by tenant (school slug) by the caller
so tenants never share cached data. A TTL of 0 disables caching entirely, which
keeps the test suite deterministic (TestingConfig sets DASHBOARD_CACHE_TTL=0).
"""
import time
import threading


class TTLCache:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        """Return the cached value for key if present and unexpired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key, value, ttl):
        with self._lock:
            self._store[key] = (time.time() + ttl, value)

    def invalidate(self, key):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()


# Module-level singleton shared across requests within a worker process.
dashboard_cache = TTLCache()
