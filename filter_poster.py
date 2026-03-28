#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Ultimate Filter Poster Engine
==================================================
Full feature list:
  ✅ Two delivery modes (toggled per-chat from admin panel):
       MODE 1 — TEXT:   "Here is your link" + expirable join button
       MODE 2 — POSTER: Full layered anime poster + info + expirable join button

  ✅ Watermark layer system (up to 3 independent layers):
       Layer A — primary text watermark (font, size, color, opacity, position)
       Layer B — secondary text watermark (e.g. channel name)
       Layer C — image/sticker overlay (Telegram sticker or image URL, position, opacity, scale)

  ✅ Watermark positions:
       center | bottom | top | left | right
       bottom-left | bottom-right | top-left | top-right

  ✅ Telegram sticker support:
       Admin sends sticker → file_id saved → rendered as overlay layer on poster

  ✅ Expirable join link:
       Real Telegram invite link that expires after LINK_EXPIRY_MINUTES
       Falls back to PUBLIC_ANIME_CHANNEL_URL if no force-sub channels

  ✅ Auto-delete:
       Poster + link message deleted after filter_auto_delete_seconds
       Configurable per-chat from admin panel

  ✅ Small caps integration:
       If global_text_style = "smallcaps" → ALL filter captions, info texts,
       button labels, and "here is your link" text use small caps

  ✅ HTML support in all captions

  ✅ Dual-DB poster cache (NeonDB + MongoDB)

  ✅ Poster DB channel (save every new poster for instant reuse)

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import math
import os
import random
import re
import time
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── PIL (Pillow) ───────────────────────────────────────────────────────────────
try:
    from PIL import (
        Image, ImageDraw, ImageFont, ImageFilter,
        ImageEnhance, ImageOps, ImageColor,
    )
    PIL_OK = True
except ImportError:
    PIL_OK = False
    logger.warning("[FilterPoster] Pillow not installed — image generation disabled")

# ── ENV ────────────────────────────────────────────────────────────────────────
POSTER_DB_CHANNEL: int      = int(os.getenv("POSTER_DB_CHANNEL", "0") or "0")
PUBLIC_URL: str             = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")
LINK_EXPIRY_MINUTES: int    = int(os.getenv("LINK_EXPIRY_MINUTES", "5") or "5")
JOIN_BTN_TEXT_DEFAULT: str  = os.getenv("JOIN_BTN_TEXT", "Join Now")
HERE_LINK_TEXT_DEFAULT: str = os.getenv(
    "HERE_IS_LINK_TEXT",
    "ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ"
)
LINK_EXPIRED_TEXT_DEFAULT: str = os.getenv(
    "LINK_EXPIRED_TEXT",
    "This invite link has expired. Please request a new one."
)

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE      = os.path.dirname(__file__)
FONT_DIR   = os.path.join(_BASE, "fonts")
ICON_DIR   = os.path.join(_BASE, "iconspng")
STICKER_DIR = os.path.join(_BASE, "sticker_cache")
os.makedirs(STICKER_DIR, exist_ok=True)

# ── In-memory caches ──────────────────────────────────────────────────────────
_poster_cache: Dict[str, Dict]  = {}   # key → {file_id, caption, ts, ...}
_img_cache:    Dict[str, bytes] = {}   # url → raw bytes
_sticker_cache: Dict[str, str]  = {}   # file_id → local path
_CACHE_TTL = 86400 * 7                 # 7 days

# ═════════════════════════════════════════════════════════════════════════════
#  SMALL CAPS — applies to ALL text in this module if style = "smallcaps"
# ═════════════════════════════════════════════════════════════════════════════

_SC_MAP = {
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ',
    'j':'ᴊ','k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ',
    's':'ꜱ','t':'ᴛ','u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ',
    'A':'ᴀ','B':'ʙ','C':'ᴄ','D':'ᴅ','E':'ᴇ','F':'ꜰ','G':'ɢ','H':'ʜ','I':'ɪ',
    'J':'ᴊ','K':'ᴋ','L':'ʟ','M':'ᴍ','N':'ɴ','O':'ᴏ','P':'ᴘ','Q':'ǫ','R':'ʀ',
    'S':'ꜱ','T':'ᴛ','U':'ᴜ','V':'ᴠ','W':'ᴡ','X':'x','Y':'ʏ','Z':'ᴢ',
}


def _to_sc(text: str) -> str:
    return ''.join(_SC_MAP.get(c, c) for c in text)


def _get_global_style() -> str:
    try:
        from database_dual import get_setting
        return get_setting("global_text_style", "normal") or "normal"
    except Exception:
        return "normal"


def _styled(text: str) -> str:
    """
    Apply global text style to plain text.
    HTML tags and link href values are NEVER modified.
    """
    style = _get_global_style()
    if style != "smallcaps" or not text:
        return text
    # Parse HTML tokens — only transform text nodes
    result: List[str] = []
    i = 0
    in_tag = False
    while i < len(text):
        ch = text[i]
        if ch == '<':
            in_tag = True
            result.append(ch)
        elif ch == '>':
            in_tag = False
            result.append(ch)
        elif in_tag:
            result.append(ch)
        else:
            result.append(_SC_MAP.get(ch, ch))
        i += 1
    return ''.join(result)


def _styled_plain(text: str) -> str:
    """Apply style to plain text (no HTML)."""
    if _get_global_style() == "smallcaps":
        return _to_sc(text)
    return text


# ═════════════════════════════════════════════════════════════════════════════
#  DB HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _cache_key(title: str, template: str) -> str:
    return hashlib.md5(f"{title.lower().strip()}:{template}".encode()).hexdigest()


def _get_cached_poster(title: str, template: str) -> Optional[Dict]:
    key = _cache_key(title, template)
    # Memory cache
    e = _poster_cache.get(key)
    if e and (datetime.utcnow() - e.get("ts", datetime.utcnow())).total_seconds() < _CACHE_TTL:
        return e
    _poster_cache.pop(key, None)
    # DB check
    try:
        from database_dual import _pg_exec, _MG
        row = _pg_exec(
            "SELECT file_id, channel_msg_id, channel_id, caption, created_at "
            "FROM poster_cache WHERE cache_key = %s",
            (key,)
        )
        if row:
            entry = {"file_id": row[0], "channel_msg_id": row[1],
                     "channel_id": row[2], "caption": row[3], "ts": row[4] or datetime.utcnow()}
            _poster_cache[key] = entry
            return entry
        if _MG.db is not None:
            doc = _MG.db.poster_cache.find_one({"cache_key": key})
            if doc:
                entry = {"file_id": doc.get("file_id"), "channel_msg_id": doc.get("channel_msg_id"),
                         "channel_id": doc.get("channel_id"), "caption": doc.get("caption"),
                         "ts": doc.get("created_at", datetime.utcnow())}
                _poster_cache[key] = entry
                return entry
    except Exception as exc:
        logger.debug(f"get_cached_poster error: {exc}")
    return None


def _save_poster_cache(title: str, template: str, file_id: str,
                        channel_msg_id: int, channel_id: int, caption: str) -> None:
    key = _cache_key(title, template)
    entry = {"file_id": file_id, "channel_msg_id": channel_msg_id,
             "channel_id": channel_id, "caption": caption, "ts": datetime.utcnow()}
    _poster_cache[key] = entry
    try:
        from database_dual import _pg_run, _MG
        _pg_run("""
            INSERT INTO poster_cache
                (cache_key, title, template, file_id, channel_msg_id, channel_id, caption)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cache_key) DO UPDATE
                SET file_id = EXCLUDED.file_id,
                    channel_msg_id = EXCLUDED.channel_msg_id,
                    created_at = NOW()
        """, (key, title, template, file_id, channel_msg_id, channel_id, caption))
        if _MG.db is not None:
            _MG.db.poster_cache.update_one(
                {"cache_key": key},
                {"$set": {**entry, "cache_key": key, "title": title, "template": template,
                          "created_at": datetime.utcnow()}},
                upsert=True,
            )
    except Exception as exc:
        logger.debug(f"save_poster_cache error: {exc}")


def migrate_poster_cache_table() -> None:
    try:
        from database_dual import _pg_run
        _pg_run("""
            CREATE TABLE IF NOT EXISTS poster_cache (
                id SERIAL PRIMARY KEY,
                cache_key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                template TEXT DEFAULT 'ani',
                file_id TEXT NOT NULL,
                channel_msg_id BIGINT DEFAULT 0,
                channel_id BIGINT DEFAULT 0,
                caption TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    except Exception as exc:
        logger.debug(f"poster_cache migration: {exc}")


# ═════════════════════════════════════════════════════════════════════════════
#  SETTINGS — per-chat from DB
# ═════════════════════════════════════════════════════════════════════════════

def _setting(key: str, default: str = "") -> str:
    try:
        from database_dual import get_setting
        return get_setting(key, default) or default
    except Exception:
        return default


def _set(key: str, value: str) -> None:
    try:
        from database_dual import set_setting
        set_setting(key, value)
    except Exception:
        pass


# ── Filter delivery mode ──────────────────────────────────────────────────────

def get_filter_mode(chat_id: int) -> str:
    """Returns 'text' or 'poster'."""
    return _setting(f"filter_mode_{chat_id}", "poster")


def set_filter_mode(chat_id: int, mode: str) -> None:
    _set(f"filter_mode_{chat_id}", mode if mode in ("text", "poster") else "poster")


def get_filter_poster_enabled(chat_id: int) -> bool:
    return _setting(f"filter_poster_enabled_{chat_id}", "true") == "true"


def set_filter_poster_enabled(chat_id: int, enabled: bool) -> None:
    _set(f"filter_poster_enabled_{chat_id}", "true" if enabled else "false")


def get_filter_template(chat_id: int) -> str:
    return _setting(f"filter_poster_template_{chat_id}", "ani")


def set_filter_template(chat_id: int, template: str) -> None:
    _set(f"filter_poster_template_{chat_id}", template)


def get_auto_delete_seconds(chat_id: int) -> int:
    try:
        return int(_setting(f"filter_auto_delete_{chat_id}", "300"))
    except Exception:
        return 300


def set_auto_delete_seconds(chat_id: int, seconds: int) -> None:
    _set(f"filter_auto_delete_{chat_id}", str(max(0, seconds)))


def get_link_expiry_minutes(chat_id: int) -> int:
    try:
        val = _setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        return int(val)
    except Exception:
        return LINK_EXPIRY_MINUTES


# ── Watermark layers ──────────────────────────────────────────────────────────
#
# Three independent layers stored as JSON in bot_settings:
#   filter_wm_a_<chat_id> → Layer A (primary text)
#   filter_wm_b_<chat_id> → Layer B (secondary text)
#   filter_wm_c_<chat_id> → Layer C (sticker/image overlay)
#
# Layer schema:
#   text layers:  {"enabled": true, "text": "BeatAnime", "position": "bottom-right",
#                  "font_size": 24, "color": "#FFFFFF", "opacity": 150}
#   image layers: {"enabled": true, "file_id": "...", "url": "...",
#                  "position": "bottom-left", "scale": 0.12, "opacity": 200}

import json as _json


def _default_wm_a() -> dict:
    return {"enabled": True, "text": "BeatAnime", "position": "bottom-right",
            "font_size": 24, "color": "#FFFFFF", "opacity": 150}


def _default_wm_b() -> dict:
    return {"enabled": False, "text": "@BeatAnime", "position": "top-right",
            "font_size": 18, "color": "#AAAAAA", "opacity": 120}


def _default_wm_c() -> dict:
    """Default layer C: channel logo sticker at bottom-left, small (12% width)."""
    import os as _os
    # Try multiple path locations for Render.com / local environments
    _candidates = [
        _os.path.join(_os.path.dirname(__file__), "assets", "channel_logo.webp"),
        "/app/assets/channel_logo.webp",
        _os.path.join(_os.getcwd(), "assets", "channel_logo.webp"),
    ]
    _logo_path = next((p for p in _candidates if _os.path.exists(p)), "")
    _local_url = f"file://{_logo_path}" if _logo_path else ""
    return {
        "enabled":  bool(_logo_path),   # ON by default only when logo file found
        "file_id":  "",                  # Telegram file_id (set when admin sends sticker in bot)
        "url":      _local_url,          # Local fallback: assets/channel_logo.webp
        "position": "bottom-left",       # Bottom-left corner, small
        "scale":    0.10,                # 10% of poster width = small logo
        "opacity":  230,
    }


def get_wm_layer(chat_id: int, layer: str) -> dict:
    defaults = {"a": _default_wm_a, "b": _default_wm_b, "c": _default_wm_c}
    raw = _setting(f"filter_wm_{layer}_{chat_id}", "")
    if raw:
        try:
            return {**defaults[layer](), **_json.loads(raw)}
        except Exception:
            pass
    return defaults.get(layer, _default_wm_a)()


def set_wm_layer(chat_id: int, layer: str, data: dict) -> None:
    _set(f"filter_wm_{layer}_{chat_id}", _json.dumps(data))


# ─ JOIN button and link text ──────────────────────────────────────────────────

def _join_btn_text() -> str:
    v = _setting("env_JOIN_BTN_TEXT", JOIN_BTN_TEXT_DEFAULT)
    return _styled_plain(v)


def _here_link_text() -> str:
    v = _setting("env_HERE_IS_LINK_TEXT", HERE_LINK_TEXT_DEFAULT)
    return _styled(v)


def _link_expired_text() -> str:
    v = _setting("env_LINK_EXPIRED_TEXT", LINK_EXPIRED_TEXT_DEFAULT)
    return _styled_plain(v)


# ═════════════════════════════════════════════════════════════════════════════
#  EXPIRABLE INVITE LINK
# ═════════════════════════════════════════════════════════════════════════════

async def _make_expirable_link(bot: Any, expiry_minutes: int) -> Optional[str]:
    """Create a real Telegram invite link that expires in `expiry_minutes`."""
    if expiry_minutes <= 0:
        return PUBLIC_URL
    try:
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels()
        if not channels:
            return None
        # Try each channel until one succeeds
        for ch_data in channels:
            try:
                cid = ch_data[0] if isinstance(ch_data, (list, tuple)) else ch_data.get("channel_username")
                if not cid:
                    continue
                # Try as int first
                try:
                    cid_int = int(cid)
                except Exception:
                    cid_int = cid  # username
                expire_ts = int(datetime.now(timezone.utc).timestamp()) + (expiry_minutes * 60)
                inv = await bot.create_chat_invite_link(
                    chat_id=cid_int,
                    expire_date=expire_ts,
                    member_limit=1,
                    name=f"Filter-{int(time.time())}",
                    creates_join_request=False,
                )
                return inv.invite_link
            except Exception as exc:
                logger.debug(f"invite link for {cid}: {exc}")
    except Exception as exc:
        logger.debug(f"_make_expirable_link: {exc}")
    return None


# ═════════════════════════════════════════════════════════════════════════════
#  AUTO-DELETE
# ═════════════════════════════════════════════════════════════════════════════

async def _auto_delete(bot: Any, chat_id: int, *message_ids: int, delay: int = 300) -> None:
    """Delete one or more messages after `delay` seconds. Never raises."""
    if delay <= 0:
        return
    await asyncio.sleep(delay)
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
#  STICKER / IMAGE DOWNLOAD
# ═════════════════════════════════════════════════════════════════════════════

async def download_sticker(bot: Any, file_id: str) -> Optional[str]:
    """
    Download a Telegram sticker/image by file_id, return local path.
    Supports: static .webp stickers, .png/.jpg/.webp images.
    Animated (.tgs) stickers are skipped (can't render as PIL overlay).
    """
    if file_id in _sticker_cache:
        path = _sticker_cache[file_id]
        if os.path.exists(path):
            return path
    try:
        tg_file = await bot.get_file(file_id)
        fp = tg_file.file_path or ""
        if fp.endswith(".tgs"):
            logger.debug("Animated sticker (.tgs) not supported as watermark — skipping")
            return None
        # Determine extension
        for ext_check in (".webp", ".png", ".jpg", ".jpeg", ".gif"):
            if fp.lower().endswith(ext_check):
                ext = ext_check
                break
        else:
            ext = ".webp"  # default for stickers
        path = os.path.join(STICKER_DIR, f"{hashlib.md5(file_id.encode()).hexdigest()}{ext}")
        await tg_file.download_to_drive(path)
        _sticker_cache[file_id] = path
        return path
    except Exception as exc:
        logger.debug(f"download_sticker error: {exc}")
        return None


def _load_image_from_url(url: str) -> Optional[Any]:
    if not PIL_OK or not url:
        return None
    if url.startswith('file://'):
        return _load_image_from_path(url[7:])
    if url in _img_cache:
        try:
            return Image.open(BytesIO(_img_cache[url])).convert("RGBA")
        except Exception:
            pass
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "BeatAniVerse/2.0"})
        if r.status_code == 200:
            _img_cache[url] = r.content
            return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception as exc:
        logger.debug(f"_load_image_from_url {url}: {exc}")
    return None


def _load_image_from_path(path: str) -> Optional[Any]:
    if not PIL_OK or not path or not os.path.exists(path):
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════════════════
#  FONT HELPERS
# ═════════════════════════════════════════════════════════════════════════════

_font_cache: Dict[Tuple[str, int], Any] = {}


def _font(name: str = "poppins-regular", size: int = 20) -> Any:
    if not PIL_OK:
        return None
    key = (name, size)
    if key in _font_cache:
        return _font_cache[key]
    # Search font directory
    if os.path.isdir(FONT_DIR):
        name_lower = name.lower().replace(" ", "-").replace("_", "-")
        for fn in os.listdir(FONT_DIR):
            stem = fn.lower().replace(" ", "-").replace("_", "-").rsplit(".", 1)[0]
            if stem == name_lower or stem.startswith(name_lower):
                try:
                    f = ImageFont.truetype(os.path.join(FONT_DIR, fn), size)
                    _font_cache[key] = f
                    return f
                except Exception:
                    pass
    # Fallback chain
    for fallback in ["poppins-bold", "poppins-regular", "roboto-medium", "roboto-regular"]:
        if os.path.isdir(FONT_DIR):
            for fn in os.listdir(FONT_DIR):
                if fallback in fn.lower():
                    try:
                        f = ImageFont.truetype(os.path.join(FONT_DIR, fn), size)
                        _font_cache[key] = f
                        return f
                    except Exception:
                        pass
    try:
        f = ImageFont.load_default()
        _font_cache[key] = f
        return f
    except Exception:
        return None


# ═════════════════════════════════════════════════════════════════════════════
#  WATERMARK RENDERING — full layer compositing
# ═════════════════════════════════════════════════════════════════════════════

def _pos_xy(position: str, img_w: int, img_h: int,
             item_w: int, item_h: int, margin: int = 20) -> Tuple[int, int]:
    """Resolve position name to (x, y) pixel coordinates."""
    pos_map = {
        "center":       ((img_w - item_w) // 2,              (img_h - item_h) // 2),
        "top":          ((img_w - item_w) // 2,              margin),
        "bottom":       ((img_w - item_w) // 2,              img_h - item_h - margin),
        "left":         (margin,                              (img_h - item_h) // 2),
        "right":        (img_w - item_w - margin,            (img_h - item_h) // 2),
        "top-left":     (margin,                              margin),
        "top-right":    (img_w - item_w - margin,            margin),
        "bottom-left":  (margin,                              img_h - item_h - margin),
        "bottom-right": (img_w - item_w - margin,            img_h - item_h - margin),
    }
    return pos_map.get(position, pos_map["center"])


def _parse_color(color_str: str, opacity: int = 255) -> Tuple[int, int, int, int]:
    """Parse color string (#RRGGBB or 'white' etc.) + opacity → RGBA tuple."""
    try:
        rgb = ImageColor.getrgb(color_str)
        return (*rgb[:3], max(0, min(255, opacity)))
    except Exception:
        return (255, 255, 255, max(0, min(255, opacity)))


def _apply_text_watermark_layer(
    img: Any,
    text: str,
    position: str,
    font_size: int = 24,
    color: str = "#FFFFFF",
    opacity: int = 150,
) -> Any:
    """
    Render a text watermark layer on `img` with drop-shadow underneath.
    Returns a new RGBA image (does not modify original).
    """
    if not PIL_OK or not text:
        return img
    try:
        img = img.convert("RGBA")
        W, H = img.size
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(layer)
        fnt   = _font("poppins-bold", font_size)

        # Measure text
        try:
            bbox = draw.textbbox((0, 0), text, font=fnt)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = font_size * len(text) // 2, font_size

        x, y = _pos_xy(position, W, H, tw, th, margin=22)

        # Shadow layer (offset +2,+2, semi-transparent black)
        shadow_color = (0, 0, 0, min(180, opacity))
        draw.text((x + 2, y + 2), text, font=fnt, fill=shadow_color)

        # Glow layer (slightly blurred, same color, larger)
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        rgba = _parse_color(color, max(0, opacity - 80))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                gd.text((x + dx, y + dy), text, font=fnt, fill=rgba)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=1))
        img = Image.alpha_composite(img, glow_layer)

        # Main text
        main_color = _parse_color(color, opacity)
        draw2 = ImageDraw.Draw(layer)
        draw2.text((x, y), text, font=fnt, fill=main_color)
        return Image.alpha_composite(img, layer)
    except Exception as exc:
        logger.debug(f"text watermark layer error: {exc}")
        return img


def _apply_image_watermark_layer(
    img: Any,
    overlay: Any,
    position: str,
    scale: float = 0.12,
    opacity: int = 200,
) -> Any:
    """
    Render an image/sticker overlay layer on `img`.
    `overlay` is a PIL Image (RGBA). Scale is relative to poster width.
    """
    if not PIL_OK or overlay is None:
        return img
    try:
        img = img.convert("RGBA")
        W, H = img.size

        # Scale overlay
        ow = max(20, int(W * scale))
        oh = int(overlay.size[1] * ow / overlay.size[0])
        overlay_rs = overlay.resize((ow, oh), Image.LANCZOS)
        overlay_rs = overlay_rs.convert("RGBA")

        # Apply opacity
        if opacity < 255:
            r, g, b, a = overlay_rs.split()
            a = a.point(lambda p: int(p * opacity / 255))
            overlay_rs = Image.merge("RGBA", (r, g, b, a))

        x, y = _pos_xy(position, W, H, ow, oh, margin=18)

        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(overlay_rs, (x, y), overlay_rs)
        return Image.alpha_composite(img, layer)
    except Exception as exc:
        logger.debug(f"image watermark layer error: {exc}")
        return img


async def apply_watermark_layers(
    img: Any,
    chat_id: int,
    bot: Any = None,
) -> Any:
    """
    Apply all three watermark layers (A, B, C) to `img` based on chat settings.
    Layer C can be a Telegram sticker (downloaded on demand).
    """
    if not PIL_OK:
        return img

    # Layer A — primary text
    la = get_wm_layer(chat_id, "a")
    if la.get("enabled", True) and la.get("text"):
        img = _apply_text_watermark_layer(
            img,
            text=la["text"],
            position=la.get("position", "bottom-right"),
            font_size=int(la.get("font_size", 24)),
            color=la.get("color", "#FFFFFF"),
            opacity=int(la.get("opacity", 150)),
        )

    # Layer B — secondary text
    lb = get_wm_layer(chat_id, "b")
    if lb.get("enabled") and lb.get("text"):
        img = _apply_text_watermark_layer(
            img,
            text=lb["text"],
            position=lb.get("position", "top-right"),
            font_size=int(lb.get("font_size", 18)),
            color=lb.get("color", "#AAAAAA"),
            opacity=int(lb.get("opacity", 120)),
        )

    # Layer C — sticker / image overlay
    lc = get_wm_layer(chat_id, "c")
    # Apply if enabled OR if a file_id is set (sticker was saved)
    if lc.get("enabled") or lc.get("file_id"):
        overlay_img = None
        # Try sticker file_id first (Telegram sticker)
        fid = lc.get("file_id", "")
        if fid and bot:
            local = await download_sticker(bot, fid)
            if local:
                overlay_img = _load_image_from_path(local)
        # Fallback to URL
        if overlay_img is None:
            url = lc.get("url", "")
            if url:
                overlay_img = _load_image_from_url(url)

        if overlay_img:
            img = _apply_image_watermark_layer(
                img,
                overlay=overlay_img,
                position=lc.get("position", "bottom-left"),  # default: bottom-left, small
                scale=float(lc.get("scale", 0.12)),           # 12% of poster width = small
                opacity=int(lc.get("opacity", 220)),
            )

    return img


# ═════════════════════════════════════════════════════════════════════════════
#  DATA FETCHING (async wrappers around poster_engine)
# ═════════════════════════════════════════════════════════════════════════════

async def _fetch_data(title: str, media_type: str) -> Optional[Dict]:
    loop = asyncio.get_event_loop()
    try:
        from poster_engine import (
            _anilist_anime, _anilist_manga, _tmdb_movie, _tmdb_tv
        )
        fn_map = {
            "ANIME": _anilist_anime,
            "MANGA": _anilist_manga,
            "MOVIE": _tmdb_movie,
            "TV":    _tmdb_tv,
        }
        fn = fn_map.get(media_type, _anilist_anime)
        return await loop.run_in_executor(None, fn, title)
    except Exception as exc:
        logger.debug(f"_fetch_data error: {exc}")
        return None


async def _generate_poster_data(
    title: str,
    template: str,
    media_type: str,
    chat_id: int,
    bot: Any = None,
) -> Tuple[Optional[BytesIO], str, Optional[Dict]]:
    """
    Generate full layered poster with all 3 watermark layers applied.
    Returns (BytesIO | None, caption_html, raw_data | None).
    """
    loop = asyncio.get_event_loop()

    from poster_engine import (
        _make_poster,
        _build_anime_data, _build_manga_data,
        _build_movie_data, _build_tv_data,
        _get_settings,
    )

    # Fetch data
    data = await _fetch_data(title, media_type)
    if not data:
        return None, "", None

    # Build poster params
    build_fn = {
        "ANIME": _build_anime_data,
        "MANGA": _build_manga_data,
        "MOVIE": _build_movie_data,
        "TV":    _build_tv_data,
    }.get(media_type, _build_anime_data)

    p_title, p_native, p_status, p_rows, p_desc, p_cover, p_score = build_fn(data)

    cat = {"ANIME": "anime", "MANGA": "manga", "MOVIE": "movie", "TV": "tvshow"}.get(media_type, "anime")
    settings = _get_settings(cat)
    wm_text = settings.get("watermark_text")
    wm_pos  = settings.get("watermark_position", "center")

    # Generate base poster (runs PIL in executor — non-blocking)
    def _make():
        return _make_poster(
            template, p_title, p_native, p_status, p_rows, p_desc,
            p_cover, p_score, wm_text, wm_pos, None, "bottom",
        )

    poster_buf = await loop.run_in_executor(None, _make)

    # Apply filter-specific watermark layers A, B, C on top
    if poster_buf and PIL_OK:
        try:
            poster_buf.seek(0)
            base_img = await loop.run_in_executor(None, lambda: Image.open(poster_buf).convert("RGBA"))
            final_img = await apply_watermark_layers(base_img, chat_id, bot=bot)
            out = BytesIO()
            await loop.run_in_executor(None, lambda: final_img.convert("RGB").save(out, format="JPEG", quality=92))
            out.seek(0)
            out.name = f"poster_{template}_{title[:20].replace(' ', '_')}.jpg"
            poster_buf = out
        except Exception as exc:
            logger.debug(f"watermark layer compositing error: {exc}")
            poster_buf.seek(0)

    # Build caption (HTML, respects global text style)
    genres_list = data.get("genres") or []
    genres_str  = ", ".join(genres_list[:4])
    branding    = settings.get("branding", "")
    site_url    = data.get("siteUrl", "")

    # Build info lines
    info_html = ""
    for label, value in (p_rows or [])[:5]:
        if value and str(value) not in ("-", "N/A", "None", "?", "0"):
            info_html += f"<b>{_styled_plain(label)}:</b> {_styled(html.escape(str(value)))}\n"

    caption_raw = (
        f"<b>{html.escape(p_title)}</b>\n"
        + (f"<i>{_styled(html.escape(genres_str))}</i>\n" if genres_str else "")
        + (f"\n{info_html}" if info_html else "")
        + (f"\n<b>{_styled(html.escape(branding))}</b>\n" if branding else "")
        + f"\n{_styled_plain('via')} @BeatAnime"
    )
    if len(caption_raw) > 1024:
        caption_raw = caption_raw[:1020] + "…"

    return poster_buf, caption_raw, data


# ═════════════════════════════════════════════════════════════════════════════
#  SAVE TO POSTER DB CHANNEL
# ═════════════════════════════════════════════════════════════════════════════

async def _save_to_poster_channel(
    bot: Any, photo_buf: BytesIO, caption: str, template: str
) -> Optional[Tuple[str, int]]:
    if not POSTER_DB_CHANNEL:
        return None
    try:
        photo_buf.seek(0)
        msg = await bot.send_photo(
            chat_id=POSTER_DB_CHANNEL,
            photo=photo_buf,
            caption=f"<b>Poster Cache</b> | <code>{html.escape(template)}</code>\n\n{caption}",
            parse_mode="HTML",
        )
        if msg.photo:
            return msg.photo[-1].file_id, msg.message_id
    except Exception as exc:
        logger.debug(f"save_to_poster_channel error: {exc}")
    return None


# ═════════════════════════════════════════════════════════════════════════════
#  MODE 1 — TEXT DELIVERY
# ═════════════════════════════════════════════════════════════════════════════

async def _deliver_text_mode(
    bot: Any,
    chat_id: int,
    title: str,
    reply_to: Optional[int],
    expiry_minutes: int,
    auto_delete_seconds: int,
) -> bool:
    """
    Deliver a text-only message: "here is your link" + expirable join button.
    Auto-deletes after `auto_delete_seconds`.
    """
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    join_url  = await _make_expirable_link(bot, expiry_minutes) or PUBLIC_URL
    join_text = _join_btn_text()
    here_text = _here_link_text()

    text = (
        f"<b>{html.escape(here_text)}</b>\n\n"
        f"<b>{_styled(html.escape(title))}</b>\n\n"
        f"<i>{_styled_plain('Link expires in')} {expiry_minutes} {_styled_plain('minutes.')}</i>"
    )

    kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=join_url)]])

    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=kb,
            reply_to_message_id=reply_to,
            disable_web_page_preview=True,
        )
        if msg and auto_delete_seconds > 0:
            asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, delay=auto_delete_seconds))
        return True
    except Exception as exc:
        logger.error(f"text mode delivery error: {exc}")
        return False


# ═════════════════════════════════════════════════════════════════════════════
#  MODE 2 — POSTER DELIVERY
# ═════════════════════════════════════════════════════════════════════════════

async def _deliver_poster_mode(
    bot: Any,
    chat_id: int,
    title: str,
    template: str,
    media_type: str,
    reply_to: Optional[int],
    expiry_minutes: int,
    auto_delete_seconds: int,
) -> bool:
    """
    Deliver a fully layered poster + info caption + expirable join button.
    Auto-deletes after `auto_delete_seconds`.
    """
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    # ── Check cache ───────────────────────────────────────────────────────────
    cached = _get_cached_poster(title, template)
    if cached and cached.get("file_id"):
        try:
            join_url  = await _make_expirable_link(bot, expiry_minutes) or PUBLIC_URL
            join_text = _join_btn_text()
            caption   = cached.get("caption", "")
            site_url  = ""  # not stored — omit info button from cache hit

            kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=join_url)]])
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=cached["file_id"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
                reply_to_message_id=reply_to,
            )
            if msg and auto_delete_seconds > 0:
                asyncio.create_task(_auto_delete(bot, chat_id, msg.message_id, delay=auto_delete_seconds))
            return True
        except Exception:
            pass   # Cache miss or expired file_id → regenerate

    # ── Placeholder ───────────────────────────────────────────────────────────
    placeholder = None
    try:
        placeholder = await bot.send_message(
            chat_id=chat_id,
            text=_styled(f"<b>Generating poster for:</b> <code>{html.escape(title)}</code>"),
            parse_mode="HTML",
            reply_to_message_id=reply_to,
        )
    except Exception:
        pass

    # ── Generate ──────────────────────────────────────────────────────────────
    try:
        poster_buf, caption, data = await asyncio.wait_for(
            _generate_poster_data(title, template, media_type, chat_id, bot=bot),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        if placeholder:
            try:
                await placeholder.edit_text(
                    _styled("<b>Poster generation timed out. Try again.</b>"),
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return False
    except Exception as exc:
        logger.error(f"poster generation error: {exc}")
        if placeholder:
            try:
                await placeholder.edit_text(
                    _styled(f"<b>Error generating poster:</b> <code>{html.escape(str(exc)[:100])}</code>"),
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return False

    if not (poster_buf or data):
        if placeholder:
            try:
                await placeholder.edit_text(
                    _styled(f"<b>Not found:</b> <code>{html.escape(title)}</code>"),
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return False

    # Delete placeholder
    if placeholder:
        try:
            await placeholder.delete()
        except Exception:
            pass

    # ── Build join link + keyboard ────────────────────────────────────────────
    join_url   = await _make_expirable_link(bot, expiry_minutes) or PUBLIC_URL
    join_text  = _join_btn_text()
    site_url   = (data or {}).get("siteUrl", "")

    btns = [[InlineKeyboardButton(join_text, url=join_url)]]
    if site_url:
        btns[0].append(InlineKeyboardButton(_styled_plain("Info"), url=site_url))
    kb = InlineKeyboardMarkup(btns)

    # ── Send ──────────────────────────────────────────────────────────────────
    sent_msg = None
    if poster_buf:
        poster_buf.seek(0)
        try:
            sent_msg = await bot.send_photo(
                chat_id=chat_id,
                photo=poster_buf,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
                reply_to_message_id=reply_to,
            )
        except Exception as exc:
            logger.error(f"poster send error: {exc}")

    # Text fallback if image send failed
    if not sent_msg:
        text_fallback = (
            caption
            + (f"\n\n<a href='{site_url}'>" + _styled_plain("Info") + "</a>" if site_url else "")
        )
        try:
            sent_msg = await bot.send_message(
                chat_id=chat_id,
                text=text_fallback,
                parse_mode="HTML",
                reply_markup=kb,
                disable_web_page_preview=bool(site_url),
                reply_to_message_id=reply_to,
            )
        except Exception as exc:
            logger.error(f"text fallback send error: {exc}")

    if not sent_msg:
        return False

    # ── Auto-delete ───────────────────────────────────────────────────────────
    if auto_delete_seconds > 0:
        asyncio.create_task(
            _auto_delete(bot, chat_id, sent_msg.message_id, delay=auto_delete_seconds)
        )

    # ── Save to poster DB channel + cache ─────────────────────────────────────
    file_id = None
    channel_msg_id = 0
    if poster_buf and POSTER_DB_CHANNEL:
        result = await _save_to_poster_channel(bot, poster_buf, caption, template)
        if result:
            file_id, channel_msg_id = result
    elif sent_msg.photo:
        file_id = sent_msg.photo[-1].file_id

    if file_id:
        _save_poster_cache(
            title=title, template=template, file_id=file_id,
            channel_msg_id=channel_msg_id, channel_id=POSTER_DB_CHANNEL,
            caption=caption,
        )

    return True


# ═════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT — called from group_message_handler in bot.py
# ═════════════════════════════════════════════════════════════════════════════

async def get_or_generate_poster(
    bot: Any,
    chat_id: int,
    title: str,
    template: str        = "ani",
    media_type: str      = "ANIME",
    reply_to_message_id: Optional[int] = None,
    auto_delete_seconds: int = 300,
    link_expiry_minutes: int = 5,
) -> bool:
    """
    Main entry point for filter-triggered poster delivery.

    Reads the chat's delivery mode from DB:
      • "text"   → MODE 1: text-only "here is your link" + join button
      • "poster" → MODE 2: full layered poster + caption + join button

    Both modes:
      ✅ Expirable Telegram invite link
      ✅ Auto-delete after auto_delete_seconds
      ✅ Global text style (small caps if enabled)
      ✅ All 3 watermark layers applied (poster mode only)
    """
    mode = get_filter_mode(chat_id)

    if mode == "text":
        return await _deliver_text_mode(
            bot=bot,
            chat_id=chat_id,
            title=title,
            reply_to=reply_to_message_id,
            expiry_minutes=link_expiry_minutes,
            auto_delete_seconds=auto_delete_seconds,
        )
    else:
        return await _deliver_poster_mode(
            bot=bot,
            chat_id=chat_id,
            title=title,
            template=template,
            media_type=media_type,
            reply_to=reply_to_message_id,
            expiry_minutes=link_expiry_minutes,
            auto_delete_seconds=auto_delete_seconds,
        )


# ═════════════════════════════════════════════════════════════════════════════
#  SETTINGS PANEL BUILDERS (used by bot.py admin panel)
# ═════════════════════════════════════════════════════════════════════════════

def get_filter_poster_settings_text(chat_id: int = 0) -> str:
    mode     = get_filter_mode(chat_id)
    enabled  = get_filter_poster_enabled(chat_id)
    template = get_filter_template(chat_id)
    del_sec  = get_auto_delete_seconds(chat_id)
    exp_min  = get_link_expiry_minutes(chat_id)
    cached   = _get_cache_count()
    channel  = f"<code>{POSTER_DB_CHANNEL}</code>" if POSTER_DB_CHANNEL else "Not set"

    # Watermark layer summaries
    la = get_wm_layer(chat_id, "a")
    lb = get_wm_layer(chat_id, "b")
    lc = get_wm_layer(chat_id, "c")

    la_info = f"{la.get('text','—')} @ {la.get('position','?')}" if la.get("enabled") else "Off"
    lb_info = f"{lb.get('text','—')} @ {lb.get('position','?')}" if lb.get("enabled") else "Off"
    lc_info = f"Sticker/Image @ {lc.get('position','?')}" if lc.get("enabled") else "Off"

    mode_label = _styled_plain("TEXT (link only)") if mode == "text" else _styled_plain("POSTER (full card)")

    return (
        "<b>" + _styled_plain("FILTER POSTER SETTINGS") + "</b>\n\n"
        + "<blockquote>"
        + f"<b>{_styled_plain('Status')}:</b> {'🟢 ' + _styled_plain('On') if enabled else '🔴 ' + _styled_plain('Off')}\n"
        + f"<b>{_styled_plain('Mode')}:</b> {mode_label}\n"
        + f"<b>{_styled_plain('Template')}:</b> <code>{template}</code>\n"
        + f"<b>{_styled_plain('Auto-Delete')}:</b> {del_sec}s ({del_sec // 60} {_styled_plain('min')})\n"
        + f"<b>{_styled_plain('Link Expiry')}:</b> {exp_min} {_styled_plain('min')}\n"
        + f"<b>{_styled_plain('Poster DB Channel')}:</b> {channel}\n"
        + f"<b>{_styled_plain('Cached Posters')}:</b> <code>{cached}</code>\n"
        + "</blockquote>\n\n"
        + "<b>" + _styled_plain("WATERMARK LAYERS") + "</b>\n"
        + "<blockquote>"
        + f"<b>A ({_styled_plain('Primary text')}):</b> {_styled_plain(la_info)}\n"
        + f"<b>B ({_styled_plain('Secondary text')}):</b> {_styled_plain(lb_info)}\n"
        + f"<b>C ({_styled_plain('Sticker/Image')}):</b> {_styled_plain(lc_info)}\n"
        + "</blockquote>"
    )


def build_filter_poster_settings_keyboard(chat_id: int = 0) -> Any:
    """Build the 3x3 admin panel keyboard for filter poster settings."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton

    enabled  = get_filter_poster_enabled(chat_id)
    mode     = get_filter_mode(chat_id)
    template = get_filter_template(chat_id)

    def _b(label: str, cb: str) -> InlineKeyboardButton:
        # Use the bot's _style_label if available — else raw
        try:
            from bot import _style_label
            return InlineKeyboardButton(_style_label(label), callback_data=cb)
        except Exception:
            return InlineKeyboardButton(label, callback_data=cb)

    tmpl_row1 = [_b("ani",   f"fp_tmpl_{chat_id}_ani"),
                 _b("crun",  f"fp_tmpl_{chat_id}_crun"),
                 _b("net",   f"fp_tmpl_{chat_id}_net")]
    tmpl_row2 = [_b("dark",  f"fp_tmpl_{chat_id}_dark"),
                 _b("light", f"fp_tmpl_{chat_id}_light"),
                 _b("mod",   f"fp_tmpl_{chat_id}_mod")]

    mode_label = "MODE: POSTER" if mode == "poster" else "MODE: TEXT"

    rows = [
        [InlineKeyboardButton(
            ("🟢 " if enabled else "🔴 ") + ("ON" if enabled else "OFF"),
            callback_data=f"fp_toggle_{chat_id}",
        ),
        InlineKeyboardButton(mode_label, callback_data=f"fp_mode_toggle_{chat_id}")],
        tmpl_row1,
        tmpl_row2,
        [_b("WM LAYER A", f"fp_wm_a_{chat_id}"),
         _b("WM LAYER B", f"fp_wm_b_{chat_id}"),
         _b("WM LAYER C", f"fp_wm_c_{chat_id}")],
        [_b("AUTO DEL", "fp_set_autodel"),
         _b("LINK EXPIRY", "fp_set_linkexpiry"),
         _b("♻️ CACHE", "fp_view_cache")],
        [_b("CLEAR CACHE", "fp_clear_cache"),
         _b("DB CHANNEL", "fp_channel_info")],
        [_b("✏️ JOIN BTN TEXT", f"fp_set_join_btn_{chat_id}"),
         _b("⏱ LINK EXPIRY", "fp_set_linkexpiry")],
        # Pre-generate posters for all registered anime channel links
        [InlineKeyboardButton(
            "🎌 PRE-GEN ALL POSTERS",
            callback_data=f"fp_pregen_all_{chat_id}",
        )],
        [InlineKeyboardButton("🔙 BACK", callback_data="admin_settings"),
         InlineKeyboardButton("CLOSE", callback_data="close_message")],
    ]
    return InlineKeyboardMarkup(rows)


def _get_cache_count() -> int:
    try:
        from database_dual import _pg_exec, _MG
        row = _pg_exec("SELECT COUNT(*) FROM poster_cache")
        if row:
            return row[0]
        if _MG.db is not None:
            return _MG.db.poster_cache.count_documents({})
    except Exception:
        pass
    return len(_poster_cache)


def _get_filter_poster_enabled(chat_id: int) -> bool:
    return get_filter_poster_enabled(chat_id)


def _set_filter_poster_enabled(chat_id: int, enabled: bool) -> None:
    set_filter_poster_enabled(chat_id, enabled)


def _get_default_poster_template(chat_id: int) -> str:
    return get_filter_template(chat_id)


def _set_default_poster_template(chat_id: int, template: str) -> None:
    set_filter_template(chat_id, template)


def _clear_poster_cache() -> int:
    count = _get_cache_count()
    _poster_cache.clear()
    try:
        from database_dual import _pg_run, _MG
        _pg_run("DELETE FROM poster_cache")
        if _MG.db is not None:
            _MG.db.poster_cache.delete_many({})
    except Exception:
        pass
    return count
