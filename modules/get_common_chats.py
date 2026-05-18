# ====================================================================
# PLACE AT: /app/modules/get_common_chats.py
# ACTION: Replace existing file
# ====================================================================
"""get_common_chats.py — PTB v20 async. Non-blocking API calls with await."""
import asyncio
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter, Unauthorized
from telegram.ext import CommandHandler, ContextTypes, filters

from beataniversebot_compat import OWNER_ID, dispatcher
from modules.helper_funcs.extraction import extract_user
from modules.sql.users_sql import get_user_com_chats


async def get_user_common_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot  = context.bot
    msg  = update.effective_message
    user = extract_user(msg, context.args)

    if not user:
        await msg.reply_text("I share no common chats with the void.")
        return

    common_list = get_user_com_chats(user)
    if not common_list:
        await msg.reply_text("No common chats with this user!")
        return

    try:
        chat_info = await bot.get_chat(user)
        name      = chat_info.first_name or str(user)
    except Exception:
        name = str(user)

    text = f"<b>Common chats with {name}</b>\n"
    for chat in common_list:
        try:
            chat_obj  = await bot.get_chat(chat)
            text     += f"• <code>{chat_obj.title}</code>\n"
            await asyncio.sleep(0.3)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except (BadRequest, Unauthorized):
            pass

    if len(text) < 4096:
        await msg.reply_text(text, parse_mode=ParseMode.HTML)
    else:
        fname = "common_chats.txt"
        with open(fname, "w") as f:
            f.write(text)
        with open(fname, "rb") as f:
            await msg.reply_document(f)
        try:
            os.remove(fname)
        except Exception:
            pass


COMMON_CHATS_HANDLER = CommandHandler(
    "getchats",
    get_user_common_chats,
    filters=filters.User(OWNER_ID),
)
dispatcher.add_handler(COMMON_CHATS_HANDLER)
