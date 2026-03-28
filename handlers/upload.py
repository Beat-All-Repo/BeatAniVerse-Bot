"""
handlers/upload.py
==================
Upload manager: auto-captions videos, manages season/episode counters.
Handles: /upload command, video messages from admin, channel post auto-caption.
"""
import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID, DEFAULT_CAPTION, ALL_QUALITIES
from core.logging_setup import logger
from core.helpers import safe_send_message, safe_edit_text
from core.buttons import bold_button, _back_btn
from core.text_utils import b, bq, code, e
from core.state_machine import (
    user_states, upload_progress, upload_lock,
    UPLOAD_SET_CAPTION, UPLOAD_SET_SEASON, UPLOAD_SET_EPISODE,
    UPLOAD_SET_TOTAL, UPLOAD_SET_CHANNEL,
)
from core.filters_system import force_sub_required


async def load_upload_progress() -> None:
    """Load upload progress from database into global dict."""
    global upload_progress
    try:
        from database_dual import db_manager
        row = None
        with db_manager.get_cursor() as cur:
            try:
                cur.execute("""
                    SELECT target_chat_id, season, episode, total_episode, video_count,
                           selected_qualities, base_caption, auto_caption_enabled, anime_name
                    FROM bot_progress WHERE id = 1
                """)
                row = cur.fetchone()
            except Exception:
                try:
                    cur.execute("""
                        SELECT target_chat_id, season, episode, total_episode, video_count,
                               selected_qualities, base_caption, auto_caption_enabled
                        FROM bot_progress WHERE id = 1
                    """)
                    row_short = cur.fetchone()
                    if row_short:
                        row = tuple(row_short) + ("Anime Name",)
                except Exception:
                    pass
        if row and len(row) >= 8:
            upload_progress.update({
                "target_chat_id": row[0],
                "season": row[1] or 1,
                "episode": row[2] or 1,
                "total_episode": row[3] or 1,
                "video_count": row[4] or 0,
                "selected_qualities": row[5].split(",") if row[5] else ["480p", "720p", "1080p"],
                "base_caption": row[6] or DEFAULT_CAPTION,
                "auto_caption_enabled": bool(row[7]),
                "anime_name": row[8] if len(row) > 8 else "Anime Name",
            })
    except Exception as exc:
        logger.debug(f"load_upload_progress error: {exc}")


async def save_upload_progress() -> None:
    """Persist upload progress to database."""
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("""
                UPDATE bot_progress SET
                    target_chat_id = %s, season = %s, episode = %s,
                    total_episode = %s, video_count = %s,
                    selected_qualities = %s, base_caption = %s,
                    auto_caption_enabled = %s, anime_name = %s
                WHERE id = 1
            """, (
                upload_progress["target_chat_id"],
                upload_progress["season"],
                upload_progress["episode"],
                upload_progress["total_episode"],
                upload_progress["video_count"],
                ",".join(upload_progress["selected_qualities"]),
                upload_progress["base_caption"],
                upload_progress["auto_caption_enabled"],
                upload_progress.get("anime_name", "Anime Name"),
            ))
    except Exception as exc:
        logger.debug(f"save_upload_progress error: {exc}")


def build_caption_from_progress() -> str:
    """Build formatted caption for current episode/quality."""
    quality = "N/A"
    if upload_progress["selected_qualities"]:
        idx = upload_progress["video_count"] % len(upload_progress["selected_qualities"])
        quality = upload_progress["selected_qualities"][idx]
    return (
        upload_progress["base_caption"]
        .replace("{anime_name}", upload_progress.get("anime_name", "Anime Name"))
        .replace("{season}", f"{upload_progress['season']:02}")
        .replace("{episode}", f"{upload_progress['episode']:02}")
        .replace("{total_episode}", f"{upload_progress['total_episode']:02}")
        .replace("{quality}", quality)
    )


def get_upload_menu_markup() -> InlineKeyboardMarkup:
    """Build upload manager keyboard."""
    auto_status = "✅ ON" if upload_progress["auto_caption_enabled"] else "❌ OFF"
    return InlineKeyboardMarkup([
        [bold_button("Preview Caption", callback_data="upload_preview"),
         bold_button("Set Caption", callback_data="upload_set_caption")],
        [bold_button("Set Anime Name", callback_data="upload_set_anime_name"),
         bold_button("Set Season", callback_data="upload_set_season")],
        [bold_button("Set Episode", callback_data="upload_set_episode"),
         bold_button("Total Episodes", callback_data="upload_set_total")],
        [bold_button("Quality Settings", callback_data="upload_quality_menu"),
         bold_button("Target Channel", callback_data="upload_set_channel")],
        [bold_button(f"Auto-Caption: {auto_status}", callback_data="upload_toggle_auto")],
        [bold_button("Reset Episode to 1", callback_data="upload_reset"),
         bold_button("Clear DB", callback_data="upload_clear_db")],
        [_back_btn("admin_back")],
    ])


async def show_upload_menu(
    chat_id: int,
    context,
    edit_msg=None,
) -> None:
    """Display the upload manager panel."""
    target = (
        f"✅ {code(str(upload_progress['target_chat_id']))}"
        if upload_progress["target_chat_id"] else "❌ Not Set"
    )
    auto = "✅ ON" if upload_progress["auto_caption_enabled"] else "❌ OFF"
    qualities = ", ".join(upload_progress["selected_qualities"]) or "None"

    text = (
        b("📤 Upload Manager") + "\n\n"
        f"<b>🎌 Anime:</b> {code(e(upload_progress.get('anime_name', 'Anime Name')))}\n"
        f"<b>📢 Target Channel:</b> {target}\n"
        f"<b>Auto-Caption:</b> {auto}\n"
        f"<b>📅 Season:</b> {code(str(upload_progress['season']))}\n"
        f"<b>🔢 Episode:</b> {code(str(upload_progress['episode']))} / "
        + code(str(upload_progress["total_episode"])) + "\n"
        f"<b>🎛 Qualities:</b> {code(qualities)}\n"
        f"<b>🎬 Videos Sent:</b> " + code(str(upload_progress["video_count"]))
    )
    markup = get_upload_menu_markup()

    if edit_msg:
        try:
            await context.bot.delete_message(
                chat_id=chat_id, message_id=edit_msg.message_id
            )
        except Exception:
            pass

    from core.panel_image import get_panel_pic_async
    img_url = await get_panel_pic_async("upload")
    if img_url:
        try:
            await context.bot.send_photo(
                chat_id, img_url, caption=text,
                parse_mode=ParseMode.HTML, reply_markup=markup
            )
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


@force_sub_required
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    try:
        await update.message.delete()
    except Exception:
        pass
    user_states.pop(update.effective_user.id, None)
    await load_upload_progress()
    await show_upload_menu(update.effective_chat.id, context)


async def handle_upload_video(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle video sent to bot by admin — auto-captions and forwards."""
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID):
        return
    if not update.message or not update.message.video:
        return

    async with upload_lock:
        await load_upload_progress()

        if not upload_progress["target_chat_id"]:
            await update.message.reply_text(
                b("❌ Target channel not set!") + "\n" + bq(b("Use /upload to configure it first.")),
                parse_mode=ParseMode.HTML,
            )
            return

        if not upload_progress["selected_qualities"]:
            await update.message.reply_text(
                b("❌ No qualities selected!") + "\n" + bq(b("Use /upload → Quality Settings.")),
                parse_mode=ParseMode.HTML,
            )
            return

        file_id = update.message.video.file_id
        caption = build_caption_from_progress()

        try:
            await context.bot.send_video(
                chat_id=upload_progress["target_chat_id"],
                video=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
            )

            quality = upload_progress["selected_qualities"][
                upload_progress["video_count"] % len(upload_progress["selected_qualities"])
            ]
            await update.message.reply_text(
                b(f"✅ Video forwarded! Quality: {quality}") + "\n"
                + bq(
                    f"<b>Season:</b> {upload_progress['season']:02}\n"
                    f"<b>Episode:</b> {upload_progress['episode']:02}"
                ),
                parse_mode=ParseMode.HTML,
            )

            upload_progress["video_count"] += 1
            if upload_progress["video_count"] >= len(upload_progress["selected_qualities"]):
                upload_progress["episode"] += 1
                upload_progress["total_episode"] = max(
                    upload_progress["total_episode"], upload_progress["episode"]
                )
                upload_progress["video_count"] = 0

            await save_upload_progress()

        except Exception as exc:
            from core.helpers import UserFriendlyError
            await update.message.reply_text(
                UserFriendlyError.get_user_message(exc), parse_mode=ParseMode.HTML,
            )


async def handle_channel_post(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Auto-caption videos posted directly to the target channel."""
    if not update.channel_post or not update.channel_post.video:
        return
    chat_id = update.effective_chat.id
    await load_upload_progress()

    if (
        chat_id != upload_progress.get("target_chat_id")
        or not upload_progress.get("auto_caption_enabled")
    ):
        return

    async with upload_lock:
        if not upload_progress["selected_qualities"]:
            return
        caption = build_caption_from_progress()
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=update.channel_post.message_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
            upload_progress["video_count"] += 1
            if upload_progress["video_count"] >= len(upload_progress["selected_qualities"]):
                upload_progress["episode"] += 1
                upload_progress["total_episode"] = max(
                    upload_progress["total_episode"], upload_progress["episode"]
                )
                upload_progress["video_count"] = 0
            await save_upload_progress()
        except Exception as exc:
            logger.debug(f"Auto-caption error: {exc}")
