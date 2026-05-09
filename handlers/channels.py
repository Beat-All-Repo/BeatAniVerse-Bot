"""
handlers/channels.py
====================
Force-sub channel management, channel welcome system, auto-approve join requests.

PATCH (ported from Beat-Channel-Join-Advanced):
  - Configurable per-channel approval toggle (/approveoff / /approveon)
  - Global auto-approve toggle (/reqmode on|off)
  - Configurable approval wait time (/reqtime <seconds>)
  - Photo welcome DM sent after approval
  - All existing features preserved (channel welcome system, etc.)
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


# ── Auto-approve runtime settings (in-memory, survives until restart) ──────────
# Persisted via bot_settings DB key so they survive restarts too.

# Default wait time in seconds before approving a join request
_DEFAULT_APPROVAL_WAIT = 5

# Global enable/disable toggle for auto-approve
_AUTO_APPROVE_ENABLED: bool = True

# In-memory cache of per-channel approval-off set
# (synced with DB key "approval_off_channels" on change)
_approval_off_channels: Optional[set] = None


def _load_approval_settings() -> None:
    """Load approval settings from DB into memory (called lazily)."""
    global _AUTO_APPROVE_ENABLED, _approval_off_channels
    try:
        from database_dual import get_setting
        raw_enabled = get_setting("auto_approve_global_enabled", "true") or "true"
        _AUTO_APPROVE_ENABLED = raw_enabled.lower() != "false"
        raw_off = get_setting("approval_off_channels", "[]") or "[]"
        _approval_off_channels = set(json.loads(raw_off))
    except Exception as exc:
        logger.debug(f"[approve] _load_approval_settings: {exc}")
        if _approval_off_channels is None:
            _approval_off_channels = set()


def _get_approval_wait() -> int:
    """Return current approval wait time from DB (or default)."""
    try:
        from database_dual import get_setting
        val = get_setting("approval_wait_time", str(_DEFAULT_APPROVAL_WAIT))
        return max(0, int(val or _DEFAULT_APPROVAL_WAIT))
    except Exception:
        return _DEFAULT_APPROVAL_WAIT


def _is_approval_off(channel_id: int) -> bool:
    """Check if auto-approve is disabled for a specific channel."""
    global _approval_off_channels
    if _approval_off_channels is None:
        _load_approval_settings()
    return channel_id in (_approval_off_channels or set())


def _set_approval_off(channel_id: int, off: bool) -> None:
    """Toggle auto-approve for a specific channel and persist to DB."""
    global _approval_off_channels
    if _approval_off_channels is None:
        _load_approval_settings()
    if off:
        _approval_off_channels.add(channel_id)
    else:
        _approval_off_channels.discard(channel_id)
    try:
        from database_dual import set_setting
        set_setting("approval_off_channels", json.dumps(list(_approval_off_channels)))
    except Exception as exc:
        logger.debug(f"[approve] _set_approval_off persist failed: {exc}")


# ── Channel welcome system (unchanged) ────────────────────────────────────────

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


# ── Auto-approve join request handler (enhanced) ──────────────────────────────

async def auto_approve_join_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Auto-approve chat join requests.

    Logic (mirrors BCJ bot):
      1. Global toggle — if /reqmode off, do nothing.
      2. Per-channel toggle — if /approveoff <id> was used, skip that channel.
      3. Original force-sub JBR mode OR global setting OR linked channel check.
      4. Wait APPROVAL_WAIT_TIME seconds (configurable via /reqtime).
      5. Approve, then send welcome photo DM.
    """
    global _AUTO_APPROVE_ENABLED

    req = update.chat_join_request
    if not req:
        return

    # 1 — Global toggle
    if _approval_off_channels is None:
        _load_approval_settings()
    if not _AUTO_APPROVE_ENABLED:
        logger.debug(f"[approve] global OFF — skipping {req.from_user.id}")
        return

    # 2 — Per-channel toggle
    if _is_approval_off(req.chat.id):
        logger.debug(f"[approve] channel {req.chat.id} approval OFF — skipping")
        return

    try:
        from database_dual import (
            get_force_sub_channel_info, get_setting, get_all_links
        )
        should_approve = False

        # 3a — Force-sub channel with join-by-request enabled
        ch_info = get_force_sub_channel_info(str(req.chat.id))
        if ch_info and ch_info[2]:
            should_approve = True

        # 3b — Global auto_approve_join_requests setting
        if not should_approve:
            jbr_global = (get_setting("auto_approve_join_requests", "false") or "false").lower() == "true"
            if jbr_global:
                should_approve = True

        # 3c — Channel appears in generated links DB
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

        # 4 — Configurable wait before approving (prevents abuse detection)
        wait_secs = _get_approval_wait()
        if wait_secs > 0:
            await asyncio.sleep(wait_secs)

        # Approve
        await context.bot.approve_chat_join_request(req.chat.id, req.from_user.id)
        logger.debug(f"[approve] ✅ approved {req.from_user.id} in {req.chat.id}")

        # 5 — Send welcome photo DM
        try:
            ch_title = req.chat.title or str(req.chat.id)

            # Configurable welcome photo URL (set via bot_settings key "approve_welcome_photo")
            _default_photo = "https://telegra.ph/file/f3d3aff9ec422158feb05-d2180e3665e0ac4d32.jpg"
            try:
                approve_photo = get_setting("approve_welcome_photo", _default_photo) or _default_photo
            except Exception:
                approve_photo = _default_photo

            user_mention = f'<a href="tg://user?id={req.from_user.id}">{e(req.from_user.first_name)}</a>'
            caption = (
                b(small_caps(f"✅ ʜᴇʏ {req.from_user.first_name},")) + "\n\n"
                + bq(
                    b(small_caps(f"ʏᴏᴜʀ ʀᴇǫᴜᴇsᴛ ᴛᴏ ᴊᴏɪɴ {ch_title} ʜᴀs ʙᴇᴇɴ ᴀᴘᴘʀᴏᴠᴇᴅ!"))
                ) + "\n\n"
                + b(small_caps("ᴡᴇʟᴄᴏᴍᴇ! ʏᴏᴜ ᴄᴀɴ ɴᴏᴡ ᴀᴄᴄᴇss ᴛʜᴇ ᴄʜᴀɴɴᴇʟ."))
            )

            # Try to get a permanent channel link for the button
            try:
                chat_obj = await context.bot.get_chat(req.chat.id)
                if chat_obj.username:
                    ch_link = f"https://t.me/{chat_obj.username}"
                else:
                    ch_link = (await context.bot.export_chat_invite_link(req.chat.id))
            except Exception:
                ch_link = None

            buttons = []
            if ch_link:
                buttons.append([InlineKeyboardButton(
                    small_caps(f"• ᴊᴏɪɴ {ch_title} •"), url=ch_link
                )])

            markup = InlineKeyboardMarkup(buttons) if buttons else None

            await context.bot.send_photo(
                chat_id=req.from_user.id,
                photo=approve_photo,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        except Exception as exc:
            # Photo failed — fall back to text welcome
            try:
                await context.bot.send_message(
                    req.from_user.id,
                    b(small_caps(f"✅ your join request for {req.chat.title or req.chat.id} has been approved!"))
                    + "\n" + bq(b(small_caps("welcome! you can now access the channel."))),
                    parse_mode="HTML",
                )
            except Exception:
                pass
            logger.debug(f"[approve] welcome photo failed: {exc}")

    except Exception as exc:
        logger.debug(f"[approve] auto-approve failed: {exc}")


# ── Admin commands (ported from BCJ bot) ──────────────────────────────────────

async def cmd_reqtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /reqtime <seconds>
    Set the wait time (in seconds) before auto-approving a join request.
    Default is 5 seconds. Set to 0 for instant approval.
    """
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(
            b("Usage:") + " <code>/reqtime {seconds}</code>\n\n"
            + bq(b("Example: /reqtime 5")),
            parse_mode=ParseMode.HTML,
        )
        return
    secs = int(args[0])
    try:
        from database_dual import set_setting
        set_setting("approval_wait_time", str(secs))
    except Exception as exc:
        logger.debug(f"[reqtime] DB write failed: {exc}")
    await update.message.reply_text(
        f"✅ {b('Request approval wait time set to')} <b>{secs}</b> seconds.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_reqmode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /reqmode on|off
    Globally enable or disable the auto-approve system.
    """
    global _AUTO_APPROVE_ENABLED
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        await update.message.reply_text(
            b("Usage:") + " <code>/reqmode on</code> " + b("or") + " <code>/reqmode off</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    mode = args[0].lower()
    _AUTO_APPROVE_ENABLED = (mode == "on")
    try:
        from database_dual import set_setting
        set_setting("auto_approve_global_enabled", "true" if _AUTO_APPROVE_ENABLED else "false")
    except Exception as exc:
        logger.debug(f"[reqmode] DB write failed: {exc}")
    status = "enabled ✅" if _AUTO_APPROVE_ENABLED else "disabled ❌"
    await update.message.reply_text(
        f"Auto-approval has been {b(status)}.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_approveoff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /approveoff <channel_id>
    Disable auto-approval for a specific channel.
    """
    args = context.args
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text(
            b("Usage:") + " <code>/approveoff {channel_id}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    channel_id = int(args[0])
    _set_approval_off(channel_id, True)
    await update.message.reply_text(
        f"✅ Auto-approval is now {b('OFF')} for channel <code>{channel_id}</code>.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_approveon(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /approveon <channel_id>
    Re-enable auto-approval for a specific channel.
    """
    args = context.args
    if not args or not args[0].lstrip("-").isdigit():
        await update.message.reply_text(
            b("Usage:") + " <code>/approveon {channel_id}</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    channel_id = int(args[0])
    _set_approval_off(channel_id, False)
    await update.message.reply_text(
        f"✅ Auto-approval is now {b('ON')} for channel <code>{channel_id}</code>.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_approve_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /approvestatus
    Show current auto-approve settings.
    """
    if _approval_off_channels is None:
        _load_approval_settings()
    wait = _get_approval_wait()
    global_status = "🟢 ON" if _AUTO_APPROVE_ENABLED else "🔴 OFF"
    off_channels = list(_approval_off_channels or [])
    off_text = "\n".join(f"  • <code>{c}</code>" for c in off_channels) if off_channels else "  None"
    text = (
        b("⚙️ Auto-Approve Settings") + "\n\n"
        + f"<b>Global Mode:</b> {global_status}\n"
        + f"<b>Wait Time:</b> {wait} seconds\n\n"
        + b("Per-channel approval OFF:") + "\n" + off_text
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
