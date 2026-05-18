# ====================================================================
# PLACE AT: /app/modules/speed_test.py
# ACTION: Replace existing file
# ====================================================================
"""
speed_test.py — PTB v20 async. Runs speedtest in executor so event loop isn't blocked.
"""
import asyncio

try:
    import speedtest as _speedtest_mod
except ImportError:
    _speedtest_mod = None

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from beataniversebot_compat import DEV_USERS, dispatcher
from modules.disable import DisableAbleCommandHandler
from modules.helper_funcs.chat_status import dev_plus


def _convert(speed):
    return round(int(speed) / 1048576, 2)


def _run_speedtest_sync(mode: str):
    """Blocking speedtest — run in executor. Returns (text_result, image_url_or_None)."""
    if not _speedtest_mod:
        return "❌ `speedtest-cli` not installed.", None
    try:
        st = _speedtest_mod.Speedtest()
        st.get_best_server()
        st.download()
        st.upload()
        result = st.results.dict()
        text = (
            f"📡 <b>Speedtest Result</b>\n"
            f"⬇️ Download: <code>{_convert(result['download'])} Mb/s</code>\n"
            f"⬆️ Upload:   <code>{_convert(result['upload'])} Mb/s</code>\n"
            f"📶 Ping:     <code>{result['ping']} ms</code>\n"
            f"🖥 Server:   <code>{result['server']['name']}, {result['server']['country']}</code>"
        )
        img_url = st.results.share() if mode == "image" else None
        return text, img_url
    except Exception as e:
        return f"❌ Speedtest error: <code>{e}</code>", None


@dev_plus
async def speedtestxyz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("ɪᴍᴀɢᴇ", callback_data="speedtest_image"),
        InlineKeyboardButton("ᴛᴇxᴛ",  callback_data="speedtest_text"),
    ]])
    await update.effective_message.reply_text(
        "Select speedtest output format:", reply_markup=buttons
    )


async def speedtestxyz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or query.from_user.id not in DEV_USERS:
        await query.answer("⛔ Dev only!", show_alert=True)
        return

    mode = "image" if query.data == "speedtest_image" else "text"
    msg  = await update.effective_message.edit_text("⏳ Running speedtest…")

    loop          = asyncio.get_event_loop()
    text, img_url = await loop.run_in_executor(None, _run_speedtest_sync, mode)

    if img_url:
        try:
            await msg.delete()
        except Exception:
            pass
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=img_url,
            caption=text,
            parse_mode=ParseMode.HTML,
        )
    else:
        await msg.edit_text(text, parse_mode=ParseMode.HTML)

    await query.answer()


SPEED_TEST_HANDLER         = DisableAbleCommandHandler("speedtest", speedtestxyz, run_async=True)
SPEED_TEST_CALLBACKHANDLER = CallbackQueryHandler(speedtestxyz_callback, pattern=r"speedtest_.*")

dispatcher.add_handler(SPEED_TEST_HANDLER)
dispatcher.add_handler(SPEED_TEST_CALLBACKHANDLER)

__help__         = "» /speedtest — Check server network speed (dev only)."
__mod_name__     = "SᴘᴇᴇᴅTᴇsᴛ"
__command_list__ = ["speedtest"]
__handlers__     = [SPEED_TEST_HANDLER, SPEED_TEST_CALLBACKHANDLER]
