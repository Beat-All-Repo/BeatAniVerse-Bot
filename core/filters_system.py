"""
core/filters_system.py
======================
Force-subscription gating, maintenance/ban checks,
per-update filter system (DM/group/command toggles).
"""
import asyncio
from functools import wraps
from typing import Optional, List, Tuple, Callable, Dict, Any

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from core.config import ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL, ADMIN_CONTACT_USERNAME
from core.text_utils import b, bq, e, small_caps
from core.buttons import bold_button
from core.helpers import safe_answer, safe_edit_text, safe_send_message
from core.logging_setup import logger


# ── Filter config (in-memory, can be modified at runtime) ─────────────────────
filters_config: Dict[str, Any] = {
    "global": {"dm": True, "group": True},
    "commands": {},
    "banned_users": set(),
    "disabled_chats": set(),
}


def passes_filter(update: "Update", command: str = "") -> bool:
    """Check if a message passes the filter system. Returns False to block."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return True
    uid = user.id
    cid = chat.id
    if uid in (ADMIN_ID, OWNER_ID):
        return True
    if uid in filters_config["banned_users"]:
        return False
    if cid in filters_config["disabled_chats"]:
        return False
    is_private = chat.type == "private"
    if is_private and not filters_config["global"].get("dm", True):
        return False
    if not is_private and not filters_config["global"].get("group", True):
        return False
    if command and command in filters_config["commands"]:
        cmd_cfg = filters_config["commands"][command]
        if is_private and not cmd_cfg.get("dm", True):
            return False
        if not is_private and not cmd_cfg.get("group", True):
            return False
    return True


# ── Force subscription check ───────────────────────────────────────────────────

async def get_unsubscribed_channels(
    user_id: int, bot: Bot
) -> List[Tuple[str, str, bool]]:
    """
    Return list of (username, title, jbr) for channels the user has not joined.
    """
    try:
        from database_dual import get_all_force_sub_channels, get_main_bot_token
    except ImportError:
        return []

    channels_info = get_all_force_sub_channels(return_usernames_only=False)
    if not channels_info:
        return []

    unsubscribed = []
    main_bot: Optional[Bot] = None

    from core.config import I_AM_CLONE
    if I_AM_CLONE:
        main_token = get_main_bot_token()
        if main_token:
            try:
                main_bot = Bot(token=main_token)
            except Exception:
                pass

    for uname, title, jbr in channels_info:
        subscribed = False
        for check_bot in filter(None, [bot, main_bot]):
            try:
                member = await check_bot.get_chat_member(chat_id=uname, user_id=user_id)
                if member.status not in ("left", "kicked"):
                    subscribed = True
                    break
                else:
                    break
            except Exception as exc:
                logger.debug(f"Membership check {uname} failed: {exc}")
                continue
        if not subscribed:
            unsubscribed.append((uname, title, jbr))

    return unsubscribed


async def send_maintenance_block(update: Update, context) -> None:
    """Show maintenance message to non-existing users."""
    try:
        from database_dual import get_setting
        backup_url = get_setting("backup_channel_url", "")
    except Exception:
        backup_url = ""

    text = (
        b("🔧 Bot Under Maintenance") + "\n\n"
        + bq(
            b("We are doing some scheduled maintenance right now.\n\n")
            + "<b>Existing members can still access the bot.\n"
            "New members, please wait for us to come back online.</b>",
        ) + "\n\n"
        + b("Stay updated via our backup channel.")
    )
    keyboard = []
    if backup_url:
        keyboard.append([InlineKeyboardButton("📢 Backup Channel", url=backup_url)])
    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    try:
        if update.callback_query:
            await safe_edit_text(update.callback_query, text, reply_markup=markup)
        elif update.effective_chat:
            await safe_send_message(
                context.bot, update.effective_chat.id, text, reply_markup=markup
            )
    except Exception as exc:
        logger.debug(f"send_maintenance_block error: {exc}")


async def send_ban_screen(update: Update, context) -> None:
    """Show a user-friendly ban screen."""
    text = (
        b("🚫 You have been restricted") + "\n\n"
        + bq(
            b("Your access to this bot has been suspended.\n\n")
            + b("If you think this is a mistake, please contact the admin.")
        ) + "\n\n"
        + f"<b>Contact:</b> @{e(ADMIN_CONTACT_USERNAME)}"
    )
    try:
        if update.callback_query:
            await safe_answer(update.callback_query)
            await safe_edit_text(update.callback_query, text)
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception:
        pass


async def _send_force_sub_screen(
    update: Update,
    context,
    unsubscribed: List[Tuple[str, str, bool]],
    user_id: int,
) -> None:
    """Display the force-sub join screen."""
    from database_dual import get_all_force_sub_channels
    user = update.effective_user
    total = len(get_all_force_sub_channels(return_usernames_only=False))
    unjoined = len(unsubscribed)
    user_name = e(
        getattr(user, "first_name", None) or
        getattr(user, "username", None) or "Friend"
    )

    text = (
        f"⚠️ {b(f'Hey {user_name}! You need to join {unjoined} channel(s).')}\n\n"
        + bq(
            b("Please join ALL the channels listed below,\n")
            + b("then click the  Try Again button.")
        )
        + f"\n\n<b>Total channels: {total} | Unjoined: {unjoined}</b>"
    )

    keyboard = []
    for uname, title, jbr in unsubscribed:
        clean = uname.lstrip("@")
        keyboard.append([InlineKeyboardButton(f" {title}", url=f"https://t.me/{clean}")])

    keyboard.append([bold_button("♻️Try Again", callback_data="verify_subscription")])
    keyboard.append([bold_button("Help", callback_data="user_help")])
    markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await safe_edit_text(update.callback_query, text, reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        elif update.effective_chat:
            await safe_send_message(context.bot, update.effective_chat.id, text, reply_markup=markup)
    except Exception as exc:
        logger.debug(f"_send_force_sub_screen error: {exc}")


def force_sub_required(func: Callable) -> Callable:
    """
    Decorator: check force-sub, maintenance mode, and ban before executing
    any command or button handler.
    """
    @wraps(func)
    async def wrapper(update: Update, context, *args, **kwargs):
        user = update.effective_user
        if user is None:
            return await func(update, context, *args, **kwargs)

        if update.callback_query:
            await safe_answer(update.callback_query)

        uid = user.id

        if uid in (ADMIN_ID, OWNER_ID):
            return await func(update, context, *args, **kwargs)

        try:
            from database_dual import is_user_banned, is_maintenance_mode, is_existing_user
        except ImportError:
            return await func(update, context, *args, **kwargs)

        if is_user_banned(uid):
            await send_ban_screen(update, context)
            return

        if is_maintenance_mode() and not is_existing_user(uid):
            await send_maintenance_block(update, context)
            return

        unsubscribed = await get_unsubscribed_channels(uid, context.bot)
        if unsubscribed:
            await _send_force_sub_screen(update, context, unsubscribed, uid)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
