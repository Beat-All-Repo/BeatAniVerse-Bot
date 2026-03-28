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

from core.config import ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL
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
        from handlers.help import broadcaststats_command
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
        from handlers.misc_cmds import logs_command
        await logs_command(update, context)
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
        from handlers.help import backup_command
        await backup_command(update, context)
        return

    # ── Clone management ───────────────────────────────────────────────────────
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
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id, get_filter_poster_settings_text(chat_id),
                reply_markup=build_filter_poster_settings_keyboard(chat_id),
            )
        except Exception:
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
            await safe_edit_text(
                query, get_filter_poster_settings_text(fp_cid),
                reply_markup=build_filter_poster_settings_keyboard(fp_cid),
            )
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
            from handlers.post_gen import show_category_settings_menu
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
            from handlers.post_gen import update_category_field, show_category_settings_menu
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
            from handlers.post_gen import update_category_field, show_category_settings_menu
            update_category_field(cat_name, "buttons", "[]")
            await safe_answer(query, "Buttons cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_font_{cat_name}":
            if not is_admin:
                return
            await safe_edit_text(
                query, b(f" Font Style for {e(cat_name.upper())}"),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("Normal", callback_data=f"cat_font_set_{cat_name}_normal"),
                     bold_button("Small Caps", callback_data=f"cat_font_set_{cat_name}_smallcaps")],
                    [_back_btn("admin_category_settings"), _close_btn()],
                ]),
            )
            return

        if data.startswith(f"cat_font_set_{cat_name}_"):
            if not is_admin:
                return
            font_val = data[len(f"cat_font_set_{cat_name}_"):]
            from handlers.post_gen import update_category_field, show_category_settings_menu
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
            user_states[uid] = SET_CATEGORY_THUMBNAIL
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Set Thumbnail for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the thumbnail URL, or 'default' to reset.")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")]]),
            )
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
        from handlers.help import exportusers_command
        asyncio.create_task(exportusers_command(update, context))
        await safe_answer(query, small_caps("📤 exporting users…"))
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
        from handlers.misc_cmds import _show_autoupdate_menu
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
                    from handlers.media_cmds import generate_and_send_post
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
    if data.startswith("user_features_"):
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from handlers.user_features import send_user_features_panel
        await send_user_features_panel(update, context, query, chat_id, page)
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
        from core.filters_system import filters_config
        dm_on = filters_config["global"].get("dm", True)
        grp_on = filters_config["global"].get("group", True)
        text = (
            b("Filter Settings") + "\n\n"
            f"<b>DM:</b> {'ON' if dm_on else 'OFF'}\n"
            f"<b>GROUP:</b> {'ON' if grp_on else 'OFF'}"
        )
        keyboard = [
            [bold_button("TOGGLE DM", callback_data="filter_toggle_dm")],
            [bold_button("TOGGLE GROUP", callback_data="filter_toggle_group")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
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

    # ── Unhandled fallback ─────────────────────────────────────────────────────
    logger.debug(f"Unhandled callback: {data!r} from user {uid}")
