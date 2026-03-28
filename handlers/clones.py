"""
handlers/clones.py
==================
Clone bot management: launching, registering, managing clone bots.
"""
import asyncio
from typing import Dict, Any

from telegram import Bot, Update
from telegram.ext import Application, ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.text_utils import b, bq, e, code
from core.helpers import safe_send_message
from core.state_machine import user_states, BroadcastMode
from core.state_machine import ADD_CLONE_TOKEN
from core.logging_setup import logger

# Running clone tasks: username → asyncio Task
_clone_tasks: Dict[str, Any] = {}


def launch_clone_bot(token: str, uname: str) -> None:
    """Schedule a clone bot polling task on the running event loop."""
    if uname in _clone_tasks:
        existing = _clone_tasks[uname]
        if not existing.done():
            logger.info(f"Clone @{uname} already running")
            return
    task = asyncio.ensure_future(_run_clone_polling(token, uname))
    _clone_tasks[uname] = task
    logger.info(f"🤖 Clone @{uname} task scheduled")


async def _run_clone_polling(token: str, uname: str) -> None:
    """Run a clone bot as an independent Application with all handlers."""
    logger.info(f" Starting clone bot @{uname} polling...")
    try:
        app = (
            Application.builder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )
        from bot import _register_all_handlers
        _register_all_handlers(app)
        async with app:
            await app.initialize()
            await app.start()
            if app.updater:
                await app.updater.start_polling(
                    allowed_updates=["ALL_TYPES"],
                    drop_pending_updates=True,
                )
            logger.info(f"✅ Clone @{uname} polling started")
            while app.running:
                await asyncio.sleep(5)
    except asyncio.CancelledError:
        logger.info(f"🛑 Clone @{uname} polling cancelled")
    except Exception as exc:
        logger.error(f"❌ Clone @{uname} error: {exc}")


async def register_clone_token(
    update: Update, context: ContextTypes.DEFAULT_TYPE, token: str
) -> None:
    """Validate and register a clone bot token."""
    chat_id = update.effective_chat.id
    try:
        clone_bot = Bot(token=token)
        me = await clone_bot.get_me()
        username = me.username

        from lifecycle import _register_bot_commands_on_bot
        asyncio.create_task(_register_bot_commands_on_bot(clone_bot))
        launch_clone_bot(token, username)

        from database_dual import add_clone_bot
        if add_clone_bot(token, username):
            await safe_send_message(
                context.bot, chat_id,
                b(f"✅ Clone bot @{e(username)} registered!") + "\n\n"
                + bq(b("Commands have been registered on the clone bot automatically.")),
            )
        else:
            await safe_send_message(context.bot, chat_id, b("❌ Failed to save clone bot to database."))
    except Exception as exc:
        await safe_send_message(
            context.bot, chat_id,
            b("❌ Invalid token or API error:") + "\n" + bq(code(e(str(exc)[:200])))
        )
