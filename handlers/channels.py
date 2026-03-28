"""
handlers/channels.py
====================
Force-sub channel management, channel welcome system, auto-approve join requests.
"""
import asyncio
import json
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.logging_setup import logger
from core.helpers import safe_send_message, safe_edit_text
from core.buttons import _btn, _back_btn, _close_btn, bold_button, _grid3
from core.text_utils import b, bq, code, e, small_caps
from core.state_machine import user_states


async def send_channel_welcome(bot, user_id: int, channel_id: int) -> None:
    """Send a welcome DM to a new channel member based on configured settings."""
    try:
        from database_dual import get_channel_welcome
        settings = get_channel_welcome(channel_id)
        if not settings or not settings.get("enabled"):
            return

        text = settings.get("welcome_text") or ""
        image_fid = settings.get("image_file_id") or ""
        image_url = settings.get("image_url") or ""
        buttons = settings.get("buttons") or []

        if not text and not image_fid and not image_url:
            return

        styled_text = b(text) if text else ""

        kb_rows = []
        for btn in buttons:
            lbl = btn.get("text", "") or btn.get("label", "")
            url = btn.get("url", "")
            if lbl and url:
                kb_rows.append([InlineKeyboardButton(small_caps(lbl), url=url)])
        markup = InlineKeyboardMarkup(kb_rows) if kb_rows else None

        image_src = image_fid or image_url or None
        if image_src:
            try:
                await bot.send_photo(
                    chat_id=user_id, photo=image_src, caption=styled_text,
                    parse_mode=ParseMode.HTML, reply_markup=markup,
                )
                return
            except Exception as exc:
                logger.debug(f"[cw] photo send failed: {exc}")

        if styled_text:
            try:
                await bot.send_message(
                    chat_id=user_id, text=styled_text, parse_mode=ParseMode.HTML,
                    reply_markup=markup, disable_web_page_preview=True,
                )
            except Exception as exc:
                logger.debug(f"[cw] message send failed: {exc}")
    except Exception as exc:
        logger.debug(f"[cw] send_channel_welcome: {exc}")


async def channel_welcome_join_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle new members joining a channel — send welcome DM."""
    msg = update.message or update.channel_post
    if not msg:
        return
    new_members = msg.new_chat_members
    if not new_members:
        return
    channel_id = msg.chat_id
    for member in new_members:
        if member.is_bot:
            continue
        asyncio.create_task(send_channel_welcome(context.bot, member.id, channel_id))


async def show_channel_welcome_panel(context, chat_id: int, query=None) -> None:
    """Show channel welcome configuration panel."""
    try:
        from database_dual import get_all_channel_welcomes
        channels = get_all_channel_welcomes()
    except Exception:
        channels = []

    text = b("📣 channel welcome system") + "\n\n"
    if channels:
        for ch_id, enabled, wtext in channels[:10]:
            icon = "🟢" if enabled else "🔴"
            text += f"{icon} <code>{ch_id}</code> — {e((wtext or '')[:40])}\n"
    else:
        text += bq(
            b(small_caps("no channels configured yet.")) + "\n"
            + small_caps("use ➕ add channel below to configure a welcome message.")
        )

    grid = [
        [InlineKeyboardButton(small_caps("➕ add/edit channel"), callback_data="cw_add")],
        [InlineKeyboardButton(small_caps("📋 list configured"), callback_data="cw_list"),
         InlineKeyboardButton(small_caps("🗑️ remove"), callback_data="cw_remove_menu")],
        [_back_btn("manage_force_sub"), _close_btn()],
    ]
    markup = InlineKeyboardMarkup(grid)

    from core.panel_image import get_panel_pic_async
    img = await get_panel_pic_async("channels")
    try:
        if query:
            await query.delete_message()
    except Exception:
        pass
    if img:
        try:
            await context.bot.send_photo(
                chat_id, img, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup
            )
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


async def auto_approve_join_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Auto-approve chat join requests."""
    req = update.chat_join_request
    if not req:
        return
    try:
        from database_dual import (
            get_force_sub_channel_info, get_setting, get_all_links
        )
        should_approve = False

        ch_info = get_force_sub_channel_info(str(req.chat.id))
        if ch_info and ch_info[2]:
            should_approve = True

        if not should_approve:
            jbr_global = (get_setting("auto_approve_join_requests", "false") or "false").lower() == "true"
            if jbr_global:
                should_approve = True

        if not should_approve:
            try:
                raw = get_all_links(limit=500, offset=0)
                linked_ids = set()
                for row in (raw or []):
                    try:
                        linked_ids.add(int(row[1]))
                    except (ValueError, TypeError):
                        pass
                if req.chat.id in linked_ids:
                    should_approve = True
            except Exception:
                pass

        if not should_approve:
            return

        await context.bot.approve_chat_join_request(req.chat.id, req.from_user.id)
        logger.debug(f"[jbr] approved {req.from_user.id} in {req.chat.id}")

        try:
            ch_title = req.chat.title or str(req.chat.id)
            await context.bot.send_message(
                req.from_user.id,
                b(small_caps(f"✅ your join request for {ch_title} has been approved!"))
                + "\n" + bq(b(small_caps("welcome! you can now access the channel."))),
                parse_mode="HTML",
            )
        except Exception:
            pass
    except Exception as exc:
        logger.debug(f"[jbr] auto-approve failed: {exc}")
