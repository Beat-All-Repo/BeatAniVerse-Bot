# ====================================================================
# PLACE AT: /app/modules/help.py
# ACTION: Replace existing file
# ====================================================================
"""
help.py — only handles the ❌ Close button callback.

WHY THIS IS STRIPPED DOWN:
• __main__.py already registers /start, /help, and all help_* callbacks.
• The old _load_modules() here re-imported every module at load time,
  causing a circular import crash on startup.
• Registering duplicate /start + /help handlers caused the bot to reply
  twice to every command.
• Only the "close" callback (delete the message) was missing from __main__.py,
  so that is the only thing registered here.
"""

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler

from beataniversebot_compat import dispatcher


def close_button(update: Update, context: CallbackContext):
    """Delete the message when the ❌ Close button is pressed."""
    query = update.callback_query
    try:
        query.answer()
    except Exception:
        pass
    try:
        query.message.delete()
    except Exception:
        pass


CLOSE_HANDLER = CallbackQueryHandler(
    close_button, pattern=r"^close$", run_async=True
)

dispatcher.add_handler(CLOSE_HANDLER)

__mod_name__ = "Help"
__handlers__ = [CLOSE_HANDLER]
