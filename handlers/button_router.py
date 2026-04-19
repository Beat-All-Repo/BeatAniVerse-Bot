"""
handlers/button_router.py
=========================
Central callback query router — all InlineKeyboardButton callbacks handled here.
Answers every query immediately. Routes to sub-handlers by data prefix.
"""
import asyncio
import json
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL,
    LINK_EXPIRY_MINUTES, JOIN_BTN_TEXT, HERE_IS_LINK_TEXT,
    ANIME_BTN_TEXT, REQUEST_BTN_TEXT, CONTACT_BTN_TEXT,
    FORCE_SUB_TEXT, BUTTON_STYLE, BOT_NAME,
)
from core.logging_setup import logger
from core.helpers import (
    safe_answer, safe_send_message, safe_edit_text, safe_reply,
    safe_send_photo, safe_delete, UserFriendlyError,
)
from core.buttons import _btn, _back_btn, _close_btn, bold_button, _grid3, _back_kb
from core.text_utils import b, bq, code, e, small_caps
from core.state_machine import (
    user_states, upload_progress,
    ADD_CLONE_TOKEN, GENERATE_LINK_IDENTIFIER,
    SET_BACKUP_CHANNEL, PENDING_BROADCAST, PENDING_BROADCAST_OPTIONS,
    SET_CATEGORY_CAPTION, SET_CATEGORY_BRANDING, SET_CATEGORY_BUTTONS,
    SET_CATEGORY_THUMBNAIL, SET_WATERMARK_TEXT, SET_CATEGORY_LOGO,
    UPLOAD_SET_CAPTION, UPLOAD_SET_SEASON, UPLOAD_SET_EPISODE,
    UPLOAD_SET_TOTAL, UPLOAD_SET_CHANNEL, SEARCH_USER_INPUT,
    BAN_USER_INPUT, UNBAN_USER_INPUT, DELETE_USER_INPUT,
    AF_ADD_CONNECTION_SOURCE, AU_ADD_MANGA_TITLE, AU_ADD_MANGA_TARGET,
    CW_SET_TEXT, CW_SET_BUTTONS, BroadcastMode,
    PENDING_CHANNEL_POST, SCHEDULE_BROADCAST_DATETIME,
)
from core.cache import cache_get, cache_set
from core.filters_system import force_sub_required
from core.panel_image import get_panel_pic, get_panel_pic_async, _PANEL_IMAGE_AVAILABLE
from core.panel_store import _deliver_panel, safe_edit_panel

# ── Filter poster integration ──────────────────────────────────────────────────
try:
    from filter_poster import (
        _get_filter_poster_enabled, _set_filter_poster_enabled,
        _get_default_poster_template, _set_default_poster_template,
        build_filter_poster_settings_keyboard, get_filter_poster_settings_text,
        _clear_poster_cache, _get_cache_count, _get_panel_db_images,
    )
    _FILTER_POSTER_AVAILABLE = True
except ImportError:
    _FILTER_POSTER_AVAILABLE = False
    def _get_cache_count(): return 0
    def _clear_poster_cache(): return 0
    def _get_panel_db_images(): return []



async def _panel_edit(query, text: str, reply_markup=None) -> None:
    """
    Smart edit for admin panel callbacks.
    Photo panels can't be edited as text — deletes and resends instead.
    """
    try:
        await query.edit_message_text(
            text=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        return
    except Exception as e1:
        err = str(e1).lower()
        if "message is not modified" in err:
            return
        # Photo message — try caption edit
        if any(k in err for k in ("no text", "can't be edited", "caption")):
            try:
                await query.edit_message_caption(
                    caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
                )
                return
            except Exception:
                pass
    # Last resort: delete + resend
    chat_id = query.message.chat_id if query.message else 0
    try:
        await query.message.delete()
    except Exception:
        pass
    if chat_id:
        try:
            bot = context.bot if hasattr(context, 'bot') else query.get_bot()
            await bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            pass


@force_sub_required
async def button_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, _data_override: str = None
) -> None:
    """
    Central callback query router.
    Answers every query immediately to prevent timeout errors.
    """
    query = update.callback_query
    if not query:
        return

    if _data_override is None:
        try:
            await query.answer()
        except Exception:
            pass

    data = _data_override if _data_override is not None else (query.data or "")

    # Helper: delete current message and send fresh panel
    async def _del_and_send(text: str, reply_markup=None, photo=None) -> None:
        """Delete the triggering panel message, then send fresh content."""
        try:
            if query and query.message:
                await query.message.delete()
        except Exception:
            pass
        if photo:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=photo, caption=text,
                    parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                )
                return
            except Exception:
                pass
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.HTML,
                reply_markup=reply_markup, disable_web_page_preview=True,
            )
        except Exception:
            pass

    # Smart edit: try text edit → caption edit → delete+resend
    async def _smart_edit(text: str, reply_markup=None) -> None:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        except Exception as _e:
            if "not modified" in str(_e).lower():
                return
        try:
            await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        except Exception:
            pass
        await _del_and_send(text, reply_markup)
    uid = query.from_user.id if query.from_user else 0
    chat_id = query.message.chat_id if query.message else uid
    is_admin = uid in (ADMIN_ID, OWNER_ID)

    # ── Utility ────────────────────────────────────────────────────────────────
    if data == "noop":
        return

    if data == "close_message":
        try:
            await query.delete_message()
        except Exception:
            pass
        return

    if data == "verify_subscription":
        from handlers.start import start
        await start(update, context)
        return

    # ── Admin panel page navigation ────────────────────────────────────────────
    if data.startswith("adm_page_"):
        if not is_admin:
            return
        try:
            page_num = int(data.split("_")[-1])
        except Exception:
            page_num = 0
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context, query=query, page=page_num)
        return

    if data == "admin_back":
        if not is_admin:
            return
        user_states.pop(uid, None)
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context, query)
        return

    # ── Image navigation ───────────────────────────────────────────────────────
    if data.startswith("imgn:"):
        try:
            parts = data.split(":", 3)
            if len(parts) == 4:
                _, cur_idx_str, img_key, direction = parts
                cur_idx = int(cur_idx_str)
                entry = cache_get(img_key)
                images = entry.get("urls", []) if isinstance(entry, dict) else (entry or [])
                saved_caption = entry.get("caption", "") if isinstance(entry, dict) else ""

                if images and len(images) > 1:
                    step = 1 if direction == "next" else -1
                    new_idx = (cur_idx + step) % len(images)
                    new_url = images[new_idx]
                    new_kb = [
                        [InlineKeyboardButton("🔙", callback_data=f"imgn:{new_idx}:{img_key}:prev"),
                         InlineKeyboardButton("✖️", callback_data="close_message"),
                         InlineKeyboardButton("🔜", callback_data=f"imgn:{new_idx}:{img_key}:next")],
                    ]
                    if query.message and query.message.reply_markup:
                        old_rows = list(query.message.reply_markup.inline_keyboard)
                        top_rows = old_rows[:-1] if old_rows else []
                        new_kb = top_rows + new_kb
                    try:
                        if saved_caption:
                            await query.message.edit_media(
                                InputMediaPhoto(media=new_url, caption=saved_caption, parse_mode=ParseMode.HTML),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                        else:
                            await query.message.edit_media(
                                InputMediaPhoto(media=new_url),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                    except Exception as exc:
                        logger.debug(f"imgn edit_media error: {exc}")
        except Exception as exc:
            logger.debug(f"imgn handler error: {exc}")
        return

    # ── Stats panel ─────────────────────────────────────────────────────────────
    if data == "admin_stats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.admin_panel import send_stats_panel
        await send_stats_panel(context, chat_id)
        return

    if data == "admin_sysstats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.helpers import get_system_stats_text
        await safe_send_message(
            context.bot, chat_id, get_system_stats_text(),
            reply_markup=InlineKeyboardMarkup([[
                bold_button("♻️ Refresh", callback_data="admin_sysstats"), _back_btn("admin_back")
            ]]),
        )
        return

    if data == "broadcast_stats_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import broadcaststats_command
        await broadcaststats_command(update, context)
        return

    # ── Admin logs ─────────────────────────────────────────────────────────────
    if data == "admin_logs":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import _send_logs_panel
        await _send_logs_panel(context.bot, chat_id)
        return

    if data in ("admin_logs_refresh", "admin_logs_200", "admin_logs_errors",
                "admin_logs_warnings", "admin_logs_download", "admin_logs_clear"):
        if not is_admin:
            return
        from handlers.misc_cmds import _send_logs_panel
        import os, glob

        if data == "admin_logs_clear":
            try:
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    for f in glob.glob(pattern):
                        open(f, "w").close()
                await safe_answer(query, "✅ Logs cleared")
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            await _send_logs_panel(context.bot, chat_id, query=query)
            return

        if data == "admin_logs_download":
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            log_text = f.read()
                        break
                if log_text:
                    from io import BytesIO
                    doc = BytesIO(log_text.encode())
                    doc.name = "bot_logs.txt"
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_document(
                        chat_id=chat_id, document=doc,
                        caption="<b>📋 Full Bot Logs</b>", parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Back", callback_data="admin_logs_refresh"),
                            InlineKeyboardButton("✖ Close", callback_data="close_message"),
                        ]]),
                    )
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        if data == "admin_logs_errors":
            # Show only error lines
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            lines = [l for l in f if "ERROR" in l or "error" in l.lower()]
                        log_text = "".join(lines[-50:])
                        break
                if not log_text:
                    log_text = "No errors found! ✅"
                from core.text_utils import e
                text = f"<b>🔴 Error Lines Only</b>\n\n<pre>{e(log_text[-3800:])}</pre>"
                await _smart_edit(text, InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 All Logs", callback_data="admin_logs_refresh"),
                    InlineKeyboardButton("✖ Close", callback_data="close_message"),
                ]]))
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        if data == "admin_logs_warnings":
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            lines = [l for l in f if "WARNING" in l or "WARN" in l]
                        log_text = "".join(lines[-50:])
                        break
                if not log_text:
                    log_text = "No warnings found! ✅"
                from core.text_utils import e
                text = f"<b>🟡 Warning Lines Only</b>\n\n<pre>{e(log_text[-3800:])}</pre>"
                await _smart_edit(text, InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 All Logs", callback_data="admin_logs_refresh"),
                    InlineKeyboardButton("✖ Close", callback_data="close_message"),
                ]]))
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        # admin_logs_refresh or admin_logs_200
        n = 200 if data == "admin_logs_200" else 80
        await _send_logs_panel(context.bot, chat_id, lines=n, query=query)
        return

    # ── Restart ────────────────────────────────────────────────────────────────
    if data == "admin_restart_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query, b("⚠️ Restart Bot?\n\n") + bq(b("This will restart the bot.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button("✔️ RESTART", callback_data="admin_do_restart"),
                bold_button("CANCEL", callback_data="admin_back"),
            ]]),
        )
        return

    if data == "admin_do_restart":
        if not is_admin:
            return
        await safe_answer(query, "Restarting…")
        from handlers.misc_cmds import reload_command
        await reload_command(update, context)
        return

    # ── Broadcast flow ─────────────────────────────────────────────────────────
    if data == "admin_broadcast_start":
        if not is_admin:
            return
        user_states[uid] = PENDING_BROADCAST
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("📣 Broadcast") + "\n\n"
            + bq(b("Send the message you want to broadcast to all users.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        context.user_data["bot_prompt_message_id"] = msg.message_id if msg else None
        return

    if data.startswith("broadcast_mode_"):
        if not is_admin:
            return
        mode = data[len("broadcast_mode_"):]
        context.user_data["broadcast_mode"] = mode
        await safe_edit_text(
            query, b(f"Mode: {e(mode)}\n\nSend /confirm to broadcast or /cancel to abort."),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        user_states[uid] = PENDING_BROADCAST_OPTIONS
        return

    if data == "broadcast_schedule":
        if not is_admin:
            return
        user_states[uid] = SCHEDULE_BROADCAST_DATETIME
        await safe_edit_text(
            query,
            b("📅 Schedule Broadcast") + "\n\n"
            + bq(b("Send the date and time for the broadcast:\n")
                 + b("Format: YYYY-MM-DD HH:MM (UTC)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    # ── Force-sub channels panel ───────────────────────────────────────────────
    if data == "manage_force_sub":
        if not is_admin:
            return
        from handlers.admin_panel import _show_channels_panel
        await _show_channels_panel(update, context, query)
        return

    if data == "fsub_add":
        if not is_admin:
            return
        user_states[uid] = "PENDING_CHANNEL_POST_OR_TEXT"
        # Reuse ADD_CHANNEL_USERNAME state for text input
        user_states[uid] = 0  # ADD_CHANNEL_USERNAME = 0
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("➕ ADD FORCE-SUB CHANNEL") + "\n\n"
            + bq(
                b("Send @username, numeric ID, or forward a post:\n\n")
                + "• <code>@BeatAnime</code>\n"
                + "• <code>-1001234567890</code>\n"
                + "• Forward any message from the channel"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        context.user_data["bot_prompt_message_id"] = msg.message_id if msg else None
        return

    if data == "fsub_fwd_help":
        user_states[uid] = PENDING_CHANNEL_POST
        await safe_edit_text(
            query, b("📩 METHOD 3: Forward a Post") + "\n\n"
            + bq("1. Open the channel\n2. Forward any message to this bot\n\nThe bot reads the channel ID automatically."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_add")]]),
        )
        return

    if data == "fsub_remove_menu":
        if not is_admin:
            return
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels(return_usernames_only=False)
        if not channels:
            await safe_answer(query, "No channels to remove.")
            return
        buttons = [_btn(f"{title or uname}", f"fsub_del_{uname}") for uname, title, jbr in channels]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_force_sub"), _close_btn()])
        await safe_edit_text(query, b("SELECT CHANNEL TO REMOVE"), reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("fsub_del_"):
        if not is_admin:
            return
        uname = data[len("fsub_del_"):]
        from database_dual import delete_force_sub_channel
        delete_force_sub_channel(uname)
        await safe_answer(query, f"Removed: {uname}")
        await button_handler(update, context, "manage_force_sub")
        return

    if data == "fsub_list_full":
        if not is_admin:
            return
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels(return_usernames_only=False)
        text = b(f"ALL FORCE-SUB CHANNELS ({len(channels)})") + "\n\n"
        for i, (uname, title, jbr) in enumerate(channels, 1):
            jbr_str = " ✔️ JBR" if jbr else ""
            text += f"<b>{i}.</b> {e(title or uname)}{jbr_str}\n    ID: <code>{e(str(uname))}</code>\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    if data == "fsub_link_stats":
        if not is_admin:
            return
        try:
            from database_dual import get_links_count
            total = get_links_count()
        except Exception:
            total = "N/A"
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels()
        await safe_answer(query, f"Total links: {total} | Channels: {len(channels)}")
        return

    if data == "generate_links":
        if not is_admin:
            return
        user_states[uid] = GENERATE_LINK_IDENTIFIER
        await safe_edit_text(
            query,
            b(small_caps("🔗 generate channel link")) + "\n\n"
            + bq(b(small_caps("send the channel @username, numeric ID, or forward a post:"))),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    if data == "admin_show_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import backup_command
        await backup_command(update, context)
        return

    # ── Clone management ───────────────────────────────────────────────────────
    if data in ("clones_disable", "clones_enable"):
        if not is_admin:
            return
        from database_dual import set_setting
        set_setting("clones_disabled", "true" if data == "clones_disable" else "false")
        status = "disabled 🚫" if data == "clones_disable" else "enabled ✅"
        await safe_answer(query, f"Clone feature {status}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "manage_clones":
        if not is_admin:
            return
        from handlers.clones import show_clones_panel
        await show_clones_panel(update, context, query)
        return

    if data == "clone_add":
        if not is_admin:
            return
        user_states[uid] = ADD_CLONE_TOKEN
        await safe_edit_text(
            query, b("🤖 Add Clone Bot") + "\n\n" + bq(b("Send the BOT TOKEN of the clone bot.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_clones")]]),
        )
        return

    if data == "clone_remove":
        if not is_admin:
            return
        from handlers.clones import show_remove_clone_menu
        await show_remove_clone_menu(query)
        return

    if data.startswith("clone_del_"):
        if not is_admin:
            return
        uname = data[len("clone_del_"):]
        from database_dual import remove_clone_bot
        remove_clone_bot(uname)
        await safe_answer(query, f"Removed @{uname}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_refresh_cmds":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        from telegram import Bot
        from lifecycle import _register_bot_commands_on_bot
        clones = get_all_clone_bots(active_only=True)
        count = 0
        for _, token, uname, _, _ in clones:
            try:
                clone_bot = Bot(token=token)
                await _register_bot_commands_on_bot(clone_bot)
                count += 1
            except Exception:
                pass
        await safe_answer(query, f"Commands refreshed on {count} clone(s).")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_remove_menu":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        clones = get_all_clone_bots(active_only=True)
        if not clones:
            await safe_answer(query, "No clone bots to remove.")
            return
        buttons = [_btn(f"@{c[2]}", f"clone_del_{c[2]}") for c in clones]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_clones"), _close_btn()])
        await safe_edit_text(
            query, b("SELECT CLONE TO REMOVE"),
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data == "clone_list_full":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        clones = get_all_clone_bots()
        text = b(f"ALL CLONE BOTS ({len(clones)})") + "\n\n"
        for i, (cid, token, uname, active, added) in enumerate(clones, 1):
            st = "🟢" if active else "🔴"
            text += f"<b>{i}.</b> {st} @{e(uname or '?')}\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    if data == "clone_move_links":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_MOVE_LINKS"
        await safe_edit_text(
            query,
            b("MOVE LINKS") + "\n\n"
            + bq("Send: <code>@from_bot @to_bot</code>\nAll links will be reassigned."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    # ── Settings ───────────────────────────────────────────────────────────────
    if data == "admin_settings":
        if not is_admin:
            return
        from handlers.admin_panel import show_settings_panel
        await show_settings_panel(update, context, query)
        return

    if data == "toggle_maintenance":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("maintenance_mode", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("maintenance_mode", new_val)
        await safe_answer(query, f"Maintenance {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "toggle_clone_redirect":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("clone_redirect_enabled", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("clone_redirect_enabled", new_val)
        await safe_answer(query, f"Clone redirect {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    # ── Auto-delete toggle ─────────────────────────────────────────────────────
    if data == "toggle_auto_delete":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("auto_delete_messages", "true")
        new = "false" if cur == "true" else "true"
        set_setting("auto_delete_messages", new)
        await safe_answer(query, small_caps(f"auto-delete: {'on' if new == 'true' else 'off'}"))
        from handlers.admin_panel import show_settings_panel
        await show_settings_panel(update, context, query)
        return

    if data == "set_dm_del_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_DM_DEL_DELAY"
        try:
            await query.delete_message()
        except Exception:
            pass
        from database_dual import get_setting
        cur = get_setting("auto_delete_dm_delay", "120")
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set dm auto-delete delay")) + "\n\n"
            + bq(
                small_caps(f"current: {cur}s") + "\n"
                + small_caps("send number of seconds (e.g. 120 = 2 min, 0 = off)\n"
                             "this applies to all bot messages in private chat")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    if data == "set_gc_del_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_GC_DEL_DELAY"
        try:
            await query.delete_message()
        except Exception:
            pass
        from database_dual import get_setting
        cur = get_setting("auto_delete_gc_delay", "60")
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set gc auto-delete delay")) + "\n\n"
            + bq(
                small_caps(f"current: {cur}s") + "\n"
                + small_caps("send number of seconds (e.g. 60 = 1 min, 0 = off)\n"
                             "posters and chatbot replies are never deleted")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    if data == "toggle_clean_gc":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("clean_gc_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("clean_gc_enabled", new_val)
        await safe_answer(query, f"Clean GC {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_link_expiry":
        if not is_admin:
            return
        from database_dual import get_setting
        current_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(f"<b>Current:</b> {current_exp} minutes\n\nSend a number (1-60):"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_settings"), _close_btn()]]),
        )
        return

    if data == "admin_watermarks_toggle":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("watermarks_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("watermarks_enabled", new_val)
        await safe_answer(query, f"Watermarks {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_spam_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        spam_protect = get_setting("spam_protection_enabled", "true") == "true"
        flood_limit  = get_setting("flood_limit", "5")
        flood_window = get_setting("flood_window_sec", "10")
        text_sp = (
            b("SPAM PROTECTION") + "\n\n"
            + bq(
                f"<b>Status:</b> {'🟢 Enabled' if spam_protect else '🔴 Disabled'}\n"
                f"<b>Flood limit:</b> {flood_limit} msgs\n"
                f"<b>Flood window:</b> {flood_window}s\n\n"
                "Anti-spam covers:\n"
                " ✔️ Flood detection\n"
                " ✔️ Message rate limiting\n"
                " ✔️ User cooldowns on anime requests\n"
                " ✔️ Banned user blocking\n"
                " ✔️ Maintenance mode blocking"
            )
        )
        sp_grid = [
            _btn("TOGGLE " + ("🟢" if spam_protect else "🔴"), "toggle_spam_protect"),
            _btn("FLOOD LIMIT",  "set_flood_limit"),
            _btn("FLOOD WINDOW", "set_flood_window"),
        ]
        sp_rows = _grid3(sp_grid)
        sp_rows.append([_back_btn("admin_settings"), _close_btn()])
        await safe_edit_text(query, text_sp, reply_markup=InlineKeyboardMarkup(sp_rows))
        return

    if data == "toggle_spam_protect":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("spam_protection_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("spam_protection_enabled", new_val)
        await safe_answer(query, f"Spam protection {'on' if new_val == 'true' else 'off'}")
        await button_handler(update, context, "admin_spam_settings")
        return

    if data == "set_backup_channel":
        if not is_admin:
            return
        user_states[uid] = SET_BACKUP_CHANNEL
        await safe_edit_text(
            query,
            b(" Set Backup Channel URL") + "\n\n"
            + bq(b("Send the backup channel URL (e.g., https://t.me/backup_channel)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_settings")]]),
        )
        return

    # ── Text style ─────────────────────────────────────────────────────────────
    if data == "admin_text_style":
        if not is_admin:
            return
        try:
            from text_style import build_text_style_keyboard, get_text_style_panel_text
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id, get_text_style_panel_text(),
                reply_markup=build_text_style_keyboard(),
            )
        except Exception:
            await safe_answer(query, "Text style module unavailable.")
        return

    if data.startswith("text_style_set_"):
        if not is_admin:
            return
        style = data[len("text_style_set_"):]
        if style in ("normal", "smallcaps", "bold"):
            try:
                from text_style import set_style, build_text_style_keyboard, get_text_style_panel_text
                set_style(style)
                await safe_answer(query, f"✅ Text style: {style}")
                await safe_edit_text(
                    query, get_text_style_panel_text(), reply_markup=build_text_style_keyboard()
                )
            except Exception:
                pass
        return

    # ── Filter poster ──────────────────────────────────────────────────────────
    if data == "admin_filter_poster":
        if not is_admin:
            return
        try:
            from filter_poster import (
                build_filter_poster_settings_keyboard, get_filter_poster_settings_text
            )
            _fp_text = get_filter_poster_settings_text(chat_id)
            _fp_kb   = build_filter_poster_settings_keyboard(chat_id)
            try:
                await query.edit_message_text(_fp_text, parse_mode=ParseMode.HTML, reply_markup=_fp_kb)
            except Exception:
                try:
                    await query.edit_message_caption(caption=_fp_text, parse_mode=ParseMode.HTML, reply_markup=_fp_kb)
                except Exception:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_message(
                        chat_id=chat_id, text=_fp_text, parse_mode=ParseMode.HTML,
                        reply_markup=_fp_kb, disable_web_page_preview=True,
                    )
        except Exception as _fpe:
            logger.debug(f"admin_filter_poster: {_fpe}")
            await safe_answer(query, "Filter poster module unavailable.")
        return

    if data.startswith("fp_toggle_"):
        if not is_admin:
            return
        try:
            fp_cid = int(data.split("_")[-1])
        except Exception:
            fp_cid = 0
        try:
            from filter_poster import (
                _get_filter_poster_enabled, _set_filter_poster_enabled,
                build_filter_poster_settings_keyboard, get_filter_poster_settings_text,
            )
            _set_filter_poster_enabled(fp_cid, not _get_filter_poster_enabled(fp_cid))
            _t = get_filter_poster_settings_text(fp_cid)
            _k = build_filter_poster_settings_keyboard(fp_cid)
            await _smart_edit(_t, _k)
        except Exception:
            pass
        return

    if data.startswith("fp_pregen_all_"):
        if not is_admin:
            return
        from jobs.scheduled import _pregen_all_filter_posters
        asyncio.create_task(_pregen_all_filter_posters(context.bot, uid, chat_id))
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🎌 poster pre-generation started!")) + "\n"
            + bq(small_caps("generating posters for all registered anime channels in background.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data.startswith("fp_tmpl_"):
        if not is_admin:
            return
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                fp_chat_id = int(parts[2])
                fp_template = parts[3]
                if _FILTER_POSTER_AVAILABLE:
                    _set_default_poster_template(fp_chat_id, fp_template)
                    await safe_answer(query, f"✅ Template set to {fp_template}")
                    _t2 = get_filter_poster_settings_text(fp_chat_id)
                    _k2 = build_filter_poster_settings_keyboard(fp_chat_id)
                    await _smart_edit(_t2, _k2)
            except Exception:
                pass
        return

    if data.startswith("fp_mode_toggle_"):
        if not is_admin:
            return
        try:
            fp_chat_id = int(data.split("_")[-1])
        except Exception:
            fp_chat_id = 0
        if _FILTER_POSTER_AVAILABLE:
            try:
                from filter_poster import get_filter_mode, set_filter_mode
                cur = get_filter_mode(fp_chat_id)
                new_mode = "text" if cur == "poster" else "poster"
                set_filter_mode(fp_chat_id, new_mode)
                label = "TEXT (link only)" if new_mode == "text" else "POSTER (full card)"
                await safe_answer(query, f"✔️ Mode: {label}")
                _t3 = get_filter_poster_settings_text(fp_chat_id)
                _k3 = build_filter_poster_settings_keyboard(fp_chat_id)
                await _smart_edit(_t3, _k3)
            except Exception:
                pass
        return

    if data.startswith("fp_wm_toggle_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[3]
        try:
            fp_chat_id = int(parts[4])
        except Exception:
            fp_chat_id = chat_id
        if _FILTER_POSTER_AVAILABLE:
            try:
                from filter_poster import get_wm_layer, set_wm_layer
                ldata = get_wm_layer(fp_chat_id, layer)
                ldata["enabled"] = not ldata.get("enabled", False)
                set_wm_layer(fp_chat_id, layer, ldata)
                state_str = "enabled" if ldata["enabled"] else "disabled"
                await safe_answer(query, f"✔️ Layer {layer.upper()} {state_str}")
                _t3 = get_filter_poster_settings_text(fp_chat_id)
                _k3 = build_filter_poster_settings_keyboard(fp_chat_id)
                await _smart_edit(_t3, _k3)
            except Exception:
                pass
        return

    if data.startswith("fp_wm_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[2]
        try:
            fp_chat_id = int(parts[3])
        except Exception:
            fp_chat_id = chat_id
        if not _FILTER_POSTER_AVAILABLE:
            await safe_answer(query, "Filter poster module unavailable.")
            return
        try:
            from filter_poster import get_wm_layer
            ldata = get_wm_layer(fp_chat_id, layer)
        except Exception:
            ldata = {}
        pos_list = "center | bottom | top | left | right | bottom-left | bottom-right | top-left | top-right"
        layer_names = {"a": "PRIMARY TEXT", "b": "SECONDARY TEXT", "c": "STICKER / IMAGE"}
        if layer == "c":
            panel_text = (
                b("WATERMARK LAYER C — STICKER / IMAGE") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-left'))}\n"
                    f"<b>Scale:</b> {ldata.get('scale', 0.12)} (0.05–0.30)\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 200)} (0–255)\n\n"
                    "<b>To set sticker:</b> Send any Telegram sticker as a reply.\n"
                    "<b>To set image:</b> Send: <code>https://url | position | scale | opacity</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        else:
            panel_text = (
                b(f"WATERMARK LAYER {layer.upper()} — {layer_names.get(layer, '')}") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Text:</b> {e(ldata.get('text', '—'))}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-right'))}\n"
                    f"<b>Font size:</b> {ldata.get('font_size', 24)}\n"
                    f"<b>Color:</b> {e(ldata.get('color', '#FFFFFF'))}\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 150)} (0–255)\n\n"
                    "<b>Send format:</b> <code>text | position | size | #color | opacity</code>\n"
                    "<b>Example:</b> <code>BeatAnime | bottom-right | 24 | #FFFFFF | 150</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        user_states[uid] = f"AWAITING_WM_LAYER_{layer.upper()}_{fp_chat_id}"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id, panel_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🟢 ENABLE" if not ldata.get("enabled") else "🔴 DISABLE",
                    callback_data=f"fp_wm_toggle_{layer}_{fp_chat_id}",
                )],
                [_back_btn("admin_filter_poster"), _close_btn()],
            ]),
        )
        return

    if data == "fp_set_autodel":
        if not is_admin:
            return
        try:
            from database_dual import get_setting
            cur_del = int(get_setting(f"filter_auto_delete_{chat_id}", "300"))
        except Exception:
            cur_del = 300
        user_states[uid] = "AWAITING_FILTER_AUTODEL"
        await safe_edit_text(
            query,
            b("FILTER AUTO-DELETE TIME") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_del}s ({cur_del // 60} min)\n\n"
                "Send seconds before poster + link auto-deletes:\n"
                "• <code>0</code> = never delete\n"
                "• <code>300</code> = 5 minutes (default)\n"
                "• <code>600</code> = 10 minutes\n"
                "• <code>1800</code> = 30 minutes"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_set_linkexpiry":
        if not is_admin:
            return
        from database_dual import get_setting
        cur_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY_FP"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_exp} min\n\n"
                "Send minutes the join link stays valid:\n"
                "• <code>0</code> = permanent (no expiry)\n"
                "• <code>5</code> = 5 minutes (default)\n"
                "• <code>60</code> = 1 hour"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_view_cache":
        if not is_admin:
            return
        count = _get_cache_count() if _FILTER_POSTER_AVAILABLE else 0
        await safe_answer(query, f"📦 {count} posters cached")
        return

    if data == "fp_clear_cache":
        if not is_admin:
            return
        if _FILTER_POSTER_AVAILABLE:
            cleared = _clear_poster_cache()
            await safe_answer(query, f"🗑 Cleared {cleared} cached posters")
            try:
                await safe_edit_text(
                    query,
                    get_filter_poster_settings_text(chat_id),
                    reply_markup=build_filter_poster_settings_keyboard(chat_id),
                )
            except Exception:
                pass
        return

    if data == "fp_channel_info":
        if not is_admin:
            return
        try:
            from filter_poster import POSTER_DB_CHANNEL as _PDC
            if _PDC:
                await safe_answer(query, f"Poster DB Channel: {_PDC}")
            else:
                await safe_answer(query, "Set POSTER_DB_CHANNEL in env to enable poster saving")
        except Exception:
            await safe_answer(query, "Filter poster module unavailable.")
        return

    # ── Feature flags ──────────────────────────────────────────────────────────
    if data == "admin_feature_flags":
        if not is_admin:
            return
        user_states.pop(uid, None)
        from handlers.admin_panel import send_feature_flags_panel
        await send_feature_flags_panel(context, chat_id, query)
        return

    if data.startswith("flag_toggle_"):
        if not is_admin:
            return
        parts = data[len("flag_toggle_"):].rsplit("_", 1)
        if len(parts) == 2:
            from database_dual import set_setting
            flag_key, new_val = parts
            set_setting(flag_key, new_val)
            is_on = new_val in ("true", "1")
            await safe_answer(query, f"{'Enabled' if is_on else 'Disabled'}!")
            from handlers.admin_panel import send_feature_flags_panel
            await send_feature_flags_panel(context, chat_id, query)
        return

    # ── Category settings ──────────────────────────────────────────────────────
    if data == "admin_category_settings":
        if not is_admin:
            return
        keyboard = [
            [bold_button("TV SHOWS", callback_data="admin_category_settings_tvshow"),
             bold_button("MOVIES", callback_data="admin_category_settings_movie")],
            [bold_button("ANIME", callback_data="admin_category_settings_anime"),
             bold_button("MANGA", callback_data="admin_category_settings_manga")],
            [bold_button("POST SETTING", callback_data="admin_settings")],
            [bold_button("AUTO FORWARD", callback_data="admin_autoforward"),
             bold_button("POST SEARCH", callback_data="admin_cmd_list")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(query, b("Choose the category"), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    for cat_name in ("anime", "manga", "movie", "tvshow"):
        if data in (f"admin_category_settings_{cat_name}", f"settings_category_{cat_name}", f"cat_settings_{cat_name}"):
            from handlers.admin_panel import show_category_settings_menu
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_caption_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_CAPTION
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Set Caption Template for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the caption template with placeholders like {title}, {score}, etc.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")
                ]]),
            )
            return

        if data == f"cat_branding_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BRANDING
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f"🏷 Set Branding for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send your branding text (appended at the bottom of posts).")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Clear", callback_data=f"cat_brand_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_brand_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "branding", "")
            await safe_answer(query, "Branding cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_buttons_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BUTTONS
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Configure Buttons for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send button config, one per line:\nFormat: Button Text - https://url")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Clear Buttons", callback_data=f"cat_btns_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_btns_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "buttons", "[]")
            await safe_answer(query, "Buttons cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_font_{cat_name}":
            if not is_admin:
                return
            await safe_edit_text(
                query, b(small_caps(f"font style — {cat_name}")),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button(small_caps("normal"),     callback_data=f"cat_font_set_{cat_name}_normal"),
                     bold_button(small_caps("small caps"), callback_data=f"cat_font_set_{cat_name}_smallcaps")],
                    [_back_btn(f"cat_settings_{cat_name}"), _close_btn()],
                ]),
            )
            return

        if data == f"cat_btn_style_{cat_name}":
            if not is_admin:
                return
            try:
                from database_dual import get_setting
                cur_style = get_setting("button_style", "normal") or "normal"
            except Exception:
                cur_style = "normal"
            await safe_edit_text(
                query,
                b(small_caps(f"button caption style — {cat_name}")) + "\n\n"
                + bq(
                    small_caps("choose how button labels are styled:") + "\n"
                    + f"<b>{small_caps('Current')}:</b> <code>{e(cur_style)}</code>\n\n"
                    + small_caps("normal") + " — Standard text\n"
                    + small_caps("smallcaps") + " — sᴍᴀʟʟ ᴄᴀᴘs ᴛᴇxᴛ\n"
                    + small_caps("custom") + " — Keep exact text you type"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button(small_caps("normal"),    callback_data=f"cat_btn_style_set_{cat_name}_normal"),
                     bold_button(small_caps("smallcaps"), callback_data=f"cat_btn_style_set_{cat_name}_smallcaps")],
                    [bold_button(small_caps("custom"),    callback_data=f"cat_btn_style_set_{cat_name}_custom")],
                    [_back_btn(f"cat_settings_{cat_name}"), _close_btn()],
                ]),
            )
            return

        if data.startswith(f"cat_btn_style_set_{cat_name}_"):
            if not is_admin:
                return
            style_val = data[len(f"cat_btn_style_set_{cat_name}_"):]
            if style_val in ("normal", "smallcaps", "custom"):
                from database_dual import set_setting
                set_setting("button_style", style_val)
                await safe_answer(query, small_caps(f"button style set to {style_val}"))
                from handlers.admin_panel import show_category_settings_menu
                await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data.startswith(f"cat_font_set_{cat_name}_"):
            if not is_admin:
                return
            font_val = data[len(f"cat_font_set_{cat_name}_"):]
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "font_style", font_val)
            await safe_answer(query, f"Font set to {font_val}")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_watermark_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_WATERMARK_TEXT
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Watermark for {e(cat_name.upper())}") + "\n\n"
                + bq("Send watermark text.\nOptionally: <code>Text | position</code>\nPositions: center bottom top bottom-right\nSend <code>none</code> to remove."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        if data == f"cat_wm_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            update_category_field(cat_name, "watermark_text", None)
            update_category_field(cat_name, "logo_file_id", None)
            await safe_answer(query, "Watermark cleared", show_alert=True)
            return

        if data == f"cat_logo_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_LOGO
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f"LOGO — {e(cat_name.upper())}") + "\n\n"
                + bq("Send an image file to use as logo overlay.\nSend <code>none</code> to remove."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        if data == f"cat_preview_{cat_name}":
            await safe_answer(query, "Generating preview poster...")
            defaults = {"anime": "Naruto", "manga": "One Piece", "movie": "Avengers", "tvshow": "Breaking Bad"}
            try:
                from filter_poster import get_or_generate_poster
                asyncio.create_task(get_or_generate_poster(
                    bot=context.bot, chat_id=chat_id,
                    title=defaults.get(cat_name, "Demo"),
                    template={"anime": "ani", "manga": "anim", "movie": "ani", "tvshow": "ani"}.get(cat_name, "ani"),
                    media_type={"anime": "ANIME", "manga": "MANGA", "movie": "MOVIE", "tvshow": "TV"}.get(cat_name, "ANIME"),
                ))
            except Exception:
                pass
            return

        if data == f"cat_thumbnail_{cat_name}":
            if not is_admin:
                return
            # Show poster LAYOUT/STYLE template picker — not thumbnail URL
            try:
                from handlers.post_gen import get_category_settings
                cur_tmpl = get_category_settings(cat_name).get("template_name", "ani")
            except Exception:
                cur_tmpl = "ani"

            # All available poster visual templates
            _POSTER_TEMPLATES = {
                # Palette templates (same structure, different colours)
                "ani":    ("🎌", "ᴀɴɪᴍᴇ ᴄʟᴀssɪᴄ",    "Dark blue · AniList · Landscape bleed"),
                "dark":   ("🌑", "ᴅᴀʀᴋ ᴘᴜʀᴘʟᴇ",       "Deep dark · Purple accent · Minimal"),
                "light":  ("☀️", "ᴄʟᴇᴀɴ ʟɪɢʜᴛ",       "White BG · Blue accent · Clean look"),
                "crun":   ("🍊", "ᴄʀᴜɴᴄʜʏʀᴏʟʟ",        "Orange accent · CR logo · Warm tone"),
                "net":    ("🔴", "ɴᴇᴛꜰʟɪx",             "Pure black · Red accent · NF logo"),
                "mod":    ("✨", "ᴍᴏᴅᴇʀɴ ᴛᴇᴀʟ",        "Dark BG · Teal accent · Sleek edges"),
                "anim":   ("📗", "ᴍᴀɴɢᴀ ɢʀᴇᴇɴ",        "Dark green · AniList · Manga style"),
                "netm":   ("🟥", "ɴᴇᴛꜰʟɪx ᴍᴀɴɢᴀ",      "Netflix style for manga"),
                # Reference-image layouts (completely different structure)
                "stream": ("📺", "sᴛʀᴇᴀᴍ",             "Cover right · Episode card · Branding badge"),
                "vessel": ("🎴", "ᴠᴇssᴇʟ",             "Split panel · Portrait cover · Vertical brand"),
                "splash": ("🎞", "sᴘʟᴀsʜ",             "Full bleed · Cinematic · Title centred"),
                "od3n":   ("⬛", "ᴏᴅ3ɴ",               "Character centre · Vertical title · Info right"),
            }
            # Filter to category-relevant templates
            _CAT_TEMPLATES = {
                "anime":  ["ani", "stream", "od3n", "vessel", "splash", "dark", "light", "crun", "net", "mod"],
                "manga":  ["anim", "vessel", "splash", "netm", "dark", "light", "mod", "stream", "od3n"],
                "movie":  ["stream", "net", "od3n", "splash", "dark", "light", "vessel", "mod", "crun", "ani"],
                "tvshow": ["stream", "net", "od3n", "splash", "dark", "light", "vessel", "mod", "crun", "ani"],
            }
            tmpl_keys = _CAT_TEMPLATES.get(cat_name, list(_POSTER_TEMPLATES.keys()))

            text = (
                b(small_caps(f"🎨 poster layout — {cat_name}")) + "\n\n"
                + bq(
                    small_caps("choose a visual layout style for") + f" <b>{e(cat_name)}</b>\n"
                    + small_caps("current: ") + f"<code>{e(cur_tmpl)}</code>"
                ) + "\n\n"
            )
            for tk in tmpl_keys:
                em, lbl, desc = _POSTER_TEMPLATES.get(tk, ("🖼", tk, ""))
                active = " ✅" if tk == cur_tmpl else ""
                text += f"{em} <b>{lbl}</b>{active}\n<i>{small_caps(desc)}</i>\n\n"

            rows = []
            row = []
            for tk in tmpl_keys:
                em, lbl, _ = _POSTER_TEMPLATES.get(tk, ("🖼", tk, ""))
                active = "✅" if tk == cur_tmpl else ""
                btn_lbl = f"{em} {active}" if active else em
                row.append(bold_button(f"{btn_lbl} {small_caps(tk)}", callback_data=f"cat_tmpl_set_{cat_name}_{tk}"))
                if len(row) == 3:
                    rows.append(row); row = []
            if row: rows.append(row)
            rows.append([_back_btn(f"cat_settings_{cat_name}"), _close_btn()])

            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows)
            )
            return

        # ── Poster template selected ────────────────────────────────────────────
        if data.startswith(f"cat_tmpl_set_{cat_name}_"):
            if not is_admin:
                return
            new_tmpl = data[len(f"cat_tmpl_set_{cat_name}_"):]
            valid = ["ani","dark","light","crun","net","mod","anim","netm","lightm","darkm","netcr","stream","vessel","splash","od3n"]
            if new_tmpl not in valid:
                await safe_answer(query, small_caps("❌ unknown template"))
                return
            from handlers.post_gen import update_category_field
            update_category_field(cat_name, "template_name", new_tmpl)
            await safe_answer(query, small_caps(f"✅ template set to {new_tmpl}"))
            from handlers.admin_panel import show_category_settings_menu
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

    # ── User management ────────────────────────────────────────────────────────
    if data == "user_management":
        if not is_admin:
            return
        from handlers.admin_panel import show_user_management_panel
        await show_user_management_panel(update, context, query)
        return

    if data == "admin_export_users_quick":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import exportusers_command
        asyncio.create_task(exportusers_command(update, context))
        await safe_answer(query, small_caps("📤 exporting users…"))
        return

    if data == "admin_import_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_USERS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Users</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with user IDs.\n\n"
                "<b>CSV format (columns):</b>\n"
                "<code>user_id, username, first_name</code>\n\n"
                "<b>Excel:</b> First column must be <code>user_id</code>.\n\n"
                "Send the file now, or /cancel to abort."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    if data == "admin_import_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_LINKS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Links</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with link data.\n\n"
                "<b>CSV columns:</b> <code>link_id, file_name, channel_id</code>\n\n"
                "Send the file now, or /cancel to abort."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    if data == "um_list_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import listusers_command
        context.args = []
        await listusers_command(update, context)
        return

    if data == "um_search_user":
        if not is_admin:
            return
        user_states[uid] = SEARCH_USER_INPUT
        await safe_edit_text(
            query,
            b("🔍 Search User") + "\n\n" + bq(b("Send user ID or @username:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_ban_user":
        if not is_admin:
            return
        user_states[uid] = BAN_USER_INPUT
        await safe_edit_text(
            query,
            b("🚫 Ban User") + "\n\n" + bq(b("Send user ID or @username to ban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_unban_user":
        if not is_admin:
            return
        user_states[uid] = UNBAN_USER_INPUT
        await safe_edit_text(
            query,
            b("✅ Unban User") + "\n\n" + bq(b("Send user ID or @username to unban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_delete_user":
        if not is_admin:
            return
        user_states[uid] = DELETE_USER_INPUT
        await safe_edit_text(
            query,
            b("🗑 Delete User") + "\n\n" + bq(b("Send the user ID to permanently delete from database:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_banned_list":
        if not is_admin:
            return
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT user_id, username, first_name FROM users WHERE banned = TRUE LIMIT 20"
                )
                banned = cur.fetchall() or []
        except Exception:
            banned = []
        if not banned:
            await safe_answer(query, "No banned users.")
            return
        text = b(f"🚫 Banned Users ({len(banned)}):") + "\n\n"
        for buid, buname, bfname in banned:
            text += f"• {e(bfname or '')} @{e(buname or '')} {code(str(buid))}\n"
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup([[_back_btn("user_management")]]))
        return

    if data.startswith("user_page_"):
        if not is_admin:
            return
        offset = int(data[len("user_page_"):])
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import listusers_command
        context.args = [str(offset)]
        await listusers_command(update, context)
        return

    if data.startswith("manage_user_"):
        if not is_admin:
            return
        target_uid_mu = int(data[len("manage_user_"):])
        try:
            from database_dual import get_user_info_by_id
            user_info = get_user_info_by_id(target_uid_mu)
        except Exception:
            user_info = None
        if not user_info:
            await safe_answer(query, "User not found.")
            return
        u_id, u_uname, u_fname, u_lname, u_joined, u_banned = user_info
        name = f"{u_fname or ''} {u_lname or ''}".strip() or "N/A"
        text = (
            b("👤 User Details") + "\n\n"
            f"<b>ID:</b> {code(str(u_id))}\n"
            f"<b>Name:</b> {e(name)}\n"
            f"<b>Username:</b> {'@' + e(u_uname) if u_uname else '—'}\n"
            f"<b>Joined:</b> {code(str(u_joined)[:16])}\n"
            f"<b>Status:</b> {'🚫 Banned' if u_banned else '✅ Active'}"
        )
        keyboard = []
        if u_banned:
            keyboard.append([bold_button("Unban", callback_data=f"user_unban_{u_id}")])
        else:
            keyboard.append([bold_button("🚫 Ban", callback_data=f"user_ban_{u_id}")])
        keyboard.append([bold_button("Delete", callback_data=f"user_del_{u_id}")])
        keyboard.append([_back_btn("user_management")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_list_page_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from database_dual import get_user_count, get_all_users
        offset = page * 10
        total = get_user_count()
        users = get_all_users(limit=10, offset=offset)
        text = b(f"USERS {offset+1}–{min(offset+10, total)} of {total:,}") + "\n\n"
        for uid2, uname, fname, lname, joined, banned in users:
            name = f"{fname or ''} {lname or ''}".strip() or "N/A"
            st = "🔴" if banned else "🟢"
            text += f"{st} <b>{e(name[:20])}</b> — @{e(uname or str(uid2))}\n"
        nav = []
        if page > 0:
            nav.append(_btn("PREV", f"user_list_page_{page-1}"))
        if total > offset + 10:
            nav.append(_btn("NEXT", f"user_list_page_{page+1}"))
        rows = [nav] if nav else []
        rows.append([_back_btn("user_management"), _close_btn()])
        try:
            await query.delete_message()
        except Exception:
            pass
        await _deliver_panel(context.bot, chat_id, "users", text, InlineKeyboardMarkup(rows), query=None)
        return

    for _state_name, _cb, _state_const in (
        ("user_search", "AWAITING_USER_SEARCH", "AWAITING_USER_SEARCH"),
        ("user_ban_input", "AWAITING_BAN_USER", "AWAITING_BAN_USER"),
        ("user_unban_input", "AWAITING_UNBAN_USER", "AWAITING_UNBAN_USER"),
        ("user_delete_input", "AWAITING_DELETE_USER", "AWAITING_DELETE_USER"),
    ):
        if data == _state_name:
            if not is_admin:
                return
            user_states[uid] = _state_const
            labels = {
                "user_search": "Search User", "user_ban_input": "Ban User",
                "user_unban_input": "Unban User", "user_delete_input": "Delete User",
            }
            await safe_edit_text(
                query, b(labels[data]) + "\n\n" + bq("Send @username or user ID:"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
            return

    if data.startswith("user_ban_"):
        if not is_admin:
            return
        from database_dual import ban_user
        target_uid = int(data[len("user_ban_"):])
        if target_uid not in (ADMIN_ID, OWNER_ID):
            ban_user(target_uid)
            await safe_answer(query, "User banned.")
        return

    if data.startswith("user_unban_"):
        if not is_admin:
            return
        from database_dual import unban_user
        target_uid = int(data[len("user_unban_"):])
        unban_user(target_uid)
        await safe_answer(query, "User unbanned.")
        return

    if data.startswith("user_del_"):
        if not is_admin:
            return
        from database_dual import db_manager
        target_uid = int(data[len("user_del_"):])
        if target_uid in (ADMIN_ID, OWNER_ID):
            await safe_answer(query, "Cannot delete admin.", show_alert=True)
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s", (target_uid,))
        except Exception:
            pass
        await safe_answer(query, "User deleted.")
        await button_handler(update, context, "user_management")
        return

    # ── Upload manager ─────────────────────────────────────────────────────────
    if data == "upload_menu":
        if not is_admin:
            return
        from handlers.upload import load_upload_progress, show_upload_menu
        await load_upload_progress()
        try:
            await query.delete_message()
        except Exception:
            pass
        await show_upload_menu(chat_id, context)
        return

    if data == "upload_preview":
        if not is_admin:
            return
        from handlers.upload import build_caption_from_progress, get_upload_menu_markup
        cap = build_caption_from_progress()
        await safe_edit_text(query, b("👁 Caption Preview:") + "\n\n" + cap, reply_markup=get_upload_menu_markup())
        return

    if data == "upload_toggle_auto":
        if not is_admin:
            return
        from handlers.upload import save_upload_progress, show_upload_menu
        upload_progress["auto_caption_enabled"] = not upload_progress["auto_caption_enabled"]
        await save_upload_progress()
        status = "ON" if upload_progress["auto_caption_enabled"] else "OFF"
        await safe_answer(query, f"Auto-caption: {status}")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data == "upload_reset":
        if not is_admin:
            return
        from handlers.upload import save_upload_progress, show_upload_menu
        upload_progress["episode"] = 1
        upload_progress["video_count"] = 0
        await save_upload_progress()
        await safe_answer(query, "Episode reset to 1.")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data.startswith("upload_toggle_q_"):
        if not is_admin:
            return
        from handlers.upload import save_upload_progress
        q_val = data[len("upload_toggle_q_"):]
        if q_val in upload_progress["selected_qualities"]:
            upload_progress["selected_qualities"].remove(q_val)
        else:
            upload_progress["selected_qualities"].append(q_val)
        await save_upload_progress()
        await safe_answer(query, f"{'Added' if q_val in upload_progress['selected_qualities'] else 'Removed'} {q_val}")
        await button_handler(update, context, "upload_quality_menu")
        return

    if data in ("upload_set_caption", "upload_set_anime_name", "upload_set_season",
                "upload_set_episode", "upload_set_total", "upload_set_channel", "upload_quality_menu",
                "upload_clear_db", "upload_confirm_clear", "upload_back"):
        if not is_admin:
            return
        from handlers.upload import show_upload_menu, save_upload_progress, get_upload_menu_markup
        from core.config import ALL_QUALITIES
        if data == "upload_set_caption":
            user_states[uid] = UPLOAD_SET_CAPTION
            await safe_edit_text(
                query, b(" Set Caption Template") + "\n\n"
                + bq(b("Send the new caption template.\nPlaceholders: {anime_name}, {season}, {episode}, {quality}")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
            )
        elif data == "upload_set_anime_name":
            user_states[uid] = UPLOAD_SET_CAPTION
            context.user_data["upload_field"] = "anime_name"
            await safe_edit_text(
                query, b("🎌 Set Anime Name") + "\n\n"
                + bq(b(f"Current: {e(upload_progress.get('anime_name', 'Anime Name'))}\n\nSend new name:")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
            )
        elif data == "upload_set_season":
            user_states[uid] = UPLOAD_SET_SEASON
            await safe_edit_text(query, b(f" Set Season\n\nCurrent: {upload_progress['season']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_episode":
            user_states[uid] = UPLOAD_SET_EPISODE
            await safe_edit_text(query, b(f" Set Episode\n\nCurrent: {upload_progress['episode']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_total":
            user_states[uid] = UPLOAD_SET_TOTAL
            await safe_edit_text(query, b(f" Set Total Episodes\n\nCurrent: {upload_progress['total_episode']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_channel":
            user_states[uid] = UPLOAD_SET_CHANNEL
            await safe_edit_text(query, b("📢 Set Target Channel\n\nSend @username or ID:"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_quality_menu":
            keyboard = []
            row = []
            for q_val in ALL_QUALITIES:
                selected = q_val in upload_progress["selected_qualities"]
                mark = "✅ " if selected else ""
                row.append(bold_button(f"{mark}{q_val}", callback_data=f"upload_toggle_q_{q_val}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([_back_btn("upload_back")])
            await safe_edit_text(query, b("🎛 Quality Settings:"), reply_markup=InlineKeyboardMarkup(keyboard))
        elif data == "upload_clear_db":
            await safe_edit_text(
                query, b(" Clear Upload Database?") + "\n\n" + bq(b("This will reset all progress counters.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Yes, Clear", callback_data="upload_confirm_clear"),
                    bold_button("CANCEL", callback_data="upload_back"),
                ]]),
            )
        elif data == "upload_confirm_clear":
            try:
                from database_dual import db_manager
                with db_manager.get_cursor() as cur:
                    cur.execute("DELETE FROM bot_progress WHERE id = 1")
                    cur.execute("""
                        INSERT INTO bot_progress (id, base_caption, selected_qualities, auto_caption_enabled, anime_name)
                        VALUES (1, %s, %s, %s, %s)
                    """, (
                        DEFAULT_CAPTION,
                        ",".join(upload_progress["selected_qualities"]),
                        upload_progress["auto_caption_enabled"],
                        upload_progress.get("anime_name", "Anime Name"),
                    ))
                from handlers.upload import load_upload_progress
                await load_upload_progress()
                await safe_answer(query, "Database cleared!")
                try:
                    await query.delete_message()
                except Exception:
                    pass
                await show_upload_menu(chat_id, context)
            except Exception as exc:
                await safe_answer(query, f"Error: {str(exc)[:50]}", show_alert=True)
        elif data == "upload_back":
            await show_upload_menu(chat_id, context, query.message)
        return

    # ── Auto-forward ───────────────────────────────────────────────────────────
    if data == "admin_autoforward":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoforward_menu
        await _show_autoforward_menu(context, chat_id)
        return

    if data == "af_add_connection":
        if not is_admin:
            return
        user_states[uid] = AF_ADD_CONNECTION_SOURCE
        await safe_edit_text(
            query, b("♻️ Add Auto-Forward Connection") + "\n\n"
            + bq(b("Step 1/2: SOURCE channel\n\nSend @username, -100ID, or forward a post:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
        )
        return

    if data == "af_set_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_DELAY"
        await safe_edit_text(
            query,
            b(small_caps("⏱ set auto-forward delay")) + "\n\n"
            + bq(small_caps("send delay in seconds (e.g. 30). send 0 for no delay.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_set_caption":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_CAPTION"
        await safe_edit_text(
            query,
            b(small_caps("✏️ set caption override")) + "\n\n"
            + bq(small_caps("send the caption text to append to all forwarded messages.\nsend /clear to remove caption override.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_replacements_menu":
        if not is_admin:
            return
        rows = []
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("SELECT id, old_pattern, new_pattern FROM auto_forward_replacements ORDER BY id LIMIT 10")
                rows = cur.fetchall() or []
        except Exception:
            pass
        text = b(small_caps("🔄 text replacements")) + "\n\n"
        if rows:
            for r_id, old_p, new_p in rows:
                text += f"• <code>{e(old_p)}</code> → <code>{e(new_p)}</code>\n"
        else:
            text += bq(small_caps("no replacements set."))
        text += "\n\n" + bq(small_caps("to add: /autoforward replacements add old_text new_text"))
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]))
        return

    if data == "af_bulk":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_BULK_COUNT"
        await safe_edit_text(
            query,
            b(small_caps("📦 bulk forward")) + "\n\n"
            + bq(small_caps("send the number of recent messages to forward from source channel (max 50).")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_filters_menu":
        if not is_admin:
            return
        dm_on = True
        grp_on = True
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT enable_in_dm, enable_in_group FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    dm_on, grp_on = bool(row[0]), bool(row[1])
        except Exception:
            pass
        dm_icon = "✅" if dm_on else "❌"
        grp_icon = "✅" if grp_on else "❌"
        ftext = (
            b("🔍 Auto-Forward Filters") + "\n\n"
            + bq(
                f"<b>Enable in DM:</b> {dm_icon}\n"
                f"<b>Enable in Group:</b> {grp_icon}\n\n"
                "<b>BLACKLIST:</b> Words that BLOCK a message from being forwarded.\n"
                "<b>WHITELIST:</b> When set, ONLY messages with a whitelisted word are forwarded.\n\n"
                "Leave whitelist empty to forward everything (except blacklisted)."
            )
        )
        fkb = [
            [bold_button(f"{dm_icon} Toggle DM", callback_data="af_toggle_dm"),
             bold_button(f"{grp_icon} Toggle Group", callback_data="af_toggle_group")],
            [bold_button("🚫 Blacklist Words", callback_data="af_blacklist"),
             bold_button("✅ Whitelist Words", callback_data="af_whitelist")],
            [bold_button("❓ Filter Guide", callback_data="af_filter_guide"),
             _back_btn("admin_autoforward")],
        ]
        await safe_edit_text(query, ftext, reply_markup=InlineKeyboardMarkup(fkb))
        return

    if data == "af_filter_guide":
        if not is_admin:
            return
        guide_text = (
            b("📖 How Filters Work") + "\n\n"
            + bq(
                "<b>Example scenario:</b>\n"
                "Forwarding from an anime channel but want to skip movie posts.\n\n"
                "<b>Step 1:</b> Add <code>movie</code> to Blacklist — any post with 'movie' is skipped.\n\n"
                "<b>Step 2 (optional):</b> Add <code>episode</code> to Whitelist — only 'episode' posts forward.\n\n"
                "<b>Note:</b> If Whitelist is EMPTY, all messages pass (except blacklisted)."
            )
        )
        await safe_edit_text(
            query, guide_text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        return

    if data in ("af_toggle_dm", "af_toggle_group"):
        if not is_admin:
            return
        col = "enable_in_dm" if data == "af_toggle_dm" else "enable_in_group"
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO auto_forward_filters (connection_id, enable_in_dm, enable_in_group)
                    VALUES (NULL, TRUE, TRUE)
                    ON CONFLICT DO NOTHING
                """)
                cur.execute(
                    f"UPDATE auto_forward_filters SET {col} = NOT {col} WHERE connection_id IS NULL"
                )
        except Exception as exc:
            logger.debug(f"af toggle error: {exc}")
        await safe_answer(query, small_caps("filter toggled!"))
        await button_handler(update, context, "af_filters_menu")
        return

    if data in ("af_blacklist", "af_whitelist"):
        if not is_admin:
            return
        kind = "Blacklist" if data == "af_blacklist" else "Whitelist"
        col = "blacklist_words" if data == "af_blacklist" else "whitelist_words"
        words = ""
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    f"SELECT {col} FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row and row[0]:
                    words = row[0]
        except Exception:
            pass
        await safe_edit_text(
            query,
            b(f" {kind} Words") + "\n\n"
            + bq(
                f"<b>Current:</b> {code(e(words or 'None'))}\n\n"
                "Send new comma-separated words to set the list:\n"
                "<i>e.g. word1, word2, word3</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        user_states[uid] = f"af_set_{col}"
        return

    if data == "af_toggle_all":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("autoforward_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("autoforward_enabled", new_val)
        await safe_answer(query, f"Auto-Forward {'enabled' if new_val == 'true' else 'disabled'}!")
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoforward_menu
        await _show_autoforward_menu(context, chat_id)
        return

    if data == "af_list_connections":
        if not is_admin:
            return
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active, delay_seconds
                    FROM auto_forward_connections ORDER BY id DESC LIMIT 20
                """)
                conns = cur.fetchall() or []
        except Exception:
            conns = []
        text = b(f"♻️ Auto-Forward Connections ({len(conns)}):") + "\n\n"
        keyboard = []
        for cid, src, tgt, active, delay in conns:
            status = "✅" if active else "❌"
            text += f"{status} {code(str(src))} → {code(str(tgt))}\n"
            keyboard.append([bold_button(f"{status} {str(src)[:15]} → {str(tgt)[:15]}", callback_data=f"af_conn_detail_{cid}")])
        keyboard.append([_back_btn("admin_autoforward")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_detail_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_detail_"):])
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active,
                           protect_content, silent, pin_message, delete_source, delay_seconds
                    FROM auto_forward_connections WHERE id = %s
                """, (conn_id,))
                conn = cur.fetchone()
        except Exception:
            conn = None
        if not conn:
            await safe_answer(query, "Connection not found.")
            return
        cid, src, tgt, active, protect, silent, pin, delete_src, delay = conn
        text = (
            b(f"♻️ Connection #{cid}") + "\n\n"
            f"<b>Source:</b> {code(str(src))}\n"
            f"<b>Target:</b> {code(str(tgt))}\n"
            f"<b>Active:</b> {'✅' if active else '❌'}\n"
            f"<b>Protect Content:</b> {'✅' if protect else '❌'}\n"
            f"<b>Silent:</b> {'✅' if silent else '❌'}\n"
            f"<b>Pin:</b> {'✅' if pin else '❌'}\n"
            f"<b>Delete Source:</b> {'✅' if delete_src else '❌'}\n"
            f"<b>Delay:</b> {code(str(delay) + 's' if delay else '0s')}"
        )
        keyboard = [
            [bold_button("Delete", callback_data=f"af_conn_del_{cid}"),
             _back_btn("af_list_connections")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_del_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_del_"):])
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM auto_forward_connections WHERE id = %s", (conn_id,))
        except Exception:
            pass
        await safe_answer(query, f"Connection #{conn_id} deleted.")
        await button_handler(update, context, "af_list_connections")
        return

    # ── Auto manga update ──────────────────────────────────────────────────────
    if data == "admin_autoupdate":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoupdate_menu
        await _show_autoupdate_menu(context, chat_id)
        return

    if data == "au_add_manga":
        if not is_admin:
            return
        user_states[uid] = AU_ADD_MANGA_TITLE
        await safe_edit_text(
            query, b("📚 Track New Manga") + "\n\n" + bq(b("Send the manga title to search on MangaDex:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    if data.startswith("au_stop_"):
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        manga_id = data[len("au_stop_"):]
        MangaTracker.remove_tracking(manga_id)
        await safe_answer(query, "Tracking stopped.")
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_list_manga":
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        text = MangaTracker.get_tracked_for_admin()
        rows = MangaTracker.get_all_tracked()
        keyboard = []
        for rec in rows:
            rec_id, manga_id, title, _, _, _, _ = rec
            keyboard.append([bold_button(f"🗑 Stop: {e(title[:20])}", callback_data=f"au_stop_{manga_id}")])
        keyboard.append([_back_btn("admin_autoupdate")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "au_remove_manga":
        if not is_admin:
            return
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_stats":
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        rows = MangaTracker.get_all_tracked()
        text_au = (
            b(" Manga Tracking Stats") + "\n\n"
            f"<b>Total tracked:</b> {code(str(len(rows)))}"
        )
        await safe_edit_text(
            query, text_au,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoupdate")]]),
        )
        return

    if data.startswith("mdex_track_"):
        if not is_admin:
            await safe_answer(query, "Only admin can set up tracking.")
            return
        from api.mangadex import MangaDexClient
        manga_id = data[len("mdex_track_"):]
        manga = MangaDexClient.get_manga(manga_id)
        if not manga:
            await safe_answer(query, "Manga not found.")
            return
        attrs = manga.get("attributes", {}) or {}
        titles = attrs.get("title", {}) or {}
        title = titles.get("en") or next(iter(titles.values()), "Unknown")
        context.user_data["au_manga_id"] = manga_id
        context.user_data["au_manga_title"] = title
        keyboard = [
            [bold_button("Full Manga", callback_data="au_mode_full"),
             bold_button("Latest Chapters", callback_data="au_mode_latest")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + "\n\n" + bq(b("Choose delivery mode:\n\nFull Manga — all chapters\nLatest Chapters — only new ones")),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("mdex_chapter_"):
        ch_id_mc = data[len("mdex_chapter_"):]
        try:
            await query.delete_message()
        except Exception:
            pass
        try:
            from api.mangadex import MangaDexClient
            pages = MangaDexClient.get_chapter_pages(ch_id_mc)
        except Exception:
            pages = None
        text_mc = b("📖 Chapter") + "\n\n"
        if pages:
            base_url_mc, ch_hash_mc, filenames_mc = pages
            text_mc += (
                f"<b>Total Pages:</b> {code(str(len(filenames_mc)))}\n"
                f"<b>Chapter ID:</b> {code(ch_id_mc)}\n\n"
                + bq(b("Read this chapter online at MangaDex for the best experience."))
            )
        else:
            text_mc += b("Could not load chapter page info.")
        await safe_send_message(
            context.bot, chat_id, text_mc,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Read Now", url=f"https://mangadex.org/chapter/{ch_id_mc}")
            ]]),
        )
        return

    if data in ("au_mode_full", "au_mode_latest"):
        if not is_admin:
            return
        mode = "full" if data == "au_mode_full" else "latest"
        context.user_data["au_manga_mode"] = mode
        title = context.user_data.get("au_manga_title", "Unknown")
        keyboard = [
            [bold_button("5 min", callback_data="au_interval_5"),
             bold_button("10 min", callback_data="au_interval_10")],
            [bold_button("Random (5-10 min)", callback_data="au_interval_random"),
             bold_button("Custom", callback_data="au_interval_custom")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()}\n\n" + bq(b("Choose check interval:")),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("au_interval_"):
        if not is_admin:
            return
        interval_key = data[len("au_interval_"):]
        if interval_key == "custom":
            from core.state_machine import AU_CUSTOM_INTERVAL
            user_states[uid] = AU_CUSTOM_INTERVAL
            await safe_edit_text(
                query, b("📚 Custom Interval") + "\n\n" + bq(b("Send interval in minutes:")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
            )
            return
        interval_map = {"5": 5, "10": 10, "random": -1}
        interval_minutes = interval_map.get(interval_key, 10)
        context.user_data["au_manga_interval"] = interval_minutes
        title = context.user_data.get("au_manga_title", "Unknown")
        mode = context.user_data.get("au_manga_mode", "latest")
        user_states[uid] = AU_ADD_MANGA_TARGET
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()} | <b>Interval:</b> {interval_minutes if interval_minutes > 0 else 'Random 5–10'} min\n\n"
            + bq(b("Send the target channel @username, numeric ID, or forward a post:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    # ── Search results ─────────────────────────────────────────────────────────
    if data.startswith("search_result_"):
        rest = data[len("search_result_"):]
        for cat_key in ("mangadex", "anime", "manga", "movie", "tvshow"):
            if rest.startswith(f"{cat_key}_"):
                raw_id = rest[len(f"{cat_key}_"):]
                try:
                    await query.delete_message()
                except Exception:
                    pass
                if cat_key == "mangadex":
                    from api.mangadex import MangaDexClient
                    manga = MangaDexClient.get_manga(raw_id)
                    if manga:
                        caption_text, cover_url = MangaDexClient.format_manga_info(manga)
                        markup = InlineKeyboardMarkup([[
                            InlineKeyboardButton("📖 Read on MangaDex", url=f"https://mangadex.org/title/{raw_id}"),
                        ], [bold_button("Track This Manga", callback_data=f"mdex_track_{raw_id}")]])
                        if cover_url:
                            await safe_send_photo(context.bot, chat_id, cover_url, caption=caption_text, reply_markup=markup)
                        else:
                            await safe_send_message(context.bot, chat_id, caption_text, reply_markup=markup)
                    else:
                        await safe_send_message(context.bot, chat_id, b("❌ Manga not found."))
                else:
                    try:
                        mid = int(raw_id)
                    except ValueError:
                        mid = None
                    from handlers.post_gen import generate_and_send_post
                    await generate_and_send_post(context, chat_id, cat_key, media_id=mid)
                return

    # ── ENV variables panel ────────────────────────────────────────────────────
    if data == "admin_env_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass

        from handlers.admin_panel import show_env_panel
        await show_env_panel(context, chat_id)
        return

    # ── Set Main Channel (for send-to-main-channel feature) ───────────────────
    if data == "admin_set_main_channel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_MAIN_CHANNEL_ID"
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📢 set main channel")) + "\n\n"
            + bq(small_caps(
                "forward any message from the channel, or send the channel @username / numeric ID.\n\n"
                "this channel will receive posters when 'send to main channel' is tapped."
            )),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    # ── pe_send_main: poster_engine send-to-main-channel callback ─────────────
    if data.startswith("pe_send_main:"):
        if not is_admin:
            return

        import json as _json
        from database_dual import get_setting

        # Get stored poster data
        try:
            raw = get_setting(f"last_poster_{uid}", "")
            pdata = _json.loads(raw) if raw else {}
        except Exception:
            pdata = {}

        src_chat = pdata.get("chat_id")
        src_msg  = pdata.get("msg_id")
        caption  = pdata.get("caption", "")

        if not src_chat or not src_msg:
            await safe_answer(query, "❌ Poster not found — regenerate and try again", show_alert=True)
            return

        # Check if default main channel is configured
        main_ch_raw = get_setting("main_channel_id", "") or ""
        main_ch_title = get_setting("main_channel_title", "") or "Default Channel"

        # Build keyboard: "Send to default" (if set) + "Enter ID/username" + cancel
        kb_rows = []
        if main_ch_raw.strip():
            kb_rows.append([InlineKeyboardButton(
                f"📢 Send to: {main_ch_title}",
                callback_data=f"pe_do_send:{src_chat}:{src_msg}:{main_ch_raw.strip()}"
            )])
        kb_rows.append([InlineKeyboardButton(
            "✏️ Enter Channel ID/Username",
            callback_data=f"pe_send_ask_id:{src_chat}:{src_msg}"
        )])
        kb_rows.append([InlineKeyboardButton("✖ Cancel", callback_data="close_message")])

        await _smart_edit(
            b("📤 Send Poster to Channel") + "\n\n"
            + bq(
                ("Default: <code>" + main_ch_raw + "</code>\n\n" if main_ch_raw else "")
                + small_caps("choose where to send the poster:")
            ),
            InlineKeyboardMarkup(kb_rows),
        )
        return

    if data.startswith("pe_send_ask_id:"):
        if not is_admin:
            return
        parts = data.split(":", 2)
        src_chat = parts[1] if len(parts) > 1 else ""
        src_msg  = parts[2] if len(parts) > 2 else ""
        user_states[uid] = f"AWAITING_SEND_TO_CHANNEL:{src_chat}:{src_msg}"
        await _smart_edit(
            b("✏️ Send Poster to Channel") + "\n\n"
            + bq(small_caps("send the channel @username or numeric ID:\nexample: @BeatAnime or -1001234567890")),
            InlineKeyboardMarkup([[InlineKeyboardButton("✖ Cancel", callback_data="close_message")]]),
        )
        return

    if data.startswith("pe_do_send:"):
        if not is_admin:
            return
        parts = data.split(":", 3)
        src_chat_s = parts[1] if len(parts) > 1 else ""
        src_msg_s  = parts[2] if len(parts) > 2 else ""
        dest_ch    = parts[3] if len(parts) > 3 else ""
        try:
            src_chat_i = int(src_chat_s)
            src_msg_i  = int(src_msg_s)
            try:
                dest_ch_i = int(dest_ch)
            except ValueError:
                dest_ch_i = dest_ch  # username
            import json as _json
            from database_dual import get_setting
            raw  = get_setting(f"last_poster_{uid}", "")
            pdat = _json.loads(raw) if raw else {}
            cap  = pdat.get("caption", "")
            await context.bot.copy_message(
                chat_id=dest_ch_i,
                from_chat_id=src_chat_i,
                message_id=src_msg_i,
                caption=cap,
                parse_mode="HTML",
            )
            await safe_answer(query, "✅ Sent to channel!")
            try:
                await query.message.delete()
            except Exception:
                pass
        except Exception as exc:
            await safe_answer(query, f"❌ Failed: {str(exc)[:80]}", show_alert=True)
        return



    if data.startswith("env_edit_"):
        if not is_admin:
            return
        env_key = data[len("env_edit_"):]
        from database_dual import get_setting
        import os as _os
        current = get_setting(f"env_{env_key}", _os.getenv(env_key, "")) or ""
        user_states[uid] = f"AWAITING_ENV_{env_key}"
        await safe_edit_text(
            query, b(f"SET {e(env_key)}") + "\n\n"
            + bq(f"<b>Current:</b> {code(e(current[:60] or '(empty)'))}\\n\nSend new value or <code>reset</code> to use .env default:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_env_panel"), _close_btn()]]),
        )
        return

    # ── Panel image controls ───────────────────────────────────────────────────
    if data == "panel_img_add_urls":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_PANEL_IMG_URLS"
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.panel_image import get_panel_db_images
        total_imgs = len(get_panel_db_images())
        await safe_send_message(
            context.bot, chat_id,
            b("🖼 Add Panel Images") + "\n\n"
            + bq(
                "<b>3 ways to add panel images:</b>\n\n"
                "1️⃣ <b>Send a photo</b> — bot saves to panel DB channel\n\n"
                "2️⃣ <b>Send file_ids</b> — comma or newline separated\n\n"
                "3️⃣ <b>Send URLs</b> — direct https:// image links\n\n"
                f"<b>Currently stored: {total_imgs} image(s)</b>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖼 View Current Images", callback_data="panel_img_manage")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data == "panel_img_toggle_source":
        if not is_admin:
            return
        try:
            from database_dual import get_setting, set_setting
            current = get_setting("panel_image_source", "url") or "url"
            new_src = "api" if current == "url" else "url"
            set_setting("panel_image_source", new_src)
            label = ("🌐 API-first (waifu.im → anilist → nekos)" if new_src == "api"
                     else "🔗 URL-first (your custom URLs / PANEL_PICS env)")
            await safe_answer(query, f"✅ Panel source: {label[:40]}", show_alert=True)
            try:
                from panel_image import clear_image_cache
                clear_image_cache()
            except Exception:
                pass
        except Exception as exc:
            logger.error(f"panel_img_toggle: {exc}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_clear_urls":
        if not is_admin:
            return
        try:
            from database_dual import set_setting
            set_setting("panel_image_urls", "[]")
            try:
                from panel_image import clear_image_cache
                clear_image_cache()
            except Exception:
                pass
            await safe_answer(query, "✅ Custom URL list cleared. Using PANEL_PICS env or APIs.", show_alert=True)
        except Exception as exc:
            await safe_answer(query, f"❌ {str(exc)[:60]}", show_alert=True)
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_manage":
        if not is_admin:
            return
        from handlers.misc_cmds import _show_panel_img_list
        await _show_panel_img_list(context.bot, chat_id, query=query, page=0)
        return

    if data.startswith("panel_img_view_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from handlers.misc_cmds import _show_panel_img_list
        await _show_panel_img_list(context.bot, chat_id, query=query, page=page)
        return

    if data.startswith("panel_img_del_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from core.panel_image import get_panel_db_images, save_panel_db_images
        from core.config import PANEL_DB_CHANNEL
        items = get_panel_db_images()
        if 0 <= page < len(items):
            removed = items.pop(page)
            for i, it in enumerate(items):
                it["index"] = i + 1
            save_panel_db_images(items)
            if _PANEL_IMAGE_AVAILABLE:
                try:
                    from panel_image import clear_tg_fileid
                    clear_tg_fileid()
                except Exception:
                    pass
            if PANEL_DB_CHANNEL and removed.get("msg_id"):
                try:
                    await context.bot.delete_message(PANEL_DB_CHANNEL, removed["msg_id"])
                except Exception:
                    pass
            new_page = max(0, page - 1) if items else 0
            from handlers.misc_cmds import _show_panel_img_list
            await _show_panel_img_list(context.bot, chat_id, query=None, page=new_page)
        else:
            await safe_answer(query, "❌ Image not found", show_alert=True)
        return

    if data == "panel_img_refresh_cache":
        if not is_admin:
            return
        try:
            from panel_image import clear_image_cache
            n = clear_image_cache()
            await safe_answer(query, f"✅ Cache cleared ({n} entries).", show_alert=False)
        except Exception:
            await safe_answer(query, "✅ Cache cleared", show_alert=False)
        await button_handler(update, context, "admin_settings")
        return

    # ── Button style ───────────────────────────────────────────────────────────
    if data == "admin_btn_style":
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import BUTTON_STYLE
        current_style = get_setting("button_style", BUTTON_STYLE) or BUTTON_STYLE
        await safe_edit_text(
            query, b("BUTTON STYLE") + "\n\n"
            + bq(
                f"<b>Current:</b> {current_style}\n\n"
                "<b>Math Bold:</b> 𝗦𝗧𝗔𝗧𝗦  𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧\n"
                "<b>Small Caps:</b> ꜱᴛᴀᴛꜱ  ʙʀᴏᴀᴅᴄᴀꜱᴛ"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'mathbold' else ''}𝗠𝗔𝗧𝗛 𝗕𝗢𝗟𝗗",
                    callback_data="btn_style_set_mathbold"),
                 InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'smallcaps' else ''}ꜱᴍᴀʟʟ ᴄᴀᴘꜱ",
                    callback_data="btn_style_set_smallcaps")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data.startswith("btn_style_set_"):
        if not is_admin:
            return
        style = data[len("btn_style_set_"):]
        if style in ("mathbold", "smallcaps"):
            from database_dual import set_setting
            from core.buttons import refresh_btn_style_cache
            set_setting("button_style", style)
            refresh_btn_style_cache()
            await safe_answer(query, f"✔️ Button style set: {style}")
            await button_handler(update, context, "admin_btn_style")
        return

    # ── DB cleanup ─────────────────────────────────────────────────────────────
    if data == "dbcleanup_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query, b(small_caps("💾 database cleanup")) + "\n\n"
            + bq(small_caps("removes expired links, old sessions, and stale cache entries.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("✅ confirm cleanup"), callback_data="dbcleanup_run"),
                _back_btn("admin_back"),
            ]]),
        )
        return

    if data == "dbcleanup_run":
        if not is_admin:
            return
        try:
            from database_dual import cleanup_expired_links
            removed = cleanup_expired_links()
            await safe_edit_text(
                query, b(small_caps("✅ cleanup done!")) + "\n" + bq(small_caps(f"removed {removed} expired entries.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back"), _close_btn()]]),
            )
        except Exception as exc:
            await safe_edit_text(query, b(small_caps(f"❌ error: {e(str(exc)[:100])}")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]))
        return

    # ── User features panel ────────────────────────────────────────────────────
    # ── User features help cards (4×2 grid → tap = feature card) ─────────────
    if data.startswith("uf_help:"):
        feature = data[len("uf_help:"):]
        HELP_CARDS = {
            "anime": (
                "🎌 <b>Anime Poster</b>\n\n"
                "<code>/anime Demon Slayer</code> — generate anime poster + info\n"
                "<code>/airing Jujutsu Kaisen</code> — next episode countdown\n"
                "<code>/character Tanjiro</code> — character details\n\n"
                "<i>Searches AniList for accurate info.</i>"
            ),
            "manga": (
                "📚 <b>Manga Poster</b>\n\n"
                "<code>/manga One Piece</code> — generate manga poster\n"
                "<code>/manga Berserk</code> — poster + info from AniList\n\n"
                "<i>Also searches MangaDex for cover art.</i>"
            ),
            "movie": (
                "🎬 <b>Movie Poster</b>\n\n"
                "<code>/movie Spirited Away</code> — TMDB movie poster\n"
                "<code>/tvshow Attack on Titan</code> — TV show poster\n"
                "<code>/search Naruto</code> — search all sources at once\n\n"
                "<i>Requires TMDB API to be configured.</i>"
            ),
            "character": (
                "👤 <b>Character Info</b>\n\n"
                "<code>/character Goku</code> — character details + image\n"
                "<code>/character Mikasa Ackerman</code> — full info\n\n"
                "<i>Data from AniList character database.</i>"
            ),
            "reactions": (
                "🤗 <b>Reaction GIFs</b>\n\n"
                "<code>/hug @user</code> — send a hug GIF\n"
                "<code>/slap @user</code> — slap someone\n"
                "<code>/kiss @user</code> — send a kiss\n"
                "<code>/pat @user</code> — pat someone\n"
                "<code>/punch @user</code> — punch!\n"
                "<code>/couple</code> — couple of the day GIF\n\n"
                "<i>Reply to a message or mention @user.</i>"
            ),
            "chatbot": (
                "💬 <b>AI Chatbot</b>\n\n"
                "Just <b>mention the bot</b> or <b>reply</b> to its message in a group.\n"
                "In DM — just type anything!\n\n"
                "<i>Powered by Gemini + Groq. Remembers conversation context.</i>"
            ),
            "notes": (
                "📝 <b>Notes System</b>\n\n"
                "<code>/save notename content</code> — save a note\n"
                "<code>/get notename</code> — retrieve a note\n"
                "<code>/notes</code> — list all saved notes\n"
                "<code>#notename</code> — trigger note by hashtag\n\n"
                "<i>Notes are saved per group.</i>"
            ),
            "group": (
                "⚖️ <b>Group Management</b>\n\n"
                "<code>/warn @user reason</code> — warn a user\n"
                "<code>/warns @user</code> — check warnings\n"
                "<code>/unwarn @user</code> — remove a warning\n"
                "<code>/rules</code> — show group rules\n"
                "<code>/afk reason</code> — set AFK status\n\n"
                "<i>Most mod commands require admin rights.</i>"
            ),
        }
        card_text = HELP_CARDS.get(feature, "<b>Feature not found.</b>")
        back_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="user_features_panel"),
            InlineKeyboardButton("✖ Close", callback_data="close_message"),
        ]])
        await _smart_edit(card_text, back_kb)
        return

    if data == "user_features_panel":
        from handlers.user_features import send_user_features_panel
        await send_user_features_panel(update, context, query=query, chat_id=chat_id)
        return

    if data.startswith("user_features_"):
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from handlers.user_features import send_user_features_panel
        await send_user_features_panel(update, context, query, chat_id, page)
        return

    if data.startswith("feat_"):
        if not is_admin:
            return
        feat_map = {
            "feat_couple":       ("/couple", "Tag two users as a couple. Usage: /couple @user1 @user2"),
            "feat_slap":         ("/slap", "Slap someone! Reply to a message with /slap"),
            "feat_hug":          ("/hug", "Hug someone! Reply to a message with /hug"),
            "feat_kiss":         ("/kiss", "Kiss someone! Reply to a message with /kiss"),
            "feat_pat":          ("/pat", "Pat someone! Reply to a message with /pat"),
            "feat_inline_search":("@Bot query", "Inline anime search — type @YourBot in any chat then anime name."),
            "feat_reactions":    ("/react", "Reaction GIFs. Reply to a message with /slap /hug /pat etc."),
            "feat_chatbot":      ("/chatbot on|off", "Toggle AI chatbot mode in a group."),
            "feat_truth_dare":   ("/truth or /dare", "Play Truth or Dare in a group!"),
            "feat_notes":        ("/save notename text", "Save group notes. Retrieve with #notename"),
            "feat_warns":        ("/warn @user", "Warn users. Also: /unwarn /warns /resetwarns"),
            "feat_muting":       ("/mute @user", "Mute users. Also: /unmute /tmute"),
            "feat_bans":         ("/ban @user", "Ban users. Also: /unban /tban /sban"),
            "feat_rules":        ("/setrules | /rules", "Set and show group rules."),
            "feat_airing":       ("/airing Demon Slayer", "Check next episode airing time from AniList."),
            "feat_character":    ("/character Tanjiro", "Get anime character info from AniList."),
            "feat_anime_info":   ("/anime Naruto", "Get landscape poster + full anime info."),
            "feat_afk":          ("/afk reason", "Set AFK status. Bot auto-replies when tagged."),
        }
        if data == "feat_chatbot":
            from database_dual import get_setting as _gs_feat, set_setting as _ss_feat
            chat_key = f"chatbot_{chat_id}"
            current_chatbot = (_gs_feat(chat_key, "true") or "true").lower()
            new_val_chatbot = "false" if current_chatbot == "true" else "true"
            _ss_feat(chat_key, new_val_chatbot)
            status_chatbot = small_caps("enabled ✅") if new_val_chatbot == "true" else small_caps("disabled 🔕")
            try:
                await query.answer(small_caps(f"chatbot {status_chatbot}"), show_alert=True)
            except Exception:
                pass
            return
        info = feat_map.get(data, (data.replace("feat_", "/"), "Feature command."))
        cmd_feat, desc_feat = info
        try:
            await query.answer(f"{cmd_feat} — {desc_feat[:100]}", show_alert=True)
        except Exception:
            pass
        return

    if data == "about_bot":
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.config import BOT_NAME
        text = (b(f" About {e(BOT_NAME)}") + "\n\n"
            + bq(b("🤖 Powered by @Beat_Anime_Ocean\n\n") + b("Features:\n") + "• Force-Sub channels"))
        await safe_send_message(
            context.bot, chat_id, text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎌 Anime Channel", url=PUBLIC_ANIME_CHANNEL_URL)],
                [_back_btn("user_back")],
            ]),
        )
        return

    if data == "user_back":
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.start import start
        await start(update, context)
        return

    if data == "user_help":
        from handlers.help import help_command
        await help_command(update, context)
        return

    # ── Channel welcome ────────────────────────────────────────────────────────
    if data == "admin_channel_welcome":
        if not is_admin:
            return
        from handlers.channels import show_channel_welcome_panel
        await show_channel_welcome_panel(context, chat_id, query)
        return

    if data == "cw_add":
        if not is_admin:
            return
        user_states[uid] = "CW_WAITING_CHANNEL_ID"
        await safe_edit_text(
            query, b("📣 add channel welcome") + "\n\n"
            + bq(b(small_caps("send the channel id, @username, or forward a post:"))),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_list":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("no channels configured yet."))
            return
        text = b("📋 " + small_caps("configured channel welcomes:")) + "\n\n"
        for ch_id_l, enabled_l, wtext_l in channels:
            icon = "🟢" if enabled_l else "🔴"
            text += f"{icon} <code>{ch_id_l}</code>\n"
            if wtext_l:
                text += f"   {e((wtext_l)[:60])}…\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_remove_menu":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("nothing to remove."))
            return
        btns = [[InlineKeyboardButton(f"🗑 {ch_id_r}", callback_data=f"cw_del_{ch_id_r}")]
                for ch_id_r, _, _ in channels[:10]]
        btns.append([_back_btn("admin_channel_welcome"), _close_btn()])
        await safe_edit_text(
            query, b(small_caps("select channel to remove:")),
            reply_markup=InlineKeyboardMarkup(btns),
        )
        return

    if data.startswith("cw_edit_"):
        if not is_admin:
            return
        ch_id_ce = int(data[len("cw_edit_"):])
        try:
            from database_dual import get_channel_welcome
            s = get_channel_welcome(ch_id_ce) or {}
        except Exception:
            s = {}
        wtext_ce   = s.get("welcome_text", "")
        img_fid_ce = s.get("image_file_id", "")
        img_url_ce = s.get("image_url", "")
        btns_json  = s.get("buttons", [])
        enabled_ce = s.get("enabled", True)
        text_ce = (
            b(small_caps(f"edit channel welcome: {ch_id_ce}")) + "\n\n"
            + bq(
                f"<b>{small_caps('enabled')}:</b> {'🟢 yes' if enabled_ce else '🔴 no'}\n"
                f"<b>{small_caps('text')}:</b> {e((wtext_ce)[:60]) if wtext_ce else small_caps('not set')}\n"
                f"<b>{small_caps('image')}:</b> {'✅ set' if img_fid_ce or img_url_ce else small_caps('not set')}\n"
                f"<b>{small_caps('buttons')}:</b> {len(btns_json)} {small_caps('configured')}"
            )
        )
        context.user_data["cw_editing_channel"] = ch_id_ce
        edit_kb = [
            [InlineKeyboardButton(small_caps("✏️ set text"),    callback_data=f"cw_settext_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("🖼 set image"),   callback_data=f"cw_setimg_{ch_id_ce}")],
            [InlineKeyboardButton(small_caps("🔘 set buttons"), callback_data=f"cw_setbtns_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("⚡ toggle on/off"), callback_data=f"cw_toggle_{ch_id_ce}")],
            [InlineKeyboardButton(small_caps("👁 preview"),     callback_data=f"cw_preview_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("🗑 remove"),      callback_data=f"cw_del_{ch_id_ce}")],
            [_back_btn("admin_channel_welcome"), _close_btn()],
        ]
        await safe_edit_text(query, text_ce, reply_markup=InlineKeyboardMarkup(edit_kb))
        return

    if data.startswith("cw_settext_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_settext_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_TEXT
        await safe_edit_text(
            query, b(small_caps("send the welcome text:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setbtns_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setbtns_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_BUTTONS
        await safe_edit_text(
            query, b(small_caps("send button config (one per line: Label - https://url):")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setimg_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setimg_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = "CW_AWAITING_IMAGE"
        await safe_edit_text(
            query, b(small_caps("send welcome image:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_preview_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_preview_"):])
        from handlers.channels import send_channel_welcome
        asyncio.create_task(send_channel_welcome(context.bot, chat_id, ch_id))
        await safe_answer(query, small_caps("preview sent to you in dm."))
        return

    if data.startswith("cw_del_"):
        if not is_admin:
            return
        try:
            from database_dual import delete_channel_welcome
            ch_id = int(data[len("cw_del_"):])
            delete_channel_welcome(ch_id)
            await safe_answer(query, small_caps(f"removed channel {ch_id}"))
            from handlers.channels import show_channel_welcome_panel
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    if data.startswith("cw_toggle_"):
        if not is_admin:
            return
        try:
            from database_dual import get_channel_welcome, set_channel_welcome
            ch_id = int(data[len("cw_toggle_"):])
            s = get_channel_welcome(ch_id)
            new_state = not (s.get("enabled", True) if s else True)
            set_channel_welcome(ch_id, enabled=new_state)
            await safe_answer(query, small_caps(f"welcome {'enabled' if new_state else 'disabled'}"))
            from handlers.channels import show_channel_welcome_panel
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    # ── Poster commands from panel ─────────────────────────────────────────────
    if data.startswith("poster_cmd_"):
        if not is_admin:
            return
        tmpl = data.replace("poster_cmd_", "")
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            f"<b>🖼 Poster Command:</b> <code>/{tmpl}</code>\n\n"
            f"<b>Usage:</b> /{tmpl} &lt;title&gt;\n"
            f"<b>Example:</b> <code>/{tmpl} Demon Slayer</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "admin_cmd_list":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.help import cmd_command
        await cmd_command(update, context)
        return

    # ── Anime module callbacks ─────────────────────────────────────────────────
    if data.startswith(("anpick_", "lang_", "size_", "anthmb_")):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc:
            logger.debug(f"anime callback error: {exc}")
        return

    # ── Filter settings ────────────────────────────────────────────────────────
    if data == "admin_filter_settings":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.filters_system import filters_config
        dm_on  = filters_config["global"].get("dm", True)
        grp_on = filters_config["global"].get("group", True)

        # Build channel+anime list from DB
        ch_lines = ""
        try:
            from database_dual import get_all_force_sub_channels, get_all_anime_channel_links
            channels = get_all_force_sub_channels() or []
            links    = get_all_anime_channel_links() or []
            # Map channel_id → anime titles
            ch_anime: dict = {}
            for row in links:
                # row = (id, anime_title, channel_id, channel_title, link_id, created_at)
                an_title = row[1] if len(row) > 1 else ""
                cid      = row[2] if len(row) > 2 else ""
                if an_title and cid:
                    ch_anime.setdefault(str(cid), []).append(an_title.title())
            for ch in channels:
                cid_v  = ch[0] if isinstance(ch, (list, tuple)) else ch.get("channel_id", "")
                cname  = ch[1] if isinstance(ch, (list, tuple)) else ch.get("channel_title", "")
                animes = ch_anime.get(str(cid_v), [])
                an_str = ", ".join(animes[:3]) if animes else small_caps("no anime linked")
                ch_lines += f"• <b>{e(str(cname))}</b>: <i>{e(an_str)}</i>\n"
        except Exception:
            ch_lines = bq(small_caps("could not load channel list"))

        text = (
            b(small_caps("🔧 filter settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('DM Filter')}:</b> {'✅ ON' if dm_on else '❌ OFF'}\n"
                f"<b>{small_caps('Group Filter')}:</b> {'✅ ON' if grp_on else '❌ OFF'}"
            )
            + (f"\n\n<b>{small_caps('📢 channels & anime:')}</b>\n" + ch_lines if ch_lines else "")
        )
        keyboard = [
            [bold_button(small_caps("toggle dm filter"),    callback_data="filter_toggle_dm"),
             bold_button(small_caps("toggle group filter"), callback_data="filter_toggle_group")],
            [bold_button(small_caps("📢 manage channels"),  callback_data="manage_force_sub")],
            [bold_button(small_caps("🎌 channel anime links"), callback_data="admin_anime_links")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "admin_anime_links":
        if not is_admin:
            return
        try:
            from database_dual import get_all_links
            raw = get_all_links(limit=100, offset=0)
            seen = set()
            rows_al = []
            for row in (raw or []):
                t = (row[2] or "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    rows_al.append(row)
        except Exception:
            rows_al = []
        text_al = b(small_caps(f"🎌 filter keywords from generated links ({len(rows_al)})")) + "\n\n"
        if rows_al:
            for row in rows_al[:20]:
                ch_id_al   = row[1]
                ch_title_al = row[2] or ch_id_al
                text_al += f"• <b>{e(ch_title_al)}</b> → <code>{e(str(ch_id_al))}</code>\n"
        else:
            text_al += bq(small_caps(
                "no links yet.\n\n"
                "use gen link in the channels panel to create one.\n"
                "the link title automatically becomes a filter keyword."
            ))
        text_al += (
            "\n\n" + bq(
                b(small_caps("how it works:")) + "\n"
                + small_caps("generate a channel link → the title becomes a filter keyword. "
                             "when any user types that title in a group, they get a poster + join button.")
            )
        )
        await safe_send_message(
            context.bot, chat_id, text_al,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    if data.startswith("del_acl_"):
        await safe_answer(query, small_caps("use /removechannel or manage links from the channels panel."), show_alert=True)
        return

    if data == "filter_toggle_dm":
        if not is_admin:
            return
        from core.filters_system import filters_config
        filters_config["global"]["dm"] = not filters_config["global"].get("dm", True)
        await safe_answer(query, f"DM filter: {'ON' if filters_config['global']['dm'] else 'OFF'}")
        await button_handler(update, context, "admin_filter_settings")
        return

    if data == "filter_toggle_group":
        if not is_admin:
            return
        from core.filters_system import filters_config
        filters_config["global"]["group"] = not filters_config["global"].get("group", True)
        await safe_answer(query, f"Group filter: {'ON' if filters_config['global']['group'] else 'OFF'}")
        await button_handler(update, context, "admin_filter_settings")
        return

    # ── Admin clear image cache ────────────────────────────────────────────────
    if data == "admin_clear_img_cache":
        if not is_admin:
            return
        try:
            from panel_image import clear_image_cache
            count = clear_image_cache()
            await safe_answer(query, f"♻️ Cleared {count} cached panel images")
        except Exception:
            await safe_answer(query, "♻️ Cache cleared")
        return

    # ── Fsub forward source ────────────────────────────────────────────────────
    if data == "fsub_fwd_source":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.admin_panel import show_fwd_source_panel
        await show_fwd_source_panel(context, chat_id)
        return

    if data == "fwd_set_chat":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_FWD_CHAT"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(context.bot, chat_id, b(" Set Forward Source Chat") + "\n\n"
            + bq("Send the channel/group ID or @username."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]))
        return

    if data == "fwd_set_msgid":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_FWD_MSGID"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(context.bot, chat_id, b(" Set Forward Message ID") + "\n\n"
            + bq("Send the message ID (number)."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]))
        return

    if data == "fwd_test":
        if not is_admin:
            return
        from database_dual import get_setting
        fwd_chat = get_setting("fwd_source_chat", "")
        fwd_msg_id = get_setting("fwd_source_msg_id", "")
        fwd_with_tag = get_setting("fwd_with_tag", "true") == "true"
        if not fwd_chat or not fwd_msg_id:
            await safe_answer(query, "❌ Set source chat and message ID first!", show_alert=True)
            return
        try:
            msg_id_int = int(fwd_msg_id)
            if fwd_with_tag:
                await context.bot.forward_message(chat_id=chat_id, from_chat_id=fwd_chat, message_id=msg_id_int)
            else:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=fwd_chat, message_id=msg_id_int)
            await safe_answer(query, "✅ Test forward sent!")
        except Exception as _fe:
            await safe_answer(query, f"❌ Failed: {str(_fe)[:80]}", show_alert=True)
        return

    if data == "fwd_toggle_tag":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("fwd_with_tag", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("fwd_with_tag", new_val)
        await safe_answer(query, f"📨 Forward Tag: {'ON' if new_val == 'true' else 'OFF'}")
        return

    if data == "fwd_toggle_private":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("fwd_private_channel", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("fwd_private_channel", new_val)
        label = "ON (private channels enabled)" if new_val == "true" else "OFF"
        try:
            await query.answer(f"🔒 Private Channel: {label}", show_alert=True)
        except Exception:
            pass
        return

    # ── fp_set_join_btn_* ──────────────────────────────────────────────────────
    if data.startswith("fp_set_join_btn_"):
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import JOIN_BTN_TEXT
        current = get_setting("env_JOIN_BTN_TEXT", "") or JOIN_BTN_TEXT
        user_states[uid] = "AWAITING_JOIN_BTN_TEXT"
        await safe_edit_text(
            query, b(small_caps("✏️ set join button text")) + "\n\n"
            + bq(b(small_caps("current: ")) + f"<code>{e(current)}</code>\n\n" + small_caps("send new button text:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return


    # ── Module info buttons (admin panel page 5) ───────────────────────────────
    if data.startswith("mod_"):
        if not is_admin:
            return
        # Map callback → (display name, commands list, description)
        _MOD_INFO = {
            "mod_admin":       ("Admins",          ["/pinned", "/invitelink", "/setgtitle", "/setdesc", "/setgpic"],
                                "Group admin tools — pin messages, manage group title, description, and profile picture."),
            "mod_antiflood":   ("Anti-Flood",       ["/setflood", "/flood"],
                                "Auto-kick/mute/ban users who send too many messages too fast."),
            "mod_approve":     ("Approve",          ["/approve", "/unapprove", "/approved", "/unapproveall"],
                                "Approve trusted users so they bypass blacklists and other restrictions."),
            "mod_blacklist":   ("Blacklist",        ["/addblacklist", "/unblacklist", "/blacklist"],
                                "Auto-delete messages containing banned words or phrases."),
            "mod_blsticker":   ("BL Stickers",      ["/blsticker", "/unblsticker", "/blstickermode"],
                                "Blacklist specific stickers from being sent in the group."),
            "mod_chatbot":     ("Chatbot",          ["/chatbot"],
                                "AI chatbot — responds when tagged or replied to. Toggle on/off per group."),
            "mod_cleaner":     ("Cleaner",          ["/cleanblue on/off"],
                                "Auto-delete blue text (service messages) like join/leave/pin notifications."),
            "mod_connection":  ("Connection",       ["/connect", "/disconnect", "/connection"],
                                "Connect to a group from PM to manage it without being in the chat."),
            "mod_currency":    ("Currency",         ["/cash <amount> <from> <to>"],
                                "Live currency conversion. Example: /cash 100 USD INR"),
            "mod_custfilters": ("Filters",          ["/filter <word> <reply>", "/stop <word>", "/filters"],
                                "Custom keyword auto-replies. When someone says a word, bot responds automatically."),
            "mod_globalbans":  ("Anti-Spam",        ["/gban <user>", "/ungban", "/gbanlist"],
                                "Global ban system — banned users are blocked across all groups the bot manages."),
            "mod_imdb":        ("IMDb",             ["/imdb <title>"],
                                "Search for movie/show info from IMDb with ratings, plot, and cast."),
            "mod_locks":       ("Locks",            ["/lock <type>", "/unlock <type>", "/locktypes"],
                                "Lock specific message types (media, stickers, links, polls etc.) in groups."),
            "mod_logchannel":  ("Log Channel",      ["/setlog <channel>", "/unsetlog", "/logchannel"],
                                "Set a channel to receive logs of bans, warns, and admin actions."),
            "mod_ping":        ("Ping",             ["/ping"],
                                "Check if the bot is alive and measure response latency."),
            "mod_purge":       ("Purge",            ["/purge", "/del"],
                                "Delete multiple messages at once. Reply to a message and use /purge."),
            "mod_reporting":   ("Reports",          ["/report", "/reports on/off"],
                                "Allow users to @report messages to admins. Admins can toggle this on/off."),
            "mod_sed":         ("Sed/Regex",        ["s/old/new"],
                                "Edit messages with sed-like syntax. Reply with s/old/new to correct yourself."),
            "mod_shell":       ("Shell",            ["/shell <cmd>"],
                                "Run shell commands on the server (owner only, use with caution)."),
            "mod_speedtest":   ("Speed Test",       ["/speedtest"],
                                "Run an internet speed test on the server and report download/upload speeds."),
            "mod_stickers":    ("Stickers",         ["/kang", "/stickerid", "/getsticker", "/stickers"],
                                "Steal stickers into a pack, get sticker file IDs, and manage sticker packs."),
            "mod_tagall":      ("Tag All",          ["/tagall", "/tag"],
                                "Tag all members in a group. Admins only. Use sparingly!"),
            "mod_translator":  ("Translator",       ["/tr <lang>", "/tl <lang>"],
                                "Translate messages. Reply to any message with /tr en to translate to English."),
            "mod_truthdare":   ("Truth or Dare",    ["/truth", "/dare"],
                                "Play Truth or Dare in a group! Gets questions/dares from a built-in list."),
            "mod_ud":          ("Urban Dict",       ["/ud <word>"],
                                "Look up slang definitions from Urban Dictionary."),
            "mod_wallpaper":   ("Wallpaper",        ["/wall <query>"],
                                "Search and send wallpapers from Wallhaven directly in Telegram."),
            "mod_wiki":        ("Wikipedia",        ["/wiki <query>"],
                                "Search Wikipedia and get a summary of any topic."),
            "mod_writetool":   ("Write Tool",       ["/write <text>"],
                                "Generate a handwritten-style image of any text you send."),
            "mod_animequotes": ("Anime Quotes",     ["/quote", "/animequote"],
                                "Get random inspirational quotes from famous anime characters."),
            "mod_gettime":     ("Time",             ["/time <city>"],
                                "Get the current time in any city or timezone around the world."),
            "mod_badwords":    ("Bad Words",        ["/addword", "/rmword", "/badwords", "/wordaction"],
                                "Filter profanity and custom bad words with configurable punishments."),
        }
        info = _MOD_INFO.get(data)
        if info:
            mod_label, cmds, desc = info
            cmds_text = " | ".join(f"<code>{c}</code>" for c in cmds) if cmds else small_caps("see /help for commands")
            msg = (
                b(f"📦 {small_caps(mod_label)}") + "\n\n"
                + bq(small_caps(desc)) + "\n\n"
                + b(small_caps("commands: ")) + cmds_text
            )
            try:
                await query.answer(f"📦 {mod_label} — {desc[:80]}", show_alert=True)
            except Exception:
                pass
        else:
            try:
                await query.answer(f"Module: {data.replace('mod_', '')}", show_alert=True)
            except Exception:
                pass
        return

    if data == "inline_anim_toggle":
        from handlers.inline_handler import get_animation_enabled, set_animation_enabled
        cur = get_animation_enabled()
        set_animation_enabled(not cur)
        status = "✅ ON" if not cur else "🔕 OFF"
        await safe_answer(query, f"Loading animation: {status}")
        # Refresh the filter poster panel so the button label updates
        try:
            from filter_poster import build_filter_poster_settings_keyboard, get_filter_poster_settings_text
            await _smart_edit(
                get_filter_poster_settings_text(chat_id),
                build_filter_poster_settings_keyboard(chat_id),
            )
        except Exception:
            pass
        return

    # ── Fast inline invite link (loading animation) ───────────────────────────
    if data.startswith("inv_loading:") or data.startswith("inv_ready:"):
        from handlers.inline_handler import handle_inv_loading_callback
        await handle_inv_loading_callback(update, context)
        return

    # ── Chatbot API key panel ─────────────────────────────────────────────────
    if data == "admin_chatbot_panel" or data.startswith("chatbot_gc_") or data.startswith("chatbot_add_") or data.startswith("chatbot_del_") or data.startswith("chatbot_gender_") or data == "chatbot_usage_stats":
        from handlers.chatbot_panel import handle_chatbot_panel_callback
        await handle_chatbot_panel_callback(update, context)
        return

    # ── Inline Request (from filter poster "Not found" / "Hindi not available") ──
    if data.startswith("request_anime:") or data.startswith("request_hindi:"):
        is_hindi = data.startswith("request_hindi:")
        anime_name = data.split(":", 1)[1].strip()
        # Trigger same logic as /request command with the anime name pre-filled
        try:
            from modules.animerequest import request_cmd as _req_cmd
            # Build fake context args
            context.args = anime_name.split()
            await _req_cmd(update, context)
        except Exception:
            # Fallback: show instructions
            _prefix = "Hindi dub of " if is_hindi else ""
            try:
                await query.answer(
                    f"Type: /request {anime_name}",
                    show_alert=True,
                )
            except Exception:
                pass
            try:
                await query.message.reply_text(
                    f"📩 <b>Send your request:</b>\n"
                    f"<code>/request {_prefix}{anime_name}</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return

    # ── Unhandled fallback ─────────────────────────────────────────────────────
    logger.debug(f"Unhandled callback: {data!r} from user {uid}")
