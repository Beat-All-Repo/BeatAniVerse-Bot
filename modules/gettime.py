# ====================================================================
# PLACE AT: /app/modules/gettime.py
# ACTION: Replace existing file
# ====================================================================
"""
gettime.py — Timezone lookup. PTB v20 async.
Fixes:
  ✅ Async handler
  ✅ ParseMode from telegram.constants
  ✅ Non-blocking HTTP (executor)
  ✅ await on reply/edit calls
  ✅ Graceful fallback when TIME_API_KEY not set
"""
import asyncio
import datetime
import html
from typing import List, Optional

import requests

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler

try:
    from beataniversebot_compat import TIME_API_KEY
except ImportError:
    TIME_API_KEY = ""


def _generate_time_sync(to_find: str, findtypes: List[str]) -> Optional[str]:
    if not TIME_API_KEY:
        return None
    try:
        data = requests.get(
            "https://api.timezonedb.com/v2.1/list-time-zone"
            f"?key={TIME_API_KEY}&format=json"
            "&fields=countryCode,countryName,zoneName,gmtOffset,timestamp,dst",
            timeout=10,
        ).json()
    except Exception:
        return None

    for zone in data.get("zones", []):
        for ft in findtypes:
            if to_find in zone.get(ft, "").lower():
                dst = "Yes" if zone.get("dst") == 1 else "No"
                ts  = (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(seconds=zone.get("gmtOffset", 0))
                )
                return (
                    f"<b>Country:</b> <code>{html.escape(zone['countryName'])}</code>\n"
                    f"<b>Zone:</b> <code>{html.escape(zone['zoneName'])}</code>\n"
                    f"<b>Code:</b> <code>{html.escape(zone['countryCode'])}</code>\n"
                    f"<b>Daylight Saving:</b> <code>{dst}</code>\n"
                    f"<b>Day:</b> <code>{ts.strftime('%A')}</code>\n"
                    f"<b>Time:</b> <code>{ts.strftime('%H:%M:%S')}</code>\n"
                    f"<b>Date:</b> <code>{ts.strftime('%d-%m-%Y')}</code>\n"
                    '<b>Timezones:</b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">Full list</a>'
                )
    return None


async def gettime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    if not context.args:
        await message.reply_text("Usage: /time <country name / code / timezone>")
        return

    query = " ".join(context.args)

    if not TIME_API_KEY:
        await message.reply_text(
            "⚠️ <b>TIME_API_KEY</b> not configured. "
            "Get a free key at <a href=\"https://timezonedb.com/register\">timezonedb.com</a> and add it to your env.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    loading = await message.reply_text(
        f"⏳ Looking up timezone for <b>{html.escape(query)}</b>...",
        parse_mode=ParseMode.HTML,
    )

    q_lower    = query.lower()
    findtypes  = ["countryCode"] if len(q_lower) == 2 else ["zoneName", "countryName"]
    loop       = asyncio.get_event_loop()
    result     = await loop.run_in_executor(None, _generate_time_sync, q_lower, findtypes)

    if not result:
        await loading.edit_text(
            f"❌ No timezone found for <b>{html.escape(query)}</b>.\n"
            '<b>List of timezones:</b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">Wikipedia</a>',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    await loading.edit_text(result, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


__help__ = """
 ❍ /time <query> — Shows timezone info for a country/city.

Examples: `/time IN`  `/time India`  `/time Asia/Kolkata`
"""

TIME_HANDLER = DisableAbleCommandHandler("time", gettime, run_async=True)
dispatcher.add_handler(TIME_HANDLER)

__mod_name__     = "Tɪᴍᴇ"
__command_list__ = ["time"]
__handlers__     = [TIME_HANDLER]
