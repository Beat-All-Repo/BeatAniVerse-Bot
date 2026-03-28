"""
handlers/autoforward.py
=======================
Auto-forward connections: channel post → target channels.
Includes: filter matching, caption override, replacements, delay, bulk.
"""
import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.logging_setup import logger
from core.helpers import safe_send_message, safe_delete, safe_edit_text
from core.buttons import _btn, _back_btn, bold_button
from core.text_utils import b, bq, code, e, small_caps
from core.state_machine import user_states, AF_ADD_CONNECTION_SOURCE, AF_ADD_CONNECTION_TARGET


async def _show_autoforward_menu(context, chat_id: int) -> None:
    try:
        from database_dual import db_manager, get_setting
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM auto_forward_connections WHERE active = TRUE")
            active_count = cur.fetchone()[0]
        af_enabled = get_setting("autoforward_enabled", "true")
    except Exception:
        active_count = 0
        af_enabled = "true"

    on_off = "ON" if active_count > 0 and af_enabled == "true" else "OFF"
    text = (
        b("Auto Forward Settings") + "\n\n"
        f"<b>Status:</b> {on_off}\n"
        f"<b>Connections:</b> {active_count}"
    )
    keyboard = [
        [bold_button("MODE", callback_data="af_set_caption")],
        [bold_button("MANAGE CONNECTIONS", callback_data="af_list_connections")],
        [bold_button("SETTINGS", callback_data="af_add_connection"),
         bold_button("FILTERS", callback_data="af_filters_menu")],
        [bold_button("REPLACEMENTS", callback_data="af_replacements_menu"),
         bold_button("DELAY", callback_data="af_set_delay")],
        [bold_button("BULK FORWARD", callback_data="af_bulk")],
        [bold_button("TOGGLE ON/OFF", callback_data="af_toggle_all")],
        [_back_btn("admin_back")],
    ]
    await safe_send_message(
        context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def autoforward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    try:
        await update.message.delete()
    except Exception:
        pass
    user_states.pop(update.effective_user.id, None)
    await _show_autoforward_menu(context, update.effective_chat.id)


async def auto_forward_message_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forward channel posts to target channels based on connection config."""
    msg = update.channel_post
    if not msg:
        return
    chat_id = update.effective_chat.id

    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT id, target_chat_id, protect_content, silent, pin_message,
                       delete_source, delay_seconds
                FROM auto_forward_connections
                WHERE source_chat_id = %s AND active = TRUE
            """, (chat_id,))
            connections = cur.fetchall() or []
    except Exception as exc:
        logger.debug(f"auto_forward DB error: {exc}")
        return

    for conn in connections:
        conn_id, target, protect, silent, pin, delete_src, delay = conn

        caption_override = None
        try:
            from database_dual import db_manager as _dm
            with _dm.get_cursor() as cur:
                cur.execute("""
                    SELECT allowed_media, blacklist_words, whitelist_words,
                           caption_override, replacements
                    FROM auto_forward_filters WHERE connection_id = %s
                """, (conn_id,))
                filter_row = cur.fetchone()
        except Exception:
            filter_row = None

        if filter_row:
            allowed_media, blacklist_words, whitelist_words, caption_override, _ = filter_row

            if allowed_media:
                media_types = [m.strip() for m in allowed_media.split(",")]
                msg_type = (
                    "photo" if msg.photo else
                    "video" if msg.video else
                    "document" if msg.document else
                    "audio" if msg.audio else
                    "sticker" if msg.sticker else
                    "text" if msg.text else None
                )
                if msg_type and msg_type not in media_types:
                    continue

            check_text = (msg.caption or msg.text or "").lower()
            if whitelist_words:
                if not any(w.strip().lower() in check_text for w in whitelist_words.split(",")):
                    continue
            if blacklist_words:
                if any(w.strip().lower() in check_text for w in blacklist_words.split(",")):
                    continue

        if delay and delay > 0:
            context.job_queue.run_once(
                _delayed_forward,
                when=delay,
                data={
                    "from_chat_id": chat_id, "message_id": msg.message_id,
                    "target_chat_id": target, "protect": protect,
                    "silent": silent, "pin": pin,
                    "delete_src": delete_src, "caption_override": caption_override,
                },
            )
        else:
            asyncio.create_task(
                _do_forward(
                    context.bot, chat_id, msg.message_id, target,
                    protect=protect, silent=silent, pin=pin,
                    delete_src=delete_src, caption_override=caption_override,
                )
            )


async def _do_forward(
    bot, from_chat_id: int, message_id: int, target_chat_id: int,
    protect=False, silent=False, pin=False,
    delete_src=False, caption_override=None,
) -> None:
    try:
        new_msg = await bot.copy_message(
            chat_id=target_chat_id, from_chat_id=from_chat_id,
            message_id=message_id, protect_content=protect,
            disable_notification=silent,
        )
        if caption_override and new_msg:
            try:
                await bot.edit_message_caption(
                    chat_id=target_chat_id, message_id=new_msg.message_id,
                    caption=caption_override, parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        if pin and new_msg:
            try:
                await bot.pin_chat_message(target_chat_id, new_msg.message_id,
                                           disable_notification=True)
            except Exception:
                pass
        if delete_src:
            await safe_delete(bot, from_chat_id, message_id)
    except Exception as exc:
        logger.debug(f"_do_forward error: {exc}")


async def _delayed_forward(context) -> None:
    d = context.job.data
    await _do_forward(
        context.bot, d["from_chat_id"], d["message_id"], d["target_chat_id"],
        protect=d.get("protect", False), silent=d.get("silent", False),
        pin=d.get("pin", False), delete_src=d.get("delete_src", False),
        caption_override=d.get("caption_override"),
    )
