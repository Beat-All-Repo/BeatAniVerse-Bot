# ====================================================================
# PLACE AT: /app/modules/animerequest.py
# ACTION: Replace existing file
# ====================================================================
"""
Anime Request System for BeatVerseProbot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPAM PROTECTION LAYERS:
  1. AniList API validation — only real anime titles accepted
  2. Per-user cooldown (5 min between requests)
  3. Per-user pending cap (max 5 pending at a time)
  4. Duplicate detection (same title can't be requested twice in same chat)

USER COMMANDS:
  /request <anime name>  — submit a validated anime request
  /myrequests            — view your own requests

ADMIN COMMANDS:
  /requests              — view all pending requests
  /fulfill <id>          — mark a request as fulfilled
  /delrequest <id>       — delete a request

STORAGE BACKEND:
  • If DATABASE_URL is set  → uses PostgreSQL via SQLAlchemy (primary)
  • If only MONGO_DB_URI is set → uses MongoDB via Motor (fallback)
  • If neither is set → module is DISABLED gracefully (no crash)

FIX APPLIED:
  • Replaced `raise SystemExit(...)` with LOGGER.warning() so the bot
    doesn't crash at startup when no DB is configured.
  • Handler registration is now conditional on DB availability.
"""

import threading
import time
import logging

import requests as http
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from beataniversebot_compat import dispatcher, DRAGONS, DB_URI, MONGO_DB_URI
from modules.disable import DisableAbleCommandHandler

LOGGER = logging.getLogger(__name__)

# ── Tunable constants ──────────────────────────────────────────────────────────
COOLDOWN_SECONDS = 300
MAX_PENDING_PER_USER = 5

ANILIST_API = "https://graphql.anilist.co"
ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english native }
    status
    episodes
    averageScore
    siteUrl
    coverImage { extraLarge large medium }
  }
}
"""

# ── In-memory cooldown {user_id: unix_timestamp_of_last_request} ───────────────
_cooldowns: dict = {}
_cd_lock = threading.Lock()

# ── Pick storage backend ───────────────────────────────────────────────────────
_USE_MONGO = False
_MODULE_DISABLED = False  # Set to True when no DB is configured

if DB_URI:
    # ── SQL backend ───────────────────────────────────────────────────────────
    import threading as _threading
    from sqlalchemy import BigInteger, Boolean, Column, String, UnicodeText
    from modules.sql import BASE, SESSION

    class AnimeRequest(BASE):
        __tablename__ = "anime_requests"

        id              = Column(BigInteger, primary_key=True, autoincrement=True)
        user_id         = Column(BigInteger,  nullable=False, index=True)
        chat_id         = Column(String(14),  nullable=False, index=True)
        raw_query       = Column(UnicodeText, nullable=False)
        validated_title = Column(UnicodeText, nullable=False)
        anilist_id      = Column(BigInteger,  nullable=True)
        anilist_url     = Column(UnicodeText, nullable=True)
        fulfilled       = Column(Boolean,     default=False)
        created_at      = Column(BigInteger,  nullable=False)

        def __init__(self, user_id, chat_id, raw_query, validated_title,
                     anilist_id=None, anilist_url=""):
            self.user_id         = user_id
            self.chat_id         = str(chat_id)
            self.raw_query       = raw_query
            self.validated_title = validated_title
            self.anilist_id      = anilist_id
            self.anilist_url     = anilist_url
            self.fulfilled       = False
            self.created_at      = int(time.time())

        def __repr__(self):
            return f"<AnimeRequest #{self.id} — {self.validated_title}>"

    AnimeRequest.__table__.create(checkfirst=True)
    DB_LOCK = _threading.RLock()

elif MONGO_DB_URI:
    # ── MongoDB backend ───────────────────────────────────────────────────────
    _USE_MONGO = True
    try:
        from BeatVerseProbot.utils.mongo import db as _mongo_db
    except ImportError:
        _mongo_db = None
    _req_col = _mongo_db.anime_requests
    _counter_col = _mongo_db.anime_req_counters

    import asyncio as _asyncio

    def _run(coro):
        """Run an async Motor coroutine synchronously from a sync context."""
        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_asyncio.run, coro)
                    return future.result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return _asyncio.run(coro)

    async def _next_id():
        result = await _counter_col.find_one_and_update(
            {"_id": "anime_requests"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )
        return result["seq"]

else:
    # ── No DB configured — disable module gracefully ───────────────────────────
    _MODULE_DISABLED = True
    LOGGER.warning(
        "animerequest: Neither DATABASE_URL nor MONGO_DB_URI is configured. "
        "The Requests module will be disabled."
    )


# ── AniList validation ─────────────────────────────────────────────────────────

def validate_on_anilist(query: str) -> dict | None:
    try:
        resp = http.post(
            ANILIST_API,
            json={"query": ANILIST_QUERY, "variables": {"search": query}},
            timeout=8,
        )
        data = resp.json()
        if "errors" in data or not data.get("data", {}).get("Media"):
            return None
        media = data["data"]["Media"]
        titles = media["title"]
        cover_img = ((media.get("coverImage") or {}).get("extraLarge")
                     or (media.get("coverImage") or {}).get("large")
                     or (media.get("coverImage") or {}).get("medium") or "")
        return {
            "id":       media["id"],
            "romaji":   titles.get("romaji") or "",
            "english":  titles.get("english") or "",
            "native":   titles.get("native") or "",
            "status":   (media.get("status") or "").replace("_", " ").title(),
            "episodes": media.get("episodes") or "?",
            "score":    media.get("averageScore") or "N/A",
            "url":      media.get("siteUrl") or "",
            "cover":    cover_img,
        }
    except Exception:
        return None


# ── DB helpers — SQL ───────────────────────────────────────────────────────────

def _sql_insert(user_id, chat_id, raw_query, validated_title, anilist_id, anilist_url):
    with DB_LOCK:
        row = AnimeRequest(user_id, str(chat_id), raw_query,
                           validated_title, anilist_id, anilist_url)
        SESSION.add(row)
        SESSION.commit()
        return row.id


def _sql_pending_count(user_id, chat_id):
    try:
        return (SESSION.query(AnimeRequest)
                .filter_by(user_id=user_id, chat_id=str(chat_id), fulfilled=False)
                .count())
    finally:
        SESSION.close()


def _sql_duplicate(chat_id, anilist_id):
    try:
        return (SESSION.query(AnimeRequest)
                .filter_by(chat_id=str(chat_id), anilist_id=anilist_id, fulfilled=False)
                .count()) > 0
    finally:
        SESSION.close()


def _sql_get_pending(chat_id):
    try:
        return (SESSION.query(AnimeRequest)
                .filter_by(chat_id=str(chat_id), fulfilled=False)
                .order_by(AnimeRequest.id.asc()).all())
    finally:
        SESSION.close()


def _sql_fulfill(req_id):
    with DB_LOCK:
        row = SESSION.query(AnimeRequest).get(req_id)
        if row:
            row.fulfilled = True
            SESSION.commit()
            return True
        SESSION.close()
        return False


def _sql_delete(req_id):
    with DB_LOCK:
        row = SESSION.query(AnimeRequest).get(req_id)
        if row:
            SESSION.delete(row)
            SESSION.commit()
            return True
        SESSION.close()
        return False


def _sql_user_requests(user_id, chat_id):
    try:
        return (SESSION.query(AnimeRequest)
                .filter_by(user_id=user_id, chat_id=str(chat_id))
                .order_by(AnimeRequest.fulfilled.asc(), AnimeRequest.id.desc())
                .limit(10).all())
    finally:
        SESSION.close()


# ── DB helpers — MongoDB ───────────────────────────────────────────────────────

async def _mongo_insert(user_id, chat_id, raw_query, validated_title, anilist_id, anilist_url):
    req_id = await _next_id()
    doc = {
        "_id":            req_id,
        "user_id":        user_id,
        "chat_id":        str(chat_id),
        "raw_query":      raw_query,
        "validated_title": validated_title,
        "anilist_id":     anilist_id,
        "anilist_url":    anilist_url,
        "fulfilled":      False,
        "created_at":     int(time.time()),
    }
    await _req_col.insert_one(doc)
    return req_id


async def _mongo_pending_count(user_id, chat_id):
    return await _req_col.count_documents(
        {"user_id": user_id, "chat_id": str(chat_id), "fulfilled": False}
    )


async def _mongo_duplicate(chat_id, anilist_id):
    return bool(await _req_col.find_one(
        {"chat_id": str(chat_id), "anilist_id": anilist_id, "fulfilled": False}
    ))


async def _mongo_get_pending(chat_id):
    cursor = _req_col.find(
        {"chat_id": str(chat_id), "fulfilled": False}
    ).sort("_id", 1)
    return await cursor.to_list(length=50)


async def _mongo_fulfill(req_id):
    result = await _req_col.update_one({"_id": req_id}, {"$set": {"fulfilled": True}})
    return result.modified_count > 0


async def _mongo_delete(req_id):
    result = await _req_col.delete_one({"_id": req_id})
    return result.deleted_count > 0


async def _mongo_user_requests(user_id, chat_id):
    cursor = _req_col.find(
        {"user_id": user_id, "chat_id": str(chat_id)}
    ).sort([("fulfilled", 1), ("_id", -1)]).limit(10)
    return await cursor.to_list(length=10)


# ── Unified DB helpers (dispatch to correct backend) ──────────────────────────

def _insert_request(user_id, chat_id, raw_query, validated_title, anilist_id, anilist_url):
    if _USE_MONGO:
        return _run(_mongo_insert(user_id, chat_id, raw_query, validated_title, anilist_id, anilist_url))
    return _sql_insert(user_id, chat_id, raw_query, validated_title, anilist_id, anilist_url)


def _pending_count_for_user(user_id, chat_id):
    if _USE_MONGO:
        return _run(_mongo_pending_count(user_id, chat_id))
    return _sql_pending_count(user_id, chat_id)


def _duplicate_exists(chat_id, anilist_id):
    if _USE_MONGO:
        return _run(_mongo_duplicate(chat_id, anilist_id))
    return _sql_duplicate(chat_id, anilist_id)


def _get_pending(chat_id):
    if _USE_MONGO:
        return _run(_mongo_get_pending(chat_id))
    return _sql_get_pending(chat_id)


def _fulfill(req_id):
    if _USE_MONGO:
        return _run(_mongo_fulfill(req_id))
    return _sql_fulfill(req_id)


def _delete(req_id):
    if _USE_MONGO:
        return _run(_mongo_delete(req_id))
    return _sql_delete(req_id)


def _user_requests(user_id, chat_id):
    if _USE_MONGO:
        return _run(_mongo_user_requests(user_id, chat_id))
    return _sql_user_requests(user_id, chat_id)


# ── Cooldown helpers ───────────────────────────────────────────────────────────

def _cooldown_remaining(user_id: int) -> int:
    with _cd_lock:
        elapsed = time.time() - _cooldowns.get(user_id, 0)
        return max(0, int(COOLDOWN_SECONDS - elapsed))


def _stamp_cooldown(user_id: int):
    with _cd_lock:
        _cooldowns[user_id] = time.time()


# ── Helper: get title/url from a row (works for both SQL ORM obj and Mongo dict) ─

def _title(row):
    return row.validated_title if hasattr(row, "validated_title") else row["validated_title"]


def _url(row):
    return row.anilist_url if hasattr(row, "anilist_url") else row.get("anilist_url", "")


def _rid(row):
    return row.id if hasattr(row, "id") else row["_id"]


def _fulfilled(row):
    return row.fulfilled if hasattr(row, "fulfilled") else row["fulfilled"]


def _uid(row):
    return row.user_id if hasattr(row, "user_id") else row["user_id"]


# ── /request ───────────────────────────────────────────────────────────────────

async def request_cmd(update: Update, context: CallbackContext):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat
    args    = context.args

    if not args:
        return await message.reply_text(
            "📋 *Usage:* `/request <anime name>`\n"
            "_Example:_ `/request Attack on Titan`",
            parse_mode=ParseMode.HTML,
        )

    wait = _cooldown_remaining(user.id)
    if wait:
        m, s = divmod(wait, 60)
        return await message.reply_text(
            f"⏳ Slow down! Wait *{m}m {s}s* before your next request.",
            parse_mode=ParseMode.HTML,
        )

    pending = _pending_count_for_user(user.id, chat.id)
    if pending >= MAX_PENDING_PER_USER:
        return await message.reply_text(
            f"❌ You already have *{pending}* unresolved requests.\n"
            "Please wait for them to be fulfilled first.",
            parse_mode=ParseMode.HTML,
        )

    query = " ".join(args).strip()
    wait_msg = await message.reply_text(
        f"🔍 Checking *{query}* on AniList...",
        parse_mode=ParseMode.HTML,
    )

    anime = validate_on_anilist(query)
    if not anime:
        await wait_msg.edit_text(
            f"❌ *\"{query}\"* is not recognised as a valid anime.\n\n"
            "Only real anime titles (verified via AniList) are accepted.\n\n"
            "_Tip:_ find the exact title on [AniList](https://anilist.co) first.",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    if _duplicate_exists(chat.id, anime["id"]):
        await wait_msg.edit_text(
            f"⚠️ *{anime['english'] or anime['romaji']}* is already in the pending list!",
            parse_mode=ParseMode.HTML,
        )
        return

    canonical = anime["english"] or anime["romaji"]
    req_id = _insert_request(
        user.id, chat.id, query,
        canonical, anime["id"], anime["url"]
    )
    _stamp_cooldown(user.id)
    await wait_msg.delete()

    # Build a styled request card with cover image if available
    cover = anime.get("cover") or anime.get("url", "")
    caption = (
        f"<b>📨 ʀᴇQᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"» <b>ᴀɴɪᴍᴇ :</b> <a href=\'{anime['url']}\'>{canonical}</a>\n"
        f"» <b>ɴᴀᴛɪᴠᴇ :</b> {anime.get('native', '') or ''}\n"
        f"» <b>ᴇᴘɪsᴏᴅᴇs :</b> <code>{anime['episodes']}</code>\n"
        f"» <b>sᴛᴀᴛᴜs :</b> <code>{anime['status']}</code>\n"
        f"» <b>sᴄᴏʀᴇ :</b> <code>{anime['score']}/100</code>\n\n"
        f"» <b>ʀᴇQᴜᴇsᴛ ɪᴅ :</b> <code>#{req_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"<i>Admins will review it soon.</i>"
    )
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 ᴠɪᴇᴡ ᴏɴ ᴀɴɪʟɪsᴛ", url=anime["url"])
    ]])
    if cover and cover.startswith("http"):
        try:
            await context.bot.send_photo(
                chat_id=message.chat_id,
                photo=cover,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
            return
        except Exception:
            pass
    await message.reply_text(
        caption,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
        reply_markup=kb,
    )


# ── /myrequests ────────────────────────────────────────────────────────────────

def myrequests_cmd(update: Update, context: CallbackContext):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    rows = _user_requests(user.id, chat.id)
    if not rows:
        return message.reply_text("You have no requests in this chat yet.")

    lines = ["📋 *Your Requests:*\n"]
    for r in rows:
        icon = "✅" if _fulfilled(r) else "⏳"
        lines.append(f"{icon} `#{_rid(r)}` — [{_title(r)}]({_url(r)})")

    message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── /requests (admin) ──────────────────────────────────────────────────────────

def requests_list_cmd(update: Update, context: CallbackContext):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat

    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can view the request list!")

    pending = _get_pending(chat.id)
    if not pending:
        return message.reply_text("✨ No pending requests right now!")

    lines = [f"📋 *Pending Requests — {chat.title}:*\n"]
    for r in pending:
        lines.append(
            f"• `#{_rid(r)}` — [{_title(r)}]({_url(r)})\n"
            f"   _user_ `{_uid(r)}`"
        )
    lines.append("\n`/fulfill <id>` · `/delrequest <id>`")

    message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── /fulfill (admin) ───────────────────────────────────────────────────────────

def fulfill_cmd(update: Update, context: CallbackContext):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat
    args    = context.args

    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can fulfill requests!")

    if not args or not args[0].isdigit():
        return message.reply_text("Usage: `/fulfill <request id>`", parse_mode=ParseMode.HTML)

    req_id = int(args[0])
    if _fulfill(req_id):
        message.reply_text(f"✅ Request `#{req_id}` marked as *fulfilled*!", parse_mode=ParseMode.HTML)
    else:
        message.reply_text(f"❌ Request `#{req_id}` not found.", parse_mode=ParseMode.HTML)


# ── /delrequest (admin) ────────────────────────────────────────────────────────

def delrequest_cmd(update: Update, context: CallbackContext):
    message = update.effective_message
    user    = update.effective_user
    chat    = update.effective_chat
    args    = context.args

    member = chat.get_member(user.id)
    if member.status not in ("administrator", "creator") and user.id not in DRAGONS:
        return message.reply_text("» Only admins can delete requests!")

    if not args or not args[0].isdigit():
        return message.reply_text("Usage: `/delrequest <request id>`", parse_mode=ParseMode.HTML)

    req_id = int(args[0])
    if _delete(req_id):
        message.reply_text(f"🗑️ Request `#{req_id}` deleted.", parse_mode=ParseMode.HTML)
    else:
        message.reply_text(f"❌ Request `#{req_id}` not found.", parse_mode=ParseMode.HTML)


# ── Register handlers (only when a DB backend is available) ───────────────────

if not _MODULE_DISABLED:
    REQ_HANDLER     = DisableAbleCommandHandler("request",    request_cmd,       run_async=True)
    MYREQ_HANDLER   = DisableAbleCommandHandler("myrequests", myrequests_cmd,    run_async=True)
    LIST_HANDLER    = DisableAbleCommandHandler("requests",   requests_list_cmd, run_async=True)
    FULFILL_HANDLER = DisableAbleCommandHandler("fulfill",    fulfill_cmd,       run_async=True)
    DELREQ_HANDLER  = DisableAbleCommandHandler("delrequest", delrequest_cmd,    run_async=True)

    for _h in [REQ_HANDLER, MYREQ_HANDLER, LIST_HANDLER, FULFILL_HANDLER, DELREQ_HANDLER]:
        dispatcher.add_handler(_h)

    __command_list__ = ["request", "myrequests", "requests", "fulfill", "delrequest"]
    __handlers__     = [REQ_HANDLER, MYREQ_HANDLER, LIST_HANDLER, FULFILL_HANDLER, DELREQ_HANDLER]

else:
    __command_list__ = []
    __handlers__     = []

__mod_name__ = "Requests"
__help__ = """
*Anime Request System:*

*User commands:*
 • `/request <anime name>` — submit a request (must be a real AniList title)
 • `/myrequests` — see your own requests & status

*Admin commands:*
 • `/requests` — view all pending requests
 • `/fulfill <id>` — mark a request fulfilled
 • `/delrequest <id>` — delete a request

*Built-in spam protection:*
 ✦ AniList API validates every title before it touches the DB
 ✦ 5-minute cooldown between requests per user
 ✦ Max 5 pending requests per user at a time
 ✦ Duplicate titles (same chat) are rejected automatically

*Storage:* PostgreSQL (primary) or MongoDB (fallback)
*Note:* This module requires DATABASE_URL or MONGO_DB_URI to be configured.
"""
