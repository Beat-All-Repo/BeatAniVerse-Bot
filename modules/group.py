# ==============================================================================
# PLACE AT: /app/modules/group.py
# ACTION: Replace existing file
# ==============================================================================
"""group.py — Group management commands (PTB v21 compatible)."""
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler
from beataniversebot_compat import dispatcher, LOGGER

logger = logging.getLogger(__name__)


async def setgtitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setgtitle <title> — Set group title (admin only)."""
    if not update.message or not update.effective_chat or not context.args:
        await update.message.reply_text("<b>Usage:</b> /setgtitle &lt;new title&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ Admin only.")
            return
    except Exception:
        return
    title = " ".join(context.args)
    try:
        await context.bot.set_chat_title(update.effective_chat.id, title)
        await update.message.reply_text(f"✅ Group title set to: <b>{title}</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {str(e)[:100]}", parse_mode=ParseMode.HTML)


async def setgpic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setgpic — Set group photo (reply to image)."""
    if not update.message or not update.effective_chat:
        return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ Admin only.")
            return
    except Exception:
        return
    reply = update.message.reply_to_message
    if not reply or not reply.photo:
        await update.message.reply_text("Reply to a photo to set it as group picture.")
        return
    try:
        file = await context.bot.get_file(reply.photo[-1].file_id)
        from io import BytesIO
        data = BytesIO()
        await file.download_to_memory(data)
        data.seek(0)
        await context.bot.set_chat_photo(update.effective_chat.id, data)
        await update.message.reply_text("✅ Group photo updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {str(e)[:100]}")


async def delgpic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/delgpic — Remove group photo (admin only)."""
    if not update.message or not update.effective_chat:
        return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ Admin only.")
            return
    except Exception:
        return
    try:
        await context.bot.delete_chat_photo(update.effective_chat.id)
        await update.message.reply_text("✅ Group photo removed!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {str(e)[:100]}")


async def setdescription_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setdescription <text> — Set group description (admin only)."""
    if not update.message or not update.effective_chat or not context.args:
        await update.message.reply_text("<b>Usage:</b> /setdescription &lt;text&gt;", parse_mode=ParseMode.HTML)
        return
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ Admin only.")
            return
    except Exception:
        return
    desc = " ".join(context.args)
    try:
        await context.bot.set_chat_description(update.effective_chat.id, desc)
        await update.message.reply_text("✅ Group description updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {str(e)[:100]}")


# Register via dispatcher shim
try:
    from modules.disable import DisableAbleCommandHandler
    for cmd, fn in [
        ("setgtitle",     setgtitle_cmd),
        ("setgpic",       setgpic_cmd),
        ("delgpic",       delgpic_cmd),
        ("setdescription",setdescription_cmd),
    ]:
        dispatcher.add_handler(DisableAbleCommandHandler(cmd, fn, run_async=True))
except Exception:
    pass

__mod_name__ = "Gʀᴏᴜᴘ"
__command_list__ = ["setgtitle", "setgpic", "delgpic", "setdescription"]
__help__ = """
<b>Who can use:</b> Group admins & owner only

<b>Commands:</b>
/setgtitle &lt;title&gt; — Change group title
/setgpic — Set group photo (reply to an image)
/delgpic — Remove group photo
/setdescription &lt;text&gt; — Set group description
"""
