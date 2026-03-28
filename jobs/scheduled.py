"""
jobs/scheduled.py
=================
All periodic background jobs:
  - manga_update_job: check tracked manga for new chapters
  - cleanup_expired_links_job: purge expired deep links
  - check_scheduled_broadcasts: fire pending scheduled broadcasts
  - _prewarm_all_caches: keep panel data warm
"""
import asyncio
from datetime import datetime
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, RATE_LIMIT_DELAY
from core.text_utils import b, bq, e, code, format_number, format_duration, small_caps
from core.helpers import safe_send_message
from core.cache import panel_cache_set
from core.logging_setup import logger


# ── Manga chapter update job ──────────────────────────────────────────────────

async def manga_update_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: check all tracked manga for new chapters."""
    from api.mangadex import MangaTracker, MangaDexClient

    tracked = MangaTracker.get_all_tracked()
    if not tracked:
        return

    for rec in tracked:
        rec_id, manga_id, manga_title, target_chat_id, lang, last_chapter, _ = rec
        try:
            chapter = MangaDexClient.get_latest_chapter(manga_id, lang)
            if not chapter:
                MangaTracker.update_last_chapter(rec_id, last_chapter or "")
                continue

            attrs = chapter.get("attributes", {}) or {}
            ch_num = attrs.get("chapter")
            ch_id = chapter.get("id", "")

            if not ch_num or str(ch_num) == str(last_chapter):
                continue

            # New chapter found!
            ch_info = MangaDexClient.format_chapter_info(chapter)
            pub_at = attrs.get("publishAt") or ""
            try:
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).strftime("%d %b %Y %H:%M")
            except Exception:
                pass

            text = (
                b("📚 New Chapter Released!") + "\n\n"
                f"<b>Manga:</b> {b(e(manga_title))}\n\n"
                + ch_info + "\n\n"
                + bq(b("Enjoy reading! 🎉"))
            )
            keyboard = [[
                InlineKeyboardButton(" Read Now", url=f"https://mangadex.org/chapter/{ch_id}"),
                InlineKeyboardButton(" Manga Page", url=f"https://mangadex.org/title/{manga_id}"),
            ]]

            if target_chat_id:
                await safe_send_message(
                    context.bot, target_chat_id, text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )

            MangaTracker.update_last_chapter(rec_id, ch_num)
            await asyncio.sleep(0.5)

        except Exception as exc:
            logger.debug(f"manga_update_job row {rec_id} error: {exc}")


# ── Expired links cleanup job ─────────────────────────────────────────────────

async def cleanup_expired_links_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: clean up expired deep links from database."""
    try:
        from database_dual import cleanup_expired_links
        cleanup_expired_links()
    except Exception as exc:
        logger.debug(f"cleanup_expired_links_job error: {exc}")


# ── Scheduled broadcasts job ──────────────────────────────────────────────────

async def check_scheduled_broadcasts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job: check for pending scheduled broadcasts and execute them."""
    try:
        from database_dual import db_manager, get_all_users
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT id, admin_id, message_text, media_file_id, media_type
                FROM scheduled_broadcasts
                WHERE status = 'pending' AND execute_at <= NOW()
                LIMIT 5
            """)
            rows = cur.fetchall() or []
    except Exception as exc:
        logger.debug(f"check_scheduled_broadcasts DB error: {exc}")
        return

    for row in rows:
        b_id, admin_id, text, media_file_id, media_type = row
        try:
            from database_dual import get_all_users
            users = get_all_users(limit=None, offset=0)
        except Exception:
            users = []
        sent = fail = 0
        for u in users:
            try:
                await context.bot.send_message(u[0], text, parse_mode="HTML")
                sent += 1
            except Exception:
                fail += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)

        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE scheduled_broadcasts SET status = 'sent' WHERE id = %s",
                    (b_id,)
                )
        except Exception:
            pass

        try:
            await context.bot.send_message(
                admin_id,
                b(f"✅ Scheduled broadcast #{b_id} done.") + "\n"
                + bq(f"<b>Sent:</b> {sent} | <b>Failed:</b> {fail}"),
                parse_mode="HTML",
            )
        except Exception:
            pass


# ── Panel cache prewarm loop ──────────────────────────────────────────────────

async def _prewarm_all_caches(bot) -> None:
    """
    Background loop: pre-build all panel data so first button tap is instant.
    Runs at startup and repeats every 45s.
    """
    from core.panel_store import prebuild_all_panels
    _PANEL_CACHE_TTL = 45

    while True:
        try:
            # Pre-build panel photo store
            try:
                await prebuild_all_panels(bot)
            except Exception as _pbe:
                logger.debug(f"[prewarm] prebuild: {_pbe}")

            # Self-ping to prevent Render free-tier spin-down
            try:
                import aiohttp
                import os
                _self_url = os.getenv("RENDER_EXTERNAL_URL", "")
                if not _self_url:
                    _port = os.getenv("PORT", "10000")
                    _self_url = f"http://localhost:{_port}"
                async with aiohttp.ClientSession() as _sess:
                    async with _sess.get(f"{_self_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as _r:
                        logger.debug(f"[keepalive] self-ping {_r.status}")
            except Exception as _kae:
                logger.debug(f"[keepalive] {_kae}")

            # Run all panel data fetches in parallel
            def _fetch_connected():
                try:
                    from database_dual import db_manager
                    with db_manager.get_cursor() as cur:
                        cur.execute("SELECT group_id FROM connected_groups WHERE active = TRUE")
                        return {r[0] for r in (cur.fetchall() or [])}
                except Exception:
                    return set()

            results = await asyncio.gather(
                asyncio.get_event_loop().run_in_executor(None, _safe_call, "get_user_count"),
                asyncio.get_event_loop().run_in_executor(None, _safe_call, "get_blocked_users_count"),
                asyncio.get_event_loop().run_in_executor(None, _safe_call, "get_all_force_sub_channels"),
                asyncio.get_event_loop().run_in_executor(None, _safe_call, "get_all_clone_bots"),
                asyncio.get_event_loop().run_in_executor(None, _safe_call_setting, "maintenance_mode", "false"),
                asyncio.get_event_loop().run_in_executor(None, _fetch_connected),
                return_exceptions=True,
            )
            user_count, blocked_count, channels, clones, maint, connected_ids = results

            panel_cache_set("user_count",       user_count       if isinstance(user_count, int)    else 0)
            panel_cache_set("blocked_count",    blocked_count    if isinstance(blocked_count, int) else 0)
            panel_cache_set("channels",         channels         if isinstance(channels, list)     else [])
            panel_cache_set("clones",           clones           if isinstance(clones, list)       else [])
            panel_cache_set("maint",            maint            if isinstance(maint, str)         else "false")
            panel_cache_set("connected_groups", connected_ids    if isinstance(connected_ids, set) else set())

            logger.debug("[prewarm] panel caches refreshed")
        except Exception as exc:
            logger.debug(f"[prewarm] error: {exc}")

        await asyncio.sleep(_PANEL_CACHE_TTL)


def _safe_call(fn_name: str) -> Any:
    """Safely call a database_dual function by name."""
    try:
        import database_dual
        fn = getattr(database_dual, fn_name, None)
        if fn:
            return fn()
    except Exception:
        pass
    return None


def _safe_call_setting(key: str, default: str) -> str:
    """Safely get a setting value."""
    try:
        from database_dual import get_setting
        return get_setting(key, default)
    except Exception:
        return default
