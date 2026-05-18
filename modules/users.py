# ====================================================================
# PLACE AT: /app/modules/users.py
# ACTION: Replace existing file
# ====================================================================
"""
users.py — PTB v20 async.
Fixes:
  ✅ All handlers async + await
  ✅ asyncio.sleep instead of time.sleep
  ✅ filters from telegram.ext.filters (PTB v20)
  ✅ await context.bot.send_message / get_chat / get_member_count
  ✅ await reply_document / chat.get_member
"""
import asyncio
from io import BytesIO

from telegram import TelegramError, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

import modules.sql.users_sql as sql
from beataniversebot_compat import DEV_USERS, LOGGER, OWNER_ID, dispatcher
from modules.helper_funcs.chat_status import dev_plus, sudo_plus
from modules.sql.users_sql import get_all_users

USERS_GROUP = 4
CHAT_GROUP  = 5

_DEV_AND_MORE = list(DEV_USERS) + [int(OWNER_ID)]


def get_user_id(username: str):
    if len(username) <= 5:
        return None

    if username.startswith("@"):
        username = username[1:]

    users = sql.get_userid_by_name(username)
    if not users:
        return None
    if len(users) == 1:
        return users[0].user_id

    for user_obj in users:
        try:
            # Use synchronous bot reference (pre-start lookup) with care
            import asyncio as _asyncio
            loop = None
            try:
                loop = _asyncio.get_running_loop()
            except RuntimeError:
                pass
            if loop:
                # can't await here — return first match
                return user_obj.user_id
            userdat = dispatcher.bot.get_chat(user_obj.user_id)
            if userdat.username == username:
                return userdat.id
        except BadRequest as excp:
            if excp.message != "Chat not found":
                LOGGER.exception("Error extracting user ID")
    return None


@dev_plus
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    to_send = update.effective_message.text.split(None, 1)
    if len(to_send) < 2:
        return

    cmd       = to_send[0]
    text      = to_send[1]
    to_group  = cmd in ("/broadcast", "/broadcastall", "/broadcastgroups")
    to_user   = cmd in ("/broadcast", "/broadcastall", "/broadcastusers")

    chats_all = sql.get_all_chats() or []
    users_all = get_all_users()
    failed = failed_user = 0

    if to_group:
        for chat in chats_all:
            try:
                await context.bot.send_message(
                    int(chat.chat_id), text,
                    parse_mode="MARKDOWN",
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.1)
            except TelegramError:
                failed += 1

    if to_user:
        for user in users_all:
            try:
                await context.bot.send_message(
                    int(user.user_id), text,
                    parse_mode="MARKDOWN",
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.1)
            except TelegramError:
                failed_user += 1

    await update.effective_message.reply_text(
        f"Broadcast complete.\nGroups failed: {failed}.\nUsers failed: {failed_user}."
    )


async def log_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg  = update.effective_message

    if msg.from_user:
        sql.update_user(msg.from_user.id, msg.from_user.username, chat.id, chat.title)

    if msg.reply_to_message and msg.reply_to_message.from_user:
        sql.update_user(
            msg.reply_to_message.from_user.id,
            msg.reply_to_message.from_user.username,
            chat.id,
            chat.title,
        )

    if msg.forward_from:
        sql.update_user(msg.forward_from.id, msg.forward_from.username)


@sudo_plus
async def chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    all_chats = sql.get_all_chats() or []
    chatfile  = "List of chats.\n0. Chat name | Chat ID | Members\n"
    idx       = 1
    for chat in all_chats:
        try:
            curr_chat    = await context.bot.get_chat(chat.chat_id)
            chat_members = await curr_chat.get_member_count()
            chatfile    += f"{idx}. {chat.chat_name} | {chat.chat_id} | {chat_members}\n"
            idx          += 1
        except Exception:
            pass

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "groups_list.txt"
        await update.effective_message.reply_document(
            document=output,
            filename="groups_list.txt",
            caption="Here be the list of groups in my database.",
        )


async def chat_checker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    try:
        member = await update.effective_message.chat.get_member(bot.id)
        if member.can_send_messages is False:
            await bot.leave_chat(update.effective_message.chat.id)
    except Unauthorized:
        pass
    except Exception:
        pass


def __user_info__(user_id):
    if user_id in [777000, 1087968824]:
        return "<b>➻ ᴄᴏᴍᴍᴏɴ ᴄʜᴀᴛs:</b> <code>???</code>"
    if user_id == dispatcher.bot.id:
        return "<b>➻ ᴄᴏᴍᴍᴏɴ ᴄʜᴀᴛs:</b> <code>???</code>"
    num_chats = sql.get_user_num_chats(user_id)
    return f"<b>➻ ᴄᴏᴍᴍᴏɴ ᴄʜᴀᴛs:</b> <code>{num_chats}</code>"


def __stats__():
    return f"• {sql.num_users()} users, across {sql.num_chats()} chats"


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


__help__ = ""

BROADCAST_HANDLER    = CommandHandler(
    ["broadcastall", "broadcastusers", "broadcastgroups", "broadcast"], broadcast
)
USER_HANDLER         = MessageHandler(filters.ALL & filters.ChatType.GROUPS, log_user)
CHAT_CHECKER_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, chat_checker)
CHATLIST_HANDLER     = CommandHandler("groups", chats)

dispatcher.add_handler(USER_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)

__mod_name__ = "Users"
__handlers__ = [(USER_HANDLER, USERS_GROUP), BROADCAST_HANDLER, CHATLIST_HANDLER]
