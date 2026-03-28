"""
core/panel_image.py
===================
Panel image retrieval system.
Provides get_panel_pic() (sync) and get_panel_pic_async() (async).
Manages the DB-stored image list and background channel scanning.
"""
import asyncio
import json
import random
import time
from typing import Optional

from core.config import (
    PANEL_DB_CHANNEL, FALLBACK_IMAGE_CHANNEL,
    PANEL_IMAGE_FILE_ID, PANEL_PICS,
)
from core.logging_setup import logger


# ── In-memory channel scan cache ──────────────────────────────────────────────
_channel_scan_cache: list = []
_channel_scan_ts: float = 0.0
_CHANNEL_SCAN_TTL: float = 300.0  # re-scan every 5 min


# ── panel_image module integration ────────────────────────────────────────────
_PANEL_IMAGE_AVAILABLE = False
try:
    from panel_image import get_panel_image_async, clear_image_cache, get_cache_status  # noqa: F401
    _PANEL_IMAGE_AVAILABLE = True
except ImportError:
    async def get_panel_image_async(panel: str = "default"): return None
    def clear_image_cache(panel=None): return 0
    def get_cache_status(): return {}


# ── DB helpers ─────────────────────────────────────────────────────────────────

def get_panel_db_images() -> list:
    """Return list of {index, msg_id, file_id} dicts stored in DB."""
    try:
        from database_dual import get_setting
        raw = get_setting("panel_db_images", "[]") or "[]"
        items = json.loads(raw)
        if isinstance(items, list):
            return items
    except Exception:
        pass
    return []


def save_panel_db_images(items: list) -> None:
    from database_dual import set_setting
    set_setting("panel_db_images", json.dumps(items))


def get_panel_db_fileid() -> Optional[str]:
    """
    Return a random file_id for panel images — shared across ALL panel types.
    Priority:
      1. Manually added images (via /addpanelimg) — stored in DB
      2. Auto-scanned from PANEL_DB_CHANNEL (if set, 5-min cache)
      3. Auto-scanned from FALLBACK_IMAGE_CHANNEL
    """
    # Priority 1: manually added images
    items = get_panel_db_images()
    if items:
        item = random.choice(items)
        return item.get("file_id") or None

    # Priority 2 & 3: auto-scan (return from cache; non-blocking)
    now = time.monotonic()
    if _channel_scan_cache and (now - _channel_scan_ts) < _CHANNEL_SCAN_TTL:
        return random.choice(_channel_scan_cache)

    return random.choice(_channel_scan_cache) if _channel_scan_cache else None


def get_panel_pic(panel_type: str = "default") -> Optional[str]:
    """
    Get panel image — synchronous, always instant.
    Priority:
      1. Manually added images via /addpanelimg (stored in DB)
      2. PANEL_IMAGE_FILE_ID env var
      3. Session file_id cache (from panel_image module — channel scan)
      4. PANEL_PICS env var (file_ids or URLs)
    No external API calls.
    """
    fid = get_panel_db_fileid()
    if fid:
        return fid

    if PANEL_IMAGE_FILE_ID:
        return PANEL_IMAGE_FILE_ID

    if _PANEL_IMAGE_AVAILABLE:
        try:
            from panel_image import get_tg_fileid, get_channel_scan_fileid
            cached_fid = get_tg_fileid("default") or get_tg_fileid(panel_type)
            if cached_fid:
                return cached_fid
            scan_fid = get_channel_scan_fileid()
            if scan_fid:
                return scan_fid
        except Exception:
            pass

    if PANEL_PICS:
        return random.choice(PANEL_PICS)

    return None


async def get_panel_pic_async(panel_type: str = "default") -> Optional[str]:
    """
    Get panel image URL — ALWAYS instant (never blocks).
    Returns cached value immediately; triggers background refresh if stale.
    """
    quick = get_panel_pic(panel_type)
    scan_channel = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
    if not quick and scan_channel and not get_panel_db_images():
        try:
            asyncio.create_task(scan_panel_channel(None))
        except Exception:
            pass
    return quick


async def scan_panel_channel(bot) -> None:
    """
    Background task: scan PANEL_DB_CHANNEL (or FALLBACK_IMAGE_CHANNEL) for photos.
    Results cached 5 min. Never blocks the event loop.
    """
    global _channel_scan_cache, _channel_scan_ts

    if get_panel_db_images():
        return

    scan_channel = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
    if not scan_channel or not bot:
        return

    try:
        file_ids = []

        # Bot API fallback: probe sequential message IDs
        sink = PANEL_DB_CHANNEL or None
        if sink:
            for msg_id in range(1, 201):
                if len(file_ids) >= 30:
                    break
                try:
                    fwd = await bot.forward_message(
                        chat_id=sink,
                        from_chat_id=scan_channel,
                        message_id=msg_id,
                        disable_notification=True,
                    )
                    if fwd and fwd.photo and not fwd.sticker:
                        file_ids.append(fwd.photo[-1].file_id)
                        try:
                            await bot.delete_message(sink, fwd.message_id)
                        except Exception:
                            pass
                    elif fwd:
                        try:
                            await bot.delete_message(sink, fwd.message_id)
                        except Exception:
                            pass
                except Exception:
                    pass

        if file_ids:
            _channel_scan_cache = file_ids
            _channel_scan_ts = time.monotonic()
            logger.info(f"[panel] scanned {len(file_ids)} panel images from channel {scan_channel}")
        else:
            _channel_scan_ts = time.monotonic()
            logger.debug(f"[panel] no photos found in channel {scan_channel}")
    except Exception as exc:
        logger.debug(f"[panel] channel scan failed: {exc}")
