"""
handlers/admin_panel.py
=======================
Admin panel UI: paginated 5-page grid, stats panel,
category settings menu, feature flags panel.
"""
import time
import asyncio
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery,
)
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, BOT_USERNAME, BOT_NAME, I_AM_CLONE,
    LINK_EXPIRY_MINUTES, SETTINGS_IMAGE_URL,
)
from core.text_utils import b, bq, e, code, small_caps, format_number
from core.helpers import (
    safe_send_message, safe_send_photo, safe_edit_text,
    safe_reply, get_uptime, get_system_stats_text,
)
from core.buttons import (
    _btn, _back_btn, _close_btn, bold_button,
    _grid3, _grid4, _back_kb,
)
from core.cache import panel_cache_get, panel_cache_set
from core.panel_store import _deliver_panel, safe_edit_panel
from core.panel_image import get_panel_pic, get_panel_pic_async, _PANEL_IMAGE_AVAILABLE
from core.state_machine import user_states
from core.filters_system import force_sub_required
from core.logging_setup import logger


# ── Pre-built cached panel pages ──────────────────────────────────────────────
_PANEL_PAGES: dict = {}
_PANEL_PAGES_TS: float = 0.0
_PANEL_PAGES_TTL: float = 60.0


def _build_panel_pages(maint: bool, clone_red: bool, clean_gc: bool):
    maint_icon = "🔴" if maint else "🟢"
    gc_icon = "✔️" if clean_gc else "❗"
    cl_icon = "✔️" if clone_red else "🔴"

    status_line = (
        f"{maint_icon} <b>{small_caps('Maintenance')}:</b> {small_caps('ON' if maint else 'OFF')}  "
        f"{gc_icon} <b>{small_caps('Clean GC')}:</b> {small_caps('ON' if clean_gc else 'OFF')}  "
        f"{cl_icon} <b>{small_caps('Clone Redirect')}:</b> {small_caps('ON' if clone_red else 'OFF')}"
    )

    def _row4(btns):
        rows = []
        for i in range(0, len(btns), 4):
            rows.append(btns[i:i + 4])
        return rows

    TOTAL = 5

    def _nav(cur):
        row = []
        if cur > 0:
            row.append(InlineKeyboardButton("◀", callback_data=f"adm_page_{cur-1}"))
        row.append(InlineKeyboardButton(f"· {cur+1}/{TOTAL} ·", callback_data="noop"))
        if cur < TOTAL - 1:
            row.append(InlineKeyboardButton("▶", callback_data=f"adm_page_{cur+1}"))
        row.append(_close_btn())
        return row

    def _header(title):
        from core.text_utils import math_bold
        return InlineKeyboardButton(math_bold(title), callback_data="noop")

    def _page(num, label, btns):
        rows = [[_header(label)]] + _row4(btns)
        rows.append(_nav(num))
        return InlineKeyboardMarkup(rows)

    main_btns = [
        _btn("STATS", "admin_stats"), _btn("BROADCAST", "admin_broadcast_start"),
        _btn("USERS", "user_management"), _btn("CHANNELS", "manage_force_sub"),
        _btn("LINKS", "generate_links"), _btn("CLONES", "manage_clones"),
        _btn("SETTINGS", "admin_settings"), _btn("CATEGORY", "admin_category_settings"),
        _btn("UPLOAD", "upload_menu"), _btn("FILTERS", "admin_filter_settings"),
        _btn("POSTER DB", "admin_filter_poster"), _btn("FLAGS", "admin_feature_flags"),
    ]
    tools_btns = [
        _btn("AUTO FWD", "admin_autoforward"), _btn("MANGA", "admin_autoupdate"),
        _btn("STYLE", "admin_text_style"), _btn("SYSTEM", "admin_sysstats"),
        _btn("LOGS", "admin_logs"), _btn("RESTART", "admin_restart_confirm"),
        _btn("IMP USERS", "admin_import_users"), _btn("IMP LINKS", "admin_import_links"),
        _btn("EXP USERS", "admin_export_users_quick"), _btn("DB CLEAN", "dbcleanup_confirm"),
        _btn("PANELS", "panel_img_add_urls"), _btn("ENV VARS", "admin_env_panel"),
    ]
    feat_btns = [
        _btn("COUPLE", "feat_couple"), _btn("SLAP", "feat_slap"),
        _btn("HUG", "feat_hug"), _btn("KISS", "feat_kiss"),
        _btn("PAT", "feat_pat"), _btn("INLINE", "feat_inline_search"),
        _btn("REACTIONS", "feat_reactions"), _btn("CHATBOT", "feat_chatbot"),
        _btn("T/DARE", "feat_truth_dare"), _btn("NOTES", "feat_notes"),
        _btn("WARNS", "feat_warns"), _btn("MUTE", "feat_muting"),
    ]
    poster_btns = [
        _btn("ANI", "poster_cmd_ani"), _btn("NET", "poster_cmd_net"),
        _btn("CRUN", "poster_cmd_crun"), _btn("DARK", "poster_cmd_dark"),
        _btn("LIGHT", "poster_cmd_light"), _btn("MOD", "poster_cmd_mod"),
        _btn("BANS", "feat_bans"), _btn("RULES", "feat_rules"),
        _btn("AIRING", "feat_airing"), _btn("CHAR", "feat_character"),
        _btn("ANIME", "feat_anime_info"), _btn("AFK", "feat_afk"),
    ]
    all_mods = [
        _btn("ADMIN", "mod_admin"),       _btn("ANTIFLOOD", "mod_antiflood"),
        _btn("APPROVE", "mod_approve"),   _btn("BLACKLIST", "mod_blacklist"),
        _btn("BL STICKER", "mod_blsticker"), _btn("CHATBOT", "mod_chatbot"),
        _btn("CLEANER", "mod_cleaner"),   _btn("CONNECTION", "mod_connection"),
        _btn("CURRENCY", "mod_currency"), _btn("FILTERS", "mod_custfilters"),
        _btn("GBAN", "mod_globalbans"),   _btn("IMDB", "mod_imdb"),
        _btn("LOCKS", "mod_locks"),       _btn("LOGCHAN", "mod_logchannel"),
        _btn("PING", "mod_ping"),         _btn("PURGE", "mod_purge"),
        _btn("REPORTING", "mod_reporting"), _btn("SED", "mod_sed"),
        _btn("SHELL", "mod_shell"),       _btn("SPEEDTEST", "mod_speedtest"),
        _btn("STICKERS", "mod_stickers"), _btn("TAGALL", "mod_tagall"),
        _btn("TRANSLATE", "mod_translator"), _btn("TRUTH/DARE", "mod_truthdare"),
        _btn("UD", "mod_ud"),             _btn("WALLPAPER", "mod_wallpaper"),
        _btn("WIKI", "mod_wiki"),         _btn("WRITE", "mod_writetool"),
        _btn("ANIMEQUOTE", "mod_animequotes"), _btn("GETTIME", "mod_gettime"),
        _btn("BAD WORDS", "mod_badwords"),
    ]

    return {
        0: _page(0, "MAIN",     main_btns),
        1: _page(1, "TOOLS",    tools_btns),
        2: _page(2, "FEATURES", feat_btns),
        3: _page(3, "POSTER",   poster_btns),
        4: _page(4, "MODULES",  all_mods),
    }, status_line


async def send_admin_menu(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    query: Optional[CallbackQuery] = None,
    page: int = 0,
) -> None:
    """Send/update the paginated admin panel."""
    global _PANEL_PAGES, _PANEL_PAGES_TS

    if query:
        _dup_key = f"adm_dup_{chat_id}_{getattr(query.message, 'message_id', 0)}"
        _ts_now = time.monotonic()
        _last_ts = panel_cache_get(_dup_key)
        if _last_ts and (_ts_now - _last_ts) < 0.8:
            try:
                await query.answer()
            except Exception:
                pass
            return
        panel_cache_set(_dup_key, _ts_now)

    from handlers.start import delete_bot_prompt
    await delete_bot_prompt(context, chat_id)
    user_states.pop(chat_id, None)

    now = time.monotonic()
    if not _PANEL_PAGES or (now - _PANEL_PAGES_TS) > _PANEL_PAGES_TTL:
        try:
            from database_dual import get_setting
            maint = get_setting("maintenance_mode", "false") == "true"
            clone_red = get_setting("clone_redirect_enabled", "false") == "true"
            clean_gc = get_setting("clean_gc_enabled", "true") == "true"
        except Exception:
            maint = clone_red = False
            clean_gc = True
        _PANEL_PAGES, _status_line = _build_panel_pages(maint, clone_red, clean_gc)
        _PANEL_PAGES["_status"] = _status_line
        _PANEL_PAGES_TS = now

    status_line = _PANEL_PAGES.get("_status", "")
    markup = _PANEL_PAGES.get(page, _PANEL_PAGES.get(0))

    text = (
        b(small_caps("admin panel")) + "\n\n"
        + status_line + "\n\n"
        + bq(
            f"<b>{small_caps('Bot')}:</b> @{e(BOT_USERNAME)}\n"
            f"<b>{small_caps('Mode')}:</b> {small_caps('Clone' if I_AM_CLONE else 'Main')}\n"
            f"<b>{small_caps('Name')}:</b> {e(BOT_NAME)}"
        )
    )

    await _deliver_panel(
        context.bot, chat_id, "admin",
        caption=text, reply_markup=markup, query=query,
    )


async def send_stats_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Send bot statistics panel."""
    try:
        from database_dual import (
            get_user_count, get_all_force_sub_channels,
            get_links_count, get_all_clone_bots,
            get_blocked_users_count, get_setting,
        )
        user_count = get_user_count()
        channel_count = len(get_all_force_sub_channels())
        link_count = get_links_count()
        clones = get_all_clone_bots(active_only=True)
        blocked = get_blocked_users_count()
        maint = "🔴 ON" if get_setting("maintenance_mode", "false") == "true" else "🟢 OFF"

        text = (
            b(" Bot Statistics") + "\n\n"
            f"<b> Total Users:</b> {code(format_number(user_count))}\n"
            f"<b> Force-Sub Channels:</b> {code(str(channel_count))}\n"
            f"<b> Generated Links:</b> {code(format_number(link_count))}\n"
            f"<b> Active Clone Bots:</b> {code(str(len(clones)))}\n"
            f"<b> Blocked Users:</b> {code(str(blocked))}\n"
            f"<b> Maintenance:</b> {maint}\n"
            f"<b> Link Expiry:</b> {code(str(LINK_EXPIRY_MINUTES) + ' min')}\n"
            f"<b> Uptime:</b> {code(get_uptime())}"
        )
    except Exception as exc:
        text = b("❌ Error loading stats: ") + code(e(str(exc)[:200]))

    grid = [
        _btn("♻️ REFRESH",      "admin_stats"),
        _btn("BROADCAST STATS", "broadcast_stats_panel"),
        _btn("SYSTEM STATS",    "admin_sysstats"),
        _btn("USERS",           "user_management"),
        _btn("LINK STATS",      "fsub_link_stats"),
        _btn("EXPORT USERS",    "admin_export_users_quick"),
    ]
    rows = _grid3(grid)
    rows.append([_back_btn("admin_back"), _close_btn()])
    markup = InlineKeyboardMarkup(rows)

    await safe_edit_panel(
        context.bot, query, chat_id,
        photo=get_panel_pic("stats"), caption=text, reply_markup=markup,
        panel_type="stats",
    )


async def show_category_settings_menu(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    category: str,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Show full settings menu for a category."""
    from handlers.post_gen import get_category_settings
    settings = get_category_settings(category)
    btns_count = len(settings.get("buttons") or [])
    wm = settings.get("watermark_text") or "None"
    logo = "✅ Set" if settings.get("logo_file_id") else "❌ Not set"

    try:
        from text_style import get_style
        style = get_style()
    except Exception:
        style = "normal"

    text = (
        f"{b(category.upper() + ' SETTINGS')}\n\n"
        + bq(
            f"<b>Template:</b> {code(settings['template_name'])}\n"
            f"<b>Font Style:</b> {code(settings['font_style'])}\n"
            f"<b>Buttons:</b> {code(str(btns_count))} configured\n"
            f"<b>Watermark:</b> {code(e(str(wm)[:30]))}\n"
            f"<b>Logo:</b> {logo}\n"
            f"<b>Caption:</b> {'✔️ Custom' if settings.get('caption_template') else 'Default'}\n"
            f"<b>Branding:</b> {'✔️ Set' if settings.get('branding') else 'None'}\n"
            f"<b>Text Style:</b> {code(style)}"
        )
    )
    grid = [
        _btn("CAPTION",      f"cat_caption_{category}"),
        _btn("BUTTONS",      f"cat_buttons_{category}"),
        _btn("TEMPLATE",     f"cat_thumbnail_{category}"),
        _btn("BRANDING",     f"cat_branding_{category}"),
        _btn("FONT STYLE",   f"cat_font_{category}"),
        _btn("BTN STYLE",    f"cat_btn_style_{category}"),
        _btn("WATERMARK",    f"cat_watermark_{category}"),
        _btn("LOGO",         f"cat_logo_{category}"),
        _btn("AUTO UPDATE",  "admin_autoupdate"),
        _btn("PREVIEW",      f"cat_preview_{category}"),
    ]
    keyboard = _grid3(grid)
    keyboard.append([_back_btn("admin_category_settings"), _close_btn()])
    markup = InlineKeyboardMarkup(keyboard)

    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    img_url = None
    if _PANEL_IMAGE_AVAILABLE:
        try:
            img_url = await get_panel_pic_async("categories")
        except Exception:
            pass
    if img_url:
        sent = await safe_send_photo(context.bot, chat_id, img_url, caption=text, reply_markup=markup)
        if sent:
            return
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


async def send_feature_flags_panel(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    query: Optional[CallbackQuery] = None,
) -> None:
    """Show feature flags panel."""
    try:
        from database_dual import get_setting
    except ImportError:
        return

    flags = [
        ("maintenance_mode",       "false", " Maintenance Mode"),
        ("clone_redirect_enabled", "false", " Clone Redirect"),
        ("error_dms_enabled",      "1",     " Error DMs to Admin"),
        ("force_sub_enabled",      "true",  " Force Subscription"),
        ("auto_delete_messages",   "true",  " Auto-Delete Messages"),
        ("watermarks_enabled",     "true",  " Watermarks"),
        ("inline_search_enabled",  "true",  " Inline Search"),
        ("group_commands_enabled", "true",  "👥 Group Commands"),
    ]

    text = b("🚩 Feature Flags") + "\n\n"
    keyboard = []
    for key, default, label in flags:
        val = get_setting(key, default)
        is_on = val in ("1", "true", "yes")
        status = "✅ ON" if is_on else "❌ OFF"
        text += f"<b>{label}:</b> {status}\n"
        toggle_val = "false" if is_on else "true"
        keyboard.append([bold_button(
            f"{'Disable' if is_on else 'Enable'} {label.split(' ', 1)[-1]}",
            callback_data=f"flag_toggle_{key}_{toggle_val}"
        )])
    keyboard.append([_back_btn("admin_back")])
    markup = InlineKeyboardMarkup(keyboard)

    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    img_url = None
    if _PANEL_IMAGE_AVAILABLE:
        try:
            img_url = await get_panel_pic_async("flags")
        except Exception:
            pass
    if img_url:
        try:
            await context.bot.send_photo(chat_id, img_url, caption=text,
                                         parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ── Broadcast execution ───────────────────────────────────────────────────────

async def _do_broadcast(
    context,
    admin_chat_id: int,
    from_chat_id: int,
    message_id: int,
    mode: str,
) -> None:
    """Execute a broadcast to all registered users."""
    import asyncio
    from database_dual import get_all_users, db_manager
    from core.config import ADMIN_ID, OWNER_ID, RATE_LIMIT_DELAY
    from core.helpers import safe_send_message, safe_delete
    from core.text_utils import b, bq, code, format_number
    from core.state_machine import BroadcastMode
    from telegram.error import Forbidden, RetryAfter

    users = get_all_users(limit=None, offset=0)
    total = len(users)
    sent = fail = blocked = deleted_count = 0
    deleted_uids: list = []

    try:
        with db_manager.get_cursor() as cur:
            cur.execute("""
                INSERT INTO broadcast_history (admin_id, mode, total_users, message_text)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (ADMIN_ID, mode, total, f"copy:{from_chat_id}:{message_id}"))
            bc_id = cur.fetchone()[0]
    except Exception:
        bc_id = None

    progress_msg = await safe_send_message(
        context.bot, admin_chat_id,
        b(f"📣 Broadcasting to {format_number(total)} users…"),
    )

    for i, user_row in enumerate(users):
        uid = user_row[0]
        if uid in (ADMIN_ID, OWNER_ID):
            continue
        try:
            if mode == BroadcastMode.AUTO_DELETE:
                msg = await context.bot.copy_message(uid, from_chat_id, message_id)
                context.job_queue.run_once(
                    lambda ctx, u=uid, m=msg.message_id: safe_delete(ctx.bot, u, m),
                    when=86400,
                )
            elif mode in (BroadcastMode.PIN, BroadcastMode.DELETE_PIN):
                msg = await context.bot.copy_message(uid, from_chat_id, message_id)
                try:
                    await context.bot.pin_chat_message(uid, msg.message_id, disable_notification=True)
                    if mode == BroadcastMode.DELETE_PIN:
                        await safe_delete(context.bot, uid, msg.message_id)
                except Exception:
                    pass
            elif mode == BroadcastMode.SILENT:
                await context.bot.copy_message(uid, from_chat_id, message_id, disable_notification=True)
            else:
                await context.bot.copy_message(uid, from_chat_id, message_id)
            sent += 1
        except Forbidden as err:
            fail += 1
            err_s = str(err).lower()
            if "blocked" in err_s:
                blocked += 1
            elif "deactivated" in err_s or "deleted" in err_s:
                deleted_count += 1
                deleted_uids.append(uid)
        except RetryAfter as err:
            await asyncio.sleep(err.retry_after + 1)
            try:
                await context.bot.copy_message(uid, from_chat_id, message_id)
                sent += 1
            except Exception:
                fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(RATE_LIMIT_DELAY)

        if progress_msg and (i + 1) % 500 == 0:
            try:
                await progress_msg.edit_text(
                    b(f"📣 Broadcasting… {i+1}/{total}"),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    if bc_id:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    UPDATE broadcast_history
                    SET completed_at = NOW(), success = %s, blocked = %s,
                        deleted = %s, failed = %s
                    WHERE id = %s
                """, (sent, blocked, deleted_count, fail, bc_id))
        except Exception:
            pass

    purged = 0
    if deleted_uids:
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = ANY(%s)", (deleted_uids,))
                purged = cur.rowcount
        except Exception:
            pass

    result = (
        b(" Broadcast Complete!") + "\n\n"
        + bq(
            f"<b> Sent:</b> {code(format_number(sent))}\n"
            f"<b> Blocked:</b> {code(format_number(blocked))}\n"
            f"<b> Deleted accounts:</b> {code(format_number(deleted_count))}\n"
            f"<b> Purged from DB:</b> {code(format_number(purged))}\n"
            f"<b> Total users:</b> {code(format_number(total))}"
        )
    )

    if progress_msg:
        try:
            await progress_msg.edit_text(result, parse_mode="HTML")
        except Exception:
            await safe_send_message(context.bot, admin_chat_id, result)
    else:
        await safe_send_message(context.bot, admin_chat_id, result)


# ── User management panel ─────────────────────────────────────────────────────

async def show_user_management_panel(update, context, query=None) -> None:
    """Show user management panel with stats and action buttons."""
    from database_dual import get_user_count, get_blocked_users_count
    from core.text_utils import b, bq, code
    from core.buttons import _btn, _grid3, _back_btn, _close_btn
    from core.helpers import safe_send_message, safe_send_photo
    from core.panel_image import get_panel_pic_async
    from telegram import InlineKeyboardMarkup
    from telegram.constants import ParseMode

    total = get_user_count()
    blocked = get_blocked_users_count()

    text = (
        b("USER MANAGEMENT") + "\n\n"
        + bq(
            f"<b>Total:</b> {total:,}\n"
            f"<b>Blocked:</b> {blocked}\n"
            f"<b>Active:</b> {total - blocked:,}"
        )
    )
    grid = [
        _btn("LIST USERS",   "user_list_page_0"),
        _btn("SEARCH",       "user_search"),
        _btn("BAN USER",     "user_ban_input"),
        _btn("UNBAN USER",   "user_unban_input"),
        _btn("DELETE USER",  "user_delete_input"),
        _btn("EXPORT CSV",   "admin_export_users_quick"),
        _btn("BLOCKED LIST", "user_blocked_list"),
        _btn("BROADCAST",    "admin_broadcast_start"),
        _btn("STATS",        "admin_stats"),
    ]
    rows = _grid3(grid)
    rows.append([_back_btn("admin_back"), _close_btn()])

    chat_id = query.message.chat_id if query else update.effective_chat.id
    try:
        if query:
            await query.delete_message()
    except Exception:
        pass

    img_url = await get_panel_pic_async("users")
    if img_url:
        sent = await safe_send_photo(
            context.bot, chat_id, img_url, caption=text,
            reply_markup=InlineKeyboardMarkup(rows)
        )
        if sent:
            return
    await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows))


# ── Settings Panel ─────────────────────────────────────────────────────────────

async def show_settings_panel(update, context, query=None) -> None:
    """Show main settings panel with all configurable options."""
    from telegram import InlineKeyboardMarkup
    from core.buttons import _btn, _grid3, _back_btn, _close_btn
    from core.helpers import safe_send_message, safe_send_photo
    from core.panel_image import get_panel_pic_async
    from database_dual import get_setting

    chat_id = query.message.chat_id if query else (
        update.effective_chat.id if update else 0
    )
    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    maint = get_setting("maintenance_mode", "false") == "true"
    clone_red = get_setting("clone_redirect_enabled", "false") == "true"
    clean_gc = get_setting("clean_gc_enabled", "true") == "true"
    main_channel = get_setting("main_channel_id", "") or "Not set"

    text = (
        b(small_caps("⚙️ settings")) + "\n\n"
        + bq(
            f"<b>{small_caps('Maintenance')}:</b> {'🔴 ON' if maint else '🟢 OFF'}\n"
            f"<b>{small_caps('Clone Redirect')}:</b> {'✅ ON' if clone_red else '❌ OFF'}\n"
            f"<b>{small_caps('Clean GC')}:</b> {'✅ ON' if clean_gc else '❌ OFF'}\n"
            f"<b>{small_caps('Main Channel')}:</b> <code>{e(str(main_channel))}</code>"
        )
    )
    # Load auto-delete config
    try:
        from database_dual import get_setting
        auto_del_on  = get_setting("auto_delete_messages", "true") == "true"
        dm_delay_val = get_setting("auto_delete_dm_delay", "120")
        gc_delay_val = get_setting("auto_delete_gc_delay", "60")
    except Exception:
        auto_del_on  = True
        dm_delay_val = "120"
        gc_delay_val = "60"

    text += (
        "\n\n" + bq(
            f"<b>{small_caps('Auto-Delete')}:</b> {'✅ ON' if auto_del_on else '❌ OFF'}\n"
            f"<b>{small_caps('DM Delay')}:</b> <code>{e(dm_delay_val)}s</code>\n"
            f"<b>{small_caps('GC Delay')}:</b> <code>{e(gc_delay_val)}s</code>"
        )
    )
    grid = [
        _btn("MAINTENANCE", "toggle_maintenance"),
        _btn("CLONE REDIRECT", "toggle_clone_redirect"),
        _btn("CLEAN GC", "toggle_clean_gc"),
        _btn("SET MAIN CHANNEL", "admin_set_main_channel"),
        _btn("LINK EXPIRY", "admin_set_link_expiry"),
        _btn("AUTO DELETE", "toggle_auto_delete"),
        _btn("DM DEL DELAY", "set_dm_del_delay"),
        _btn("GC DEL DELAY", "set_gc_del_delay"),
        _btn("CATEGORY SETTINGS", "admin_category_settings"),
        _btn("FEATURE FLAGS", "admin_feature_flags"),
        _btn("ENV VARS", "admin_env_panel"),
        _btn("TEXT STYLE", "admin_text_style"),
    ]
    rows = _grid3(grid)
    rows.append([_back_btn("admin_back"), _close_btn()])
    markup = InlineKeyboardMarkup(rows)

    img = None
    try:
        img = await get_panel_pic_async("settings")
    except Exception:
        pass

    if img:
        sent = await safe_send_photo(context.bot, chat_id, img, caption=text, reply_markup=markup)
        if sent:
            return
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ── Channels Panel (Force-Sub) ────────────────────────────────────────────────

async def _show_channels_panel(update, context, query=None) -> None:
    """Show force-sub channels management panel."""
    from telegram import InlineKeyboardMarkup
    from core.buttons import _btn, _grid3, _back_btn, _close_btn
    from core.helpers import safe_send_message, safe_send_photo
    from core.panel_image import get_panel_pic_async
    from database_dual import get_all_force_sub_channels

    chat_id = query.message.chat_id if query else (
        update.effective_chat.id if update else 0
    )
    if query:
        try:
            await query.delete_message()
        except Exception:
            pass

    channels = get_all_force_sub_channels()

    text = b(small_caps("📢 force-sub channels")) + "\n\n"
    if channels:
        for ch in channels[:10]:
            cid = ch.get("channel_id") or ch[0] if isinstance(ch, (list, tuple)) else ch
            cname = ch.get("channel_name") or ch[1] if isinstance(ch, (list, tuple)) else str(cid)
            text += f"• <code>{e(str(cid))}</code> — <b>{e(str(cname))}</b>\n"
    else:
        text += bq(small_caps("no force-sub channels configured"))

    grid = [
        _btn("➕ ADD CHANNEL", "fsub_add"),
        _btn("➖ REMOVE", "fsub_remove"),
        _btn("✅ VERIFY ALL", "fsub_verify"),
        _btn("📊 STATS", "fsub_link_stats"),
        _btn("🔗 GENERATE LINK", "generate_links"),
    ]
    rows = _grid3(grid)
    rows.append([_back_btn("admin_back"), _close_btn()])
    markup = InlineKeyboardMarkup(rows)

    img = None
    try:
        img = await get_panel_pic_async("channels")
    except Exception:
        pass

    if img:
        sent = await safe_send_photo(context.bot, chat_id, img, caption=text, reply_markup=markup)
        if sent:
            return
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ── Env Panel ─────────────────────────────────────────────────────────────────

async def show_env_panel(context, chat_id: int) -> None:
    """Show environment variables management panel."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from core.buttons import _btn, _back_btn, _close_btn
    from core.helpers import safe_send_message
    from database_dual import get_setting

    ENV_KEYS = [
        ("BOT_NAME",                "Bot Name"),
        ("PUBLIC_ANIME_CHANNEL_URL","Anime Channel URL"),
        ("REQUEST_CHANNEL_URL",     "Request Channel URL"),
        ("ADMIN_CONTACT_USERNAME",  "Admin Username"),
        ("JOIN_BTN_TEXT",           "Join Button Text"),
        ("HERE_IS_LINK_TEXT",       "Link Message Text"),
        ("LINK_EXPIRY_MINUTES",     "Link Expiry (min)"),
        ("WELCOME_IMAGE_URL",       "Welcome Image URL"),
        ("TRANSITION_STICKER",      "Transition Sticker ID"),
        ("MAIN_CHANNEL_ID",         "Main Channel ID"),
    ]

    text = b(small_caps("🔧 environment variables")) + "\n\n"
    rows = []
    for key, label in ENV_KEYS:
        val = get_setting(f"env_{key}", "") or ""
        short = (val[:20] + "…") if len(val) > 20 else val
        text += f"<b>{small_caps(label)}:</b> <code>{e(short) if short else 'not set'}</code>\n"
        rows.append([InlineKeyboardButton(
            f"✏️ {label}", callback_data=f"env_edit_{key}"
        )])

    rows.append([_back_btn("admin_back"), _close_btn()])
    markup = InlineKeyboardMarkup(rows)
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)


# ── Auto-forward Source Panel ─────────────────────────────────────────────────

async def show_fwd_source_panel(context, chat_id: int) -> None:
    """Show auto-forward source channel management panel."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from core.buttons import _btn, _back_btn, _close_btn
    from core.helpers import safe_send_message
    from database_dual import get_setting

    fwd_source = get_setting("autoforward_source_chat", "") or "Not configured"
    fwd_dest   = get_setting("autoforward_dest_chat", "")   or "Not configured"
    fwd_on     = get_setting("autoforward_enabled", "false") == "true"

    text = (
        b(small_caps("🔄 auto-forward settings")) + "\n\n"
        + bq(
            f"<b>{small_caps('Status')}:</b> {'✅ ON' if fwd_on else '❌ OFF'}\n"
            f"<b>{small_caps('Source')}:</b> <code>{e(fwd_source)}</code>\n"
            f"<b>{small_caps('Destination')}:</b> <code>{e(fwd_dest)}</code>"
        )
    )

    rows = [
        [InlineKeyboardButton(
            f"{'🔴 Disable' if fwd_on else '🟢 Enable'} Auto-Forward",
            callback_data="fwd_toggle"
        )],
        [InlineKeyboardButton("📤 Set Source Chat", callback_data="fwd_set_chat")],
        [InlineKeyboardButton("📥 Set Destination", callback_data="fwd_set_dest")],
        [InlineKeyboardButton("🗑 Clear Config",    callback_data="fwd_clear")],
        [_back_btn("admin_back"), _close_btn()],
    ]
    markup = InlineKeyboardMarkup(rows)
    await safe_send_message(context.bot, chat_id, text, reply_markup=markup)
