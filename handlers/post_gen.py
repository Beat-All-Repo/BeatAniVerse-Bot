"""
handlers/post_gen.py
====================
Post generation engine, category settings management,
watermark system, and button building from settings.
"""
import json
import asyncio
from io import BytesIO
from typing import Optional, Dict, Any, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID, TMDB_API_KEY, PUBLIC_ANIME_CHANNEL_URL, JOIN_BTN_TEXT
from core.text_utils import b, bq, e, code, small_caps
from core.helpers import safe_send_message, safe_send_photo
from core.cache import cache_get, cache_set
from core.logging_setup import logger, db_logger


# ── Category defaults ─────────────────────────────────────────────────────────
CATEGORY_DEFAULTS = {
    "anime": {
        "template_name": "rich_anime", "branding": "", "buttons": "[]",
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    },
    "manga": {
        "template_name": "rich_manga", "branding": "", "buttons": "[]",
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    },
    "movie": {
        "template_name": "rich_movie", "branding": "", "buttons": "[]",
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    },
    "tvshow": {
        "template_name": "rich_tvshow", "branding": "", "buttons": "[]",
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    },
}


def get_category_settings(category: str) -> Dict:
    """Fetch or initialize category settings from DB."""
    defaults = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["anime"])
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT template_name, branding, buttons, caption_template,
                       thumbnail_url, font_style, logo_file_id, logo_position,
                       watermark_text, watermark_position
                FROM category_settings WHERE category = %s
            """, (category,))
            row = cur.fetchone()
        if row:
            return {
                "template_name": row[0] or defaults["template_name"],
                "branding": row[1] or "",
                "buttons": json.loads(row[2]) if row[2] and row[2] != "[]" else [],
                "caption_template": row[3] or "",
                "thumbnail_url": row[4] or "",
                "font_style": row[5] or "normal",
                "logo_file_id": row[6],
                "logo_position": row[7] or "bottom",
                "watermark_text": row[8],
                "watermark_position": row[9] or "center",
            }
    except Exception as exc:
        db_logger.debug(f"get_category_settings error: {exc}")
    return {
        "template_name": defaults["template_name"], "branding": "", "buttons": [],
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    }


def update_category_field(category: str, field: str, value: Any) -> bool:
    """Update a single field in category_settings (upsert)."""
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute(
                f"UPDATE category_settings SET {field} = %s WHERE category = %s",
                (value, category),
            )
            if cur.rowcount == 0:
                try:
                    cur.execute(
                        "INSERT INTO category_settings (category) VALUES (%s) ON CONFLICT (category) DO NOTHING",
                        (category,),
                    )
                    cur.execute(
                        f"UPDATE category_settings SET {field} = %s WHERE category = %s",
                        (value, category),
                    )
                except Exception:
                    pass
        return True
    except Exception as exc:
        db_logger.error(f"update_category_field {field}: {exc}")
        return False


def build_buttons_from_settings(
    settings: Dict,
    anime_title: str = "",
    join_url: str = "",
) -> Optional[InlineKeyboardMarkup]:
    """
    Convert settings buttons list to InlineKeyboardMarkup.
    Supports:
      - {link} placeholder → replaced with join_url
      - Button text styles: normal | smallcaps | custom
      - Emoji in button labels
      - Colour prefixes: #g #r #b #p #y
    """
    btns = settings.get("buttons", [])
    if not btns:
        return None

    # Determine button text style from settings
    btn_style = settings.get("button_style", "normal")
    try:
        from database_dual import get_setting
        btn_style = get_setting("button_style", btn_style) or btn_style
    except Exception:
        pass

    def _apply_btn_style(text: str) -> str:
        if btn_style == "smallcaps":
            return small_caps(text)
        # "normal" or "custom" — keep as-is (custom means user sets exactly what they want)
        return text

    keyboard = []
    row = []
    for i, btn in enumerate(btns):
        label = btn.get("text", "Link")
        url   = btn.get("url", "")
        if not url:
            continue

        # Resolve {link} placeholder in URL
        if "{link}" in url:
            url = url.replace("{link}", join_url or "")
        if not url:
            continue

        # Colour prefix → prepend icon
        for pfx, icon in [
            ("#g ", "🟢 "), ("#r ", "🔴 "), ("#b ", "🔵 "),
            ("#p ", "🟣 "), ("#y ", "🟡 ")
        ]:
            if label.startswith(pfx):
                label = icon + label[len(pfx):]
                break

        label = _apply_btn_style(label)
        row.append(InlineKeyboardButton(label, url=url))
        if len(row) == 2 or i == len(btns) - 1:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(keyboard) if keyboard else None

async def add_watermark(
    image_url: str, text: str, position: str = "center"
) -> Optional[BytesIO]:
    """Download image and stamp watermark, return BytesIO or None."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    import requests
    try:
        resp = requests.get(image_url, timeout=12)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pos_map = {
            "bottom": ((img.width - text_w) // 2, img.height - text_h - 15),
            "top": ((img.width - text_w) // 2, 15),
            "left": (15, (img.height - text_h) // 2),
            "right": (img.width - text_w - 15, (img.height - text_h) // 2),
            "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
            "bottom-left": (15, img.height - text_h - 15),
            "bottom-right": (img.width - text_w - 15, img.height - text_h - 15),
        }
        pos = pos_map.get(position, pos_map["center"])
        draw.text((pos[0] + 2, pos[1] + 2), text, fill=(0, 0, 0, 100), font=font)
        draw.text(pos, text, fill=(255, 255, 255, 200), font=font)
        final = Image.alpha_composite(img, overlay)
        out = BytesIO()
        final.convert("RGB").save(out, format="JPEG", quality=90)
        out.seek(0)
        return out
    except Exception as exc:
        logger.debug(f"Watermark error: {exc}")
        return None


def _cache_post(category: str, key: str, data: Optional[Dict]) -> None:
    """Cache post data for history."""
    if not data:
        return
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO posts_cache (category, title, anilist_id, media_data, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                category, key[:200],
                data.get("id") if isinstance(data, dict) else None,
                json.dumps(data)[:5000] if data else None,
            ))
    except Exception:
        pass


async def generate_and_send_post(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    category: str,
    search_query: str = "",
    media_id: Optional[int] = None,
    source_manga_id: Optional[str] = None,
    preferred_size: str = "extraLarge",
) -> bool:
    """
    Full post generation for anime, manga, movie, tvshow.
    Returns True on success.
    """
    from api.anilist import AniListClient
    from api.tmdb import TMDBClient
    from api.mangadex import MangaDexClient

    settings = get_category_settings(category)
    data = None
    poster_url = None
    caption_text = ""

    try:
        if category == "anime":
            data = (
                AniListClient.get_by_id(media_id, "ANIME") if media_id
                else AniListClient.search_anime(search_query)
            )
            if not data:
                await safe_send_message(context.bot, chat_id, b("❌ No anime found for: ") + code(e(search_query or str(media_id))))
                return False
            tmpl = settings.get("caption_template", "")
            caption_text = AniListClient.format_anime_caption(data, tmpl if tmpl else None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            cover = (data.get("coverImage") or {})
            if preferred_size == "bannerImage":
                poster_url = data.get("bannerImage") or cover.get("extraLarge") or cover.get("large") or cover.get("medium")
            else:
                size_order = ["extraLarge", "large", "medium"]
                if preferred_size == "large":
                    size_order = ["large", "extraLarge", "medium"]
                elif preferred_size == "medium":
                    size_order = ["medium", "large", "extraLarge"]
                poster_url = next((cover.get(s) for s in size_order if cover.get(s)), None)

        elif category == "manga":
            if source_manga_id:
                manga = MangaDexClient.get_manga(source_manga_id)
                if manga:
                    caption_text, poster_url = MangaDexClient.format_manga_info(manga)
                    anilist_data = AniListClient.search_manga(search_query or "")
                    if anilist_data:
                        tmpl = settings.get("caption_template", "")
                        caption_text = AniListClient.format_manga_caption(anilist_data, tmpl if tmpl else None)
                        cover = (anilist_data.get("coverImage") or {})
                        poster_url = cover.get("extraLarge") or cover.get("large") or poster_url
                else:
                    await safe_send_message(context.bot, chat_id, b("❌ Manga not found on MangaDex."))
                    return False
            else:
                data = (
                    AniListClient.get_by_id(media_id, "MANGA") if media_id
                    else AniListClient.search_manga(search_query)
                )
                if not data:
                    md_results = MangaDexClient.search_manga(search_query)
                    if md_results:
                        caption_text, poster_url = MangaDexClient.format_manga_info(md_results[0])
                    else:
                        await safe_send_message(context.bot, chat_id, b("❌ No manga found for: ") + code(e(search_query or "")))
                        return False
                else:
                    tmpl = settings.get("caption_template", "")
                    caption_text = AniListClient.format_manga_caption(data, tmpl if tmpl else None)
                    cover = (data.get("coverImage") or {})
                    size_order = ["extraLarge", "large", "medium"]
                    poster_url = next((cover.get(s) for s in size_order if cover.get(s)), None)
                branding = settings.get("branding", "")
                if branding:
                    caption_text += f"\n\n{branding}"

        elif category == "movie":
            data = TMDBClient.search_movie(search_query) if not media_id else TMDBClient.get_movie_details(media_id)
            if not data:
                await safe_send_message(context.bot, chat_id, b("❌ No movie found. Make sure TMDB_API_KEY is configured." if not TMDB_API_KEY else "❌ No movie found."))
                return False
            tmpl = settings.get("caption_template", "")
            caption_text = TMDBClient.format_movie_caption(data, tmpl if tmpl else None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            poster_path = data.get("poster_path")
            if poster_path:
                poster_url = TMDBClient.get_poster_url(poster_path)

        elif category == "tvshow":
            data = TMDBClient.search_tv(search_query) if not media_id else TMDBClient.get_tv_details(media_id)
            if not data:
                await safe_send_message(context.bot, chat_id, b("❌ No TV show found."))
                return False
            tmpl = settings.get("caption_template", "")
            caption_text = TMDBClient.format_tv_caption(data, tmpl if tmpl else None)
            branding = settings.get("branding", "")
            if branding:
                caption_text += f"\n\n{branding}"
            poster_path = data.get("poster_path")
            if poster_path:
                poster_url = TMDBClient.get_poster_url(poster_path)

    except Exception as exc:
        logger.error(f"generate_and_send_post fetch error: {exc}")
        await safe_send_message(context.bot, chat_id, b("❌ Failed to fetch data. Please try again."))
        return False

    # Apply font style
    if settings.get("font_style") == "smallcaps":
        from core.text_utils import small_caps
        caption_text = small_caps(caption_text)

    # Truncate if too long
    if len(caption_text) > 4000:
        caption_text = caption_text[:3980] + "\n<b>…(truncated)</b>"

    # Apply global text style
    try:
        from text_style import apply_style
        caption_text = apply_style(caption_text)
    except Exception:
        pass

    # Build buttons
    buttons_markup = build_buttons_from_settings(settings)
    existing_rows = list(buttons_markup.inline_keyboard) if buttons_markup else []

    # Collect alt images
    _alt_images = []
    if data and isinstance(data, dict):
        cov = data.get("coverImage") or {}
        for sz in ("extraLarge", "large", "medium"):
            url_ = cov.get(sz)
            if url_ and url_ not in _alt_images:
                _alt_images.append(url_)
        banner = data.get("bannerImage")
        if banner and banner not in _alt_images:
            _alt_images.append(banner)
    if poster_url and poster_url not in _alt_images:
        _alt_images.insert(0, poster_url)

    nav_row = []
    if len(_alt_images) > 1:
        img_key = f"imgset_{category}_{search_query or str(media_id)}"
        cache_set(img_key, {"urls": _alt_images, "caption": caption_text, "shown": set()})
        nav_row = [
            InlineKeyboardButton("🔙", callback_data=f"imgn:0:{img_key}:prev"),
            InlineKeyboardButton("✕", callback_data="close_message"),
            InlineKeyboardButton("🔜", callback_data=f"imgn:0:{img_key}:next"),
        ]
    else:
        nav_row = [InlineKeyboardButton("✕", callback_data="close_message")]

    try:
        from database_dual import get_setting
        join_text = get_setting("env_JOIN_BTN_TEXT", JOIN_BTN_TEXT) or JOIN_BTN_TEXT
    except Exception:
        join_text = JOIN_BTN_TEXT

    join_btn = InlineKeyboardButton(join_text, url=PUBLIC_ANIME_CHANNEL_URL)
    nav_keyboard = existing_rows + [[join_btn], nav_row]
    buttons_markup = InlineKeyboardMarkup(nav_keyboard)

    # Watermark
    wm_text = settings.get("watermark_text")
    wm_pos = settings.get("watermark_position", "center")
    if poster_url and wm_text:
        try:
            wm_image = await add_watermark(poster_url, wm_text, wm_pos)
            if wm_image:
                await context.bot.send_photo(
                    chat_id, wm_image, caption=caption_text,
                    parse_mode=ParseMode.HTML, reply_markup=buttons_markup,
                )
                _cache_post(category, search_query or str(media_id), data)
                return True
        except Exception as exc:
            logger.debug(f"Watermark send failed: {exc}")

    # Try landscape poster via poster_engine
    try:
        from poster_engine import (
            _make_poster, _build_anime_data, _build_manga_data,
            _build_movie_data, _build_tv_data, _get_settings as _pe_settings,
        )
        if data:
            _pe_cat_map = {"anime": "ani", "manga": "anim", "movie": "net", "tvshow": "net"}
            _pe_tmpl = _pe_cat_map.get(category, "ani")
            _pe_s = _pe_settings(category)
            _wm_txt = _pe_s.get("watermark_text") or wm_text
            _wm_pos = _pe_s.get("watermark_position", "center")
            if category == "anime":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_anime_data(data)
            elif category == "manga":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_manga_data(data)
            elif category == "movie":
                _t, _n, _st, _rows, _d, _cu, _sc = _build_movie_data(data)
            else:
                _t, _n, _st, _rows, _d, _cu, _sc = _build_tv_data(data)
            _lp_buf = _make_poster(_pe_tmpl, _t, _n, _st, _rows, _d, _cu, _sc,
                                   _wm_txt, _wm_pos, None, "bottom")
            if _lp_buf:
                await context.bot.send_photo(
                    chat_id, _lp_buf,
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=buttons_markup,
                )
                _cache_post(category, search_query or str(media_id), data)
                return True
    except Exception as _pe_exc:
        logger.debug(f"Landscape poster failed, falling back: {_pe_exc}")

    # Standard send
    if poster_url:
        sent = await safe_send_photo(
            context.bot, chat_id, poster_url,
            caption=caption_text, reply_markup=buttons_markup,
        )
        if not sent:
            await safe_send_message(context.bot, chat_id, caption_text, reply_markup=buttons_markup)
    else:
        await safe_send_message(context.bot, chat_id, caption_text, reply_markup=buttons_markup)

    _cache_post(category, search_query or str(media_id), data)
    return True
