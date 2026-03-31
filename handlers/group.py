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

    # Filter poster fires in ANY group (bot just needs to be member)
    if _FILTER_POSTER_AVAILABLE and lower and not lower.startswith("/"):
        asyncio.create_task(_handle_anime_filter(update, context, lower))

    # Single-letter alpha filter panel — also fires in ALL groups
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
        from handlers.media_cmds import generate_and_send_post
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
    Background task: detect anime title in message, deliver poster + join button.
    Keywords come directly from generated_links.channel_title — no separate table.
    """
    try:
        from database_dual import get_all_links, get_filter_poster_cache, save_filter_poster_cache, get_setting
        from filter_poster import _auto_delete, _get_default_poster_template, get_auto_delete_seconds, get_link_expiry_minutes
        from poster_engine import _anilist_anime, _build_anime_data, _make_poster, _get_settings
        import hashlib as _hl

        chat_id = update.effective_chat.id
        bot = context.bot

        all_links = get_all_links(limit=500, offset=0)
        if not all_links:
            return

        matched_anime = None
        matched_channel_id = None
        matched_link_id = None

        seen_titles = set()
        for row in all_links:
            link_id_r = row[0]
            channel_id_r = row[1]
            channel_title_r = (row[2] or "").strip()
            if not channel_title_r or channel_title_r.lower() in seen_titles:
                continue
            seen_titles.add(channel_title_r.lower())
            if len(channel_title_r) < 3:
                continue
            a_title = channel_title_r.lower()
            if a_title in lower_text or re.search(r'\b' + re.escape(a_title) + r'\b', lower_text):
                matched_anime = channel_title_r
                matched_channel_id = channel_id_r
                matched_link_id = link_id_r
                break

        if not matched_anime:
            return

        template = _get_default_poster_template(chat_id)
        cache_key = _hl.md5(f"{matched_anime.lower()}:{template}".encode()).hexdigest()
        auto_del = get_auto_delete_seconds(chat_id)
        exp_min = get_link_expiry_minutes(chat_id)

        # Build expirable invite link
        join_url = None
        invite_link_obj = None
        expire_ts = int(time.time()) + (exp_min * 60)
        _cid = matched_channel_id
        try:
            _cid = int(matched_channel_id)
        except (ValueError, TypeError):
            pass
        try:
            invite_link_obj = await bot.create_chat_invite_link(
                chat_id=_cid, expire_date=expire_ts, member_limit=1,
                creates_join_request=False, name=f"FP-{int(time.time())}",
            )
            join_url = invite_link_obj.invite_link
        except Exception as _ie:
            logger.debug(f"[filter] expirable invite link failed for {_cid}: {_ie}")

        if not join_url:
            join_url = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")

        delete_delay = exp_min * 60 if (invite_link_obj and join_url) else auto_del

        _raw_btn_text = (
            get_setting("env_JOIN_BTN_TEXT", "") or
            get_setting("env_join_btn_text", "") or
            JOIN_BTN_TEXT
        )
        join_text = small_caps(_raw_btn_text) if _raw_btn_text else small_caps("ᴊᴏɪɴ ɴᴏᴡ")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=join_url)]])

        # Check poster cache — serve instantly if available
        cached = get_filter_poster_cache(cache_key)
        if cached and cached.get("file_id"):
            try:
                caption = cached.get("caption", "")
                sent = await bot.send_photo(
                    chat_id=chat_id, photo=cached["file_id"],
                    caption=caption, parse_mode="HTML", reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                )
                if sent and delete_delay > 0:
                    asyncio.create_task(_auto_delete(bot, chat_id, sent.message_id, delay=delete_delay))
                return
            except Exception:
                pass

        # Generate poster
        loop = asyncio.get_event_loop()
        data = None
        try:
            data = await loop.run_in_executor(None, _anilist_anime, matched_anime)
        except Exception:
            pass

        poster_buf = None
        caption = f"<b>{html.escape(matched_anime)}</b>"
        site_url = ""

        if data:
            settings = _get_settings("anime")
            try:
                title_b, native, st, rows, desc, cover_url, score = await loop.run_in_executor(
                    None, _build_anime_data, data
                )
                # Try PosterBot template first for higher quality
                poster_buf = None
                try:
                    from modules.anime import _pb_create_poster_sync, _PB_TEMPLATE_MAP
                    if _PB_TEMPLATE_MAP.get(template) is not None:
                        poster_buf = await loop.run_in_executor(
                            None, _pb_create_poster_sync, template, data
                        )
                except Exception:
                    pass
                if not poster_buf:
                    poster_buf = await loop.run_in_executor(
                        None, _make_poster, template, title_b, native, st, rows, desc,
                        cover_url, score, settings.get("watermark_text"),
                        settings.get("watermark_position", "center"), None, "bottom",
                    )
                site_url = data.get("siteUrl", "")
                genres = ", ".join((data.get("genres") or [])[:3])
                t_d = data.get("title", {}) or {}
                eng = t_d.get("english") or t_d.get("romaji") or matched_anime
                caption = f"<b>{html.escape(eng)}</b>"
                if native:
                    caption += f"\n<i>{html.escape(native)}</i>"
                if genres:
                    caption += f"\n\n» <b>Genre:</b> {html.escape(genres)}"
                if len(caption) > 900:
                    caption = caption[:896] + "…"
            except Exception as _be:
                logger.debug(f"[filter] poster build error: {_be}")

        if site_url:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(join_text, url=join_url),
                InlineKeyboardButton("📋 Info", url=site_url),
            ]])

        sent_msg = None
        file_id_to_cache = None

        # Save to POSTER_DB_CHANNEL if configured
        from core.config import PANEL_DB_CHANNEL
        POSTER_DB_CHANNEL = int(os.getenv("POSTER_DB_CHANNEL", "0") or "0")
        if POSTER_DB_CHANNEL and poster_buf:
            try:
                poster_buf.seek(0)
                db_msg = await bot.send_photo(
                    chat_id=POSTER_DB_CHANNEL, photo=poster_buf,
                    caption=f"FilterPoster | {matched_anime} | {template}",
                    parse_mode="HTML",
                )
                if db_msg.photo:
                    file_id_to_cache = db_msg.photo[-1].file_id
            except Exception as _dbe:
                logger.debug(f"[filter] DB channel save: {_dbe}")

        if poster_buf:
            try:
                poster_buf.seek(0)
                sent_msg = await bot.send_photo(
                    chat_id=chat_id, photo=file_id_to_cache or poster_buf,
                    caption=caption, parse_mode="HTML", reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                )
                if sent_msg and not file_id_to_cache and sent_msg.photo:
                    file_id_to_cache = sent_msg.photo[-1].file_id
            except Exception as _se:
                logger.debug(f"[filter] poster send: {_se}")

        if not sent_msg:
            try:
                sent_msg = await bot.send_message(
                    chat_id=chat_id, text=caption, parse_mode="HTML",
                    reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

        if file_id_to_cache:
            try:
                save_filter_poster_cache(
                    cache_key=cache_key, anime_title=matched_anime,
                    template=template, file_id=file_id_to_cache,
                    channel_id=0, caption=caption,
                )
            except Exception:
                pass

        if sent_msg and delete_delay > 0:
            asyncio.create_task(_auto_delete(bot, chat_id, sent_msg.message_id, delay=delete_delay))

    except Exception as _top:
        logger.debug(f"[filter] _handle_anime_filter: {_top}")
