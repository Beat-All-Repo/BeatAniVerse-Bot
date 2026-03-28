# ==============================================================================
# PLACE AT: /app/modules/alive.py
# ACTION: Replace existing file
# ==============================================================================
"""
alive.py — /alive command, works with PTB v21 + pyrogram stub.

Features:
  ✅ Each info item in its own blockquote (version, telethon, pyrogram all separate)
  ✅ Help button uses callback_data → opens help panel inline (no broken URL)
  ✅ Support button opens support chat URL
  ✅ Panel image = same image as user welcome panel (get_panel_pic)
  ✅ Single response only — no duplicates
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from beataniversebot_compat import BOT_NAME, BOT_USERNAME, OWNER_ID, SUPPORT_CHAT, dispatcher

logger = logging.getLogger(__name__)

try:
    from telegram import __version__ as telever
except Exception:
    telever = "N/A"
try:
    from telethon import __version__ as tlhver
except Exception:
    tlhver = "N/A"
try:
    from pyrogram import __version__ as pyrover
except Exception:
    pyrover = "N/A"


def _get_welcome_panel_image() -> str:
    """
    Get the same image used on the user welcome/start panel.
    Uses get_panel_pic() — the exact same priority chain as the start panel:
      1. Manually added images via /addpanelimg (DB)
      2. PANEL_IMAGE_FILE_ID env
      3. Session file_id cache from channel scan
      4. PANEL_PICS env
    """
    try:
        from bot import get_panel_pic
        img = get_panel_pic("default")
        if img:
            return img
    except Exception:
        pass
    # Fallback: try env_START_IMG from DB override
    try:
        from database_dual import get_setting
        db_val = get_setting("env_START_IMG", "") or ""
        if db_val:
            return db_val
    except Exception:
        pass
    # Last fallback: START_IMG env
    try:
        from beataniversebot_compat import START_IMG
        return START_IMG or ""
    except Exception:
        pass
    return ""


async def alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/alive — show bot status with version info, separate blockquotes per item."""
    user    = update.effective_user
    mention = f'<a href="tg://user?id={user.id}">{user.first_name}</a>' if user else "you"

    # Each info block in its own expandable blockquote
    text = (
        f"<b>ʜᴇʏ {mention},\n\nɪ ᴀᴍ {BOT_NAME}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        f"» <b>ᴍʏ ᴅᴇᴠᴇʟᴏᴘᴇʀ :</b> <a href='https://t.me/BeatAnime'>Beat</a>\n\n"
        # Each version in its own blockquote
        f"<blockquote>» <b>ʟɪʙʀᴀʀʏ ᴠᴇʀsɪᴏɴ :</b> <code>{telever}</code></blockquote>\n"
        f"<blockquote>» <b>ᴛᴇʟᴇᴛʜᴏɴ ᴠᴇʀsɪᴏɴ :</b> <code>{tlhver}</code></blockquote>\n"
        f"<blockquote>» <b>ᴘʏʀᴏɢʀᴀᴍ ᴠᴇʀsɪᴏɴ :</b> <code>{pyrover}</code></blockquote>\n"
        "━━━━━━━━━━━━━━━━━\n\n"
    )

    # Help button uses callback_data so it opens the actual help panel inline
    # NOT a URL — URL form breaks on link bots ("link does not exist")
    buttons = [[
        InlineKeyboardButton("ʜᴇʟᴘ",    callback_data="user_help"),
        InlineKeyboardButton("sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}"),
    ]]
    markup = InlineKeyboardMarkup(buttons)

    # Use same image as user welcome/start panel
    img = _get_welcome_panel_image()
    if img:
        try:
            await update.message.reply_photo(
                photo=img,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
            return
        except Exception:
            pass

    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


# Register via dispatcher shim for legacy compatibility
try:
    from modules.disable import DisableAbleCommandHandler
    ALIVE_HANDLER = DisableAbleCommandHandler("alive", alive_cmd, run_async=True)
    dispatcher.add_handler(ALIVE_HANDLER)
except Exception:
    pass

__mod_name__     = "Aʟɪᴠᴇ"
__command_list__ = ["alive"]
