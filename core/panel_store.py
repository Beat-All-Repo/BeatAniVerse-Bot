"""
core/panel_store.py
===================
Panel Store System — pre-render panels into PANEL_DB_CHANNEL for instant delivery.
 - _PANEL_STORE: in-memory cache of {panel_type → {file_id, caption, ts}}
 - _deliver_panel(): fast CDN-speed panel delivery
 - _prebuild_all_panels(): background warm-up
 - safe_edit_panel(): convenience alias
"""
import asyncio
import json
import time
from typing import Optional

from telegram.constants import ParseMode
from telegram import InlineKeyboardMarkup, CallbackQuery, Bot

from core.config import PANEL_DB_CHANNEL
from core.logging_setup import logger
from core.panel_image import get_panel_pic, _PANEL_IMAGE_AVAILABLE
from core.helpers import safe_send_message


# ── In-memory panel store ──────────────────────────────────────────────────────
_PANEL_STORE: dict = {}
_PANEL_STORE_TTL: int = 300  # rebuild panels every 5 min


def _ps_key(panel_type: str) -> str:
    return f"panel_store_{panel_type}"


def _ps_get(panel_type: str) -> Optional[dict]:
    """Get stored panel from memory cache."""
    entry = _PANEL_STORE.get(panel_type)
    if entry and (time.monotonic() - entry.get("ts", 0)) < _PANEL_STORE_TTL:
        return entry
    try:
        from database_dual import get_setting
        raw = get_setting(_ps_key(panel_type), "")
        if raw:
            data = json.loads(raw)
            _PANEL_STORE[panel_type] = {**data, "ts": time.monotonic()}
            return _PANEL_STORE[panel_type]
    except Exception:
        pass
    return None


def _ps_set(panel_type: str, file_id: str, caption: str) -> None:
    """Cache a panel's photo file_id + caption."""
    entry = {"file_id": file_id, "caption": caption, "ts": time.monotonic()}
    _PANEL_STORE[panel_type] = entry
    try:
        from database_dual import set_setting
        set_setting(_ps_key(panel_type), json.dumps({"file_id": file_id, "caption": caption}))
    except Exception:
        pass


def _ps_invalidate(panel_type: str = None) -> None:
    """Invalidate stored panel(s) so they're rebuilt on next access."""
    if panel_type:
        _PANEL_STORE.pop(panel_type, None)
    else:
        _PANEL_STORE.clear()


async def _deliver_panel(
    bot,
    chat_id: int,
    panel_type: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
    query: Optional[CallbackQuery] = None,
) -> bool:
    """
    Ultra-fast panel delivery using pre-stored file_ids.
    Flow:
      1. Delete triggering message (if any)
      2. Check panel store for pre-cached file_id
      3a. If found: send_photo with cached file_id + keyboard
      3b. If not found: get_panel_pic() → send_photo → store file_id
      4. Text fallback if no photo available at all
    """
    # Step 1: Delete old message
    if query and query.message:
        try:
            await query.message.delete()
        except Exception:
            pass

    # Step 2: Look up cached file_id
    stored = _ps_get(panel_type)
    photo_to_send = stored["file_id"] if stored else None

    # Step 3a: If no cached file_id, get from panel image system
    if not photo_to_send:
        photo_to_send = get_panel_pic(panel_type)

    # Step 3b: Send
    if photo_to_send:
        try:
            try:
                sent = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_to_send,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    message_effect_id=5104841245755180586,  # 🔥
                )
            except Exception:
                sent = await bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_to_send,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
            # Store file_id for next time
            if sent and sent.photo and not stored:
                fid = sent.photo[-1].file_id
                _ps_set(panel_type, fid, caption)
                if _PANEL_IMAGE_AVAILABLE:
                    try:
                        from panel_image import set_tg_fileid
                        set_tg_fileid(panel_type, fid)
                        set_tg_fileid("default", fid)
                    except Exception:
                        pass
            return True
        except Exception as exc:
            logger.debug(f"_deliver_panel photo failed for {panel_type}: {exc}")
            _ps_invalidate(panel_type)

    # Step 4: Text fallback
    try:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                message_effect_id=5104841245755180586,
            )
        except Exception:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        return True
    except Exception as exc:
        logger.debug(f"_deliver_panel text fallback failed: {exc}")
        return False


async def safe_edit_panel(
    bot,
    query,
    chat_id: int,
    photo,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
    panel_type: str = "default",
) -> bool:
    """Alias → _deliver_panel. All panels now use the panel store system."""
    return await _deliver_panel(
        bot=bot,
        chat_id=chat_id,
        panel_type=panel_type,
        caption=caption,
        reply_markup=reply_markup,
        query=query,
    )


async def prebuild_all_panels(bot) -> None:
    """
    Background loop: pre-send every panel to PANEL_DB_CHANNEL to warm up
    file_ids, then store them. Runs every 5 min.
    """
    if not PANEL_DB_CHANNEL:
        return

    PANEL_TYPES = [
        "admin", "stats", "users", "channels", "clones",
        "settings", "broadcast", "upload", "categories",
        "poster", "manga", "autoforward", "flags", "style",
        "default",
    ]

    for ptype in PANEL_TYPES:
        try:
            photo = get_panel_pic(ptype)
            if not photo:
                continue
            stored = _ps_get(ptype)
            if stored:
                continue

            sent = await bot.send_photo(
                chat_id=PANEL_DB_CHANNEL,
                photo=photo,
                caption=f"<b>Panel Store</b> | <code>{ptype}</code>",
                parse_mode="HTML",
            )
            if sent and sent.photo:
                fid = sent.photo[-1].file_id
                _ps_set(ptype, fid, "")
                if _PANEL_IMAGE_AVAILABLE:
                    try:
                        from panel_image import set_tg_fileid
                        set_tg_fileid(ptype, fid)
                        set_tg_fileid("default", fid)
                    except Exception:
                        pass
                logger.debug(f"[panel_store] pre-built {ptype}")

            await asyncio.sleep(0.3)
        except Exception as exc:
            logger.debug(f"[panel_store] pre-build {ptype} failed: {exc}")
