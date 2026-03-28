# ====================================================================
# PLACE AT: /app/modules/reactions.py
# ACTION: Replace existing file
# ====================================================================
"""
reactions.py — anime GIF reactions, fully async for PTB v20+

FIXES:
• All handlers are now async — ParseMode.MARKDOWN removed
• captions use HTML to avoid crashes on names with special chars
• Graceful fallback when nekos.best is down
"""

import asyncio
import html
import logging
import requests

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

logger = logging.getLogger(__name__)

NEKOS_API = "https://nekos.best/api/v2/{}"

_FALLBACK_GIFS = {
    "hug":   "https://media.giphy.com/media/od5H3PmEG5EVq/giphy.gif",
    "pat":   "https://media.giphy.com/media/ARSp9T7wwxNcs/giphy.gif",
    "slap":  "https://media.giphy.com/media/jLeyZWgtwgr2U/giphy.gif",
    "kiss":  "https://media.giphy.com/media/bGm9FuBCGg4SY/giphy.gif",
    "poke":  "https://media.giphy.com/media/6cFcUiCG5eONW/giphy.gif",
    "wave":  "https://media.giphy.com/media/MEXT0bAbH8tDm/giphy.gif",
    "bite":  "https://media.giphy.com/media/11e0gp6YNbXhba/giphy.gif",
    "punch": "https://media.giphy.com/media/xUOwFZuBzNqDqmcJja/giphy.gif",
    "nod":   "https://media.giphy.com/media/TZEV8RMmOBM8g/giphy.gif",
    "shoot": "https://media.giphy.com/media/xUA7b7dY8UMTVMlYXS/giphy.gif",
    "wink":  "https://media.giphy.com/media/bc9PGg9n8ASrq/giphy.gif",
    "cry":   "https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif",
    "laugh": "https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif",
    "blush": "https://media.giphy.com/media/3o6UB3VhArvomJHtdK/giphy.gif",
}


async def _fetch_gif(action: str):
    loop = asyncio.get_event_loop()
    try:
        def _get():
            return requests.get(NEKOS_API.format(action), timeout=8).json()
        data = await loop.run_in_executor(None, _get)
        result = data["results"][0]
        return result["url"], result.get("anime_name", "")
    except Exception as exc:
        logger.debug(f"[reactions] nekos.best/{action} failed: {exc}")
        return _FALLBACK_GIFS.get(action, ""), ""


async def _send_reaction(update, context, action, verb, emoji):
    message = update.effective_message
    if not message:
        return
    sender = html.escape(update.effective_user.first_name or "Someone")
    gif_url, anime_name = await _fetch_gif(action)
    if message.reply_to_message and message.reply_to_message.from_user:
        target = html.escape(message.reply_to_message.from_user.first_name or "someone")
        caption = f"{emoji} <b>{sender}</b> {verb} <b>{target}</b>!"
    else:
        caption = f"{emoji} <b>{sender}</b> wants to {action} someone!"
    if anime_name:
        caption += f"\n<i>From: {html.escape(anime_name)}</i>"
    if gif_url:
        try:
            await message.reply_animation(animation=gif_url, caption=caption, parse_mode=ParseMode.HTML)
            return
        except Exception as exc:
            logger.debug(f"[reactions] reply_animation failed: {exc}")
    await message.reply_text(caption, parse_mode=ParseMode.HTML)


async def hug(update, context):   await _send_reaction(update, context, "hug",   "hugs",        "🤗")
async def pat(update, context):   await _send_reaction(update, context, "pat",   "pats",        "👋")
async def slap(update, context):  await _send_reaction(update, context, "slap",  "slaps",       "👋")
async def kiss(update, context):  await _send_reaction(update, context, "kiss",  "kisses",      "💋")
async def poke(update, context):  await _send_reaction(update, context, "poke",  "pokes",       "👉")
async def wave(update, context):  await _send_reaction(update, context, "wave",  "waves at",    "👋")
async def bite(update, context):  await _send_reaction(update, context, "bite",  "bites",       "😬")
async def punch(update, context): await _send_reaction(update, context, "punch", "punches",     "👊")
async def nod(update, context):   await _send_reaction(update, context, "nod",   "nods at",     "🙂")
async def shoot(update, context): await _send_reaction(update, context, "shoot", "shoots",      "🔫")
async def wink(update, context):  await _send_reaction(update, context, "wink",  "winks at",    "😉")
async def cry(update, context):   await _send_reaction(update, context, "cry",   "is crying",   "😢")
async def laugh(update, context): await _send_reaction(update, context, "laugh", "is laughing", "😂")
async def blush(update, context): await _send_reaction(update, context, "blush", "blushes at",  "😊")


def register(app) -> None:
    for cmd, fn in [
        ("hug", hug), ("pat", pat), ("slap", slap), ("kiss", kiss),
        ("poke", poke), ("wave", wave), ("bite", bite), ("punch", punch),
        ("nod", nod), ("shoot", shoot), ("wink", wink), ("cry", cry),
        ("laugh", laugh), ("blush", blush),
    ]:
        app.add_handler(CommandHandler(cmd, fn))
    logger.info("[reactions] Handlers registered")


# Legacy PTB v13 compat
try:
    from beataniversebot_compat import dispatcher
    from modules.disable import DisableAbleCommandHandler
    for _cmd, _fn in [
        ("hug", hug), ("pat", pat), ("slap", slap), ("kiss", kiss),
        ("poke", poke), ("wave", wave), ("bite", bite), ("punch", punch),
        ("nod", nod), ("shoot", shoot), ("wink", wink), ("cry", cry),
        ("laugh", laugh), ("blush", blush),
    ]:
        dispatcher.add_handler(DisableAbleCommandHandler(_cmd, _fn, run_async=True))
except Exception:
    pass


__mod_name__ = "Reactions"
__command_list__ = ["hug","pat","slap","kiss","poke","wave","bite","punch","nod","shoot","wink","cry","laugh","blush"]
__help__ = """
*Anime Reactions:*
 • /hug, /pat, /slap, /kiss, /poke, /wave
 • /bite, /punch, /wink, /cry, /laugh, /blush
_Reply to someone to target them!_
"""
