import logging
logger = logging.getLogger(__name__)
# ====================================================================
# PLACE AT: /app/modules/chatbot.py
# ACTION: Replace existing file
# ====================================================================
from typing import Optional
import html
import json
import re
from time import sleep

import requests
from telegram import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
    User,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
)
try:
    from telegram.ext import filters as Filters
    # PTB v21: Filters.text → filters.TEXT, etc.
    _F = Filters
except ImportError:
    from telegram.ext import Filters
    _F = Filters
from telegram.utils.helpers import mention_html

import modules.sql.chatbot_sql as sql
from beataniversebot_compat import BOT_ID, BOT_NAME, BOT_USERNAME, dispatcher
from modules.helper_funcs.chat_status import user_admin, user_admin_no_reply
from modules.log_channel import gloggable


@user_admin_no_reply
@gloggable
def beatrm(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"rm_chat\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        is_active = sql.disable_chatbot(chat.id)
        if is_active:
            is_active = sql.disable_chatbot(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"AI_DISABLED\n"
                f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            )
        else:
            update.effective_message.edit_text(
                "{} ᴄʜᴀᴛʙᴏᴛ ᴅɪsᴀʙʟᴇᴅ ʙʏ {}.".format(
                    dispatcher.bot.first_name, mention_html(user.id, user.first_name)
                ),
                parse_mode=ParseMode.HTML,
            )

    return ""


@user_admin_no_reply
@gloggable
def beatadd(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    match = re.match(r"add_chat\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        is_active = sql.enable_chatbot(chat.id)
        if is_active:
            is_active = sql.enable_chatbot(user_id)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"AI_ENABLE\n"
                f"<b>Admin :</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            )
        else:
            update.effective_message.edit_text(
                "{} ᴄʜᴀᴛʙᴏᴛ ᴇɴᴀʙʟᴇᴅ ʙʏ {}.".format(
                    dispatcher.bot.first_name, mention_html(user.id, user.first_name)
                ),
                parse_mode=ParseMode.HTML,
            )

    return ""


@user_admin
@gloggable
def chatbot_panel(update: Update, context: CallbackContext):
    message = update.effective_message
    msg = "• ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴩᴛɪᴏɴ ᴛᴏ ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ ᴄʜᴀᴛʙᴏᴛ"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="ᴇɴᴀʙʟᴇ", callback_data="add_chat({})"),
                InlineKeyboardButton(text="ᴅɪsᴀʙʟᴇ", callback_data="rm_chat({})"),
            ],
        ]
    )
    message.reply_text(
        text=msg,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


def beat_message(context: CallbackContext, message):
    reply_message = message.reply_to_message
    if message.text.lower() == "beatverse":
        return True
    elif BOT_USERNAME in message.text:
        return True
    elif reply_message:
        if reply_message.from_user.id == BOT_ID:
            return True
    else:
        return False


# Conversation history per chat for context-aware chatbot
_chatbot_history: dict = {}
_CHATBOT_MAX_HISTORY = 10  # Keep last 10 exchanges per chat

def _get_chatbot_reply(message_text: str, chat_id: int, bot_name: str) -> str:
    """
    Get chatbot reply using Anthropic API (real human-like response).
    Falls back to a hardcoded reply if API unavailable.
    """
    import os
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    # Maintain per-chat conversation history
    history = _chatbot_history.get(chat_id, [])
    history.append({"role": "user", "content": message_text})
    if len(history) > _CHATBOT_MAX_HISTORY * 2:
        history = history[-(_CHATBOT_MAX_HISTORY * 2):]
    _chatbot_history[chat_id] = history

    if anthropic_key:
        try:
            api_resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 200,
                    "system": (
                        f"You are {bot_name}, a friendly anime-loving Telegram bot assistant. "
                        "You respond in short, casual, friendly messages (1-3 sentences). "
                        "You love anime, manga, and Japanese culture. "
                        "Never break character. Respond in the same language as the user."
                    ),
                    "messages": history,
                },
                timeout=8,
            )
            if api_resp.status_code == 200:
                reply = api_resp.json()["content"][0]["text"].strip()
                # Add assistant reply to history
                history.append({"role": "assistant", "content": reply})
                _chatbot_history[chat_id] = history
                return reply
        except Exception as exc:
            logger.debug(f"[chatbot] Anthropic API: {exc}")

    # Fallback: simple keyword-based replies (no external API needed)
    text_lower = message_text.lower()
    if any(w in text_lower for w in ["hello", "hi", "hey", "namaste", "helo"]):
        return f"Hey there! 👋 I'm {bot_name}! Ask me about anime, use /anime to get posters!"
    if any(w in text_lower for w in ["anime", "manga", "watch"]):
        return "Great taste! Try /anime <name> to get a poster. My fav is Demon Slayer! 🗡️"
    if any(w in text_lower for w in ["help", "commands", "cmd"]):
        return "Use /cmd to see all my commands, or /anime <name> to search anime! 🎌"
    if any(w in text_lower for w in ["thanks", "thank you", "thx", "ty"]):
        return "You're welcome! 😊 Anything else I can help with?"
    if "?" in message_text:
        return "Hmm, that's a good question! Try /help for more info. 🤔"
    return "Interesting! Tell me more or try /anime for some anime magic! ✨"


def chatbot(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_id = update.effective_chat.id
    bot = context.bot
    is_active = sql.is_chatbot_active(chat_id)
    if is_active:
        return

    if message.text and not message.document:
        if not beat_message(context, message):
            return
        try:
            bot.send_chat_action(chat_id, action="typing")
            reply_text = _get_chatbot_reply(
                message.text, chat_id,
                getattr(bot, "first_name", BOT_NAME) or BOT_NAME
            )
            if reply_text:
                sleep(0.3)
                message.reply_text(reply_text)
        except Exception as exc:
            logger.debug(f"[chatbot] send error: {exc}")


__help__ = f"""
*{BOT_NAME} has an chatbot which provides you a seemingless chatting experience :*

 »  /chatbot *:* Shows chatbot control panel
"""

__mod_name__ = "Cʜᴀᴛʙᴏᴛ"


CHATBOTK_HANDLER = CommandHandler("chatbot", chatbot_panel, run_async=True)
ADD_CHAT_HANDLER = CallbackQueryHandler(beatadd, pattern=r"add_chat", run_async=True)
RM_CHAT_HANDLER = CallbackQueryHandler(beatrm, pattern=r"rm_chat", run_async=True)
try:
    # PTB v21 filters
    from telegram.ext import filters as _F21
    _chatbot_filter = (
        _F21.TEXT
        & ~_F21.Regex(r"^#[^\s]+")
        & ~_F21.Regex(r"^!")
        & ~_F21.Regex(r"^\/")
    )
except Exception:
    # PTB v13 fallback
    _chatbot_filter = (
        Filters.text
        & (~Filters.regex(r"^#[^\s]+") & ~Filters.regex(r"^!") & ~Filters.regex(r"^\/"))
    )

CHATBOT_HANDLER = MessageHandler(_chatbot_filter, chatbot, run_async=True)

dispatcher.add_handler(ADD_CHAT_HANDLER)
dispatcher.add_handler(CHATBOTK_HANDLER)
dispatcher.add_handler(RM_CHAT_HANDLER)
dispatcher.add_handler(CHATBOT_HANDLER)

__handlers__ = [
    ADD_CHAT_HANDLER,
    CHATBOTK_HANDLER,
    RM_CHAT_HANDLER,
    CHATBOT_HANDLER,
]
