# ====================================================================
# PLACE AT: /app/modules/source.py
# ACTION: Replace existing file
# ====================================================================
from platform import python_version as y

try:
    from pyrogram import __version__ as z
except ImportError:
    z = "N/A"
try:
    from pyrogram import filters
except ImportError:
    filters = None
try:
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message as PyroMessage
except ImportError:
    PyroMessage = None
from telegram import __version__ as o
from telethon import __version__ as s

from beataniversebot_compat import BOT_NAME, BOT_USERNAME, OWNER_ID, START_IMG, pbot


@pbot.on_message(filters.command(["repo", "source"]))
async def repo(_, message):
    await message.reply_photo(
        photo=START_IMG,
        caption=f"""**ʜᴇʏ {message.from_user.mention},

ɪ ᴀᴍ [{BOT_NAME}](https://t.me/{BOT_USERNAME})**

**» ᴍʏ ᴅᴇᴠᴇʟᴏᴘᴇʀ :** [Beat](https://t.me/BeatAnime)
**» ᴩʏᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :** `{y()}`
**» ʟɪʙʀᴀʀʏ ᴠᴇʀsɪᴏɴ :** `{o}` 
**» ᴛᴇʟᴇᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :** `{s}` 
**» ᴘʏʀᴏɢʀᴀᴍ ᴠᴇʀsɪᴏɴ :** `{z}`
""",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", user_id=OWNER_ID),
                    InlineKeyboardButton(
                        "ᴄʜᴀɴɴᴇʟ",
                        url="https://t.me/BeatAnime",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "sᴜᴩᴩᴏʀᴛ ɢʀᴏᴜᴩ",
                        url="https://t.me/Beat_Anime_Discussion",
                    ),
                ],
            ]
        ),
    )


__mod_name__ = "Rᴇᴩᴏ"
