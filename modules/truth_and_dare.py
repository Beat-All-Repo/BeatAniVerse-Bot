# ====================================================================
# PLACE AT: /app/modules/truth_and_dare.py
# ACTION: Replace existing file
# ====================================================================
"""
truth_and_dare.py — PTB v20 async with executor for blocking HTTP.
"""
import asyncio
import requests

from telegram import Update
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler


def _fetch_truth_sync() -> str:
    try:
        return requests.get("https://api.truthordarebot.xyz/v1/truth",
                            timeout=8).json().get("question", "")
    except Exception:
        return "Would you rather fight one horse-sized duck or 100 duck-sized horses?"


def _fetch_dare_sync() -> str:
    try:
        return requests.get("https://api.truthordarebot.xyz/v1/dare",
                            timeout=8).json().get("question", "")
    except Exception:
        return "Do 10 push-ups right now!"


async def truth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loop = asyncio.get_event_loop()
    q    = await loop.run_in_executor(None, _fetch_truth_sync)
    await update.effective_message.reply_text(f"🤔 <b>Truth:</b>\n{q}",
                                              parse_mode="HTML")


async def dare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loop = asyncio.get_event_loop()
    q    = await loop.run_in_executor(None, _fetch_dare_sync)
    await update.effective_message.reply_text(f"😈 <b>Dare:</b>\n{q}",
                                              parse_mode="HTML")


TRUTH_HANDLER = DisableAbleCommandHandler("truth", truth, run_async=True)
DARE_HANDLER  = DisableAbleCommandHandler("dare",  dare,  run_async=True)

dispatcher.add_handler(TRUTH_HANDLER)
dispatcher.add_handler(DARE_HANDLER)

__help__ = """
*Truth & Dare*

 ❍ /truth — Random truth question
 ❍ /dare  — Random dare challenge
"""
__mod_name__     = "Tʀᴜᴛʜ-Dᴀʀᴇ"
__command_list__ = ["truth", "dare"]
__handlers__     = [TRUTH_HANDLER, DARE_HANDLER]
