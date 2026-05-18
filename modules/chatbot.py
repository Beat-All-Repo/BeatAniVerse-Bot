# ====================================================================
# PLACE AT: /app/modules/chatbot.py
# ACTION: Replace existing file
# ====================================================================
"""
modules/chatbot.py
==================
Human-like chatbot powered by Anthropic Claude.

Chatbot modes:
  • "Trigger-only" (default, chat NOT in enabled table):
    Replies only when @mentioned, replied-to, or "beatverse" keyword used.
  • "Full mode" (admin runs /chatbot → Enable):
    Replies to any text message in the chat — including plain 'hello'.

Features:
  ✅ Full mode enabled for GCs via /chatbot command
  ✅ Trigger-only mode for GCs that haven't enabled it
  ✅ Always replies in DMs (private chats)
  ✅ Never repeats a sentence already said in this chat
  ✅ Full per-chat history for context
  ✅ Language-adaptive replies
  ✅ Anthropic API with keyword fallback
"""
import html
import logging
import os
import re
import hashlib
import time
from collections import deque
from typing import Optional

import requests
from telegram import (
    CallbackQuery, Chat, InlineKeyboardButton, InlineKeyboardMarkup,
    ParseMode, Update, User,
)
from telegram.ext import (
    CallbackContext, CallbackQueryHandler,
    CommandHandler, MessageHandler,
)
try:
    from telegram.ext import filters as Filters
    _F = Filters
except ImportError:
    from telegram.ext import Filters
    _F = Filters

import modules.sql.chatbot_sql as sql
from beataniversebot_compat import BOT_ID, BOT_NAME, BOT_USERNAME, dispatcher
from modules.helper_funcs.chat_status import user_admin, user_admin_no_reply
from modules.log_channel import gloggable

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Per-chat state
# ─────────────────────────────────────────────────────────────────────────────

_chat_history: dict[int, list]  = {}
_sent_sentences: dict[int, deque] = {}

_MAX_HISTORY      = 20
_MAX_SENT_HASHES  = 500


def _sentence_hash(s: str) -> str:
    normalised = re.sub(r'\s+', ' ', s.strip().lower())
    normalised = re.sub(r'[^\w\s]', '', normalised)
    return hashlib.md5(normalised.encode()).hexdigest()


def _register_sent(chat_id: int, text: str) -> None:
    if chat_id not in _sent_sentences:
        _sent_sentences[chat_id] = deque(maxlen=_MAX_SENT_HASHES)
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        _sent_sentences[chat_id].append(_sentence_hash(sentence))


def _contains_repeated_sentence(chat_id: int, text: str) -> bool:
    known = _sent_sentences.get(chat_id, deque())
    for sentence in re.split(r'(?<=[.!?])\s+', text):
        if _sentence_hash(sentence) in known:
            return True
    return False


def _trim_history(chat_id: int) -> None:
    h = _chat_history.get(chat_id, [])
    if len(h) > _MAX_HISTORY * 2:
        _chat_history[chat_id] = h[-(_MAX_HISTORY * 2):]


# ─────────────────────────────────────────────────────────────────────────────
#  Core reply logic
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are {bot_name}, a cool anime-obsessed Telegram chatbot. You text like a real person:
- Short replies (1-3 sentences MAX, never more)
- Casual tone, contractions, occasional emoji (not every message)
- NEVER use the same sentence twice in a conversation
- NEVER start with "I", greetings like "Hey!" every time, or filler phrases
  like "That's great!", "Interesting!", "Of course!", "Sure!", "Absolutely!"
- Vary your openers naturally — sometimes start with a question, sometimes
  with a direct statement, sometimes with an emoji, sometimes with nothing
- Match the user's language (Hindi? Reply in Hindi. English? English.)
- You love anime, manga, Demon Slayer, One Piece, JJK, and Japanese culture
- If you don't know something, say so casually — don't make things up
- Never break character or mention that you're an AI unless directly asked
"""

_ANTI_REPEAT_INJECT = """
IMPORTANT: Look at the conversation so far. Your next reply MUST NOT contain
any sentence, phrase, or expression you have already used earlier in this chat.
Rephrase everything differently every single time.
"""


def _call_anthropic(chat_id: int, user_text: str, bot_name: str) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    history = _chat_history.get(chat_id, [])
    history.append({"role": "user", "content": user_text})
    _trim_history(chat_id)
    _chat_history[chat_id] = history

    system = _SYSTEM_PROMPT.format(bot_name=bot_name) + _ANTI_REPEAT_INJECT

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 180,
                    "system": system,
                    "messages": history,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                reply = resp.json()["content"][0]["text"].strip()
                if reply and not _contains_repeated_sentence(chat_id, reply):
                    history.append({"role": "assistant", "content": reply})
                    _chat_history[chat_id] = history
                    _register_sent(chat_id, reply)
                    return reply
                elif reply:
                    logger.debug(f"[chatbot] attempt {attempt+1}: repeated, retrying")
                    history[-1]["content"] = (
                        user_text + "\n\n[Note: rephrase completely, don't repeat anything you already said]"
                    )
                    continue
            else:
                logger.debug(f"[chatbot] API {resp.status_code}: {resp.text[:200]}")
                break
        except Exception as exc:
            logger.debug(f"[chatbot] API error: {exc}")
            break

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Fallback engine
# ─────────────────────────────────────────────────────────────────────────────

_FALLBACK_POOLS: dict[str, list[str]] = {
    "greet": [
        "yo, what's up 👋",
        "heya! how's it going?",
        "oh hey! need something?",
        "hi there! all good?",
        "what brings you here?",
    ],
    "anime": [
        "solid taste ngl 🔥 /anime <title> for a poster",
        "oh that one's a banger. who's your fave character?",
        "nice pick! mine's prob Gojo rn 😤",
        "haven't seen it yet — worth watching?",
        "the animation on that one is insane fr",
    ],
    "help": [
        "/cmd shows everything I can do",
        "try /help — got loads of stuff",
        "/anime, /manga, /movie — take your pick",
        "just hit /cmd and scroll through",
    ],
    "thanks": [
        "np 👌",
        "anytime!",
        "sure thing",
        "👍",
        "always here",
    ],
    "question": [
        "good Q, honestly not sure tbh",
        "hmm idk, maybe try googling that one",
        "no idea rn 😅 ask again later?",
        "great question, zero clue though lol",
    ],
    "default": [
        "lol ok",
        "hm, interesting",
        "fair enough",
        "true tbh",
        "say more?",
        "okay and?",
        "makes sense",
        "👀",
    ],
}

_fallback_used: dict[int, dict[str, int]] = {}


def _fallback_reply(chat_id: int, text: str) -> str:
    tl = text.lower()
    if any(w in tl for w in ["hello", "hi", "hey", "namaste", "helo", "yo", "sup",
                               "hii", "hlo", "hlw", "hola", "ola", "kaise", "kya haal"]):
        topic = "greet"
    elif any(w in tl for w in ["anime", "manga", "watch", "episode", "demon", "naruto",
                                "jjk", "bleach", "one piece", "aot", "haikyuu"]):
        topic = "anime"
    elif any(w in tl for w in ["help", "command", "cmd", "what can", "how to"]):
        topic = "help"
    elif any(w in tl for w in ["thanks", "thank you", "thx", "ty", "tysm", "shukriya",
                                "dhanyavaad", "shukriya"]):
        topic = "thanks"
    elif "?" in text:
        topic = "question"
    else:
        topic = "default"

    pool = _FALLBACK_POOLS[topic]
    if chat_id not in _fallback_used:
        _fallback_used[chat_id] = {}
    idx = _fallback_used[chat_id].get(topic, 0)

    attempts = 0
    while attempts < len(pool):
        candidate = pool[idx % len(pool)]
        if not _contains_repeated_sentence(chat_id, candidate):
            _fallback_used[chat_id][topic] = (idx + 1) % len(pool)
            _register_sent(chat_id, candidate)
            return candidate
        idx += 1
        attempts += 1

    _fallback_used[chat_id][topic] = 1
    reply = pool[0]
    _register_sent(chat_id, reply)
    return reply


def _get_reply(chat_id: int, text: str, bot_name: str) -> str:
    reply = _call_anthropic(chat_id, text, bot_name)
    if reply:
        return reply
    return _fallback_reply(chat_id, text)


# ─────────────────────────────────────────────────────────────────────────────
#  Trigger logic — decides WHETHER to reply
# ─────────────────────────────────────────────────────────────────────────────

def _is_trigger_mention(message, bot_id: int, bot_username: str) -> bool:
    """
    Returns True if the message is a direct trigger regardless of chat mode:
    • @mention of the bot
    • Reply to a bot message
    • "beatverse" keyword
    """
    text = message.text or ""

    if bot_username and f"@{bot_username.lower()}" in text.lower():
        return True

    if message.reply_to_message:
        ru = message.reply_to_message.from_user
        if ru and ru.id == bot_id:
            return True

    if re.search(r'\bbeatverse\b', text, re.IGNORECASE):
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
#  Telegram handlers
# ─────────────────────────────────────────────────────────────────────────────

@user_admin_no_reply
@gloggable
async def beatrm(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user:  Optional[User]          = update.effective_user
    match = re.match(r"rm_chat\((.+?)\)", query.data)
    if match:
        chat: Optional[Chat] = update.effective_chat
        sql.disable_chatbot(chat.id)
        await update.effective_message.edit_text(
            f"{dispatcher.bot.first_name} chatbot <b>disabled</b> by {html.escape(user.first_name)}.\n"
            f"Bot will only respond to @mentions, replies, or the keyword <code>beatverse</code>.",
            parse_mode=ParseMode.HTML,
        )
    return ""


@user_admin_no_reply
@gloggable
async def beatadd(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user:  Optional[User]          = update.effective_user
    match = re.match(r"add_chat\((.+?)\)", query.data)
    if match:
        chat: Optional[Chat] = update.effective_chat
        sql.enable_chatbot(chat.id)
        await update.effective_message.edit_text(
            f"{dispatcher.bot.first_name} chatbot <b>enabled</b> by {html.escape(user.first_name)}.\n"
            f"Bot will now reply to <b>any message</b> in this chat.",
            parse_mode=ParseMode.HTML,
        )
    return ""


@user_admin
@gloggable
async def chatbot_panel(update: Update, context: CallbackContext):
    message  = update.effective_message
    chat_id  = update.effective_chat.id
    is_on    = sql.is_chatbot_active(chat_id)  # True = fully enabled
    status   = "✅ Fully Enabled (replies to all messages)" if is_on else "🔕 Trigger-Only (mention / reply / 'beatverse')"
    msg = (
        f"<b>Chatbot — {html.escape(update.effective_chat.title or 'This Chat')}</b>\n\n"
        f"Status: <b>{status}</b>\n\n"
        "<b>Trigger-only mode</b> (default):\n"
        "• Someone @mentions the bot\n"
        "• Someone replies to the bot's message\n"
        "• Someone says <code>beatverse</code>\n\n"
        "<b>Full mode</b> (after Enable):\n"
        "• Bot replies to <b>every</b> text message\n\n"
        "It never repeats the same sentence twice."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Enable (Full)",     callback_data=f"add_chat({chat_id})"),
        InlineKeyboardButton("🔕 Trigger-Only", callback_data=f"rm_chat({chat_id})"),
    ]])
    await message.reply_text(msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)


def chatbot(update: Update, context: CallbackContext):
    message = update.effective_message
    if not message or not message.text:
        return

    chat_id   = update.effective_chat.id
    chat_type = update.effective_chat.type   # "private", "group", "supergroup"
    bot       = context.bot
    bot_id    = getattr(bot, "id",         BOT_ID)       or BOT_ID
    bot_uname = getattr(bot, "username",   BOT_USERNAME) or BOT_USERNAME
    bot_name  = getattr(bot, "first_name", BOT_NAME)     or BOT_NAME

    # ── Decide whether to reply ──────────────────────────────────────────────
    chatbot_fully_enabled = sql.is_chatbot_active(chat_id)

    if chat_type == "private":
        # DMs: always reply
        should_reply = True
    elif chatbot_fully_enabled:
        # Group with chatbot fully enabled: reply to any text
        should_reply = True
    else:
        # Group with trigger-only mode: only respond to mentions/replies/keyword
        should_reply = _is_trigger_mention(message, bot_id, bot_uname)

    if not should_reply:
        return

    try:
        await context.bot.send_chat_action(chat_id, action="typing")
        reply = _get_reply(chat_id, message.text, bot_name)
        if reply:
            import time as _t; _t.sleep(0.4)
            await message.reply_text(reply)
    except Exception as exc:
        logger.debug(f"[chatbot] send error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
#  Registration
# ─────────────────────────────────────────────────────────────────────────────

__help__ = f"""
*{BOT_NAME} has a built-in chatbot that feels like talking to a real person:*

» /chatbot — Show chatbot control panel (admins only)

*Trigger-only mode (default):*
• Reply to one of the bot's messages
• Tag it with @{BOT_USERNAME}
• Say `beatverse` in the chat

*Full mode (admin enables via /chatbot):*
• Bot replies to any text message, including plain "hello"

It never repeats itself and adjusts to your language automatically.
"""

__mod_name__ = "Cʜᴀᴛʙᴏᴛ"

CHATBOTK_HANDLER = CommandHandler("chatbot", chatbot_panel)
ADD_CHAT_HANDLER  = CallbackQueryHandler(beatadd, pattern=r"add_chat")
RM_CHAT_HANDLER   = CallbackQueryHandler(beatrm,  pattern=r"rm_chat")

try:
    from telegram.ext import filters as _F21
    _chatbot_filter = (
        _F21.TEXT
        & ~_F21.Regex(r"^#[^\s]+")
        & ~_F21.Regex(r"^!")
        & ~_F21.Regex(r"^\/")
    )
except Exception:
    _chatbot_filter = (
        Filters.text
        & ~Filters.regex(r"^#[^\s]+")
        & ~Filters.regex(r"^!")
        & ~Filters.regex(r"^\/")
    )

CHATBOT_HANDLER = MessageHandler(_chatbot_filter, chatbot)

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
