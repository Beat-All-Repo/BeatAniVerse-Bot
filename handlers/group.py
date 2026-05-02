"""
PATCH for handlers/group.py
============================
Changes:
  1. Filter now also triggers on FIRST WORD of a message (index-type trigger)
  2. Inline matching results sent as buttons when multiple anime match
  3. Callback handler for inline match selection

Replace your existing `group_message_handler` and add the new callback handler.
"""

import asyncio
import html
import os
import re
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CallbackQueryHandler

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
        get_or_generate_poster,
    )
    _FILTER_POSTER_AVAILABLE = True
except ImportError:
    _FILTER_POSTER_AVAILABLE = False
    def _get_filter_poster_enabled(cid): return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def _get_all_anime_titles() -> list[str]:
    """Fetch all registered anime titles from anime_channel_links table."""
    try:
        from database_dual import get_all_anime_channel_links
        rows = get_all_anime_channel_links()
        # rows: (id, anime_title, channel_id, channel_title, link_id, created_at)
        return [r[1] for r in rows if r[1]]
    except Exception:
        return []


def _find_matches(query: str, all_titles: list[str]) -> list[str]:
    """
    Return list of matching anime titles for a query.
    Priority:
      1. Exact match (full text)
      2. Starts-with match on full text
      3. Starts-with match on first word only
      4. Contains match
    Returns max 5 results, deduplicated.
    """
    q = _normalize(query)
    if not q:
        return []

    exact, starts, first_word, contains = [], [], [], []

    for title in all_titles:
        t = _normalize(title)
        if t == q:
            exact.append(title)
        elif t.startswith(q):
            starts.append(title)
        elif t.split()[0] == q.split()[0]:  # first word matches
            first_word.append(title)
        elif q in t:
            contains.append(title)

    seen = set()
    results = []
    for lst in (exact, starts, first_word, contains):
        for item in lst:
            key = _normalize(item)
            if key not in seen:
                seen.add(key)
                results.append(item)
            if len(results) >= 5:
                break
        if len(results) >= 5:
            break

    return results


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN GROUP MESSAGE HANDLER  (replace existing one)
# ─────────────────────────────────────────────────────────────────────────────

async def group_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.message or not update.effective_chat:
        return
    from core.filters_system import passes_filter
    if not passes_filter(update):
        return

    chat_id = update.effective_chat.id
    text = update.message.text or update.message.caption or ""
    lower = text.lower().strip()

    # ── Alpha filter panel (single letter) ───────────────────────────────────
    stripped = text.strip()
    if len(stripped) == 1 and stripped.isalpha() and not lower.startswith("/"):
        try:
            from modules.anime import _send_alpha_filter_panel
            asyncio.create_task(_send_alpha_filter_panel(update, context, stripped))
        except Exception as _afe:
            logger.debug(f"alpha_filter: {_afe}")

    # ── Filter poster trigger ─────────────────────────────────────────────────
    if _FILTER_POSTER_AVAILABLE and _get_filter_poster_enabled(chat_id):
        # Build candidate queries:
        #   1. Full message text
        #   2. First word only (index-type trigger)
        full_query = text.strip()
        first_word = text.strip().split()[0] if text.strip() else ""

        queries_to_try = [full_query]
        if first_word and first_word != full_query and len(first_word) >= 3:
            queries_to_try.append(first_word)

        all_titles = _get_all_anime_titles()
        matches: list[str] = []

        for q in queries_to_try:
            matches = _find_matches(q, all_titles)
            if matches:
                break

        if matches:
            if len(matches) == 1:
                # Single match → fire poster directly
                asyncio.create_task(
                    get_or_generate_poster(
                        bot=context.bot,
                        chat_id=chat_id,
                        title=matches[0],
                        reply_to_message_id=update.message.message_id,
                        auto_delete_seconds=get_auto_delete_seconds(chat_id),
                        link_expiry_minutes=get_link_expiry_minutes(chat_id),
                    )
                )
            else:
                # Multiple matches → send inline selection buttons
                asyncio.create_task(
                    _send_inline_match_buttons(
                        update, context, matches, chat_id
                    )
                )

    # ── Connected-group-only features below ───────────────────────────────────
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
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass
    asyncio.create_task(_del_user_cmd())

    async def _group_post(category: str, query_text: str) -> None:
        from handlers.post_gen import generate_and_send_post
        sent = await generate_and_send_post(context, chat_id, category, query_text)
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


# ─────────────────────────────────────────────────────────────────────────────
#  INLINE MATCH BUTTONS
# ─────────────────────────────────────────────────────────────────────────────

async def _send_inline_match_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    matches: list[str],
    chat_id: int,
) -> None:
    """Send a message with one button per matched anime title."""
    del_seconds = get_auto_delete_seconds(chat_id)

    buttons = [
        [InlineKeyboardButton(
            f"🎌 {title}",
            callback_data=f"filter_pick:{chat_id}:{title[:48]}"
        )]
        for title in matches
    ]
    buttons.append([
        InlineKeyboardButton("❌ Cancel", callback_data=f"filter_pick_cancel:{chat_id}")
    ])

    text = f"<b>Found {len(matches)} results</b> — pick one:"

    try:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
            reply_to_message_id=update.message.message_id,
        )
        if sent and del_seconds > 0:
            asyncio.create_task(
                _auto_delete(context.bot, chat_id, sent.message_id, delay=del_seconds)
            )
    except Exception as exc:
        logger.debug(f"inline_match_buttons error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
#  CALLBACK: user taps a match button
# ─────────────────────────────────────────────────────────────────────────────

async def filter_pick_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data or ""

    # Cancel
    if data.startswith("filter_pick_cancel:"):
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # Pick
    if data.startswith("filter_pick:"):
        # format: filter_pick:<chat_id>:<title>
        parts = data.split(":", 2)
        if len(parts) < 3:
            return
        try:
            chat_id = int(parts[1])
        except ValueError:
            return
        title = parts[2]

        # Delete the selection message
        try:
            await query.message.delete()
        except Exception:
            pass

        if not _FILTER_POSTER_AVAILABLE:
            return

        asyncio.create_task(
            get_or_generate_poster(
                bot=context.bot,
                chat_id=chat_id,
                title=title,
                reply_to_message_id=None,
                auto_delete_seconds=get_auto_delete_seconds(chat_id),
                link_expiry_minutes=get_link_expiry_minutes(chat_id),
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
#  DEPRECATED stub (kept for import safety)
# ─────────────────────────────────────────────────────────────────────────────

async def _handle_anime_filter(
    update: Update, context, lower_text: str
) -> None:
    return  # No-op


