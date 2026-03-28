"""
core/cache.py
=============
In-memory caching utilities.
 - API response cache with TTL (for AniList, TMDB, etc.)
 - Panel data cache (pre-computed bot panel content)
"""
import time
from typing import Any, Optional, Dict


# ── API response cache ─────────────────────────────────────────────────────────
_api_cache: Dict[str, Any] = {}
_API_CACHE_TTL: int = 300  # 5 minutes


def cache_get(key: str) -> Optional[Any]:
    """Get a value from the API cache if not expired."""
    entry = _api_cache.get(key)
    if entry and (time.time() - entry["ts"]) < _API_CACHE_TTL:
        return entry["data"]
    return None


def cache_set(key: str, data: Any) -> None:
    """Store a value in the API cache."""
    _api_cache[key] = {"data": data, "ts": time.time()}
    # Trim cache to prevent unbounded growth
    if len(_api_cache) > 500:
        oldest = min(_api_cache, key=lambda k: _api_cache[k]["ts"])
        _api_cache.pop(oldest, None)


def cache_clear() -> int:
    """Clear all cached API responses. Returns number cleared."""
    count = len(_api_cache)
    _api_cache.clear()
    return count


# ── Panel data cache ───────────────────────────────────────────────────────────
_PANEL_CACHE: dict = {}
_PANEL_CACHE_TS: dict = {}
_PANEL_CACHE_TTL = 45  # seconds


def panel_cache_get(key: str) -> Optional[Any]:
    ts = _PANEL_CACHE_TS.get(key, 0)
    if time.monotonic() - ts < _PANEL_CACHE_TTL:
        return _PANEL_CACHE.get(key)
    return None


def panel_cache_set(key: str, value: Any) -> None:
    _PANEL_CACHE[key] = value
    _PANEL_CACHE_TS[key] = time.monotonic()
