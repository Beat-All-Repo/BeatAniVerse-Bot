# ====================================================================
# PLACE AT: /app/modules/misc.py
# ACTION: Replace existing file
# ====================================================================
"""
misc.py — PTB v20 async.
Fixes:
  ✅ All handlers async + await
  ✅ ParseMode from telegram.constants
  ✅ filters from telegram.ext.filters (PTB v20)
  ✅ CommandHandler from telegram.ext (no run_async kwarg needed)
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes, filters

from beataniversebot_compat import BOT_NAME, dispatcher
from modules.disable import DisableAbleCommandHandler
from modules.helper_funcs.chat_status import user_admin

MARKDOWN_HELP = f"""
Markdown is a very powerful formatting tool. {BOT_NAME} supports it for saved messages and buttons.

• <code>_italic_</code>: italic text
• <code>*bold*</code>: bold text
• <code>`code`</code>: monospace / code
• <code>[sometext](someURL)</code>: hyperlink
• <code>[buttontext](buttonurl:someURL)</code>: inline button

Multiple buttons on one line:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
"""


@user_admin
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args    = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if len(args) < 2:
        return

    if message.reply_to_message:
        await message.reply_to_message.reply_text(
            args[1], parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    else:
        await message.reply_text(
            args[1], quote=False, parse_mode="MARKDOWN", disable_web_page_preview=True
        )
    try:
        await message.delete()
    except Exception:
        pass


async def markdown_help_sender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    await msg.reply_text(MARKDOWN_HELP, parse_mode=ParseMode.HTML)
    await msg.reply_text("Try forwarding the following message to me, and you'll see it in action!")
    await msg.reply_text(
        "/save test This is a markdown test. _italics_, *bold*, code, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)"
    )


async def markdown_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        await update.effective_message.reply_text(
            "Contact me in PM for the Markdown guide.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Markdown help",
                    url=f"t.me/{context.bot.username}?start=markdownhelp",
                )
            ]]),
        )
        return
    await markdown_help_sender(update, context)


__help__ = """
*Available commands:*

*Markdown:*
 ❍ /markdownhelp — quick summary of Markdown (PM only)

*Other:*
 ❍ /ud <word> — Urban Dictionary lookup
 ❍ /wiki <query> — Wikipedia lookup
"""

ECHO_HANDLER    = DisableAbleCommandHandler(
    "echo", echo, filters=filters.ChatType.GROUPS, run_async=True
)
MD_HELP_HANDLER = CommandHandler("markdownhelp", markdown_help)

dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)

__mod_name__     = "Exᴛʀᴀs"
__command_list__ = ["echo", "markdownhelp"]
__handlers__     = [ECHO_HANDLER, MD_HELP_HANDLER]
