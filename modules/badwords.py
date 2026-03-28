# ====================================================================
# PLACE AT: /app/modules/badwords.py
# ACTION: Replace existing file
# ====================================================================
"""
badwords.py — Bad Words / Auto-Moderation System
=================================================
Features:
  • /addword <word>  — Add a word to ban list (group admin only)
  • /rmword <word>   — Remove a word from ban list
  • /badwords        — List all banned words in this group
  • /clearwords      — Clear all banned words
  • /wordaction      — Set what happens: warn / mute / ban / del (default: warn+del)
  • Auto-detection: bot monitors all messages, acts on matches

Word matching: case-insensitive, partial word match (e.g. "bad" matches "badness")

Actions:
  warn   — Warn the user (3 warns → auto ban)
  mute   — Mute for 1 hour
  ban    — Permanently ban
  del    — Only delete the message (no other action)
  kick   — Kick from group

Credits: BeatAnime | @BeatAnime
"""

import html
import re
import json
from typing import Optional

from telegram import Update, ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from beataniversebot_compat import dispatcher, LOGGER

# ── Storage (DB-backed via bot_settings) ──────────────────────────────────────
def _get_db():
    try:
        from database_dual import get_setting, set_setting
        return get_setting, set_setting
    except Exception:
        return None, None

def _key_words(chat_id): return f"badwords_list_{chat_id}"
def _key_action(chat_id): return f"badwords_action_{chat_id}"

def get_bad_words(chat_id: int) -> list:
    get_setting, _ = _get_db()
    if get_setting:
        try:
            raw = get_setting(_key_words(chat_id), "[]")
            return json.loads(raw or "[]")
        except Exception:
            pass
    return []

def save_bad_words(chat_id: int, words: list) -> None:
    _, set_setting = _get_db()
    if set_setting:
        try:
            set_setting(_key_words(chat_id), json.dumps(words))
        except Exception:
            pass

def get_word_action(chat_id: int) -> str:
    get_setting, _ = _get_db()
    if get_setting:
        try:
            return get_setting(_key_action(chat_id), "warn") or "warn"
        except Exception:
            pass
    return "warn"

def set_word_action(chat_id: int, action: str) -> None:
    _, set_setting = _get_db()
    if set_setting:
        try:
            set_setting(_key_action(chat_id), action)
        except Exception:
            pass

# Warn counter storage
_warn_counts: dict = {}

def _get_warns(chat_id: int, user_id: int) -> int:
    try:
        from database_dual import get_setting
        val = get_setting(f"warn_{chat_id}_{user_id}", "0")
        return int(val or "0")
    except Exception:
        return _warn_counts.get(f"{chat_id}:{user_id}", 0)

def _set_warns(chat_id: int, user_id: int, count: int) -> None:
    try:
        from database_dual import set_setting
        set_setting(f"warn_{chat_id}_{user_id}", str(count))
    except Exception:
        pass
    _warn_counts[f"{chat_id}:{user_id}"] = count

# ── Helper: check if sender is admin ─────────────────────────────────────────
async def _is_admin(update: Update, context) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        return member.status in ("administrator", "creator")
    except Exception:
        return False

# ── Commands ──────────────────────────────────────────────────────────────────
async def addword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/addword <word> — Add a bad word (admin only)."""
    if not update.message or not update.effective_chat:
        return
    if not await _is_admin(update, context):
        await update.message.reply_text("⚠️ Only admins can add bad words.")
        return
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> /addword &lt;word&gt;\n"
            "<i>You can add multiple words: /addword word1 word2 word3</i>",
            parse_mode=ParseMode.HTML
        )
        return
    chat_id = update.effective_chat.id
    words = get_bad_words(chat_id)
    added = []
    for w in context.args:
        w_clean = w.lower().strip()
        if w_clean and w_clean not in words:
            words.append(w_clean)
            added.append(w_clean)
    save_bad_words(chat_id, words)
    if added:
        await update.message.reply_text(
            f"✅ Added {len(added)} bad word(s): <code>{html.escape(', '.join(added))}</code>\n"
            f"Total bad words: <b>{len(words)}</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("ℹ️ All those words are already in the list.")

async def rmword_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/rmword <word> — Remove a bad word (admin only)."""
    if not update.message or not update.effective_chat:
        return
    if not await _is_admin(update, context):
        await update.message.reply_text("⚠️ Only admins can remove bad words.")
        return
    if not context.args:
        await update.message.reply_text("<b>Usage:</b> /rmword &lt;word&gt;", parse_mode=ParseMode.HTML)
        return
    chat_id = update.effective_chat.id
    words = get_bad_words(chat_id)
    removed = []
    for w in context.args:
        w_clean = w.lower().strip()
        if w_clean in words:
            words.remove(w_clean)
            removed.append(w_clean)
    save_bad_words(chat_id, words)
    if removed:
        await update.message.reply_text(
            f"✅ Removed: <code>{html.escape(', '.join(removed))}</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("ℹ️ Those words were not in the list.")

async def badwords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/badwords — List all bad words in this group."""
    if not update.message or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    words = get_bad_words(chat_id)
    action = get_word_action(chat_id)
    if not words:
        await update.message.reply_text(
            "📋 <b>No bad words set for this group.</b>\n"
            "Use /addword &lt;word&gt; to add some.",
            parse_mode=ParseMode.HTML
        )
        return
    word_list = "\n".join(f"• <code>{html.escape(w)}</code>" for w in words)
    await update.message.reply_text(
        f"📋 <b>Bad Words ({len(words)} total)</b>\n\n"
        f"{word_list}\n\n"
        f"<b>Current action:</b> {action.upper()}\n"
        f"<i>Change with /wordaction warn|mute|ban|del|kick</i>",
        parse_mode=ParseMode.HTML
    )

async def clearwords_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/clearwords — Remove all bad words (admin only)."""
    if not update.message or not update.effective_chat:
        return
    if not await _is_admin(update, context):
        await update.message.reply_text("⚠️ Only admins can clear bad words.")
        return
    save_bad_words(update.effective_chat.id, [])
    await update.message.reply_text("✅ All bad words cleared.")

async def wordaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/wordaction <warn|mute|ban|del|kick> — Set the action for bad words."""
    if not update.message or not update.effective_chat:
        return
    if not await _is_admin(update, context):
        await update.message.reply_text("⚠️ Only admins can change this.")
        return
    valid_actions = ["warn", "mute", "ban", "del", "kick", "nothing"]
    if not context.args or context.args[0].lower() not in valid_actions:
        current = get_word_action(update.effective_chat.id)
        await update.message.reply_text(
            f"<b>Current action:</b> <code>{current}</code>\n\n"
            "<b>Available actions:</b>\n"
            "• <code>warn</code> — Warn user (3 warns = auto ban)\n"
            "• <code>mute</code> — Mute for 1 hour\n"
            "• <code>ban</code>  — Permanently ban\n"
            "• <code>del</code>  — Only delete message\n"
            "• <code>kick</code> — Kick from group\n\n"
            "<b>Usage:</b> /wordaction warn",
            parse_mode=ParseMode.HTML
        )
        return
    action = context.args[0].lower()
    set_word_action(update.effective_chat.id, action)
    await update.message.reply_text(
        f"✅ Bad word action set to: <b>{action.upper()}</b>",
        parse_mode=ParseMode.HTML
    )

# ── Auto-detection message handler ────────────────────────────────────────────
async def check_message_for_badwords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monitor all group messages for bad words."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return
    if update.effective_chat.type == "private":
        return

    msg = update.message
    text = (msg.text or msg.caption or "").lower()
    if not text:
        return

    # Skip if sender is admin or bot
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, update.effective_user.id
        )
        if member.status in ("administrator", "creator"):
            return
    except Exception:
        pass

    chat_id = update.effective_chat.id
    words = get_bad_words(chat_id)
    if not words:
        return

    triggered_word = None
    for word in words:
        # Word boundary match (prevents partial false positives for short words)
        if len(word) <= 3:
            if word in text.split():
                triggered_word = word
                break
        else:
            if word in text:
                triggered_word = word
                break

    if not triggered_word:
        return

    action = get_word_action(chat_id)
    user = update.effective_user
    user_mention = f"<a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>"

    # Always delete the message
    try:
        await msg.delete()
    except Exception:
        pass

    if action == "del":
        # Just delete, notify briefly
        try:
            notif = await context.bot.send_message(
                chat_id,
                f"🚫 Message by {user_mention} deleted (contained banned word).",
                parse_mode=ParseMode.HTML
            )
            import asyncio
            await asyncio.sleep(5)
            await notif.delete()
        except Exception:
            pass
        return

    if action == "warn":
        count = _get_warns(chat_id, user.id) + 1
        _set_warns(chat_id, user.id, count)
        warn_limit = 3
        if count >= warn_limit:
            try:
                await context.bot.ban_chat_member(chat_id, user.id)
                _set_warns(chat_id, user.id, 0)
                await context.bot.send_message(
                    chat_id,
                    f"🚫 {user_mention} was <b>banned</b> after {warn_limit} warnings for using bad words.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
        else:
            await context.bot.send_message(
                chat_id,
                f"⚠️ {user_mention} warned for using a banned word.\n"
                f"<b>Warnings: {count}/{warn_limit}</b>",
                parse_mode=ParseMode.HTML
            )

    elif action == "mute":
        try:
            from datetime import datetime, timedelta, timezone
            until = datetime.now(timezone.utc) + timedelta(hours=1)
            await context.bot.restrict_chat_member(
                chat_id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await context.bot.send_message(
                chat_id,
                f"🔇 {user_mention} has been <b>muted for 1 hour</b> for using a banned word.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            LOGGER.debug(f"badwords mute error: {e}")

    elif action == "ban":
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.send_message(
                chat_id,
                f"🚫 {user_mention} has been <b>banned</b> for using a banned word.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            LOGGER.debug(f"badwords ban error: {e}")

    elif action == "kick":
        try:
            await context.bot.ban_chat_member(chat_id, user.id)
            await context.bot.unban_chat_member(chat_id, user.id)
            await context.bot.send_message(
                chat_id,
                f"👢 {user_mention} has been <b>kicked</b> for using a banned word.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            LOGGER.debug(f"badwords kick error: {e}")

# ── Register handlers ─────────────────────────────────────────────────────────
def register(app) -> None:
    app.add_handler(CommandHandler("addword",   addword_cmd))
    app.add_handler(CommandHandler("rmword",    rmword_cmd))
    app.add_handler(CommandHandler("badwords",  badwords_cmd))
    app.add_handler(CommandHandler("clearwords",clearwords_cmd))
    app.add_handler(CommandHandler("wordaction",wordaction_cmd))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        check_message_for_badwords
    ), group=10)
    LOGGER.info("[badwords] Handlers registered")

__mod_name__ = "BadWords"
__command_list__ = ["addword", "rmword", "badwords", "clearwords", "wordaction"]
__help__ = """
<b>🚫 Bad Words / Auto-Moderation</b>

Automatically act on users who send banned words in the group.

<b>Admin commands:</b>
• /addword &lt;word&gt; — Add a banned word (can add multiple)
• /rmword &lt;word&gt;  — Remove a banned word
• /badwords         — List all banned words + current action
• /clearwords       — Remove all banned words
• /wordaction &lt;action&gt; — Set what happens when triggered:
   <code>warn</code>  — Warn user (3 warns = auto ban)
   <code>mute</code>  — Mute for 1 hour
   <code>ban</code>   — Permanently ban
   <code>del</code>   — Delete message only
   <code>kick</code>  — Kick from group

<b>Example:</b>
<code>/addword spam scam promo</code>
<code>/wordaction mute</code>

<i>Bot always deletes the offending message regardless of action.</i>
"""
