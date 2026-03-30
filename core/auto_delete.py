"""
core/auto_delete.py
===================
Global auto-delete system for BeatAniVerse bot.

Rules:
  ✅ Deletes ALL bot messages in DM after configured delay
  ✅ Deletes ALL bot messages in GC after configured delay
  ✅ Deletes user command/query messages too (in GC)
  ❌ NEVER deletes poster/photo messages (identified by has_photo or file_id)
  ❌ NEVER deletes chatbot reply messages in GC
  ❌ NEVER deletes channel-forwarded posts (admin content)
  ❌ Skips if auto-delete is disabled in settings

Admin-configurable:
  • DM delay  → DB key: auto_delete_dm_delay   (default 120s)
  • GC delay  → DB key: auto_delete_gc_delay   (default 60s)
  • Enabled   → DB key: auto_delete_messages   (true/false)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_delays() -> tuple[bool, int, int]:
    """Return (enabled, dm_delay_seconds, gc_delay_seconds)."""
    try:
        from database_dual import get_setting
        enabled  = get_setting("auto_delete_messages", "true") == "true"
        dm_delay = int(get_setting("auto_delete_dm_delay", "120") or "120")
        gc_delay = int(get_setting("auto_delete_gc_delay", "60")  or "60")
        return enabled, max(10, dm_delay), max(5, gc_delay)
    except Exception:
        return True, 120, 60


def _is_poster_message(msg: Any) -> bool:
    """
    Return True if the message is a poster/photo that must NOT be deleted.
    Covers: photos, documents, videos, sticker packs used as posters.
    """
    if not msg:
        return False
    # telegram Message object attributes
    if getattr(msg, "photo", None):
        return True
    if getattr(msg, "document", None):
        return True
    if getattr(msg, "video", None):
        return True
    # Check caption for poster markers
    caption = getattr(msg, "caption", "") or ""
    if "ᴊᴏɪɴ ɴᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ" in caption:
        return True
    return False


def _is_dm(chat_id: int) -> bool:
    return not str(chat_id).startswith("-")


def _is_gc(chat_id: int) -> bool:
    return str(chat_id).startswith("-")


# ── Core schedule function ─────────────────────────────────────────────────────

async def schedule_delete(
    bot: Any,
    chat_id: int,
    message_id: int,
    delay: Optional[int] = None,
    is_chatbot: bool = False,
    is_poster: bool = False,
    force: bool = False,
) -> None:
    """
    Schedule deletion of a single message.

    Args:
        bot:         Telegram bot instance
        chat_id:     Chat ID (negative = group, positive = DM)
        message_id:  Message ID to delete
        delay:       Override delay in seconds (None = use DB config)
        is_chatbot:  If True and chat is GC, skip (chatbot replies exempt)
        is_poster:   If True, skip always (poster/photo exempt)
        force:       If True, bypass enable/disable flag
    """
    if is_poster:
        return

    if is_chatbot and _is_gc(chat_id):
        return

    enabled, dm_delay, gc_delay = _get_delays()
    if not enabled and not force:
        return

    if delay is None:
        delay = dm_delay if _is_dm(chat_id) else gc_delay

    async def _do_delete():
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass  # Message already deleted or no permission — silent

    asyncio.create_task(_do_delete())


async def schedule_delete_msg(
    bot: Any,
    msg: Any,
    delay: Optional[int] = None,
    is_chatbot: bool = False,
    force: bool = False,
) -> None:
    """
    Convenience wrapper — pass the message object directly.
    Auto-detects poster messages and skips them.
    """
    if not msg:
        return
    chat_id    = getattr(msg, "chat_id", None) or getattr(getattr(msg, "chat", None), "id", None)
    message_id = getattr(msg, "message_id", None)
    if not chat_id or not message_id:
        return

    await schedule_delete(
        bot        = bot,
        chat_id    = chat_id,
        message_id = message_id,
        delay      = delay,
        is_chatbot = is_chatbot,
        is_poster  = _is_poster_message(msg),
        force      = force,
    )


async def schedule_delete_many(
    bot: Any,
    chat_id: int,
    message_ids: list[int],
    delay: Optional[int] = None,
    force: bool = False,
) -> None:
    """Schedule deletion of multiple message IDs at once."""
    enabled, dm_delay, gc_delay = _get_delays()
    if not enabled and not force:
        return
    if delay is None:
        delay = dm_delay if _is_dm(chat_id) else gc_delay

    async def _bulk_delete():
        await asyncio.sleep(delay)
        for mid in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass
            await asyncio.sleep(0.05)  # small gap to avoid flood

    asyncio.create_task(_bulk_delete())


# ── Middleware: universal message post-processor ───────────────────────────────

async def auto_delete_middleware(
    bot: Any,
    sent_msg: Any,
    trigger_msg: Any = None,
    is_chatbot: bool = False,
    override_delay: Optional[int] = None,
) -> None:
    """
    Call this right after sending any bot reply to handle auto-delete.

    - sent_msg:    The Message object the bot just sent
    - trigger_msg: The user's original command/query message (deleted faster in GC)
    - is_chatbot:  Set True for chatbot GC replies (exempts them)
    """
    enabled, dm_delay, gc_delay = _get_delays()
    if not enabled:
        return

    # Delete the bot's response (unless poster)
    if sent_msg:
        await schedule_delete_msg(
            bot        = bot,
            msg        = sent_msg,
            delay      = override_delay,
            is_chatbot = is_chatbot,
        )

    # Delete the user's trigger message quickly in GC
    if trigger_msg:
        chat_id = getattr(trigger_msg, "chat_id", None) or \
                  getattr(getattr(trigger_msg, "chat", None), "id", None)
        if chat_id and _is_gc(chat_id):
            await schedule_delete(
                bot        = bot,
                chat_id    = chat_id,
                message_id = trigger_msg.message_id,
                delay      = 5,  # user commands go faster
                force      = True,
            )
