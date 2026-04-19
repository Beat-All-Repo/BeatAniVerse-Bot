#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot.py — Entry point for BeatAnimeVerse Bot
============================================
This file is intentionally slim (~200 lines).
All logic lives in the appropriate modules under:
  core/         — Config, utilities, helpers, state, filters
  api/          — AniList, TMDB, MangaDex clients
  handlers/     — Command & callback handlers
  jobs/         — Background scheduled jobs
  lifecycle.py  — post_init / post_shutdown hooks

To run:  python bot.py
"""

import os
import sys
import asyncio
import logging

# ── Setup logging first ───────────────────────────────────────────────────────
from core.logging_setup import setup_logging, logger
setup_logging()

# ── Imports ───────────────────────────────────────────────────────────────────
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    InlineQueryHandler,
    ChatJoinRequestHandler,
    filters,
)

from core.config import (
    BOT_TOKEN, DATABASE_URL, MONGO_DB_URI,
    ADMIN_ID, OWNER_ID,
)
from lifecycle import post_init, post_shutdown

# ── Verify environment ────────────────────────────────────────────────────────
if not BOT_TOKEN or BOT_TOKEN in ("YOUR_TOKEN_HERE", ""):
    logger.error("❌ BOT_TOKEN is not set!")
    sys.exit(1)
if not DATABASE_URL and not MONGO_DB_URI:
    logger.error("❌ Neither DATABASE_URL (NeonDB) nor MONGO_DB_URI (MongoDB) is set!")
    sys.exit(1)
if not ADMIN_ID and not OWNER_ID:
    logger.error("❌ Neither ADMIN_ID nor OWNER_ID is set!")
    sys.exit(1)

# ── Compatibility shim (loads BeatVerse module stubs) ─────────────────────────
import beataniversebot_compat as _compat


def _register_all_handlers(app: Application) -> None:
    """Register every bot handler on the given Application instance."""
    # Import handlers
    from handlers.start import start, delete_update_message
    from handlers.help import (
        help_command, ping_command,
        id_command, info_command, cmd_command,
    )
    from handlers.admin_panel import send_admin_menu
    from handlers.post_gen import generate_and_send_post

    admin_filter = filters.User(user_id=ADMIN_ID) | filters.User(user_id=OWNER_ID)

    # ── Core commands ─────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("help",    help_command))
    app.add_handler(CommandHandler("test",    lambda u, c: None))  # keep-alive
    app.add_handler(CommandHandler("cmd",     cmd_command))
    app.add_handler(CommandHandler("commands",cmd_command))
    app.add_handler(CommandHandler("id",      id_command))
    app.add_handler(CommandHandler("info",    info_command))
    app.add_handler(CommandHandler("ping",    ping_command))
    

    # ── Media content commands ────────────────────────────────────────────────
    from handlers.media_cmds import (
        anime_command, manga_command, movie_command,
        tvshow_command, search_command,
    )
    app.add_handler(CommandHandler("anime",   anime_command))
    app.add_handler(CommandHandler("manga",   manga_command))
    app.add_handler(CommandHandler("movie",   movie_command))
    app.add_handler(CommandHandler("tvshow",  tvshow_command))
    app.add_handler(CommandHandler("search",  search_command))

    # ── Anime extras ──────────────────────────────────────────────────────────
    try:
        from modules.anime import airing_cmd, character_cmd
        app.add_handler(CommandHandler("airing",    airing_cmd))
        app.add_handler(CommandHandler("character", character_cmd))
        logger.info("[anime] /airing and /character registered")
    except Exception as _anime_err:
        logger.warning(f"anime extras: {_anime_err}")

    # ── Admin-only commands ───────────────────────────────────────────────────
    from handlers.misc_cmds import (
        stats_command, sysstats_command, users_command,
        settings_command, upload_command, autoupdate_command,
        autoforward_command, add_channel_command, remove_channel_command,
        channel_command, ban_user_command, unban_user_command,
        listusers_command, deleteuser_command, exportusers_command,
        broadcaststats_command, backup_command, addclone_command,
        clones_command, reload_command, logs_command,
        connect_command, disconnect_command, connections_command,
        set_loader_cmd, addpanelimg_command, getfileid_command,
    )
    app.add_handler(CommandHandler("stats",          stats_command,          filters=admin_filter))
    app.add_handler(CommandHandler("sysstats",       sysstats_command,       filters=admin_filter))
    app.add_handler(CommandHandler("users",          users_command,          filters=admin_filter))
    app.add_handler(CommandHandler("settings",       settings_command,       filters=admin_filter))
    app.add_handler(CommandHandler("upload",         upload_command,         filters=admin_filter))
    app.add_handler(CommandHandler("autoupdate",     autoupdate_command,     filters=admin_filter))
    app.add_handler(CommandHandler("autoforward",    autoforward_command,    filters=admin_filter))
    app.add_handler(CommandHandler("addchannel",     add_channel_command,    filters=admin_filter))
    app.add_handler(CommandHandler("removechannel",  remove_channel_command, filters=admin_filter))
    app.add_handler(CommandHandler("channel",        channel_command,        filters=admin_filter))
    app.add_handler(CommandHandler("banuser",        ban_user_command,       filters=admin_filter))
    app.add_handler(CommandHandler("unbanuser",      unban_user_command,     filters=admin_filter))
    app.add_handler(CommandHandler("listusers",      listusers_command,      filters=admin_filter))
    app.add_handler(CommandHandler("deleteuser",     deleteuser_command,     filters=admin_filter))
    app.add_handler(CommandHandler("exportusers",    exportusers_command,    filters=admin_filter))
    app.add_handler(CommandHandler("broadcaststats", broadcaststats_command, filters=admin_filter))
    app.add_handler(CommandHandler("backup",         backup_command,         filters=admin_filter))
    app.add_handler(CommandHandler("addclone",       addclone_command,       filters=admin_filter))
    app.add_handler(CommandHandler("clones",         clones_command,         filters=admin_filter))
    app.add_handler(CommandHandler(["reload", "restart"], reload_command,    filters=admin_filter))
    app.add_handler(CommandHandler("logs",           logs_command,           filters=admin_filter))
    app.add_handler(CommandHandler("connect",        connect_command,        filters=admin_filter))
    app.add_handler(CommandHandler("disconnect",     disconnect_command,     filters=admin_filter))
    app.add_handler(CommandHandler("connections",    connections_command,    filters=admin_filter))
    app.add_handler(CommandHandler("set_loader",     set_loader_cmd,         filters=admin_filter))
    app.add_handler(CommandHandler("addpanelimg",    addpanelimg_command))
    app.add_handler(CommandHandler("getfileid",      getfileid_command))

    # ── Poster template commands (admin only) ─────────────────────────────────
    try:
        from poster_engine import (
            poster_ani, poster_anim, poster_crun, poster_net, poster_netm,
            poster_light, poster_lightm, poster_dark, poster_darkm,
            poster_netcr, poster_mod, poster_modm,
            cmd_my_plan, cmd_plans, cmd_add_premium,
            cmd_remove_premium, cmd_premium_list,
        )
        for _cmd, _fn in [
            ("ani", poster_ani), ("anim", poster_anim), ("crun", poster_crun),
            ("net", poster_net), ("netm", poster_netm), ("light", poster_light),
            ("lightm", poster_lightm), ("dark", poster_dark), ("darkm", poster_darkm),
            ("netcr", poster_netcr), ("mod", poster_mod), ("modm", poster_modm),
        ]:
            app.add_handler(CommandHandler(_cmd, _fn, filters=admin_filter))
        app.add_handler(CommandHandler("add_premium",    cmd_add_premium,    filters=admin_filter))
        app.add_handler(CommandHandler("remove_premium", cmd_remove_premium, filters=admin_filter))
        app.add_handler(CommandHandler("premium_list",   cmd_premium_list,   filters=admin_filter))
        app.add_handler(CommandHandler("my_plan",  cmd_my_plan))
        app.add_handler(CommandHandler("plans",    cmd_plans))
        logger.info("[poster] Poster commands registered")
    except Exception as _pe:
        logger.warning(f"[poster] Failed to load poster commands: {_pe}")

    # ── User feature commands ─────────────────────────────────────────────────
    from handlers.user_features import (
        user_reaction_cmd, couple_cmd, afk_cmd, afk_check_handler,
        note_save_cmd, note_get_cmd, notes_list_cmd, note_trigger_handler,
        warn_cmd, unwarn_cmd, warns_cmd, resetwarns_cmd,
        rules_cmd, setrules_cmd, chatbot_private_handler, chatbot_group_handler,
    )
    for _rc in ("slap", "hug", "kiss", "pat", "punch", "poke", "wave",
                "bite", "wink", "cry", "laugh", "blush", "nod", "shoot"):
        app.add_handler(CommandHandler(_rc, user_reaction_cmd))
    app.add_handler(CommandHandler("couple",     couple_cmd))
    app.add_handler(CommandHandler("afk",        afk_cmd))
    app.add_handler(CommandHandler("notes",      notes_list_cmd))
    app.add_handler(CommandHandler("save",       note_save_cmd))
    app.add_handler(CommandHandler("get",        note_get_cmd))
    app.add_handler(CommandHandler("rules",      rules_cmd))
    app.add_handler(CommandHandler("setrules",   setrules_cmd, filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("warns",      warns_cmd))
    app.add_handler(CommandHandler("warn",       warn_cmd,       filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("unwarn",     unwarn_cmd,     filters=filters.ChatType.GROUPS))
    app.add_handler(CommandHandler("resetwarns", resetwarns_cmd, filters=filters.ChatType.GROUPS))

    # Note triggers — #notename
    app.add_handler(MessageHandler(
        filters.Regex(r'^#[\w]+') & ~filters.COMMAND, note_trigger_handler
    ))
    # AFK auto-reply
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, afk_check_handler), group=5)
    # Chatbot
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        chatbot_private_handler
    ), group=6)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS
        & filters.Regex(r'(?i)^(hey|hi|hello|bot|@)'),
        chatbot_group_handler
    ), group=7)

    # ── Module commands (bridge) ──────────────────────────────────────────────
    def _M(module_name):
        """Stub handler — module commands handled by the dispatcher bridge."""
        async def _handler(update, context):
            pass
        _handler.__name__ = f"mod_{module_name}_cmd"
        return _handler

    _G = filters.ChatType.GROUPS

    # Group management
    from handlers.group_mgmt import (
        pin_cmd, unpin_cmd, del_cmd, promote_cmd, demote_cmd,
        mute_cmd, unmute_cmd, ban_cmd, unban_cmd, kick_cmd, invitelink_cmd,
    )
    for _cmd_name, _cmd_fn in [
        ("pin", pin_cmd), ("unpin", unpin_cmd), ("del", del_cmd),
        ("promote", promote_cmd), ("demote", demote_cmd),
        ("mute", mute_cmd), ("unmute", unmute_cmd),
        ("ban", ban_cmd), ("unban", unban_cmd), ("kick", kick_cmd),
        ("invitelink", invitelink_cmd),
    ]:
        app.add_handler(CommandHandler(_cmd_name, _cmd_fn, filters=_G))

    # Welcome system
    for _wc in ("welcome", "goodbye", "setwelcome", "setgoodbye",
                "resetwelcome", "resetgoodbye", "welcomemute",
                "cleanservice", "cleanwelcome"):
        app.add_handler(CommandHandler(_wc, _M("welcome"), filters=_G))
    app.add_handler(CommandHandler("welcomehelp",     _M("welcome")))
    app.add_handler(CommandHandler("welcomemutehelp", _M("welcome")))

    # Misc module commands
    app.add_handler(CommandHandler(["aq", "animequote"], _M("animequotes")))
    app.add_handler(CommandHandler(["truth", "dare"],    _M("truth_and_dare")))
    app.add_handler(CommandHandler("wiki",               _M("wiki")))
    app.add_handler(CommandHandler("ud",                 _M("ud")))
    app.add_handler(CommandHandler(["tr", "tl"],         _M("translator")))
    app.add_handler(CommandHandler("time",               _M("gettime")))
    app.add_handler(CommandHandler("write",              _M("writetool")))
    app.add_handler(CommandHandler("imdb",               _M("imdb")))
    app.add_handler(CommandHandler(["stickerid", "getsticker", "kang"], _M("stickers")))
    app.add_handler(CommandHandler("cash",               _M("currency_converter")))
    app.add_handler(CommandHandler("speedtest",          _M("speed_test")))
    app.add_handler(CommandHandler(["gban", "ungban"],   _M("global_bans")))
    app.add_handler(CommandHandler("addsudo",            _M("disasters")))
    app.add_handler(CommandHandler(["sh", "shell"],      _M("shell")))
    app.add_handler(CommandHandler("dbcleanup",          _M("dbcleanup")))
    app.add_handler(CommandHandler(["eval", "exec"],     _M("eval")))
    app.add_handler(CommandHandler(["filter", "stop", "filters"], _M("cust_filters"), filters=_G))
    app.add_handler(CommandHandler(["lock", "unlock", "locks"],   _M("locks"),        filters=_G))
    app.add_handler(CommandHandler(["setflood", "flood"],         _M("antiflood"),    filters=_G))
    app.add_handler(CommandHandler(["approve", "unapprove"],      _M("approve"),      filters=_G))
    app.add_handler(CommandHandler(["addblacklist", "blacklist"],  _M("blacklist"),    filters=_G))
    app.add_handler(CommandHandler("purge",                        _M("purge"),        filters=_G))
    app.add_handler(CommandHandler("tagall",                       _M("tagall"),       filters=_G))
    app.add_handler(CommandHandler(["setlog", "unsetlog"],         _M("log_channel"),  filters=_G))
    app.add_handler(CommandHandler("chatbot",                      _M("chatbot"),      filters=_G))
    app.add_handler(CommandHandler("wall",                         _M("wallpaper")))
    app.add_handler(CommandHandler(["request", "requests", "myrequests", "fulfill"], _M("animerequest")))

    # Badwords register hook
    try:
        from modules.badwords import register as _bw_register
        _bw_register(app)
        logger.info("[badwords] registered")
    except Exception as _e:
        logger.warning(f"badwords: {_e}")

    # ── Callback query router ─────────────────────────────────────────────────
    from handlers.button_router import button_handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # ── Message handlers ──────────────────────────────────────────────────────
    from handlers.admin_input import handle_admin_message
    from handlers.group import group_message_handler
    from handlers.upload import handle_upload_video, handle_channel_post
    from handlers.admin_photo import handle_admin_photo
    from handlers.channels import auto_approve_join_request, channel_welcome_join_handler
    from handlers.autoforward import auto_forward_message_handler
    from handlers.clean_gc import _clean_gc_service_handler, _clean_gc_command_handler

    # NEW: Import the group filter poster handler
    from filter_poster import get_or_generate_poster

    app.add_handler(MessageHandler(
        admin_filter & ~filters.COMMAND, handle_admin_message
    ))

    # General group text handler (notes, afk, etc.)
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
        group_message_handler,
    ), group=10)

    # Group caption handler
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.CAPTION & ~filters.COMMAND,
        group_message_handler,
    ), group=10)

    # ←←← FILTER POSTER — works in groups AND DMs ←←←
    # Group=15 so it runs after notes/afk (group=10) but before lower priority
    app.add_handler(
        MessageHandler(
            (filters.ChatType.GROUPS | filters.ChatType.PRIVATE)
            & filters.TEXT & ~filters.COMMAND,
            get_or_generate_poster
        ),
        group=15
    )

    # Inline query
    from handlers.inline_handler import inline_query_handler
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # Channel handlers
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL, auto_forward_message_handler))
    app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.VIDEO, handle_channel_post))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.VIDEO & admin_filter, handle_upload_video
    ))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE
        & (filters.PHOTO | filters.Document.IMAGE | filters.Sticker.ALL)
        & admin_filter,
        handle_admin_photo,
    ))

    # Join requests
    app.add_handler(ChatJoinRequestHandler(auto_approve_join_request))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS, channel_welcome_join_handler
    ))

    # Clean GC
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.StatusUpdate.ALL,
        _clean_gc_service_handler,
    ), group=-1)
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.COMMAND,
        _clean_gc_command_handler,
    ), group=10)

    # Error handler
    from handlers.error_handler import error_handler
    app.add_error_handler(error_handler)

    # Command refresh
    from bot_commands_setup import register_command_setup_handlers
    register_command_setup_handlers(app)

    logger.info("✅ All handlers registered")


def main() -> None:
    """Bot entry point — set up and start polling."""
    # Mirror ADMIN/OWNER if only one is set
    import core.config as cfg
    if cfg.ADMIN_ID == 0 and cfg.OWNER_ID != 0:
        cfg.ADMIN_ID = cfg.OWNER_ID
    if cfg.OWNER_ID == 0 and cfg.ADMIN_ID != 0:
        cfg.OWNER_ID = cfg.ADMIN_ID

    # Initialize database
    try:
        from database_dual import init_db
        init_db(DATABASE_URL, MONGO_DB_URI)
        logger.info("✅ Database initialized")
    except Exception as exc:
        logger.error(f"❌ Database init failed: {exc}")
        return

    # Test DB
    try:
        from database_dual import get_user_count
        count = get_user_count()
        logger.info(f"✅ Database working — {count} users registered")
    except Exception as exc:
        logger.error(f"❌ Database test failed: {exc}")
        return

    # Wire compat shim
    _compat._set_bot_info(0, cfg.BOT_NAME, "")

    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    # Wire module dispatcher bridge
    class _AppDispatcherBridge:
        def __init__(self, app):
            self._app = app
            self._count = 0

        def add_handler(self, handler, group=50, *args, **kwargs):
            try:
                import functools
                orig_cb = getattr(handler, "callback", None)
                if orig_cb is not None and not asyncio.iscoroutinefunction(orig_cb):
                    @functools.wraps(orig_cb)
                    async def _async_wrapper(update, context, _cb=orig_cb):
                        try:
                            result = _cb(update, context)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as exc:
                            logger.debug(f"[bridge] {getattr(_cb, '__name__', '?')}: {exc}")
                    handler.callback = _async_wrapper
                self._app.add_handler(handler, group=50)
                self._count += 1
            except Exception as exc:
                logger.debug(f"[bridge] add_handler failed: {exc}")

        def add_error_handler(self, *args, **kwargs):
            try:
                self._app.add_error_handler(*args, **kwargs)
            except Exception:
                pass

        @property
        def bot(self):
            return self._app.bot

    _bridge = _AppDispatcherBridge(application)
    _compat._set_dispatcher(_bridge)
    logger.info("[bridge] Module dispatcher wired to PTB v21 Application (group=50)")

    # Load BeatVerse modules
    try:
        import importlib
        import glob
        _mod_dir = os.path.join(os.path.dirname(__file__), "modules")
        _skip = {"__init__", "sql", "helper_funcs"}
        _no_load = set(os.getenv("NO_LOAD", "tagall telegraph backups country").split())
        _loaded = []
        for _f in sorted(glob.glob(os.path.join(_mod_dir, "*.py"))):
            _mn = os.path.basename(_f)[:-3]
            if _mn.startswith("__") or _mn in _skip or _mn in _no_load:
                continue
            try:
                importlib.import_module(f"modules.{_mn}")
                _loaded.append(_mn)
            except Exception as _exc:
                logger.warning(f"Module {_mn} failed to load: {_exc}")
        logger.info(f"✅ Loaded {len(_loaded)} BeatVerse modules")
    except Exception as _exc:
        logger.warning(f"Module loading error: {_exc}")

    # Register all handlers
    _register_all_handlers(application)

    # Set lifecycle hooks
    application.post_init = post_init
    application.post_shutdown = post_shutdown

    logger.info("🚀 Starting bot polling…")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
