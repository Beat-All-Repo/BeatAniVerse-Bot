# ====================================================================
# PLACE AT: /app/modules/animequotes.py
# ACTION: Replace existing file
# ====================================================================
"""
modules/animequotes.py
======================
Random anime quote via animechan.io — PTB v20 async, HTML formatting.
Fixes:
  ✅ PTB v20 async handler (was sync PTB v13)
  ✅ ParseMode imported from telegram.constants (not telegram)
  ✅ Markdown-style formatting replaced with proper HTML
  ✅ Non-blocking HTTP via asyncio executor
  ✅ Correct ContextTypes.DEFAULT_TYPE signature
"""

import asyncio
import html
import logging
import requests

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler

logger = logging.getLogger(__name__)

ANIMECHAN_API = "https://animechan.io/api/v1/quotes/random"


def _fetch_quote_sync() -> dict:
    """Blocking HTTP call — run in executor so it doesn't freeze the event loop."""
    try:
        resp = requests.get(ANIMECHAN_API, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug(f"[animequote] fetch error: {exc}")
        return {}


async def animequote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a random anime quote. Async PTB v20 handler."""
    message = update.effective_message

    try:
        loop     = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _fetch_quote_sync)
        data      = response.get("data", {})
        quote     = data.get("content", "").strip()
        character = (data.get("character") or {}).get("name", "Unknown")
        anime     = (data.get("anime") or {}).get("name", "Unknown")
    except Exception as exc:
        logger.debug(f"[animequote] parse error: {exc}")
        await message.reply_text("⚠️ Couldn't fetch a quote right now. Try again later!")
        return

    if not quote:
        await message.reply_text("⚠️ No quote returned. Try again later!")
        return

    msg = (
        f" <blockquote expandable><i>{html.escape(quote)}</i></blockquote>\n\n"
        f"— <b>{html.escape(character)}</b>\n"
        f" <code>{html.escape(anime)}</code>"
    )
    await message.reply_text(msg, parse_mode=ParseMode.HTML)


__help__ = """
*Anime Quotes:*

 • `/aq`*:* get a random anime quote
 • `/animequote`*:* same as /aq
"""

AQ_HANDLER = DisableAbleCommandHandler(["aq", "animequote"], animequote, run_async=True)

dispatcher.add_handler(AQ_HANDLER)

__mod_name__     = "AnimeQuotes"
__command_list__ = ["aq", "animequote"]
__handlers__     = [AQ_HANDLER]
