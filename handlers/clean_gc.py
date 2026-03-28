"""handlers/clean_gc.py — Clean group chat: delete service messages and commands."""
import asyncio
from telegram import Update
from telegram.ext import ContextTypes

async def _clean_gc_service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    try:
        from database_dual import get_setting
        if get_setting("clean_gc_enabled", "true") != "true": return
    except Exception: pass
    try: await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
    except Exception: pass

async def _clean_gc_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat: return
    try:
        from database_dual import get_setting
        if get_setting("clean_gc_enabled", "true") != "true": return
    except Exception: pass
    msg = update.message
    chat_id, msg_id = msg.chat_id, msg.message_id
    async def _delayed_del():
        await asyncio.sleep(3)
        try: await context.bot.delete_message(chat_id, msg_id)
        except Exception: pass
    asyncio.create_task(_delayed_del())
