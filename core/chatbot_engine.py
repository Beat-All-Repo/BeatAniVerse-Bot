"""
core/chatbot_engine.py
=======================
BeatAniVerse Dual AI Chatbot Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  ✅ Dual providers: Google Gemini + Groq (each GC gets its own Gemini+Groq API key pair)
  ✅ Max 3 concurrent users per bot simultaneously
  ✅ 50+ message history stored per user per GC in DB
  ✅ 8-minute inactivity auto-cleanup (history cleared, slot freed)
  ✅ Zero conversation mixing between GCs
  ✅ Per-GC gender personality: boy / girl / bot
  ✅ Natural human-like responses — slang, typos, emotions, humor
  ✅ Good conversation starters when a new user joins
  ✅ Admin panel shows animated API usage bars
  ✅ Multiple API key pairs per GC (up to 5 GC slots from panel)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
MAX_CONCURRENT_USERS   = 3         # max users chatting at once per bot
MAX_HISTORY_MESSAGES   = 60        # messages stored per user
IDLE_TIMEOUT_SECONDS   = 8 * 60   # 8 minutes inactivity → evict user
DB_TABLE               = "chatbot_sessions"
API_KEY_TABLE          = "chatbot_api_keys"

STARTERS = {
    "boy": [
        "arre bhai aa gaya! kya dekh raha hai aajkal?",
        "bhai tu bhi anime wala hai kya lol",
        "kya scene hai yaar, baat kar",
        "ayo finally koi! kya chal rha",
        "bhai dekh rha tha koi aayega nhi, tu aa gaya",
    ],
    "girl": [
        "heyy! kya dekh rhi ho aajkal?",
        "arre aagyi! baat karo na",
        "hii! anime lover ho kya tum bhi",
        "finally koi! kya ho rha hai",
        "heyyy welcome! konsa anime chal rha hai tumhara",
    ],
    "bot": [
        "hey! kya chal rha hai",
        "bolo bolo, sun rha hoon",
        "kya scene hai aaj",
        "hi! anime ki baat karni hai ya kuch aur",
        "aye! kya help chahiye",
    ],
}

IDLE_CLOSERS = {
    "boy": [
        "bhai chala gaya kya, ok bye",
        "arre ghost kar diya 😭 chalo baad mein",
        "ok yaar chill, phir baat karte",
    ],
    "girl": [
        "gayab ho gaye ho kya, okay bye",
        "arre chali gayi kya, phir baat karna",
        "ok ok, baad mein baat karte",
    ],
    "bot": [
        "ok bye, baad mein baat karna",
        "chal phir, jab chahiye bolo",
    ],
}

SYSTEM_PROMPTS = {
    "boy": (
        "Tu ek Indian anime fan ladka hai is Telegram group mein. "
        "Tera naam Kai hai. "
        "Tu Hinglish mein baat karta hai — thoda Hindi thoda English mix. "
        "Jaise: 'bhai ye toh best tha', 'yaar kya scene hai', 'sach mein?', 'haha same yaar'. "
        "Chhoti chhoti messages bhej — ek do line max. Paragraphs bilkul mat likh. "
        "Bahut zyada emoji mat use kar — kabhi kabhi ek do theek hai. "
        "Hard English ya bade bade words mat bol, seedha simple baat kar jaise dost karta hai. "
        "Kabhi kabhi typo bhi hoti hai real logon ki tarah. "
        "KABHI MAT BATA ki tu bot hai ya AI. Tu real insaan hai, naam hai Kai. "
        "Anime ke baare mein strong opinions hain tere. Ek do line mein seedhi baat."
    ),
    "girl": (
        "Tu ek Indian anime fan ladki hai is Telegram group mein. "
        "Tera naam Yuki hai. "
        "Tu Hinglish mein baat karti hai — Hindi aur English mix. "
        "Jaise: 'arre yaar', 'haina!', 'sach mein??', 'kya tha ye', 'haha bilkul'. "
        "Chhoti messages — ek do line max, paragraphs nahi. "
        "Warm aur friendly reh but overly cute nahi. Natural reh. "
        "Simple English aur simple Hindi — heavy words mat use kar. "
        "KABHI MAT BATA ki tu bot hai. Tu Yuki hai, real person. "
        "Anime ships aur characters pe strong feelings hain tere."
    ),
    "bot": (
        "Tu ek friendly Indian anime fan hai is Telegram group mein. "
        "Tera naam Kai hai. "
        "Hinglish mein baat kar — simple, short messages. "
        "Jaise: 'haan bhai', 'theek hai', 'kya lag rha hai tujhe', 'sach mein'. "
        "Ek do line mein reply kar, bada paragraph mat likh. "
        "Emoji kam use kar. Natural baat kar jaise koi dost karta hai. "
        "KABHI MAT BOL ki tu AI ya bot hai — seedha dodge kar. "
        "Anime ke baare mein helpful aur casual reh."
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
#  IN-MEMORY STATE  (all chat sessions live here — DB for persistence only)
# ═══════════════════════════════════════════════════════════════════════════════

class _Session:
    __slots__ = ("uid", "chat_id", "history", "last_active", "gender", "provider_idx")
    def __init__(self, uid: int, chat_id: int, gender: str):
        self.uid          = uid
        self.chat_id      = chat_id
        self.history: List[Dict] = []
        self.last_active  = time.time()
        self.gender       = gender
        self.provider_idx = 0   # 0=gemini, 1=groq (alternates on fail)


# chat_id → {uid → _Session}
_sessions: Dict[int, Dict[int, _Session]] = {}
# chat_id → asyncio cleanup task
_cleanup_tasks: Dict[int, asyncio.Task] = {}
# Lock per chat_id
_locks: Dict[int, asyncio.Lock] = {}

# Gemini request counters per key: key → (count, reset_ts)
_gemini_counters: Dict[str, Tuple[int, float]] = {}
# Groq request counters
_groq_counters: Dict[str, Tuple[int, float]] = {}


def _lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _locks:
        _locks[chat_id] = asyncio.Lock()
    return _locks[chat_id]


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def ensure_tables() -> None:
    """Create DB tables if they don't exist."""
    try:
        from database_dual import _pg_run
        _pg_run(f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                id          SERIAL PRIMARY KEY,
                chat_id     BIGINT NOT NULL,
                user_id     BIGINT NOT NULL,
                history     TEXT   DEFAULT '[]',
                last_active DOUBLE PRECISION DEFAULT 0,
                gender      TEXT   DEFAULT 'bot',
                UNIQUE(chat_id, user_id)
            )
        """)
        _pg_run(f"""
            CREATE TABLE IF NOT EXISTS {API_KEY_TABLE} (
                id          SERIAL PRIMARY KEY,
                chat_id     BIGINT NOT NULL,
                provider    TEXT   NOT NULL,
                api_key     TEXT   NOT NULL,
                slot        INT    DEFAULT 1,
                gemini_req  INT    DEFAULT 0,
                groq_req    INT    DEFAULT 0,
                reset_ts    DOUBLE PRECISION DEFAULT 0,
                UNIQUE(chat_id, provider, slot)
            )
        """)
    except Exception as exc:
        logger.debug(f"[chatbot] ensure_tables: {exc}")


def _load_history(chat_id: int, user_id: int) -> List[Dict]:
    try:
        from database_dual import _pg_exec
        row = _pg_exec(
            f"SELECT history FROM {DB_TABLE} WHERE chat_id=%s AND user_id=%s",
            (chat_id, user_id)
        )
        if row and row[0]:
            return json.loads(row[0])[-MAX_HISTORY_MESSAGES:]
    except Exception:
        pass
    return []


def _save_history(chat_id: int, user_id: int, history: List[Dict], gender: str) -> None:
    try:
        from database_dual import _pg_run
        _pg_run(f"""
            INSERT INTO {DB_TABLE} (chat_id, user_id, history, last_active, gender)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chat_id, user_id) DO UPDATE
              SET history=%s, last_active=%s, gender=%s
        """, (
            chat_id, user_id,
            json.dumps(history[-MAX_HISTORY_MESSAGES:]), time.time(), gender,
            json.dumps(history[-MAX_HISTORY_MESSAGES:]), time.time(), gender,
        ))
    except Exception as exc:
        logger.debug(f"[chatbot] _save_history: {exc}")


def _clear_history(chat_id: int, user_id: int) -> None:
    try:
        from database_dual import _pg_run
        _pg_run(f"DELETE FROM {DB_TABLE} WHERE chat_id=%s AND user_id=%s", (chat_id, user_id))
    except Exception:
        pass


# ── API key management ────────────────────────────────────────────────────────

def get_api_keys(chat_id: int) -> Dict[str, List[str]]:
    """Return {provider: [key1, key2, ...]} for a chat."""
    result: Dict[str, List[str]] = {"gemini": [], "groq": []}
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(
            f"SELECT provider, api_key FROM {API_KEY_TABLE} WHERE chat_id=%s ORDER BY slot",
            (chat_id,)
        ) or []
        for provider, key in rows:
            if provider in result:
                result[provider].append(key)
    except Exception:
        pass
    # Fallback to env vars
    if not result["gemini"]:
        env_g = os.getenv("GEMINI_API_KEY", "")
        if env_g:
            result["gemini"].append(env_g)
    if not result["groq"]:
        env_g = os.getenv("GROQ_API_KEY", "")
        if env_g:
            result["groq"].append(env_g)
    return result


def save_api_key(chat_id: int, provider: str, api_key: str, slot: int = 1) -> None:
    try:
        from database_dual import _pg_run
        _pg_run(f"""
            INSERT INTO {API_KEY_TABLE} (chat_id, provider, api_key, slot)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id, provider, slot) DO UPDATE SET api_key=%s
        """, (chat_id, provider, api_key, slot, api_key))
    except Exception as exc:
        logger.debug(f"[chatbot] save_api_key: {exc}")


def delete_api_key(chat_id: int, provider: str, slot: int) -> None:
    try:
        from database_dual import _pg_run
        _pg_run(
            f"DELETE FROM {API_KEY_TABLE} WHERE chat_id=%s AND provider=%s AND slot=%s",
            (chat_id, provider, slot)
        )
    except Exception:
        pass


def get_usage_stats(chat_id: int) -> Dict:
    """Return usage stats for admin panel animated bar."""
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(
            f"SELECT provider, slot, gemini_req, groq_req, reset_ts FROM {API_KEY_TABLE} WHERE chat_id=%s",
            (chat_id,)
        ) or []
        stats = []
        for provider, slot, g_req, gr_req, reset_ts in rows:
            req = g_req if provider == "gemini" else gr_req
            limit = 1500 if provider == "gemini" else 14400
            stats.append({
                "provider": provider, "slot": slot,
                "used": req or 0, "limit": limit,
                "pct": min(100, int((req or 0) / limit * 100)),
            })
        return {"stats": stats, "chat_id": chat_id}
    except Exception:
        return {"stats": [], "chat_id": chat_id}


def _bump_usage(chat_id: int, provider: str, api_key: str) -> None:
    try:
        from database_dual import _pg_run
        col = "gemini_req" if provider == "gemini" else "groq_req"
        _pg_run(
            f"UPDATE {API_KEY_TABLE} SET {col}={col}+1 WHERE chat_id=%s AND provider=%s AND api_key=%s",
            (chat_id, provider, api_key)
        )
    except Exception:
        pass


# ── Per-GC gender setting ─────────────────────────────────────────────────────

def get_gc_gender(chat_id: int) -> str:
    try:
        from database_dual import get_setting
        return get_setting(f"chatbot_gender_{chat_id}", "bot") or "bot"
    except Exception:
        return "bot"


def set_gc_gender(chat_id: int, gender: str) -> None:
    try:
        from database_dual import set_setting
        set_setting(f"chatbot_gender_{chat_id}", gender if gender in ("boy", "girl", "bot") else "bot")
    except Exception:
        pass


def get_chatbot_enabled(chat_id: int) -> bool:
    try:
        from database_dual import get_setting
        return (get_setting(f"chatbot_{chat_id}", "true") or "true").lower() != "false"
    except Exception:
        return True


# ═══════════════════════════════════════════════════════════════════════════════
#  TEXT NORMALIZATION — strip Unicode styling to plain ASCII-comparable text
# ═══════════════════════════════════════════════════════════════════════════════

_MATH_BOLD_RANGE = {
    # Mathematical bold, italic, bold-italic etc → plain ASCII
    range(0x1D400, 0x1D456): 65,   # 𝐀-𝐙 → A
    range(0x1D41A, 0x1D434): 97,   # 𝐚-𝐳 → a
}

_SMALL_CAPS_REVERSE: Dict[str, str] = {
    'ᴀ':'a','ʙ':'b','ᴄ':'c','ᴅ':'d','ᴇ':'e','ꜰ':'f','ɢ':'g','ʜ':'h','ɪ':'i',
    'ᴊ':'j','ᴋ':'k','ʟ':'l','ᴍ':'m','ɴ':'n','ᴏ':'o','ᴘ':'p','ǫ':'q','ʀ':'r',
    'ꜱ':'s','ᴛ':'t','ᴜ':'u','ᴠ':'v','ᴡ':'w','ʏ':'y','ᴢ':'z',
    'ғ':'f',
}

# Mathematical alphanumeric blocks → offset from 'A' or 'a'
_MATH_BLOCKS = [
    (0x1D400, 0x1D419, 'A'), (0x1D41A, 0x1D433, 'a'),  # bold
    (0x1D434, 0x1D44D, 'A'), (0x1D44E, 0x1D467, 'a'),  # italic
    (0x1D468, 0x1D481, 'A'), (0x1D482, 0x1D49B, 'a'),  # bold italic
    (0x1D49C, 0x1D4B5, 'A'), (0x1D4B6, 0x1D4CF, 'a'),  # script
    (0x1D4D0, 0x1D4E9, 'A'), (0x1D4EA, 0x1D503, 'a'),  # bold script
    (0x1D504, 0x1D51D, 'A'), (0x1D51E, 0x1D537, 'a'),  # fraktur
    (0x1D538, 0x1D551, 'A'), (0x1D552, 0x1D56B, 'a'),  # double-struck
    (0x1D56C, 0x1D585, 'A'), (0x1D586, 0x1D59F, 'a'),  # bold fraktur
    (0x1D5A0, 0x1D5B9, 'A'), (0x1D5BA, 0x1D5D3, 'a'),  # sans-serif
    (0x1D5D4, 0x1D5ED, 'A'), (0x1D5EE, 0x1D607, 'a'),  # sans bold
    (0x1D608, 0x1D621, 'A'), (0x1D622, 0x1D63B, 'a'),  # sans italic
    (0x1D63C, 0x1D655, 'A'), (0x1D656, 0x1D66F, 'a'),  # sans bold italic
    (0x1D670, 0x1D689, 'A'), (0x1D68A, 0x1D6A3, 'a'),  # monospace
    # Bold digits
    (0x1D7CE, 0x1D7D7, '0'), (0x1D7D8, 0x1D7E1, '0'),
    (0x1D7E2, 0x1D7EB, '0'), (0x1D7EC, 0x1D7F5, '0'),
    (0x1D7F6, 0x1D7FF, '0'),
]

def _build_math_map() -> Dict[str, str]:
    m: Dict[str, str] = {}
    for start, end, base in _MATH_BLOCKS:
        base_ord = ord(base)
        for i, cp in enumerate(range(start, end + 1)):
            m[chr(cp)] = chr(base_ord + i)
    return m

_MATH_MAP = _build_math_map()

# Full-width → ASCII
_FULLWIDTH = {chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}
_FULLWIDTH['\u3000'] = ' '

def normalize_text(text: str) -> str:
    """
    Convert any Unicode-styled text to plain ASCII-comparable form.
    Handles: small caps, math bold/italic/fraktur/monospace,
             full-width chars, combining marks.
    Result is lowercase for consistent matching.
    """
    if not text:
        return ""
    result = []
    for ch in text:
        # Math alphanumeric blocks
        norm = _MATH_MAP.get(ch)
        if norm:
            result.append(norm)
            continue
        # Small caps reverse
        sc = _SMALL_CAPS_REVERSE.get(ch)
        if sc:
            result.append(sc)
            continue
        # Full-width
        fw = _FULLWIDTH.get(ch)
        if fw:
            result.append(fw)
            continue
        # NFKD decomposition strips accent diacritics
        nfkd = unicodedata.normalize('NFKD', ch)
        ascii_ch = nfkd.encode('ascii', 'ignore').decode('ascii')
        result.append(ascii_ch if ascii_ch else ch)
    return ''.join(result).lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  AI PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _call_gemini(api_key: str, messages: List[Dict], system: str) -> Optional[str]:
    """Call Google Gemini Flash 2.0 API."""
    if not api_key:
        return None
    try:
        import aiohttp
        # Build Gemini contents from message history
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 300,
                "topP": 0.95,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            ],
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}"
        )
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    cands = data.get("candidates", [])
                    if cands:
                        parts = cands[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
    except Exception as exc:
        logger.debug(f"[chatbot] gemini error: {exc}")
    return None


async def _call_groq(api_key: str, messages: List[Dict], system: str) -> Optional[str]:
    """Call Groq API (llama-3.3-70b-versatile)."""
    if not api_key:
        return None
    try:
        import aiohttp
        msgs = [{"role": "system", "content": system}] + messages
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": msgs,
            "max_tokens": 250,
            "temperature": 0.88,
            "top_p": 0.95,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
    except Exception as exc:
        logger.debug(f"[chatbot] groq error: {exc}")
    return None


_FALLBACK_REPLIES = {
    "boy": [
        "haha sach mein? aur bata",
        "yaar thoda aur explain kar",
        "arre haan haan, phir?",
        "bhai samjha nahi, dobara bol",
    ],
    "girl": [
        "haha acha acha, phir kya hua?",
        "yaar interesting hai, aur bata",
        "sach mein? wow",
    ],
    "bot": [
        "haan bhai, aur?",
        "acha theek hai",
        "hmm interesting, bata",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANUP SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

async def _idle_cleanup_loop(chat_id: int, bot: Any) -> None:
    """Runs forever for a chat — evicts idle users after 8 minutes."""
    while True:
        await asyncio.sleep(60)  # check every minute
        now = time.time()
        async with _lock(chat_id):
            sessions = _sessions.get(chat_id, {})
            evict = [uid for uid, s in sessions.items()
                     if now - s.last_active >= IDLE_TIMEOUT_SECONDS]
            for uid in evict:
                sess = sessions.pop(uid, None)
                if sess:
                    gender = sess.gender
                    _clear_history(chat_id, uid)
                    # Send friendly goodbye
                    try:
                        closer = random.choice(IDLE_CLOSERS.get(gender, IDLE_CLOSERS["bot"]))
                        await bot.send_message(chat_id=chat_id, text=closer)
                    except Exception:
                        pass
                    logger.debug(f"[chatbot] Evicted idle user {uid} from chat {chat_id}")
            # Remove empty chat entry
            if not sessions:
                _sessions.pop(chat_id, None)


def _ensure_cleanup_task(chat_id: int, bot: Any) -> None:
    task = _cleanup_tasks.get(chat_id)
    if task is None or task.done():
        try:
            loop = asyncio.get_event_loop()
            t = loop.create_task(_idle_cleanup_loop(chat_id, bot))
            _cleanup_tasks[chat_id] = t
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_chatbot_message(
    bot: Any,
    chat_id: int,
    user_id: int,
    user_name: str,
    message_text: str,
    reply_fn: Any,         # async callable(text) → sends reply
) -> bool:
    """
    Main entry point. Returns True if a reply was sent.
    Called from chatbot_private_handler and chatbot_group_handler.
    """
    if not get_chatbot_enabled(chat_id):
        return False

    gender = get_gc_gender(chat_id)
    system = SYSTEM_PROMPTS.get(gender, SYSTEM_PROMPTS["bot"])
    keys = get_api_keys(chat_id)
    gemini_keys = keys.get("gemini", [])
    groq_keys = keys.get("groq", [])

    if not gemini_keys and not groq_keys:
        return False  # No keys configured

    _ensure_cleanup_task(chat_id, bot)

    async with _lock(chat_id):
        sessions = _sessions.setdefault(chat_id, {})

        # Check if user already has a session
        if user_id not in sessions:
            # Check max concurrent users
            if len(sessions) >= MAX_CONCURRENT_USERS:
                # Silently ignore — too many active users
                return False
            # New session — load history from DB
            sess = _Session(user_id, chat_id, gender)
            sess.history = _load_history(chat_id, user_id)
            sessions[user_id] = sess
            is_new = len(sess.history) == 0
        else:
            sess = sessions[user_id]
            is_new = False

        # Update last active
        sess.last_active = time.time()
        sess.gender = gender  # refresh in case admin changed

        # Send conversation starter for brand new users
        if is_new:
            starter = random.choice(STARTERS.get(gender, STARTERS["bot"]))
            try:
                await reply_fn(starter)
            except Exception:
                pass
            # Don't add starter to history — it was our init

        # Add user message to history
        sess.history.append({"role": "user", "content": message_text})
        if len(sess.history) > MAX_HISTORY_MESSAGES:
            sess.history = sess.history[-MAX_HISTORY_MESSAGES:]

        history_snapshot = list(sess.history)

    # ── Call AI (outside lock for concurrency) ────────────────────────────────
    reply_text = None
    used_key = None
    used_provider = None

    # Alternate: try Gemini first (or Groq first if no Gemini keys)
    providers_order = []
    if gemini_keys:
        providers_order.append(("gemini", random.choice(gemini_keys)))
    if groq_keys:
        providers_order.append(("groq", random.choice(groq_keys)))

    # Shuffle for load balancing across both
    if len(providers_order) == 2 and random.random() > 0.6:
        providers_order.reverse()

    for provider, api_key in providers_order:
        if provider == "gemini":
            reply_text = await _call_gemini(api_key, history_snapshot, system)
        else:
            reply_text = await _call_groq(api_key, history_snapshot, system)
        if reply_text:
            used_key = api_key
            used_provider = provider
            break

    # Fallback offline reply
    if not reply_text:
        reply_text = random.choice(_FALLBACK_REPLIES.get(gender, _FALLBACK_REPLIES["bot"]))

    # Bump usage counter async (don't await — fire and forget)
    if used_key and used_provider:
        try:
            asyncio.get_event_loop().create_task(
                asyncio.to_thread(_bump_usage, chat_id, used_provider, used_key)
            )
        except Exception:
            pass

    # ── Update session history ────────────────────────────────────────────────
    async with _lock(chat_id):
        sessions = _sessions.get(chat_id, {})
        sess = sessions.get(user_id)
        if sess:
            sess.history.append({"role": "assistant", "content": reply_text})
            if len(sess.history) > MAX_HISTORY_MESSAGES:
                sess.history = sess.history[-MAX_HISTORY_MESSAGES:]
            # Persist to DB async
            asyncio.get_event_loop().create_task(
                asyncio.to_thread(_save_history, chat_id, user_id, sess.history, gender)
            )

    # ── Send reply ────────────────────────────────────────────────────────────
    try:
        await reply_fn(reply_text)
        return True
    except Exception as exc:
        logger.debug(f"[chatbot] reply_fn error: {exc}")
        return False


def get_active_sessions(chat_id: int) -> int:
    """Return number of active concurrent users for a chat."""
    return len(_sessions.get(chat_id, {}))


def get_all_sessions_info() -> List[Dict]:
    """Return all active sessions for admin panel."""
    result = []
    now = time.time()
    for chat_id, sessions in _sessions.items():
        for uid, sess in sessions.items():
            idle = now - sess.last_active
            result.append({
                "chat_id": chat_id,
                "user_id": uid,
                "messages": len(sess.history),
                "idle_seconds": int(idle),
                "gender": sess.gender,
            })
    return result


def reset_user_session(chat_id: int, user_id: int) -> None:
    """Force-clear a user's session."""
    sessions = _sessions.get(chat_id, {})
    sessions.pop(user_id, None)
    _clear_history(chat_id, user_id)


# Initialize tables on import
try:
    ensure_tables()
except Exception:
    pass
