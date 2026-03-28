# Don't Remove Credit @BeatAnime
# Ask Doubt on telegram @Beat_Anime_Discussion
#
# Copyright (C) 2025 by BeatAnime | @BeatAnime | @Beat_Anime_Discussion
# This file is part of BeatAniVerse Bot project.
# Released under the MIT License.
# All rights reserved.

"""
BeatAniVerse Bot — Command Setup Module
=========================================
Automatically sets bot commands per authority level:
  • USER     — public enjoyment commands only (no features revealed)
  • ADMIN    — all admin + management commands
  • OWNER    — every command including dev/sudo tools

Mirrors the authority-level pattern from bot_commands_setup.py.

How to use:
  1. Drop this file in your BeatAniVerse-v2/ directory.
  2. In bot.py post_init, call:
         from bot_commands_setup import initialize_bot_commands
         await initialize_bot_commands(application.bot)
  3. Done — commands auto-set on every restart.
"""

import os
import logging
from typing import Optional

from telegram import (
    Bot,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# ── Authority IDs (read at module load — same env vars as bot.py) ─────────────
OWNER_ID: int = int(os.getenv("OWNER_ID", "0") or "0")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0") or os.getenv("OWNER_ID", "0"))

# ── DRAGONS / sudo users — same list as bot.py ────────────────────────────────
def _get_dragons() -> list:
    try:
        raw = os.getenv("DRAGONS", "")
        return [int(x.strip()) for x in raw.split() if x.strip().isdigit()]
    except Exception:
        return []


# ════════════════════════════════════════════════════════════════════════════════
#  COMMAND LISTS — 3 authority tiers
# ════════════════════════════════════════════════════════════════════════════════

# ── TIER 1: USER — only fun/info commands, NO features revealed ───────────────
USER_COMMANDS = [
    BotCommand("start",   "Start the bot"),
    BotCommand("help",    "Get help and support"),
    BotCommand("ping",    "Check bot response time"),
    BotCommand("alive",   "Check if bot is online"),
    BotCommand("id",      "Get your user / chat ID"),
    BotCommand("info",    "Get user information"),
    BotCommand("my_plan", "Check your poster plan"),
    BotCommand("plans",   "View available poster plans"),
]

# ── TIER 2: ADMIN — all management, content, link provider commands ───────────
ADMIN_COMMANDS = USER_COMMANDS + [
    # ── Content generation ──────────────────────────────────────────────────
    BotCommand("anime",   "Generate anime post (AniList)"),
    BotCommand("manga",   "Generate manga post"),
    BotCommand("movie",   "Generate movie post (TMDB)"),
    BotCommand("tvshow",  "Generate TV show post"),
    BotCommand("search",  "Search anime / manga / movies"),
    # ── Poster templates ────────────────────────────────────────────────────
    BotCommand("ani",     "AniList anime poster"),
    BotCommand("anim",    "AniList manga poster"),
    BotCommand("crun",    "Crunchyroll poster"),
    BotCommand("net",     "Netflix anime poster"),
    BotCommand("netm",    "Netflix manga poster"),
    BotCommand("dark",    "Dark anime poster"),
    BotCommand("darkm",   "Dark manga poster"),
    BotCommand("light",   "Light anime poster"),
    BotCommand("lightm",  "Light manga poster"),
    BotCommand("mod",     "Modern anime poster"),
    BotCommand("modm",    "Modern manga poster"),
    BotCommand("netcr",   "Netflix x Crunchyroll poster"),
    # ── Link provider ───────────────────────────────────────────────────────
    BotCommand("addchannel",    "Add force-sub channel (ID or @username)"),
    BotCommand("removechannel", "Remove force-sub channel"),
    BotCommand("channel",       "List force-sub channels"),
    BotCommand("addclone",      "Add a clone bot"),
    BotCommand("clones",        "List active clone bots"),
    # ── User management ─────────────────────────────────────────────────────
    BotCommand("stats",         "Bot statistics"),
    BotCommand("sysstats",      "Server system stats"),
    BotCommand("users",         "User count"),
    BotCommand("banuser",       "Ban a user"),
    BotCommand("unbanuser",     "Unban a user"),
    BotCommand("listusers",     "List all users"),
    BotCommand("exportusers",   "Export users as CSV"),
    # ── Broadcast ───────────────────────────────────────────────────────────
    BotCommand("broadcaststats", "Broadcast history"),
    # ── Upload & forward ────────────────────────────────────────────────────
    BotCommand("upload",       "Open upload manager"),
    BotCommand("autoforward",  "Auto-forward manager"),
    BotCommand("autoupdate",   "Manga chapter auto-update"),
    # ── Settings ────────────────────────────────────────────────────────────
    BotCommand("settings",     "Category settings panel"),
    BotCommand("connect",      "Connect a group"),
    BotCommand("disconnect",   "Disconnect a group"),
    BotCommand("connections",  "List connected groups"),
    BotCommand("cmd",          "Full admin command list"),
    BotCommand("logs",         "View recent bot logs"),
    BotCommand("backup",       "List generated links"),
    BotCommand("reload",       "Restart / reload the bot"),
    # ── Premium ─────────────────────────────────────────────────────────────
    BotCommand("add_premium",    "Grant premium to user"),
    BotCommand("remove_premium", "Revoke premium from user"),
    BotCommand("premium_list",   "List all premium users"),
]

# ── TIER 3: OWNER — everything above + dev / sudo-only tools ─────────────────
OWNER_COMMANDS = ADMIN_COMMANDS + [
    BotCommand("gban",          "Global ban a user"),
    BotCommand("ungban",        "Global unban a user"),
    BotCommand("gbanlist",      "List globally banned users"),
    BotCommand("devping",       "Developer-level ping with full stats"),
    BotCommand("eval",          "Evaluate Python code"),
    BotCommand("sh",            "Run shell command"),
    BotCommand("deleteuser",    "Delete user from database"),
    BotCommand("restart",       "Force restart bot"),
    BotCommand("refresh_commands",     "Refresh your command menu"),
    BotCommand("refresh_all_commands", "Refresh commands for all admins"),
    BotCommand("set_bot_description",  "Update bot profile description"),
]


# ════════════════════════════════════════════════════════════════════════════════
#  AUTHORITY CHECK
# ════════════════════════════════════════════════════════════════════════════════

def _is_owner(user_id: int) -> bool:
    return user_id in (OWNER_ID, ADMIN_ID)


def _is_admin(user_id: int) -> bool:
    """Admin = owner + DRAGONS list + any user flagged as admin in DB."""
    if _is_owner(user_id):
        return True
    if user_id in _get_dragons():
        return True
    # DB check — graceful fallback if DB unavailable
    try:
        from database_dual import _pg_exec
        row = _pg_exec(
            "SELECT 1 FROM users WHERE user_id = %s AND is_banned = FALSE",
            (user_id,)
        )
        # Additional admin table if exists
        row2 = _pg_exec(
            "SELECT 1 FROM bot_settings WHERE key = %s",
            (f"admin_{user_id}",)
        )
        return bool(row2)
    except Exception:
        return False


# ════════════════════════════════════════════════════════════════════════════════
#  CORE: SET COMMANDS FOR A SINGLE USER
# ════════════════════════════════════════════════════════════════════════════════

async def set_bot_commands_for_user(bot: Bot, user_id: int) -> bool:
    """
    Set bot commands for a specific user based on their authority level.
    
    Tier 1 (user)  → USER_COMMANDS     (fun/info only)
    Tier 2 (admin) → ADMIN_COMMANDS    (management + content)
    Tier 3 (owner) → OWNER_COMMANDS    (everything)
    """
    try:
        if _is_owner(user_id):
            await bot.set_my_commands(
                commands=OWNER_COMMANDS,
                scope=BotCommandScopeChat(chat_id=user_id),
            )
            logger.info(f"[CMD_SETUP] OWNER commands set for {user_id}")
        elif _is_admin(user_id):
            await bot.set_my_commands(
                commands=ADMIN_COMMANDS,
                scope=BotCommandScopeChat(chat_id=user_id),
            )
            logger.info(f"[CMD_SETUP] ADMIN commands set for {user_id}")
        else:
            await bot.set_my_commands(
                commands=USER_COMMANDS,
                scope=BotCommandScopeChat(chat_id=user_id),
            )
            logger.info(f"[CMD_SETUP] USER commands set for {user_id}")
        return True
    except TelegramError as exc:
        logger.warning(f"[CMD_SETUP] TelegramError for {user_id}: {exc}")
    except Exception as exc:
        logger.warning(f"[CMD_SETUP] Error setting commands for {user_id}: {exc}")
    return False


# ════════════════════════════════════════════════════════════════════════════════
#  SET DEFAULT (global scope — users who haven't started yet)
# ════════════════════════════════════════════════════════════════════════════════

async def set_default_bot_commands(bot: Bot) -> bool:
    """Set USER_COMMANDS as the global default (visible to everyone)."""
    try:
        await bot.set_my_commands(
            commands=USER_COMMANDS,
            scope=BotCommandScopeDefault(),
        )
        # Also set for all private chats
        await bot.set_my_commands(
            commands=USER_COMMANDS,
            scope=BotCommandScopeAllPrivateChats(),
        )
        logger.info("[CMD_SETUP] Default USER commands set globally")
        return True
    except Exception as exc:
        logger.warning(f"[CMD_SETUP] Error setting default commands: {exc}")
        return False


# ════════════════════════════════════════════════════════════════════════════════
#  SET BOT PROFILE DESCRIPTION
# ════════════════════════════════════════════════════════════════════════════════

async def set_bot_description_and_help(bot: Bot) -> None:
    """Set bot profile short description and full description."""
    bot_name = os.getenv("BOT_NAME", "BeatAniVerse Bot")
    support  = os.getenv("SUPPORT_CHAT", "Beat_Anime_Discussion")
    channel  = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")

    short_desc = (
        f"🎌 {bot_name}\n\n"
        "Your gateway to Anime, Manga & Movies!\n"
        "Use /start to begin."
    )
    full_desc = (
        f"🎌 {bot_name}\n\n"
        "All-in-one anime Telegram bot.\n\n"
        "• Force-sub & deep links\n"
        "• 12 poster templates\n"
        "• Manga tracker (MangaDex)\n"
        "• Auto-forward & broadcasts\n"
        "• Full group management\n"
        "• Dual DB: NeonDB + MongoDB\n\n"
        f"/start — begin | /help — support\n"
        f"@{support} | @BeatAnime"
    )
    # Telegram hard limit: 512 chars for bot description
    full_desc = full_desc[:512]

    try:
        await bot.set_my_short_description(short_description=short_desc)
        logger.info("[CMD_SETUP] Short description set")
    except Exception as exc:
        logger.warning(f"[CMD_SETUP] Short description error: {exc}")

    try:
        await bot.set_my_description(description=full_desc)
        logger.info("[CMD_SETUP] Full description set")
    except Exception as exc:
        logger.warning(f"[CMD_SETUP] Full description error: {exc}")


# ════════════════════════════════════════════════════════════════════════════════
#  MAIN INIT — called from post_init in bot.py
# ════════════════════════════════════════════════════════════════════════════════

async def initialize_bot_commands(bot: Bot) -> None:
    """
    Initialize all bot commands on startup.

    Call this from post_init in bot.py:
        from bot_commands_setup import initialize_bot_commands
        await initialize_bot_commands(application.bot)
    """
    logger.info("[CMD_SETUP] Initializing bot commands...")

    # 1. Set bot profile description
    await set_bot_description_and_help(bot)

    # 2. Set global default (USER level for everyone)
    await set_default_bot_commands(bot)

    # 3. Set OWNER commands for OWNER_ID (skip if env var not configured = 0)
    if OWNER_ID and OWNER_ID != 0:
        await set_bot_commands_for_user(bot, OWNER_ID)
    if ADMIN_ID and ADMIN_ID != 0 and ADMIN_ID != OWNER_ID:
        await set_bot_commands_for_user(bot, ADMIN_ID)

    # 4. Set ADMIN commands for all DRAGONS
    for dragon_id in _get_dragons():
        await set_bot_commands_for_user(bot, dragon_id)

    # 5. Set ADMIN commands for any DB-stored admins
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(
            "SELECT value FROM bot_settings WHERE key LIKE 'admin_%'"
        )
        if rows:
            for row in rows:
                try:
                    # Guard: row may be a tuple with 0 or 1+ columns — unpack safely
                    val = row[0] if isinstance(row, (tuple, list)) and len(row) > 0 else row
                    aid = int(val)
                    if aid and aid != 0:
                        await set_bot_commands_for_user(bot, aid)
                except Exception:
                    pass
    except Exception as exc:
        logger.debug(f"[CMD_SETUP] DB admin scan skipped: {exc}")

    logger.info("[CMD_SETUP] Bot commands initialized successfully!")


# ════════════════════════════════════════════════════════════════════════════════
#  /refresh_commands — any user can refresh their own command list
# ════════════════════════════════════════════════════════════════════════════════

async def refresh_commands_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    /refresh_commands — refresh command menu for the calling user.
    Works for everyone: users get USER tier, admins get ADMIN tier, owner gets OWNER tier.
    """
    user_id = update.effective_user.id
    msg = update.effective_message

    temp = await msg.reply_text(
        "<i>Refreshing your commands…</i>",
        parse_mode="HTML",
    )

    success = await set_bot_commands_for_user(context.bot, user_id)

    if success:
        tier = "OWNER" if _is_owner(user_id) else ("ADMIN" if _is_admin(user_id) else "USER")
        await temp.edit_text(
            f"<b>Commands refreshed!</b>\n\n"
            f"<b>Your level:</b> <code>{tier}</code>\n"
            f"<i>Your command menu has been updated.</i>",
            parse_mode="HTML",
        )
    else:
        await temp.edit_text(
            "<b>Failed to refresh commands.</b>\n\n"
            "<i>Please try again later or contact support.</i>",
            parse_mode="HTML",
        )


# ════════════════════════════════════════════════════════════════════════════════
#  /refresh_all_commands — owner/admin only
# ════════════════════════════════════════════════════════════════════════════════

async def refresh_all_commands_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    /refresh_all_commands — refresh commands for owner + all DRAGONS.
    Owner/admin only.
    """
    uid = update.effective_user.id
    if not _is_admin(uid):
        return

    msg = update.effective_message
    temp = await msg.reply_text(
        "<i>Refreshing commands for all privileged users…</i>",
        parse_mode="HTML",
    )

    try:
        # Default scope
        await set_default_bot_commands(context.bot)

        # Owner
        await set_bot_commands_for_user(context.bot, OWNER_ID)
        owner_ok = True

        # DRAGONS
        dragons = _get_dragons()
        dragon_ok = 0
        for did in dragons:
            if await set_bot_commands_for_user(context.bot, did):
                dragon_ok += 1

        # DB admins
        db_admin_ok = 0
        try:
            from database_dual import _pg_exec_many
            rows = _pg_exec_many(
                "SELECT value FROM bot_settings WHERE key LIKE 'admin_%'"
            )
            if rows:
                for (val,) in rows:
                    try:
                        if await set_bot_commands_for_user(context.bot, int(val)):
                            db_admin_ok += 1
                    except Exception:
                        pass
        except Exception:
            pass

        await temp.edit_text(
            f"<b>Commands refreshed!</b>\n\n"
            f"<b>├ Default (all users):</b> ✅\n"
            f"<b>├ Owner:</b> {'✅' if owner_ok else '❌'}\n"
            f"<b>├ Dragons ({len(dragons)}):</b> ✅ {dragon_ok}/{len(dragons)}\n"
            f"<b>└ DB Admins:</b> ✅ {db_admin_ok}",
            parse_mode="HTML",
        )
    except Exception as exc:
        await temp.edit_text(
            f"<b>Failed to refresh all commands:</b>\n\n"
            f"<code>{str(exc)[:500]}</code>",
            parse_mode="HTML",
        )


# ════════════════════════════════════════════════════════════════════════════════
#  /set_bot_description — owner only
# ════════════════════════════════════════════════════════════════════════════════

async def set_description_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    /set_bot_description — update bot profile description. Owner only.
    """
    if update.effective_user.id not in (OWNER_ID, ADMIN_ID):
        return

    msg = update.effective_message
    temp = await msg.reply_text(
        "<i>Updating bot description…</i>", parse_mode="HTML"
    )

    try:
        await set_bot_description_and_help(context.bot)
        await temp.edit_text(
            "<b>Bot description updated!</b>\n\n"
            "<i>Users will now see the updated profile description and help info.</i>",
            parse_mode="HTML",
        )
    except Exception as exc:
        await temp.edit_text(
            f"<b>Failed to update description:</b>\n\n"
            f"<code>{str(exc)[:500]}</code>",
            parse_mode="HTML",
        )


# ════════════════════════════════════════════════════════════════════════════════
#  REGISTER HANDLERS — call this from bot.py
# ════════════════════════════════════════════════════════════════════════════════

def register_command_setup_handlers(application) -> None:
    """
    Register /refresh_commands, /refresh_all_commands, /set_bot_description
    into the Application dispatcher.

    Call once from bot.py main():
        from bot_commands_setup import register_command_setup_handlers
        register_command_setup_handlers(application)
    """
    application.add_handler(
        CommandHandler("refresh_commands",     refresh_commands_handler)
    )
    application.add_handler(
        CommandHandler("refresh_all_commands", refresh_all_commands_handler)
    )
    application.add_handler(
        CommandHandler("set_bot_description",  set_description_handler)
    )
    logger.info("[CMD_SETUP] Handlers registered: /refresh_commands, /refresh_all_commands, /set_bot_description")


logger.info("[CMD_SETUP] bot_commands_setup module loaded!")
