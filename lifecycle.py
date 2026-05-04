"""
lifecycle.py
============
Bot lifecycle hooks:
  - post_init: called after application starts
  - post_shutdown: cleanup on shutdown
  - _register_bot_commands_on_bot: set Telegram command menus
  - _send_restart_notification: DM admin on every start
"""
import asyncio
import json
import os
from typing import List

from telegram import Bot, BotCommand, BotCommandScopeChat, BotCommandScopeAllPrivateChats
from telegram.ext import Application

from core.config import ADMIN_ID, OWNER_ID, BOT_TOKEN, BOT_NAME, PANEL_DB_CHANNEL, FALLBACK_IMAGE_CHANNEL
from core.text_utils import e
from core.logging_setup import logger


async def post_init(application: Application) -> None:
    """Called after application starts — register commands and start services."""
    import core.config as cfg

    me = await application.bot.get_me()
    cfg.BOT_USERNAME = me.username or ""

    try:
        from database_dual import am_i_a_clone_token, set_main_bot_token
        cfg.I_AM_CLONE = am_i_a_clone_token(BOT_TOKEN)
        if not cfg.I_AM_CLONE:
            set_main_bot_token(BOT_TOKEN)
            logger.info("✅ Main bot token saved to DB")
    except Exception as exc:
        cfg.I_AM_CLONE = False
        logger.warning(f"Could not save main bot token: {exc}")

    logger.info(f"✅ Bot @{cfg.BOT_USERNAME} started as {'CLONE' if cfg.I_AM_CLONE else 'MAIN'}")

    # Register commands on this bot
    await _register_bot_commands_on_bot(application.bot)

    # Start and register all clone bots
    try:
        from database_dual import get_all_clone_bots
        from handlers.clones import launch_clone_bot
        clones = get_all_clone_bots(active_only=True)
        for _, token, uname, _, _ in clones:
            try:
                clone_bot = Bot(token=token)
                await _register_bot_commands_on_bot(clone_bot)
                logger.info(f"✅ Commands registered on clone @{uname}")
                launch_clone_bot(token, uname)
            except Exception as exc:
                logger.warning(f"Could not start clone @{uname}: {exc}")
    except Exception as exc:
        logger.warning(f"Could not iterate clones: {exc}")

    # Start health check server
    try:
        from health_check import health_server
        await health_server.start()
        logger.info("✅ Health check server started")
    except Exception as exc:
        logger.warning(f"Health server failed: {exc}")

    # Trigger panel image channel scan
    _scan_target = PANEL_DB_CHANNEL if PANEL_DB_CHANNEL else FALLBACK_IMAGE_CHANNEL
    if _scan_target:
        from core.panel_image import scan_panel_channel
        asyncio.create_task(scan_panel_channel(application.bot))
        logger.info(f"✅ Panel image scan scheduled from channel {_scan_target}")

    # Schedule background jobs
    if application.job_queue:
        from jobs.scheduled import (
            manga_update_job,
            cleanup_expired_links_job,
            check_scheduled_broadcasts,
            _prewarm_all_caches,
        )
        application.job_queue.run_repeating(manga_update_job,           interval=3600, first=180)
        application.job_queue.run_repeating(cleanup_expired_links_job,  interval=600,  first=90)
        application.job_queue.run_repeating(check_scheduled_broadcasts, interval=60,   first=180)
        logger.info("✅ Background jobs scheduled")

    # Migrate poster_cache table
    try:
        from filter_poster import migrate_poster_cache_table
        migrate_poster_cache_table()
        logger.info("✅ poster_cache table ready")
    except Exception as _e:
        logger.warning(f"poster_cache migration: {_e}")

    # Migrate search analytics table
    try:
        from database_dual import ensure_search_analytics_table
        ensure_search_analytics_table()
        logger.info("✅ search_analytics table ready")
    except Exception as _e:
        logger.warning(f"search_analytics migration: {_e}")

    # Start panel prewarm loop
    asyncio.create_task(_prewarm_all_caches(application.bot))

    # Apply DB migrations
    _migration_sqls = [
        """CREATE TABLE IF NOT EXISTS manga_auto_updates (
            id SERIAL PRIMARY KEY,
            manga_id TEXT NOT NULL DEFAULT '',
            manga_title TEXT NOT NULL DEFAULT '',
            target_chat_id BIGINT,
            notify_language TEXT DEFAULT 'en',
            last_chapter TEXT,
            interval_minutes INTEGER DEFAULT 60,
            mode TEXT DEFAULT 'latest',
            watermark BOOLEAN DEFAULT FALSE,
            active BOOLEAN DEFAULT TRUE,
            last_checked TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )""",
        "ALTER TABLE bot_progress ADD COLUMN IF NOT EXISTS anime_name TEXT DEFAULT 'Anime Name'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS notify_language TEXT DEFAULT 'en'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS interval_minutes INTEGER DEFAULT 60",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'latest'",
        "ALTER TABLE manga_auto_updates ADD COLUMN IF NOT EXISTS watermark BOOLEAN DEFAULT FALSE",
        "INSERT INTO bot_settings (key, value) VALUES ('loading_sticker_id', ''), ('loading_anim_enabled', 'true') ON CONFLICT (key) DO NOTHING",
        "INSERT INTO bot_settings (key, value) VALUES ('watermark_sticker_id', ''), ('watermark_image_id', '') ON CONFLICT (key) DO NOTHING",
    ]
    try:
        from database_dual import db_manager
        for _sql in _migration_sqls:
            try:
                with db_manager.get_cursor() as _cur:
                    _cur.execute(_sql)
            except Exception as _me:
                logger.debug(f"DB migration (non-fatal): {str(_me)[:80]}")
        try:
            with db_manager.get_cursor() as _cur:
                _cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_manga_track_unique ON manga_auto_updates(manga_id, target_chat_id)")
        except Exception:
            pass
    except Exception as exc:
        logger.debug(f"DB migrations: {exc}")
    logger.info("✅ DB migrations applied")

    # Initialize bot commands per authority level
    from bot_commands_setup import initialize_bot_commands
    await initialize_bot_commands(application.bot)

    # Send restart notification
    await _send_restart_notification(application.bot)


async def post_shutdown(application: Application) -> None:
    """Cleanup on bot shutdown."""
    try:
        from health_check import health_server
        await health_server.stop()
    except Exception:
        pass
    try:
        from database_dual import db_manager
        if db_manager:
            db_manager.close_all()
    except Exception:
        pass
    logger.info("✅ Shutdown complete.")


async def _register_bot_commands_on_bot(bot: Bot) -> None:
    """Register Telegram's /command menu for different authority levels."""
    user_commands = [
        BotCommand("start",     "Main menu"),
        BotCommand("help",      "Help & channels"),
        BotCommand("cmd",       "All available commands"),
        BotCommand("alive",     "Is bot online?"),
        BotCommand("anime",     "Anime poster & info"),
        BotCommand("manga",     "Manga poster & info"),
        BotCommand("movie",     "Movie poster & info"),
        BotCommand("my_plan",   "My daily poster limit"),
        BotCommand("aq",        "Random anime quote"),
        BotCommand("truth",     "Truth question"),
        BotCommand("dare",      "Dare challenge"),
        BotCommand("hug",       "Hug someone (reply)"),
        BotCommand("slap",      "Slap someone (reply)"),
        BotCommand("afk",       "Set AFK status"),
        BotCommand("rules",     "View group rules"),
        BotCommand("warns",     "My warn count"),
        BotCommand("wiki",      "Wikipedia search"),
        BotCommand("tr",        "Translate text (reply)"),
        BotCommand("ping",      "Bot speed check"),
        BotCommand("id",        "Get user/chat ID"),
    ]
    group_admin_commands = [
        BotCommand("cmd",          "All commands by authority"),
        BotCommand("ban",          "Ban a user"),
        BotCommand("kick",         "Kick a user"),
        BotCommand("mute",         "Mute a user"),
        BotCommand("warn",         "Warn a user"),
        BotCommand("pin",          "Pin a message"),
        BotCommand("purge",        "Delete messages"),
        BotCommand("promote",      "Promote to admin"),
        BotCommand("filter",       "Add custom filter"),
        BotCommand("filters",      "List filters"),
        BotCommand("lock",         "Lock message type"),
        BotCommand("setrules",     "Set group rules"),
        BotCommand("save",         "Save a note"),
        BotCommand("notes",        "List all notes"),
        BotCommand("welcome",      "Toggle welcome message"),
        BotCommand("setwelcome",   "Set welcome message"),
        BotCommand("setflood",     "Set flood limit"),
        BotCommand("approve",      "Approve a user"),
        BotCommand("addblacklist", "Blacklist a word"),
        BotCommand("chatbot",      "Toggle AI chatbot"),
        BotCommand("tagall",       "Mention all members"),
    ]
    bot_admin_commands = [
        BotCommand("cmd",          "All commands by authority"),
        BotCommand("stats",        "Bot statistics"),
        BotCommand("sysstats",     "Server stats"),
        BotCommand("users",        "User database"),
        BotCommand("upload",       "Upload manager"),
        BotCommand("settings",     "Category settings"),
        BotCommand("autoupdate",   "Manga tracker"),
        BotCommand("autoforward",  "Auto-forward manager"),
        BotCommand("broadcast",    "Send broadcast"),
        BotCommand("addchannel",   "Add force-sub channel"),
        BotCommand("banuser",      "Ban from bot"),
        BotCommand("add_premium",  "Give premium plan"),
        BotCommand("addclone",     "Add clone bot"),
        BotCommand("reload",       "Restart bot"),
        BotCommand("logs",         "View logs"),
        BotCommand("gban",         "Global ban"),
        BotCommand("backup",       "Links backup"),
        BotCommand("exportusers",  "Export CSV"),
        BotCommand("listusers",    "Browse users"),
    ]

    try:
        await bot.set_my_commands(user_commands)
        logger.info(f"✅ User commands menu registered ({len(user_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (users) failed: {exc}")

    try:
        from telegram import BotCommandScopeAllChatAdministrators
        await bot.set_my_commands(
            group_admin_commands,
            scope=BotCommandScopeAllChatAdministrators(),
        )
        logger.info(f"✅ Group admin commands menu registered ({len(group_admin_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (group admins) failed: {exc}")

    try:
        await bot.set_my_commands(
            bot_admin_commands,
            scope=BotCommandScopeChat(chat_id=ADMIN_ID),
        )
        if OWNER_ID and OWNER_ID != ADMIN_ID:
            await bot.set_my_commands(
                bot_admin_commands,
                scope=BotCommandScopeChat(chat_id=OWNER_ID),
            )
        logger.info(f"✅ Bot admin commands menu registered ({len(bot_admin_commands)} cmds)")
    except Exception as exc:
        logger.warning(f"Command menu (bot admin) failed: {exc}")


async def _send_restart_notification(bot: Bot) -> None:
    """Send restart notification to admin on every start."""
    triggered_by = ""
    try:
        import core.config as cfg
        triggered_by = cfg.BOT_USERNAME
    except Exception:
        pass
    try:
        if os.path.exists("restart_message.json"):
            with open("restart_message.json") as f:
                rinfo = json.load(f)
            triggered_by = rinfo.get("triggered_by", triggered_by)
            try:
                os.remove("restart_message.json")
            except Exception:
                pass
    except Exception:
        pass

    text = f"<blockquote><b>Bᴏᴛ Rᴇsᴛᴀʀᴛᴇᴅ by @{e(triggered_by)}</b></blockquote>"
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    except Exception as exc:
        logger.warning(f"Could not send restart notification: {exc}")
