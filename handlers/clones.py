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
    """Validate and register a clone bot token. Clones cannot make clones."""
    chat_id = update.effective_chat.id
    uid = update.effective_user.id if update.effective_user else 0

    # ── Check if clones feature is disabled from admin panel ──────────────────
    try:
        from database_dual import get_setting
        if get_setting("clones_disabled", "false") == "true":
            await safe_send_message(
                context.bot, chat_id,
                b("🚫 Clone bots are currently disabled by admin.") + "\n"
                + bq("Enable from admin panel → Clones → Enable Clones")
            )
            return
    except Exception:
        pass

    # ── Clones cannot create clones ───────────────────────────────────────────
    from core.config import I_AM_CLONE
    if I_AM_CLONE:
        await safe_send_message(
            context.bot, chat_id,
            b("⛔ Clone bots cannot create other clones.") + "\n"
            + bq("Only the main bot can register clone bots.")
        )
        return

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


# ── Clone management panels ────────────────────────────────────────────────────

async def show_clones_panel(update, context, query=None) -> None:
    """Show registered clone bots panel."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from core.text_utils import b, bq, code, e, small_caps
    from core.buttons import _btn, _grid3, _back_btn, _close_btn, bold_button
    from core.helpers import safe_send_message
    from database_dual import get_all_clone_bots, get_setting
    from core.config import ADMIN_ID, OWNER_ID, I_AM_CLONE

    chat_id = query.message.chat_id if query else (
        update.effective_chat.id if update else 0)
    if query:
        try: await query.delete_message()
        except Exception: pass

    clones_disabled = get_setting("clones_disabled", "false") == "true"
    clones = get_all_clone_bots(active_only=False)

    text = b(small_caps("🤖 clone bots")) + "\n\n"
    if I_AM_CLONE:
        text += bq("⚠️ " + small_caps("this is a clone bot — cannot create sub-clones.")) + "\n\n"
    if clones_disabled:
        text += "🔴 " + b(small_caps("clone feature is disabled")) + "\n\n"
    if clones:
        for _, token, uname, active, added in clones:
            status = "🟢" if active else "🔴"
            text += f"{status} @{e(uname or '?')} — {code(str(added or '')[:10])}\n"
    else:
        text += bq(small_caps("no clone bots registered yet."))

    toggle_label = small_caps("✅ enable clones") if clones_disabled else small_caps("🚫 disable clones")
    toggle_cb = "clones_enable" if clones_disabled else "clones_disable"

    rows = [
        [InlineKeyboardButton(toggle_label, callback_data=toggle_cb)],
    ]
    if not I_AM_CLONE:
        rows.insert(0, [
            bold_button(small_caps("➕ add clone"), callback_data="clone_add"),
            bold_button(small_caps("➖ remove"),    callback_data="clone_remove"),
        ])
        rows.append([bold_button(small_caps("🔄 refresh commands"), callback_data="clone_refresh_cmds")])
    rows.append([_back_btn("admin_back"), _close_btn()])
    await safe_send_message(context.bot, chat_id, text,
                            reply_markup=InlineKeyboardMarkup(rows))


async def show_remove_clone_menu(query) -> None:
    """Show inline menu to select which clone to remove."""
    from telegram import InlineKeyboardMarkup
    from core.text_utils import b, bq, e, small_caps
    from core.buttons import _back_btn, _close_btn, bold_button
    from core.helpers import safe_edit_text
    from database_dual import get_all_clone_bots

    clones = get_all_clone_bots(active_only=False)
    if not clones:
        try:
            await query.answer(small_caps("no clones to remove"), show_alert=True)
        except Exception:
            pass
        return

    rows = []
    for _, token, uname, active, _ in clones:
        rows.append([bold_button(
            f"🗑 @{e(uname)}", callback_data=f"clone_del_{uname}")])
    rows.append([_back_btn("manage_clones"), _close_btn()])

    await safe_edit_text(
        query, b(small_caps("select clone to remove:")),
        reply_markup=InlineKeyboardMarkup(rows))
