"""
handlers/help.py
================
/help, /cmd, /ping, /alive, /id, /info commands.
"""
import html
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, BOT_NAME, BOT_USERNAME,
    PUBLIC_ANIME_CHANNEL_URL, ADMIN_CONTACT_USERNAME,
    HELP_CHANNEL_1_URL, HELP_CHANNEL_1_NAME,
    HELP_CHANNEL_2_URL, HELP_CHANNEL_2_NAME,
    HELP_CHANNEL_3_URL, HELP_CHANNEL_3_NAME,
    HELP_IMAGE_URL, HELP_TEXT_CUSTOM, I_AM_CLONE,
)
from core.text_utils import b, bq, e, code, small_caps
from core.helpers import safe_reply, safe_send_photo, safe_send_message, get_uptime
from core.buttons import bold_button, _close_btn
from core.filters_system import force_sub_required
from core.state_machine import user_states
from core.logging_setup import logger


@force_sub_required
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Help command.
    - Regular users: shows custom ENV info with channel buttons only.
    - Admin/Owner: shows full admin command reference.
    """
    uid = update.effective_user.id if update.effective_user else 0
    from handlers.start import delete_update_message, delete_bot_prompt
    await delete_update_message(update, context)
    is_admin = uid in (ADMIN_ID, OWNER_ID)

    keyboard = []
    if HELP_CHANNEL_1_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_1_NAME, url=HELP_CHANNEL_1_URL)])
    if HELP_CHANNEL_2_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_2_NAME, url=HELP_CHANNEL_2_URL)])
    if HELP_CHANNEL_3_URL:
        keyboard.append([InlineKeyboardButton(HELP_CHANNEL_3_NAME, url=HELP_CHANNEL_3_URL)])
    if PUBLIC_ANIME_CHANNEL_URL and not any(PUBLIC_ANIME_CHANNEL_URL == r[0].url for r in keyboard if r):
        keyboard.append([InlineKeyboardButton("ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ", url=PUBLIC_ANIME_CHANNEL_URL)])
    if ADMIN_CONTACT_USERNAME:
        keyboard.append([InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ", url=f"https://t.me/{ADMIN_CONTACT_USERNAME}")])
    keyboard.append([bold_button("CLOSE", callback_data="close_message")])
    markup = InlineKeyboardMarkup(keyboard)

    if not is_admin:
        user_text = HELP_TEXT_CUSTOM if HELP_TEXT_CUSTOM else (
            b(f"ℹ️ {e(BOT_NAME)}") + "\n\n"
            + bq(
                b(" Your gateway to Anime, Manga & Movies!\n\n")
                + "Use the buttons below to join our channels."
            )
        )
        if HELP_IMAGE_URL:
            sent = await safe_send_photo(
                context.bot, update.effective_chat.id,
                HELP_IMAGE_URL, caption=user_text, reply_markup=markup,
            )
            if sent:
                return
        await safe_reply(update, user_text, reply_markup=markup)
        return

    user_states.pop(uid, None)
    await delete_bot_prompt(context, update.effective_chat.id)

    text = (
        b("📖 Admin Command Reference") + "\n\n"
        + bq(
            b(" Content Generation:\n")
            + "<b>/anime</b> [name] — Anime post (AniList)\n"
            + "<b>/manga</b> [name] — Manga post (AniList + MangaDex)\n"
            + "<b>/movie</b> [name] — Movie post (TMDB)\n"
            + "<b>/tvshow</b> [name] — TV show post (TMDB)\n"
            + "<b>/search</b> [name] — Search all categories\n\n"
            + b(" Poster Templates (Admin only):\n")
            + "<b>/ani, /anim, /crun, /net, /netm</b>\n"
            + "<b>/light, /lightm, /dark, /darkm</b>\n"
            + "<b>/mod, /modm, /netcr</b> — Styled poster images\n\n"
            + b(" Link Provider:\n")
            + "<b>/addchannel</b> @id_or_username [Title] [jbr]\n"
            + "<b>/removechannel</b> @username_or_id\n"
            + "<b>/channel</b> — List force-sub channels\n"
            + "<b>/genlink</b> (via admin panel)\n\n"
            + b(" User Management:\n")
            + "<b>/banuser, /unbanuser, /listusers</b>\n"
            + "<b>/deleteuser, /exportusers</b>\n\n"
            + b(" Broadcast:\n")
            + "<b>/broadcast</b> (via /start panel)\n"
            + "<b>/broadcaststats</b> — Broadcast history\n\n"
            + b(" Clone Bots:\n")
            + "<b>/addclone</b> TOKEN — Add clone\n"
            + "<b>/clones</b> — List clones\n\n"
            + b(" Upload Manager:\n")
            + "<b>/upload</b> — Open upload panel\n\n"
            + b(" Settings & Tools:\n")
            + "<b>/settings</b> — Category settings\n"
            + "<b>/autoforward</b> — Auto-forward manager\n"
            + "<b>/autoupdate</b> — Manga chapter tracker\n"
            + "<b>/connect, /disconnect</b> — Group connections\n"
            + "<b>/stats, /sysstats, /users</b>\n"
            + "<b>/backup, /reload, /logs</b>\n\n"
            + b(" Premium (Poster):\n")
            + "<b>/add_premium</b> id rank [duration]\n"
            + "<b>/remove_premium</b> id\n"
            + "<b>/premium_list</b> — List premium users",
            expandable=True,
        )
    )

    if HELP_IMAGE_URL:
        sent = await safe_send_photo(
            context.bot, update.effective_chat.id,
            HELP_IMAGE_URL, caption=text, reply_markup=markup,
        )
        if sent:
            return

    await safe_reply(update, text, reply_markup=markup)


@force_sub_required
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    t0 = time.monotonic()
    try:
        msg = await safe_reply(update, b("🏓 Pinging…"))
        if msg:
            elapsed_ms = (time.monotonic() - t0) * 1000
            await msg.edit_text(
                b("🏓 Pong!") + "\n\n"
                f"<b>Response Time:</b> {code(f'{elapsed_ms:.0f}ms')}\n"
                f"<b>Status:</b> {code('Online ✅')}",
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        pass


@force_sub_required
async def alive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        b("✅ Bot is Alive!") + "\n\n"
        f"<b>⏱ Uptime:</b> {code(get_uptime())}\n"
        f"<b>🤖 Username:</b> @{e(BOT_USERNAME)}\n"
        f"<b>🏷 Mode:</b> {code('Clone Bot' if I_AM_CLONE else 'Main Bot')}"
    )
    await safe_reply(update, text)


@force_sub_required
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat

    text = b(small_caps("🆔 id info")) + "\n\n"

    if user:
        uname = f" @{e(user.username)}" if user.username else ""
        text += (
            f"» {b(small_caps('user id'))} {code(str(user.id))}{uname}\n"
            f"» {b(small_caps('name'))} {e(user.full_name or '')}\n"
        )
    text += (
        f"» {b(small_caps('chat id'))} {code(str(chat.id))}\n"
        f"» {b(small_caps('type'))} {code(chat.type)}\n"
    )
    if chat.username:
        text += f"» {b(small_caps('username'))} @{e(chat.username)}\n"

    if msg.reply_to_message:
        rep = msg.reply_to_message
        text += "\n" + b(small_caps("replied message")) + "\n"

        if rep.sender_chat:
            ch = rep.sender_chat
            text += (
                f"» {b(small_caps('channel id'))} {code(str(ch.id))}\n"
                f"» {b(small_caps('channel title'))} {e(ch.title or '')}\n"
            )
            if ch.username:
                text += f"» {b(small_caps('channel username'))} @{e(ch.username)}\n"
            try:
                ch_full = await context.bot.get_chat(ch.id)
                if ch_full.invite_link:
                    text += f"» {b(small_caps('invite link'))} {e(ch_full.invite_link)}\n"
                if ch_full.member_count:
                    text += f"» {b(small_caps('members'))} {code(str(ch_full.member_count))}\n"
            except Exception:
                pass

        _fwd_chat = None
        try:
            _fo = getattr(rep, "forward_origin", None)
            if _fo and hasattr(_fo, "chat"):
                _fwd_chat = _fo.chat
            elif _fo and hasattr(_fo, "sender_chat"):
                _fwd_chat = _fo.sender_chat
        except Exception:
            pass
        if _fwd_chat:
            text += (
                f"» {b(small_caps('fwd channel id'))} {code(str(_fwd_chat.id))}\n"
                f"» {b(small_caps('fwd channel title'))} {e(_fwd_chat.title or '')}\n"
            )
            if getattr(_fwd_chat, "username", None):
                text += f"» {b(small_caps('fwd username'))} @{e(_fwd_chat.username)}\n"

        if rep.from_user and not rep.sender_chat:
            ru = rep.from_user
            runame = f" @{e(ru.username)}" if ru.username else ""
            text += (
                f"» {b(small_caps('replied user id'))} {code(str(ru.id))}{runame}\n"
                f"» {b(small_caps('replied name'))} {e(ru.full_name or '')}\n"
            )

        media_fields = [
            ("sticker",    rep.sticker,    rep.sticker.file_id if rep.sticker else None),
            ("photo",      rep.photo,      rep.photo[-1].file_id if rep.photo else None),
            ("video",      rep.video,      rep.video.file_id if rep.video else None),
            ("audio",      rep.audio,      rep.audio.file_id if rep.audio else None),
            ("document",   rep.document,   rep.document.file_id if rep.document else None),
            ("animation",  rep.animation,  rep.animation.file_id if rep.animation else None),
            ("voice",      rep.voice,      rep.voice.file_id if rep.voice else None),
            ("video note", rep.video_note, rep.video_note.file_id if rep.video_note else None),
        ]
        for label, obj, fid in media_fields:
            if fid:
                text += f"» {b(small_caps(label + ' file id'))}\n  {code(fid)}\n"

    if len(text) > 3500:
        text = text[:3496] + "…"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


@force_sub_required
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    target = None
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            target = await context.bot.get_chat(context.args[0])
        except Exception as exc:
            from core.helpers import UserFriendlyError
            await update.message.reply_text(UserFriendlyError.get_user_message(exc), parse_mode=ParseMode.HTML)
            return
    else:
        target = update.effective_user

    if not target:
        await update.message.reply_text(b("No target specified."), parse_mode=ParseMode.HTML)
        return

    uid_val = getattr(target, "id", "N/A")
    uname = getattr(target, "username", None)
    fname = getattr(target, "first_name", None)
    lname = getattr(target, "last_name", None)
    title = getattr(target, "title", None)
    chat_type = getattr(target, "type", None)

    text = b("👤 Info") + "\n\n"
    text += f"<b>ID:</b> {code(str(uid_val))}\n"
    if uname:
        text += f"<b>Username:</b> @{e(uname)}\n"
    if fname:
        text += f"<b>First Name:</b> {e(fname)}\n"
    if lname:
        text += f"<b>Last Name:</b> {e(lname)}\n"
    if title:
        text += f"<b>Title:</b> {e(title)}\n"
    if chat_type:
        text += f"<b>Type:</b> {code(chat_type)}\n"

    try:
        from database_dual import get_user_info_by_id
        user_info = get_user_info_by_id(int(uid_val))
        if user_info:
            _, _, _, _, joined, banned = user_info
            text += f"<b>Joined Bot:</b> {code(str(joined)[:16])}\n"
            text += f"<b>Status:</b> {'🚫 Banned' if banned else '✅ Active'}\n"
    except Exception:
        pass

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /cmd — Show commands based on who is asking.
    Authority-aware: bot admin > group admin > regular user.
    """
    from handlers.start import delete_update_message
    await delete_update_message(update, context)
    uid = update.effective_user.id if update.effective_user else 0
    chat = update.effective_chat
    is_bot_admin = uid in (ADMIN_ID, OWNER_ID)

    is_group_admin = False
    if chat and chat.type in ("group", "supergroup"):
        try:
            m = await context.bot.get_chat_member(chat.id, uid)
            is_group_admin = m.status in ("administrator", "creator")
        except Exception:
            pass

    def sec(title, cmds):
        lines = f"<b>{small_caps(title)}</b>\n"
        for cmd, desc in cmds:
            lines += f"  /{cmd} — {small_caps(desc)}\n"
        return lines + "\n"

    public = sec("🌐 General — Everyone", [
        ("start", "Main menu"), ("help", "Help & channel links"),
        ("cmd", "Show all commands"), ("alive", "Check if bot is online"),
        ("ping", "Bot response speed"), ("id", "Your Telegram user / chat ID"),
        ("info", "User info lookup"), ("my_plan", "Your daily poster usage limit"),
        ("plans", "View all available poster plans"),
        ("rules", "View group rules"), ("report", "Report a message to admins (reply)"),
    ])
    anime_s = sec("🎌 Anime & Media — Everyone", [
        ("anime", "<n> — Anime poster + info"), ("manga", "<n> — Manga poster + info"),
        ("movie", "<n> — Movie poster + info"), ("tvshow", "<n> — TV show poster"),
        ("search", "<n> — Multi-source search"), ("airing", "<n> — Next episode countdown"),
        ("character", "<n> — Character details"), ("imdb", "<n> — IMDb lookup"),
    ])
    fun_s = sec("🎮 Fun & Reactions — Everyone", [
        ("hug", "Hug someone"), ("slap", "Slap someone"), ("kiss", "Kiss someone"),
        ("pat", "Pat someone"), ("couple", "Couple of the day"),
        ("truth", "Random truth question"), ("dare", "Random dare challenge"),
        ("afk", "<reason> — Set yourself as AFK"), ("aq", "Random anime quote"),
    ])
    tools_s = sec("🛠 Tools — Everyone", [
        ("wiki", "<topic> — Wikipedia summary"), ("ud", "<word> — Urban Dictionary"),
        ("tr", "<lang> <text> — Translate"), ("time", "<city> — Current time"),
        ("write", "<text> — Handwriting image"), ("wall", "<query> — Anime wallpaper"),
        ("cash", "<amount> <from> <to> — Currency"), ("ping", "Bot speed check"),
    ])

    if is_bot_admin:
        bot_admin_s = sec("🔴 Bot Admin Only", [
            ("stats", "Bot statistics"), ("sysstats", "Server stats"),
            ("upload", "Upload manager"), ("settings", "Category settings"),
            ("autoupdate", "Manga tracker"), ("autoforward", "Auto-forward manager"),
            ("broadcast", "Send broadcast"), ("addchannel", "Add force-sub channel"),
            ("banuser", "Ban from bot"), ("add_premium", "Give premium plan"),
            ("addclone", "Add clone bot"), ("reload", "Restart bot"),
            ("logs", "View logs"), ("gban", "Global ban"),
            ("backup", "Links backup"), ("exportusers", "Export CSV"),
        ])
        text = b("📋 All Commands — Bot Admin View") + "\n\n" + public + anime_s + fun_s + tools_s + bot_admin_s
    elif is_group_admin:
        mod_s = sec("🛡 Moderation — Group Admins", [
            ("ban", "@user <reason> — Ban"), ("kick", "@user — Kick"),
            ("mute", "@user — Mute"), ("warn", "@user <reason> — Warn"),
            ("pin", "Pin replied message"), ("setrules", "<text> — Set rules"),
            ("filter", "<keyword> <reply> — Add filter"), ("purge", "Delete messages"),
        ])
        text = b("📋 Commands — Group Admin View") + "\n\n" + public + anime_s + fun_s + tools_s + mod_s
    else:
        text = b("📋 Commands — User View") + "\n\n" + public + anime_s + fun_s + tools_s

    TELE_MAX = 3800
    pages = []
    current_page = ""
    for chunk in [text[i:i+TELE_MAX] for i in range(0, len(text), TELE_MAX)]:
        pages.append(chunk)

    send_to = update.effective_user.id
    close_kb = InlineKeyboardMarkup([[InlineKeyboardButton("✖️ Close", callback_data="close_message")]])
    sent_any = False
    for i, page_text in enumerate(pages):
        suffix = f"\n\n<i>Page {i+1}/{len(pages)}</i>" if len(pages) > 1 else ""
        kb = close_kb if i == len(pages) - 1 else None
        try:
            await context.bot.send_message(
                chat_id=send_to,
                text=page_text + suffix,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
            sent_any = True
        except Forbidden:
            send_to = update.effective_chat.id
            try:
                await context.bot.send_message(
                    chat_id=send_to,
                    text=page_text + suffix,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                    disable_web_page_preview=True,
                )
                sent_any = True
            except Exception as exc:
                logger.debug(f"cmd_command send failed: {exc}")
        except Exception as exc:
            logger.debug(f"cmd_command DM failed: {exc}")

    if sent_any and send_to == update.effective_user.id and update.effective_chat.id != update.effective_user.id:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=b(small_caps("📋 command list sent to your dm!")),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
