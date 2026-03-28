"""handlers/error_handler.py — Central error handler."""
import traceback
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID, OWNER_ID
from core.helpers import UserFriendlyError, safe_answer, safe_send_message
from core.logging_setup import error_logger, logger

try:
    from database_dual import get_setting as _gs
except ImportError:
    def _gs(k, d=""): return d

_error_dm_counts = {}
ERROR_DM_MAX = 5

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    err = context.error
    if not err: return
    error_logger.error(f"Exception: {err}", exc_info=True)
    if UserFriendlyError.is_ignorable(err): return
    if update and update.effective_user:
        uid = update.effective_user.id
        if uid not in (ADMIN_ID, OWNER_ID):
            friendly = UserFriendlyError.get_user_message(err)
            try:
                if update.callback_query: await safe_answer(update.callback_query, "Something went wrong. Please try again.")
                elif update.message: await update.message.reply_text(friendly, parse_mode="HTML")
                elif update.effective_chat: await safe_send_message(context.bot, update.effective_chat.id, friendly)
            except Exception: pass
    if _gs("error_dms_enabled", "1") not in ("0", "false"):
        update_key = getattr(update, "update_id", "global") if update else "global"
        count = _error_dm_counts.get(update_key, 0)
        if count < ERROR_DM_MAX:
            _error_dm_counts[update_key] = count + 1
            context_info = ""
            if update:
                if update.effective_user: context_info += f"User: @{update.effective_user.username or update.effective_user.id}\n"
                if update.effective_chat: context_info += f"Chat: {update.effective_chat.id}\n"
                if update.callback_query: context_info += f"Callback: {update.callback_query.data}\n"
                elif update.message and update.message.text: context_info += f"Text: {update.message.text[:100]}\n"
            admin_msg = UserFriendlyError.get_admin_message(err, context_info)
            try: await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
            except Exception: pass
