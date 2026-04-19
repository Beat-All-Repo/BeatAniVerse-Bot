"""
handlers/inline_handler.py
==========================
Inline query handler — shows ONLY DB-registered anime channels.
On result click → fast expirable invite link (with loading animation while generating).
"""
import re
import asyncio
import time

from telegram import (
    Update, InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultCachedPhoto,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL, LINK_EXPIRY_MINUTES
from core.logging_setup import logger
from core.text_utils import b, bq, code, e, small_caps
from core.filters_system import force_sub_required, get_unsubscribed_channels

# Pre-built loading animation callback prefix
_LOADING_CB = "inv_loading:"
_READY_CB   = "inv_ready:"


def _norm(t: str) -> str:
    """Normalize Unicode-styled text for comparison."""
    try:
        from core.chatbot_engine import normalize_text
        return normalize_text(t)
    except Exception:
        return t.lower()


def _get_db_anime(query: str):
    """
    Search generated_links + anime_channel_links for titles matching query.
    Returns list of (title, channel_id, link_id) — DB titles only.
    """
    try:
        from database_dual import get_all_links, get_all_anime_channel_links
        all_links = get_all_links(limit=2000, offset=0) or []
        q_norm = _norm(query)
        results = []
        seen = set()

        for row in all_links:
            link_id = row[0]
            ch_id   = row[1]
            title   = (row[2] or "").strip()
            if not title or _norm(title) in seen:
                continue
            if len(title) < 2:
                continue
            t_norm = _norm(title)
            if not query or q_norm in t_norm or t_norm.startswith(q_norm):
                seen.add(t_norm)
                results.append((title, ch_id, link_id))
            if len(results) >= 50:
                break

        # Also search anime_channel_links table
        try:
            acl = get_all_anime_channel_links() or []
            for arow in acl:
                an_title = (arow[1] or "").strip()
                if not an_title or _norm(an_title) in seen:
                    continue
                t_norm = _norm(an_title)
                if not query or q_norm in t_norm or t_norm.startswith(q_norm):
                    seen.add(t_norm)
                    results.append((an_title, arow[2], arow[4]))
                if len(results) >= 50:
                    break
        except Exception:
            pass

        return results
    except Exception as exc:
        logger.debug(f"[inline] _get_db_anime: {exc}")
        return []


@force_sub_required
async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query_obj = update.inline_query
    if not query_obj:
        return

    uid = query_obj.from_user.id
    search = (query_obj.query or "").strip()
    search_lower = search.lower()

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

    # ── EMPTY QUERY — show DB anime list (first 8 alphabetically) ─────────────
    if not search:
        db_items = _get_db_anime("")[:8]
        if db_items:
            for title, ch_id, link_id in db_items:
                results.append(InlineQueryResultArticle(
                    id=f"db_{link_id or abs(hash(title)) % 999999}",
                    title=f"🎌 {title}",
                    description=small_caps("tap to get instant join link"),
                    input_message_content=InputTextMessageContent(
                        b(small_caps("generating your link")) + " ⏳",
                        parse_mode=ParseMode.HTML,
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "🔗 " + small_caps("get link"),
                            callback_data=f"{_LOADING_CB}{ch_id}:{link_id or ''}",
                        )
                    ]]),
                ))
        else:
            results.append(InlineQueryResultArticle(
                id="db_empty",
                title=small_caps("no anime channels yet"),
                description=small_caps("add channels via /addchannel"),
                input_message_content=InputTextMessageContent(
                    b(small_caps("no anime channels in database yet.")),
                    parse_mode=ParseMode.HTML,
                ),
            ))
        try:
            await query_obj.answer(results, cache_time=5, is_personal=True)
        except Exception:
            pass
        return

    # ── WATCH / DEFAULT — search DB-only ──────────────────────────────────────
    anime_q = re.sub(r"^(watch|poster)\s*", "", search, flags=re.IGNORECASE).strip() or search
    db_items = _get_db_anime(_norm(anime_q))

    if db_items:
        for title, ch_id, link_id in db_items[:10]:
            results.append(InlineQueryResultArticle(
                id=f"db_{link_id or abs(hash(title)) % 999999}",
                title=f"🎌 {title}",
                description=small_caps("tap → instant expirable join link"),
                input_message_content=InputTextMessageContent(
                    b(e(title)) + "\n\n" + small_caps("generating your link") + " ⏳",
                    parse_mode=ParseMode.HTML,
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "⏳ " + small_caps("generating link..."),
                        callback_data=f"{_LOADING_CB}{ch_id}:{link_id or ''}",
                    )
                ]]),
            ))
    else:
        results.append(InlineQueryResultArticle(
            id="not_found",
            title=small_caps(f"not in database: {anime_q[:30]}"),
            description=small_caps("only db-registered anime are shown"),
            input_message_content=InputTextMessageContent(
                b(small_caps(f"'{anime_q}' is not in our anime database yet.")) + "\n"
                + bq(small_caps("ask admin to add it!")),
                parse_mode=ParseMode.HTML,
            ),
        ))

    try:
        await query_obj.answer(results[:10], cache_time=5, is_personal=True)
    except Exception as exc:
        logger.debug(f"[inline] answer: {exc}")


def get_animation_enabled() -> bool:
    """Check if loading animation is enabled (default: True)."""
    try:
        from database_dual import get_setting
        return get_setting("inline_anim_enabled", "true") != "false"
    except Exception:
        return True


def set_animation_enabled(enabled: bool) -> None:
    try:
        from database_dual import set_setting
        set_setting("inline_anim_enabled", "true" if enabled else "false")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  CALLBACK: Fast invite link with optional loading animation + original text
# ═══════════════════════════════════════════════════════════════════════════════

async def handle_inv_loading_callback(update, context):
    """
    Called when user taps inline result button.
    • If animation ON: shows ⏳ → ⏳ . → ⏳ .. → ⏳ ... while link generates
    • Link creation runs simultaneously so no speed penalty
    • Final button shows Join Now with real expirable link
    """
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception:
        pass

    cb = query.data or ""

    # ── Animation ON/OFF toggle (from admin panel) ───────────────────────────
    if cb == "inline_anim_toggle":
        cur = get_animation_enabled()
        set_animation_enabled(not cur)
        status = "✅ ON" if not cur else "🔕 OFF"
        try:
            await query.answer(f"Loading animation: {status}", show_alert=True)
        except Exception:
            pass
        return

    # Format: inv_loading:{channel_id}:{optional_link_id}
    payload = cb[len(_LOADING_CB):]
    parts = payload.split(":", 1)
    ch_id_raw = parts[0]

    try:
        ch_id = int(ch_id_raw)
    except ValueError:
        ch_id = ch_id_raw

    try:
        from filter_poster import get_link_expiry_minutes
        chat_id = query.message.chat_id if query.message else 0
        exp_min = get_link_expiry_minutes(chat_id)
    except Exception:
        exp_min = int(LINK_EXPIRY_MINUTES)

    link_holder = {"url": None}

    async def _make_link():
        try:
            expire_ts = int(time.time()) + (exp_min * 60)
            inv = await context.bot.create_chat_invite_link(
                chat_id=ch_id,
                expire_date=expire_ts,
                member_limit=1,
                creates_join_request=False,
                name=f"Inline-{int(time.time())}",
            )
            link_holder["url"] = inv.invite_link
        except Exception as exc:
            logger.debug(f"[inline] invite link error: {exc}")
            link_holder["url"] = PUBLIC_ANIME_CHANNEL_URL

    if get_animation_enabled():
        # Animation runs simultaneously with link generation — zero speed cost
        loading_frames = [".", " ..", " ...", " ..", " .."]
        stop_anim = asyncio.Event()

        async def _animate():
            i = 0
            while not stop_anim.is_set():
                frame = loading_frames[i % len(loading_frames)]
                try:
                    await query.edit_message_reply_markup(
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(frame, callback_data="noop")
                        ]])
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.35)
                i += 1

        anim_task = asyncio.create_task(_animate())
        await _make_link()           # Link creation happens here
        stop_anim.set()
        anim_task.cancel()
        try:
            await anim_task
        except asyncio.CancelledError:
            pass
    else:
        await _make_link()

    join_url = link_holder["url"] or PUBLIC_ANIME_CHANNEL_URL
    join_text = small_caps("ᴊᴏɪɴ ɴᴏᴡ ✅")

    # Update the inline button to show real link
    sent_msg = None
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(join_text, url=join_url)
            ]])
        )
        sent_msg = query.message  # track for auto-delete
    except Exception:
        try:
            sent_msg = await query.message.reply_text(
                "<b>ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ!</b>\n"
                "<i>ʟɪɴᴋ ᴇxᴘɪʀᴇs ɪɴ 5 ᴍɪɴᴜᴛᴇs.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(join_text, url=join_url)
                ]]),
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    # Auto-delete the message after 5 minutes
    if sent_msg:
        async def _del_after():
            await asyncio.sleep(300)
            try:
                await sent_msg.delete()
            except Exception:
                pass
        asyncio.create_task(_del_after())

