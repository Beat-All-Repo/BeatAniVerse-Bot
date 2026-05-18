# ====================================================================
# PLACE AT: /app/modules/afk.py
# ACTION: Replace existing file
# ====================================================================
"""
afk.py — PTB v20 async.
Fixes:
  ✅ All handlers async
  ✅ await on all Telegram API calls (reply_text, bot.get_chat)
  ✅ filters from telegram.ext.filters (PTB v20) not telegram.ext.Filters
  ✅ bot.get_chat → await context.bot.get_chat
  ✅ ParseMode from telegram.constants
"""
import html
import random

from telegram import MessageEntity, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes, MessageHandler, filters

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler, DisableAbleMessageHandler
from modules.sql import afk_sql as sql
from modules.users import get_user_id

AFK_GROUP       = 7
AFK_REPLY_GROUP = 8


async def afk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args    = update.effective_message.text.split(None, 1)
    user    = update.effective_user
    message = update.effective_message

    if not user or user.id in [777000, 1087968824]:
        return

    notice = ""
    if len(args) >= 2:
        reason = args[1]
        if len(reason) > 100:
            reason = reason[:100]
            notice = "\n(Reason shortened to 100 chars.)"
    else:
        reason = ""

    sql.set_afk(user.id, reason)
    try:
        await message.reply_text(f"{html.escape(user.first_name)} is now away!{notice}")
    except BadRequest:
        pass


async def no_longer_afk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user    = update.effective_user
    message = update.effective_message

    if not user:
        return

    res = sql.rm_afk(user.id)
    if res:
        if message.new_chat_members:
            return
        options = [
            "{} is here!", "{} is back!", "{} is now in the chat!",
            "{} is awake!", "{} is back online!", "{} is finally here!",
            "Welcome back! {}", "Where is {}?\nIn the chat!",
        ]
        try:
            await message.reply_text(random.choice(options).format(html.escape(user.first_name)))
        except Exception:
            pass


async def reply_afk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message  = update.effective_message
    userc    = update.effective_user
    userc_id = userc.id if userc else 0

    if message.entities and message.parse_entities(
        [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]
    ):
        entities  = message.parse_entities(
            [MessageEntity.TEXT_MENTION, MessageEntity.MENTION]
        )
        chk_users = []
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id  = ent.user.id
                fst_name = ent.user.first_name
                if user_id in chk_users:
                    continue
                chk_users.append(user_id)
                await _check_afk(update, user_id, fst_name, userc_id)

            elif ent.type == MessageEntity.MENTION:
                user_id = get_user_id(
                    message.text[ent.offset: ent.offset + ent.length]
                )
                if not user_id or user_id in chk_users:
                    continue
                chk_users.append(user_id)
                try:
                    chat     = await context.bot.get_chat(user_id)
                    fst_name = chat.first_name
                except BadRequest:
                    continue
                await _check_afk(update, user_id, fst_name, userc_id)

    elif message.reply_to_message and message.reply_to_message.from_user:
        user_id  = message.reply_to_message.from_user.id
        fst_name = message.reply_to_message.from_user.first_name
        await _check_afk(update, user_id, fst_name, userc_id)


async def _check_afk(update: Update, user_id: int, fst_name: str, userc_id: int) -> None:
    if not sql.is_afk(user_id):
        return
    user = sql.check_afk_status(user_id)
    if int(userc_id) == int(user_id):
        return
    if not user.reason:
        await update.effective_message.reply_text(f"{html.escape(fst_name)} is afk.")
    else:
        await update.effective_message.reply_text(
            f"{html.escape(fst_name)} is afk.\n"
            f"Reason: <code>{html.escape(user.reason)}</code>",
            parse_mode=ParseMode.HTML,
        )


__help__ = """
*Away from Group*

 ❍ /afk <reason> — Mark yourself as AFK.
 ❍ brb <reason> — Same as /afk.

When AFK, any @mention of you will get an auto-reply.
"""

AFK_HANDLER       = DisableAbleCommandHandler("afk", afk, run_async=True)
AFK_REGEX_HANDLER = DisableAbleMessageHandler(
    filters.Regex(r"(?i)^brb(.*)$"), afk, friendly="afk", run_async=True
)
NO_AFK_HANDLER    = MessageHandler(filters.ALL & filters.ChatType.GROUPS, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(filters.ALL & filters.ChatType.GROUPS, reply_afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)

__mod_name__     = "Aꜰᴋ"
__command_list__ = ["afk"]
__handlers__     = [
    (AFK_HANDLER,       AFK_GROUP),
    (AFK_REGEX_HANDLER, AFK_GROUP),
    (NO_AFK_HANDLER,    AFK_GROUP),
    (AFK_REPLY_HANDLER, AFK_REPLY_GROUP),
]
