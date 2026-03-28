"""handlers/media_cmds.py — /anime /manga /movie /tvshow /search"""
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_ID, OWNER_ID, TMDB_API_KEY
from core.text_utils import b, bq, code, e
from core.helpers import safe_reply
from core.filters_system import force_sub_required, passes_filter
from handlers.start import delete_update_message
from handlers.post_gen import generate_and_send_post
from core.state_machine import user_states

@force_sub_required
async def anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID): return
    if not passes_filter(update, "anime"): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /anime [name]") + "\n" + bq("<b>Example:</b> /anime Naruto"))
        return
    await generate_and_send_post(context, update.effective_chat.id, "anime", " ".join(context.args))

@force_sub_required
async def manga_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID): return
    if not passes_filter(update, "manga"): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /manga [name]") + "\n" + bq("<b>Example:</b> /manga One Piece"))
        return
    await generate_and_send_post(context, update.effective_chat.id, "manga", " ".join(context.args))

@force_sub_required
async def movie_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID): return
    if not passes_filter(update, "movie"): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /movie [name]"))
        return
    if not TMDB_API_KEY:
        await safe_reply(update, b("⚠️ TMDB API key not configured."))
        return
    await generate_and_send_post(context, update.effective_chat.id, "movie", " ".join(context.args))

@force_sub_required
async def tvshow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    if uid not in (ADMIN_ID, OWNER_ID): return
    if not passes_filter(update, "tvshow"): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /tvshow [name]"))
        return
    if not TMDB_API_KEY:
        await safe_reply(update, b("⚠️ TMDB API key not configured."))
        return
    await generate_and_send_post(context, update.effective_chat.id, "tvshow", " ".join(context.args))

@force_sub_required
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /search [name]") + "\n" + bq(b("Example: /search Naruto")))
        return
    from api.anilist import AniListClient
    from api.mangadex import MangaDexClient
    from api.tmdb import TMDBClient
    from core.helpers import safe_send_message, safe_delete
    from core.buttons import bold_button
    from telegram import InlineKeyboardMarkup
    chat_id = update.effective_chat.id
    query_text = " ".join(context.args)
    searching_msg = await safe_send_message(context.bot, chat_id, b(f"🔍 Searching for: {e(query_text)}…"))
    results = []
    anime = AniListClient.search_anime(query_text)
    if anime:
        t = (anime.get("title") or {})
        results.append(("anime", anime["id"], f"🎌 {t.get('romaji') or t.get('english') or 'Unknown'}", "anime"))
    manga = AniListClient.search_manga(query_text)
    if manga:
        t = (manga.get("title") or {})
        results.append(("manga", manga["id"], f"📚 {t.get('romaji') or t.get('english') or 'Unknown'}", "manga"))
    if TMDB_API_KEY:
        movie = TMDBClient.search_movie(query_text)
        if movie:
            results.append(("movie", movie.get("id", 0), f"🎬 {movie.get('title') or 'Unknown'}", "movie"))
        tv = TMDBClient.search_tv(query_text)
        if tv:
            results.append(("tvshow", tv.get("id", 0), f"📺 {tv.get('name') or 'Unknown'}", "tvshow"))
    md_results = MangaDexClient.search_manga(query_text, limit=3)
    for md in md_results[:2]:
        attrs = md.get("attributes", {}) or {}
        titles = attrs.get("title", {}) or {}
        title = titles.get("en") or next(iter(titles.values()), "Unknown")
        results.append(("mangadex", md["id"], f"📖 {title} (MangaDex)", "mangadex"))
    if searching_msg:
        await safe_delete(context.bot, chat_id, searching_msg.message_id)
    if not results:
        await safe_send_message(context.bot, chat_id, b("❌ No results found.") + "\n" + bq(b("Try a different search term.")))
        return
    keyboard = [[bold_button(label[:40], callback_data=f"search_result_{cb_type}_{media_id}")] for _, media_id, label, cb_type in results]
    await safe_send_message(context.bot, chat_id, b(f"🔍 Search results for: {e(query_text)}"), reply_markup=InlineKeyboardMarkup(keyboard))
