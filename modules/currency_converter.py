# ====================================================================
# PLACE AT: /app/modules/currency_converter.py
# ACTION: Replace existing file
# ====================================================================
"""
currency_converter.py — PTB v20 async with non-blocking HTTP.
Fixes:
  ✅ Async handler
  ✅ ParseMode from telegram.constants
  ✅ Non-blocking via executor
  ✅ Uses free exchangerate-api (no key needed)
"""
import asyncio
import html
import requests

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler

__help__ = """
*Currency Converter*

 ❍ /cash <amount> <from> <to>

Example:
 `/cash 100 USD INR`
 `/cash 50 EUR GBP`
"""


def _convert_sync(amount: float, from_c: str, to_c: str):
    try:
        url  = f"https://api.exchangerate-api.com/v4/latest/{from_c.upper()}"
        data = requests.get(url, timeout=10).json()
        rate = data["rates"].get(to_c.upper())
        if rate is None:
            return None, "Currency not found"
        return round(amount * rate, 4), None
    except Exception as e:
        return None, str(e)


async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    args    = context.args

    if not args or len(args) < 3:
        await message.reply_text(__help__, parse_mode=ParseMode.MARKDOWN)
        return

    try:
        amount = float(args[0])
        from_c = args[1]
        to_c   = args[2]
    except ValueError:
        await message.reply_text("❌ Invalid amount. Usage: /cash 100 USD INR")
        return

    loop          = asyncio.get_event_loop()
    result, error = await loop.run_in_executor(None, _convert_sync, amount, from_c, to_c)

    if error:
        await message.reply_text(f"❌ {html.escape(error)}", parse_mode=ParseMode.HTML)
        return

    await message.reply_text(
        f"💱 <b>{amount} {html.escape(from_c.upper())}</b> = "
        f"<b>{result} {html.escape(to_c.upper())}</b>",
        parse_mode=ParseMode.HTML,
    )


CONVERTER_HANDLER = DisableAbleCommandHandler("cash", convert, run_async=True)
dispatcher.add_handler(CONVERTER_HANDLER)

__mod_name__     = "Cᴜʀʀᴇɴᴄʏ"
__command_list__ = ["cash"]
__handlers__     = [CONVERTER_HANDLER]
