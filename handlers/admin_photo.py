"""
handlers/admin_photo.py
=======================
Handles photos, stickers, and documents sent by the admin user.
Covers all image-based conversation states:
  - SET_CATEGORY_LOGO
  - AWAITING_WATERMARK_<cat>
  - AWAITING_LOGO_<cat>
  - AWAITING_WM_LAYER_<layer>_<chat_id>
  - CW_AWAITING_IMAGE   (channel welcome image)
  - PENDING_CHANNEL_POST (forwarded post → extract channel ID)
  - AF_ADD_CONNECTION_SOURCE / AF_ADD_CONNECTION_TARGET (forwarded posts)
  - AU_ADD_MANGA_TARGET (forwarded post → manga target channel)
"""

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.text_utils import b, bq, e, code, small_caps
from core.state_machine import (
    user_states,
    SET_CATEGORY_LOGO,
    PENDING_CHANNEL_POST,
    AF_ADD_CONNECTION_SOURCE, AF_ADD_CONNECTION_TARGET,
    AU_ADD_MANGA_TARGET,
    ADD_CHANNEL_TITLE,
)
from core.buttons import _back_btn, bold_button, _close_btn
from core.logging_setup import logger


def _extract_fwd_chat(msg):
    """Extract forwarded-from chat from a message (PTB v21 compatible)."""
    fwd_chat = None
    try:
        _fo = getattr(msg, "forward_origin", None)
        if _fo and hasattr(_fo, "chat"):
            fwd_chat = _fo.chat
        elif _fo and hasattr(_fo, "sender_chat"):
            fwd_chat = _fo.sender_chat
        elif getattr(msg, "forward_from_chat", None):
            fwd_chat = msg.forward_from_chat
    except Exception:
        pass
    return fwd_chat


async def handle_admin_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle photo / sticker / document / animation sent by admin.
    Routes based on current user state.
    """
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return

    uid = update.effective_user.id
    state = user_states.get(uid)

    if not update.message:
        return

    msg = update.message

    # ── Extract file_id from whatever media was sent ──────────────────────────
    file_id = None
    file_type = "image"

    if msg.sticker:
        file_id = msg.sticker.file_id
        file_type = "sticker"
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_type = "image"
    elif msg.document:
        mime = msg.document.mime_type or ""
        fname = (msg.document.file_name or "").lower()
        if "image" in mime or "pdf" in mime or fname.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf")
        ):
            file_id = msg.document.file_id
            file_type = "pdf" if "pdf" in mime else "image"
        else:
            return  # not an image — ignore
    elif msg.animation:
        file_id = msg.animation.file_id
        file_type = "animation"

    # ── States that need a file_id ────────────────────────────────────────────

    if file_id:
        # AWAITING_WATERMARK_<CATEGORY>
        if isinstance(state, str) and state.startswith("AWAITING_WATERMARK_"):
            cat = state[len("AWAITING_WATERMARK_"):].lower()
            user_states.pop(uid, None)
            from handlers.post_gen import update_category_field
            ok = update_category_field(cat, "logo_file_id", file_id)
            update_category_field(cat, "logo_position", "bottom-right")
            kind = {"sticker": "Sticker", "image": "Image",
                    "pdf": "Document", "animation": "GIF"}.get(file_type, "File")
            if ok:
                await msg.reply_text(
                    b(f"✅ {kind} watermark saved for {cat.upper()}!")
                    + "\n<i>It will appear as overlay on all posters for this category.</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [_back_btn(f"cat_settings_{cat}"), _close_btn()]
                    ]),
                )
            else:
                await msg.reply_text(
                    b(f"❌ Failed to save watermark for {cat}. Check DB connection."),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [_back_btn(f"cat_settings_{cat}"), _close_btn()]
                    ]),
                )
            return

        # AWAITING_LOGO_<CATEGORY>
        if isinstance(state, str) and state.startswith("AWAITING_LOGO_"):
            cat = state[len("AWAITING_LOGO_"):].lower()
            user_states.pop(uid, None)
            from handlers.post_gen import update_category_field
            ok = update_category_field(cat, "logo_file_id", file_id)
            if ok:
                await msg.reply_text(
                    b(f"✅ Logo saved for {cat.upper()}!"),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [_back_btn(f"cat_settings_{cat}"), _close_btn()]
                    ]),
                )
            else:
                await msg.reply_text(
                    b(f"❌ Failed to save logo. Check DB connection."),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [_back_btn(f"cat_settings_{cat}"), _close_btn()]
                    ]),
                )
            return

        # SET_CATEGORY_LOGO (legacy state constant)
        if state == SET_CATEGORY_LOGO:
            category = context.user_data.get("editing_category")
            if category:
                from handlers.post_gen import update_category_field
                from handlers.admin_panel import show_category_settings_menu
                ok = update_category_field(category, "logo_file_id", file_id)
                if ok:
                    await msg.reply_text(
                        b(f"✅ Logo updated for {e(category.upper())}!"),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await msg.reply_text(
                        b("❌ Failed to save logo. Check DB connection."),
                        parse_mode=ParseMode.HTML,
                    )
            user_states.pop(uid, None)
            from handlers.admin_panel import show_category_settings_menu
            await show_category_settings_menu(
                context, update.effective_chat.id, category or "anime", None
            )
            return

        # AWAITING_WM_LAYER_<layer>_<chat_id>  (filter poster visual watermark)
        if isinstance(state, str) and state.startswith("AWAITING_WM_LAYER_"):
            parts_s = state.split("_")
            layer = parts_s[3].lower() if len(parts_s) > 3 else "c"
            try:
                fp_cid = int(parts_s[4])
            except Exception:
                fp_cid = uid
            user_states.pop(uid, None)
            try:
                from filter_poster import get_wm_layer, set_wm_layer
                ldata = get_wm_layer(fp_cid, layer)
                ldata["file_id"] = file_id
                ldata["enabled"] = True
                ldata["is_sticker"] = (file_type == "sticker")
                set_wm_layer(fp_cid, layer, ldata)
                _kind_wm = "sticker" if file_type == "sticker" else "image"
                await msg.reply_text(
                    b(small_caps(f"✅ layer {layer.upper()} visual watermark set ({_kind_wm})!"))
                    + "\n" + bq(b(small_caps("it will appear as overlay on all posters."))),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [_back_btn("admin_filter_poster"), _close_btn()]
                    ]),
                )
            except Exception as exc:
                await msg.reply_text(
                    b(f"❌ {e(str(exc)[:100])}"),
                    parse_mode=ParseMode.HTML,
                )
            return

        # CW_AWAITING_IMAGE — channel welcome image
        if isinstance(state, str) and state == "CW_AWAITING_IMAGE":
            ch_id = context.user_data.get("cw_editing_channel")
            if ch_id and file_id:
                try:
                    from database_dual import set_channel_welcome
                    set_channel_welcome(ch_id, image_file_id=file_id, image_url="")
                    user_states.pop(uid, None)
                    _kind = "sticker" if file_type == "sticker" else "image"
                    await msg.reply_text(
                        b(small_caps(f"✅ welcome {_kind} saved!")),
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                small_caps("✏️ edit more"),
                                callback_data=f"cw_edit_{ch_id}"
                            ),
                            _back_btn("admin_channel_welcome"),
                        ]]),
                    )
                except Exception as exc:
                    logger.debug(f"CW_AWAITING_IMAGE error: {exc}")
            return

    # ── States that use forwarded messages (no file_id needed) ────────────────

    # PENDING_CHANNEL_POST — admin forwards a post to extract channel ID
    if state == PENDING_CHANNEL_POST:
        fwd_chat = _extract_fwd_chat(msg)
        if not fwd_chat:
            await msg.reply_text(
                b("❌ This doesn't look like a forwarded channel post.\n\n")
                + bq("Forward any message from the channel you want to add."),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("🔙 Cancel", callback_data="manage_force_sub")]
                ]),
            )
            return
        try:
            tg_chat = await context.bot.get_chat(fwd_chat.id)
            context.user_data["new_ch_uname"] = str(tg_chat.id)
            context.user_data["new_ch_title"] = tg_chat.title
            user_states[uid] = ADD_CHANNEL_TITLE
            ch_info = f"<b>Channel:</b> {e(tg_chat.title)}\n<b>ID:</b> <code>{tg_chat.id}</code>"
            if tg_chat.username:
                ch_info += f"\n<b>Username:</b> @{e(tg_chat.username)}"
            await msg.reply_text(
                b("✅ Channel detected from forwarded post!") + "\n\n"
                + bq(ch_info) + "\n\n"
                + b("Send a display title, or /skip to use the channel name:"),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("🔙 Cancel", callback_data="manage_force_sub")]
                ]),
            )
        except Exception as exc:
            await msg.reply_text(
                b("❌ Could not verify that channel.\n\n")
                + bq(
                    b("Make sure the bot is admin in ")
                    + code(str(fwd_chat.id))
                    + b(f"\n\nError: ")
                    + code(e(str(exc)[:100]))
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [bold_button("🔙 Cancel", callback_data="manage_force_sub")]
                ]),
            )
        return

    # AF_ADD_CONNECTION_SOURCE — auto-forward: forwarded post sets source channel
    if state == AF_ADD_CONNECTION_SOURCE:
        fwd_chat = _extract_fwd_chat(msg)
        if fwd_chat:
            try:
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                context.user_data["af_source_id"] = tg_chat.id
                context.user_data["af_source_uname"] = tg_chat.username
                user_states[uid] = AF_ADD_CONNECTION_TARGET
                await msg.reply_text(
                    b(f"✅ Source detected: {e(tg_chat.title)}") + "\n\n"
                    + bq(b("Step 2/2: Send the TARGET channel @username, ID, or forward a post:")),
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [bold_button("🔙 Cancel", callback_data="admin_autoforward")]
                    ]),
                )
            except Exception as exc:
                await msg.reply_text(
                    b("❌ Could not verify source channel: ") + code(e(str(exc)[:100])),
                    parse_mode=ParseMode.HTML,
                )
        return

    # AF_ADD_CONNECTION_TARGET — auto-forward: forwarded post sets target channel
    if state == AF_ADD_CONNECTION_TARGET:
        fwd_chat = _extract_fwd_chat(msg)
        if fwd_chat:
            try:
                from database_dual import db_manager
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                src_id = context.user_data.get("af_source_id")
                src_uname = context.user_data.get("af_source_uname", "")
                if not src_id:
                    await msg.reply_text(
                        b("Session expired. Start over."), parse_mode=ParseMode.HTML
                    )
                    user_states.pop(uid, None)
                    return
                with db_manager.get_cursor() as cur:
                    cur.execute("""
                        INSERT INTO auto_forward_connections
                            (source_chat_id, source_chat_username, target_chat_id,
                             target_chat_username, active)
                        VALUES (%s, %s, %s, %s, TRUE)
                        ON CONFLICT DO NOTHING
                    """, (src_id, src_uname, tg_chat.id, tg_chat.username))
                await msg.reply_text(
                    b("✅ Auto-forward connection created!") + "\n\n"
                    + bq(
                        b("Source: ") + code(str(src_id)) + "\n"
                        + b("Target: ") + code(str(tg_chat.id)) + " — " + e(tg_chat.title)
                    ),
                    parse_mode=ParseMode.HTML,
                )
                user_states.pop(uid, None)
            except Exception as exc:
                await msg.reply_text(
                    b(f"❌ Error: {e(str(exc)[:100])}"), parse_mode=ParseMode.HTML
                )
        return

    # AU_ADD_MANGA_TARGET — manga tracker: forwarded post sets target channel
    if state == AU_ADD_MANGA_TARGET:
        fwd_chat = _extract_fwd_chat(msg)
        if fwd_chat:
            try:
                from api.mangadex import MangaTracker
                tg_chat = await context.bot.get_chat(fwd_chat.id)
                manga_id = context.user_data.get("au_manga_id")
                manga_title = context.user_data.get("au_manga_title", "Unknown")
                if not manga_id:
                    await msg.reply_text(
                        b("Session expired. Please start over."), parse_mode=ParseMode.HTML
                    )
                    user_states.pop(uid, None)
                    return
                success = MangaTracker.add_tracking(manga_id, manga_title, tg_chat.id)
                if success:
                    await msg.reply_text(
                        b(f"✅ Now tracking: {e(manga_title)}") + "\n\n"
                        + bq(
                            f"<b>Channel:</b> {e(tg_chat.title or str(tg_chat.id))}\n"
                            f"<b>Channel ID:</b> <code>{tg_chat.id}</code>\n\n"
                            + b("New chapters will be sent automatically.")
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await msg.reply_text(
                        b("❌ Failed to add tracking. Make sure bot is admin."),
                        parse_mode=ParseMode.HTML,
                    )
                user_states.pop(uid, None)
                for k in ("au_manga_id", "au_manga_title", "au_manga_mode", "au_manga_interval"):
                    context.user_data.pop(k, None)
            except Exception as exc:
                await msg.reply_text(
                    b(f"❌ Error: {e(str(exc)[:100])}"), parse_mode=ParseMode.HTML
                )
        return
