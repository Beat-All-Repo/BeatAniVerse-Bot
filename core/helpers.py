"""
core/helpers.py
===============
Safe Telegram API wrappers (send, edit, delete, answer),
user-friendly error messages, and system stats helpers.
"""
import time
import asyncio
import traceback
import psutil
from typing import Optional, Any, Dict
from datetime import datetime, timezone

from telegram import (
    Bot, Update, CallbackQuery, InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.error import (
    TelegramError, Forbidden, BadRequest, NetworkError,
    TimedOut, RetryAfter,
)

from core.config import (
    ADMIN_ID, OWNER_ID, BOT_START_TIME,
)
from core.text_utils import b, code, e, format_size, format_duration
from core.logging_setup import logger


# ── Error class ────────────────────────────────────────────────────────────────

class UserFriendlyError:
    """Translates technical errors into plain, friendly language."""

    FRIENDLY_MAP: Dict[str, str] = {
        "forbidden": (
            "🚫 <b>Bot can't message this user</b>\n\n"
            "The user has blocked the bot or deleted their account."
        ),
        "chat not found": (
            "🔍 <b>Chat not found</b>\n\n"
            "The channel or group doesn't exist, or the bot hasn't been added there."
        ),
        "bot is not a member": (
            "🤖 <b>Bot is not in the channel</b>\n\n"
            "Please add the bot to the channel as an admin first."
        ),
        "not enough rights": (
            "🔐 <b>Missing permissions</b>\n\n"
            "The bot doesn't have admin rights in that channel."
        ),
        "message to edit not found": (
            "💬 <b>Message was deleted</b>\n\n"
            "The message was already deleted, so it couldn't be updated. This is harmless."
        ),
        "message is not modified": (
            "✏️ <b>Nothing changed</b>\n\n"
            "The message already shows the latest information."
        ),
        "query is too old": (
            "⏰ <b>Button expired</b>\n\n"
            "This button is too old. Please tap the menu button again to get a fresh one."
        ),
        "retry after": (
            "⏳ <b>Telegram rate limit</b>\n\n"
            "Too many messages sent too quickly. The bot will automatically retry shortly."
        ),
        "timed out": (
            "⌛ <b>Connection timed out</b>\n\n"
            "The request took too long. Please try again."
        ),
        "network error": (
            "🌐 <b>Network issue</b>\n\n"
            "There was a connection problem. Please try again in a moment."
        ),
        "invalid token": (
            "🔑 <b>Invalid bot token</b>\n\n"
            "The bot token provided doesn't work. Please check it and try again."
        ),
        "wrong file identifier": (
            "🖼 <b>File not available</b>\n\n"
            "This file is no longer accessible. Please send it again."
        ),
        "parse entities": (
            "📝 <b>Text formatting error</b>\n\n"
            "There was an issue formatting the message. This has been logged."
        ),
        "peer_id_invalid": (
            "👤 <b>User ID is invalid</b>\n\n"
            "That user ID doesn't exist or can't be reached."
        ),
    }

    GENERIC_USER_MSG = (
        "😅 <b>Something went wrong</b>\n\n"
        "Don't worry — this isn't your fault. "
        "The issue has been automatically reported to our team."
    )

    @staticmethod
    def get_user_message(error: Exception) -> str:
        err_str = str(error).lower()
        for key, msg in UserFriendlyError.FRIENDLY_MAP.items():
            if key in err_str:
                return msg
        return UserFriendlyError.GENERIC_USER_MSG

    @staticmethod
    def get_admin_message(error: Exception, context_info: str = "") -> str:
        err_type = type(error).__name__
        err_detail = str(error)
        tb = traceback.format_exc()
        tb_short = tb[-1500:] if len(tb) > 1500 else tb
        return (
            f"<b>⚠️ Technical Error</b>\n"
            f"<b>Type:</b> <code>{e(err_type)}</code>\n"
            f"<b>Detail:</b> <code>{e(err_detail[:300])}</code>\n"
            + (f"<b>Context:</b> <code>{e(context_info[:200])}</code>\n" if context_info else "")
            + f"\n<pre>{e(tb_short)}</pre>"
        )

    @staticmethod
    def is_ignorable(error: Exception) -> bool:
        ignorable = [
            "query is too old",
            "message is not modified",
            "message to edit not found",
            "have no rights to send",
        ]
        err_str = str(error).lower()
        return any(ig in err_str for ig in ignorable)


# ── Safe Telegram API wrappers ────────────────────────────────────────────────

async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> bool:
    """Delete a message safely, ignoring all errors."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        return False


async def safe_answer(
    query: CallbackQuery,
    text: str = "",
    show_alert: bool = False,
) -> None:
    """Answer a callback query, silently ignoring timeout errors."""
    try:
        await query.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


async def safe_send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = True,
) -> Optional[Any]:
    """Send a message safely with proper error handling."""
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
    except RetryAfter as exc:
        await asyncio.sleep(exc.retry_after + 1)
        try:
            return await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
        except Exception:
            return None
    except Exception as exc:
        logger.debug(f"safe_send_message failed to {chat_id}: {exc}")
        return None


async def gc_auto_delete(bot: Bot, chat_id: int, msg: Any, delay: int = None) -> None:
    """Schedule auto-deletion of a bot message in a group chat."""
    try:
        if not msg:
            return
        if str(chat_id).startswith("-"):
            if delay is None:
                try:
                    from database_dual import get_setting
                    delay = int(get_setting("auto_delete_delay", "60"))
                except Exception:
                    delay = 60
            try:
                from database_dual import get_setting
                if get_setting("auto_delete_messages", "true") != "true":
                    return
            except Exception:
                pass

            async def _do_delete():
                await asyncio.sleep(delay)
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
                except Exception:
                    pass
            asyncio.create_task(_do_delete())
    except Exception:
        pass


async def safe_edit_text(
    query: CallbackQuery,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """Edit a message text safely; fall back to sending new message."""
    try:
        return await query.edit_message_text(
            text=text, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except BadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return None
    except Exception:
        pass
    try:
        chat_id = query.message.chat_id
        return await safe_send_message(
            query.message.get_bot(),
            chat_id, text, parse_mode, reply_markup
        )
    except Exception as exc:
        logger.debug(f"safe_edit_text fallback failed: {exc}")
    return None


async def safe_edit_caption(
    query: CallbackQuery,
    caption: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """Edit a message caption safely."""
    try:
        return await query.edit_message_caption(
            caption=caption, parse_mode=parse_mode, reply_markup=reply_markup
        )
    except Exception:
        return await safe_edit_text(query, caption, parse_mode, reply_markup)


async def safe_reply(
    update: Update,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    disable_web_page_preview: bool = True,
) -> Optional[Any]:
    """Reply to a message or callback query safely."""
    try:
        if update.message:
            return await update.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif update.callback_query and update.callback_query.message:
            return await update.callback_query.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        elif update.effective_chat:
            bot = update._bot
            return await safe_send_message(
                bot, update.effective_chat.id, text, parse_mode, reply_markup
            )
    except Exception as exc:
        logger.debug(f"safe_reply failed: {exc}")
    return None


async def safe_send_photo(
    bot: Bot,
    chat_id: int,
    photo: Any,
    caption: str = "",
    parse_mode: str = ParseMode.HTML,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> Optional[Any]:
    """
    Send photo with robust error handling + auto text fallback.
    If image URL is unreachable or invalid → sends caption as text.
    """
    if not photo:
        if caption:
            return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
        return None
    try:
        return await bot.send_photo(
            chat_id=chat_id, photo=photo, caption=caption,
            parse_mode=parse_mode, reply_markup=reply_markup,
        )
    except BadRequest as exc:
        err = str(exc).lower()
        if any(k in err for k in (
            "photo_invalid", "url_invalid", "wrong file", "failed to get",
            "invalid document", "webpage_media_empty", "wrong_url"
        )):
            logger.debug(f"safe_send_photo bad image, using text fallback: {exc}")
        else:
            logger.debug(f"safe_send_photo BadRequest: {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    except (NetworkError, TimedOut) as exc:
        logger.debug(f"safe_send_photo network error (text fallback): {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    except Forbidden:
        pass
    except Exception as exc:
        logger.debug(f"safe_send_photo failed: {exc}")
        if caption:
            try:
                return await safe_send_message(bot, chat_id, caption, parse_mode, reply_markup)
            except Exception:
                pass
    return None


# ── System stats ───────────────────────────────────────────────────────────────

def get_uptime() -> str:
    return format_duration(int(time.time() - BOT_START_TIME))


def get_db_size() -> str:
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT pg_database_size(current_database())")
            return format_size(cur.fetchone()[0])
    except Exception:
        return "N/A"


def get_disk_usage() -> str:
    try:
        usage = psutil.disk_usage("/")
        return f"{format_size(usage.free)} free / {format_size(usage.total)} total"
    except Exception:
        return "N/A"


def get_cpu_usage() -> str:
    try:
        return f"{psutil.cpu_percent(interval=0.3):.1f}%"
    except Exception:
        return "N/A"


def get_memory_usage() -> str:
    try:
        m = psutil.virtual_memory()
        return f"{m.percent:.1f}% ({format_size(m.used)} / {format_size(m.total)})"
    except Exception:
        return "N/A"


def get_network_info() -> str:
    try:
        net = psutil.net_io_counters()
        return f"↑{format_size(net.bytes_sent)} ↓{format_size(net.bytes_recv)}"
    except Exception:
        return "N/A"


def get_system_stats_text() -> str:
    from core.config import BOT_USERNAME, I_AM_CLONE, BOT_NAME
    return (
        b(" System Statistics") + "\n\n"
        f"<b>⏱ Uptime:</b> {code(get_uptime())}\n"
        f"<b> CPU:</b> {code(get_cpu_usage())}\n"
        f"<b> Memory:</b> {code(get_memory_usage())}\n"
        f"<b> DB Size:</b> {code(get_db_size())}\n"
        f"<b> Disk:</b> {code(get_disk_usage())}\n"
        f"<b> Network:</b> {code(get_network_info())}\n"
        f"<b> Mode:</b> {code('Clone Bot' if I_AM_CLONE else 'Main Bot')}\n"
        f"<b> Username:</b> @{e(BOT_USERNAME)}"
    )
