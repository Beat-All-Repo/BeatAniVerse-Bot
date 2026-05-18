# ====================================================================
# PLACE AT: /app/modules/wiki.py
# ACTION: Replace existing file
# ====================================================================
"""
wiki.py — Wikipedia lookup. PTB v20 async.
Fixes:
  ✅ Async handler
  ✅ ParseMode from telegram.constants
  ✅ Non-blocking wikipedia lookup (executor)
  ✅ await on bot.send_document
  ✅ HTML-safe output
"""
import asyncio
import html

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler

try:
    import wikipedia
    from wikipedia.exceptions import DisambiguationError, PageError
except ImportError:
    wikipedia = None
    class DisambiguationError(Exception): pass
    class PageError(Exception): pass


def _wiki_search_sync(search: str):
    if not wikipedia:
        return None, None, None
    try:
        summary = wikipedia.summary(search, sentences=5)
        url     = wikipedia.page(search).url
        return summary, url, None
    except DisambiguationError as e:
        return None, None, f"Disambiguation: {e.options[:5]}"
    except PageError as e:
        return None, None, f"Page not found: {e}"
    except Exception as e:
        return None, None, str(e)


async def wiki(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    # Support /wiki <query> or reply to a message
    if context.args:
        search = " ".join(context.args)
    elif message.reply_to_message and message.reply_to_message.text:
        search = message.reply_to_message.text.strip()
    else:
        await message.reply_text("Usage: /wiki <topic>")
        return

    if not wikipedia:
        await message.reply_text("❌ <code>wikipedia</code> package not installed.", parse_mode=ParseMode.HTML)
        return

    loop                   = asyncio.get_event_loop()
    summary, url, err_msg  = await loop.run_in_executor(None, _wiki_search_sync, search)

    if err_msg:
        await message.reply_text(f"⚠️ {html.escape(err_msg)}", parse_mode=ParseMode.HTML)
        return

    if not summary:
        await message.reply_text("No results found.")
        return

    url_html = f'\n\n<a href="{url}">📖 Read more on Wikipedia</a>' if url else ""
    result   = f"<b>{html.escape(search)}</b>\n\n{html.escape(summary)}{url_html}"

    if len(result) > 4000:
        # Send as file
        try:
            fname = "wiki_result.txt"
            with open(fname, "w") as f:
                f.write(f"{search}\n\n{summary}\n\n{url or ''}")
            with open(fname, "rb") as f:
                await context.bot.send_document(
                    document=f,
                    filename=fname,
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=message.message_id,
                )
        except Exception as exc:
            await message.reply_text(result[:4096], parse_mode=ParseMode.HTML,
                                     disable_web_page_preview=True)
    else:
        await message.reply_text(result, parse_mode=ParseMode.HTML,
                                 disable_web_page_preview=True)


WIKI_HANDLER = DisableAbleCommandHandler("wiki", wiki, run_async=True)
dispatcher.add_handler(WIKI_HANDLER)

__help__         = "» /wiki <topic> — Look up a topic on Wikipedia."
__mod_name__     = "Wɪᴋɪ"
__command_list__ = ["wiki"]
__handlers__     = [WIKI_HANDLER]
