"""
handlers/start.py
=================
/start command, deep link handling, welcome screen,
loading animation, safety anchor system.
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Any

# ── In-memory invite link cache (BCJ pattern) ─────────────────────────────────
# channel_id (int) → {"link": str, "ts": datetime, "jbr": bool}
# Dict lookup = nanoseconds. Zero DB, zero API on cache hit.
_invite_cache: dict = {}
_channel_locks: dict = defaultdict(asyncio.Lock)  # one lock per channel

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot,
)
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, BOT_USERNAME, BOT_NAME, I_AM_CLONE,
    WELCOME_SOURCE_CHANNEL, WELCOME_SOURCE_MESSAGE_ID,
    WELCOME_IMAGE_URL, PUBLIC_ANIME_CHANNEL_URL,
    REQUEST_CHANNEL_URL, ADMIN_CONTACT_USERNAME,
    LINK_EXPIRY_MINUTES, HERE_IS_LINK_TEXT, JOIN_BTN_TEXT,
    TRANSITION_STICKER_ID,
)
from core.text_utils import b, bq, e, small_caps, code
from core.helpers import (
    safe_delete, safe_send_message, safe_send_photo,
    safe_answer, safe_edit_text,
)
from core.buttons import _close_btn, bold_button
from core.state_machine import user_states, _safety_anchors
from core.filters_system import force_sub_required
from core.panel_store import _deliver_panel
from core.logging_setup import logger


# ── Loading animation ─────────────────────────────────────────────────────────


# ── Fire animation (welcome screen) ───────────────────────────────────────────

async def _send_fire_animation(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> None:
    """
    Sends a fire-style animation before the welcome panel.
    Priority: DB sticker → TRANSITION_STICKER_ID → emoji frame animation → silent skip.
    Auto-deletes after brief display so it doesn't clutter chat.
    """
    # Try DB-stored sticker first
    fire_sticker_id = ""
    try:
        from database_dual import get_setting
        fire_sticker_id = get_setting("fire_sticker_id", "") or ""
        if not fire_sticker_id:
            fire_sticker_id = get_setting("loading_sticker_id", "") or ""
    except Exception:
        pass

    if not fire_sticker_id:
        fire_sticker_id = TRANSITION_STICKER_ID or ""

    # Try sending sticker
    if fire_sticker_id:
        try:
            stk_msg = await context.bot.send_sticker(chat_id, fire_sticker_id)
            await asyncio.sleep(1.2)
            try:
                await context.bot.delete_message(chat_id, stk_msg.message_id)
            except Exception:
                pass
            return
        except Exception:
            pass

    # Fallback: emoji fire frame animation
    _FIRE_FRAMES = ["🔥", "🔥🔥", "🔥🔥🔥", "🔥🔥", "🔥"]
    fire_msg = None
    try:
        fire_msg = await context.bot.send_message(
            chat_id,
            _FIRE_FRAMES[0],
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )
    except Exception:
        return

    if fire_msg:
        for frame in _FIRE_FRAMES[1:]:
            await asyncio.sleep(0.15)
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=fire_msg.message_id,
                    text=frame,
                )
            except Exception:
                break
        await asyncio.sleep(0.3)
        try:
            await context.bot.delete_message(chat_id, fire_msg.message_id)
        except Exception:
            pass


async def loading_animation_start(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> Optional[Any]:
    """
    Loading animation — supports custom TG sticker or default ❗ text frames.
    Returns the message object.
    """
    try:
        from database_dual import get_setting
        if get_setting("loading_anim_enabled", "true") == "false":
            return None
    except Exception:
        pass

    msg = None
    try:
        from database_dual import get_setting
        sticker_id = get_setting("loading_sticker_id", "") or TRANSITION_STICKER_ID
        if sticker_id:
            msg = await context.bot.send_sticker(chat_id, sticker_id)
            _safety_anchors[chat_id] = msg.message_id
            return msg
    except Exception:
        pass

    frames = ["❗", "❗❗", "❗❗❗"]
    try:
        msg = await context.bot.send_message(
            chat_id, b(frames[0]), parse_mode=ParseMode.HTML
        )
        _safety_anchors[chat_id] = msg.message_id
        for frame in frames[1:]:
            await asyncio.sleep(0.18)
            try:
                await msg.edit_text(b(frame), parse_mode=ParseMode.HTML)
            except Exception:
                break
    except Exception as exc:
        logger.debug(f"loading_animation_start failed: {exc}")
    return msg


async def loading_animation_end(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int, msg: Optional[Any]
) -> None:
    """Delete the loading message."""
    if not msg:
        return
    if _safety_anchors.get(chat_id) == msg.message_id:
        del _safety_anchors[chat_id]
    await safe_delete(context.bot, chat_id, msg.message_id)


async def send_transition_sticker(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """Fire-and-forget transition sticker, auto-delete after 1s."""
    sticker_to_send = ""
    try:
        from database_dual import get_setting
        sticker_to_send = get_setting("loading_sticker_id", "") or ""
    except Exception:
        pass
    if not sticker_to_send:
        sticker_to_send = TRANSITION_STICKER_ID or ""
    if not sticker_to_send:
        return
    try:
        sticker_msg = await context.bot.send_sticker(chat_id, sticker_to_send)
        async def _delete_later():
            await asyncio.sleep(1.0)
            await safe_delete(context.bot, chat_id, sticker_msg.message_id)
        asyncio.create_task(_delete_later())
    except Exception as exc:
        logger.debug(f"Transition sticker failed: {exc}")


async def ensure_safety_anchor(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """Send a silent anchor message that prevents mobile Telegram exit-on-delete bug."""
    if chat_id in _safety_anchors:
        return
    try:
        anchor = await context.bot.send_message(
            chat_id,
            "<b>❗</b>",
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )
        _safety_anchors[chat_id] = anchor.message_id
    except Exception as exc:
        logger.debug(f"Safety anchor failed for {chat_id}: {exc}")


# ── Message management helpers ────────────────────────────────────────────────

async def delete_update_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Delete the user's trigger message."""
    msg = update.message
    if not msg:
        return
    msg_text = msg.text or ""
    if msg_text.startswith("/start"):
        return
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id == ADMIN_ID and user_states.get(user_id) in (
        "PENDING_BROADCAST", "PENDING_BROADCAST_OPTIONS", "PENDING_BROADCAST_CONFIRM"
    ):
        return
    try:
        await msg.delete()
    except Exception:
        pass


async def delete_bot_prompt(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> None:
    """Delete the previously stored bot prompt message."""
    msg_id = context.user_data.pop("bot_prompt_message_id", None)
    if msg_id and context.bot:
        await safe_delete(context.bot, chat_id, msg_id)


async def store_bot_prompt(
    context: ContextTypes.DEFAULT_TYPE, msg: Any
) -> None:
    """Store a bot message ID so it can be deleted later."""
    if msg and hasattr(msg, "message_id"):
        context.user_data["bot_prompt_message_id"] = msg.message_id


# ── /start handler ────────────────────────────────────────────────────────────

@force_sub_required
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main /start handler.
    - Regular users: welcome screen
    - Admin: admin panel
    - Deep links: channel link delivery
    """
    user = update.effective_user
    chat_id = update.effective_chat.id
    uid = user.id if user else 0

    if user:
        # Always register locally FIRST (works even if DB is down)
        try:
            from broadcast_engine import register_user_local
            register_user_local(uid)
        except Exception:
            pass
        # Then try DB
        try:
            from database_dual import add_user
            add_user(uid, user.username, user.first_name, user.last_name)
        except Exception:
            pass

    await delete_bot_prompt(context, chat_id)

    # ── Deep link: NO animation, go straight to link delivery ────────────────
    # Animation adds ~2.5 s of intentional sleeps — skip it entirely for links.
    if context.args:
        link_id = context.args[0]

        if link_id.lower() == "help":
            from handlers.help import help_command
            await help_command(update, context)
            return

        try:
            from database_dual import get_setting
            clone_redirect = get_setting("clone_redirect_enabled", "false").lower() == "true"
        except Exception:
            clone_redirect = False

        if clone_redirect and not I_AM_CLONE and uid not in (ADMIN_ID, OWNER_ID):
            try:
                from database_dual import get_all_clone_bots
                clones = get_all_clone_bots(active_only=True)
                if clones:
                    clone_uname = clones[0][2]
                    await safe_send_message(
                        context.bot, chat_id,
                        b("🔄 Getting your link via our server bot…"),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "📥 Get Your Link",
                                url=f"https://t.me/{clone_uname}?start={link_id}"
                            )
                        ]]),
                    )
                    return
            except Exception:
                pass

        await handle_deep_link(update, context, link_id)
        return

    # ── Regular /start: sticker only, no loading animation ───────────────────
    if uid not in (ADMIN_ID, OWNER_ID):
        await send_transition_sticker(context, chat_id)

    # Admin panel
    if uid in (ADMIN_ID, OWNER_ID):
        user_states.pop(uid, None)
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context)
        return

    # Regular user welcome
    keyboard = [
        [InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)],
        [InlineKeyboardButton("ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")],
        [InlineKeyboardButton("ʀᴇǫᴜᴇsᴛ ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=REQUEST_CHANNEL_URL)],
        [
            InlineKeyboardButton("ꜰᴇᴀᴛᴜʀᴇs", callback_data="user_features_0"),
            InlineKeyboardButton("ᴀʙᴏᴜᴛ ᴍᴇ", callback_data="about_bot"),
        ],
        [_close_btn()],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    # ── Fire animation before welcome panel ───────────────────────────────────
    await _send_fire_animation(context, chat_id)

    _sent_start_msg = None
    try:
        _sent_start_msg = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=WELCOME_SOURCE_CHANNEL,
            message_id=WELCOME_SOURCE_MESSAGE_ID,
            reply_markup=markup,
        )
    except Exception:
        pass

    if _sent_start_msg:
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id,
                message_id=_sent_start_msg.message_id,
                reaction=[{"type": "emoji", "emoji": "🔥"}],
                is_big=True,
            )
        except Exception:
            pass
        return

    welcome_caption = (
        b(small_caps(f"✨ ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ {e(BOT_NAME)}!")) + "\n\n"
        + bq(
            b(small_caps("ʏᴏᴜʀ ɢᴀᴛᴇᴡᴀʏ ᴛᴏ ᴀʟʟ ᴛʜɪɴɢs ᴀɴɪᴍᴇ, ᴍᴀɴɢᴀ & ᴍᴏᴠɪᴇs!"))
        )
    )

    if WELCOME_IMAGE_URL:
        try:
            sent_photo = await context.bot.send_photo(
                chat_id, WELCOME_IMAGE_URL,
                caption=welcome_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                message_effect_id=5104841245755180586,
            )
            if sent_photo:
                try:
                    await context.bot.set_message_reaction(
                        chat_id=chat_id,
                        message_id=sent_photo.message_id,
                        reaction=[{"type": "emoji", "emoji": "🔥"}],
                        is_big=True,
                    )
                except Exception:
                    pass
            return
        except Exception:
            pass

    try:
        _fb_msg = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_caption,
            parse_mode="HTML",
            reply_markup=markup,
            message_effect_id=5104841245755180586,
            disable_web_page_preview=True,
        )
    except Exception:
        _fb_msg = await safe_send_message(
            context.bot, chat_id, welcome_caption, reply_markup=markup
        )
    if _fb_msg:
        try:
            await context.bot.set_message_reaction(
                chat_id=chat_id, message_id=_fb_msg.message_id,
                reaction=[{"type": "emoji", "emoji": "🔥"}], is_big=True,
            )
        except Exception:
            pass
        # Auto-delete welcome message in DM after delay (photo/poster excluded by middleware)
        try:
            from core.auto_delete import schedule_delete_msg
            await schedule_delete_msg(context.bot, _fb_msg)
        except Exception:
            pass


# ── Deep link handler ─────────────────────────────────────────────────────────

async def _loading_dots(bot, chat_id: int, msg_id: int) -> None:
    """
    Parallel dot animation — runs DURING link generation, not before it.
    Cancelled immediately when the link is ready so it never blocks delivery.
    Bold small-caps style as requested.
    """
    _frames = [
        f"<b>{small_caps('ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ .')}</b>",
        f"<b>{small_caps('ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ ..')}</b>",
        f"<b>{small_caps('ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ ...')}</b>",
        f"<b>{small_caps('ɢᴇɴᴇʀᴀᴛɪɴɢ ʟɪɴᴋ ..')}</b>",
    ]
    i = 0
    while True:
        await asyncio.sleep(0.35)
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=_frames[i % len(_frames)],
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            return
        i += 1


async def handle_deep_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    link_id: str,
) -> None:
    """
    Handle deep link /start?start=<link_id>.

    Speed design:
    ┌─ send loading message ──────────────────────────────────────────── fast
    ├─ start dot animation task (parallel, never blocks generation)
    ├─ check _invite_cache dict (nanoseconds) ──────────── CACHE HIT → done
    └─ on miss: create_chat_invite_link (one API call) ── CACHE MISS → ~0.8s

    Any user tapping the same channel within 5 min gets
    the cached link with zero API calls.
    """
    from core.text_utils import now_utc
    chat_id = update.effective_chat.id

    try:
        from database_dual import get_link_info, get_force_sub_channel_info, get_main_bot_token
    except ImportError:
        await safe_send_message(context.bot, chat_id, b("❌ Service unavailable."))
        return

    # ── Validate link_id ──────────────────────────────────────────────────────
    link_info = get_link_info(link_id)
    if not link_info:
        await safe_send_message(
            context.bot, chat_id,
            b("❌ Invalid Link") + "\n\n"
            + bq(b("This link is invalid or has been removed. "
                   "Please tap the original post button again.")),
        )
        return

    channel_identifier, creator_id, created_time, never_expires = link_info

    # ── Post expiry check ─────────────────────────────────────────────────────
    if not never_expires:
        try:
            created_dt = datetime.fromisoformat(str(created_time))
            if now_utc() > created_dt + timedelta(minutes=LINK_EXPIRY_MINUTES):
                await safe_send_message(
                    context.bot, chat_id,
                    b("⏰ Link Expired") + "\n\n"
                    + bq(
                        b("This invite link has expired.\n\n")
                        + b("💡 Tip: Tap the post button again to get a fresh link.")
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(" ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)
                    ]]),
                )
                return
        except Exception:
            pass

    # ── Resolve channel_id — no get_chat() needed ────────────────────────────
    if isinstance(channel_identifier, str) and channel_identifier.lstrip("-").isdigit():
        channel_id = int(channel_identifier)
    else:
        channel_id = channel_identifier

    # ── Clone: use main bot token ─────────────────────────────────────────────
    invite_bot = context.bot
    if I_AM_CLONE:
        main_token = get_main_bot_token()
        if main_token:
            try:
                invite_bot = Bot(token=main_token)
            except Exception:
                pass

    # ── JBR mode ──────────────────────────────────────────────────────────────
    _ch_info = get_force_sub_channel_info(str(channel_id))
    _jbr_mode = bool(_ch_info and _ch_info[2]) if _ch_info else False

    # ── FAST PATH: serve from cache (nanoseconds, no animation needed) ────────
    _cached = _invite_cache.get(channel_id)
    if _cached and _cached.get("jbr") == _jbr_mode:
        age = (datetime.utcnow() - _cached["ts"]).total_seconds()
        if age < 300:  # 5-minute cache window
            await _send_link_message(context.bot, chat_id, _cached["link"], _jbr_mode)
            return

    # ── SLOW PATH: cache miss — show parallel loading animation ───────────────
    # Send initial loading message (one fast network call, reply to /start msg)
    _reply_to = getattr(update.message, "message_id", None)
    try:
        loading_msg = await context.bot.send_message(
            chat_id,
            f"<b>{small_caps('ᴡᴀᴛᴄʜɪɴɢ ...')}</b>",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=_reply_to,
            disable_notification=True,
        )
        # Start dot animation as a background task —
        # runs DURING the API call below, adds 0ms to generation time
        anim_task = asyncio.create_task(
            _loading_dots(context.bot, chat_id, loading_msg.message_id)
        )
    except Exception:
        loading_msg = None
        anim_task = None

    # ── Now generate the link (animation runs in parallel here) ───────────────
    invite_link = None
    try:
        async with _channel_locks[channel_id]:
            # Double-check after acquiring lock
            _cached = _invite_cache.get(channel_id)
            if _cached and _cached.get("jbr") == _jbr_mode:
                age = (datetime.utcnow() - _cached["ts"]).total_seconds()
                if age < 300:
                    invite_link = _cached["link"]

            if not invite_link:
                # Revoke stale link if present
                if _cached:
                    try:
                        await invite_bot.revoke_chat_invite_link(channel_id, _cached["link"])
                    except Exception:
                        pass
                    _invite_cache.pop(channel_id, None)

                # One API call — this is where animation dots actually play
                invite = await invite_bot.create_chat_invite_link(
                    channel_id,
                    expire_date=int((datetime.utcnow() + timedelta(minutes=10)).timestamp()),
                    name=f"DeepLink {link_id[:8]}",
                    creates_join_request=_jbr_mode,
                )
                invite_link = invite.invite_link

                # Store in cache — next user is instant
                _invite_cache[channel_id] = {
                    "link": invite_link,
                    "ts":   datetime.utcnow(),
                    "jbr":  _jbr_mode,
                }

                # Auto-revoke after 5 min
                async def _revoke_later(_b=invite_bot, _c=channel_id, _l=invite_link):
                    await asyncio.sleep(300)
                    try:
                        await _b.revoke_chat_invite_link(_c, _l)
                    except Exception:
                        pass
                    _invite_cache.pop(_c, None)
                asyncio.create_task(_revoke_later())

    except Forbidden as exc:
        if anim_task:
            anim_task.cancel()
        if loading_msg:
            try:
                await context.bot.delete_message(chat_id, loading_msg.message_id)
            except Exception:
                pass
        await safe_send_message(
            context.bot, chat_id,
            b("🚫 Bot Access Error") + "\n\n"
            + bq(b("The bot has been removed from that channel. Please contact admin.")),
        )
        logger.error(f"handle_deep_link Forbidden: {exc}")
        return
    except Exception as exc:
        if anim_task:
            anim_task.cancel()
        if loading_msg:
            try:
                await context.bot.delete_message(chat_id, loading_msg.message_id)
            except Exception:
                pass
        logger.error(f"handle_deep_link error: {exc}")
        from core.helpers import UserFriendlyError
        await safe_send_message(context.bot, chat_id, UserFriendlyError.get_user_message(exc))
        return

    # ── Stop animation, delete loading message, send link ─────────────────────
    if anim_task:
        anim_task.cancel()
    if loading_msg:
        try:
            await context.bot.delete_message(chat_id, loading_msg.message_id)
        except Exception:
            pass

    await _send_link_message(context.bot, chat_id, invite_link, _jbr_mode)


async def _send_link_message(bot, chat_id: int, invite_link: str, jbr_mode: bool) -> None:
    """Send the final invite link message."""
    try:
        from database_dual import get_setting
        _here_link = get_setting("env_HERE_IS_LINK_TEXT", HERE_IS_LINK_TEXT) or HERE_IS_LINK_TEXT
        _join_text  = get_setting("env_JOIN_BTN_TEXT", JOIN_BTN_TEXT) or JOIN_BTN_TEXT
    except Exception:
        _here_link = HERE_IS_LINK_TEXT
        _join_text  = JOIN_BTN_TEXT

    _jbr_note = ""
    if jbr_mode:
        _jbr_note = "\n" + b(small_caps("ᴛᴀᴘ ᴊᴏɪɴ → ʀᴇǫᴜᴇsᴛ sᴇɴᴛ → ᴀᴜᴛᴏ-ᴀᴘᴘʀᴏᴠᴇᴅ ɪɴsᴛᴀɴᴛʟʏ"))

    _link_msg = (
        f"<blockquote><b>{small_caps(_here_link)}</b></blockquote>\n\n"
        + f"<u><b>{small_caps('ɴᴏᴛᴇ: ɪꜰ ᴛʜᴇ ʟɪɴᴋ ɪs ᴇxᴘɪʀᴇᴅ, ᴘʟᴇᴀsᴇ ᴄʟɪᴄᴋ ᴛʜᴇ ᴘᴏsᴛ ʟɪɴᴋ ᴀɢᴀɪɴ.')}</b></u>"
    )
    if _jbr_note:
        _link_msg += "\n" + _jbr_note

    keyboard = [[bold_button(small_caps(_join_text), url=invite_link)]]
    await bot.send_message(
        chat_id, _link_msg,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
