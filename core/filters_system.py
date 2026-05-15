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

async def _is_sub_single(bot: Bot, user_id: int,
                          uname: str, ch_id: Optional[int],
                          jbr: bool) -> bool:
    """
    Exact port of is_sub() from Advance-File-Share-bot (request_fsub.py / helper_func.py):

    1. Try get_chat_member(channel_id, user_id).
       - status MEMBER / ADMIN / OWNER / RESTRICTED → True ✅
       - status LEFT / KICKED:
           • JBR mode → check DB whitelist (req_user_exist equivalent) → True if found
           • Direct mode → False ❌
    2. If get_chat_member raises (private channel, bot not admin, etc.):
       - JBR mode → check DB whitelist (give benefit of doubt)
       - Direct mode → False ❌
    """
    from database_dual import has_fsub_join_request

    # Always use numeric channel_id for get_chat_member — most reliable
    lookup = ch_id if ch_id else uname
    try:
        member = await bot.get_chat_member(chat_id=lookup, user_id=user_id)
        status = member.status
        logger.debug(f"[fsub] user={user_id} ch={lookup} status={status} jbr={jbr}")

        if status not in ("left", "kicked"):
            return True  # joined, admin, owner, or restricted-but-still-in

        # User is left/kicked — for JBR channels, check whitelist
        if jbr and ch_id:
            in_whitelist = has_fsub_join_request(ch_id, user_id)
            logger.debug(f"[fsub] JBR whitelist check ch={ch_id} user={user_id} → {in_whitelist}")
            return in_whitelist
        return False

    except Exception as exc:
        logger.debug(f"[fsub] get_chat_member({lookup}) raised: {exc}")
        # Bot can't check membership (private channel, not admin, etc.)
        # For JBR channels: check whitelist instead of blocking
        if jbr and ch_id:
            in_whitelist = has_fsub_join_request(ch_id, user_id)
            logger.debug(f"[fsub] JBR fallback whitelist ch={ch_id} user={user_id} → {in_whitelist}")
            return in_whitelist
        return False


async def get_unsubscribed_channels(
    user_id: int, bot: Bot
) -> List[Tuple[str, str, bool, str]]:
    """
    Return 4-tuples (uname, title, jbr, invite_link) for channels the user
    has NOT yet fully joined/whitelisted.

    Mirrors is_subscribed() + is_sub() from Advance-File-Share-bot exactly.
    """
    try:
        from database_dual import get_all_force_sub_channels, get_main_bot_token
    except ImportError:
        return []

    channels_info = get_all_force_sub_channels(return_usernames_only=False)
    if not channels_info:
        return []

    main_bot: Optional[Bot] = None
    from core.config import I_AM_CLONE
    if I_AM_CLONE:
        main_token = get_main_bot_token()
        if main_token:
            try:
                main_bot = Bot(token=main_token)
            except Exception:
                pass

    unsubscribed: List[Tuple[str, str, bool, str]] = []

    for row in channels_info:
        uname       = row[0] if len(row) > 0 else ""
        title       = row[1] if len(row) > 1 else uname
        jbr         = bool(row[2]) if len(row) > 2 else False
        invite_link = row[3] if len(row) > 3 else ""

        # Resolve numeric channel_id — needed for whitelist lookup
        # Priority: stored column → parse numeric username → bot.get_chat (JBR only)
        ch_id: Optional[int] = None
        if len(row) > 4 and row[4]:
            try:
                ch_id = int(row[4])
            except (ValueError, TypeError):
                pass
        if ch_id is None:
            # Covers channels stored as "-1001234567890" in channel_username
            try:
                ch_id = int(uname.lstrip("@"))
            except (ValueError, TypeError):
                pass
        # For JBR channels where ch_id is still None (public @username channels):
        # resolve via Bot API once and update DB so future checks are instant.
        if ch_id is None and jbr:
            try:
                chat_obj = await bot.get_chat(uname)
                ch_id = chat_obj.id
                # Persist so we don't need to resolve again
                try:
                    from database_dual import _pg_run as _pgr
                    _pgr(
                        "UPDATE force_sub_channels SET channel_id = %s WHERE channel_username = %s AND channel_id IS NULL",
                        (ch_id, uname),
                    )
                except Exception:
                    pass
            except Exception as _ge:
                logger.debug(f"[fsub] could not resolve ch_id for {uname}: {_ge}")

        # Check via main bot first, then clone bot
        subscribed = False
        for check_bot in filter(None, [bot, main_bot]):
            subscribed = await _is_sub_single(check_bot, user_id, uname, ch_id, jbr)
            if subscribed:
                break

        if not subscribed:
            unsubscribed.append((uname, title, jbr, invite_link))

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


def _make_channel_join_url(uname: str, jbr: bool, invite_link: str) -> str:
    """
    Build the best URL for a force-sub channel button.

    Priority:
      1. Stored invite_link  (already a full URL, works for both public & private).
      2. Public @username    → https://t.me/{username}
      3. Numeric channel ID  → None (caller will skip button or show placeholder).
    """
    if invite_link:
        return invite_link
    # Public username stored as "@handle" or bare "handle"
    clean = uname.lstrip("@")
    if clean and not clean.lstrip("-").isdigit():
        return f"https://t.me/{clean}"
    # Private channel with no invite link stored yet – nothing we can do here
    return ""


async def _send_force_sub_screen(
    update: Update,
    context,
    unsubscribed: List[Tuple],
    user_id: int,
) -> None:
    """
    Display the force-sub join screen matching the BeatAniVerse UI:
      • Photo banner (configurable via bot setting "fsub_photo")
      • Caption with user name, unjoined/total count, help note
      • One button per channel — small caps channel title only (no emoji prefix)
      • ♻️ Try Again at bottom
    """
    from database_dual import get_all_force_sub_channels, get_setting
    user      = update.effective_user
    total     = len(get_all_force_sub_channels(return_usernames_only=False))
    unjoined  = len(unsubscribed)
    user_name = e(
        getattr(user, "first_name", None) or
        getattr(user, "username", None) or "Friend"
    )

    # unjoined = channels user still needs to join/request
    # total    = all configured fsub channels
    # Display: "X/Y channels" → X left to join out of Y total required
    caption = (
        f"⚠️ {b(f'ʜᴇʏ, {small_caps(user_name)} ×')} »\n\n"
        f"{b(f'ʏᴏᴜ ʜᴀᴠᴇɴᴛ ᴊᴏɪɴᴇᴅ {unjoined}/{total} ᴄʜᴀɴɴᴇʟs ʏᴇᴛ. ')}"
        f"{b('ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟs ᴘʀᴏᴠɪᴅᴇᴅ ʙᴇʟᴏᴡ, ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ.. !')}\n\n"
        f"❗ {b('ғᴀᴄɪɴɢ ᴘʀᴏʙʟᴇᴍs, ᴜsᴇ:')} /help"
    )

    # ── Buttons: channel title only in small caps, no emoji prefix ────────────
    keyboard = []
    for row in unsubscribed:
        uname       = row[0] if len(row) > 0 else ""
        title       = row[1] if len(row) > 1 else uname
        invite_link = row[3] if len(row) > 3 else ""

        url   = _make_channel_join_url(uname, bool(row[2]) if len(row) > 2 else False, invite_link)
        label = small_caps(title.strip()) if title.strip() else small_caps(uname.lstrip("@"))

        if url:
            keyboard.append([InlineKeyboardButton(label, url=url)])
        else:
            # No link yet — show as non-tappable so the list is still complete
            keyboard.append([InlineKeyboardButton(f"{label} ⚠️", callback_data="noop")])

    keyboard.append([bold_button("♻️ ᴛʀʏ ᴀɢᴀɪɴ", callback_data="verify_subscription")])
    markup = InlineKeyboardMarkup(keyboard)

    # ── Delivery: photo if configured, pure text otherwise ────────────────────
    try:
        fsub_photo = get_setting("fsub_photo", "") or ""
    except Exception:
        fsub_photo = ""

    chat_id = update.effective_chat.id if update.effective_chat else user_id
    query   = update.callback_query   # may be None

    async def _try_send_photo() -> bool:
        """Return True on success."""
        try:
            if query:
                # Edit existing message in-place if it already has a photo
                if getattr(query.message, "photo", None) or getattr(query.message, "document", None):
                    from telegram import InputMediaPhoto
                    await query.message.edit_media(
                        InputMediaPhoto(media=fsub_photo, caption=caption,
                                        parse_mode=ParseMode.HTML),
                        reply_markup=markup,
                    )
                    return True
                # Otherwise delete the old message and send a fresh photo
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fsub_photo, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=markup,
                )
                return True
            elif update.message:
                await update.message.reply_photo(
                    photo=fsub_photo, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=markup,
                )
                return True
            else:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=fsub_photo, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=markup,
                )
                return True
        except Exception as _pe:
            logger.debug(f"[fsub] photo send failed: {_pe}")
            return False

    async def _send_text() -> None:
        """Send or edit as plain text — always works."""
        if query:
            try:
                # If current message is a photo we must delete+resend (can't edit to text)
                if getattr(query.message, "photo", None):
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_message(
                        chat_id=chat_id, text=caption,
                        parse_mode=ParseMode.HTML, reply_markup=markup,
                    )
                    return
                await safe_edit_text(query, caption, reply_markup=markup)
                return
            except Exception as _te:
                logger.debug(f"[fsub] text edit failed: {_te}")
        if update.message:
            await update.message.reply_text(
                caption, parse_mode=ParseMode.HTML, reply_markup=markup,
            )
        else:
            await safe_send_message(context.bot, chat_id, caption, reply_markup=markup)

    # Try photo first if configured; fall back to text silently
    if fsub_photo:
        ok = await _try_send_photo()
        if not ok:
            await _send_text()
    else:
        await _send_text()


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
            # ── Store pending deep-link so "Try Again" can resume it ──────────
            pending_link_id = None
            if context.args:
                pending_link_id = context.args[0]
            elif update.callback_query:
                # Already in callback context — preserve whatever was stored
                pending_link_id = context.user_data.get("pending_link_id")

            if pending_link_id:
                context.user_data["pending_link_id"] = pending_link_id
                # Pre-generate the invite link in background so "Try Again"
                # delivers it instantly from cache without a new API call.
                async def _pregenerate(bot=context.bot, lid=pending_link_id):
                    try:
                        from handlers.start import _prewarm_link
                        await _prewarm_link(bot, lid)
                    except Exception:
                        pass
                asyncio.create_task(_pregenerate())

            await _send_force_sub_screen(update, context, unsubscribed, uid)
            return

        return await func(update, context, *args, **kwargs)

    return wrapper
