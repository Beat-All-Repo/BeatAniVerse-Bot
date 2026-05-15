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
    ChatJoinRequest handler — exact logic from Advance-File-Share-bot (PTB port).

    Step 1 — Check if this channel is a JBR force-sub channel.
             Scan by numeric chat.id (reliable) + username fallback.
    Step 2 — If yes: record user in whitelist DB immediately.
             This is what makes "Try Again" work — is_sub() checks this table.
    Step 3 — Auto-approve if reqmode is ON and per-channel toggle allows it.
    """
    global _AUTO_APPROVE_ENABLED

    req = update.chat_join_request
    if not req:
        return

    chat_id = req.chat.id
    user_id = req.from_user.id

    # ── Step 1: Is this a JBR fsub channel? ──────────────────────────────────
    # Mirrors: reqChannel_exist(chat_id) from reference bot
    # We scan all channels and match by numeric ID — the only reliable method.
    is_jbr_fsub = False
    try:
        from database_dual import get_all_force_sub_channels, record_fsub_join_request
        all_chs = get_all_force_sub_channels(return_usernames_only=False)
        for row in (all_chs or []):
            stored_uname = (row[0] or "").strip()
            jbr_flag     = bool(row[2]) if len(row) > 2 else False
            stored_ch_id = row[4] if len(row) > 4 else None  # numeric channel_id column

            if not jbr_flag:
                continue  # only care about JBR channels

            # Match by stored numeric channel_id
            if stored_ch_id is not None:
                try:
                    if int(stored_ch_id) == chat_id:
                        is_jbr_fsub = True
                        break
                except (ValueError, TypeError):
                    pass

            # Match by parsing channel_username as numeric ID
            # (covers channels added before channel_id column was populated)
            try:
                if int(stored_uname.lstrip("@")) == chat_id:
                    is_jbr_fsub = True
                    break
            except (ValueError, TypeError):
                pass

            # Match by @username (public JBR channels)
            if req.chat.username:
                req_u  = req.chat.username.lstrip("@").lower()
                stor_u = stored_uname.lstrip("@").lower()
                if req_u and req_u == stor_u:
                    is_jbr_fsub = True
                    break
    except Exception as _se:
        logger.debug(f"[jbr] channel scan error: {_se}")

    # ── Step 2: Whitelist user immediately (THE key fix) ─────────────────────
    # Mirrors: db.req_user(chat_id, user_id) from reference bot
    # Stored by numeric chat_id. is_sub() will find it on the next check.
    if is_jbr_fsub:
        try:
            record_fsub_join_request(chat_id, user_id)
            logger.debug(f"[jbr] ✅ whitelisted user={user_id} ch={chat_id}")
        except Exception as _re:
            logger.debug(f"[jbr] whitelist write failed: {_re}")

    # ── Step 3: Auto-approve (only if reqmode ON and not toggled off) ─────────
    if _approval_off_channels is None:
        _load_approval_settings()
    if not _AUTO_APPROVE_ENABLED:
        return
    if _is_approval_off(chat_id):
        return

    try:
        from database_dual import get_setting, get_all_links
        should_approve = is_jbr_fsub  # JBR fsub channels are always approved

        # Also approve for global setting or generated-link channels
        if not should_approve:
            jbr_global = (get_setting("auto_approve_join_requests", "false") or "false").lower() == "true"
            if jbr_global:
                should_approve = True
        if not should_approve:
            try:
                raw = get_all_links(limit=500, offset=0)
                linked_ids = {int(r[1]) for r in (raw or []) if r and r[1]}
                if chat_id in linked_ids:
                    should_approve = True
            except Exception:
                pass

        if not should_approve:
            return

        wait_secs = _get_approval_wait()
        if wait_secs > 0:
            await asyncio.sleep(wait_secs)

        try:
            await context.bot.approve_chat_join_request(chat_id, user_id)
            logger.debug(f"[approve] ✅ approved user={user_id} ch={chat_id}")
        except Exception as _ae:
            logger.debug(f"[approve] approve call failed (may already be approved): {_ae}")

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


async def handle_chat_member_left(update, context) -> None:
    """
    Mirrors handle_Chatmembers() from Advance-File-Share-bot.
    When a user leaves/is kicked from a JBR fsub channel,
    remove them from the whitelist so they must request again.
    """
    cmu = update.chat_member
    if not cmu:
        return

    chat_id  = cmu.chat.id
    old_mem  = cmu.old_chat_member
    new_mem  = cmu.new_chat_member

    if not old_mem or not new_mem:
        return

    # Only care when transitioning FROM member TO left/kicked
    was_member = old_mem.status in ("member", "administrator", "creator", "restricted")
    now_left   = new_mem.status in ("left", "kicked")
    if not (was_member and now_left):
        return

    user_id = new_mem.user.id

    try:
        from database_dual import is_jbr_fsub_channel, remove_fsub_join_request
        if is_jbr_fsub_channel(chat_id):
            remove_fsub_join_request(chat_id, user_id)
            logger.debug(f"[jbr] removed whitelist: user={user_id} ch={chat_id}")
    except Exception as exc:
        logger.debug(f"[jbr] handle_chat_member_left error: {exc}")

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


# ══════════════════════════════════════════════════════════════════════════════
# FSub management commands  (/addfsub  /delfsub  /fsublist)
# Ported from Beat-Channel-Join-Advanced, adapted for python-telegram-bot
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_addfsub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addfsub <channel_id|@username>  [jbr]
    Add a channel to the force-subscription list.
    Append 'jbr' to enable join-by-request mode for private channels.
    Examples:
      /addfsub @mychannel
      /addfsub -1001234567890 jbr
    """
    args = context.args or []
    if not args:
        await update.message.reply_text(
            b("Usage:") + "\n"
            + "<code>/addfsub @username</code>\n"
            + "<code>/addfsub -1001234567890</code>\n"
            + "<code>/addfsub -1001234567890 jbr</code>  ← join-request mode",
            parse_mode=ParseMode.HTML,
        )
        return

    raw       = args[0].strip()
    jbr_mode  = len(args) >= 2 and args[1].lower() == "jbr"

    # Resolve the channel
    try:
        tg_chat = await context.bot.get_chat(raw if raw.startswith("@") else int(raw))
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Cannot find channel <code>{e(raw)}</code>.\n\n"
            f"Make sure the bot is an admin there.\n<i>{e(str(exc))}</i>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Confirm bot is admin
    try:
        me      = await context.bot.get_me()
        bot_mem = await context.bot.get_chat_member(tg_chat.id, me.id)
        if bot_mem.status not in ("administrator", "creator"):
            await update.message.reply_text(
                f"❌ I must be an <b>admin</b> in <b>{e(tg_chat.title)}</b> to add it as an fsub channel.",
                parse_mode=ParseMode.HTML,
            )
            return
    except Exception:
        pass  # Can't check membership — proceed anyway

    is_private   = not tg_chat.username
    stored_uname = f"@{tg_chat.username}" if tg_chat.username else str(tg_chat.id)
    invite_link  = ""

    # Auto-generate invite link for private channels
    if is_private:
        try:
            if jbr_mode:
                lnk = await context.bot.create_chat_invite_link(
                    tg_chat.id, creates_join_request=True
                )
            else:
                lnk = await context.bot.export_chat_invite_link(tg_chat.id)
            invite_link = getattr(lnk, "invite_link", lnk) or ""
        except Exception as _le:
            logger.debug(f"[addfsub] invite link gen failed: {_le}")

    from database_dual import add_force_sub_channel
    add_force_sub_channel(
        stored_uname,
        tg_chat.title,
        join_by_request=jbr_mode,
        invite_link=invite_link or None,
        channel_id=tg_chat.id,
    )

    jbr_note   = " <b>(🔔 Join-Request mode)</b>" if jbr_mode else ""
    link_note  = "\n<i>✅ Invite link stored.</i>" if invite_link else (
        "\n<i>⚠️ No invite link — use /addfsub after making bot admin.</i>"
        if is_private else ""
    )
    type_label = "Private" if is_private else "Public"

    await update.message.reply_text(
        f"✅ <b>Force-sub channel added!</b>\n\n"
        f"<b>Title:</b> {e(tg_chat.title)}\n"
        f"<b>ID:</b> <code>{tg_chat.id}</code>\n"
        f"<b>Type:</b> {type_label}{jbr_note}"
        f"{link_note}",
        parse_mode=ParseMode.HTML,
    )


async def cmd_delfsub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /delfsub <channel_id|@username>
    Remove a channel from the force-subscription list.
    """
    args = context.args or []
    if not args:
        await update.message.reply_text(
            b("Usage:") + " <code>/delfsub @username</code>  or  <code>/delfsub -100123456</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    raw = args[0].strip()
    from database_dual import delete_force_sub_channel, get_all_force_sub_channels

    # Resolve display name
    display = raw
    try:
        tg_chat = await context.bot.get_chat(raw if raw.startswith("@") else int(raw))
        display = tg_chat.title or raw
        # Normalise to stored key
        stored_uname = f"@{tg_chat.username}" if tg_chat.username else str(tg_chat.id)
    except Exception:
        stored_uname = raw

    delete_force_sub_channel(stored_uname)
    await update.message.reply_text(
        f"✅ Removed <b>{e(display)}</b> (<code>{e(stored_uname)}</code>) from force-sub list.",
        parse_mode=ParseMode.HTML,
    )


async def cmd_fsublist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /fsublist
    List all active force-subscription channels with their mode.
    """
    from database_dual import get_all_force_sub_channels

    channels = get_all_force_sub_channels(return_usernames_only=False)
    if not channels:
        await update.message.reply_text(
            "📋 <b>No force-sub channels configured.</b>\n\n"
            "Use <code>/addfsub @username</code> to add one.",
            parse_mode=ParseMode.HTML,
        )
        return

    lines = [b("📋 Force-Sub Channels") + "\n"]
    for i, row in enumerate(channels, 1):
        uname       = row[0] if len(row) > 0 else "?"
        title       = row[1] if len(row) > 1 else uname
        jbr         = bool(row[2]) if len(row) > 2 else False
        invite_link = row[3] if len(row) > 3 else ""

        mode_badge  = " 🔔 <i>JBR</i>"  if jbr else " 📢 <i>Direct</i>"
        link_badge  = " ✅ link stored"  if invite_link else ""
        # Try to resolve current title from Telegram (best-effort)
        try:
            ch = await context.bot.get_chat(int(uname) if uname.lstrip("-").isdigit() else uname)
            title = ch.title or title
        except Exception:
            pass

        lines.append(
            f"\n<b>{i}.</b> {e(title)}{mode_badge}{link_badge}\n"
            f"   ID: <code>{e(uname)}</code>"
        )

    lines.append(
        "\n\n<i>Commands: /addfsub  /delfsub  /reqmode  /reqtime  /approvestatus</i>"
    )
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ══════════════════════════════════════════════════════════════════════════════
# Startup: Scan pending join requests for all JBR fsub channels
# ══════════════════════════════════════════════════════════════════════════════

async def sync_jbr_whitelist_on_startup(bot) -> None:
    """
    Called once at bot startup.

    For every JBR force-sub channel:
      - Verify bot is still an admin (log warning if not).
      - For every user in fsub_join_requests table for this channel:
          • If they are now a MEMBER  → clear the whitelist entry (they joined).
          • If they are still pending  → keep the entry (they'll be whitelisted
            and auto-approved when they interact with the bot next).

    We cannot fetch the list of pending requests via Bot API, so we rely on
    the real-time ChatJoinRequest handler to add new entries.  This function
    only cleans up stale ones.
    """
    try:
        from database_dual import (
            get_all_force_sub_channels, get_all_fsub_whitelisted_users,
            clear_fsub_join_request,
        )
    except ImportError as _ie:
        logger.debug(f"[jbr_startup] import error: {_ie}")
        return

    channels = get_all_force_sub_channels(return_usernames_only=False)
    jbr_channels = [row for row in (channels or []) if len(row) > 2 and row[2]]

    if not jbr_channels:
        return

    logger.info(f"[jbr_startup] Syncing whitelist for {len(jbr_channels)} JBR channel(s)…")

    for row in jbr_channels:
        uname      = row[0]
        ch_id_raw  = row[4] if len(row) > 4 else None  # numeric id if stored
        ch_lookup  = ch_id_raw if ch_id_raw else uname

        # Check bot is admin
        try:
            me     = await bot.get_me()
            bot_mb = await bot.get_chat_member(ch_lookup, me.id)
            if bot_mb.status not in ("administrator", "creator"):
                logger.warning(f"[jbr_startup] Bot is NOT admin in {uname} — JBR auto-approve won't work!")
        except Exception as _ae:
            logger.debug(f"[jbr_startup] admin check failed for {uname}: {_ae}")

        # Clean up users who are now full members (already approved)
        whitelisted = get_all_fsub_whitelisted_users(uname)
        if not whitelisted:
            continue

        for uid in whitelisted:
            try:
                member = await bot.get_chat_member(ch_lookup, uid)
                if member.status not in ("left", "kicked"):
                    # Already a member — clear the whitelist entry
                    clear_fsub_join_request(uid, uname)
                    logger.debug(f"[jbr_startup] cleared stale whitelist: user={uid} ch={uname}")
            except Exception:
                pass  # Can't verify — leave the entry in place

    logger.info("[jbr_startup] JBR whitelist sync complete.")
