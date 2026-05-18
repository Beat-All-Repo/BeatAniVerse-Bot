# ====================================================================
# PLACE AT: /app/modules/ud.py
# ACTION: Replace existing file
# ====================================================================
"""
ud.py — Urban Dictionary lookup. PTB v20 async.
Fixes:
  ✅ Async handler
  ✅ ParseMode from telegram.constants
  ✅ Non-blocking HTTP (executor)
  ✅ HTML-escaped output (was using ParseMode.HTML but sending Markdown)
"""
import asyncio
import html
import requests

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler


def _fetch_ud_sync(term: str) -> dict:
    try:
        r = requests.get(
            f"https://api.urbandictionary.com/v0/define?term={term}", timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


async def ud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not context.args:
        await message.reply_text("Usage: /ud <word>")
        return
    term = " ".join(context.args)

    loop    = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _fetch_ud_sync, term)

    items = results.get("list", [])
    if not items:
        await message.reply_text(f"No results found for <b>{html.escape(term)}</b>.", parse_mode=ParseMode.HTML)
        return

    top      = items[0]
    defn     = html.escape(top.get("definition", "N/A"))
    example  = html.escape(top.get("example", ""))
    link     = top.get("permalink", "")

    reply = f"<b>{html.escape(term)}</b>\n\n{defn}"
    if example:
        reply += f"\n\n<i>{example}</i>"
    if link:
        reply += f'\n\n<a href="{link}">📖 View on UD</a>'

    await message.reply_text(reply[:4096], parse_mode=ParseMode.HTML,
                             disable_web_page_preview=True)


UD_HANDLER = DisableAbleCommandHandler(["ud"], ud, run_async=True)
dispatcher.add_handler(UD_HANDLER)

__help__ = "» /ud <word> — Look up a word on Urban Dictionary."
__mod_name__     = "Uʀʙᴀɴ D"
__command_list__ = ["ud"]
__handlers__     = [UD_HANDLER]
