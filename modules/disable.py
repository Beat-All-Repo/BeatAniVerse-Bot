# ====================================================================
# PLACE AT: /app/modules/disable.py
# ACTION: Replace existing file
# ====================================================================
"""
disable.py — PTB v21 compatible
Removed broken check_update() overrides that used removed PTB v13 APIs:
  - message.bot  → AttributeError in v21
  - self.filters(update) → TypeError: _MergedFilter not callable in v21
"""
import importlib
from typing import Union

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters as tg_filters,
)

try:
    from telegram.utils.helpers import escape_markdown
except ImportError:
    from telegram.helpers import escape_markdown

from beataniversebot_compat import dispatcher
from modules.helper_funcs.handlers import CMD_STARTERS, SpamChecker
from modules.helper_funcs.misc import is_module_loaded

FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from modules.helper_funcs.chat_status import (
        connection_status,
        is_user_admin,
        user_admin,
    )
    from modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        """
        PTB v21 compatible DisableAbleCommandHandler.
        Does NOT override check_update() — uses parent PTB v21 implementation
        which is correct and doesn't use removed APIs.
        """
        def __init__(self, command, callback, admin_ok=False, **kwargs):
            # Strip PTB v13 run_async kwarg silently
            kwargs.pop("run_async", None)
            super().__init__(command, callback, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, str):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)

    class DisableAbleMessageHandler(MessageHandler):
        """
        PTB v21 compatible DisableAbleMessageHandler.
        Does NOT override check_update() — uses parent PTB v21 implementation.
        """
        def __init__(self, filters, callback, friendly="", **kwargs):
            kwargs.pop("run_async", None)
            super().__init__(filters, callback, **kwargs)
            DISABLE_OTHER.append(friendly)
            self.friendly = friendly

    class DisableAbleRegexHandler(MessageHandler):
        """PTB v21 compat: RegexHandler removed, use MessageHandler with regex filter."""
        def __init__(self, pattern, callback, friendly="", filters=None, **kwargs):
            kwargs.pop("run_async", None)
            import re
            from telegram.ext import filters as F
            regex_filter = F.Regex(pattern)
            if filters:
                try:
                    combined = regex_filter & filters
                except Exception:
                    combined = regex_filter
            else:
                combined = regex_filter
            super().__init__(combined, callback, **kwargs)
            DISABLE_OTHER.append(friendly)
            self.friendly = friendly

    # ── Disable/enable commands ───────────────────────────────────────────────

    @user_admin
    def disable(update: Update, context: CallbackContext):
        chat = update.effective_chat
        if len(context.args) >= 1:
            disable_cmd = context.args[0]
            if disable_cmd.startswith("/"):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in DISABLE_CMDS:
                sql.disable_command(chat.id, disable_cmd)
                update.effective_message.reply_text(
                    f"Disabled the use of `/{disable_cmd}` in this group."
                )
            else:
                update.effective_message.reply_text(
                    f"That command can't be disabled — it is either invalid or admin-only."
                )
        else:
            update.effective_message.reply_text("What should I disable?")

    @user_admin
    def enable(update: Update, context: CallbackContext):
        chat = update.effective_chat
        if len(context.args) >= 1:
            enable_cmd = context.args[0]
            if enable_cmd.startswith("/"):
                enable_cmd = enable_cmd[1:]
            if sql.enable_command(chat.id, enable_cmd):
                update.effective_message.reply_text(
                    f"Enabled the use of `/{enable_cmd}` in this group."
                )
            else:
                update.effective_message.reply_text(
                    "Is that even disabled?"
                )
        else:
            update.effective_message.reply_text("What should I enable?")

    @user_admin
    def disable_module(update: Update, context: CallbackContext):
        chat = update.effective_chat
        if len(context.args) >= 1:
            module = context.args[0].lower()
            cmds = [c for c in DISABLE_CMDS]
            disabled = []
            for cmd in cmds:
                sql.disable_command(chat.id, cmd)
                disabled.append(cmd)
            if disabled:
                update.effective_message.reply_text(
                    f"Disabled: {', '.join(disabled)}"
                )
            else:
                update.effective_message.reply_text("Nothing to disable.")
        else:
            update.effective_message.reply_text("Specify a module.")

    @user_admin
    def enable_module(update: Update, context: CallbackContext):
        chat = update.effective_chat
        if len(context.args) >= 1:
            disabled_cmds = sql.get_all_disabled(chat.id)
            for cmd in disabled_cmds:
                sql.enable_command(chat.id, cmd)
            update.effective_message.reply_text("Enabled all disabled commands.")
        else:
            update.effective_message.reply_text("Specify a module.")

    def build_curr_disabled(chat_id):
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return "No commands are currently disabled."
        return "Disabled commands:\n" + "\n".join(f"• `/{cmd}`" for cmd in disabled)

    def list_cmds(update: Update, context: CallbackContext):
        if DISABLE_CMDS:
            result = "Toggleable commands:\n" + "\n".join(f"• `/{cmd}`" for cmd in set(DISABLE_CMDS))
        else:
            result = "No toggleable commands available."
        update.effective_message.reply_text(result)

    def commands(update: Update, context: CallbackContext):
        chat = update.effective_chat
        from telegram.constants import ParseMode
        update.effective_message.reply_text(
            build_curr_disabled(chat.id), parse_mode=ParseMode.HTML
        )

    def __stats__():
        return f"• {sql.num_disabled()} disabled items, across {sql.num_chats()} chats."

    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)

    DISABLE_HANDLER       = CommandHandler("disable",       disable,        run_async=True)
    DISABLE_MODULE_HANDLER= CommandHandler("disablemodule", disable_module, run_async=True)
    ENABLE_HANDLER        = CommandHandler("enable",        enable,         run_async=True)
    ENABLE_MODULE_HANDLER = CommandHandler("enablemodule",  enable_module,  run_async=True)
    COMMANDS_HANDLER      = CommandHandler(["cmds", "disabled"], commands,  run_async=True)
    TOGGLE_HANDLER        = CommandHandler("listcmds",      list_cmds,      run_async=True)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(DISABLE_MODULE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(ENABLE_MODULE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)

    __help__ = """
    ❍ /cmds*:* check the current status of disabled commands

    *Admins only:*
    ❍ /enable <cmd name>*:* enable that command
    ❍ /disable <cmd name>*:* disable that command
    ❍ /enablemodule <module name>*:* enable all commands in that module
    ❍ /disablemodule <module name>*:* disable all commands in that module
    ❍ /listcmds*:* list all possible toggleable commands
    """

    __mod_name__ = "Dɪsᴀʙʟᴇ"

else:
    # Fallbacks when module is not loaded — PTB v21 compatible
    DisableAbleCommandHandler = CommandHandler
    DisableAbleMessageHandler = MessageHandler

    class DisableAbleRegexHandler(MessageHandler):
        """PTB v21 compat stub for RegexHandler."""
        def __init__(self, pattern, callback, friendly="", filters=None, **kwargs):
            kwargs.pop("run_async", None)
            import re
            from telegram.ext import filters as F
            combined = F.Regex(pattern)
            super().__init__(combined, callback, **kwargs)
