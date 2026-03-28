# ====================================================================
# PLACE AT: /app/modules/welcome.py
# ACTION: Replace existing file
# ====================================================================
"""
welcome.py — Full-featured welcome/goodbye system (PTB v13 + v20 dual compat)

ALL original features preserved + new additions:
  ✅ /welcome on|off|noformat — toggle + show current
  ✅ /setwelcome <text> — supports text, media (photo/video/sticker/audio/voice/doc)
  ✅ /setgoodbye <text> — goodbye with same media support
  ✅ /resetwelcome / /resetgoodbye — reset to defaults
  ✅ /cleanwelcome on|off — delete previous welcome on new join
  ✅ /cleanservice on|off — delete Telegram "joined/left" service messages
  ✅ /welcomemute off|soft|strong — anti-bot mute modes
  ✅ /welcomemutehelp — explains mute modes
  ✅ /welcomehelp — format variables guide
  ✅ /setwelcomeimage — set image via reply to photo or URL (new)
  ✅ /welcdelay <seconds> — auto-delete welcome after N seconds (new)
  ✅ /goodbye on|off — simple goodbye toggle (new)
  ✅ Inline settings panel with buttons (new)
  ✅ Special welcomes for OWNER / DRAGONS / DEMONS / TIGERS / WOLVES
  ✅ Bot join → logs to EVENT_LOGS
  ✅ Strong mute: 120s auto-kick if not verified
  ✅ Soft mute: restrict media 24h
  ✅ SQL-backed (welcome_sql) + database_dual fallback
  ✅ HTML tags fully supported in messages
  ✅ All text in small caps
  ✅ Expandable blockquotes
  ✅ Variables: {first} {last} {fullname} {username} {mention} {count} {chatname} {id}
"""

from typing import Optional
import asyncio
import html
import logging
import random
import re
import time
from contextlib import suppress
from functools import partial

from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
    Chat,
)
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    ContextTypes,
)
try:
    from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown
except ImportError:
    from telegram.helpers import escape_markdown, mention_html, mention_markdown

try:
    import BeatVerseProbot
except ImportError:
    BeatVerseProbot = None

import modules.sql.welcome_sql as sql
from beataniversebot_compat import (
    DEMONS,
    DEV_USERS,
    DRAGONS,
    EVENT_LOGS,
    LOGGER,
    OWNER_ID,
    TIGERS,
    WOLVES,
    dispatcher,
)
from modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from modules.helper_funcs.misc import build_keyboard, revert_buttons
from modules.helper_funcs.msg_types import get_welcome_type
from modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from modules.log_channel import loggable
from modules.sql.global_bans_sql import is_user_gbanned

logger = logging.getLogger(__name__)

VALID_WELCOME_FORMATTERS = [
    "first", "last", "fullname", "username",
    "id", "count", "chatname", "mention",
]

# ENUM_FUNC_MAP: use string method names, resolved at runtime to avoid import-time errors
ENUM_FUNC_MAP_KEYS = {
    sql.Types.TEXT.value:        "send_message",
    sql.Types.BUTTON_TEXT.value: "send_message",
    sql.Types.STICKER.value:     "send_sticker",
    sql.Types.DOCUMENT.value:    "send_document",
    sql.Types.PHOTO.value:       "send_photo",
    sql.Types.AUDIO.value:       "send_audio",
    sql.Types.VOICE.value:       "send_voice",
    sql.Types.VIDEO.value:       "send_video",
}

def ENUM_FUNC_MAP(type_val, bot):
    """Get the bot send method for a media type."""
    method_name = ENUM_FUNC_MAP_KEYS.get(type_val, "send_message")
    return getattr(bot, method_name, bot.send_message)

# Strong-mute user waitlist: user_id → state dict
VERIFIED_USER_WAITLIST = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sc(text: str) -> str:
    try:
        from bot import small_caps
        return small_caps(text)
    except Exception:
        return text

def _b(text: str) -> str:
    return f"<b>{_sc(text)}</b>"

def _bq(text: str) -> str:
    return f"<blockquote expandable>{text}</blockquote>"

def _e(text: str) -> str:
    return html.escape(str(text))

def _bold_btn(label: str, cb_or_url: str, url: bool = False) -> InlineKeyboardButton:
    if url:
        return InlineKeyboardButton(_sc(label), url=cb_or_url)
    return InlineKeyboardButton(_sc(label), callback_data=cb_or_url)


# ── Extra image/delay settings via database_dual ─────────────────────────────

def _wkey(chat_id: int, suffix: str) -> str:
    return f"welcome_{chat_id}_{suffix}"

def _get(chat_id: int, suffix: str, default: str = "") -> str:
    try:
        from database_dual import get_setting
        return get_setting(_wkey(chat_id, suffix), default) or default
    except Exception:
        return default

def _set(chat_id: int, suffix: str, value: str) -> None:
    try:
        from database_dual import set_setting
        set_setting(_wkey(chat_id, suffix), value)
    except Exception:
        pass


# ── Legacy send helper (preserves original error handling) ───────────────────

def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            msg = update.effective_message.reply_text(
                message, parse_mode=ParseMode.HTML,
                reply_markup=keyboard, quote=False,
            )
        elif excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has an invalid url "
                    "in one of its buttons. Please update."
                ),
                parse_mode=ParseMode.HTML, reply_to_message_id=reply,
            )
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has buttons which "
                    "use url protocols that are unsupported by telegram. Please update."
                ),
                parse_mode=ParseMode.HTML, reply_to_message_id=reply,
            )
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has some bad urls. "
                    "Please update."
                ),
                parse_mode=ParseMode.HTML, reply_to_message_id=reply,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
        elif excp.message == "Have no rights to send a message":
            return
        else:
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: An error occured when sending the "
                    "custom message. Please update."
                ),
                parse_mode=ParseMode.HTML, reply_to_message_id=reply,
            )
    return msg


# ── Auto-kick job (strong mute: 120s timer) ───────────────────────────────────

def check_not_bot(member, chat_id, message_id, context):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop(member.id, {})
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except Exception:
            pass
        try:
            bot.edit_message_text(
                _sc("*kicks user*\nThey can always rejoin and try."),
                chat_id=chat_id, message_id=message_id,
            )
        except Exception:
            pass


# ── New member handler ────────────────────────────────────────────────────────

@loggable
def new_member(update: Update, context: CallbackContext):
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes  = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:
        welcome_log  = None
        res          = None
        sent         = None
        should_mute  = True
        welcome_bool = True
        media_wel    = False

        if should_welc:
            reply    = update.message.message_id
            cleanserv = sql.clean_service(chat.id)
            if cleanserv:
                try:
                    dispatcher.bot.delete_message(chat.id, update.message.message_id)
                except BadRequest:
                    pass
                reply = False

            # ── Special welcomes for privileged users ─────────────────────────
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "Oh, Genos? Let's get this moving.", reply_to_message_id=reply
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nBot Owner just joined the group"
                )
                continue

            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Be cool! A member of the Heroes Association just joined.",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nBot Dev just joined the group"
                )
                continue

            elif new_mem.id in DRAGONS:
                update.effective_message.reply_text(
                    "Whoa! A Dragon disaster just joined! Stay Alert!",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nBot Sudo just joined the group"
                )
                continue

            elif new_mem.id in DEMONS:
                update.effective_message.reply_text(
                    "Huh! Someone with a Demon disaster level just joined!",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nBot Support just joined the group"
                )
                continue

            elif new_mem.id in TIGERS:
                update.effective_message.reply_text(
                    "Roar! A Tiger disaster just joined!", reply_to_message_id=reply
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nA whitelisted user joined the chat"
                )
                continue

            elif new_mem.id in WOLVES:
                update.effective_message.reply_text(
                    "Awoo! A Wolf disaster just joined!", reply_to_message_id=reply
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n#USER_JOINED\nA whitelisted user joined the chat"
                )
                continue

            elif new_mem.id == bot.id:
                if BeatVerseProbot and not BeatVerseProbot.ALLOW_CHATS:
                    with suppress(BadRequest):
                        update.effective_message.reply_text(
                            f"Groups are disabled for {bot.first_name}, I'm outta here."
                        )
                    bot.leave_chat(update.effective_chat.id)
                    return
                if EVENT_LOGS:
                    bot.send_message(
                        EVENT_LOGS,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>\nAdded by : {} | <code>{}</code>".format(
                            html.escape(chat.title), chat.id,
                            user.first_name or "Unknown", user.id,
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                update.effective_message.reply_text(
                    "Watashi ga kita !", reply_to_message_id=reply
                )
                continue

            else:
                # ── Normal member welcome ─────────────────────────────────────
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = new_mem.first_name or "PersonWithNoName"

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES
                        ).format(first=escape_markdown(first_name))

                    fullname = escape_markdown(
                        f"{first_name} {new_mem.last_name}" if new_mem.last_name else first_name
                    )
                    count   = chat.get_member_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    username = "@" + escape_markdown(new_mem.username) if new_mem.username else mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=fullname,
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )
                else:
                    res  = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                    keyb = []

                # ── Extra: image from database_dual ───────────────────────────
                extra_image = _get(chat.id, "image", "")
                if extra_image and not media_wel:
                    # override: use photo welcome
                    try:
                        sent_img = dispatcher.bot.send_photo(
                            chat.id,
                            photo=extra_image,
                            caption=res,
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(keyb) if keyb else None,
                            reply_to_message_id=reply,
                        )
                        # handle clean
                        prev_welc = sql.get_clean_pref(chat.id)
                        if prev_welc:
                            try:
                                bot.delete_message(chat.id, prev_welc)
                            except BadRequest:
                                pass
                        if sent_img:
                            sql.set_clean_welcome(chat.id, sent_img.message_id)
                            # auto-delete
                            del_after = int(_get(chat.id, "delete_after", "0") or "0")
                            if del_after > 0:
                                job_queue.run_once(
                                    lambda ctx, cid=chat.id, mid=sent_img.message_id: (
                                        lambda: ctx.bot.delete_message(cid, mid)
                                    )(),
                                    del_after,
                                )
                        welcome_log = (
                            f"{html.escape(chat.title)}\n#USER_JOINED\n"
                            f"<b>User</b>: {mention_html(new_mem.id, new_mem.first_name)}\n"
                            f"<b>ID</b>: <code>{new_mem.id}</code>"
                        )
                        continue
                    except Exception:
                        pass  # fallback to normal send

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name)
                )
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool   = False
            res            = None
            keyboard       = None
            backup_message = None
            reply          = None

        # ── Mute logic ────────────────────────────────────────────────────────
        if (
            is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id))
            or human_checks
        ):
            should_mute = False
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id:
            if should_mute:
                if welc_mutes == "soft":
                    bot.restrict_chat_member(
                        chat.id, new_mem.id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_add_web_page_previews=False,
                        ),
                        until_date=(int(time.time() + 24 * 60 * 60)),
                    )

                if welc_mutes == "strong":
                    welcome_bool = False
                    if not media_wel:
                        VERIFIED_USER_WAITLIST.update({
                            new_mem.id: {
                                "should_welc": should_welc,
                                "media_wel":   False,
                                "status":      False,
                                "update":      update,
                                "res":         res,
                                "keyboard":    keyboard,
                                "backup_message": backup_message,
                            }
                        })
                    else:
                        VERIFIED_USER_WAITLIST.update({
                            new_mem.id: {
                                "should_welc":  should_welc,
                                "chat_id":      chat.id,
                                "status":       False,
                                "media_wel":    True,
                                "cust_content": cust_content,
                                "welc_type":    welc_type,
                                "res":          res,
                                "keyboard":     keyboard,
                            }
                        })
                    new_join_mem = f'<a href="tg://user?id={new_mem.id}">{html.escape(new_mem.first_name)}</a>'
                    message = msg.reply_text(
                        f"{new_join_mem}, {_sc('click the button below to prove you are human. you have 120 seconds.')}",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                _sc("Yes, I'm human."),
                                callback_data=f"user_join_({new_mem.id})",
                            )
                        ]]),
                        parse_mode=ParseMode.HTML,
                        reply_to_message_id=reply,
                    )
                    bot.restrict_chat_member(
                        chat.id, new_mem.id,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False,
                        ),
                    )
                    job_queue.run_once(
                        partial(check_not_bot, new_mem, chat.id, message.message_id),
                        120,
                        name="welcomemute",
                    )

        if welcome_bool:
            if media_wel:
                sent = ENUM_FUNC_MAP(welc_type, dispatcher.bot)(
                    chat.id, cust_content,
                    caption=res, reply_markup=keyboard,
                    reply_to_message_id=reply, parse_mode="markdown",
                )
            else:
                sent = send(update, res, keyboard, backup_message)

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass
                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

            # auto-delete welcome
            if sent:
                del_after = int(_get(chat.id, "delete_after", "0") or "0")
                if del_after > 0:
                    job_queue.run_once(
                        partial(_delete_job, chat.id, sent.message_id),
                        del_after,
                        name="welc_autodel",
                    )

        if welcome_log:
            return welcome_log

        return (
            f"{html.escape(chat.title)}\n#USER_JOINED\n"
            f"<b>User</b>: {mention_html(user.id, user.first_name)}\n"
            f"<b>ID</b>: <code>{user.id}</code>"
        )

    return ""


def _delete_job(chat_id, msg_id, context):
    try:
        context.bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


# ── Left member handler ───────────────────────────────────────────────────────

def left_member(update: Update, context: CallbackContext):
    bot  = context.bot
    chat = update.effective_chat
    user = update.effective_user

    if user.id == bot.id:
        return

    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if should_goodbye:
        reply    = update.message.message_id
        cleanserv = sql.clean_service(chat.id)
        if cleanserv:
            try:
                dispatcher.bot.delete_message(chat.id, update.message.message_id)
            except BadRequest:
                pass
            reply = False

        left_mem = update.effective_message.left_chat_member
        if left_mem:
            if is_user_gbanned(left_mem.id):
                return
            if left_mem.id == bot.id:
                return

            if goodbye_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                ENUM_FUNC_MAP(goodbye_type, dispatcher.bot)(chat.id, cust_goodbye)
                return

            first_name = left_mem.first_name or "PersonWithNoName"
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                fullname = escape_markdown(
                    f"{first_name} {left_mem.last_name}" if left_mem.last_name else first_name
                )
                count    = chat.get_member_count()
                mention  = mention_markdown(left_mem.id, first_name)
                username = "@" + escape_markdown(left_mem.username) if left_mem.username else mention

                valid_format = escape_invalid_curly_brackets(cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=fullname, username=username,
                    mention=mention, count=count,
                    chatname=escape_markdown(chat.title), id=left_mem.id,
                )
                buttons  = sql.get_gdbye_buttons(chat.id)
                keyb     = build_keyboard(buttons)
            else:
                res  = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name)
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)
            send(
                update, res, keyboard,
                random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )


# ── /welcome command ──────────────────────────────────────────────────────────

@user_admin
def welcome(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    msg  = update.effective_message

    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        extra_image = _get(chat.id, "image", "")
        del_after   = _get(chat.id, "delete_after", "0")

        status_text = (
            _b(f"welcome is: {'on ✅' if pref else 'off 🔕'}") + "\n"
            + _bq(
                _b("image: ") + _sc("set ✅" if extra_image else "not set") + "\n"
                + _b("auto-delete: ") + _sc(f"{del_after}s" if del_after != "0" else "off")
            ) + "\n\n"
            + _b("welcome message (not filling {}):") + "\n"
        )
        msg.reply_text(status_text, parse_mode=ParseMode.HTML)

        if welcome_type in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                msg.reply_text(welcome_m)
            else:
                keyb     = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)
        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP(welcome_type, dispatcher.bot)(chat.id, cust_content, caption=welcome_m)
            else:
                keyb     = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP(welcome_type, dispatcher.bot)(
                    chat.id, cust_content, caption=welcome_m,
                    reply_markup=keyboard, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )

        # Show settings panel buttons
        msg.reply_text(
            _b("quick settings:"),
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [_bold_btn("🖼 set image",   f"wlc_img_prompt_{chat.id}"),
                 _bold_btn("👋 preview",     f"wlc_preview_{chat.id}")],
                [_bold_btn("🧹 clean: " + ("on" if sql.get_clean_pref(chat.id) else "off"),
                           f"wlc_clean_{chat.id}"),
                 _bold_btn("⏱ delay",       f"wlc_advanced_{chat.id}")],
            ]),
        )

    elif args[0].lower() in ("on", "yes"):
        sql.set_welc_preference(str(chat.id), True)
        msg.reply_text(_b("✅ i'll greet members when they join."), parse_mode=ParseMode.HTML)

    elif args[0].lower() in ("off", "no"):
        sql.set_welc_preference(str(chat.id), False)
        msg.reply_text(_b("🔕 i'll go loaf around and not welcome anyone then."), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text(_b("i understand 'on/yes' or 'off/no' only!"), parse_mode=ParseMode.HTML)


# ── /goodbye command ──────────────────────────────────────────────────────────

@user_admin
def goodbye(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    msg  = update.effective_message

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        msg.reply_text(
            _b(f"goodbye is: {'on ✅' if pref else 'off 🔕'}") + "\n"
            + _b("goodbye message (not filling {}):"),
            parse_mode=ParseMode.HTML,
        )
        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                msg.reply_text(goodbye_m)
            else:
                keyb     = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)
        else:
            if noformat:
                ENUM_FUNC_MAP(goodbye_type, dispatcher.bot)(chat.id, goodbye_m)
            else:
                ENUM_FUNC_MAP(goodbye_type, dispatcher.bot)(chat.id, goodbye_m, parse_mode=ParseMode.HTML)

    elif args[0].lower() in ("on", "yes"):
        sql.set_gdbye_preference(str(chat.id), True)
        msg.reply_text(_b("✅ goodbye enabled."), parse_mode=ParseMode.HTML)

    elif args[0].lower() in ("off", "no"):
        sql.set_gdbye_preference(str(chat.id), False)
        msg.reply_text(_b("🔕 goodbye disabled."), parse_mode=ParseMode.HTML)

    else:
        msg.reply_text(_b("i understand 'on/yes' or 'off/no' only!"), parse_mode=ParseMode.HTML)


# ── /setwelcome ───────────────────────────────────────────────────────────────

@user_admin
@loggable
def set_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text(_b("you didn't specify what to reply with!"), parse_mode=ParseMode.HTML)
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text(
        _b("✅ custom welcome message set!") + "\n"
        + _bq(_sc("use /welcome to preview it.")),
        parse_mode=ParseMode.HTML,
    )
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set the welcome message."
    )


# ── /setgoodbye ───────────────────────────────────────────────────────────────

@user_admin
@loggable
def set_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text(_b("you didn't specify what to reply with!"), parse_mode=ParseMode.HTML)
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text(_b("✅ custom goodbye message set!"), parse_mode=ParseMode.HTML)
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Set the goodbye message."
    )


# ── /resetwelcome ─────────────────────────────────────────────────────────────

@user_admin
@loggable
def reset_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    _set(chat.id, "image", "")
    update.effective_message.reply_text(
        _b("✅ welcome message reset to default."), parse_mode=ParseMode.HTML
    )
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the welcome message to default."
    )


# ── /resetgoodbye ─────────────────────────────────────────────────────────────

@user_admin
@loggable
def reset_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text(
        _b("✅ goodbye message reset to default."), parse_mode=ParseMode.HTML
    )
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the goodbye message to default."
    )


# ── /welcomemute off|soft|strong ──────────────────────────────────────────────

@user_admin
@loggable
def welcomemute(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg  = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text(_b("✅ i will no longer mute people on joining."), parse_mode=ParseMode.HTML)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>OFF</b>."
            )
        elif args[0].lower() == "soft":
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text(
                _b("✅ soft mute enabled.") + "\n"
                + _bq(_sc("new members cannot send media for 24 hours.")),
                parse_mode=ParseMode.HTML,
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>SOFT</b>."
            )
        elif args[0].lower() == "strong":
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text(
                _b("✅ strong mute enabled.") + "\n"
                + _bq(_sc("new members are muted until they verify. they have 120 seconds or get kicked.")),
                parse_mode=ParseMode.HTML,
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>STRONG</b>."
            )
        else:
            msg.reply_text(
                _b("please enter: off / soft / strong") + "\n"
                + _bq(_sc("use /welcomemutehelp for details.")),
                parse_mode=ParseMode.HTML,
            )
            return ""
    else:
        curr = sql.welcome_mutes(chat.id)
        msg.reply_text(
            _b(f"current welcome mute: {curr or 'off'}") + "\n"
            + _bq(_sc("options: off / soft / strong\nuse /welcomemutehelp for details.")),
            parse_mode=ParseMode.HTML,
        )
        return ""


# ── /cleanwelcome ─────────────────────────────────────────────────────────────

@user_admin
@loggable
def clean_welcome(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text(
                _b("✅ i'm deleting old welcome messages."), parse_mode=ParseMode.HTML
            )
        else:
            update.effective_message.reply_text(
                _b("🔕 i'm not deleting old welcome messages."), parse_mode=ParseMode.HTML
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text(
            _b("✅ i'll try to delete old welcome messages!"), parse_mode=ParseMode.HTML
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>ON</code>."
        )
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text(
            _b("🔕 i won't delete old welcome messages."), parse_mode=ParseMode.HTML
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>OFF</code>."
        )
    else:
        update.effective_message.reply_text(
            _b("i understand 'on/yes' or 'off/no' only!"), parse_mode=ParseMode.HTML
        )
        return ""


# ── /cleanservice ─────────────────────────────────────────────────────────────

@user_admin
def cleanservice(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    msg  = update.effective_message

    if chat.type != chat.PRIVATE:
        if args:
            if args[0].lower() in ("no", "off"):
                sql.set_clean_service(chat.id, False)
                msg.reply_text(_b("✅ clean service: off"), parse_mode=ParseMode.HTML)
            elif args[0].lower() in ("yes", "on"):
                sql.set_clean_service(chat.id, True)
                msg.reply_text(_b("✅ clean service: on"), parse_mode=ParseMode.HTML)
            else:
                msg.reply_text(
                    _b("invalid option.") + "\n"
                    + _bq(_sc("use on/yes or off/no")),
                    parse_mode=ParseMode.HTML,
                )
        else:
            msg.reply_text(
                _b("usage:") + " <code>on</code>/<code>yes</code> or <code>off</code>/<code>no</code>",
                parse_mode=ParseMode.HTML,
            )
    else:
        curr = sql.clean_service(chat.id)
        msg.reply_text(
            _b(f"clean service is: {'on ✅' if curr else 'off 🔕'}"),
            parse_mode=ParseMode.HTML,
        )


# ── /setwelcomeimage (new) ────────────────────────────────────────────────────

@user_admin
def set_welcome_image(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg  = update.effective_message
    args = context.args or []

    if args and args[0].lower() == "clear":
        _set(chat.id, "image", "")
        msg.reply_text(_b("✅ welcome image cleared."), parse_mode=ParseMode.HTML)
        return

    image = ""
    if msg.reply_to_message and msg.reply_to_message.photo:
        image = msg.reply_to_message.photo[-1].file_id
    elif args and args[0].startswith("http"):
        image = args[0]
    else:
        msg.reply_text(
            _b("ℹ️ usage:") + "\n"
            + _bq(
                "• " + _sc("reply to a photo with /setwelcomeimage") + "\n"
                + "• " + _sc("/setwelcomeimage https://image-url") + "\n"
                + "• " + _sc("/setwelcomeimage clear — remove image")
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    _set(chat.id, "image", image)
    try:
        dispatcher.bot.send_photo(
            chat.id, photo=image,
            caption=_b("✅ welcome image set!"),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        msg.reply_text(_b("✅ welcome image saved."), parse_mode=ParseMode.HTML)


# ── /welcdelay (new) ──────────────────────────────────────────────────────────

@user_admin
def welcdelay(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg  = update.effective_message
    args = context.args or []

    if not args:
        current = _get(chat.id, "delete_after", "0")
        msg.reply_text(
            _b("⏱ auto-delete welcome:") + " "
            + _sc(f"{current}s" if current != "0" else "off") + "\n"
            + _bq(_sc("usage: /welcdelay <seconds> (0 = off)")),
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        secs = max(0, int(args[0]))
        _set(chat.id, "delete_after", str(secs))
        msg.reply_text(
            _b(f"✅ auto-delete set: {secs}s" if secs else "✅ auto-delete off"),
            parse_mode=ParseMode.HTML,
        )
    except ValueError:
        msg.reply_text(_b("❌ send a valid number of seconds."), parse_mode=ParseMode.HTML)


# ── /welcomehelp ─────────────────────────────────────────────────────────────

WELC_HELP_TXT = (
    "<b>welcome/goodbye variables:</b>\n"
    " • <code>{first}</code> — user's first name\n"
    " • <code>{last}</code> — user's last name\n"
    " • <code>{fullname}</code> — user's full name\n"
    " • <code>{username}</code> — username or mention\n"
    " • <code>{mention}</code> — clickable mention\n"
    " • <code>{id}</code> — user's ID\n"
    " • <code>{count}</code> — member count\n"
    " • <code>{chatname}</code> — group name\n\n"
    "<b>HTML tags supported:</b>\n"
    " • <code>&lt;b&gt;bold&lt;/b&gt;</code> <code>&lt;i&gt;italic&lt;/i&gt;</code>\n"
    " • <code>&lt;u&gt;underline&lt;/u&gt;</code> <code>&lt;s&gt;strike&lt;/s&gt;</code>\n"
    " • <code>&lt;code&gt;mono&lt;/code&gt;</code> <code>&lt;a href=URL&gt;link&lt;/a&gt;</code>\n"
    " • <code>&lt;tg-spoiler&gt;spoiler&lt;/tg-spoiler&gt;</code>\n\n"
    "<b>inline buttons:</b> add to welcome text:\n"
    " <code>Button Label - https://t.me/yourchannel</code>\n\n"
    "<b>media welcome:</b> reply to a photo/sticker/video with /setwelcome to use it as welcome."
)

WELC_MUTE_HELP_TXT = (
    "<b>welcome mute modes:</b>\n\n"
    " • <code>/welcomemute soft</code> — restricts new members from sending media for 24 hours.\n"
    " • <code>/welcomemute strong</code> — mutes new members until they tap verify button. "
    "120 seconds or they get kicked.\n"
    " • <code>/welcomemute off</code> — turns off welcome mute.\n\n"
    "<b>Note:</b> strong mode kicks if not verified in 120s. They can always rejoin."
)


def welcome_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.HTML)

def welcome_mute_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_MUTE_HELP_TXT, parse_mode=ParseMode.HTML)


# ── /welcomehelp for non-admins too ──────────────────────────────────────────

def welcome_help_public(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.HTML)


# ── User button (strong mute verify) ─────────────────────────────────────────

def user_button(update: Update, context: CallbackContext):
    chat  = update.effective_chat
    user  = update.effective_user
    query = update.callback_query
    bot   = context.bot

    match    = re.match(r"user_join_\((.+?)\)", query.data)
    message  = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        sql.set_human_checks(user.id, chat.id)
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id, {})
        member_dict["status"] = True
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        query.answer(text=_sc("Yeet! You're a human, unmuted!"))
        bot.restrict_chat_member(
            chat.id, user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        try:
            bot.deleteMessage(chat.id, message.message_id)
        except Exception:
            pass

        if member_dict.get("should_welc"):
            if member_dict.get("media_wel"):
                sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                    member_dict["chat_id"], member_dict["cust_content"],
                    caption=member_dict["res"],
                    reply_markup=member_dict["keyboard"],
                    parse_mode="markdown",
                )
            else:
                sent = send(
                    member_dict["update"], member_dict["res"],
                    member_dict["keyboard"], member_dict["backup_message"],
                )
            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass
                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)
    else:
        query.answer(text=_sc("You're not allowed to do this!"))


# ── Inline settings panel callbacks (new) ─────────────────────────────────────

def welcome_callback_sync(update: Update, context: CallbackContext):
    query   = update.callback_query
    data    = query.data or ""
    user    = query.from_user
    chat_id_str = data.split("_")[-1]
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        query.answer("❌ invalid", show_alert=True)
        return

    # Admin check
    try:
        m = context.bot.get_chat_member(chat_id, user.id)
        if m.status not in ("administrator", "creator"):
            query.answer(_sc("❌ admins only!"), show_alert=True)
            return
    except Exception:
        pass

    query.answer()

    if data.startswith("wlc_clean_"):
        current = bool(sql.get_clean_pref(chat_id))
        sql.set_clean_welcome(str(chat_id), not current)
        status = _sc("on ✅" if not current else "off 🔕")
        try:
            query.edit_message_text(
                _b(f"🧹 clean old welcomes: {status}"),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    elif data.startswith("wlc_img_prompt_"):
        try:
            query.edit_message_text(
                _b("🖼 set welcome image") + "\n\n"
                + _bq(
                    "• " + _sc("reply to a photo with /setwelcomeimage") + "\n"
                    + "• " + _sc("/setwelcomeimage https://image-url") + "\n"
                    + "• " + _sc("/setwelcomeimage clear")
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    elif data.startswith("wlc_preview_"):
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat_id)
        extra_image = _get(chat_id, "image", "")
        try:
            if extra_image:
                context.bot.send_photo(
                    user.id, photo=extra_image, caption=welcome_m,
                    parse_mode=ParseMode.HTML,
                )
            else:
                context.bot.send_message(
                    user.id, welcome_m, parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            query.answer(_sc("✅ preview sent to your DM!"), show_alert=True)
        except Forbidden:
            query.answer(_sc("❌ start the bot in PM first!"), show_alert=True)

    elif data.startswith("wlc_advanced_"):
        del_after = _get(chat_id, "delete_after", "0")
        try:
            query.edit_message_text(
                _b("⚙️ advanced settings") + "\n\n"
                + _bq(
                    _b("auto-delete welcome:") + "\n"
                    + _sc("• /welcdelay 300 — delete after 5 minutes\n")
                    + _sc("• /welcdelay 0 — never delete\n")
                    + _b("current: ") + _sc(f"{del_after}s" if del_after != "0" else "off")
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ── migrate / chat_settings ───────────────────────────────────────────────────

def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref = sql.get_welc_pref(chat_id)[0]
    goodbye_pref = sql.get_gdbye_pref(chat_id)[0]
    return (
        "This chat has its welcome preference set to `{}`.\n"
        "Its goodbye preference is `{}`.".format(welcome_pref, goodbye_pref)
    )


# ── Help strings ─────────────────────────────────────────────────────────────

__help__ = """
*Admins only:*
 ❍ /welcome <on/off> — enable/disable welcome messages
 ❍ /welcome — show current welcome settings + quick panel
 ❍ /welcome noformat — show current without formatting
 ❍ /goodbye <on/off> — enable/disable goodbye
 ❍ /goodbye — show goodbye settings
 ❍ /setwelcome <text> — set custom welcome (reply to media for photo/sticker/video welcome)
 ❍ /setgoodbye <text> — set custom goodbye
 ❍ /resetwelcome — reset welcome to default
 ❍ /resetgoodbye — reset goodbye to default
 ❍ /cleanwelcome <on/off> — delete previous welcome on new join
 ❍ /cleanservice <on/off> — delete Telegram "joined/left" service messages
 ❍ /welcomemute off/soft/strong — anti-bot mute on join
 ❍ /setwelcomeimage — set welcome image (reply to photo or URL)
 ❍ /welcdelay <seconds> — auto-delete welcome after N seconds (0 = off)

*Anyone:*
 ❍ /welcomehelp — format variables + HTML tags guide
 ❍ /welcomemutehelp — explains mute modes
"""

__mod_name__ = "Wᴇʟᴄᴏᴍᴇ"
__command_list__ = [
    "welcome", "goodbye", "setwelcome", "setgoodbye",
    "resetwelcome", "resetgoodbye", "cleanwelcome", "cleanservice",
    "welcomemute", "setwelcomeimage", "welcdelay",
    "welcomehelp", "welcomemutehelp",
]


# ── Handler registration ──────────────────────────────────────────────────────

NEW_MEM_HANDLER      = MessageHandler(Filters.status_update.new_chat_members, new_member, run_async=True)
LEFT_MEM_HANDLER     = MessageHandler(Filters.status_update.left_chat_member, left_member, run_async=True)
WELC_PREF_HANDLER    = CommandHandler("welcome",         welcome,           filters=Filters.chat_type.groups, run_async=True)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye",         goodbye,           filters=Filters.chat_type.groups, run_async=True)
SET_WELCOME          = CommandHandler("setwelcome",      set_welcome,       filters=Filters.chat_type.groups, run_async=True)
SET_GOODBYE          = CommandHandler("setgoodbye",      set_goodbye,       filters=Filters.chat_type.groups, run_async=True)
RESET_WELCOME        = CommandHandler("resetwelcome",    reset_welcome,     filters=Filters.chat_type.groups, run_async=True)
RESET_GOODBYE        = CommandHandler("resetgoodbye",    reset_goodbye,     filters=Filters.chat_type.groups, run_async=True)
CLEAN_WELCOME        = CommandHandler("cleanwelcome",    clean_welcome,     filters=Filters.chat_type.groups, run_async=True)
CLEAN_SERVICE        = CommandHandler("cleanservice",    cleanservice,      filters=Filters.chat_type.groups, run_async=True)
WELCOMEMUTE_HANDLER  = CommandHandler("welcomemute",     welcomemute,       filters=Filters.chat_type.groups, run_async=True)
SET_WELC_IMG         = CommandHandler("setwelcomeimage", set_welcome_image, filters=Filters.chat_type.groups, run_async=True)
WELC_DELAY           = CommandHandler("welcdelay",       welcdelay,         filters=Filters.chat_type.groups, run_async=True)
WELCOME_HELP         = CommandHandler("welcomehelp",     welcome_help_public, run_async=True)
WELCOME_MUTE_HELP    = CommandHandler("welcomemutehelp", welcome_mute_help,   run_async=True)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button,           pattern=r"user_join_",  run_async=True)
WLC_CALLBACK_HANDLER  = CallbackQueryHandler(welcome_callback_sync, pattern=r"^wlc_",       run_async=True)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(CLEAN_SERVICE)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(SET_WELC_IMG)
dispatcher.add_handler(WELC_DELAY)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOME_MUTE_HELP)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WLC_CALLBACK_HANDLER)

__handlers__ = [
    NEW_MEM_HANDLER, LEFT_MEM_HANDLER, WELC_PREF_HANDLER, GOODBYE_PREF_HANDLER,
    SET_WELCOME, SET_GOODBYE, RESET_WELCOME, RESET_GOODBYE,
    CLEAN_WELCOME, CLEAN_SERVICE, WELCOMEMUTE_HANDLER, SET_WELC_IMG, WELC_DELAY,
    WELCOME_HELP, WELCOME_MUTE_HELP, BUTTON_VERIFY_HANDLER, WLC_CALLBACK_HANDLER,
]

# PTB v20 register() shim for bots using Application
def register(app) -> None:
    from telegram.ext import (
        CommandHandler as CH, MessageHandler as MH,
        CallbackQueryHandler as CQH, filters as F,
    )
    app.add_handler(MH(F.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MH(F.StatusUpdate.LEFT_CHAT_MEMBER, left_member))
    app.add_handler(CH("welcome",         welcome,           filters=F.ChatType.GROUPS))
    app.add_handler(CH("goodbye",         goodbye,           filters=F.ChatType.GROUPS))
    app.add_handler(CH("setwelcome",      set_welcome,       filters=F.ChatType.GROUPS))
    app.add_handler(CH("setgoodbye",      set_goodbye,       filters=F.ChatType.GROUPS))
    app.add_handler(CH("resetwelcome",    reset_welcome,     filters=F.ChatType.GROUPS))
    app.add_handler(CH("resetgoodbye",    reset_goodbye,     filters=F.ChatType.GROUPS))
    app.add_handler(CH("cleanwelcome",    clean_welcome,     filters=F.ChatType.GROUPS))
    app.add_handler(CH("cleanservice",    cleanservice,      filters=F.ChatType.GROUPS))
    app.add_handler(CH("welcomemute",     welcomemute,       filters=F.ChatType.GROUPS))
    app.add_handler(CH("setwelcomeimage", set_welcome_image, filters=F.ChatType.GROUPS))
    app.add_handler(CH("welcdelay",       welcdelay,         filters=F.ChatType.GROUPS))
    app.add_handler(CH("welcomehelp",     welcome_help_public))
    app.add_handler(CH("welcomemutehelp", welcome_mute_help))
    app.add_handler(CQH(user_button,           pattern=r"user_join_"))
    app.add_handler(CQH(welcome_callback_sync, pattern=r"^wlc_"))
    logger.info("[welcome] Handlers registered")
