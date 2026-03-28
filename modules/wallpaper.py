# ==============================================================================
# PLACE AT: /app/modules/wallpaper.py
# ACTION: Replace existing file
# ==============================================================================
"""wallpaper.py — /wall and /wallpaper commands, PTB v21 compatible."""
import random
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from beataniversebot_compat import dispatcher, pbot

logger = logging.getLogger(__name__)

_WALL_APIS = [
    lambda q: f"https://api.safone.me/wall?query={q}",
]


async def wall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/wall <query> — Get an anime wallpaper."""
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> /wall &lt;query&gt;\n<b>Example:</b> /wall Demon Slayer",
            parse_mode=ParseMode.HTML
        )
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text("`Searching for wallpapers...`", parse_mode=ParseMode.MARKDOWN)

    try:
        url = requests.get(f"https://api.safone.me/wall?query={query}", timeout=10).json()
        results = url.get("results", [])
        if not results:
            await msg.edit_text(f"`No wallpaper found for: {query}`", parse_mode=ParseMode.MARKDOWN)
            return
        chosen = random.choice(results[:5])
        img_url = chosen.get("imageUrl") or chosen.get("url", "")
        if not img_url:
            raise ValueError("No image URL")
        user = update.effective_user
        caption = f"🥀 <b>ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ :</b> {user.first_name if user else 'User'}"
        await update.message.reply_photo(
            photo=img_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ʟɪɴᴋ", url=img_url)]]),
        )
        await msg.delete()
    except Exception as exc:
        await msg.edit_text(f"`Wallpaper not found for: {query}`", parse_mode=ParseMode.MARKDOWN)
        logger.debug(f"wall_cmd error: {exc}")


# Legacy Pyrogram handler (stub if pyrogram not available)
try:
    from pyrogram import filters
    from pyrogram.types import InlineKeyboardButton as PyroBtn, InlineKeyboardMarkup as PyroMarkup
    @pbot.on_message(filters.command(["wall", "wallpaper"]))
    async def wall_pyro(_, message):
        try:
            query = message.text.split(None, 1)[1]
        except IndexError:
            return await message.reply_text("`Please give some query to search.`")
        m = await message.reply_text("`Searching for wallpapers...`")
        try:
            results = requests.get(f"https://api.safone.me/wall?query={query}", timeout=10).json().get("results", [])
            if not results:
                return await m.edit_text(f"`No wallpaper found for: {query}`")
            img_url = random.choice(results[:5]).get("imageUrl", "")
            await message.reply_photo(
                photo=img_url,
                caption=f"🥀 **ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ :** {message.from_user.mention}",
                reply_markup=PyroMarkup([[PyroBtn("ʟɪɴᴋ", url=img_url)]]),
            )
            await m.delete()
        except Exception as e:
            await m.edit_text(f"`Wallpaper not found for: {query}`")
except Exception:
    pass

# Register PTB handler via dispatcher shim
try:
    from modules.disable import DisableAbleCommandHandler
    dispatcher.add_handler(DisableAbleCommandHandler(["wall", "wallpaper"], wall_cmd, run_async=True))
except Exception:
    pass

__mod_name__ = "Wᴀʟʟᴘᴀᴘᴇʀ"
__command_list__ = ["wall", "wallpaper"]
__help__ = """
<b>Who can use:</b> Everyone

<b>Commands:</b>
/wall &lt;query&gt; — Get an anime wallpaper
/wallpaper &lt;query&gt; — Same as /wall

<b>Example:</b> /wall Demon Slayer
"""
