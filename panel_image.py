# ==============================================================================
# PLACE AT: /app/panel_image.py
# ACTION: Replace existing file
# ==============================================================================
#!/usr/bin/env python3
"""
BeatAniVerse Bot — Panel Image System (Channel-Only Edition)
=============================================================
Images come EXCLUSIVELY from Telegram channels — zero external API calls.

Priority order:
  1. Manually added images via /addpanelimg → stored in DB (bot_settings)
  2. Auto-scanned photos from PANEL_DB_CHANNEL (env var)
  3. Auto-scanned photos from FALLBACK_IMAGE_CHANNEL (default: -1003794802745)
  4. Returns None — panel shows text-only (never fetches from any image API)

Speed:
  • All delivery is via Telegram file_id — no HTTP fetches, CDN-speed always.
  • All panels share the same file_id pool (no per-panel separate fetches).
  • Stickers and non-photo messages are automatically skipped during scan.

Admin can add images via:
  Admin Panel → SETTINGS → 🖼 PANEL IMAGE SOURCE → /addpanelimg

No waifu.im, nekos.best, AniList, TMDB, safone, pic.re — ever.
"""

import os
import time
import random
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# ── In-memory file_id cache — session-scoped, shared across all panel types ───
_tg_fileid_cache: Dict[str, str] = {}   # "default" → file_id
_channel_scan_cache: list = []           # list of file_ids from channel scan
_channel_scan_ts: float = 0.0
_CHANNEL_SCAN_TTL: float = 300.0        # re-use scan for 5 minutes


# ── Telegram file_id cache ────────────────────────────────────────────────────

def get_tg_fileid(panel: str = "default") -> Optional[str]:
    """Return cached Telegram file_id, or None."""
    # All panels share one pool — always use "default" key
    return _tg_fileid_cache.get("default") or _tg_fileid_cache.get(panel)

def set_tg_fileid(panel: str, file_id: str) -> None:
    """Store a Telegram file_id after a successful send."""
    if file_id:
        _tg_fileid_cache["default"] = file_id  # share across all panels
        _tg_fileid_cache[panel] = file_id
        logger.debug(f"Panel file_id cached: {file_id[:20]}…")

def clear_tg_fileid(panel: str = None) -> None:
    """Clear file_id cache (call when panel images change)."""
    _tg_fileid_cache.clear()


# ── Channel scan cache ────────────────────────────────────────────────────────

def get_channel_scan_fileid() -> Optional[str]:
    """Return a random file_id from the channel scan cache, or None."""
    if _channel_scan_cache:
        return random.choice(_channel_scan_cache)
    return None

def set_channel_scan_cache(file_ids: list) -> None:
    """Store file_ids scanned from a channel."""
    global _channel_scan_cache, _channel_scan_ts
    _channel_scan_cache = file_ids
    _channel_scan_ts = time.monotonic()

def is_channel_scan_fresh() -> bool:
    return bool(_channel_scan_cache and (time.monotonic() - _channel_scan_ts) < _CHANNEL_SCAN_TTL)


# ── Main public API ───────────────────────────────────────────────────────────

def get_panel_image(panel: str = "default", force_refresh: bool = False) -> Optional[str]:
    """
    Synchronous panel image getter — channel file_ids only, no APIs.
    Returns a Telegram file_id string, or None.
    """
    # Session cache hit
    if not force_refresh:
        fid = get_tg_fileid(panel)
        if fid:
            return fid

    # Channel scan cache
    fid = get_channel_scan_fileid()
    if fid:
        return fid

    return None


def get_panel_image_sync(panel: str = "default") -> Optional[str]:
    return get_panel_image(panel)


async def get_panel_image_async(panel: str = "default") -> Optional[str]:
    """
    Async wrapper — always instant, no awaiting external HTTP.
    Returns cached file_id or None.
    """
    return get_panel_image(panel)


def clear_image_cache(panel: str = None) -> int:
    """Clear all caches. Returns number of entries cleared."""
    count = len(_tg_fileid_cache) + len(_channel_scan_cache)
    _tg_fileid_cache.clear()
    _channel_scan_cache.clear()
    return count


def get_cache_status() -> Dict[str, Any]:
    """Return cache status for admin diagnostics."""
    return {
        "file_id_cache_size": len(_tg_fileid_cache),
        "channel_scan_size":  len(_channel_scan_cache),
        "channel_scan_fresh": is_channel_scan_fresh(),
        "sample_fid":         (_channel_scan_cache[0][:20] + "…") if _channel_scan_cache else None,
    }


# ── Compatibility shims (keep old import paths working) ──────────────────────

def _is_cached(panel: str = "default") -> bool:
    """Compat: always True if we have any file_id cached."""
    return bool(get_tg_fileid(panel) or _channel_scan_cache)
