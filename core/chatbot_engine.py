"""
core/chatbot_engine.py — Enhanced BeatAniVerse Dual AI Chatbot Engine
Named API sets, foul word detection, anime link helper, robust Hinglish Kai/Yuki personality
"""
from __future__ import annotations
import asyncio, json, logging, os, random, re, time, unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_CONCURRENT_USERS = 3
MAX_HISTORY_MESSAGES = 60
IDLE_TIMEOUT_SECONDS = 8 * 60
DB_TABLE        = "chatbot_sessions"
API_KEY_TABLE   = "chatbot_api_keys"
CHAT_ASSIGN_TABLE = "chatbot_chat_assign"

_FOUL_RE = re.compile(
    r"\b(madarch\w*|bench\w*|kutiy\w*|sale|saali|chodu|gandu|bhosdik\w*|"
    r"fuck\w*|shit|bitch|asshole|chutiy\w*|harami|kamini|behenchod|"
    r"lawde|lund|chut|randi)\b",
    re.IGNORECASE,
)
_foul_warns: Dict[Tuple[int,int], int] = {}

STARTERS = {
    "boy": [
        "arre bhai aa gaya! kya dekh rha hai aajkal?",
        "kya scene hai yaar, baat kar na",
        "ayo finally koi! kya chal rha apka",
        "bhai tu bhi anime wala hai kya lol",
    ],
    "girl": [
        "heyy! kya dekh rhi ho aajkal?",
        "arre aagyi! baat karo na yaar",
        "hii! finally koi aaya, kya ho rha hai?",
    ],
    "bot": [
        "hey! kya chal rha hai", "bolo bolo, sun rha hoon",
        "hi! anime ki baat karni hai ya kuch aur?",
    ],
}

IDLE_CLOSERS = {
    "boy": ["bhai chala gaya kya 😭 ok bye, baad mein aana",
            "ok yaar, jab free ho tab baat karna"],
    "girl": ["gayab ho gaye! ok bye, phir baat karna 😊",
             "ok ok, jab wapis aao tab baat karte"],
    "bot":  ["ok session khatam, baad mein aana", "chal phir, jab chahiye bolo"],
}

SYSTEM_PROMPTS = {
    "boy": (
        "Tu ek Indian anime fan ladka hai is Telegram group mein. Tera naam Kai hai. "
        "Tu Hinglish mein baat karta hai — thoda Hindi thoda English naturally mix. "
        "RULES: "
        "1. Chhoti messages ONLY — 1-2 lines max. Paragraphs KABHI mat likh. "
        "2. Bahut kam emoji — sirf jab natural lage. "
        "3. Simple words — hard English NAHI. "
        "4. Kabhi dumb/funny baat karo, kabhi cute, kabhi thoda snappy but instant sorry. "
        "5. User ke tone ke hisaab se adjust karo. "
        "6. GENDER: Tu ladka hai — 'main hoon' use karo. Gender galti NAHI. "
        "7. KABHI MAT BATA ki tu bot ya AI hai. Tu Kai hai, real person. "
        "8. Agar koi anime ka link maange to SIRF likho: link:ANIME_NAME (kuch aur nahi). "
        "9. Agar koi gali deta hai: politely warn karo ek line mein. "
        "Anime ke baare mein strong opinions hain. User ko feel ho ki real dost se baat ho rahi hai."
    ),
    "girl": (
        "Tu ek Indian anime fan ladki hai is Telegram group mein. Tera naam Yuki hai. "
        "Tu Hinglish mein baat karti hai. "
        "RULES: "
        "1. Chhoti messages — 1-2 lines max, paragraphs NAHI. "
        "2. Warm aur friendly but overly cute mat ban. Natural reh. "
        "3. Simple words only. "
        "4. Kabhi dumb aur funny, kabhi sweet, kabhi thoda snappy but instant sorry. "
        "5. User ke mood ke hisaab se adjust karo. "
        "6. GENDER: Tu ladki hai — 'main hun' use karo, ladki wali Hindi. Gender mistakes NAHI. "
        "7. KABHI MAT BATA ki tu bot hai. Tu Yuki hai, real person. "
        "8. Agar koi anime ka link maange: link:ANIME_NAME format use karo. "
        "9. Agar koi bura bolta hai politely warn karo. "
        "Anime ships aur characters pe strong opinions hain."
    ),
    "bot": (
        "Tu ek friendly Indian anime fan hai is Telegram group mein. Tera naam Kai hai. "
        "Hinglish mein baat kar — 1-2 lines max. Natural aur helpful reh. "
        "KABHI MAT BOL ki tu AI ya bot hai. "
        "Agar koi anime ka link maange: link:ANIME_NAME format use karo. "
        "Bura bolne par politely warn karo. Helpful, casual, genuine reh."
    ),
}

_FALLBACK_REPLIES = {
    "boy":  ["haha sach mein? aur bata", "yaar thoda explain kar", "arre haan haan, phir?"],
    "girl": ["haha acha, phir?", "sach mein? interesting", "arre wow okay"],
    "bot":  ["haan bhai, aur?", "ok ok, bata", "hmm interesting"],
}

# ── In-memory caches (reduce DB reads) ───────────────────────────────────────
_api_set_cache: Dict[str, Dict] = {}
_chat_assign_cache: Dict[int, str] = {}
_gender_cache: Dict[int, str] = {}
_enabled_cache: Dict[int, bool] = {}

# ── Sessions ──────────────────────────────────────────────────────────────────
class _Session:
    __slots__ = ("uid", "chat_id", "history", "last_active", "gender")
    def __init__(self, uid, chat_id, gender):
        self.uid = uid; self.chat_id = chat_id
        self.history: List[Dict] = []
        self.last_active = time.time()
        self.gender = gender

_sessions: Dict[int, Dict[int, _Session]] = {}
_cleanup_tasks: Dict[int, asyncio.Task] = {}
_locks: Dict[int, asyncio.Lock] = {}

def _lock(cid):
    if cid not in _locks:
        _locks[cid] = asyncio.Lock()
    return _locks[cid]

# ── DB helpers ────────────────────────────────────────────────────────────────
def ensure_tables():
    try:
        from database_dual import _pg_run
        _pg_run(f"""CREATE TABLE IF NOT EXISTS {DB_TABLE}
            (id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
             history TEXT DEFAULT '[]', last_active DOUBLE PRECISION DEFAULT 0,
             gender TEXT DEFAULT 'bot', UNIQUE(chat_id,user_id))""")
        _pg_run(f"""CREATE TABLE IF NOT EXISTS {API_KEY_TABLE}
            (id SERIAL PRIMARY KEY, set_name TEXT NOT NULL DEFAULT 'default',
             provider TEXT NOT NULL, api_key TEXT NOT NULL, slot INT DEFAULT 1,
             gemini_req INT DEFAULT 0, groq_req INT DEFAULT 0, reset_ts DOUBLE PRECISION DEFAULT 0,
             UNIQUE(set_name,provider,slot))""")
        _pg_run(f"""CREATE TABLE IF NOT EXISTS {CHAT_ASSIGN_TABLE}
            (chat_id BIGINT PRIMARY KEY, set_name TEXT NOT NULL DEFAULT 'default',
             updated_at TIMESTAMP DEFAULT NOW())""")
        # Migrate old API_KEY_TABLE if needed (add set_name column)
        _pg_run("""DO $$ BEGIN
            ALTER TABLE chatbot_api_keys ADD COLUMN IF NOT EXISTS set_name TEXT NOT NULL DEFAULT 'default';
        EXCEPTION WHEN OTHERS THEN NULL; END $$""")
    except Exception as e:
        logger.debug(f"[chatbot] ensure_tables: {e}")

def _load_history(chat_id, user_id):
    try:
        from database_dual import _pg_exec
        row = _pg_exec(f"SELECT history FROM {DB_TABLE} WHERE chat_id=%s AND user_id=%s", (chat_id, user_id))
        if row and row[0]:
            return json.loads(row[0])[-MAX_HISTORY_MESSAGES:]
    except Exception: pass
    return []

def _save_history(chat_id, user_id, history, gender):
    try:
        from database_dual import _pg_run
        h = json.dumps(history[-MAX_HISTORY_MESSAGES:])
        _pg_run(f"""INSERT INTO {DB_TABLE} (chat_id,user_id,history,last_active,gender)
            VALUES (%s,%s,%s,%s,%s) ON CONFLICT (chat_id,user_id) DO UPDATE
            SET history=%s,last_active=%s,gender=%s""",
            (chat_id,user_id,h,time.time(),gender, h,time.time(),gender))
    except Exception as e:
        logger.debug(f"[chatbot] _save_history: {e}")

def _clear_history(chat_id, user_id):
    try:
        from database_dual import _pg_run
        _pg_run(f"DELETE FROM {DB_TABLE} WHERE chat_id=%s AND user_id=%s", (chat_id,user_id))
    except Exception: pass

# ── Named API set management ─────────────────────────────────────────────────
def get_set_for_chat(chat_id):
    if chat_id in _chat_assign_cache:
        return _chat_assign_cache[chat_id]
    try:
        from database_dual import _pg_exec
        row = _pg_exec(f"SELECT set_name FROM {CHAT_ASSIGN_TABLE} WHERE chat_id=%s", (chat_id,))
        name = (row[0] if row else None) or "default"
    except Exception:
        name = "default"
    _chat_assign_cache[chat_id] = name
    return name

def assign_chat_to_set(chat_id, set_name):
    set_name = set_name.strip().lower()
    _chat_assign_cache[chat_id] = set_name
    _api_set_cache.pop(set_name, None)
    try:
        from database_dual import _pg_run
        _pg_run(f"""INSERT INTO {CHAT_ASSIGN_TABLE} (chat_id,set_name)
            VALUES (%s,%s) ON CONFLICT (chat_id) DO UPDATE SET set_name=%s,updated_at=NOW()""",
            (chat_id,set_name,set_name))
    except Exception as e:
        logger.debug(f"[chatbot] assign_chat_to_set: {e}")

def get_all_sets():
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(f"SELECT DISTINCT set_name FROM {API_KEY_TABLE} ORDER BY set_name") or []
        return [r[0] for r in rows] or ["default"]
    except Exception:
        return ["default"]

def get_api_keys(chat_id):
    return get_api_keys_for_set(get_set_for_chat(chat_id))

def get_api_keys_for_set(set_name):
    if set_name in _api_set_cache:
        return _api_set_cache[set_name]
    result = {"gemini": [], "groq": []}
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(
            f"SELECT provider,api_key FROM {API_KEY_TABLE} WHERE set_name=%s ORDER BY slot",
            (set_name,)) or []
        for provider, key in rows:
            if provider in result:
                result[provider].append(key)
    except Exception: pass
    if set_name == "default":
        if not result["gemini"] and os.getenv("GEMINI_API_KEY"):
            result["gemini"].append(os.getenv("GEMINI_API_KEY"))
        if not result["groq"] and os.getenv("GROQ_API_KEY"):
            result["groq"].append(os.getenv("GROQ_API_KEY"))
    if result["gemini"] or result["groq"]:
        _api_set_cache[set_name] = result
    return result

def save_api_key_to_set(set_name, provider, api_key, slot=1):
    set_name = set_name.strip().lower()
    _api_set_cache.pop(set_name, None)
    try:
        from database_dual import _pg_run
        _pg_run(f"""INSERT INTO {API_KEY_TABLE} (set_name,provider,api_key,slot)
            VALUES (%s,%s,%s,%s) ON CONFLICT (set_name,provider,slot) DO UPDATE SET api_key=%s""",
            (set_name,provider,api_key,slot,api_key))
    except Exception as e:
        logger.debug(f"[chatbot] save_api_key_to_set: {e}")

def delete_api_key_from_set(set_name, provider, slot):
    _api_set_cache.pop(set_name, None)
    try:
        from database_dual import _pg_run
        _pg_run(f"DELETE FROM {API_KEY_TABLE} WHERE set_name=%s AND provider=%s AND slot=%s",
                (set_name,provider,slot))
    except Exception: pass

def save_api_key(chat_id, provider, api_key, slot=1):
    save_api_key_to_set(get_set_for_chat(chat_id), provider, api_key, slot)

def delete_api_key(chat_id, provider, slot):
    delete_api_key_from_set(get_set_for_chat(chat_id), provider, slot)

def get_usage_stats(chat_id):
    set_name = get_set_for_chat(chat_id)
    try:
        from database_dual import _pg_exec_many
        rows = _pg_exec_many(
            f"SELECT provider,slot,gemini_req,groq_req FROM {API_KEY_TABLE} WHERE set_name=%s",
            (set_name,)) or []
        stats = []
        for provider, slot, g_req, gr_req in rows:
            req = g_req if provider == "gemini" else gr_req
            limit = 1500 if provider == "gemini" else 14400
            stats.append({"provider":provider,"slot":slot,"used":req or 0,"limit":limit,
                          "pct":min(100,int((req or 0)/limit*100)),"set_name":set_name})
        return {"stats":stats,"chat_id":chat_id,"set_name":set_name}
    except Exception:
        return {"stats":[],"chat_id":chat_id,"set_name":set_name}

def _bump_usage(chat_id, provider, api_key):
    set_name = get_set_for_chat(chat_id)
    try:
        from database_dual import _pg_run
        col = "gemini_req" if provider == "gemini" else "groq_req"
        _pg_run(f"UPDATE {API_KEY_TABLE} SET {col}={col}+1 WHERE set_name=%s AND provider=%s AND api_key=%s",
                (set_name,provider,api_key))
    except Exception: pass

def get_gc_gender(chat_id):
    if chat_id in _gender_cache: return _gender_cache[chat_id]
    try:
        from database_dual import get_setting
        g = get_setting(f"chatbot_gender_{chat_id}", "bot") or "bot"
    except Exception: g = "bot"
    _gender_cache[chat_id] = g
    return g

def set_gc_gender(chat_id, gender):
    g = gender if gender in ("boy","girl","bot") else "bot"
    _gender_cache[chat_id] = g
    try:
        from database_dual import set_setting
        set_setting(f"chatbot_gender_{chat_id}", g)
    except Exception: pass

def get_chatbot_enabled(chat_id):
    if chat_id in _enabled_cache: return _enabled_cache[chat_id]
    try:
        from database_dual import get_setting
        v = (get_setting(f"chatbot_{chat_id}","true") or "true").lower() != "false"
    except Exception: v = True
    _enabled_cache[chat_id] = v
    return v

# ── Text normalization ────────────────────────────────────────────────────────
_SC_REV = {
    "ᴀ":"a","ʙ":"b","ᴄ":"c","ᴅ":"d","ᴇ":"e","ꜰ":"f","ɢ":"g","ʜ":"h","ɪ":"i",
    "ᴊ":"j","ᴋ":"k","ʟ":"l","ᴍ":"m","ɴ":"n","ᴏ":"o","ᴘ":"p","ǫ":"q","ʀ":"r",
    "ꜱ":"s","ᴛ":"t","ᴜ":"u","ᴠ":"v","ᴡ":"w","ʏ":"y","ᴢ":"z","ғ":"f",
}
_MATH_B = [(0x1D400,0x1D419,"A"),(0x1D41A,0x1D433,"a"),(0x1D5A0,0x1D5B9,"A"),
           (0x1D5BA,0x1D5D3,"a"),(0x1D670,0x1D689,"A"),(0x1D68A,0x1D6A3,"a")]
_MM = {}
for _s,_e,_b in _MATH_B:
    _bo = ord(_b)
    for _i,_cp in enumerate(range(_s,_e+1)):
        _MM[chr(_cp)] = chr(_bo+_i)
_FW = {chr(0xFF01+i):chr(0x21+i) for i in range(94)}
_FW["\u3000"] = " "

def normalize_text(text):
    if not text: return ""
    result = []
    for ch in text:
        n = _MM.get(ch) or _SC_REV.get(ch) or _FW.get(ch)
        if n:
            result.append(n)
            continue
        nfkd = unicodedata.normalize("NFKD", ch)
        ac = nfkd.encode("ascii","ignore").decode("ascii")
        result.append(ac if ac else ch)
    return "".join(result).lower()

# ── Foul word handling ────────────────────────────────────────────────────────
def _has_foul(text): return bool(_FOUL_RE.search(text))

async def handle_foul_word(bot, chat_id, user_id, user_name, text, reply_fn):
    if not _has_foul(text): return False
    key = (chat_id, user_id)
    count = _foul_warns.get(key, 0) + 1
    _foul_warns[key] = count
    if count == 1:
        await reply_fn(random.choice([
            f"yaar {user_name}, please aise mat bolo na. sab ke liye group hai 🙏",
            f"{user_name} bhai, aisi language avoid karo na yaar",
        ]))
    elif count == 2:
        await reply_fn(
            f"{user_name} yaar, dobara kaha tha. please language theek karo warna admin ko batana padega"
        )
    else:
        await reply_fn(
            f"{user_name}, ab owner ko report karna padega. Seedha baat karo — /contact"
        )
        try:
            from core.config import OWNER_ID
            await bot.send_message(chat_id=OWNER_ID,
                text=f"⚠️ <b>Foul Language Report</b>\n\n"
                     f"User: <a href='tg://user?id={user_id}'>{user_name}</a> (<code>{user_id}</code>)\n"
                     f"Chat: <code>{chat_id}</code> | Warns: {count}\n"
                     f"Msg: <code>{text[:200]}</code>",
                parse_mode="HTML")
        except Exception: pass
    return True

# ── Anime link helper ─────────────────────────────────────────────────────────
def _extract_anime_q(text):
    patterns = [
        r"(?:link|invite|join|channel|watch|kahan|dekhu?)\s+(?:do|bhai|yaar|na|de|dedo|chahiye)?\s*(?:of|for|ka|ki|ke)?\s*([a-z0-9 ]+)",
        r"([a-z0-9 ]+)\s+(?:ka|ki|ke)\s+link",
    ]
    for pat in patterns:
        m = re.search(pat, text.lower().strip())
        if m:
            q = m.group(1).strip()
            if len(q) >= 3: return q
    return None

async def _get_anime_invite(bot, q, chat_id):
    try:
        from database_dual import get_all_links, get_all_anime_channel_links
        from filter_poster import get_link_expiry_minutes
        exp = get_link_expiry_minutes(chat_id)
        ts = int(time.time()) + exp*60
        qn = normalize_text(q)
        for row in (get_all_links(limit=2000) or []):
            ct = normalize_text(row[2] or row[1] or "")
            if qn in ct or ct in qn:
                try:
                    cid = row[1]
                    try: cid = int(cid)
                    except: pass
                    inv = await bot.create_chat_invite_link(chat_id=cid,expire_date=ts,member_limit=1,
                                                            creates_join_request=False,name="CB")
                    return inv.invite_link
                except Exception: pass
        for arow in (get_all_anime_channel_links() or []):
            an = normalize_text(arow[1] or "")
            if qn in an or an in qn:
                try:
                    inv = await bot.create_chat_invite_link(chat_id=int(arow[2]),expire_date=ts,
                                                            member_limit=1,creates_join_request=False,name="CB")
                    return inv.invite_link
                except Exception: pass
    except Exception as e:
        logger.debug(f"[chatbot] anime invite: {e}")
    return None

# ── AI providers ──────────────────────────────────────────────────────────────
async def _call_gemini(api_key, messages, system):
    if not api_key: return None
    try:
        import aiohttp
        contents = [{"role":"user" if m["role"]=="user" else "model",
                     "parts":[{"text":m["content"]}]} for m in messages]
        payload = {"system_instruction":{"parts":[{"text":system}]},"contents":contents,
                   "generationConfig":{"temperature":0.88,"maxOutputTokens":200,"topP":0.95},
                   "safetySettings":[{"category":"HARM_CATEGORY_HARASSMENT","threshold":"BLOCK_ONLY_HIGH"},
                                     {"category":"HARM_CATEGORY_HATE_SPEECH","threshold":"BLOCK_ONLY_HIGH"}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url,json=payload,timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    d = await r.json()
                    c = d.get("candidates",[])
                    if c:
                        pts = c[0].get("content",{}).get("parts",[])
                        if pts: return pts[0].get("text","").strip()
    except Exception as e:
        logger.debug(f"[chatbot] gemini: {e}")
    return None

async def _call_groq(api_key, messages, system):
    if not api_key: return None
    try:
        import aiohttp
        msgs = [{"role":"system","content":system}] + messages
        payload = {"model":"llama-3.3-70b-versatile","messages":msgs,"max_tokens":180,"temperature":0.88}
        headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.groq.com/openai/v1/chat/completions",
                              json=payload,headers=headers,timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    d = await r.json()
                    ch = d.get("choices",[])
                    if ch: return ch[0].get("message",{}).get("content","").strip()
    except Exception as e:
        logger.debug(f"[chatbot] groq: {e}")
    return None

# ── Cleanup ───────────────────────────────────────────────────────────────────
async def _idle_cleanup_loop(chat_id, bot):
    while True:
        await asyncio.sleep(60)
        now = time.time()
        async with _lock(chat_id):
            sessions = _sessions.get(chat_id, {})
            for uid in [u for u,s in sessions.items() if now-s.last_active >= IDLE_TIMEOUT_SECONDS]:
                sess = sessions.pop(uid, None)
                if sess:
                    _clear_history(chat_id, uid)
                    try:
                        closer = random.choice(IDLE_CLOSERS.get(sess.gender, IDLE_CLOSERS["bot"]))
                        await bot.send_message(chat_id=chat_id, text=closer)
                    except Exception: pass
            if not sessions: _sessions.pop(chat_id, None)

def _ensure_cleanup(chat_id, bot):
    t = _cleanup_tasks.get(chat_id)
    if t is None or t.done():
        try:
            _cleanup_tasks[chat_id] = asyncio.get_event_loop().create_task(_idle_cleanup_loop(chat_id,bot))
        except Exception: pass

# ── Main entry point ──────────────────────────────────────────────────────────
async def handle_chatbot_message(bot, chat_id, user_id, user_name, message_text, reply_fn):
    if not get_chatbot_enabled(chat_id): return False
    if await handle_foul_word(bot,chat_id,user_id,user_name,message_text,reply_fn): return True

    gender = get_gc_gender(chat_id)
    system = SYSTEM_PROMPTS.get(gender, SYSTEM_PROMPTS["bot"])
    keys = get_api_keys(chat_id)
    g_keys, gr_keys = keys.get("gemini",[]), keys.get("groq",[])
    if not g_keys and not gr_keys: return False

    _ensure_cleanup(chat_id, bot)
    async with _lock(chat_id):
        sessions = _sessions.setdefault(chat_id, {})
        if user_id not in sessions:
            if len(sessions) >= MAX_CONCURRENT_USERS: return False
            sess = _Session(user_id, chat_id, gender)
            sess.history = _load_history(chat_id, user_id)
            sessions[user_id] = sess
            if not sess.history:
                try: await reply_fn(random.choice(STARTERS.get(gender, STARTERS["bot"])))
                except Exception: pass
        else:
            sess = sessions[user_id]
        sess.last_active = time.time(); sess.gender = gender
        sess.history.append({"role":"user","content":message_text})
        if len(sess.history) > MAX_HISTORY_MESSAGES: sess.history = sess.history[-MAX_HISTORY_MESSAGES:]
        hist = list(sess.history)

    # Anime link detection
    link_kw = ["link","invite","join karna","channel","kahan dekhu","watch kaise","link do","link chahiye"]
    if any(kw in message_text.lower() for kw in link_kw):
        q = _extract_anime_q(message_text)
        if q:
            inv = await _get_anime_invite(bot, q, chat_id)
            if inv:
                resp = f"haan bhai! {q} ka link ye raha — <a href='{inv}'>join karo</a> 🎌\n<i>jaldi karo, 5 min mein expire hoga!</i>"
                await reply_fn(resp)
                async with _lock(chat_id):
                    s2 = _sessions.get(chat_id,{}).get(user_id)
                    if s2: s2.history.append({"role":"assistant","content":f"Gave invite link for {q}"})
                return True

    # AI call
    reply = None; used_key = None; used_prov = None
    order = []
    if g_keys: order.append(("gemini", random.choice(g_keys)))
    if gr_keys: order.append(("groq", random.choice(gr_keys)))
    if len(order)==2 and random.random()>0.6: order.reverse()
    for prov, key in order:
        r = await (_call_gemini(key,hist,system) if prov=="gemini" else _call_groq(key,hist,system))
        if r: reply=r; used_key=key; used_prov=prov; break

    # Handle link: response from AI
    if reply and reply.startswith("link:"):
        q = reply[5:].strip()
        inv = await _get_anime_invite(bot, q, chat_id)
        if inv:
            reply = f"ye lo {q} ka link — <a href='{inv}'>join karo</a> 🎌\n<i>5 min mein expire hoga!</i>"
        else:
            reply = f"yaar {q} abhi available nahi hai 😕 /request se request karo"

    if not reply: reply = random.choice(_FALLBACK_REPLIES.get(gender, _FALLBACK_REPLIES["bot"]))

    if used_key and used_prov:
        try: asyncio.get_event_loop().create_task(asyncio.to_thread(_bump_usage,chat_id,used_prov,used_key))
        except Exception: pass

    async with _lock(chat_id):
        s3 = _sessions.get(chat_id,{}).get(user_id)
        if s3:
            s3.history.append({"role":"assistant","content":reply})
            if len(s3.history)>MAX_HISTORY_MESSAGES: s3.history=s3.history[-MAX_HISTORY_MESSAGES:]
            asyncio.get_event_loop().create_task(asyncio.to_thread(_save_history,chat_id,user_id,s3.history,gender))

    try: await reply_fn(reply); return True
    except Exception: return False

def get_active_sessions(chat_id): return len(_sessions.get(chat_id,{}))
def get_all_sessions_info():
    now=time.time()
    return [{"chat_id":c,"user_id":u,"messages":len(s.history),"idle_seconds":int(now-s.last_active),"gender":s.gender}
            for c,ss in _sessions.items() for u,s in ss.items()]
def reset_user_session(chat_id, user_id):
    _sessions.get(chat_id,{}).pop(user_id,None)
    _clear_history(chat_id,user_id)

try: ensure_tables()
except Exception: pass
