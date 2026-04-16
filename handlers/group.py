"""
handlers/group.py
=================
Group message handler: filter poster detection, anime commands in groups,
alpha-filter panel, auto-delete, connected groups.
"""
import asyncio
import html
import os
import re
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL, JOIN_BTN_TEXT,
    LINK_EXPIRY_MINUTES,
)
from core.logging_setup import logger
from core.helpers import safe_send_message
from core.cache import panel_cache_get, panel_cache_set
from core.text_utils import small_caps


try:
    from filter_poster import (
        _get_filter_poster_enabled,
        _auto_delete,
        get_auto_delete_seconds,
        get_link_expiry_minutes,
    )
    _FILTER_POSTER_AVAILABLE = True
except ImportError:
    _FILTER_POSTER_AVAILABLE = False
    def _get_filter_poster_enabled(cid): return False


async def group_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle messages in connected groups.
    Filter poster fires in ALL groups. Other features only in connected groups.
    """
    if not update.message or not update.effective_chat:
        return
    from core.filters_system import passes_filter
    if not passes_filter(update):
        return

    chat_id = update.effective_chat.id
    text = update.message.text or update.message.caption or ""
    lower = text.lower().strip()

    # Filter poster is now handled entirely by filter_poster.py (get_or_generate_poster)
    # which runs at group=15 with a proper DB lookup first — no duplicate needed here.

    # Single-letter alpha filter panel — fires in ALL groups
    stripped = text.strip()
    if len(stripped) == 1 and stripped.isalpha() and not lower.startswith("/"):
        try:
            from modules.anime import _send_alpha_filter_panel
            asyncio.create_task(_send_alpha_filter_panel(update, context, stripped))
        except Exception as _afe:
            logger.debug(f"alpha_filter: {_afe}")

    # Check if group is connected
    _connected = panel_cache_get("connected_groups")
    if _connected is not None:
        if chat_id not in _connected:
            return
    else:
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("SELECT group_id FROM connected_groups WHERE active = TRUE")
                rows = cur.fetchall() or []
            _ids = {r[0] for r in rows}
            panel_cache_set("connected_groups", _ids)
            if chat_id not in _ids:
                return
        except Exception:
            return

    try:
        from database_dual import get_setting
        if get_setting("group_commands_enabled", "true") != "true":
            return
        auto_del = get_setting("auto_delete_messages", "true") == "true"
        del_delay = int(get_setting("auto_delete_delay", "60"))
    except Exception:
        auto_del = True
        del_delay = 60

    async def _del_user_cmd(msg=update.message):
        # Delete user's command message in GC after 5s always (clean chat)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass
    asyncio.create_task(_del_user_cmd())

    async def _group_post(category: str, query_text: str) -> None:
        from handlers.post_gen import generate_and_send_post
        sent = await generate_and_send_post(context, chat_id, category, query_text)
        # Never auto-delete poster photos — only delete text/non-photo responses
        if sent:
            from core.auto_delete import schedule_delete_msg
            await schedule_delete_msg(context.bot, sent, delay=del_delay)

    for prefix, category in [
        ("/anime ", "anime"), ("/manga ", "manga"),
        ("/movie ", "movie"), ("/tvshow ", "tvshow"),
    ]:
        if lower.startswith(prefix):
            query_text = text[len(prefix):].strip()
            if query_text:
                await _group_post(category, query_text)
            return




async def _handle_anime_filter(
    update: Update, context, lower_text: str
) -> None:
    """
    DEPRECATED — logic fully moved to filter_poster.get_or_generate_poster (group=15).
    This function is kept only for backwards-compatibility import safety.
    It intentionally does nothing.
    """
    return  # No-op
