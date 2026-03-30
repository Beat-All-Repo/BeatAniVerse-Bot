# ====================================================================
# PLACE AT: /app/poster_engine.py
# ACTION: Replace existing file
# ====================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Poster Engine
==================================
Full layered poster generation system.

Features:
  ✅ 12 poster templates: ani, anim, crun, net, netm, light, lightm,
                           dark, darkm, mod, modm, netcr
  ✅ Layered image compositing:
       Layer 0 — gradient background
       Layer 1 — blur + dark cover fill
       Layer 2 — cover art (rounded corners + shadow)
       Layer 3 — overlay gradient (bottom fade)
       Layer 4 — logo/watermark (configurable position)
       Layer 5 — text (title, metadata, description)
       Layer 6 — accent bar + score badge
  ✅ Per-category watermark text + position from DB settings
  ✅ Premium system (Bronze/Silver/Gold tiers) with daily limits
  ✅ ALL commands admin-only. Users can only see /my_plan and /plans.
  ✅ AniList API (anime + manga), TMDB (movie + tvshow), MangaDex fallback

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import os
import re
import html
import time
import hashlib
import logging
import traceback
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any

import requests

try:
    from PIL import (Image, ImageDraw, ImageFont, ImageFilter,
                     ImageEnhance, ImageOps)
    PIL_OK = True
except ImportError:
    PIL_OK = False

from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ── Text style ────────────────────────────────────────────────────────────────
try:
    from text_style import apply_style as _apply_poster_style
except ImportError:
    def _apply_poster_style(t): return t

# ── Env ────────────────────────────────────────────────────────────────────────
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0") or os.getenv("OWNER_ID", "0"))
OWNER_ID: int = int(os.getenv("OWNER_ID", str(ADMIN_ID)))
PUBLIC_ANIME_CHANNEL_URL: str = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

# ── Paths ──────────────────────────────────────────────────────────────────────
_BASE = Path(__file__).parent
FONT_DIR = _BASE / "fonts"
ICON_DIR = _BASE / "iconspng"

# ── Font cache ─────────────────────────────────────────────────────────────────
_FONT_MAP: Dict[str, Path] = {}


def _load_fonts() -> None:
    if not FONT_DIR.exists():
        return
    for fp in FONT_DIR.iterdir():
        if fp.suffix.lower() in (".ttf", ".otf"):
            key = fp.stem.lower().replace(" ", "-").replace("_", "-")
            _FONT_MAP[key] = fp


_load_fonts()


def _font(name: str, size: int) -> Any:
    """Get PIL ImageFont by name and size. Falls back gracefully."""
    if not PIL_OK:
        return None
    key = name.lower().replace(" ", "-").replace("_", "-")
    path = _FONT_MAP.get(key)
    if not path:
        for fallback in ["poppins-bold", "poppins-regular", "bebas-neue-bold",
                         "roboto-medium", "roboto-regular"]:
            if fallback in _FONT_MAP:
                path = _FONT_MAP[fallback]
                break
    try:
        if path:
            return ImageFont.truetype(str(path), size)
    except Exception:
        pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


# ── API cache ──────────────────────────────────────────────────────────────────
_API_CACHE: Dict[str, Any] = {}
_API_TTL = 300


def _cache_get(k: str) -> Optional[Any]:
    e = _API_CACHE.get(k)
    return e["v"] if e and time.time() - e["t"] < _API_TTL else None


def _cache_set(k: str, v: Any) -> None:
    _API_CACHE[k] = {"v": v, "t": time.time()}
    if len(_API_CACHE) > 400:
        oldest = min(_API_CACHE, key=lambda x: _API_CACHE[x]["t"])
        _API_CACHE.pop(oldest, None)


# ── AniList ────────────────────────────────────────────────────────────────────
_AL_URL = "https://graphql.anilist.co"
_AL_ABBR = {
    # Shortforms
    "aot": "attack on titan", "bnha": "my hero academia", "mha": "my hero academia",
    "hxh": "hunter x hunter", "dbs": "dragon ball super", "dbz": "dragon ball z",
    "op": "one piece", "fma": "fullmetal alchemist", "snk": "attack on titan",
    "jjk": "jujutsu kaisen", "csm": "chainsaw man",
    # English → Romaji mappings to help AniList find correct result
    "demon slayer": "Kimetsu no Yaiba",
    "attack on titan": "Shingeki no Kyojin",
    "my hero academia": "Boku no Hero Academia",
    "jujutsu kaisen": "Jujutsu Kaisen",
    "one punch man": "One Punch-Man",
    "dr stone": "Dr. Stone",
    "dr. stone": "Dr. Stone",
    "promised neverland": "Yakusoku no Neverland",
    "the promised neverland": "Yakusoku no Neverland",
    "your lie in april": "Shigatsu wa Kimi no Uso",
    "a silent voice": "Koe no Katachi",
    "spirited away": "Sen to Chihiro no Kamikakushi",
    "howls moving castle": "Howl no Ugoku Shiro",
    "princess mononoke": "Mononoke Hime",
    "violet evergarden": "Violet Evergarden",
    "sword art online": "Sword Art Online",
    "re zero": "Re:Zero kara Hajimeru Isekai Seikatsu",
    "rezero": "Re:Zero kara Hajimeru Isekai Seikatsu",
    "that time i got reincarnated as a slime": "Tensei shitara Slime Datta Ken",
    "slime": "Tensei shitara Slime Datta Ken",
    "black clover": "Black Clover",
    "tokyo revengers": "Tokyo Revengers",
    "blue lock": "Blue Lock",
    "chainsaw man": "Chainsaw Man",
    "spy x family": "Spy x Family",
    "bleach": "Bleach",
    "naruto": "Naruto",
    "dragon ball": "Dragon Ball Z",
    "made in abyss": "Made in Abyss",
    "frieren": "Sousou no Frieren",
    "oshi no ko": "Oshi no Ko",
    "vinland saga": "Vinland Saga",
    "mushoku tensei": "Mushoku Tensei: Jobless Reincarnation",
    "overlord": "Overlord",
    "no game no life": "No Game No Life",
    "hunter x hunter": "Hunter x Hunter (2011)",
    "fullmetal alchemist": "Fullmetal Alchemist: Brotherhood",
    "fmab": "Fullmetal Alchemist: Brotherhood",
    "steins gate": "Steins;Gate",
    "death note": "Death Note",
    "code geass": "Code Geass: Hangyaku no Lelouch",
    "evangelion": "Neon Genesis Evangelion",
    "nge": "Neon Genesis Evangelion",
    "cowboy bebop": "Cowboy Bebop",
    "one piece": "One Piece",
    "fairy tail": "Fairy Tail",
    "fate": "Fate/stay night: Unlimited Blade Works",
    "danmachi": "Dungeon ni Deai wo Motomeru no wa Machigatteiru Darou ka",
    "konosuba": "Kono Subarashii Sekai ni Shukufuku wo!",
    "sao": "Sword Art Online",
    "danganronpa": "Danganronpa",
    "classroom of elite": "Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "cote": "Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "eminence in shadow": "Kage no Jitsuryokusha ni Naritakute!",
    "tensura": "Tensei shitara Slime Datta Ken",
    "shield hero": "Tate no Yuusha no Nariagari",
    "rising of shield hero": "Tate no Yuusha no Nariagari",
    "demon slayer swordsmith": "Kimetsu no Yaiba: Katanakaji no Sato-hen",
    "kny": "Kimetsu no Yaiba",
    "ds": "Kimetsu no Yaiba",
}
_ANIME_GQL = """
query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl
  title{romaji english native}
  description(asHtml:false)
  coverImage{extraLarge large medium}
  bannerImage format status season seasonYear
  episodes duration averageScore popularity
  genres
  studios(isMain:true){nodes{name}}
  startDate{year month day}
  nextAiringEpisode{episode timeUntilAiring}
  countryOfOrigin isAdult
}}"""
_MANGA_GQL = """
query($s:String){Media(search:$s,type:MANGA,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl
  title{romaji english native}
  description(asHtml:false)
  coverImage{extraLarge large medium}
  format status chapters volumes averageScore popularity
  genres
  startDate{year month day}
  countryOfOrigin
}}"""


def _al_query(gql: str, search: str) -> Optional[Dict]:
    """
    Smart AniList search with multi-strategy fallback.
    Prevents wrong results (e.g. 'Demon Slayer' returning 'Onigiri').
    Strategy:
      1. Try abbreviated/mapped query (e.g. 'demon slayer' → 'Kimetsu no Yaiba')
      2. Try original query as-is
      3. Try title-cased version
    All use sort:[SEARCH_MATCH,POPULARITY_DESC] in GQL to prefer popular anime.
    """
    key = "al:" + hashlib.md5(f"{gql}{search}".encode()).hexdigest()
    cached = _cache_get(key)
    if cached is not None:
        return cached

    search_clean = search.strip()
    # Map abbreviation or English → Romaji
    q_mapped = _AL_ABBR.get(search_clean.lower(), search_clean)

    # Build list of queries to try in order
    queries_to_try = [q_mapped]
    if q_mapped.lower() != search_clean.lower():
        queries_to_try.append(search_clean)        # original
    if search_clean != search_clean.title():
        queries_to_try.append(search_clean.title()) # Title Case

    for q in queries_to_try:
        try:
            r = requests.post(
                _AL_URL,
                json={"query": gql, "variables": {"s": q}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=12,
            )
            if r.status_code == 200:
                result = r.json().get("data", {}).get("Media")
                if result:
                    # Sanity check: verify result title loosely matches query
                    # Prevents returning completely unrelated anime
                    res_titles = [
                        (result.get("title") or {}).get("english", "") or "",
                        (result.get("title") or {}).get("romaji", "") or "",
                        (result.get("title") or {}).get("native", "") or "",
                    ]
                    search_words = set(search_clean.lower().split())
                    # If search has 2+ words, at least one must appear in result titles
                    if len(search_words) >= 2:
                        res_text = " ".join(res_titles).lower()
                        word_match = any(w in res_text for w in search_words if len(w) > 3)
                        if not word_match:
                            logger.debug(f"AniList sanity check failed: '{q}' → '{res_titles[0]}', trying next")
                            continue
                    _cache_set(key, result)
                    return result
        except Exception as exc:
            logger.debug(f"AniList query failed for '{q}': {exc}")

    return None


def _anilist_anime(q: str) -> Optional[Dict]:
    return _al_query(_ANIME_GQL, q)


def _anilist_manga(q: str) -> Optional[Dict]:
    return _al_query(_MANGA_GQL, q)


# ── TMDB ───────────────────────────────────────────────────────────────────────
_TMDB_BASE = "https://api.themoviedb.org/3"
_TMDB_IMG = "https://image.tmdb.org/t/p"


def _tmdb(endpoint: str, params: dict = None) -> Optional[Dict]:
    if not TMDB_API_KEY:
        return None
    p = {"api_key": TMDB_API_KEY}
    if params:
        p.update(params)
    try:
        r = requests.get(f"{_TMDB_BASE}{endpoint}", params=p, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _tmdb_movie(q: str) -> Optional[Dict]:
    r = _tmdb("/search/movie", {"query": q, "language": "en-US"})
    if r and r.get("results"):
        return _tmdb(f"/movie/{r['results'][0]['id']}", {"language": "en-US", "append_to_response": "credits"})
    return None


def _tmdb_tv(q: str) -> Optional[Dict]:
    r = _tmdb("/search/tv", {"query": q, "language": "en-US"})
    if r and r.get("results"):
        return _tmdb(f"/tv/{r['results'][0]['id']}", {"language": "en-US", "append_to_response": "credits"})
    return None


def _tmdb_poster(path: str) -> str:
    return f"{_TMDB_IMG}/w500{path}" if path else ""


# ── Text helpers ───────────────────────────────────────────────────────────────

def _clean(text: str, max_len: int = 300) -> str:
    if not text:
        return "No description available."
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _wrap(text: str, max_chars: int = 60) -> List[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if len(test) > max_chars:
            if line:
                lines.append(line)
            line = w
        else:
            line = test
    if line:
        lines.append(line)
    return lines


# ── Image helpers ──────────────────────────────────────────────────────────────

def _dl(url: str) -> Optional[Any]:
    if not PIL_OK or not url:
        return None
    key = "img:" + hashlib.md5(url.encode()).hexdigest()
    cached = _cache_get(key)
    if cached:
        return cached
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "BeatAniVerse/2.0"})
        if r.status_code == 200:
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            _cache_set(key, img)
            return img
    except Exception:
        pass
    return None


def _rounded_paste(base: Any, overlay: Any, pos: Tuple, radius: int = 18) -> Any:
    """Paste overlay onto base at pos with rounded corners."""
    mask = Image.new("L", overlay.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([(0, 0), overlay.size], radius=radius, fill=255)
    base.paste(overlay, pos, mask)
    return base


def _draw_shadow(draw, x, y, w, h, radius=18, color=(0, 0, 0, 80), offset=8):
    draw.rounded_rectangle(
        [(x + offset, y + offset), (x + w + offset, y + h + offset)],
        radius=radius, fill=color,
    )


def _score_badge(draw, x, y, score, accent_rgb):
    r = 38
    draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(*accent_rgb, 230))
    draw.ellipse([(x - r + 2, y - r + 2), (x + r - 2, y + r - 2)],
                 outline=(255, 255, 255, 120), width=2)
    f = _font("poppins-bold", 16)
    draw.text((x, y), f"{score}", fill=(255, 255, 255), font=f, anchor="mm")


# ── TEMPLATE PALETTE ──────────────────────────────────────────────────────────

TEMPLATES = {
    # Anime templates
    "ani":   {"bg": (8, 12, 28),   "accent": (31, 119, 210), "text": (240, 245, 255), "logo": "anilist_logo"},
    "crun":  {"bg": (22, 8, 0),    "accent": (249, 130, 0),  "text": (255, 248, 240), "logo": "crunchyroll_logo"},
    "net":   {"bg": (10, 10, 10),  "accent": (229, 9, 20),   "text": (255, 255, 255), "logo": "netflix_logo"},
    "light": {"bg": (240, 248, 255),"accent": (50, 110, 220), "text": (15, 20, 50),   "logo": None},
    "dark":  {"bg": (10, 8, 18),   "accent": (138, 43, 226), "text": (235, 228, 255), "logo": None},
    "netcr": {"bg": (8, 4, 4),     "accent": (220, 30, 30),  "text": (255, 255, 255), "logo": "netflix_logo"},
    "mod":   {"bg": (4, 10, 20),   "accent": (0, 198, 160),  "text": (230, 255, 250), "logo": None},
    # Manga templates
    "anim":  {"bg": (6, 18, 10),   "accent": (40, 200, 80),  "text": (230, 255, 235), "logo": "anilist_logo"},
    "netm":  {"bg": (10, 10, 10),  "accent": (229, 9, 20),   "text": (255, 255, 255), "logo": "netflix_logo"},
    "lightm":{"bg": (255, 252, 238),"accent": (200, 95, 0),  "text": (35, 20, 5),    "logo": None},
    "darkm": {"bg": (8, 5, 16),    "accent": (175, 60, 255), "text": (240, 228, 255), "logo": None},
    "modm":  {"bg": (4, 8, 20),    "accent": (0, 160, 230),  "text": (225, 245, 255), "logo": None},
    # Reference-image templates (distinct layouts, not just colour changes)
    "stream": {"bg": (8, 10, 22),  "accent": (229, 9, 20),   "text": (255, 255, 255), "logo": None},  # Img1 Netflix-style
    "vessel": {"bg": (12, 14, 30), "accent": (50, 100, 220), "text": (240, 245, 255), "logo": None},  # Img2 Split minimal
    "splash": {"bg": (5, 5, 8),    "accent": (200, 180, 255),"text": (255, 255, 255), "logo": None},  # Img3 Full-bleed cinematic
    "od3n":   {"bg": (12, 12, 14), "accent": (220, 190, 60), "text": (220, 222, 228), "logo": None},  # Img4 Character-center
}

# ── LAYERED POSTER GENERATION ──────────────────────────────────────────────────

W, H = 1280, 720   # landscape (YouTube-thumbnail) dimensions


def _make_poster(
    template: str,
    title: str,
    native_title: str,
    status: str,
    info_rows: List[Tuple[str, str]],
    desc: str,
    cover_url: str,
    score: Any,
    watermark_text: Optional[str],
    watermark_pos: str,
    logo_file_id: Optional[str],
    logo_pos: str,
) -> Optional[BytesIO]:
    """
    Landscape poster generator — 1280×720 (YouTube thumbnail ratio).
    Layout mirrors the reference image:
      LEFT  — blurred full-bleed BG, genre tags, big title, description, action buttons
      RIGHT — cover art with fade, episode/score card (bottom-right), channel branding (top-right)
    """
    if not PIL_OK:
        return None

    # ── Route to distinct layout functions for reference-image templates ──────
    _branding = watermark_text or ""
    if template == "stream":
        return _make_stream(title, native_title, status, info_rows, desc,
                            cover_url, score, watermark_text, _branding)
    if template == "vessel":
        return _make_vessel(title, native_title, status, info_rows, desc,
                            cover_url, score, watermark_text, _branding)
    if template == "splash":
        return _make_splash(title, native_title, status, info_rows, desc,
                            cover_url, score, watermark_text, _branding)
    if template == "od3n":
        return _make_od3n(title, native_title, status, info_rows, desc,
                          cover_url, score, watermark_text, _branding)

    # ── Original palette-based layout (all other templates) ──────────────────
    t = TEMPLATES.get(template, TEMPLATES["ani"])
    bg_rgb  = t["bg"]
    acc_rgb = t["accent"]
    txt_rgb = t["text"]

    # ── Layer 0: Solid dark background ────────────────────────────────────────
    img = Image.new("RGBA", (W, H), (*bg_rgb, 255))

    # ── Layer 1: Blurred full-bleed cover as BG ───────────────────────────────
    cover_raw = _dl(cover_url)
    if cover_raw:
        try:
            bg_c = cover_raw.copy().resize((W, H), Image.LANCZOS)
            bg_c = bg_c.filter(ImageFilter.GaussianBlur(radius=32))
            dark = Image.new("RGBA", (W, H), (0, 0, 0, 185))
            img  = Image.alpha_composite(img, bg_c.convert("RGBA"))
            img  = Image.alpha_composite(img, dark)
        except Exception:
            pass

    # ── Layer 2: Left-side gradient (darken left half for text readability) ───
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd   = ImageDraw.Draw(fade)
    FADE_W = 750
    for x in range(FADE_W):
        alpha = int(145 * (1 - x / FADE_W))
        fd.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
    img  = Image.alpha_composite(img, fade)
    draw = ImageDraw.Draw(img)

    # ── Layer 3: Cover art on RIGHT side (fills right portion, fades left) ────
    RIGHT_START = 630
    CW, CH = W - RIGHT_START, H
    if cover_raw:
        try:
            cov = cover_raw.copy()
            cw, ch = cov.size
            scale = max(CW / cw, CH / ch)
            cov   = cov.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
            lft   = (cov.width  - CW) // 2
            top   = (cov.height - CH) // 2
            cov   = cov.crop((lft, top, lft + CW, top + CH))

            # Fade mask — hard transparent on left edge → fully opaque on right
            mask = Image.new("L", (CW, CH), 255)
            md   = ImageDraw.Draw(mask)
            FADE_EDGE = 260
            for x in range(FADE_EDGE):
                md.line([(x, 0), (x, CH)], fill=int(255 * (x / FADE_EDGE)))

            img.paste(cov.convert("RGBA"), (RIGHT_START, 0), mask)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # ── Layer 4: Accent left bar ──────────────────────────────────────────────
    draw.rectangle([(0, 0), (5, H)], fill=(*acc_rgb, 255))

    # ── Layer 5: Genre tag line ───────────────────────────────────────────────
    genres_val = next((v for lb, v in info_rows if lb in ("Genres", "Genre")), "")
    if genres_val:
        tags = [g.strip() for g in genres_val.split(",")[:4]]
        genre_str = "  •  ".join(tags)
        draw.text((60, 88), genre_str,
                  fill=(190, 190, 190, 230),
                  font=_font("poppins-regular", 21))

    # ── Layer 6: BIG title (Bebas Neue, uppercase) ────────────────────────────
    ty = 140
    title_up    = title.upper()
    title_lines = _wrap(title_up, 20)          # ~20 chars per line for 82pt font
    for ln in title_lines[:3]:
        draw.text((55, ty), ln,
                  fill=(255, 255, 255, 255),
                  font=_font("bebas-neue-bold", 82))
        ty += 92
    ty += 6

    # ── Layer 7: Native title (smaller, accent colour) ────────────────────────
    if native_title and native_title != title:
        draw.text((60, ty), native_title[:36],
                  fill=(*acc_rgb, 200),
                  font=_font("poppins-regular", 22))
        ty += 34

    # ── Layer 8: Description (soft white) ────────────────────────────────────
    desc_font  = _font("poppins-regular", 21)
    desc_lines = _wrap(desc, 50)
    for ln in desc_lines[:4]:
        draw.text((60, ty), ln, fill=(210, 210, 210, 210), font=desc_font)
        ty += 30
    ty += 14

    # ── Layer 9: Action buttons (Download / Watch Now) ────────────────────────
    if ty < H - 100:
        bty = min(ty, H - 88)
        BH  = 52
        # DOWNLOAD — white outline
        draw.rectangle([(58, bty), (258, bty + BH)],
                        outline=(255, 255, 255, 240), width=3)
        draw.text((158, bty + BH // 2), "DOWNLOAD",
                  fill=(255, 255, 255),
                  font=_font("poppins-bold", 18), anchor="mm")
        # WATCH NOW — accent fill
        draw.rectangle([(276, bty), (486, bty + BH)],
                        fill=(*acc_rgb, 255))
        draw.text((381, bty + BH // 2), "WATCH NOW",
                  fill=(255, 255, 255),
                  font=_font("poppins-bold", 18), anchor="mm")

    # ── Layer 10: Info card (bottom-right corner) ─────────────────────────────
    ep_val  = next((v for lb, v in info_rows if "Episode" in lb), "?")
    sea_val = next((v for lb, v in info_rows if "Season" in lb), "?")
    dur_val = next((v for lb, v in info_rows if lb in ("Runtime", "Duration")), "?")
    sc_val  = next((v for lb, v in info_rows if lb in ("Score", "Rating")), str(score) if score else "?")

    CX, CY, CRW, CRH = RIGHT_START + 8, H - 152, 630, 142
    draw.rounded_rectangle([(CX, CY), (CX + CRW, CY + CRH)],
                            radius=10, fill=(10, 10, 10, 210))
    draw.rounded_rectangle([(CX, CY), (CX + CRW, CY + CRH)],
                            radius=10, outline=(*acc_rgb, 80), width=1)

    draw.text((CX + 18, CY + 14),  f"Episode — {ep_val}",
              fill=(255, 255, 255), font=_font("poppins-bold", 26))
    draw.text((CX + 18, CY + 56),  f"Season  — {sea_val}",
              fill=(175, 175, 175), font=_font("poppins-regular", 20))
    draw.text((CX + 18, CY + 84),  f"Score   — {sc_val}",
              fill=(175, 175, 175), font=_font("poppins-regular", 20))
    draw.text((CX + 18, CY + 112), f"Status  — {status}",
              fill=(130, 130, 130), font=_font("poppins-regular", 18))

    # ── Layer 11: Channel branding top-right ──────────────────────────────────
    brand = watermark_text or "@BeatAnime"
    bx    = W - 18
    try:
        bbox = draw.textbbox((0, 0), brand, font=_font("poppins-bold", 22))
        bw   = bbox[2] - bbox[0]
    except Exception:
        bw = len(brand) * 14
    draw.rounded_rectangle([(bx - bw - 30, 14), (bx, 58)],
                            radius=6, fill=(0, 0, 0, 170))
    draw.line([(bx - bw - 32, 14), (bx - bw - 32, 58)],
              fill=(*acc_rgb, 255), width=4)
    draw.text((bx - 10, 36), brand,
              fill=(255, 255, 255), font=_font("poppins-bold", 22), anchor="rm")

    # ── Layer 12: Template logo (e.g. Netflix / Crunchyroll) ──────────────────
    logo_key = t.get("logo")
    if logo_key:
        logo_img = _dl_icon(logo_key)
        if logo_img:
            try:
                LW, LH = 80, 36
                logo_img = logo_img.resize((LW, LH), Image.LANCZOS)
                logo_alpha = logo_img.split()[3] if logo_img.mode == "RGBA" else None
                img.paste(logo_img, (W - LW - 24, 68), logo_alpha)
                draw = ImageDraw.Draw(img)
            except Exception:
                pass

    # ── Layer 13: Watermark overlay (always applied when set) ────────────────
    if watermark_text:
        _apply_watermark(img, draw, watermark_text, watermark_pos, txt_rgb)

    # ── Export ────────────────────────────────────────────────────────────────
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=93, optimize=True)
    buf.seek(0)
    buf.name = f"poster_{template}_{title[:20].replace(' ', '_')}.jpg"
    return buf



def _make_stream(
    title, native_title, status, info_rows, desc,
    cover_url, score, watermark_text, branding,
):
    """
    Layout (1280×720):
      Full-bleed blurred cover BG · dark overlay
      LEFT : accent bar │ genre tags │ BIG TITLE │ description │ DOWNLOAD + WATCH NOW
      RIGHT: cover art with left-fade gradient
      TOP-RIGHT : branding badge (dark pill)
      BTM-RIGHT : episode/season/duration card + small thumbnail
    """
    img = Image.new("RGBA", (W, H), (8, 10, 22, 255))
    cover_raw = _dl(cover_url)

    # Blurred BG
    if cover_raw:
        try:
            bg = cover_raw.copy().resize((W, H), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(36))
            img = Image.alpha_composite(img, bg.convert("RGBA"))
            img = Image.alpha_composite(img, Image.new("RGBA", (W, H), (5, 8, 20, 195)))
        except Exception:
            pass

    draw = ImageDraw.Draw(img)

    # Cover art right side with left-fade
    RS = 620
    if cover_raw:
        try:
            cw, ch = cover_raw.size
            scale = max((W - RS) / cw, H / ch)
            cov = cover_raw.copy().resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
            lft = (cov.width  - (W - RS)) // 2
            top = (cov.height - H)         // 2
            cov = cov.crop((lft, top, lft + W - RS, top + H))
            mask = Image.new("L", (W - RS, H), 255)
            md = ImageDraw.Draw(mask)
            for x in range(300):
                md.line([(x, 0), (x, H)], fill=int(255 * (x / 300)))
            img.paste(cov.convert("RGBA"), (RS, 0), mask)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # Left accent bar
    draw.rectangle([(0, 0), (5, H)], fill=(229, 9, 20, 255))

    # Genre tags
    genres = next((v for lb, v in info_rows if lb in ("Genres", "Genre")), "")
    if genres:
        tags = [g.strip() for g in genres.split(",")[:4]]
        draw.text(
            (62, 74), "  •  ".join(tags),
            fill=(185, 185, 185, 220), font=_font("poppins-regular", 22),
        )

    # Big title
    ty = 126
    for ln in _wrap(title.upper(), 17)[:3]:
        draw.text((58, ty), ln, fill=(255, 255, 255, 255),
                  font=_font("bebas-neue-bold", 96))
        ty += 104
    ty += 6

    # Native title
    if native_title and native_title != title:
        draw.text((62, ty), native_title[:38],
                  fill=(160, 180, 220, 200), font=_font("poppins-regular", 22))
        ty += 34

    # Description
    for ln in _wrap(desc, 50)[:3]:
        draw.text((62, ty), ln, fill=(200, 205, 215, 215),
                  font=_font("poppins-regular", 20))
        ty += 28
    ty += 18

    # Buttons
    bty = min(ty, H - 82)
    BH = 50
    draw.rectangle([(60, bty), (255, bty + BH)], outline=(255, 255, 255, 230), width=2)
    draw.text((157, bty + BH // 2), "DOWNLOAD",
              fill=(255, 255, 255), font=_font("poppins-bold", 16), anchor="mm")
    draw.rectangle([(275, bty), (476, bty + BH)], fill=(229, 9, 20, 255))
    draw.text((375, bty + BH // 2), "WATCH NOW",
              fill=(255, 255, 255), font=_font("poppins-bold", 16), anchor="mm")

    # Top-right branding badge
    brand = watermark_text or branding or "@BeatAnime"
    try:
        bw = draw.textbbox((0, 0), brand, font=_font("poppins-bold", 20))[2]
    except Exception:
        bw = len(brand) * 12
    bx = W - 16
    draw.rounded_rectangle([(bx - bw - 38, 12), (bx, 54)],
                            radius=6, fill=(5, 5, 15, 210))
    draw.line([(bx - bw - 40, 12), (bx - bw - 40, 54)],
              fill=(229, 9, 20, 255), width=4)
    draw.text((bx - 10, 33), brand, fill=(255, 255, 255),
              font=_font("poppins-bold", 20), anchor="rm")

    # Bottom-right info card
    ep_val  = next((v for lb, v in info_rows if "Episode" in lb), "N/A")
    sea_val = next((v for lb, v in info_rows if "Season"  in lb), "01")
    dur_val = next((v for lb, v in info_rows if lb in ("Duration", "Runtime")), "23m")
    sc_val  = str(score) if score and str(score) not in ("?", "None", "0") else "N/A"

    CX, CY, CRW, CRH = RS + 10, H - 152, W - RS - 20, 142
    draw.rounded_rectangle([(CX, CY), (CX + CRW, CY + CRH)],
                            radius=10, fill=(8, 8, 18, 220))
    draw.rounded_rectangle([(CX, CY), (CX + CRW, CY + CRH)],
                            radius=10, outline=(50, 55, 70, 100), width=1)

    # Thumbnail in card
    THUMB_W = 110
    if cover_raw:
        try:
            th = cover_raw.copy().resize((THUMB_W, CRH - 16), Image.LANCZOS)
            mask_th = Image.new("L", th.size, 255)
            img.paste(th.convert("RGBA"), (CX + CRW - THUMB_W - 10, CY + 8), mask_th)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    draw.text((CX + 18, CY + 14), f"Episode  —  {ep_val}",
              fill=(255, 255, 255), font=_font("poppins-bold", 24))
    draw.text((CX + 18, CY + 54), f"Season   —  {sea_val}",
              fill=(165, 165, 175), font=_font("poppins-regular", 19))
    draw.text((CX + 18, CY + 82), f"Duration —  {dur_val}",
              fill=(145, 145, 158), font=_font("poppins-regular", 18))
    draw.text((CX + 18, CY + 110), f"Score    —  {sc_val}",
              fill=(120, 120, 135), font=_font("poppins-regular", 17))

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=94, optimize=True)
    buf.seek(0)
    buf.name = f"poster_stream_{title[:16].replace(' ','_')}.jpg"
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE: "vessel"  (Image 2 — Anime Vessel split-panel)
# ─────────────────────────────────────────────────────────────────────────────
def _make_vessel(
    title, native_title, status, info_rows, desc,
    cover_url, score, watermark_text, branding,
):
    """
    Layout (1280×720):
      LEFT PANEL (~58%)  : dark navy BG │ title │ description │ author/tags │ button
      RIGHT PANEL (~42%) : portrait cover art (rounded shadow)
      RIGHT EDGE         : vertical branding text rotated 90°
      DECORATIVE         : hollow circles bottom-left
    """
    PANEL_W = 740  # left panel width
    img = Image.new("RGBA", (W, H), (12, 14, 30, 255))
    draw = ImageDraw.Draw(img)

    # Subtle gradient on left panel
    for x in range(PANEL_W):
        alpha = int(18 * (1 - x / PANEL_W))
        draw.line([(x, 0), (x, H)], fill=(20, 25, 55, alpha))

    # Right panel: slightly lighter
    draw.rectangle([(PANEL_W, 0), (W, H)], fill=(18, 20, 40, 255))

    cover_raw = _dl(cover_url)

    # Cover art (portrait, centered in right panel, rounded)
    if cover_raw:
        try:
            COV_W, COV_H = 310, 460
            COV_X = PANEL_W + (W - PANEL_W - COV_W) // 2 - 30
            COV_Y = (H - COV_H) // 2

            cov = cover_raw.copy()
            cw, ch = cov.size
            scale = max(COV_W / cw, COV_H / ch)
            cov = cov.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
            l = (cov.width - COV_W) // 2
            t = (cov.height - COV_H) // 2
            cov = cov.crop((l, t, l + COV_W, t + COV_H))

            # Shadow
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle(
                [(COV_X + 10, COV_Y + 10), (COV_X + COV_W + 10, COV_Y + COV_H + 10)],
                radius=18, fill=(0, 0, 0, 130))
            img = Image.alpha_composite(img, sh)

            # Rounded cover
            mask = Image.new("L", (COV_W, COV_H), 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                [(0, 0), (COV_W, COV_H)], radius=18, fill=255)
            img.paste(cov.convert("RGB"), (COV_X, COV_Y), mask)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # Vertical branding text (right edge)
    brand = watermark_text or branding or "BEAT ANIME"
    try:
        vfont = _font("bebas-neue-bold", 34)
        txt_img = Image.new("RGBA", (500, 50), (0, 0, 0, 0))
        ImageDraw.Draw(txt_img).text(
            (0, 0), brand.upper(), fill=(60, 65, 100, 200), font=vfont)
        txt_rot = txt_img.rotate(90, expand=True)
        vx = W - txt_rot.width - 8
        vy = (H - txt_rot.height) // 2
        img.paste(txt_rot, (vx, vy), txt_rot)
        draw = ImageDraw.Draw(img)
    except Exception:
        pass

    # Decorative hollow circles (bottom-left)
    for i, (cr, co) in enumerate([(100, 35), (70, 25), (45, 18)]):
        cx_ = -cr + 80 + i * 40
        cy_ = H - cr + 60 - i * 20
        draw.ellipse([(cx_ - cr, cy_ - cr), (cx_ + cr, cy_ + cr)],
                     outline=(40, 50, 90, 80), width=3)

    # Left panel content
    LX = 60

    # Genre tags
    genres = next((v for lb, v in info_rows if lb in ("Genres", "Genre")), "")
    if genres:
        tags = [g.strip() for g in genres.split(",")[:3]]
        draw.text((LX, 60), "  ·  ".join(tags),
                  fill=(120, 135, 185, 210), font=_font("poppins-regular", 20))

    # Big title
    ty = 108
    title_lines = _wrap(title, 20)[:3]
    for ln in title_lines:
        draw.text((LX, ty), ln, fill=(240, 245, 255, 255),
                  font=_font("bebas-neue-bold", 80))
        ty += 86
    ty += 8

    # Native title
    if native_title and native_title != title:
        draw.text((LX, ty), native_title[:40],
                  fill=(110, 125, 175, 185), font=_font("poppins-regular", 20))
        ty += 32

    # Description
    for ln in _wrap(desc, 52)[:3]:
        draw.text((LX, ty), ln, fill=(175, 180, 210, 210),
                  font=_font("poppins-regular", 19))
        ty += 26
    ty += 18

    # Author / studio row
    studio = next((v for lb, v in info_rows if lb in ("Studio",)), "")
    if studio:
        draw.text((LX, ty), f"🎬  {studio}", fill=(140, 155, 200, 200),
                  font=_font("poppins-regular", 19))
        ty += 28

    # Status + score
    sc_str = f"⭐  {score}/100" if score and str(score) not in ("?", "None", "0") else ""
    st_str = status or ""
    side_str = "  ·  ".join(filter(None, [st_str, sc_str]))
    if side_str:
        draw.text((LX, ty), side_str, fill=(120, 130, 175, 190),
                  font=_font("poppins-regular", 18))
        ty += 30
    ty += 12

    # "Get Started" button
    bty = min(ty, H - 68)
    BTW = 190
    draw.rounded_rectangle([(LX, bty), (LX + BTW, bty + 46)],
                            radius=23, fill=(50, 100, 220, 230))
    draw.text((LX + BTW // 2, bty + 23), "Get Started  →",
              fill=(255, 255, 255), font=_font("poppins-bold", 16), anchor="mm")

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=94, optimize=True)
    buf.seek(0)
    buf.name = f"poster_vessel_{title[:16].replace(' ','_')}.jpg"
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE: "splash"  (Image 3 — Full-bleed cinematic title card)
# ─────────────────────────────────────────────────────────────────────────────
def _make_splash(
    title, native_title, status, info_rows, desc,
    cover_url, score, watermark_text, branding,
):
    """
    Layout (1280×720):
      Full-bleed cover as background · heavy dark gradient
      CENTER: large stylised title with shadow band
      BOTTOM : genre · score · studio · branding
    """
    img = Image.new("RGBA", (W, H), (5, 5, 8, 255))
    cover_raw = _dl(cover_url)

    # Full-bleed cover
    if cover_raw:
        try:
            bg = cover_raw.copy().resize((W, H), Image.LANCZOS)
            img = Image.alpha_composite(img, bg.convert("RGBA"))
        except Exception:
            pass

    # Dark gradient (bottom-heavy)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        ratio = y / H
        # Heavier at top and bottom, lighter in middle
        alpha = int(210 * (0.6 + 0.4 * abs(ratio - 0.45)))
        gd.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, grad)

    # Additional center band (for text readability)
    band_h = 200
    band_y = (H - band_h) // 2 - 20
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(band).rectangle([(0, band_y), (W, band_y + band_h)],
                                   fill=(0, 0, 0, 110))
    img = Image.alpha_composite(img, band)
    draw = ImageDraw.Draw(img)

    # ── Title: large, centered, with letter-spacing illusion ──
    title_up = title.upper()
    tf = _font("bebas-neue-bold", 110)
    try:
        tw = draw.textbbox((0, 0), title_up, font=tf)[2]
    except Exception:
        tw = len(title_up) * 65
    tx = (W - min(tw, W - 80)) // 2
    ty_title = band_y + 20

    # Drop shadow
    draw.text((tx + 4, ty_title + 4), title_up, fill=(0, 0, 0, 160), font=tf)

    # Main title text — if fits single line
    if tw <= W - 80:
        draw.text((tx, ty_title), title_up, fill=(255, 255, 255, 255), font=tf)
    else:
        # Wrap to 2 lines at smaller size
        tf2 = _font("bebas-neue-bold", 82)
        for i, ln in enumerate(_wrap(title_up, 16)[:2]):
            try:
                lw = draw.textbbox((0, 0), ln, font=tf2)[2]
            except Exception:
                lw = len(ln) * 48
            lx = (W - lw) // 2
            draw.text((lx, ty_title + i * 88), ln,
                      fill=(255, 255, 255, 255), font=tf2)

    # Native subtitle
    if native_title and native_title != title:
        try:
            nw = draw.textbbox((0, 0), native_title, font=_font("poppins-regular", 28))[2]
        except Exception:
            nw = len(native_title) * 17
        draw.text(((W - nw) // 2, band_y + band_h - 40), native_title,
                  fill=(200, 210, 230, 190), font=_font("poppins-regular", 28))

    # Bottom info bar
    genres = next((v for lb, v in info_rows if lb in ("Genres", "Genre")), "")
    studio = next((v for lb, v in info_rows if lb == "Studio"), "")
    sc_str = f"{score}/100" if score and str(score) not in ("?", "None", "0") else ""
    pieces = [g.strip() for g in genres.split(",")[:3]] + ([f"⭐ {sc_str}"] if sc_str else []) + ([studio] if studio else [])
    bottom_str = "   ·   ".join(pieces)
    if bottom_str:
        try:
            bw2 = draw.textbbox((0, 0), bottom_str, font=_font("poppins-regular", 22))[2]
        except Exception:
            bw2 = len(bottom_str) * 13
        draw.text(((W - bw2) // 2, H - 72), bottom_str,
                  fill=(210, 215, 225, 220), font=_font("poppins-regular", 22))

    # Branding bottom-center
    brand = watermark_text or branding or "@BeatAnime"
    try:
        bbw = draw.textbbox((0, 0), brand, font=_font("poppins-bold", 18))[2]
    except Exception:
        bbw = len(brand) * 11
    draw.text(((W - bbw) // 2, H - 36), brand,
              fill=(160, 170, 190, 180), font=_font("poppins-bold", 18))

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=94, optimize=True)
    buf.seek(0)
    buf.name = f"poster_splash_{title[:16].replace(' ','_')}.jpg"
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE: "od3n"  (Image 4 — Character-center, vertical title, info right)
# ─────────────────────────────────────────────────────────────────────────────
def _make_od3n(
    title, native_title, status, info_rows, desc,
    cover_url, score, watermark_text, branding,
):
    """
    Layout (1280×720):
      Full dark BG
      CENTER/LEFT : character cover art (full height, no crop top)
      LEFT EDGE   : vertical rotated large title + hollow squares
      RIGHT PANEL : genre tags │ description │ studio·score │ buttons │ thumbnails
      BOTTOM-LEFT : social icon row
    """
    img = Image.new("RGBA", (W, H), (12, 12, 14, 255))
    draw = ImageDraw.Draw(img)
    cover_raw = _dl(cover_url)

    # ── Subtle horizontal scanline texture (dark) ──
    for y in range(0, H, 4):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 4))

    # ── Vertical title text (left edge, rotated 90° CCW) ──
    VERT_FONT_SIZE = 118
    vtf = _font("bebas-neue-bold", VERT_FONT_SIZE)
    title_upper = title.upper()[:20]  # cap length
    try:
        tsize = draw.textbbox((0, 0), title_upper, font=vtf)
        txt_w = tsize[2] - tsize[0]
    except Exception:
        txt_w = len(title_upper) * 68

    txt_layer = Image.new("RGBA", (txt_w + 20, VERT_FONT_SIZE + 20), (0, 0, 0, 0))
    ImageDraw.Draw(txt_layer).text(
        (10, 5), title_upper, fill=(55, 58, 62, 230), font=vtf)
    rotated = txt_layer.rotate(90, expand=True)
    vert_x = 8
    vert_y = (H - rotated.height) // 2
    img.paste(rotated, (vert_x, vert_y), rotated)
    draw = ImageDraw.Draw(img)

    CHAR_START_X = vert_x + rotated.width + 8  # where character starts

    # ── Hollow squares (left decoration strip) ──
    sq_x = CHAR_START_X - 2
    for i, (sy, ss) in enumerate([(90, 42), (165, 32), (230, 24), (285, 18), (330, 13)]):
        draw.rectangle([(sq_x, sy), (sq_x + ss, sy + ss)],
                       outline=(70, 74, 80, 160), width=2)

    # ── Character cover art (center-left, full height) ──
    CHAR_W = 480
    CHAR_X = CHAR_START_X + 10
    if cover_raw:
        try:
            cw, ch = cover_raw.size
            scale = max(CHAR_W / cw, H / ch)
            cov = cover_raw.copy().resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)
            l = (cov.width  - CHAR_W) // 2
            t = max(0, (cov.height - H) // 2)
            cov = cov.crop((l, t, l + CHAR_W, t + H))

            # Fade mask: hard on right edge
            mask = Image.new("L", (CHAR_W, H), 255)
            md = ImageDraw.Draw(mask)
            RFADE = 120
            for x in range(RFADE):
                md.line([(CHAR_W - RFADE + x, 0), (CHAR_W - RFADE + x, H)],
                        fill=int(255 * (1 - x / RFADE)))
            img.paste(cov.convert("RGBA"), (CHAR_X, 0), mask)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # ── Right info panel ──
    RX = CHAR_X + CHAR_W + 20
    PANEL_W2 = W - RX - 20

    # Genre tags (top right)
    genres = next((v for lb, v in info_rows if lb in ("Genres", "Genre")), "")
    RY = 50
    if genres:
        tags = [g.strip().upper() for g in genres.split(",")[:3]]
        draw.text((RX, RY), "   ".join(tags),
                  fill=(195, 198, 205, 220), font=_font("poppins-regular", 18))
        RY += 32
    RY += 8

    # Teaser description (split into 2 parts like Image 4)
    desc_short = _wrap(desc, 36)
    half = max(1, len(desc_short) // 2)
    # Left sub-column of right panel
    SUB_X = RX
    for ln in desc_short[:half]:
        draw.text((SUB_X, RY), ln, fill=(165, 168, 178, 210),
                  font=_font("poppins-regular", 18))
        RY += 24
    RY += 10

    # Studio + score
    studio = next((v for lb, v in info_rows if lb == "Studio"), "")
    sc_val = str(score) if score and str(score) not in ("?", "None", "0") else ""
    if studio:
        draw.text((RX, RY), studio.upper() + "   STUDIO",
                  fill=(175, 178, 188, 210), font=_font("poppins-bold", 17))
        RY += 26
    if sc_val:
        try:
            star_str = f"{sc_val}  ★"
            draw.text((RX, RY), star_str,
                      fill=(220, 190, 60, 235), font=_font("poppins-bold", 22))
        except Exception:
            pass
        RY += 32
    RY += 14

    # DOWNLOAD + MORE INFO buttons
    BH2 = 44
    BW2 = (PANEL_W2 - 10) // 2
    draw.rectangle([(RX, RY), (RX + BW2, RY + BH2)],
                   outline=(200, 202, 210, 200), width=2)
    draw.text((RX + BW2 // 2, RY + BH2 // 2), "DOWNLOAD",
              fill=(220, 222, 228), font=_font("poppins-bold", 14), anchor="mm")
    draw.rectangle([(RX + BW2 + 10, RY), (RX + PANEL_W2, RY + BH2)],
                   outline=(200, 202, 210, 200), width=2)
    draw.text((RX + BW2 + 10 + BW2 // 2, RY + BH2 // 2), "MORE INFO",
              fill=(220, 222, 228), font=_font("poppins-bold", 14), anchor="mm")
    RY += BH2 + 20

    # Character thumbnails (bottom right — 2 small previews)
    if cover_raw:
        TH_W, TH_H = 120, 90
        for i in range(2):
            try:
                tx2 = RX + i * (TH_W + 12)
                ty2 = H - TH_H - 36
                th = cover_raw.copy().resize((TH_W, TH_H), Image.LANCZOS)
                # Slightly different crop for variety
                cw2, ch2 = cover_raw.size
                scale2 = max(TH_W / cw2, TH_H / ch2)
                th2 = cover_raw.copy().resize(
                    (int(cw2 * scale2), int(ch2 * scale2)), Image.LANCZOS)
                offset_x = max(0, min(th2.width - TH_W,  i * (th2.width // 3)))
                offset_y = max(0, min(th2.height - TH_H, i * 40))
                th2 = th2.crop((offset_x, offset_y, offset_x + TH_W, offset_y + TH_H))
                img.paste(th2.convert("RGBA"), (tx2, ty2))
                draw = ImageDraw.Draw(img)
                draw.rectangle([(tx2, ty2), (tx2 + TH_W, ty2 + TH_H)],
                                outline=(80, 82, 90, 160), width=1)
            except Exception:
                pass

    # "NEXT>> / BRANDING" text bottom-right
    brand = watermark_text or branding or "@BeatAnime"
    draw.text((W - 16, H - 50), "NEXT>>", fill=(160, 162, 170, 180),
              font=_font("poppins-bold", 14), anchor="rm")
    draw.text((W - 16, H - 28), brand.upper(),
              fill=(140, 142, 155, 170), font=_font("poppins-bold", 13), anchor="rm")

    # Social icons row (bottom-left text substitutes)
    icons = ["♡", "✉", "✈", "⊹"]
    ix = CHAR_X + 10
    for ico in icons:
        draw.text((ix, H - 32), ico, fill=(170, 172, 182, 200),
                  font=_font("poppins-regular", 22))
        ix += 34

    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=94, optimize=True)
    buf.seek(0)
    buf.name = f"poster_od3n_{title[:16].replace(' ','_')}.jpg"
    return buf


_icon_cache: Dict[str, Optional[Any]] = {}


def _dl_icon(name: str) -> Optional[Any]:
    if name in _icon_cache:
        return _icon_cache[name]
    path = ICON_DIR / f"{name}.png"
    try:
        if path.exists():
            img = Image.open(path).convert("RGBA")
            _icon_cache[name] = img
            return img
    except Exception:
        pass
    _icon_cache[name] = None
    return None


def _apply_watermark(img: Any, draw: Any, text: str, position: str,
                     txt_rgb: tuple) -> None:
    """
    Full watermark layer with drop-shadow.
    position: center | bottom | top | bottom-right | bottom-left | top-right | top-left
    """
    try:
        font = _font("poppins-regular", 28)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = len(text) * 16, 28

        pos_map = {
            "center":       ((W - tw) // 2,        (H - th) // 2),
            "bottom":       ((W - tw) // 2,         H - th - 70),
            "top":          ((W - tw) // 2,         18),
            "bottom-right": (W - tw - 20,           H - th - 70),
            "bottom-left":  (20,                    H - th - 70),
            "top-right":    (W - tw - 20,           18),
            "top-left":     (20,                    18),
            "left":         (20,                    (H - th) // 2),
            "right":        (W - tw - 20,           (H - th) // 2),
        }
        x, y = pos_map.get(position, pos_map["center"])

        # Semi-transparent watermark overlay (separate layer)
        wm_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        wd = ImageDraw.Draw(wm_layer)
        # Shadow
        wd.text((x + 2, y + 2), text, fill=(0, 0, 0, 80), font=font)
        # Main text
        wd.text((x, y), text, fill=(*txt_rgb[:3], 110), font=font)
        result = Image.alpha_composite(img.convert("RGBA"), wm_layer)
        img.paste(result.convert(img.mode), (0, 0))
        draw = ImageDraw.Draw(img)
    except Exception as exc:
        logger.debug(f"Watermark error: {exc}")


# ── Format helpers ─────────────────────────────────────────────────────────────

def _parse_date(d: Optional[Dict]) -> str:
    if not d:
        return "N/A"
    y, m, day = d.get("year"), d.get("month"), d.get("day")
    parts = [str(y)] if y else []
    if m:
        import calendar
        parts.insert(0, calendar.month_abbr[m] if 1 <= m <= 12 else str(m))
    if day:
        parts.insert(0, str(day))
    return " ".join(parts) if parts else "N/A"


def _build_anime_data(data: Dict) -> Tuple:
    t = data.get("title", {}) or {}
    title = t.get("english") or t.get("romaji") or "Unknown"
    native = t.get("native", "")
    status = (data.get("status") or "").replace("_", " ").title()
    episodes = str(data.get("episodes") or "?")
    duration = data.get("duration")
    score = data.get("averageScore", "?")
    genres = ", ".join((data.get("genres") or [])[:4])
    season = f"{(data.get('season') or '').title()} {data.get('seasonYear') or ''}".strip()
    studios = (data.get("studios", {}) or {}).get("nodes", [])
    studio = studios[0].get("name", "") if studios else ""
    desc = _clean(data.get("description", ""), 300)
    cover = (data.get("coverImage") or {})
    cover_url = cover.get("extraLarge") or cover.get("large") or ""
    rows = [
        ("Status", status), ("Episodes", episodes + (f" × {duration}min" if duration else "")),
        ("Season", season), ("Genres", genres[:40]), ("Studio", studio[:30]),
        ("Score", f"{score}/100" if score and score != "?" else "N/A"),
    ]
    return title, native, status, rows, desc, cover_url, score


def _build_manga_data(data: Dict) -> Tuple:
    t = data.get("title", {}) or {}
    title = t.get("english") or t.get("romaji") or "Unknown"
    native = t.get("native", "")
    status = (data.get("status") or "").replace("_", " ").title()
    chapters = str(data.get("chapters") or "Ongoing")
    volumes = str(data.get("volumes") or "?")
    score = data.get("averageScore", "?")
    genres = ", ".join((data.get("genres") or [])[:4])
    desc = _clean(data.get("description", ""), 300)
    cover = (data.get("coverImage") or {})
    cover_url = cover.get("extraLarge") or cover.get("large") or ""
    rows = [
        ("Status", status), ("Chapters", chapters),
        ("Volumes", volumes), ("Genres", genres[:40]),
        ("Score", f"{score}/100" if score and score != "?" else "N/A"),
    ]
    return title, native, status, rows, desc, cover_url, score


def _build_movie_data(data: Dict) -> Tuple:
    title = data.get("title", "Unknown")
    status = "Released" if data.get("release_date") else "N/A"
    rating = str(round(data.get("vote_average", 0) * 10)) + "/100" if data.get("vote_average") else "N/A"
    genres = ", ".join([g["name"] for g in (data.get("genres") or [])[:4]])
    runtime = f"{data.get('runtime', '?')} min"
    desc = _clean(data.get("overview", ""), 300)
    cover_url = _tmdb_poster(data.get("poster_path", ""))
    rows = [
        ("Status", status), ("Runtime", runtime),
        ("Genres", genres[:40]), ("Rating", rating),
        ("Year", (data.get("release_date") or "")[:4]),
    ]
    return title, "", status, rows, desc, cover_url, data.get("vote_average", "?")


def _build_tv_data(data: Dict) -> Tuple:
    title = data.get("name", "Unknown")
    status = data.get("status", "N/A")
    rating = str(round(data.get("vote_average", 0) * 10)) + "/100" if data.get("vote_average") else "N/A"
    genres = ", ".join([g["name"] for g in (data.get("genres") or [])[:4]])
    seasons = str(data.get("number_of_seasons", "?"))
    eps = str(data.get("number_of_episodes", "?"))
    desc = _clean(data.get("overview", ""), 300)
    cover_url = _tmdb_poster(data.get("poster_path", ""))
    rows = [
        ("Status", status), ("Seasons", seasons),
        ("Episodes", eps), ("Genres", genres[:40]), ("Rating", rating),
    ]
    return title, "", status, rows, desc, cover_url, data.get("vote_average", "?")


# ── Category settings lookup ───────────────────────────────────────────────────

def _get_settings(category: str) -> dict:
    try:
        from database_dual import get_category_settings
        return get_category_settings(category)
    except Exception:
        return {
            "watermark_text": None, "watermark_position": "center",
            "logo_file_id": None, "logo_position": "bottom",
            "branding": "", "caption_template": "",
        }


# ── Permission check ──────────────────────────────────────────────────────────

def _is_admin(uid: int) -> bool:
    return uid in (ADMIN_ID, OWNER_ID)


# ── POSTER COMMAND HANDLER FACTORY ────────────────────────────────────────────

async def _poster_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    template: str, media_type: str,
) -> None:
    """
    Generic handler for all poster commands.
    Admin: unlimited.
    Users: daily limit based on plan (Free=20, Bronze=30, Silver=40, Gold=50).
    /my_plan and /plans are visible to all users.
    """
    uid = update.effective_user.id if update.effective_user else 0
    is_admin_user = _is_admin(uid)

    if not is_admin_user:
        # Check user daily limit
        try:
            from database_dual import (
                is_poster_premium, get_poster_rank,
                check_and_update_poster_usage, get_poster_usage_today,
                POSTER_TASK_LIMITS,
            )
            rank = get_poster_rank(uid) if is_poster_premium(uid) else "default"
            limit = POSTER_TASK_LIMITS.get(rank, 20)
            used = get_poster_usage_today(uid)
            if used >= limit:
                await update.effective_message.reply_text(
                    f"<b>⚠️ Daily Limit Reached</b>\n\n"
                    f"You have used <b>{used}/{limit}</b> posters today.\n"
                    f"Your plan: <b>{rank.title()}</b>\n\n"
                    f"<i>Use /my_plan to check your plan or /plans to upgrade.</i>",
                    parse_mode="HTML",
                )
                return
            # Count this usage
            check_and_update_poster_usage(uid, limit)
        except Exception:
            pass  # If DB fails, allow the request

    if not context.args:
        await update.effective_message.reply_text(
            f"<b>Usage:</b> /{template} &lt;title&gt;\n"
            f"<b>Example:</b> <code>/{template} Naruto</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    query = " ".join(context.args).strip()
    chat_id = update.effective_chat.id

    status = await update.effective_message.reply_text(
        f"<b>🎨 Generating {template.upper()} poster…</b>",
        parse_mode=ParseMode.HTML,
    )

    try:
        # Fetch data
        data = None
        if media_type == "ANIME":
            data = _anilist_anime(query)
        elif media_type == "MANGA":
            data = _anilist_manga(query)
        elif media_type == "MOVIE":
            data = _tmdb_movie(query)
        elif media_type == "TV":
            data = _tmdb_tv(query)

        if not data:
            await status.edit_text(
                f"<b>❌ Not Found</b>\n\nNo results for <code>{html.escape(query)}</code>.",
                parse_mode=ParseMode.HTML,
            )
            return

        # Load category settings (watermark, branding, etc.)
        cat = media_type.lower()
        if cat == "tv":
            cat = "tvshow"
        settings = _get_settings(cat)
        wm_text = settings.get("watermark_text")
        wm_pos = settings.get("watermark_position", "center")
        logo_fid = settings.get("logo_file_id")
        logo_pos = settings.get("logo_position", "bottom")
        branding = settings.get("branding", "")

        # Build poster parameters
        if media_type == "ANIME":
            title, native, st, rows, desc, cover_url, score = _build_anime_data(data)
        elif media_type == "MANGA":
            title, native, st, rows, desc, cover_url, score = _build_manga_data(data)
        elif media_type == "MOVIE":
            title, native, st, rows, desc, cover_url, score = _build_movie_data(data)
        else:
            title, native, st, rows, desc, cover_url, score = _build_tv_data(data)

        # Generate poster image
        poster_buf = _make_poster(
            template=template,
            title=title,
            native_title=native,
            status=st,
            info_rows=rows,
            desc=desc,
            cover_url=cover_url,
            score=score,
            watermark_text=wm_text,
            watermark_pos=wm_pos,
            logo_file_id=logo_fid,
            logo_pos=logo_pos,
        )

        # Build caption — use custom template if set, else default
        site_url = data.get("siteUrl", "")
        genres   = ", ".join((data.get("genres") or [])[:3]) if media_type in ("ANIME", "MANGA") else ""
        score_v  = data.get("averageScore", "")
        status_v = (data.get("status") or "").replace("_", " ").title()
        episodes = str(data.get("episodes") or "?")
        stnode   = ((data.get("studios") or {}).get("nodes") or [])
        studio   = stnode[0].get("name", "") if stnode else ""
        lang_v   = ""  # poster_engine commands don't have lang selection — left empty

        # Try custom caption template
        tmpl_cap = settings.get("caption_template", "")
        if tmpl_cap:
            caption = (tmpl_cap
                .replace("{title}",    html.escape(title))
                .replace("{native}",   html.escape(native or ""))
                .replace("{genres}",   html.escape(genres))
                .replace("{score}",    str(score_v))
                .replace("{status}",   html.escape(status_v))
                .replace("{episodes}", episodes)
                .replace("{studio}",   html.escape(studio))
                .replace("{lang}",     lang_v)
                .replace("{language}", lang_v)
                .replace("{link}",     join_url))
        else:
            caption = (
                f"<b>{html.escape(title)}</b>\n"
                f"{'<i>' + html.escape(genres) + '</i>' + chr(10) if genres else ''}"
                f"{'<b>' + html.escape(branding) + '</b>' + chr(10) if branding else ''}"
            )

        if len(caption) > 1024:
            caption = caption[:1020] + "…"
        caption = _apply_poster_style(caption)

        # Buttons — info + join now to watch
        from core.config import JOIN_BTN_TEXT
        try:
            from database_dual import get_setting as _gs
            join_txt = _gs("env_JOIN_BTN_TEXT", "") or JOIN_BTN_TEXT
            join_url = _gs("env_PUBLIC_ANIME_CHANNEL_URL", "") or PUBLIC_ANIME_CHANNEL_URL
            main_ch  = _gs("main_channel_id", "")
        except Exception:
            join_txt = JOIN_BTN_TEXT
            join_url = PUBLIC_ANIME_CHANNEL_URL
            main_ch  = ""

        # Try anime channel link from DB
        try:
            from database_dual import get_anime_channel_links as _acl
            alinks = _acl(title)
            if alinks and alinks[0][2]:  # has link_id
                bot_uname = context.bot.username or ""
                if bot_uname:
                    join_url = f"https://t.me/{bot_uname}?start={alinks[0][2]}"
        except Exception:
            pass

        btns = [
            [InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ", url=join_url)],
        ]
        if site_url:
            btns.append([InlineKeyboardButton("📋 ɪɴꜰᴏ", url=site_url)])

        # "Send to main channel" only for admin in private
        if chat_id == uid and uid in (ADMIN_ID, OWNER_ID) and main_ch:
            btns.append([InlineKeyboardButton(
                "📤 sᴇɴᴅ ᴛᴏ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ",
                callback_data=f"pe_send_main:{template}:{media_type}"
            )])

        if poster_buf:
            sent_poster = await context.bot.send_photo(
                chat_id=chat_id,
                photo=poster_buf,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btns),
            )
            # Store for send-to-main later
            if sent_poster:
                import json as _json
                try:
                    from database_dual import set_setting as _ss
                    _ss(f"last_poster_{uid}", _json.dumps({
                        "chat_id": chat_id,
                        "msg_id":  sent_poster.message_id,
                        "caption": caption,
                    }))
                except Exception:
                    pass
        else:
            # Fallback: send as text card if PIL unavailable
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption + f"\n\n<a href='{html.escape(cover_url)}'>🖼 Cover</a>" if cover_url else caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btns),
                disable_web_page_preview=False,
            )

        try:
            await status.delete()
        except Exception:
            pass

    except Exception as exc:
        logger.error(f"Poster error ({template}): {exc}\n{traceback.format_exc()}")
        try:
            await status.edit_text(
                "<b>⚠️ An error occurred. Please try again later.</b>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ── Individual command wrappers (one per template) ────────────────────────────

async def poster_ani(u, c):   await _poster_cmd(u, c, "ani",    "ANIME")
async def poster_anim(u, c):  await _poster_cmd(u, c, "anim",   "MANGA")
async def poster_crun(u, c):  await _poster_cmd(u, c, "crun",   "ANIME")
async def poster_net(u, c):   await _poster_cmd(u, c, "net",    "ANIME")
async def poster_netm(u, c):  await _poster_cmd(u, c, "netm",   "MANGA")
async def poster_light(u, c): await _poster_cmd(u, c, "light",  "ANIME")
async def poster_lightm(u,c): await _poster_cmd(u, c, "lightm", "MANGA")
async def poster_dark(u, c):  await _poster_cmd(u, c, "dark",   "ANIME")
async def poster_darkm(u, c): await _poster_cmd(u, c, "darkm",  "MANGA")
async def poster_netcr(u, c): await _poster_cmd(u, c, "netcr",  "ANIME")
async def poster_mod(u, c):   await _poster_cmd(u, c, "mod",    "ANIME")
async def poster_modm(u, c):  await _poster_cmd(u, c, "modm",   "MANGA")


# ── PREMIUM COMMANDS ──────────────────────────────────────────────────────────

async def cmd_my_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/my_plan — anyone can check their own plan (no admin check)."""
    uid = update.effective_user.id if update.effective_user else 0
    try:
        from database_dual import (is_poster_premium, get_poster_rank,
                                    get_poster_usage_today, POSTER_TASK_LIMITS,
                                    get_poster_premium)
        is_prem = is_poster_premium(uid)
        rank = get_poster_rank(uid) if is_prem else "default"
        limit = POSTER_TASK_LIMITS.get(rank, 20)
        used = get_poster_usage_today(uid)
        remaining = max(0, limit - used)

        if not is_prem:
            text = (
                f"<b>📋 Your Plan: Free</b>\n\n"
                f"• Daily Limit: <b>{limit}</b> posters\n"
                f"• Used Today: <b>{used}</b>\n"
                f"• Remaining: <b>{remaining}</b>\n\n"
                f"<i>Contact admin to upgrade!</i>"
            )
        else:
            doc = get_poster_premium(uid)
            expiry = doc.get("expiry_time") if doc else None
            exp_str = "Permanent"
            if expiry:
                remaining_time = expiry - datetime.utcnow()
                if remaining_time.total_seconds() > 0:
                    d, s = divmod(int(remaining_time.total_seconds()), 86400)
                    h = s // 3600
                    exp_str = f"{d}d {h}h remaining"
                else:
                    exp_str = "⚠️ Expired"
            text = (
                f"<b>✨ Your Plan: {rank.title()} Premium</b>\n\n"
                f"• Daily Limit: <b>{limit}</b> posters\n"
                f"• Used Today: <b>{used}</b>\n"
                f"• Remaining: <b>{remaining}</b>\n"
                f"• Expiry: <b>{exp_str}</b>"
            )
    except Exception as exc:
        text = f"<b>⚠️ Could not load plan info:</b> <code>{html.escape(str(exc)[:100])}</code>"

    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 BeatAnime", url=PUBLIC_ANIME_CHANNEL_URL)]
        ]),
    )


async def cmd_plans(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/plans — anyone can view available plans."""
    try:
        from database_dual import POSTER_TASK_LIMITS as TL
        bronze, silver, gold, free = TL["bronze"], TL["silver"], TL["gold"], TL["default"]
    except Exception:
        bronze, silver, gold, free = 30, 40, 50, 20

    await update.effective_message.reply_text(
        f"<b>💎 BeatAniVerse Poster Plans</b>\n\n"
        f"🆓 <b>Free</b> — {free} posters/day\n"
        f"🥉 <b>Bronze</b> — {bronze} posters/day\n"
        f"🥈 <b>Silver</b> — {silver} posters/day\n"
        f"🥇 <b>Gold</b> — {gold} posters/day\n\n"
        f"<i>Contact admin to upgrade your plan!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{os.getenv('ADMIN_CONTACT_USERNAME','Beat_Anime_Ocean')}")],
            [InlineKeyboardButton("📢 BeatAnime", url=PUBLIC_ANIME_CHANNEL_URL)],
        ]),
    )


async def cmd_add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/add_premium <user_id> <rank> [duration] — admin only."""
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return
    args = context.args
    if len(args) < 2:
        await update.effective_message.reply_text(
            "<b>Usage:</b> /add_premium &lt;user_id&gt; &lt;rank&gt; [duration]\n"
            "<b>Rank:</b> gold | silver | bronze\n"
            "<b>Duration:</b> 7d | 2w | 1m | permanent",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        target = int(args[0])
    except ValueError:
        await update.effective_message.reply_text("<b>❌ Invalid user ID.</b>", parse_mode=ParseMode.HTML)
        return
    rank = args[1].lower()
    from database_dual import POSTER_TASK_LIMITS
    if rank not in POSTER_TASK_LIMITS or rank == "default":
        await update.effective_message.reply_text(
            "<b>❌ Invalid rank.</b> Use: gold / silver / bronze", parse_mode=ParseMode.HTML
        )
        return
    expiry = None
    if len(args) >= 3:
        dur = args[2].lower()
        try:
            if dur == "permanent":
                expiry = None
            elif dur.endswith("d"):
                expiry = datetime.utcnow() + timedelta(days=int(dur[:-1]))
            elif dur.endswith("w"):
                expiry = datetime.utcnow() + timedelta(weeks=int(dur[:-1]))
            elif dur.endswith("m"):
                expiry = datetime.utcnow() + timedelta(days=30 * int(dur[:-1]))
            elif dur.endswith("h"):
                expiry = datetime.utcnow() + timedelta(hours=int(dur[:-1]))
        except Exception:
            await update.effective_message.reply_text(
                "<b>❌ Invalid duration.</b> Use: 7d, 2w, 1m, or permanent",
                parse_mode=ParseMode.HTML
            )
            return

    from database_dual import add_poster_premium
    add_poster_premium(target, rank, expiry)
    exp_str = expiry.strftime("%Y-%m-%d %H:%M UTC") if expiry else "Permanent"
    await update.effective_message.reply_text(
        f"<b>✅ Premium Added</b>\n\n"
        f"User: <code>{target}</code>\n"
        f"Rank: <b>{rank.title()}</b>\n"
        f"Expires: <b>{exp_str}</b>",
        parse_mode=ParseMode.HTML,
    )
    try:
        lim = POSTER_TASK_LIMITS.get(rank, 20)
        await context.bot.send_message(
            target,
            f"<b>🎉 Congratulations!</b>\n\n"
            f"You've been upgraded to <b>{rank.title()} Premium</b>!\n"
            f"Daily limit: <b>{lim}</b> posters\n"
            f"Expires: <b>{exp_str}</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def cmd_remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/remove_premium <user_id> — admin only."""
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return
    if not context.args:
        await update.effective_message.reply_text(
            "<b>Usage:</b> /remove_premium &lt;user_id&gt;", parse_mode=ParseMode.HTML
        )
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("<b>❌ Invalid user ID.</b>", parse_mode=ParseMode.HTML)
        return
    from database_dual import remove_poster_premium
    remove_poster_premium(target)
    await update.effective_message.reply_text(
        f"<b>✅ Premium removed</b> for user <code>{target}</code>.",
        parse_mode=ParseMode.HTML,
    )
    try:
        await context.bot.send_message(
            target, "<b>ℹ️ Your premium plan has been removed by the administrator.</b>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass


async def cmd_premium_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/premium_list — admin only."""
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return
    from database_dual import get_all_poster_premium
    users = get_all_poster_premium()
    if not users:
        await update.effective_message.reply_text(
            "<b>📋 No premium users.</b>", parse_mode=ParseMode.HTML
        )
        return
    lines = ["<b>💎 Premium Users:</b>\n"]
    for u in users[:30]:
        uid2 = u.get("user_id", "?")
        rank = u.get("rank", "?")
        exp = u.get("expiry_time")
        exp_str = exp.strftime("%Y-%m-%d") if exp else "Permanent"
        lines.append(f"• <code>{uid2}</code> — <b>{rank.title()}</b> (exp: {exp_str})")
    await update.effective_message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.HTML
    )
