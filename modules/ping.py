# ====================================================================
# PLACE AT: /app/modules/ping.py
# ACTION: Replace existing file
# ====================================================================
"""
modules/ping.py
===============
/ping — measures real Telegram round-trip latency + uptime.
Fully async PTB v20. Compatible with the _LazyDispatcher compat shim.
"""
import time
import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import StartTime, dispatcher
from modules.disable import DisableAbleCommandHandler


def get_readable_time(seconds: int) -> str:
    count       = 0
    ping_time   = ""
    time_list   = []
    time_suffix = ["s", "ᴍ", "ʜ", "ᴅᴀʏs"]

    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Async ping — measures real Telegram round-trip time without blocking the event loop.
    """
    msg = update.effective_message

    start_time = time.time()
    message    = await msg.reply_text("🏓 ᴘɪɴɢɪɴɢ ʙᴀʙʏ....​")
    end_time   = time.time()

    telegram_ping = str(round((end_time - start_time) * 1000, 3)) + " ms"
    uptime        = get_readable_time(int(time.time() - StartTime))

    await message.edit_text(
        "ɪ ᴀᴍ ᴀʟɪᴠᴇ ʙᴀʙʏ! 🖤\n"
        "<b>ᴛɪᴍᴇ ᴛᴀᴋᴇɴ:</b> <code>{}</code>\n"
        "<b>ᴜᴘᴛɪᴍᴇ:</b> <code>{}</code>".format(telegram_ping, uptime),
        parse_mode=ParseMode.HTML,
    )


PING_HANDLER = DisableAbleCommandHandler("ping", ping, run_async=True)
dispatcher.add_handler(PING_HANDLER)

__mod_name__     = "Pɪɴɢ"
__command_list__ = ["ping"]
__handlers__     = [PING_HANDLER]
