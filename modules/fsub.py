# ====================================================================
# PLACE AT: /app/modules/fsub.py
# ACTION: Replace existing file
# ====================================================================
"""
Force Subscription Module for BeatVerseProbot
Admins can add/remove/list force-sub channels stored in PostgreSQL.
"""
import threading

from sqlalchemy import BigInteger, Column, String
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext

from beataniversebot_compat import dispatcher, DRAGONS
from modules.sql import BASE, SESSION
from modules.helper_funcs.chat_status import user_admin
from modules.disable import DisableAbleCommandHandler


# ── SQL Model ──────────────────────────────────────────────────────────────────

class FSubChannel(BASE):
    __tablename__ = "fsub_channels"
    channel_id = Column(String(14), primary_key=True)

    def __init__(self, channel_id):
        self.channel_id = str(channel_id)

    def __repr__(self):
        return f"<FSubChannel {self.channel_id}>"


FSubChannel.__table__.create(checkfirst=True)
FSUB_LOCK = threading.RLock()


# ── SQL helpers ────────────────────────────────────────────────────────────────

def add_fsub_channel(channel_id: int) -> bool:
    with FSUB_LOCK:
        existing = SESSION.query(FSubChannel).get(str(channel_id))
        if existing:
            SESSION.close()
            return False
        ch = FSubChannel(str(channel_id))
        SESSION.add(ch)
        SESSION.commit()
        return True


def remove_fsub_channel(channel_id: int) -> bool:
    with FSUB_LOCK:
        ch = SESSION.query(FSubChannel).get(str(channel_id))
        if ch:
            SESSION.delete(ch)
            SESSION.commit()
            return True
        SESSION.close()
        return False


def get_fsub_channels() -> list:
    try:
        return [int(c.channel_id) for c in SESSION.query(FSubChannel).all()]
    finally:
        SESSION.close()


# ── Command handlers ───────────────────────────────────────────────────────────

@user_admin
def addfsub(update: Update, context: CallbackContext):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    # Only group admins + dragons can use this
    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can add FSub channels!")

    if not args:
        return message.reply_text(
            "Usage: `/addfsub <channel_id>`\nExample: `/addfsub -1001234567890`",
            parse_mode=ParseMode.HTML,
        )

    try:
        channel_id = int(args[0])
    except ValueError:
        return message.reply_text("❌ Invalid channel ID. Must be a number.")

    try:
        chat_info = context.bot.get_chat(channel_id)
        bot_member = context.bot.get_chat_member(channel_id, context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return message.reply_text(
                f"❌ I must be an admin in *{chat_info.title}* to add it as an FSub channel.",
                parse_mode=ParseMode.HTML,
            )

        success = add_fsub_channel(channel_id)
        if success:
            message.reply_text(
                f"✅ *Force Subscription Added*\n\n"
                f"Channel: *{chat_info.title}*\n"
                f"ID: `{channel_id}`\n\n"
                f"Users must now join this channel to use the bot.",
                parse_mode=ParseMode.HTML,
            )
        else:
            message.reply_text(
                f"⚠️ Channel *{chat_info.title}* is already in the FSub list.",
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        message.reply_text(
            f"❌ Error: `{str(e)}`\n\nMake sure the channel ID is correct and I'm a member.",
            parse_mode=ParseMode.HTML,
        )


@user_admin
def delfsub(update: Update, context: CallbackContext):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    args = context.args

    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can remove FSub channels!")

    if not args:
        return message.reply_text(
            "Usage: `/delfsub <channel_id>`",
            parse_mode=ParseMode.HTML,
        )

    try:
        channel_id = int(args[0])
    except ValueError:
        return message.reply_text("❌ Invalid channel ID.")

    if remove_fsub_channel(channel_id):
        message.reply_text(
            f"✅ Removed channel `{channel_id}` from Force Subscription list.",
            parse_mode=ParseMode.HTML,
        )
    else:
        message.reply_text(
            f"❌ Channel `{channel_id}` not found in FSub list.",
            parse_mode=ParseMode.HTML,
        )


def fsublist(update: Update, context: CallbackContext):
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can view the FSub list!")

    channels = get_fsub_channels()

    if not channels:
        return message.reply_text(
            "📋 No Force Subscription channels configured.\n\n"
            "Use `/addfsub <channel_id>` to add channels.",
            parse_mode=ParseMode.HTML,
        )

    text = "📋 *Force Subscription Channels:*\n\n"
    for i, channel_id in enumerate(channels, 1):
        try:
            chat_info = context.bot.get_chat(channel_id)
            link = (
                f"https://t.me/{chat_info.username}"
                if chat_info.username
                else "Private Channel"
            )
            text += f"*{i}. {chat_info.title}*\n"
            text += f"   ➥ ID: `{channel_id}`\n"
            text += f"   ➥ Link: {link}\n\n"
        except Exception as e:
            text += f"*{i}.* `{channel_id}` (Error: {e})\n\n"

    message.reply_text(text, parse_mode=ParseMode.HTML)


def check_fsub(update: Update, context: CallbackContext) -> bool:
    """
    Returns True if user has joined all FSub channels.
    Call this at the start of handlers that require FSub.
    """
    channels = get_fsub_channels()
    if not channels:
        return True

    user_id = update.effective_user.id
    not_joined = []

    for channel_id in channels:
        try:
            member = context.bot.get_chat_member(channel_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(channel_id)
        except Exception:
            not_joined.append(channel_id)

    if not not_joined:
        return True

    # Build join buttons
    buttons = []
    for channel_id in not_joined:
        try:
            chat_info = context.bot.get_chat(channel_id)
            if chat_info.username:
                link = f"https://t.me/{chat_info.username}"
            else:
                link = context.bot.export_chat_invite_link(channel_id)
            buttons.append([InlineKeyboardButton(f"📢 {chat_info.title}", url=link)])
        except Exception:
            pass

    if buttons:
        update.effective_message.reply_text(
            "❗ *You must join the following channels to use this bot:*",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    return False


ADDFSUB_HANDLER = DisableAbleCommandHandler("addfsub", addfsub, run_async=True)
DELFSUB_HANDLER = DisableAbleCommandHandler("delfsub", delfsub, run_async=True)
FSUBLIST_HANDLER = DisableAbleCommandHandler("fsublist", fsublist, run_async=True)

dispatcher.add_handler(ADDFSUB_HANDLER)
dispatcher.add_handler(DELFSUB_HANDLER)
dispatcher.add_handler(FSUBLIST_HANDLER)

__mod_name__ = "ForceSub"
__command_list__ = ["addfsub", "delfsub", "fsublist"]
__handlers__ = [ADDFSUB_HANDLER, DELFSUB_HANDLER, FSUBLIST_HANDLER]
__help__ = """
*Force Subscription (Admin only):*

 • `/addfsub <channel_id>`*:* add a channel to force-sub list
 • `/delfsub <channel_id>`*:* remove a channel from force-sub list
 • `/fsublist`*:* view all force-sub channels
"""
