# ====================================================================
# PLACE AT: /app/modules/sed.py
# ACTION: Replace existing file
# ====================================================================
"""
sed.py — PTB v20 async.
Fixes:
  ✅ async handler with await
  ✅ filters from telegram.ext.filters (PTB v20)
  ✅ telegram.constants.MessageLimit instead of telegram.MAX_MESSAGE_LENGTH
"""
import sre_constants

try:
    import regex
except ImportError:
    import re as regex

import telegram
from telegram import Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes, filters

from beataniversebot_compat import LOGGER, dispatcher
from modules.disable import DisableAbleMessageHandler
from modules.helper_funcs.regex_helper import infinite_loop_check

DELIMITERS = ("/", ":", "|", "_")


def separate_sed(sed_string: str):
    if (
        len(sed_string) >= 3
        and sed_string[1] in DELIMITERS
        and sed_string.count(sed_string[1]) >= 2
    ):
        delim   = sed_string[1]
        start   = counter = 2
        while counter < len(sed_string):
            if sed_string[counter] == "\\":
                counter += 1
            elif sed_string[counter] == delim:
                replace = sed_string[start:counter]
                counter += 1
                start   = counter
                break
            counter += 1
        else:
            return None

        while counter < len(sed_string):
            if (
                sed_string[counter] == "\\"
                and counter + 1 < len(sed_string)
                and sed_string[counter + 1] == delim
            ):
                sed_string = sed_string[:counter] + sed_string[counter + 1:]
            elif sed_string[counter] == delim:
                replace_with = sed_string[start:counter]
                counter += 1
                break
            counter += 1
        else:
            return replace, sed_string[start:], ""

        flags = sed_string[counter:] if counter < len(sed_string) else ""
        return replace, replace_with, flags.lower()


async def sed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message    = update.effective_message
    sed_result = separate_sed(message.text)

    if not sed_result or not message.reply_to_message:
        return

    to_fix = (
        message.reply_to_message.text
        or message.reply_to_message.caption
        or ""
    )
    if not to_fix:
        return

    repl, repl_with, flags = sed_result
    if not repl:
        await message.reply_to_message.reply_text(
            "You're trying to replace nothing with something?"
        )
        return

    try:
        try:
            check = regex.match(repl, to_fix, flags=regex.IGNORECASE, timeout=5)
        except TimeoutError:
            return

        if check and check.group(0).lower() == to_fix.lower():
            await message.reply_to_message.reply_text(
                f"Hey everyone, {update.effective_user.first_name} is trying to make me say "
                "stuff I don't wanna say!"
            )
            return

        if infinite_loop_check(repl):
            await message.reply_text("I'm afraid I can't run that regex.")
            return

        if "i" in flags and "g" in flags:
            text = regex.sub(repl, repl_with, to_fix, flags=regex.I, timeout=3).strip()
        elif "i" in flags:
            text = regex.sub(repl, repl_with, to_fix, count=1, flags=regex.I, timeout=3).strip()
        elif "g" in flags:
            text = regex.sub(repl, repl_with, to_fix, timeout=3).strip()
        else:
            text = regex.sub(repl, repl_with, to_fix, count=1, timeout=3).strip()

    except TimeoutError:
        await message.reply_text("Regex timed out.")
        return
    except sre_constants.error:
        LOGGER.warning(message.text)
        LOGGER.exception("SRE constant error")
        await message.reply_text("Do you even sed? Apparently not.")
        return

    if not text:
        return

    max_len = getattr(MessageLimit, "MAX_TEXT_LENGTH", None) or getattr(telegram, "MAX_MESSAGE_LENGTH", 4096)
    if len(text) >= max_len:
        await message.reply_text("The result of the sed command was too long for Telegram!")
    else:
        await message.reply_to_message.reply_text(text)


__mod_name__ = "Sed/Regex"

SED_HANDLER = DisableAbleMessageHandler(
    filters.Regex(r"s([{}]).*?\1.*".format("".join(DELIMITERS))),
    sed,
    friendly="sed",
    run_async=True,
)

dispatcher.add_handler(SED_HANDLER)
