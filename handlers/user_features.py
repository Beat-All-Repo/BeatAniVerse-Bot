"""
handlers/user_features.py
=========================
User features: AFK, notes, warns, rules, reactions, chatbot.
These are the bot.py implementations extracted into this module.
"""
import asyncio
import html
from datetime import datetime, timezone
from typing import Dict, Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.state_machine import afk_users, notes_memory, warns_memory
from core.logging_setup import logger


# ── Reaction GIFs ──────────────────────────────────────────────────────────────
import requests

_REACTION_API = {
    "slap":  "https://nekos.best/api/v2/slap",
    "hug":   "https://nekos.best/api/v2/hug",
    "kiss":  "https://nekos.best/api/v2/kiss",
    "pat":   "https://nekos.best/api/v2/pat",
    "punch": "https://nekos.best/api/v2/punch",
    "poke":  "https://nekos.best/api/v2/poke",
}
_REACTION_TEXTS = {
    "slap":  ("{sender} slapped {target}! 👋", "{sender} slapped themselves??? 🤔"),
    "hug":   ("{sender} hugged {target}! 🤗", "{sender} wants a hug 🥺"),
    "kiss":  ("{sender} kissed {target}! 💋", "{sender} sent a flying kiss 💋"),
    "pat":   ("{sender} patted {target}! 😊", "{sender} pats themselves 😅"),
    "punch": ("{sender} punched {target}! 👊", "{sender} punched the air 💨"),
    "poke":  ("{sender} poked {target}! 👉", "{sender} pokes around 👀"),
}

async def user_reaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user: return
    cmd = (update.message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    sender_name = update.effective_user.first_name or "Someone"
    target_name = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        target_name = " ".join(context.args)
    templates = _REACTION_TEXTS.get(cmd, ("{sender} uses {cmd}!", "{sender}!"))
    if target_name:
        caption = templates[0].format(sender=sender_name, target=target_name, cmd=cmd)
    else:
        caption = templates[1].format(sender=sender_name, cmd=cmd)
    gif_url = None
    api_url = _REACTION_API.get(cmd)
    if api_url:
        try:
            r = requests.get(api_url, timeout=5)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results: gif_url = results[0].get("url")
        except Exception: pass
    try:
        if gif_url:
            await update.message.reply_animation(animation=gif_url, caption=f"<b>{html.escape(caption)}</b>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"<b>{html.escape(caption)}</b>", parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.debug(f"reaction cmd error: {exc}")


async def couple_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user or not update.effective_chat: return
    sender = update.effective_user
    if context.args:
        caption = f"💑 <b>{html.escape(sender.first_name)}</b> and <b>{html.escape(' '.join(context.args))}</b> are now a couple!"
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        partner = update.message.reply_to_message.from_user
        caption = f"💑 <b>{html.escape(sender.first_name)}</b> and <b>{html.escape(partner.first_name)}</b> are a couple! 💕"
    else:
        caption = f"💑 <b>{html.escape(sender.first_name)}</b> is looking for their other half! 💕"
    try:
        gif_url = None
        try:
            r = requests.get("https://nekos.best/api/v2/kiss", timeout=5)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results: gif_url = results[0].get("url")
        except Exception: pass
        if gif_url:
            await update.message.reply_animation(animation=gif_url, caption=caption, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(caption, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.debug(f"couple_cmd error: {exc}")


async def afk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message: return
    uid = update.effective_user.id
    reason = " ".join(context.args) if context.args else "AFK"
    afk_users[uid] = {"reason": reason, "time": datetime.now(timezone.utc)}
    await update.message.reply_text(
        f"<b>{html.escape(update.effective_user.first_name)}</b> is now AFK: <i>{html.escape(reason)}</i>",
        parse_mode=ParseMode.HTML,
    )

async def afk_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user: return
    uid = update.effective_user.id
    msg = update.message
    if uid in afk_users:
        afk_data = afk_users.pop(uid)
        elapsed = datetime.now(timezone.utc) - afk_data["time"]
        mins = int(elapsed.total_seconds() // 60)
        time_str = f"{mins} min" if mins < 60 else f"{mins // 60}h {mins % 60}m"
        try:
            await msg.reply_text(f"<b>{html.escape(update.effective_user.first_name)}</b> is back! (was AFK for {time_str})", parse_mode=ParseMode.HTML)
        except Exception: pass
        return
    if msg.entities:
        for entity in msg.entities:
            if entity.type == "mention":
                try:
                    mention_text = msg.text[entity.offset + 1:entity.offset + entity.length]
                    for afk_uid, afk_data in afk_users.items():
                        member = await context.bot.get_chat_member(msg.chat_id, afk_uid)
                        if member and hasattr(member, "user") and member.user.username == mention_text:
                            elapsed = datetime.now(timezone.utc) - afk_data["time"]
                            mins = int(elapsed.total_seconds() // 60)
                            await msg.reply_text(f"<b>{html.escape(member.user.first_name)}</b> is AFK: <i>{html.escape(afk_data['reason'])}</i> ({mins}m ago)", parse_mode=ParseMode.HTML)
                except Exception: pass


def _get_notes(chat_id: int) -> Dict[str, str]:
    try:
        from database_dual import get_setting
        import json
        val = get_setting(f"notes_{chat_id}", "")
        if val: return json.loads(val)
    except Exception: pass
    return notes_memory.get(chat_id, {})

def _save_notes(chat_id: int, notes: Dict) -> None:
    import json
    try:
        from database_dual import set_setting
        set_setting(f"notes_{chat_id}", json.dumps(notes))
    except Exception: pass
    notes_memory[chat_id] = notes

async def note_save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("<b>Usage:</b> /save notename your note content", parse_mode=ParseMode.HTML)
        return
    name = context.args[0].lower()
    text_content = " ".join(context.args[1:])
    chat_id = update.effective_chat.id
    notes = _get_notes(chat_id)
    notes[name] = text_content
    _save_notes(chat_id, notes)
    await update.message.reply_text(f"<b>📝 Note saved:</b> #{html.escape(name)}", parse_mode=ParseMode.HTML)

async def note_get_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    if not context.args:
        await update.message.reply_text("Usage: /get notename", parse_mode=ParseMode.HTML)
        return
    name = context.args[0].lower()
    notes = _get_notes(update.effective_chat.id)
    content = notes.get(name)
    if content:
        await update.message.reply_text(f"<b>#{html.escape(name)}:</b>\n{html.escape(content)}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"<b>No note named #{html.escape(name)}</b>", parse_mode=ParseMode.HTML)

async def notes_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    notes = _get_notes(update.effective_chat.id)
    if not notes:
        await update.message.reply_text("<b>No notes saved in this chat.</b>", parse_mode=ParseMode.HTML)
        return
    text = "<b>📝 Notes in this chat:</b>\n" + "\n".join(f"• #{html.escape(n)}" for n in notes)
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def note_trigger_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    import re
    match = re.match(r'^#([\w]+)', (update.message.text or "").strip())
    if not match: return
    name = match.group(1).lower()
    notes = _get_notes(update.effective_chat.id)
    content = notes.get(name)
    if content:
        await update.message.reply_text(f"<b>#{html.escape(name)}:</b>\n{html.escape(content)}", parse_mode=ParseMode.HTML)


def _warn_key(chat_id, uid): return f"warn_{chat_id}_{uid}"

def _get_warns(chat_id, uid) -> int:
    try:
        from database_dual import get_setting
        return int(get_setting(_warn_key(chat_id, uid), "0") or "0")
    except Exception:
        return warns_memory.get(f"{chat_id}:{uid}", 0)

def _set_warns(chat_id, uid, count) -> None:
    try:
        from database_dual import set_setting
        set_setting(_warn_key(chat_id, uid), str(count))
    except Exception: pass
    warns_memory[f"{chat_id}:{uid}"] = count

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user: return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"): return
    except Exception: return
    target = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target = update.message.reply_to_message.from_user
    if not target:
        await update.message.reply_text("Reply to a user to warn them.", parse_mode=ParseMode.HTML)
        return
    reason = " ".join(context.args) if context.args else "No reason given"
    chat_id = update.effective_chat.id
    count = _get_warns(chat_id, target.id) + 1
    _set_warns(chat_id, target.id, count)
    try:
        from database_dual import get_setting
        warn_limit = int(get_setting("warn_limit", "3") or "3")
    except Exception:
        warn_limit = 3
    await update.message.reply_text(f"⚠️ <b>{html.escape(target.first_name)}</b> warned ({count}/{warn_limit})\nReason: {html.escape(reason)}", parse_mode=ParseMode.HTML)
    if count >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            _set_warns(chat_id, target.id, 0)
            await update.message.reply_text(f"🔴 <b>{html.escape(target.first_name)}</b> has been banned after {warn_limit} warnings.", parse_mode=ParseMode.HTML)
        except Exception: pass

async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to remove their warn.")
        return
    target = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    count = max(0, _get_warns(chat_id, target.id) - 1)
    _set_warns(chat_id, target.id, count)
    await update.message.reply_text(f"✅ Removed 1 warn from <b>{html.escape(target.first_name)}</b>. Now at {count} warns.", parse_mode=ParseMode.HTML)

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    target = None
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target = update.message.reply_to_message.from_user
    else:
        target = update.effective_user
    chat_id = update.effective_chat.id
    count = _get_warns(chat_id, target.id)
    try:
        from database_dual import get_setting
        warn_limit = int(get_setting("warn_limit", "3") or "3")
    except Exception:
        warn_limit = 3
    await update.message.reply_text(f"⚠️ <b>{html.escape(target.first_name)}</b> has <b>{count}/{warn_limit}</b> warns.", parse_mode=ParseMode.HTML)

async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user to reset their warns.")
        return
    target = update.message.reply_to_message.from_user
    _set_warns(update.effective_chat.id, target.id, 0)
    await update.message.reply_text(f"✅ Warns reset for <b>{html.escape(target.first_name)}</b>.", parse_mode=ParseMode.HTML)

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    try:
        from database_dual import get_setting
        rules = get_setting(f"rules_{update.effective_chat.id}", "")
    except Exception:
        rules = ""
    if rules:
        await update.message.reply_text(f"<b> Group Rules:</b>\n\n{html.escape(rules)}", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("<b>No rules set for this group yet.</b>", parse_mode=ParseMode.HTML)

async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user: return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"): return
    except Exception: return
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /setrules your rules text here", parse_mode=ParseMode.HTML)
        return
    rules_text = " ".join(context.args)
    try:
        from database_dual import set_setting
        set_setting(f"rules_{update.effective_chat.id}", rules_text)
    except Exception: pass
    await update.message.reply_text("✅ Rules saved!", parse_mode=ParseMode.HTML)

async def chatbot_private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    await _chatbot_reply(update, context, update.message.text)

async def chatbot_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text: return
    text = update.message.text.strip()
    bot_username = context.bot.username or ""
    triggered = False
    if f"@{bot_username}" in text:
        text = text.replace(f"@{bot_username}", "").strip()
        triggered = True
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        if update.message.reply_to_message.from_user.id == context.bot.id:
            triggered = True
    if triggered:
        await _chatbot_reply(update, context, text)

async def _chatbot_reply(update: Update, context, text: str) -> None:
    """Route to new dual chatbot engine (Gemini + Groq)."""
    chat_id = update.effective_chat.id
    user_msg = text.strip()
    if not user_msg:
        return

    user = update.effective_user
    user_id = user.id if user else 0
    user_name = (user.first_name or "User") if user else "User"

    try:
        await context.bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass

    async def _send_reply(reply_text: str):
        sent = None
        try:
            sent = await update.message.reply_text(reply_text)
        except Exception:
            try:
                sent = await context.bot.send_message(chat_id=chat_id, text=reply_text)
            except Exception:
                pass
        return sent

    try:
        from core.chatbot_engine import handle_chatbot_message
        await handle_chatbot_message(
            bot=context.bot,
            chat_id=chat_id,
            user_id=user_id,
            user_name=user_name,
            message_text=user_msg,
            reply_fn=_send_reply,
        )
    except Exception as exc:
        logger.debug(f"[chatbot] engine error: {exc}")

    # chat_id for auto-delete middleware below
    chat_id = update.effective_chat.id if update.effective_chat else 0
    try:
        from core.auto_delete import auto_delete_middleware
        await auto_delete_middleware(
            bot          = update.get_bot() if hasattr(update, "get_bot") else update.message.get_bot(),
            sent_msg     = sent_chatbot,
            trigger_msg  = update.message,
            is_chatbot   = True,   # ← exempts GC chatbot replies from deletion
        )
    except Exception:
        pass


# ── User Features Panel ────────────────────────────────────────────────────────

async def send_user_features_panel(
    update,
    context,
    query=None,
    chat_id: int = 0,
    page: int = 0,
) -> None:
    """User features panel — 4×2 grid of feature buttons. Click = help for that feature."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from core.text_utils import b, bq, small_caps as sc
    from core.helpers import safe_send_message

    if not chat_id:
        if query:
            chat_id = query.message.chat_id
        elif update and update.effective_chat:
            chat_id = update.effective_chat.id

    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    # 8 feature buttons in 4×2 grid — each opens its own help card
    FEATURES = [
        ("🎌 Anime",       "uf_help:anime",    "uf"),
        ("📚 Manga",       "uf_help:manga",    "uf"),
        ("🎬 Movie",       "uf_help:movie",    "uf"),
        ("👤 Character",   "uf_help:character","uf"),
        ("🤗 Reactions",   "uf_help:reactions","uf"),
        ("💬 Chatbot",     "uf_help:chatbot",  "uf"),
        ("📝 Notes",       "uf_help:notes",    "uf"),
        ("⚖️ Group Tools", "uf_help:group",    "uf"),
    ]

    rows = []
    for i in range(0, len(FEATURES), 2):
        row = []
        for label, cb, _ in FEATURES[i:i+2]:
            row.append(InlineKeyboardButton(label, callback_data=cb))
        rows.append(row)
    rows.append([InlineKeyboardButton("✖ Close", callback_data="close_message")])

    text = (
        b("🎮 User Features") + "\n\n"
        + bq(sc("tap any feature to see its commands and usage"))
    )

    markup = InlineKeyboardMarkup(rows)
    try:
        from core.panel_image import get_panel_pic_async
        from core.helpers import safe_send_photo
        img = await get_panel_pic_async("features")
        if img:
            sent = await safe_send_photo(context.bot, chat_id, img, caption=text, reply_markup=markup)
            if sent:
                return
    except Exception:
        pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)



    if not chat_id:
        if query:
            chat_id = query.message.chat_id
        elif update and update.effective_chat:
            chat_id = update.effective_chat.id

    # Delete previous panel before sending new
    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    sc = small_caps

    FEATURES_PAGES = [
        {
            "title": "🎌 ᴀɴɪᴍᴇ & ᴍᴀɴɢᴀ",
            "items": [
                ("/anime &lt;name&gt;",     "ɢᴇɴᴇʀᴀᴛᴇ ᴀɴɪᴍᴇ ᴘᴏsᴛᴇʀ + ɪɴꜰᴏ"),
                ("/manga &lt;name&gt;",     "ɢᴇɴᴇʀᴀᴛᴇ ᴍᴀɴɢᴀ ᴘᴏsᴛᴇʀ"),
                ("/net &lt;title&gt;",      "ɴᴇᴛꜰʟɪx-sᴛʏʟᴇ ᴘᴏsᴛᴇʀ"),
                ("/airing &lt;name&gt;",    "ᴄʜᴇᴄᴋ ᴀɪʀɪɴɢ ꜱᴄʜᴇᴅᴜʟᴇ"),
                ("/character &lt;name&gt;", "ᴄʜᴀʀᴀᴄᴛᴇʀ ɪɴꜰᴏ"),
                ("/movie &lt;name&gt;",     "ɢᴇɴᴇʀᴀᴛᴇ ᴍᴏᴠɪᴇ ᴘᴏsᴛᴇʀ"),
            ],
        },
        {
            "title": "👥 ꜱᴏᴄɪᴀʟ",
            "items": [
                ("/hug",   "sᴇɴᴅ ᴀ ʜᴜɢ ɢɪꜰ"),
                ("/slap",  "sʟᴀᴘ sᴏᴍᴇᴏɴᴇ"),
                ("/kiss",  "sᴇɴᴅ ᴀ ᴋɪss ɢɪꜰ"),
                ("/pat",   "ᴘᴀᴛ sᴏᴍᴇᴏɴᴇ"),
                ("/punch", "ᴘᴜɴᴄʜ sᴏᴍᴇᴏɴᴇ"),
                ("/couple","sʜᴏᴡ ᴀ ᴄᴏᴜᴘʟᴇ ɢɪꜰ"),
            ],
        },
        {
            "title": "📋 ɢʀᴏᴜᴘ ᴛᴏᴏʟs",
            "items": [
                ("/warn",       "ᴡᴀʀɴ ᴀ ᴜsᴇʀ"),
                ("/warns",      "ᴄʜᴇᴄᴋ ᴡᴀʀɴs"),
                ("/unwarn",     "ʀᴇᴍᴏᴠᴇ ᴀ ᴡᴀʀɴ"),
                ("/save",       "sᴀᴠᴇ ᴀ ɴᴏᴛᴇ"),
                ("/get",        "ɢᴇᴛ ᴀ ɴᴏᴛᴇ"),
                ("/rules",      "sʜᴏᴡ ɢʀᴏᴜᴘ ʀᴜʟᴇs"),
            ],
        },
    ]

    pages = FEATURES_PAGES
    page = page % len(pages)
    pg = pages[page]

    lines = "\n".join(
        f"<code>{cmd}</code> — {desc}"
        for cmd, desc in pg["items"]
    )
    text = (
        b(pg["title"]) + "\n\n"
        + lines + "\n\n"
        + bq(sc("use /help for full command list"))
    )

    total = len(pages)
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("🔙", callback_data=f"user_features_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"· {page+1}/{total} ·", callback_data="noop"))
    if page < total - 1:
        nav_row.append(InlineKeyboardButton("🔜", callback_data=f"user_features_{page+1}"))

    keyboard = [
        nav_row,
        [InlineKeyboardButton("✖️ " + sc("close"), callback_data="close_message")],
    ]

    try:
        from core.panel_image import get_panel_pic_async
        img = await get_panel_pic_async("features")
    except Exception:
        img = None

    markup = InlineKeyboardMarkup(keyboard)
    if img:
        sent = await safe_send_photo(context.bot, chat_id, img, caption=text, reply_markup=markup)
        if sent:
            return
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
