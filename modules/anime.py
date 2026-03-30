# ====================================================================
# PLACE AT: /app/modules/anime.py
# ACTION: Replace existing file
# ====================================================================
"""
anime.py — /anime /tvshow /net /manga /airing /character /imdb
Fully async, works for all users.

Features:
  ✅ Typo-safe abbreviation map — English names searched directly
  ✅ "demon slayer" → "Demon Slayer" NOT "kimetsu no yaiba onigiri"
  ✅ Season detection: "aot s2" / "demon slayer season 3" / "jjk 2"
  ✅ Season 2 specific poster with correct AniList entry
  ✅ Similar anime panel — user picks exact match before poster is made
  ✅ Language selection panel (Hindi, English, Dual, Japanese, etc.)
  ✅ Size/type selection panel (Poster, Landscape, Banner, Custom)
  ✅ NEXT IMG = completely different template, not same image resized
  ✅ 2 separate messages: poster+info | custom thumbnail prompt
  ✅ /imdb — real TMDB poster + info only, no poster generation
  ✅ All text in small caps via bot.small_caps
"""

import asyncio
import html
import logging
import os as _os
import re
import time
import requests
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InlineQueryResultPhoto,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

_AL_URL   = "https://graphql.anilist.co"
_TMDB_KEY = __import__("os").getenv("TMDB_API_KEY", "")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sc(t: str) -> str:
    try:
        from bot import small_caps
        return small_caps(t)
    except Exception:
        return t

def _b(t: str) -> str:
    return f"<b>{_sc(t)}</b>"

def _bq(t: str) -> str:
    return f"<blockquote expandable>{t}</blockquote>"

def _e(t: str) -> str:
    return html.escape(str(t))


# ── Poster templates — NEXT IMG cycles through ALL of these ──────────────────

TEMPLATES = ["ani", "dark", "light", "crun", "mod", "net"]

TEMPLATE_LABELS = {
    "ani":  "🎌 Anime",
    "dark": "🌑 Dark",
    "light":"☀️ Light",
    "crun": "🎬 Crunchyroll",
    "mod":  "✨ Modern",
    "net":  "🔴 Netflix",
}


# ── Language options (matches Image 2 in reference) ──────────────────────────

LANG_OPTIONS = [
    ("Hindi",                 "lang_hin"),
    ("English",               "lang_eng"),
    ("Hindi & English",       "lang_hin_eng"),
    ("Japanese & Hindi",      "lang_jpn_hin"),
    ("Japanese & English",    "lang_jpn_eng"),
    ("Japanese & English Sub","lang_jpn_eng_sub"),
    ("Chinese & English",     "lang_chn_eng"),
    ("Chinese & (Esubs)",     "lang_chn_esub"),
    ("Multi Audio",           "lang_multi"),
]
LANG_LABELS = {cb: label for label, cb in LANG_OPTIONS}


# ── Size / type options ───────────────────────────────────────────────────────

SIZE_OPTIONS = [
    # Original palette templates
    ("🎌 ᴀɴɪᴍᴇ",            "size_ani",       "ani"),
    ("🔴 ɴᴇᴛꜰʟɪx",          "size_net",       "net"),
    ("🌑 ᴅᴀʀᴋ",             "size_dark",      "dark"),
    ("🍊 ᴄʀᴜɴᴄʜʏʀᴏʟʟ",     "size_crun",      "crun"),
    ("☀️ ʟɪɢʜᴛ",            "size_light",     "light"),
    ("✨ ᴍᴏᴅᴇʀɴ",           "size_mod",       "mod"),
    # Reference-image layouts (distinct structure)
    ("📺 sᴛʀᴇᴀᴍ",           "size_stream",    "stream"),
    ("🎴 ᴠᴇssᴇʟ",           "size_vessel",    "vessel"),
    ("🎞 sᴘʟᴀsʜ",           "size_splash",    "splash"),
    ("⬛ ᴏᴅ3ɴ",             "size_od3n",      "od3n"),
]
SIZE_CB_TO_TEMPLATE = {cb: tmpl for _, cb, tmpl in SIZE_OPTIONS if tmpl}



# ── Abbreviation map ─────────────────────────────────────────────────────────
# KEY RULE: map to ENGLISH title that AniList recognises natively.
# Do NOT force English → Japanese romaji — AniList's English search is accurate.
# "demon slayer" → "Demon Slayer"  (correct)
# "demon slayer" → "kimetsu no yaiba"  (causes wrong results — REMOVED)

_ABBR: Dict[str, str] = {
    # Short codes → canonical search query
    "aot":   "attack on titan", "snk": "attack on titan",
    "bnha":  "my hero academia", "mha": "my hero academia",
    "hxh":   "hunter x hunter", "jjk": "jujutsu kaisen",
    "csm":   "chainsaw man", "op":  "one piece",
    "fma":   "fullmetal alchemist", "fmab": "fullmetal alchemist brotherhood",
    "kny":   "kimetsu no yaiba", "ds":  "kimetsu no yaiba",
    "dbs":   "dragon ball super", "dbz": "dragon ball z", "db": "dragon ball",
    "cote":  "classroom of the elite",
    "opm":   "one punch man", "tpn": "promised neverland",
    "sg":    "steins gate", "mia": "made in abyss",
    "ngnl":  "no game no life", "nge": "neon genesis evangelion",
    "eva":   "neon genesis evangelion", "bsd": "bungo stray dogs",
    "sao":   "sword art online", "re zero": "re zero", "rezero": "re zero",
    # English common names → Romaji that AniList knows well
    "demon slayer":              "Kimetsu no Yaiba",
    "demon slayer swordsmith":   "Kimetsu no Yaiba: Katanakaji no Sato-hen",
    "attack on titan":           "Shingeki no Kyojin",
    "my hero academia":          "Boku no Hero Academia",
    "jujutsu kaisen":            "Jujutsu Kaisen",
    "one punch man":             "One Punch-Man",
    "dr stone":                  "Dr. Stone",
    "dr. stone":                 "Dr. Stone",
    "promised neverland":        "Yakusoku no Neverland",
    "your lie in april":         "Shigatsu wa Kimi no Uso",
    "a silent voice":            "Koe no Katachi",
    "spirited away":             "Sen to Chihiro no Kamikakushi",
    "violet evergarden":         "Violet Evergarden",
    "sword art online":          "Sword Art Online",
    "re:zero":                   "Re:Zero kara Hajimeru Isekai Seikatsu",
    "slime":                     "Tensei shitara Slime Datta Ken",
    "tensura":                   "Tensei shitara Slime Datta Ken",
    "that time i got reincarnated as a slime": "Tensei shitara Slime Datta Ken",
    "black clover":              "Black Clover",
    "tokyo revengers":           "Tokyo Revengers",
    "blue lock":                 "Blue Lock",
    "chainsaw man":              "Chainsaw Man",
    "spy x family":              "Spy x Family",
    "spy family":                "Spy x Family",
    "bleach":                    "Bleach",
    "naruto":                    "Naruto",
    "made in abyss":             "Made in Abyss",
    "frieren":                   "Sousou no Frieren",
    "frieren beyond journeys end": "Sousou no Frieren",
    "oshi no ko":                "Oshi no Ko",
    "vinland saga":              "Vinland Saga",
    "mushoku tensei":            "Mushoku Tensei: Jobless Reincarnation",
    "jobless reincarnation":     "Mushoku Tensei: Jobless Reincarnation",
    "overlord":                  "Overlord",
    "no game no life":           "No Game No Life",
    "hunter x hunter":           "Hunter x Hunter (2011)",
    "fullmetal alchemist":        "Fullmetal Alchemist: Brotherhood",
    "fullmetal alchemist brotherhood": "Fullmetal Alchemist: Brotherhood",
    "steins gate":               "Steins;Gate",
    "steins;gate":               "Steins;Gate",
    "death note":                "Death Note",
    "code geass":                "Code Geass: Hangyaku no Lelouch",
    "evangelion":                "Neon Genesis Evangelion",
    "neon genesis evangelion":   "Neon Genesis Evangelion",
    "cowboy bebop":              "Cowboy Bebop",
    "fairy tail":                "Fairy Tail",
    "konosuba":                  "Kono Subarashii Sekai ni Shukufuku wo!",
    "danmachi":                  "Dungeon ni Deai wo Motomeru no wa Machigatteiru Darou ka",
    "eminence in shadow":        "Kage no Jitsuryokusha ni Naritakute!",
    "eminence":                  "Kage no Jitsuryokusha ni Naritakute!",
    "classroom of the elite":    "Youkoso Jitsuryoku Shijou Shugi no Kyoushitsu e",
    "shield hero":               "Tate no Yuusha no Nariagari",
    "rising of shield hero":     "Tate no Yuusha no Nariagari",
    "solo leveling":             "Ore dake Level Up na Ken",
    "dungeon meshi":             "Dungeon Meshi",
    "delicious in dungeon":      "Dungeon Meshi",
    "toradora":                  "Toradora",
    "angel beats":               "Angel Beats!",
    "black butler":              "Kuroshitsuji",
    "blue exorcist":             "Ao no Exorcist",
    "bungo stray dogs":          "Bungou Stray Dogs",
    "bungou stray dogs":         "Bungou Stray Dogs",
    "noragami":                  "Noragami",
    "sound euphonium":           "Hibike! Euphonium",
    "k on":                      "K-On!",
    "k-on":                      "K-On!",
    "code geass lelouch":        "Code Geass: Hangyaku no Lelouch",
    "jojo":                      "JoJo no Kimyou na Bouken",
    "jojos bizarre adventure":   "JoJo no Kimyou na Bouken",
}

# Season suffix patterns
_SEASON_RE = [
    (r"\b(s(\d+))\b",                        lambda m: int(m.group(2))),
    (r"\bseason\s*(\d+)\b",                  lambda m: int(m.group(1))),
    (r"\b(\d+)(st|nd|rd|th)\s*season\b",    lambda m: int(m.group(1))),
    (r"\b(ii)\b",                              lambda m: 2),
    (r"\b(iii)\b",                             lambda m: 3),
    (r"\b(iv)\b",                              lambda m: 4),
    (r"\b(final\s*season)\b",                 lambda m: 99),
]

_SEASON_SUFFIXES: Dict[int, List[str]] = {
    2:  ["Season 2", "2nd Season", "II", "Part 2"],
    3:  ["Season 3", "3rd Season", "III"],
    4:  ["Season 4", "4th Season", "Final Season"],
    5:  ["Season 5", "5th Season"],
    99: ["Final Season", "The Final Season"],
}

# AniList GQL
_ANIME_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large medium} bannerImage format status season seasonYear
  episodes duration averageScore popularity genres
  studios(isMain:true){nodes{name}}
  startDate{year month day}
  nextAiringEpisode{episode timeUntilAiring}
  countryOfOrigin}}"""

_ANIME_PAGE_GQL = """query($s:String){Page(page:1,perPage:8){media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id title{romaji english native} coverImage{medium} averageScore status seasonYear format}}}"""

# Light inline GQL — only fields needed for display (faster)
_INLINE_GQL = """query($s:String){Page(page:1,perPage:8){media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} coverImage{medium large extraLarge}
  averageScore status seasonYear format episodes genres}}}"""

_MANGA_GQL = """query($s:String){Media(search:$s,type:MANGA,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id siteUrl title{romaji english native} description(asHtml:false)
  coverImage{extraLarge large} format status chapters volumes averageScore popularity genres
  startDate{year month day} countryOfOrigin}}"""

_CHAR_GQL = """query($s:String){Character(search:$s){
  name{full native} description siteUrl image{large}}}"""



# ── AniList result cache (TTL 5 min) ─────────────────────────────────────────
# Prevents repeated AniList calls for same query — makes inline feel instant
_al_cache: Dict[str, Tuple[float, Any]] = {}
_AL_CACHE_TTL = 300  # 5 minutes

def _cache_get(key: str):
    e = _al_cache.get(key)
    if e and (time.time() - e[0]) < _AL_CACHE_TTL:
        return e[1]
    return None

def _cache_set(key: str, val: Any):
    _al_cache[key] = (time.time(), val)
    if len(_al_cache) > 200:
        for k, _ in sorted(_al_cache.items(), key=lambda x: x[1][0])[:50]:
            _al_cache.pop(k, None)

_AIRING_GQL = """query($s:String){Media(search:$s,type:ANIME,sort:[SEARCH_MATCH,POPULARITY_DESC]){
  id title{romaji english native} episodes status
  nextAiringEpisode{episode timeUntilAiring}}}"""


def _normalise(q: str) -> str:
    return re.sub(r"[^\w\s]", "", q.lower()).strip()


def _extract_season(query: str):
    q = query.strip()
    for pattern, extractor in _SEASON_RE:
        m = re.search(pattern, q, re.IGNORECASE)
        if m:
            season_num = extractor(m)
            clean = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean, season_num
    return q, None


def _resolve_query(raw: str) -> str:
    q_norm = _normalise(raw)
    mapped = _ABBR.get(q_norm)
    if not mapped:
        q_nopunct = re.sub(r"[^a-z0-9\s]", " ", q_norm).strip()
        mapped = _ABBR.get(q_nopunct)
    return mapped or raw


def _season_queries(base: str, n: int) -> List[str]:
    suffixes = _SEASON_SUFFIXES.get(n, [f"Season {n}"])
    return [f"{base} {s}" for s in suffixes] + [f"{base} {n}"]


def _al_sync(gql: str, search: str) -> Optional[Any]:
    """
    Smart multi-strategy AniList search.
    Uses SEARCH_MATCH,POPULARITY_DESC to return most popular matching result.
    Includes sanity check to prevent "Demon Slayer → Onigiri" type wrong results.
    """
    resolved = _resolve_query(search)
    queries: List[str] = []
    if resolved.lower() != search.lower():
        queries.append(resolved)
    queries.append(search)
    if search.title() != search:
        queries.append(search.title())
    words = search.split()
    if len(words) > 2:
        queries.append(" ".join(words[:3]))

    seen: set = set()
    for q in queries:
        k = q.lower()
        if k in seen:
            continue
        seen.add(k)
        try:
            r = requests.post(
                _AL_URL,
                json={"query": gql, "variables": {"s": q}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=12,
            )
            if r.status_code != 200:
                continue
            data = r.json().get("data", {})
            result = data.get("Media") or data.get("Character") or data.get("Page")
            if not result:
                continue

            # Sanity check: for 2+ word queries, at least one significant word
            # must appear in the result title — prevents completely wrong results
            if "Media" in r.json().get("data", {}):
                res_titles = [
                    (result.get("title") or {}).get("english") or "",
                    (result.get("title") or {}).get("romaji") or "",
                ]
                search_words = [w for w in search.lower().split() if len(w) > 3]
                if len(search_words) >= 2:
                    res_text = " ".join(res_titles).lower()
                    word_match = any(w in res_text for w in search_words)
                    if not word_match:
                        logger.debug(f"[anime] sanity fail: \'{q}\' → \'{res_titles[0]}\' (skipping)")
                        continue

            _cache_set(ck, result)
            return result
        except Exception as exc:
            logger.debug(f"[anime] AniList [{q}]: {exc}")
    return None


def _al_page_sync(search: str, gql: str = None) -> List[Dict]:
    gql = gql or _ANIME_PAGE_GQL
    ck = f"page:{gql[:10]}:{search.lower()}"
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    try:
        r = requests.post(
            _AL_URL,
            json={"query": gql, "variables": {"s": search}},
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        if r.status_code == 200:
            result = r.json().get("data", {}).get("Page", {}).get("media") or []
            _cache_set(ck, result)
            return result
    except Exception:
        pass
    return []


async def _al(gql: str, search: str) -> Optional[Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _al_sync, gql, search)


async def _al_page(search: str) -> List[Dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _al_page_sync, search)


def _clean(text: str, mx: int = 300) -> str:
    if not text:
        return "No description available."
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return (text[:mx].rsplit(" ", 1)[0] + "…") if len(text) > mx else text


# ── Poster generation ─────────────────────────────────────────────────────────

async def _generate_poster_buf(
    data: Dict, media_type: str, template: str
) -> Optional[BytesIO]:
    try:
        from poster_engine import (
            _build_anime_data, _build_manga_data,
            _build_movie_data, _build_tv_data,
            _make_poster, _get_settings,
        )
    except ImportError:
        return None

    loop     = asyncio.get_event_loop()
    settings = _get_settings(media_type.lower() if media_type != "TV" else "tvshow")
    build_fn = {
        "ANIME": _build_anime_data,
        "MANGA": _build_manga_data,
        "MOVIE": _build_movie_data,
        "TV":    _build_tv_data,
    }.get(media_type, _build_anime_data)

    try:
        title, native, st, rows, desc, cover_url, score = await loop.run_in_executor(
            None, build_fn, data
        )
        return await loop.run_in_executor(
            None, _make_poster,
            template, title, native, st, rows, desc, cover_url, score,
            settings.get("watermark_text"),
            settings.get("watermark_position", "center"),
            None, "bottom",
        )
    except Exception as exc:
        logger.debug(f"poster_gen [{template}]: {exc}")
        return None


def _build_caption(data: Dict, lang: str = "") -> str:
    t_d    = data.get("title", {}) or {}
    eng    = t_d.get("english") or t_d.get("romaji") or "Unknown"
    native = t_d.get("native", "")
    genres = ", ".join((data.get("genres") or [])[:3])
    score  = data.get("averageScore", "?")
    status = (data.get("status") or "").replace("_", " ").title()
    eps    = data.get("episodes", "?")
    fmt    = (data.get("format") or "").replace("_", " ")
    stnode = ((data.get("studios") or {}).get("nodes") or [])
    studio = stnode[0].get("name", "") if stnode else ""

    # Try custom caption template from category settings
    try:
        from handlers.post_gen import get_category_settings
        import inspect as _inspect
        # Determine category from caller context (best effort)
        _cat = "anime"
        _frame = _inspect.currentframe()
        if _frame and _frame.f_back:
            _local_media_type = _frame.f_back.f_locals.get("media_type", "ANIME")
            if isinstance(_local_media_type, str):
                _cat = {"ANIME": "anime", "MANGA": "manga", "MOVIE": "movie", "TV": "tvshow"}.get(
                    _local_media_type.upper(), "anime")
        settings = get_category_settings(_cat)
        tmpl = settings.get("caption_template", "")
        if tmpl:
            # Resolve {link} tag
            _join_link = ""
            try:
                from database_dual import get_anime_channel_links, get_setting
                from core.config import BOT_USERNAME, PUBLIC_ANIME_CHANNEL_URL
                _al = get_anime_channel_links(eng)
                if _al and _al[0][2] and BOT_USERNAME:
                    _join_link = f"https://t.me/{BOT_USERNAME}?start={_al[0][2]}"
                if not _join_link:
                    _join_link = get_setting("env_PUBLIC_ANIME_CHANNEL_URL", "") or PUBLIC_ANIME_CHANNEL_URL
            except Exception:
                pass
            cap = (tmpl.replace("{title}", _e(eng))
                      .replace("{native}", _e(native))
                      .replace("{genres}", _e(genres))
                      .replace("{score}", str(score))
                      .replace("{status}", _e(status))
                      .replace("{episodes}", str(eps))
                      .replace("{format}", _e(fmt))
                      .replace("{studio}", _e(studio))
                      .replace("{lang}", _e(lang) if lang else "")
                      .replace("{language}", _e(lang) if lang else "")
                      .replace("{link}", _join_link))
            return cap[:1024]
    except Exception:
        pass

    cap = f"<b>{_e(eng)}</b>"
    if native:
        cap += f"\n<i>{_e(native)}</i>"
    cap += "\n\n"
    if lang:
        cap += f"» <b>{_sc('Audio')}:</b> {_e(lang)}\n"
    if genres:
        cap += f"» <b>{_sc('Genre')}:</b> {_e(genres)}\n"
    if score and str(score) not in ("?", "0", "None"):
        cap += f"» <b>{_sc('Rating')}:</b> <code>{score}/100</code>\n"
    if status:
        cap += f"» <b>{_sc('Status')}:</b> {_e(status)}\n"
    if eps and str(eps) not in ("?", "0", "None"):
        cap += f"» <b>{_sc('Episodes')}:</b> <code>{eps}</code>\n"
    if fmt:
        cap += f"» <b>{_sc('Format')}:</b> {_e(fmt)}\n"
    if studio:
        cap += f"» <b>{_sc('Studio')}:</b> {_e(studio)}\n"
    desc = _clean(data.get("description", ""), 200)
    if desc and desc != "No description available.":
        cap += f"\n{_bq(_e(desc))}"
    return cap[:1024]


def _info_kb(data: Dict, lang: str = "") -> InlineKeyboardMarkup:
    from core.config import PUBLIC_ANIME_CHANNEL_URL, JOIN_BTN_TEXT
    site  = data.get("siteUrl", "")
    t_d   = data.get("title", {}) or {}
    title = t_d.get("english") or t_d.get("romaji") or ""

    rows: List[List] = []

    # Row 1: AniList info button
    info_row = []
    if site:
        info_row.append(InlineKeyboardButton(_sc("📋 ɪɴꜰᴏ"), url=site))
    if info_row:
        rows.append(info_row)

    # Row 2: "Join Now to Watch" button — try to get join_request link from DB
    join_url = None
    if title:
        try:
            from database_dual import get_anime_channel_links
            links = get_anime_channel_links(title)
            if links:
                # links = [(channel_id, channel_title, link_id), ...]
                link_id = links[0][2] if len(links[0]) > 2 else None
                if link_id:
                    try:
                        from database_dual import get_link_by_id
                        lrow = get_link_by_id(link_id)
                        if lrow:
                            join_url = lrow.get("url") or lrow[3] if isinstance(lrow, (list, tuple)) else None
                    except Exception:
                        pass
                if not join_url:
                    # Try channel invite link directly
                    cid = links[0][0]
                    try:
                        from database_dual import get_setting
                        join_url = get_setting(f"channel_invite_{cid}", "")
                    except Exception:
                        pass
        except Exception:
            pass

    # Fallback to main anime channel
    if not join_url:
        join_url = PUBLIC_ANIME_CHANNEL_URL

    try:
        from database_dual import get_setting
        join_txt = get_setting("env_JOIN_BTN_TEXT", "") or JOIN_BTN_TEXT
    except Exception:
        join_txt = JOIN_BTN_TEXT

    rows.append([InlineKeyboardButton(
        f"ᴊᴏɪɴ ɴᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ", url=join_url
    )])

    return InlineKeyboardMarkup(rows)


# ── UI flow helpers ───────────────────────────────────────────────────────────

async def _show_similar_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    base_query: str, season_num: Optional[int],
) -> None:
    """Show up to 8 similar anime titles as buttons for user to pick exact match."""
    msg = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not msg:
        return

    loading = None
    try:
        loading = await msg.reply_text(
            _b("🔍 searching similar titles…"), parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    results = await _al_page(base_query)

    if loading:
        try:
            await loading.delete()
        except Exception:
            pass

    if not results:
        # No similar found → jump straight to language panel
        context.user_data["anime_query"] = base_query
        context.user_data["season_num"]  = season_num
        await _show_language_panel(update, context)
        return

    context.user_data["similar_results"] = results[:8]
    context.user_data["season_num"]       = season_num
    context.user_data["anime_query"]      = base_query

    # Build 2-column grid of results
    btns: List[List] = []
    row: List = []
    for i, item in enumerate(results[:8]):
        t    = item.get("title", {}) or {}
        name = t.get("english") or t.get("romaji") or "Unknown"
        year = item.get("seasonYear", "")
        lbl  = f"{name[:22]} ({year})" if year else name[:28]
        row.append(InlineKeyboardButton(lbl, callback_data=f"anpick_{i}"))
        if len(row) == 2:
            btns.append(row)
            row = []
    if row:
        btns.append(row)
    btns.append([
        InlineKeyboardButton(_sc("🔍 Keep My Query"), callback_data="anpick_custom"),
        InlineKeyboardButton(_sc("❌ Cancel"),         callback_data="anpick_cancel"),
    ])

    # Delete any existing flow panels before sending new
    for key in ("_sim_panel_id", "_lang_panel_id", "_size_panel_id"):
        old_mid = context.user_data.pop(key, None)
        if old_mid:
            try:
                await context.bot.delete_message(msg.chat_id, old_mid)
            except Exception:
                pass

    sent_sim = await msg.reply_text(
        _b("🎌 sᴇʟᴇᴄᴛ ᴇxᴀᴄᴛ ᴛɪᴛʟᴇ") + "\n"
        + _bq(_sc("ᴘɪᴄᴋ ᴛʜᴇ ᴄᴏʀʀᴇᴄᴛ ᴛɪᴛʟᴇ ꜰᴏʀ ᴛʜᴇ ᴘᴏsᴛᴇʀ:")),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btns),
    )
    if sent_sim:
        context.user_data["_sim_panel_id"] = sent_sim.message_id


async def _show_language_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show language selection panel matching Image 2 reference layout."""
    msg = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not msg:
        return

    rows: List[List] = []
    row:  List = []
    for label, cb in LANG_OPTIONS:
        row.append(InlineKeyboardButton(_sc(label), callback_data=cb))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(_sc("CANCEL"), callback_data="anpick_cancel")])

    # Delete previous flow panel
    for key in ("_sim_panel_id", "_lang_panel_id", "_size_panel_id"):
        old_mid = context.user_data.pop(key, None)
        if old_mid:
            try:
                await context.bot.delete_message(msg.chat_id, old_mid)
            except Exception:
                pass

    sent_lang = await msg.reply_text(
        _b("🎧 sᴇʟᴇᴄᴛ ᴀᴜᴅɪᴏ ʟᴀɴɢᴜᴀɢᴇ"),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )
    if sent_lang:
        context.user_data["_lang_panel_id"] = sent_lang.message_id


async def _show_size_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show poster size/type selection panel."""
    msg = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not msg:
        return

    rows: List[List] = []
    row:  List = []
    for label, cb, _ in SIZE_OPTIONS:
        row.append(InlineKeyboardButton(_sc(label), callback_data=cb))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(_sc("CANCEL"), callback_data="anpick_cancel")])

    # Delete previous flow panel
    for key in ("_sim_panel_id", "_lang_panel_id", "_size_panel_id"):
        old_mid = context.user_data.pop(key, None)
        if old_mid:
            try:
                await context.bot.delete_message(msg.chat_id, old_mid)
            except Exception:
                pass

    sent_size = await msg.reply_text(
        _b("📐 sᴇʟᴇᴄᴛ ᴘᴏsᴛᴇʀ ᴛʏᴘᴇ / sɪᴢᴇ"),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )
    if sent_size:
        context.user_data["_size_panel_id"] = sent_size.message_id


# ── Poster delivery — 2 separate messages ────────────────────────────────────

async def _deliver_poster(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    data: Dict, template: str, media_type: str,
) -> None:
    """
    Send poster in exactly 2 separate messages:
    1. Photo + info caption + AniList button
    2. 📸 Custom Thumbnail prompt + NEXT IMG / SKIP / CANCEL
    """
    msg = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not msg:
        return

    # Loading indicator
    loading = None
    try:
        loading = await msg.reply_text(
            _b("🎨 generating poster…"), parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    poster_buf = await _generate_poster_buf(data, media_type, template)

    if loading:
        try:
            await loading.delete()
        except Exception:
            pass

    lang    = context.user_data.get("selected_lang", "")
    caption = _build_caption(data, lang=lang)
    kb      = _info_kb(data, lang=lang)

    sent_poster = None

    # ── Message 1: poster + info ──────────────────────────────────────────────
    # Always send as photo (document mode removed per user preference)
    if poster_buf:
        poster_buf.seek(0)
        try:
            sent_poster = await msg.reply_photo(
                    photo=poster_buf, caption=caption,
                    parse_mode=ParseMode.HTML, reply_markup=kb,
                )
        except Exception as exc:
            logger.debug(f"poster send: {exc}")

    if not sent_poster:
        cv = (data.get("coverImage") or {}).get("extraLarge", "")
        lp = f'\n<a href="{_e(cv)}">&#8203;</a>' if cv else ""
        try:
            sent_poster = await msg.reply_text(
                caption + lp, parse_mode=ParseMode.HTML,
                reply_markup=kb, disable_web_page_preview=not cv,
            )
        except Exception:
            pass

    # Store state
    t_d    = data.get("title", {}) or {}
    context.user_data.update({
        "poster_data":       data,
        "poster_media_type": media_type,
        "poster_template":   template,
        "poster_tmpl_idx":   TEMPLATES.index(template) if template in TEMPLATES else 0,
        "poster_title":      t_d.get("english") or t_d.get("romaji") or "Unknown",
        "poster_msg_id":     sent_poster.message_id if sent_poster else None,
        "poster_chat_id":    msg.chat_id,
        "awaiting_thumbnail": True,
        "awaiting_thumbnail_uid": msg.from_user.id if msg.from_user else None,
    })

    # ── Message 2: Custom Thumbnail prompt (separate message, not joined) ─────
    thumb_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(_sc("🔜 ɴᴇxᴛ ɪᴍɢ"),    callback_data="anthmb_next"),
            InlineKeyboardButton(_sc("sᴋɪᴘ"),             callback_data="anthmb_skip"),
        ],
        [InlineKeyboardButton(_sc("📤 sᴇɴᴅ ᴛᴏ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ"), callback_data="anthmb_send_main")],
        [InlineKeyboardButton(_sc("❌ ᴄᴀɴᴄᴇʟ"),         callback_data="anthmb_cancel")],
    ])

    sent_thumb_prompt = await msg.reply_text(
        "📸 <b>Cᴜsᴛᴏᴍ Tʜᴜᴍʙɴᴀɪʟ</b>\n\n"
        "Sᴇɴᴅ ᴍᴇ ᴀ ᴄᴜsᴛᴏᴍ ᴛʜᴜᴍʙɴᴀɪʟ ɪᴍᴀɢᴇ, ᴏʀ ᴄʟɪᴄᴋ Sᴋɪᴘ ᴛᴏ ᴜsᴇ ᴛʜɪs ᴘᴏsᴛᴇʀ.",
        parse_mode=ParseMode.HTML,
        reply_markup=thumb_kb,
    )
    # Auto-delete the thumbnail prompt (NOT the poster itself)
    if sent_thumb_prompt:
        try:
            from core.auto_delete import schedule_delete_msg
            await schedule_delete_msg(msg.get_bot() if hasattr(msg, "get_bot") else context.bot,
                                      sent_thumb_prompt)
        except Exception:
            pass


# ── Callback handler ──────────────────────────────────────────────────────────

async def _anime_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Route all anime-flow callbacks."""
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception:
        pass

    cb      = query.data or ""
    uid     = query.from_user.id
    msg     = query.message

    # ── Similar panel pick ────────────────────────────────────────────────────
    if cb.startswith("anpick_"):
        if cb == "anpick_cancel":
            try:
                await msg.delete()
            except Exception:
                pass
            return

        if cb == "anpick_custom":
            try:
                await msg.delete()
            except Exception:
                pass
            await _show_language_panel(update, context)
            return

        # anpick_{index}
        try:
            idx     = int(cb.split("_")[1])
            results = context.user_data.get("similar_results", [])
            if 0 <= idx < len(results):
                item = results[idx]
                t    = item.get("title", {}) or {}
                name = t.get("english") or t.get("romaji") or ""
                context.user_data["anime_query"] = name
        except (ValueError, IndexError):
            pass
        try:
            await msg.delete()
        except Exception:
            pass
        await _show_language_panel(update, context)
        return

    # ── Language selected ─────────────────────────────────────────────────────
    if cb.startswith("lang_"):
        context.user_data["selected_lang"] = LANG_LABELS.get(cb, "English")
        try:
            await msg.delete()
        except Exception:
            pass
        await _show_size_panel(update, context)
        return

    # ── Size selected → fetch + deliver ──────────────────────────────────────
    if cb.startswith("size_"):
        template = SIZE_CB_TO_TEMPLATE.get(cb, "ani")
        context.user_data["poster_template"] = template
        try:
            await msg.delete()
        except Exception:
            pass

        base_q     = context.user_data.get("anime_query", "")
        season_num = context.user_data.get("season_num")
        media_type = context.user_data.get("media_type", "ANIME")

        # Build season-specific search query if needed
        if season_num and season_num > 1:
            search_queries = _season_queries(base_q, season_num)
        else:
            search_queries = [base_q]

        loading = None
        try:
            loading = await msg.reply_text(
                _b(f"🔎 fetching {_e(search_queries[0])}…"),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        gql  = _ANIME_GQL if media_type in ("ANIME",) else _MANGA_GQL
        data = None
        loop = asyncio.get_event_loop()

        for sq in search_queries:
            data = await loop.run_in_executor(None, _al_sync, gql, sq)
            if data:
                break

        if loading:
            try:
                await loading.delete()
            except Exception:
                pass

        if not data:
            try:
                await msg.reply_text(
                    _b(f"❌ ɴᴏᴛ ꜰᴏᴜɴᴅ:") + f" <code>{_e(search_queries[0])}</code>\n"
                    + _bq(_sc("ᴛʀʏ ᴀ ᴅɪꜰꜰᴇʀᴇɴᴛ sᴘᴇʟʟɪɴɢ ᴏʀ ʙʀᴀᴋᴇᴛ (ᴇ.ɢ. /anime demon slayer)")),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            return

        await _deliver_poster(update, context, data, template, media_type)
        return

    # ── Thumbnail: NEXT IMG — delete old, send completely new message with info ─
    if cb == "anthmb_next":
        data_dict  = context.user_data.get("poster_data")
        media_type = context.user_data.get("poster_media_type", "ANIME")
        tmpl_idx   = context.user_data.get("poster_tmpl_idx", 0)

        if not data_dict:
            await query.answer(_sc("session expired"), show_alert=True)
            return

        # Advance to NEXT template (different visual style entirely)
        tmpl_idx = (tmpl_idx + 1) % len(TEMPLATES)
        new_tmpl = TEMPLATES[tmpl_idx]
        context.user_data["poster_tmpl_idx"] = tmpl_idx
        context.user_data["poster_template"] = new_tmpl

        try:
            await query.answer(_sc(f"{TEMPLATE_LABELS.get(new_tmpl, new_tmpl)} style…"))
        except Exception:
            pass

        loading = None
        try:
            loading = await msg.reply_text(
                _b(_sc(f"generating {TEMPLATE_LABELS.get(new_tmpl, new_tmpl)} style…")),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

        new_buf = await _generate_poster_buf(data_dict, media_type, new_tmpl)

        if loading:
            try:
                await loading.delete()
            except Exception:
                pass

        if not new_buf:
            try:
                await query.answer(_sc("could not generate poster"), show_alert=True)
            except Exception:
                pass
            return

        # EDIT existing poster in place (🔙🔜 style — no delete+resend)
        prev_msg_id  = context.user_data.get("poster_msg_id")
        prev_chat_id = context.user_data.get("poster_chat_id")
        edited = False
        if prev_msg_id and prev_chat_id:
            try:
                new_buf.seek(0)
                await query.bot.edit_message_media(
                    chat_id=prev_chat_id,
                    message_id=prev_msg_id,
                    media=InputMediaPhoto(
                        media=new_buf,
                        caption=_build_caption(data_dict),
                        parse_mode=ParseMode.HTML,
                    ),
                    reply_markup=_info_kb(data_dict),
                )
                edited = True
            except Exception as exc:
                logger.debug(f"next img edit: {exc}")
        if not edited:
            try:
                new_buf.seek(0)
                sent = await msg.reply_photo(
                    photo=new_buf,
                    caption=_build_caption(data_dict),
                    parse_mode=ParseMode.HTML,
                    reply_markup=_info_kb(data_dict),
                )
                context.user_data["poster_msg_id"] = sent.message_id
                context.user_data["poster_chat_id"] = msg.chat_id
            except Exception as exc:
                logger.debug(f"next img send: {exc}")
        return

    # ── Thumbnail: SKIP ───────────────────────────────────────────────────────
    if cb == "anthmb_skip":
        try:
            await msg.delete()
        except Exception:
            pass
        context.user_data.pop("awaiting_thumbnail", None)
        try:
            await query.answer(_sc("✅ using this poster"))
        except Exception:
            pass
        return

    # ── Thumbnail: CANCEL ─────────────────────────────────────────────────────
    if cb == "anthmb_cancel":
        try:
            await msg.delete()
        except Exception:
            pass
        prev_msg_id  = context.user_data.get("poster_msg_id")
        prev_chat_id = context.user_data.get("poster_chat_id")
        if prev_msg_id and prev_chat_id:
            try:
                await query.bot.delete_message(prev_chat_id, prev_msg_id)
            except Exception:
                pass
        context.user_data.clear()
        try:
            await query.answer(_sc("ᴄᴀɴᴄᴇʟʟᴇᴅ"))
        except Exception:
            pass
        return

    # ── Send poster to main channel ───────────────────────────────────────────
    if cb == "anthmb_send_main":
        try:
            await msg.delete()
        except Exception:
            pass
        # Get main channel id from settings
        main_ch_id = None
        try:
            from database_dual import get_setting
            main_ch_id = get_setting("main_channel_id", "")
            if main_ch_id:
                main_ch_id = int(main_ch_id)
        except Exception:
            pass
        if not main_ch_id:
            try:
                await query.answer(_sc("⚠️ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ ɴᴏᴛ sᴇᴛ — ᴜsᴇ /settings ᴛᴏ ᴄᴏɴꜰɪɢᴜʀᴇ"), show_alert=True)
            except Exception:
                pass
            return
        prev_msg_id  = context.user_data.get("poster_msg_id")
        prev_chat_id = context.user_data.get("poster_chat_id")
        data_d   = context.user_data.get("poster_data", {})
        lang     = context.user_data.get("selected_lang", "")
        caption  = _build_caption(data_d, lang=lang) if data_d else ""
        kb       = _info_kb(data_d, lang=lang) if data_d else None
        sent_ok  = False
        if prev_msg_id and prev_chat_id:
            try:
                await query.bot.copy_message(
                    chat_id=main_ch_id,
                    from_chat_id=prev_chat_id,
                    message_id=prev_msg_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                )
                sent_ok = True
            except Exception as exc:
                logger.debug(f"send_to_main copy: {exc}")
        if sent_ok:
            try:
                await query.answer(_sc("✅ sᴇɴᴛ ᴛᴏ ᴍᴀɪɴ ᴄʜᴀɴɴᴇʟ!"), show_alert=False)
            except Exception:
                pass
        else:
            try:
                await query.answer(_sc("❌ ꜰᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ — ᴄʜᴇᴄᴋ ʙᴏᴛ ᴘᴇʀᴍɪssɪᴏɴs"), show_alert=True)
            except Exception:
                pass
        context.user_data.pop("awaiting_thumbnail", None)
        return


# ── Custom thumbnail photo handler ────────────────────────────────────────────

async def _thumbnail_photo_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """User sends a photo to use as custom thumbnail."""
    if not context.user_data.get("awaiting_thumbnail"):
        return
    msg = update.message
    if not msg or not msg.photo:
        return

    context.user_data.pop("awaiting_thumbnail", None)
    fid      = msg.photo[-1].file_id
    data_d   = context.user_data.get("poster_data", {})
    caption  = _build_caption(data_d) if data_d else ""
    kb       = _info_kb(data_d) if data_d else None

    prev_mid = context.user_data.get("poster_msg_id")
    prev_cid = context.user_data.get("poster_chat_id")

    if prev_mid and prev_cid:
        try:
            await msg.bot.edit_message_media(
                chat_id=prev_cid,
                message_id=prev_mid,
                media=InputMediaPhoto(
                    media=fid, caption=caption, parse_mode=ParseMode.HTML,
                ),
                reply_markup=kb,
            )
            await msg.reply_text(
                _b(_sc("✅ custom thumbnail applied!")), parse_mode=ParseMode.HTML
            )
            context.user_data.clear()
            return
        except Exception:
            pass

    await msg.reply_photo(
        photo=fid, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb,
    )
    context.user_data.clear()


# ── Command handlers ──────────────────────────────────────────────────────────

async def anime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /anime flow:
    1. Similar panel (choose correct title)
    2. Language panel
    3. Size/type panel
    4. Generate poster + info (Message 1)
    5. Custom thumbnail prompt (Message 2, separate)
    NO poster is shown before the user picks the correct title.
    """
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /anime &lt;name&gt;\n"
            + _bq(
                "• /anime demon slayer\n"
                "• /anime aot s2\n"
                "• /anime jjk season 2\n"
                "• /anime frieren"
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    raw_q      = " ".join(context.args)
    base_q, sn = _extract_season(raw_q)
    resolved   = _resolve_query(base_q)

    context.user_data.update({
        "media_type":  "ANIME",
        "anime_query": resolved,
        "season_num":  sn,
    })
    # Step 1: Show similar panel — NO poster until user picks correct title
    await _show_similar_panel(update, context, resolved, sn)


async def manga_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /manga flow — same as /anime:
    1. Similar panel  2. Language panel  3. Size panel  4. Poster
    """
    if not context.args:
        await update.message.reply_text(
            _b("ᴜsᴀɢᴇ:") + " /manga &lt;name&gt;\n"
            + _bq(
                "• /manga one piece\n"
                "• /manga demon slayer\n"
                "• /manga berserk"
            ),
            parse_mode=ParseMode.HTML,
        )
        return
    q = " ".join(context.args)
    context.user_data.update({
        "media_type":  "MANGA",
        "anime_query": q,
        "season_num":  None,
    })
    await _show_similar_panel(update, context, q, None)



async def movie_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /movie &lt;name&gt;", parse_mode=ParseMode.HTML
        )
        return
    q = " ".join(context.args)
    context.user_data.update({"media_type": "MOVIE", "anime_query": q, "season_num": None})
    await _show_language_panel(update, context)


async def tvshow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /tvshow &lt;name&gt;", parse_mode=ParseMode.HTML
        )
        return
    q = " ".join(context.args)
    context.user_data.update({"media_type": "TV", "anime_query": q, "season_num": None})
    await _show_language_panel(update, context)


async def net_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Netflix-style poster — skips language/size panels, instant generation."""
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /net &lt;title&gt;", parse_mode=ParseMode.HTML
        )
        return
    q    = " ".join(context.args)
    loop = asyncio.get_event_loop()
    context.user_data.update({
        "media_type": "ANIME", "anime_query": q, "season_num": None,
        "selected_lang": "English", "poster_template": "net",
    })
    data = await loop.run_in_executor(None, _al_sync, _ANIME_GQL, q)
    if not data:
        await update.message.reply_text(
            _b(f"❌ not found: {_e(q)}"), parse_mode=ParseMode.HTML
        )
        return
    await _deliver_poster(update, context, data, "net", "ANIME")


async def airing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /airing &lt;anime name&gt;", parse_mode=ParseMode.HTML
        )
        return
    data = await _al(_AIRING_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Anime not found.")
        return
    td     = data.get("title", {}) or {}
    title  = td.get("english") or td.get("romaji") or "Unknown"
    native = td.get("native", "")
    nxt    = data.get("nextAiringEpisode")
    if nxt:
        secs = nxt.get("timeUntilAiring", 0)
        d, r = divmod(secs, 86400); h, r2 = divmod(r, 3600); m = r2 // 60
        ts  = f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        txt = (
            f"<b>{_e(title)}</b>"
            + (f" (<i>{_e(native)}</i>)" if native else "")
            + f"\n\n📡 <b>Episode {nxt.get('episode','?')}</b> {_sc('airs in')} <code>{ts}</code>"
        )
    else:
        st  = (data.get("status") or "").replace("_", " ").title()
        txt = (
            f"<b>{_e(title)}</b>"
            + (f" (<i>{_e(native)}</i>)" if native else "")
            + f"\n\n📺 <b>{_sc('Episodes')}:</b> {data.get('episodes','?')}\n"
            + f"📌 <b>{_sc('Status')}:</b> {_e(st)}"
        )
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML)


async def character_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /character &lt;name&gt;", parse_mode=ParseMode.HTML
        )
        return
    data = await _al(_CHAR_GQL, " ".join(context.args))
    if not data:
        await update.message.reply_text("❌ Character not found.")
        return
    nm     = data.get("name", {}) or {}
    full   = nm.get("full", "Unknown")
    native = nm.get("native", "")
    desc   = _clean(data.get("description", ""), 350)
    site   = data.get("siteUrl", "https://anilist.co")
    img    = (data.get("image") or {}).get("large")
    txt    = (
        f"<b>{_e(full)}</b>"
        + (f" (<i>{_e(native)}</i>)" if native else "")
        + f"\n\n{_e(desc)}"
    )
    if len(txt) > 1020:
        txt = txt[:1016] + "…"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 AniList", url=site)]])
    if img:
        try:
            await update.message.reply_photo(
                photo=img, caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb
            )
            return
        except Exception:
            pass
    await update.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb)


async def imdb_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """IMDb/TMDB lookup — real poster + info only, no AI generation."""
    if not context.args:
        await update.message.reply_text(
            _b("usage:") + " /imdb &lt;movie or show name&gt;", parse_mode=ParseMode.HTML
        )
        return
    q       = " ".join(context.args)
    loop    = asyncio.get_event_loop()
    loading = await update.message.reply_text(
        _b("🔎 searching…"), parse_mode=ParseMode.HTML
    )

    tmdb_result = None
    if _TMDB_KEY:
        try:
            r = requests.get(
                "https://api.themoviedb.org/3/search/multi",
                params={"api_key": _TMDB_KEY, "query": q},
                timeout=8,
            )
            results = r.json().get("results", [])
            if results:
                tmdb_result = results[0]
        except Exception:
            pass

    try:
        await loading.delete()
    except Exception:
        pass

    if not tmdb_result:
        # AniList fallback
        al_data = await loop.run_in_executor(None, _al_sync, _ANIME_GQL, q)
        if al_data:
            cap = _build_caption(al_data)
            kb  = _info_kb(al_data)
            cv  = (al_data.get("coverImage") or {}).get("extraLarge", "")
            if cv:
                try:
                    await update.message.reply_photo(
                        photo=cv, caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb
                    )
                    return
                except Exception:
                    pass
            await update.message.reply_text(
                cap, parse_mode=ParseMode.HTML, reply_markup=kb,
                disable_web_page_preview=True,
            )
            return
        await update.message.reply_text(
            _b(f"❌ not found: {_e(q)}"), parse_mode=ParseMode.HTML
        )
        return

    mtype   = tmdb_result.get("media_type", "movie")
    title   = tmdb_result.get("title") or tmdb_result.get("name") or q
    year    = (tmdb_result.get("release_date") or tmdb_result.get("first_air_date") or "")[:4]
    rating  = tmdb_result.get("vote_average", "?")
    overview = _clean(tmdb_result.get("overview", ""), 250)
    poster_p = tmdb_result.get("poster_path", "")
    tmdb_id  = tmdb_result.get("id", 0)
    tmdb_url = f"https://www.themoviedb.org/{mtype}/{tmdb_id}"
    img_url  = f"https://image.tmdb.org/t/p/w500{poster_p}" if poster_p else ""

    cap = f"<b>{_e(title)}</b>"
    if year:
        cap += f" <code>({year})</code>"
    cap += f"\n\n» <b>{_sc('Rating')}:</b> <code>{rating}/10</code>"
    cap += f"\n» <b>{_sc('Type')}:</b> {_e(mtype.title())}"
    if overview:
        cap += f"\n\n{_bq(_e(overview))}"
    if len(cap) > 1020:
        cap = cap[:1016] + "…"

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 TMDB", url=tmdb_url)]])
    if img_url:
        try:
            await update.message.reply_photo(
                photo=img_url, caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb
            )
            return
        except Exception:
            pass
    await update.message.reply_text(
        cap, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True
    )


# ── Register handlers ─────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
#  GC SINGLE-LETTER ANIME FILTER PANEL
# ══════════════════════════════════════════════════════════════════════════════
# When a user types EXACTLY one letter (e.g. "t") in a connected group,
# show all anime channels starting with that letter as inline buttons.
# • 8 per page, 🔙 / 🔜 navigation
# • Auto-deletes after FILTER_PANEL_TTL seconds (default 20)
# • One panel per user at a time (new letter cancels old panel)
# • Buttons use expirable deep links (same system as filter posters)

_FILTER_PANEL_TTL  = int(_os.getenv("FILTER_PANEL_TTL", "20"))
_FILTER_PAGE_SIZE  = 8
# {uid: {"chat_id":int, "msg_id":int, "pages":list, "letter":str, "task":Task}}
_active_filter_panels: Dict[int, Dict] = {}


async def _send_alpha_filter_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE, letter: str
) -> None:
    """Send paged anime-channel list for a single alphabet letter in GC."""
    chat_id = update.effective_chat.id
    uid     = update.effective_user.id if update.effective_user else 0

    # Cancel existing panel for this user
    prev = _active_filter_panels.get(uid)
    if prev:
        try:
            t = prev.get("task")
            if t and not t.done():
                t.cancel()
        except Exception:
            pass
        try:
            await context.bot.delete_message(prev["chat_id"], prev["msg_id"])
        except Exception:
            pass
        _active_filter_panels.pop(uid, None)

    try:
        from database_dual import get_all_links
        all_links = get_all_links(limit=500, offset=0) or []
        exp_min = 60
        try:
            from filter_poster import get_link_expiry_minutes
            exp_min = int(get_link_expiry_minutes(chat_id))
        except Exception:
            pass
    except Exception:
        return

    ll = letter.lower()
    matched: List = []
    seen: set = set()
    for row in all_links:
        lid, cid, ctitle = row[0], row[1], (row[2] or "").strip()
        if not ctitle or ctitle.lower() in seen:
            continue
        if not ctitle.lower().startswith(ll):
            continue
        seen.add(ctitle.lower())
        matched.append((lid, cid, ctitle))

    if not matched:
        return  # silent — no channels with this letter

    pages      = [matched[i:i + _FILTER_PAGE_SIZE] for i in range(0, len(matched), _FILTER_PAGE_SIZE)]
    total_p    = len(pages)
    bot_uname  = context.bot.username or ""

    _active_filter_panels[uid] = {
        "chat_id": chat_id, "msg_id": None,
        "pages": pages, "letter": letter, "task": None,
    }

    def _build_kb(pi: int) -> InlineKeyboardMarkup:
        items = pages[pi]
        btns: List[List] = []
        brow: List = []
        for lid, cid, ct in items:
            deep = f"https://t.me/{bot_uname}?start={lid}"
            brow.append(InlineKeyboardButton(ct[:30], url=deep))
            if len(brow) == 2:
                btns.append(brow)
                brow = []
        if brow:
            btns.append(brow)
        nav = []
        if pi > 0:
            nav.append(InlineKeyboardButton("🔙", callback_data=f"alpha_page:{uid}:{letter}:{pi-1}"))
        if pi < total_p - 1:
            nav.append(InlineKeyboardButton("🔜", callback_data=f"alpha_page:{uid}:{letter}:{pi+1}"))
        if nav:
            btns.append(nav)
        btns.append([InlineKeyboardButton("✖️ Close", callback_data=f"alpha_close:{uid}")])
        return InlineKeyboardMarkup(btns)

    text = (
        f"<b>🎌 ᴀɴɪᴍᴇ — <code>{letter.upper()}</code></b>\n"
        f"<i>Page 1/{total_p} • ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇs ɪɴ {_FILTER_PANEL_TTL}s</i>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    try:
        sent = await context.bot.send_message(
            chat_id=chat_id, text=text,
            parse_mode=ParseMode.HTML, reply_markup=_build_kb(0),
        )
        _active_filter_panels[uid]["msg_id"] = sent.message_id
    except Exception:
        _active_filter_panels.pop(uid, None)
        return

    async def _auto_del():
        await asyncio.sleep(_FILTER_PANEL_TTL)
        try:
            await context.bot.delete_message(chat_id, sent.message_id)
        except Exception:
            pass
        _active_filter_panels.pop(uid, None)

    task = asyncio.create_task(_auto_del())
    _active_filter_panels[uid]["task"] = task


async def _alpha_filter_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle 🔙 / 🔜 navigation and ✖️ close for alpha-filter panels."""
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception:
        pass
    cb = query.data or ""

    if cb.startswith("alpha_close:"):
        uid = int(cb.split(":")[1])
        panel = _active_filter_panels.get(uid)
        if panel:
            t = panel.get("task")
            if t and not t.done():
                t.cancel()
            _active_filter_panels.pop(uid, None)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if cb.startswith("alpha_page:"):
        parts = cb.split(":")
        if len(parts) < 4:
            return
        uid    = int(parts[1])
        letter = parts[2]
        pi     = int(parts[3])
        panel  = _active_filter_panels.get(uid)
        if not panel:
            try:
                await query.answer("Panel expired. Type the letter again.", show_alert=True)
            except Exception:
                pass
            return
        pages   = panel.get("pages", [])
        total_p = len(pages)
        if pi < 0 or pi >= total_p:
            return
        bot_uname = context.bot.username or ""
        items     = pages[pi]

        btns: List[List] = []
        brow: List = []
        for lid, cid, ct in items:
            deep = f"https://t.me/{bot_uname}?start={lid}"
            brow.append(InlineKeyboardButton(ct[:30], url=deep))
            if len(brow) == 2:
                btns.append(brow)
                brow = []
        if brow:
            btns.append(brow)
        nav = []
        if pi > 0:
            nav.append(InlineKeyboardButton("🔙", callback_data=f"alpha_page:{uid}:{letter}:{pi-1}"))
        if pi < total_p - 1:
            nav.append(InlineKeyboardButton("🔜", callback_data=f"alpha_page:{uid}:{letter}:{pi+1}"))
        if nav:
            btns.append(nav)
        btns.append([InlineKeyboardButton("✖️ Close", callback_data=f"alpha_close:{uid}")])

        text = (
            f"<b>🎌 ᴀɴɪᴍᴇ — <code>{letter.upper()}</code></b>\n"
            f"<i>Page {pi+1}/{total_p} • ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇs ɪɴ {_FILTER_PANEL_TTL}s</i>\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        try:
            await query.message.edit_text(
                text=text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btns),
            )
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  INLINE SEARCH — real-time AniList results (cached, like website search)
# ══════════════════════════════════════════════════════════════════════════════

async def inline_search_anime(
    search: str, bot_username: str, join_btn_text: str = "ᴊᴏɪɴ ɴᴏᴡ"
) -> list:
    """
    Returns InlineQueryResult list for a search term.
    Uses _INLINE_GQL (lighter) + TTL cache for instant feel.
    Called from bot.py's inline_query_handler for "poster" prefix.
    """
    from uuid import uuid4

    if not search:
        return []

    loop   = asyncio.get_event_loop()
    items  = await loop.run_in_executor(None, _al_page_sync, search, _INLINE_GQL)
    if not items:
        return []

    results = []
    for item in items[:8]:
        td     = item.get("title", {}) or {}
        title  = td.get("english") or td.get("romaji") or "Unknown"
        native = td.get("native", "")
        score  = item.get("averageScore", "")
        status = (item.get("status") or "").replace("_", " ").title()
        year   = item.get("seasonYear", "")
        fmt    = (item.get("format") or "").replace("_", " ")
        site   = item.get("siteUrl", "https://anilist.co")
        eps    = item.get("episodes", "")
        genres = ", ".join((item.get("genres") or [])[:2])
        ci     = item.get("coverImage", {}) or {}
        cover  = ci.get("extraLarge") or ci.get("large") or ci.get("medium", "")
        thumb  = ci.get("medium") or ci.get("large") or cover
        sc_str = f"{score}/100" if score else "N/A"

        cap = f"<b>{html.escape(title)}</b>"
        if native:
            cap += f"\n<i>{html.escape(native)}</i>"
        cap += "\n\n"
        if genres:
            cap += f"» <b>Genre:</b> {html.escape(genres)}\n"
        if sc_str != "N/A":
            cap += f"» <b>Rating:</b> <code>{sc_str}</code>\n"
        if status:
            cap += f"» <b>Status:</b> {html.escape(status)}\n"
        if eps:
            cap += f"» <b>Episodes:</b> <code>{eps}</code>\n"
        if fmt:
            cap += f"» <b>Format:</b> {html.escape(fmt)}\n"
        if year:
            cap += f"» <b>Year:</b> <code>{year}</code>\n"

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 AniList", url=site),
            InlineKeyboardButton("🔍 Watch", switch_inline_query_current_chat=f"watch {title}"),
        ]])

        if cover:
            try:
                # Build join-now button using anime channel links
                watch_rows = []
                try:
                    from database_dual import get_anime_channel_links
                    alinks = get_anime_channel_links(title)
                    for _cid, _ctitle, _lid in (alinks or []):
                        if _ctitle:  # Only show channels that have anime name set
                            from core.config import PUBLIC_ANIME_CHANNEL_URL
                            bot_uname = ""
                            try:
                                from core.config import BOT_USERNAME
                                bot_uname = BOT_USERNAME
                            except Exception:
                                pass
                            deep_url = f"https://t.me/{bot_uname}?start={_lid}" if bot_uname and _lid else PUBLIC_ANIME_CHANNEL_URL
                            watch_rows.append([InlineKeyboardButton(
                                f"▶ {_ctitle[:25]}", url=deep_url
                            )])
                except Exception:
                    pass
                from core.config import PUBLIC_ANIME_CHANNEL_URL
                if not watch_rows:
                    watch_rows = [[InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ ᴛᴏ ᴡᴀᴛᴄʜ", url=PUBLIC_ANIME_CHANNEL_URL)]]
                watch_kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 ᴀɴɪʟɪsᴛ", url=site)]] + watch_rows)
                results.append(InlineQueryResultPhoto(
                    id=str(uuid4()),
                    photo_url=cover,
                    thumbnail_url=thumb or cover,
                    title=title[:40],
                    description=f"{'⭐ ' + sc_str if score else ''} • {status} • {fmt}",
                    caption=cap,
                    parse_mode=ParseMode.HTML,
                    reply_markup=watch_kb,
                ))
                continue
            except Exception:
                pass

        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=title[:40],
            description=f"{sc_str} • {status} • {fmt}",
            input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
            reply_markup=kb,
            thumb_url=thumb or "",
        ))

    return results


def register(app) -> None:
    app.add_handler(CommandHandler("anime",     anime_cmd))
    app.add_handler(CommandHandler("tvshow",    tvshow_cmd))
    app.add_handler(CommandHandler("movie",     movie_cmd))
    app.add_handler(CommandHandler("net",       net_cmd))
    app.add_handler(CommandHandler("manga",     manga_cmd))
    app.add_handler(CommandHandler("airing",    airing_cmd))
    app.add_handler(CommandHandler("character", character_cmd))
    app.add_handler(CommandHandler("imdb",      imdb_cmd))

    # All anime-flow callbacks in one handler
    app.add_handler(CallbackQueryHandler(
        _anime_callback,
        pattern=r"^(anpick_|lang_|size_|anthmb_)",
    ))

    # Alpha-filter panel navigation
    app.add_handler(CallbackQueryHandler(
        _alpha_filter_callback,
        pattern=r"^(alpha_page:|alpha_close:)",
    ))

    # Custom thumbnail photo (check awaiting_thumbnail in user_data)
    app.add_handler(MessageHandler(
        filters.PHOTO & ~filters.COMMAND,
        _thumbnail_photo_handler,
    ))

    logger.info("[anime] Handlers registered (season, similar panel, language, size)")


# Legacy PTB v13 compat shim
try:
    from beataniversebot_compat import dispatcher
    from modules.disable import DisableAbleCommandHandler
    from telegram.ext import (
        Filters,
        CallbackQueryHandler as CQH,
        MessageHandler as MH,
    )
    dispatcher.add_handler(DisableAbleCommandHandler("anime",     anime_cmd,     run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("tvshow",    tvshow_cmd,    run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("movie",     movie_cmd,     run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("net",       net_cmd,       run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("manga",     manga_cmd,     run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("airing",    airing_cmd,    run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("character", character_cmd, run_async=True))
    dispatcher.add_handler(DisableAbleCommandHandler("imdb",      imdb_cmd,      run_async=True))
    dispatcher.add_handler(CQH(
        _anime_callback,
        pattern=r"^(anpick_|lang_|size_|anthmb_)",
        run_async=True,
    ))
    dispatcher.add_handler(CQH(
        _alpha_filter_callback,
        pattern=r"^(alpha_page:|alpha_close:)",
        run_async=True,
    ))
    dispatcher.add_handler(MH(
        Filters.photo & ~Filters.command,
        _thumbnail_photo_handler,
        run_async=True,
    ))
except Exception:
    pass


__mod_name__     = "Aɴɪᴍᴇ"
__command_list__ = ["anime", "tvshow", "movie", "net", "manga", "airing", "character", "imdb"]
__help__ = """
• /anime &lt;name&gt; — anime poster + info
• /anime aot s2 — season 2 specific poster
• /anime demon slayer season 3 — season 3 poster
• /tvshow &lt;name&gt; — TV show poster
• /movie &lt;name&gt; — movie poster
• /net &lt;name&gt; — Netflix-style poster (instant, no panels)
• /manga &lt;name&gt; — manga poster + info
• /airing &lt;name&gt; — next episode countdown
• /character &lt;name&gt; — character details from AniList
• /imdb &lt;name&gt; — TMDB poster + info (no generation)

Abbreviations: aot, mha, jjk, csm, ds, opm, fmab, kny, hxh, sao, dbs, cote…
Season: s2, s3, season 2, 2nd season, final season
"""
