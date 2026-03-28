"""
handlers/inline_handler.py
==========================
@bot inline query handler — 4 divisions:
  1. Empty → show main menu (Poster / Watch / Character / Group Mgmt)
  2. poster <n> or <n> → AniList search with cover photo
  3. watch <n> → browse generated_links (anime channels)
  4. character <n> → character info with photo
  5. manage → group management quick cards
Force-sub gate for non-admin users.
"""
import re
import asyncio

from telegram import (
    Update, InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL
from core.logging_setup import logger
from core.text_utils import b, bq, code, e, small_caps
from core.filters_system import force_sub_required, get_unsubscribed_channels


@force_sub_required
async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query_obj = update.inline_query
    if not query_obj:
        return

    uid = query_obj.from_user.id
    search = (query_obj.query or "").strip()

    # Force-sub gate
    if uid not in (ADMIN_ID, OWNER_ID):
        try:
            from database_dual import is_user_banned
            if is_user_banned(uid):
                return
        except Exception:
            pass
        try:
            unsubbed = await get_unsubscribed_channels(uid, context.bot)
            if unsubbed:
                ch_list = "\n".join(f"• {n}" for n, _, _ in unsubbed[:3])
                await query_obj.answer([
                    InlineQueryResultArticle(
                        id="fsub_gate",
                        title=small_caps("⚠️ subscribe to channels first"),
                        description=small_caps("tap to see required channels"),
                        input_message_content=InputTextMessageContent(
                            b(small_caps("⚠️ please subscribe to all required channels first.")) + "\n"
                            + bq(ch_list + "\n\n" + small_caps("use /start in the bot to join.")),
                            parse_mode=ParseMode.HTML,
                        ),
                    )
                ], cache_time=10, is_personal=True)
                return
        except Exception:
            pass

    results = []
    search_lower = search.lower()

    # ── EMPTY QUERY — show 4 division menu ────────────────────────────────────
    if not search:
        menu_items = [
            ("🎌 Poster", "poster", "Search anime/manga/movie poster",
             "Type: @YourBot poster demon slayer"),
            ("📺 Anime to Watch", "watch", "Browse available anime channels",
             "Type: @YourBot watch jujutsu kaisen"),
            ("👤 Character Info", "character", "Search anime character details",
             "Type: @YourBot character tanjiro"),
            ("⚙️ Group Mgmt", "manage", "Group management quick commands",
             "Type: @YourBot manage to see commands"),
        ]
        for title_lbl, kw, desc, hint in menu_items:
            results.append(
                InlineQueryResultArticle(
                    id=f"menu_{kw}",
                    title=small_caps(title_lbl),
                    description=small_caps(desc),
                    input_message_content=InputTextMessageContent(
                        b(small_caps(title_lbl)) + "\n" + bq(small_caps(hint)),
                        parse_mode=ParseMode.HTML,
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            small_caps(f"🔍 search {kw}"),
                            switch_inline_query_current_chat=f"{kw} "
                        )
                    ]]),
                )
            )
        try:
            await query_obj.answer(results, cache_time=30, is_personal=False)
        except Exception:
            pass
        return

    # ── WATCH — search generated_links ────────────────────────────────────────
    if search_lower.startswith("watch"):
        watch_q = re.sub(r"^watch\s*", "", search, flags=re.IGNORECASE).strip()
        try:
            from database_dual import get_all_links, get_setting
            from core.config import BOT_USERNAME
            all_links = get_all_links(limit=200, offset=0) or []

            seen_t: set = set()
            for row in all_links:
                link_id_r = row[0]
                ch_title = (row[2] or "").strip()
                if not ch_title or ch_title.lower() in seen_t:
                    continue
                if watch_q and watch_q.lower() not in ch_title.lower():
                    continue
                seen_t.add(ch_title.lower())

                deep_link = f"https://t.me/{BOT_USERNAME}?start={link_id_r}"
                join_text = small_caps("ᴊᴏɪɴ ɴᴏᴡ")
                kb = InlineKeyboardMarkup([[InlineKeyboardButton(join_text, url=deep_link)]])

                results.append(
                    InlineQueryResultArticle(
                        id=f"watch_{link_id_r}",
                        title=small_caps(ch_title[:40]),
                        description=small_caps("tap to get join link"),
                        input_message_content=InputTextMessageContent(
                            b(small_caps(ch_title)) + "\n"
                            + bq(small_caps("click join now to access this anime channel")),
                            parse_mode=ParseMode.HTML,
                        ),
                        reply_markup=kb,
                    )
                )
                if len(results) >= 10:
                    break
        except Exception as exc:
            logger.debug(f"[inline] watch: {exc}")

        try:
            await query_obj.answer(
                results or [InlineQueryResultArticle(
                    id="watch_empty",
                    title=small_caps("no anime channels found"),
                    description=small_caps("generate links first using /start"),
                    input_message_content=InputTextMessageContent(
                        b(small_caps("no anime channels available yet.")),
                        parse_mode=ParseMode.HTML,
                    ),
                )],
                cache_time=10, is_personal=True,
            )
        except Exception:
            pass
        return

    # ── CHARACTER INFO ─────────────────────────────────────────────────────────
    if search_lower.startswith("character ") or search_lower.startswith("char "):
        char_q = re.sub(r"^(character|char)\s+", "", search, flags=re.IGNORECASE).strip()
        if char_q:
            try:
                from modules.anime import _al_sync, _CHAR_GQL
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, _al_sync, _CHAR_GQL, char_q)
                if data:
                    nm = data.get("name", {}) or {}
                    full = nm.get("full", char_q)
                    native = nm.get("native", "")
                    desc = re.sub(r"<[^>]+>", "", data.get("description", "") or "")
                    desc = (desc[:180].rsplit(" ", 1)[0] + "…") if len(desc) > 180 else desc
                    img = (data.get("image") or {}).get("large") or ""
                    site = data.get("siteUrl", "")
                    cap = f"<b>{e(full)}</b>"
                    if native:
                        cap += f" (<i>{e(native)}</i>)"
                    if desc:
                        cap += f"\n\n{e(desc)}"
                    if len(cap) > 900:
                        cap = cap[:896] + "…"

                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📋 AniList", url=site)]]) if site else None
                    if img:
                        results.append(InlineQueryResultPhoto(
                            id=f"char_{abs(hash(full)) % 1000000}",
                            photo_url=img, thumbnail_url=img, title=full,
                            description=(desc[:80] + "…") if len(desc) > 80 else desc,
                            caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb,
                        ))
                    else:
                        results.append(InlineQueryResultArticle(
                            id=f"char_art_{abs(hash(full)) % 1000000}", title=full,
                            description=(desc[:80] + "…") if len(desc) > 80 else desc,
                            input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
                            reply_markup=kb,
                        ))
            except Exception as exc:
                logger.debug(f"[inline] character: {exc}")
        try:
            await query_obj.answer(
                results or [InlineQueryResultArticle(
                    id="char_empty",
                    title=small_caps(f"character not found: {char_q}"),
                    description=small_caps("try a different name"),
                    input_message_content=InputTextMessageContent(
                        b(small_caps(f"character '{char_q}' not found.")),
                        parse_mode=ParseMode.HTML,
                    ),
                )],
                cache_time=20, is_personal=False,
            )
        except Exception:
            pass
        return

    # ── GROUP MANAGEMENT ───────────────────────────────────────────────────────
    if search_lower.startswith("manage"):
        manage_items = [
            ("🚫 Ban", "/ban @user reason", "Ban a user from the group"),
            ("🔇 Mute", "/mute @user", "Mute a user"),
            ("👢 Kick", "/kick @user", "Kick (remove, can rejoin)"),
            ("⚠️ Warn", "/warn @user reason", "Warn user (3 = auto ban)"),
            ("📌 Pin", "/pin (reply to msg)", "Pin a message"),
            ("📋 Rules", "/rules", "Show group rules"),
            ("🗑 Purge", "/purge (reply to msg)", "Delete messages in bulk"),
            ("👑 Promote", "/promote @user", "Promote user to admin"),
            ("📉 Demote", "/demote @user", "Demote admin to member"),
            ("🔗 Link", "/invitelink", "Get group invite link"),
        ]
        for lbl, cmd, desc in manage_items:
            results.append(InlineQueryResultArticle(
                id=f"mgmt_{abs(hash(lbl)) % 1000000}",
                title=small_caps(lbl), description=small_caps(desc),
                input_message_content=InputTextMessageContent(
                    b(small_caps(lbl)) + "\n" + code(cmd) + "\n" + bq(small_caps(desc)),
                    parse_mode=ParseMode.HTML,
                ),
            ))
        try:
            await query_obj.answer(results, cache_time=60, is_personal=False)
        except Exception:
            pass
        return

    # ── POSTER / DEFAULT — AniList search ─────────────────────────────────────
    anime_q = re.sub(r"^poster\s+", "", search, flags=re.IGNORECASE).strip() or search

    if anime_q:
        try:
            from modules.anime import inline_search_anime
            from core.config import BOT_USERNAME
            _inline_res = await inline_search_anime(anime_q, BOT_USERNAME)
            if _inline_res:
                try:
                    await query_obj.answer(_inline_res[:8], cache_time=10, is_personal=True)
                except Exception:
                    pass
                return
        except Exception as _ise:
            logger.debug(f"[inline] inline_search_anime: {_ise}")

        # Fallback: single AniList result
        try:
            from modules.anime import _al_sync, _ANIME_GQL, _resolve_query
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, _al_sync, _ANIME_GQL, _resolve_query(anime_q)
            )
            if data:
                t_d = data.get("title", {}) or {}
                title = t_d.get("english") or t_d.get("romaji") or anime_q
                score = data.get("averageScore", "?")
                status = (data.get("status") or "").replace("_", " ").title()
                genres = ", ".join((data.get("genres") or [])[:3])
                cover = (data.get("coverImage") or {}).get("large") or ""
                site = data.get("siteUrl", "")

                cap = f"<b>{e(title)}</b>"
                if genres:
                    cap += f"\n» <b>{small_caps('Genre')}:</b> {e(genres)}"
                if str(score) not in ("?", "0", "None"):
                    cap += f"\n» <b>{small_caps('Rating')}:</b> <code>{score}/100</code>"
                if status:
                    cap += f"\n» <b>{small_caps('Status')}:</b> {e(status)}"

                kb = None
                if site:
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton(small_caps(" Info"), url=site),
                    ]])

                if cover:
                    results.append(InlineQueryResultPhoto(
                        id=f"anime_poster_{data.get('id', abs(hash(title)) % 1000000)}",
                        photo_url=cover, thumbnail_url=cover,
                        title=title, description=f"{score}/100 • {status} • {genres}",
                        caption=cap, parse_mode=ParseMode.HTML, reply_markup=kb,
                    ))
                else:
                    results.append(InlineQueryResultArticle(
                        id=f"anime_art_{data.get('id', abs(hash(title)) % 1000000)}",
                        title=f"🎌 {title}",
                        description=f"{score}/100 • {status} • {genres}",
                        input_message_content=InputTextMessageContent(cap, parse_mode=ParseMode.HTML),
                        reply_markup=kb,
                    ))
        except Exception as exc:
            logger.debug(f"[inline] poster: {exc}")

    try:
        await query_obj.answer(
            results[:10] or [InlineQueryResultArticle(
                id="not_found",
                title=small_caps(f"not found: {anime_q[:30]}"),
                description=small_caps("try a different search term"),
                input_message_content=InputTextMessageContent(
                    b(small_caps(f"'{anime_q}' not found on AniList.")),
                    parse_mode=ParseMode.HTML,
                ),
            )],
            cache_time=15, is_personal=False,
        )
    except Exception as exc:
        logger.debug(f"[inline] answer: {exc}")
