# ====================================================================
# PLACE AT: /app/modules/fun.py
# ACTION: Replace existing file
# ====================================================================
"""
fun.py — random fun commands.

FIXES APPLIED:
• Removed /pat and /slap — reactions.py already owns both with GIF responses.
  Having both registered caused every /pat and /slap to fire TWICE.
"""

import html
import random
import time

from telegram import ChatPermissions, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

try:
    import BeatVerseProbot.modules.fun_strings as fun_strings
except ImportError:
    from modules import fun_strings
from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler
from modules.helper_funcs.chat_status import is_user_admin
from modules.helper_funcs.extraction import extract_user


def runs(update: Update, context: CallbackContext):
    update.effective_message.reply_text(random.choice(fun_strings.RUN_STRINGS))


def sanitize(update: Update, context: CallbackContext):
    message = update.effective_message
    name = (
        message.reply_to_message.from_user.first_name
        if message.reply_to_message
        else message.from_user.first_name
    )
    reply_animation = (
        message.reply_to_message.reply_animation
        if message.reply_to_message
        else message.reply_animation
    )
    reply_animation(random.choice(fun_strings.GIFS), caption=f"*Sanitizes {name}*")


def roll(update: Update, context: CallbackContext):
    update.message.reply_text(random.choice(range(1, 7)))


def shout(update: Update, context: CallbackContext):
    args = context.args
    text = " ".join(args)
    result = []
    result.append(" ".join(list(text)))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + " " + "  " * pos + symbol)
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    return update.effective_message.reply_text(msg, parse_mode="MARKDOWN")


def toss(update: Update, context: CallbackContext):
    update.message.reply_text(random.choice(fun_strings.TOSS))


def shrug(update: Update, context: CallbackContext):
    msg = update.effective_message
    reply_text = (
        msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text
    )
    reply_text(r"¯\_(ツ)_/¯")


def bluetext(update: Update, context: CallbackContext):
    msg = update.effective_message
    reply_text = (
        msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text
    )
    reply_text(
        "/BLUE /TEXT\n/MUST /CLICK\n/I /AM /A /STUPID /ANIMAL /THAT /IS /ATTRACTED /TO /COLORS"
    )


def rlg(update: Update, context: CallbackContext):
    eyes = random.choice(fun_strings.EYES)
    mouth = random.choice(fun_strings.MOUTHS)
    ears = random.choice(fun_strings.EARS)

    if len(eyes) == 2:
        repl = ears[0] + eyes[0] + mouth[0] + eyes[1] + ears[1]
    else:
        repl = ears[0] + eyes[0] + mouth[0] + eyes[0] + ears[1]
    update.message.reply_text(repl)


def decide(update: Update, context: CallbackContext):
    reply_text = (
        update.effective_message.reply_to_message.reply_text
        if update.effective_message.reply_to_message
        else update.effective_message.reply_text
    )
    reply_text(random.choice(fun_strings.DECIDE))


def eightball(update: Update, context: CallbackContext):
    reply_text = (
        update.effective_message.reply_to_message.reply_text
        if update.effective_message.reply_to_message
        else update.effective_message.reply_text
    )
    reply_text(random.choice(fun_strings.EIGHTBALL))


def table(update: Update, context: CallbackContext):
    reply_text = (
        update.effective_message.reply_to_message.reply_text
        if update.effective_message.reply_to_message
        else update.effective_message.reply_text
    )
    reply_text(random.choice(fun_strings.TABLE))


__help__ = """
 ❍ /runs*:* reply a random string from an array of replies
 ❍ /shrug*:* get shrug XD
 ❍ /table*:* get flip/unflip :v
 ❍ /decide*:* Randomly answers yes/no/maybe
 ❍ /toss*:* Tosses A coin
 ❍ /bluetext*:* check urself :V
 ❍ /roll*:* Roll a dice
 ❍ /rlg*:* Join ears,nose,mouth and create an emo ;-;
 ❍ /shout <keyword>*:* write anything you want to give loud shout
 ❍ /sanitize*:* always use this before /pat or any contact
 ❍ /8ball*:* predicts using 8ball method

*Note:* /pat and /slap are in the Reactions module (with anime GIFs!).
"""

SANITIZE_HANDLER = DisableAbleCommandHandler("sanitize", sanitize, run_async=True)
RUNS_HANDLER = DisableAbleCommandHandler("runs", runs, run_async=True)
ROLL_HANDLER = DisableAbleCommandHandler("roll", roll, run_async=True)
TOSS_HANDLER = DisableAbleCommandHandler("toss", toss, run_async=True)
SHRUG_HANDLER = DisableAbleCommandHandler("shrug", shrug, run_async=True)
BLUETEXT_HANDLER = DisableAbleCommandHandler("bluetext", bluetext, run_async=True)
RLG_HANDLER = DisableAbleCommandHandler("rlg", rlg, run_async=True)
DECIDE_HANDLER = DisableAbleCommandHandler("decide", decide, run_async=True)
EIGHTBALL_HANDLER = DisableAbleCommandHandler("8ball", eightball, run_async=True)
TABLE_HANDLER = DisableAbleCommandHandler("table", table, run_async=True)
SHOUT_HANDLER = DisableAbleCommandHandler("shout", shout, run_async=True)

dispatcher.add_handler(SHOUT_HANDLER)
dispatcher.add_handler(SANITIZE_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(ROLL_HANDLER)
dispatcher.add_handler(TOSS_HANDLER)
dispatcher.add_handler(SHRUG_HANDLER)
dispatcher.add_handler(BLUETEXT_HANDLER)
dispatcher.add_handler(RLG_HANDLER)
dispatcher.add_handler(DECIDE_HANDLER)
dispatcher.add_handler(EIGHTBALL_HANDLER)
dispatcher.add_handler(TABLE_HANDLER)

__mod_name__ = "Fᴜɴ​"
__command_list__ = [
    "runs",
    "roll",
    "toss",
    "shrug",
    "bluetext",
    "rlg",
    "decide",
    "table",
    "sanitize",
    "shout",
    "8ball",
]
__handlers__ = [
    RUNS_HANDLER,
    ROLL_HANDLER,
    TOSS_HANDLER,
    SHRUG_HANDLER,
    BLUETEXT_HANDLER,
    RLG_HANDLER,
    DECIDE_HANDLER,
    TABLE_HANDLER,
    SANITIZE_HANDLER,
    SHOUT_HANDLER,
    EIGHTBALL_HANDLER,
]
