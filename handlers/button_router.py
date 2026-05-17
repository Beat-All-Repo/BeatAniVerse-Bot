"""
handlers/button_router.py
=========================
Central callback query router — all InlineKeyboardButton callbacks handled here.
Answers every query immediately. Routes to sub-handlers by data prefix.

MERGED VERSION — combines button_router.py + button_router__1_.py
All callbacks from both sources are present. File 1 (button_router.py) is the
superset; File 2 additions are fully merged below with compat aliases.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETE CALLBACK REGISTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UTILITY
  noop                          — Silent no-op
  close_message                 — Delete current message
  top_searches_refresh          — Refresh /top leaderboard inline

FORCE-SUB / SUBSCRIPTION
  verify_subscription           — Re-verify fsub + deliver pending deep-link
  fsub_add                      — Start add-channel flow
  fsub_remove_menu              — Show remove channel menu
  fsub_del_<id>                 — Delete a specific fsub channel
  fsub_list_full                — List all fsub channels
  fsub_link_stats               — Show link count stats
  fsub_fwd_help                 — Show forward-a-post help
  fsub_fwd_source               — Show forward-source panel
  new_ch_jbr_yes / new_ch_jbr_no — Set JBR mode for new channel
  manage_force_sub              — Open channels management panel
  generate_links                — Generate invite link for channel
  admin_show_links              — Show all backup links

ADMIN PANEL NAVIGATION
  adm_page_<n>                  — Navigate admin panel pages 0-5
  admin_back                    — Return to admin main menu

STATS / SYSTEM
  admin_stats                   — Send stats panel
  admin_sysstats                — Send system stats
  broadcast_stats_panel         — Show broadcast stats
  admin_logs                    — Open logs panel
  admin_logs_refresh            — Refresh log view (80 lines)
  admin_logs_200                — Refresh log view (200 lines)
  admin_logs_errors             — Filter error lines only
  admin_logs_warnings           — Filter warning lines only
  admin_logs_download           — Download full log as file
  admin_logs_clear              — Wipe log file

RESTART
  admin_restart_confirm         — Prompt restart confirmation
  admin_do_restart              — Execute restart

BROADCAST
  admin_broadcast_start         — Enter broadcast compose mode
  broadcast_mode_<mode>         — Set broadcast delivery mode
  broadcast_schedule            — Schedule broadcast for future time

CLONE MANAGEMENT
  manage_clones                 — Open clones panel
  clone_add                     — Start add-clone-bot flow
  clone_remove                  — Alias → clone_remove_menu
  clone_remove_menu             — List clones for removal
  clone_del_<uname>             — Delete specific clone bot
  clone_refresh_cmds            — Refresh commands on all clones
  clone_list_full               — List all clones (incl. inactive)
  clone_move_links              — Move all links to another bot
  clones_disable / clones_enable — Toggle clone feature globally

SETTINGS
  admin_settings                — Open settings panel
  toggle_maintenance            — Toggle maintenance mode
  toggle_clone_redirect         — Toggle clone redirect
  toggle_auto_delete            — Toggle auto-delete globally
  set_dm_del_delay              — Set DM auto-delete delay
  set_gc_del_delay              — Set group auto-delete delay
  toggle_clean_gc               — Toggle clean group chat mode
  admin_link_expiry             — Set link expiry minutes
  admin_watermarks_toggle       — Toggle watermarks on/off
  admin_spam_settings           — Open spam protection panel
  toggle_spam_protect           — Toggle spam protection
  set_flood_limit               — Set flood message limit
  set_flood_window              — Set flood detection window (seconds)
  set_backup_channel            — Set backup channel URL
  admin_text_style              — Open text style picker
  text_style_set_<style>        — Set text style (normal/smallcaps/bold)
  admin_btn_style               — Open button style picker
  btn_style_set_<style>         — Set button style (mathbold/smallcaps)
  admin_set_main_channel        — Set main channel for poster delivery
  admin_link_expiry             — Configure link expiry

FILTER POSTER
  admin_filter_poster           — Open filter poster settings
  fp_toggle_<cid>               — Toggle filter poster on/off per chat
  fp_pregen_all_<cid>           — Pre-generate all posters in background
  fp_tmpl_<cid>_<tpl>          — Set poster template
  fp_mode_toggle_<cid>          — Toggle poster/text mode
  fp_wm_toggle_<layer>_<cid>    — Toggle watermark layer on/off
  fp_wm_<layer>_<cid>           — Open watermark layer editor
  fp_set_autodel                — Set filter auto-delete time
  fp_set_linkexpiry             — Set link expiry for filter
  fp_view_cache                 — Show cached poster count
  fp_set_channel_name           — Set channel display name on poster
  fp_set_caption_tmpl           — Set filter caption template
  fp_clear_cache                — Clear poster cache
  fp_channel_info               — Show poster DB channel
  fp_set_join_btn_<x>           — Set join button label text
  inline_anim_toggle            — Toggle loading animation for inline

FEATURE FLAGS
  admin_feature_flags           — Open feature flags panel
  flag_toggle_<key>_<val>       — Toggle a feature flag

CATEGORY SETTINGS  (cat_name ∈ anime|manga|movie|tvshow)
  admin_category_settings       — Open category picker
  admin_category_settings_<cat> — Open settings for category
  settings_category_<cat>       — Alias above
  cat_settings_<cat>            — Alias above
  cat_caption_<cat>             — Edit caption template
  cat_branding_<cat>            — Edit branding text
  cat_brand_clear_<cat>         — Clear branding
  cat_buttons_<cat>             — Configure inline buttons
  cat_btns_clear_<cat>          — Clear buttons
  cat_font_<cat>                — Pick font style
  cat_font_set_<cat>_<style>    — Set font style value
  cat_btn_style_<cat>           — Open button style picker
  cat_btn_style_set_<cat>_<s>   — Set button style value
  cat_watermark_<cat>           — Edit watermark text
  cat_wm_clear_<cat>            — Clear watermark
  cat_logo_<cat>                — Set logo overlay image
  cat_preview_<cat>             — Generate preview poster
  cat_thumbnail_<cat>           — Open poster layout/template picker
  cat_tmpl_set_<cat>_<tpl>      — Apply selected poster template

USER MANAGEMENT
  user_management               — Open user management panel
  admin_export_users_quick      — Export all users to CSV
  admin_import_users            — Import users from CSV/XLSX
  admin_import_links            — Import links from CSV/XLSX
  um_list_users                 — List users
  um_search_user                — Search user by ID/username
  um_ban_user                   — Ban user input prompt
  um_unban_user                 — Unban user input prompt
  um_delete_user                — Delete user from DB prompt
  um_banned_list                — List banned users
  user_page_<offset>            — Paginate user list
  user_list_page_<page>         — Paginate full user list
  manage_user_<uid>             — Show individual user details
  user_search                   — State: await search input
  user_ban_input                — State: await ban input
  user_unban_input              — State: await unban input
  user_delete_input             — State: await delete input
  user_ban_<uid>                — Execute ban on specific user
  user_unban_<uid>              — Execute unban on specific user
  user_del_<uid>                — Execute delete on specific user

UPLOAD MANAGER
  upload_menu                   — Open upload manager
  upload_preview                — Preview caption template
  upload_toggle_auto            — Toggle auto-caption
  upload_reset                  — Reset episode counter to 1
  upload_toggle_q_<quality>     — Toggle a quality selection
  upload_set_caption            — Set caption template
  upload_set_anime_name         — Set anime name
  upload_set_season             — Set season number
  upload_set_episode            — Set starting episode
  upload_set_total              — Set total episode count
  upload_set_channel            — Set target channel
  upload_quality_menu           — Open quality selection grid
  upload_clear_db               — Prompt clear upload database
  upload_confirm_clear          — Execute clear upload database
  upload_back                   — Return to upload menu

AUTO-FORWARD
  admin_autoforward             — Open auto-forward menu
  af_add_connection             — Start add-connection flow
  af_set_delay                  — Set forwarding delay
  af_set_caption                — Set caption override
  af_replacements_menu          — View text replacements
  af_bulk                       — Start bulk forward
  af_filters_menu               — Open AF filter options
  af_filter_guide               — Show filter how-to guide
  af_toggle_dm                  — Toggle forward in DM
  af_toggle_group               — Toggle forward in groups
  af_blacklist / af_whitelist   — Edit blacklist/whitelist words
  af_toggle_all                 — Toggle auto-forward globally
  af_list_connections           — List all connections
  af_conn_detail_<id>           — Show connection details
  af_conn_del_<id>              — Delete a connection

AUTO MANGA UPDATE
  admin_autoupdate              — Open manga tracking menu
  au_add_manga                  — Track new manga
  au_stop_<id>                  — Stop tracking manga
  au_list_manga                 — List tracked manga
  au_remove_manga               — Alias → au_list_manga
  au_stats                      — Manga tracking statistics
  au_mode_full / au_mode_latest — Choose delivery mode
  au_interval_<key>             — Set check interval
  mdex_track_<id>               — Start tracking a MangaDex title
  mdex_chapter_<id>             — View chapter page info

SEARCH RESULTS
  search_result_<cat>_<id>      — Show poster for search result
    Supported cats: mangadex, anime, manga, movie, tvshow

ENV PANEL
  admin_env_panel               — Open environment variables panel
  env_edit_<KEY>                — Edit a specific env key

POSTER ENGINE / SEND TO CHANNEL
  admin_set_main_channel        — Set default poster destination channel
  pe_send_main:<x>              — Initiate send-to-channel flow
  pe_send_ask_id:<chat>:<msg>   — Prompt for custom channel ID
  pe_do_send:<chat>:<msg>:<dst> — Execute copy_message to channel

PANEL IMAGE MANAGEMENT
  panel_img_add_urls            — Add panel images (photo/file_id/URL)
  panel_img_toggle_source       — Toggle API-first vs URL-first source
  panel_img_clear_urls          — Clear custom URL list
  panel_img_manage              — List / manage stored images
  panel_img_view_<page>         — Paginate image list
  panel_img_del_<idx>           — Delete image at index
  panel_img_refresh_cache       — Clear image cache
  admin_clear_img_cache         — Clear image cache (alias)

IMAGE NAVIGATION
  imgn:<idx>:<key>:next|prev    — Navigate multi-image galleries

DB CLEANUP
  dbcleanup_confirm             — Prompt DB cleanup
  dbcleanup_run                 — Execute DB cleanup

USER FEATURES PANEL
  user_features_panel           — Show user features (start)
  user_features_<page>          — Paginate feature pages
  uf_help:<feature>             — Show feature help card
  feat_<feature>                — Show feature command help / toggle

  Feature help cards (uf_help:): anime, manga, movie, character,
    reactions, chatbot, notes, group

  Feature toggles / info (feat_): couple, slap, hug, kiss, pat,
    inline_search, reactions, chatbot (toggle!), truth_dare, notes,
    warns, muting, bans, rules, airing, character, anime_info, afk

MISC / NAVIGATION
  about_bot                     — Show about panel
  user_back                     — Return to start screen
  user_help                     — Open help panel
  admin_cmd_list                — Show command list

CHANNEL WELCOME
  admin_channel_welcome         — Open channel welcome panel
  cw_add                        — Start add-welcome flow
  cw_list                       — List configured welcomes
  cw_remove_menu                — Menu to select welcome to remove
  cw_edit_<cid>                 — Edit welcome for specific channel
  cw_settext_<cid>              — Set welcome text
  cw_setbtns_<cid>              — Set welcome buttons
  cw_setimg_<cid>               — Set welcome image
  cw_preview_<cid>              — Preview welcome message
  cw_del_<cid>                  — Delete channel welcome
  cw_toggle_<cid>               — Toggle welcome on/off

POSTER COMMANDS (from admin panel)
  poster_cmd_<tmpl>             — Show poster command usage

ANIME MODULE
  anpick_* / lang_* / size_* / anthmb_* — Route to anime module callback

FILTER SETTINGS
  admin_filter_settings         — Open filter settings panel
  admin_anime_links             — Show anime/channel keyword links
  del_acl_<x>                   — Redirects to channel management panel
  filter_toggle_dm              — Toggle DM filter
  filter_toggle_group           — Toggle group filter

FSUB FORWARD SOURCE
  fwd_set_chat                  — Set forward source chat
  fwd_set_msgid                 — Set forward source message ID
  fwd_test                      — Test forward source message
  fwd_toggle_tag                — Toggle forward with/without tag
  fwd_toggle_private            — Toggle private channel support

MODULE INFO CARDS (admin panel page 4)
  mod_admin, mod_antiflood, mod_approve, mod_blacklist, mod_blsticker,
  mod_chatbot, mod_cleaner, mod_connection, mod_currency, mod_custfilters,
  mod_globalbans, mod_imdb, mod_locks, mod_logchannel, mod_ping, mod_purge,
  mod_reporting, mod_sed, mod_shell, mod_speedtest, mod_stickers, mod_tagall,
  mod_translator, mod_truthdare, mod_ud, mod_wallpaper, mod_wiki,
  mod_writetool, mod_animequotes, mod_gettime, mod_badwords

INLINE HANDLER
  inv_loading:<x> / inv_ready:<x>  — Inline invite loading animation

CHATBOT PANEL (comprehensive — covers all sub-routes)
  admin_chatbot_panel           — Open chatbot API key panel
  chatbot_gc_view:<gc>          — View group chatbot config
  chatbot_gc_toggle:<gc>        — Toggle chatbot in group
  chatbot_gc_assign:<gc>        — Assign API key set to group
  chatbot_assign_set:<x>        — Confirm key set assignment
  chatbot_gender_<x>            — Set bot gender/persona
  chatbot_usage_stats:<x>       — View usage stats
  chatbot_sets                  — List API key sets
  chatbot_set_view:<id>         — View specific key set
  chatbot_add_key:<id>          — Add API key to set
  chatbot_new_set               — Create new key set
  chatbot_del_key:<id>          — Delete key from set
  chatbot_add_gc                — Add group to chatbot config
  chatbot_add_gemini:<x>        — Legacy: add Gemini key
  chatbot_add_groq:<x>          — Legacy: add Groq key
  chatbot_del_gemini:<x>        — Legacy: delete Gemini key
  chatbot_del_groq:<x>          — Legacy: delete Groq key

ANIME/HINDI REQUEST
  request_anime:<title>         — Request anime via /request
  request_hindi:<title>         — Request Hindi dub via /request

SPAM PROTECTION INPUTS
  set_flood_limit               — Prompt: set new flood limit
  set_flood_window              — Prompt: set new flood window (seconds)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END OF REGISTRY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import asyncio
import html
import json
import time
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from core.config import (
    ADMIN_ID, OWNER_ID, PUBLIC_ANIME_CHANNEL_URL,
    LINK_EXPIRY_MINUTES, JOIN_BTN_TEXT, HERE_IS_LINK_TEXT,
    ANIME_BTN_TEXT, REQUEST_BTN_TEXT, CONTACT_BTN_TEXT,
    FORCE_SUB_TEXT, BUTTON_STYLE, BOT_NAME,
)
from core.logging_setup import logger
from core.helpers import (
    safe_answer, safe_send_message, safe_edit_text, safe_reply,
    safe_send_photo, safe_delete, UserFriendlyError,
)
from core.buttons import _btn, _back_btn, _close_btn, bold_button, _grid3, _back_kb
from core.text_utils import b, bq, code, e, small_caps
from core.state_machine import (
    user_states, upload_progress,
    ADD_CLONE_TOKEN, GENERATE_LINK_IDENTIFIER,
    SET_BACKUP_CHANNEL, PENDING_BROADCAST, PENDING_BROADCAST_OPTIONS,
    SET_CATEGORY_CAPTION, SET_CATEGORY_BRANDING, SET_CATEGORY_BUTTONS,
    SET_CATEGORY_THUMBNAIL, SET_WATERMARK_TEXT, SET_CATEGORY_LOGO,
    UPLOAD_SET_CAPTION, UPLOAD_SET_SEASON, UPLOAD_SET_EPISODE,
    UPLOAD_SET_TOTAL, UPLOAD_SET_CHANNEL, SEARCH_USER_INPUT,
    BAN_USER_INPUT, UNBAN_USER_INPUT, DELETE_USER_INPUT,
    AF_ADD_CONNECTION_SOURCE, AU_ADD_MANGA_TITLE, AU_ADD_MANGA_TARGET,
    CW_SET_TEXT, CW_SET_BUTTONS, BroadcastMode,
    PENDING_CHANNEL_POST, SCHEDULE_BROADCAST_DATETIME,
)
from core.cache import cache_get, cache_set
from core.filters_system import force_sub_required
from core.panel_image import get_panel_pic, get_panel_pic_async, _PANEL_IMAGE_AVAILABLE
from core.panel_store import _deliver_panel, safe_edit_panel

# ── Filter poster integration ──────────────────────────────────────────────────
try:
    from filter_poster import (
        _get_filter_poster_enabled, _set_filter_poster_enabled,
        _get_default_poster_template, _set_default_poster_template,
        build_filter_poster_settings_keyboard, get_filter_poster_settings_text,
        _clear_poster_cache, _get_cache_count, _get_panel_db_images,
    )
    _FILTER_POSTER_AVAILABLE = True
except ImportError:
    _FILTER_POSTER_AVAILABLE = False
    def _get_cache_count(): return 0
    def _clear_poster_cache(): return 0
    def _get_panel_db_images(): return []



async def _panel_edit(query, text: str, reply_markup=None) -> None:
    """
    Smart edit for admin panel callbacks.
    Photo panels can't be edited as text — deletes and resends instead.
    """
    try:
        await query.edit_message_text(
            text=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
        return
    except Exception as e1:
        err = str(e1).lower()
        if "message is not modified" in err:
            return
        # Photo message — try caption edit
        if any(k in err for k in ("no text", "can't be edited", "caption")):
            try:
                await query.edit_message_caption(
                    caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
                )
                return
            except Exception:
                pass
    # Last resort: delete + resend
    chat_id = query.message.chat_id if query.message else 0
    try:
        await query.message.delete()
    except Exception:
        pass
    if chat_id:
        try:
            bot = context.bot if hasattr(context, 'bot') else query.get_bot()
            await bot.send_message(
                chat_id=chat_id, text=text,
                parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            pass


@force_sub_required
async def button_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, _data_override: str = None
) -> None:
    """
    Central callback query router.
    Answers every query immediately to prevent timeout errors.
    """
    query = update.callback_query
    if not query:
        return

    if _data_override is None:
        try:
            await query.answer()
        except Exception:
            pass

    data = _data_override if _data_override is not None else (query.data or "")

    # Helper: delete current message and send fresh panel
    async def _del_and_send(text: str, reply_markup=None, photo=None) -> None:
        """Delete the triggering panel message, then send fresh content."""
        try:
            if query and query.message:
                await query.message.delete()
        except Exception:
            pass
        if photo:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id, photo=photo, caption=text,
                    parse_mode=ParseMode.HTML, reply_markup=reply_markup,
                )
                return
            except Exception:
                pass
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=ParseMode.HTML,
                reply_markup=reply_markup, disable_web_page_preview=True,
            )
        except Exception:
            pass

    # Smart edit: try text edit → caption edit → delete+resend
    async def _smart_edit(text: str, reply_markup=None) -> None:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        except Exception as _e:
            if "not modified" in str(_e).lower():
                return
        try:
            await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            return
        except Exception:
            pass
        await _del_and_send(text, reply_markup)
    uid = query.from_user.id if query.from_user else 0
    chat_id = query.message.chat_id if query.message else uid
    is_admin = uid in (ADMIN_ID, OWNER_ID)

    # ── Utility ────────────────────────────────────────────────────────────────
    if data == "noop":
        return

    if data == "close_message":
        try:
            await query.delete_message()
        except Exception:
            pass
        return

    if data == "top_searches_refresh":
        # Refresh /top leaderboard inline
        try:
            from database_dual import get_top_search_analytics
            top = get_top_search_analytics(limit=10)
        except Exception:
            top = []
        if not top:
            try:
                from filter_poster import get_top_filter_searches
                top = get_top_filter_searches(limit=10)
            except Exception:
                top = []
        border = "▰" * 13
        lines = [
            "<b>╔══════════════════════╗</b>",
            "<blockquote><b>   ║✦ 🏆 ᴛᴏᴘ sᴇᴀʀᴄʜᴇs ✦║</b></blockquote>",
            "<b>╚══════════════════════╝</b>",
            f"<b>┌─➤{border}</b>",
            "<blockquote>",
        ]
        medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 10
        for i, (title, count) in enumerate((top or [])[:10]):
            medal = medals[i]
            lines.append(f"<b>{medal} {i+1}. {html.escape(title[:30])}</b>  <code>{count} 🔍</code>")
        if not top:
            lines.append("<i>No data yet.</i>")
        lines.append("</blockquote>")
        lines.append(f"<b>└─➤{border}</b>")
        lines.append("\n<i>Unique searches in last 2 weeks per user</i>")
        text = "\n".join(lines)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="top_searches_refresh")]])
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        return

    if data == "verify_subscription":
        # ── Step 1: Show "watching..." loading state immediately (no delay) ───
        # Edit only the text/caption so the user sees activity instantly.
        _watching_text = f"<b>{small_caps('ᴡᴀᴛᴄʜɪɴɢ ...')}</b>"
        try:
            if query.message and query.message.photo:
                # Photo message — edit caption
                await query.message.edit_caption(
                    caption=_watching_text,
                    parse_mode="HTML",
                    reply_markup=None,
                )
            else:
                await query.message.edit_text(
                    text=_watching_text,
                    parse_mode="HTML",
                    reply_markup=None,
                )
        except Exception:
            pass  # If edit fails, continue silently — speed not affected

        # ── Step 2: Re-verify subscription (this IS the speed-critical path) ─
        from core.filters_system import get_unsubscribed_channels
        unsubscribed = await get_unsubscribed_channels(uid, context.bot)

        if unsubscribed:
            # Still not subscribed — re-show the fsub screen
            from core.filters_system import _send_force_sub_screen
            await _send_force_sub_screen(update, context, unsubscribed, uid)
            return

        # ── Step 3: Subscription verified — deliver pending link or start ────
        pending_link_id = context.user_data.pop("pending_link_id", None)

        try:
            await query.message.delete()
        except Exception:
            pass

        if pending_link_id:
            # User came via a channel deep-link — deliver that link now.
            # The link is already warm in cache (pre-generated when fsub screen
            # was shown), so delivery is instant with zero extra API calls.
            from handlers.start import handle_deep_link
            await handle_deep_link(update, context, pending_link_id)
        else:
            from handlers.start import start
            await start(update, context)
        return

    # ── Admin panel page navigation ────────────────────────────────────────────
    if data.startswith("adm_page_"):
        if not is_admin:
            return
        try:
            page_num = int(data.split("_")[-1])
        except Exception:
            page_num = 0
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context, query=query, page=page_num)
        return

    if data == "admin_back":
        if not is_admin:
            return
        user_states.pop(uid, None)
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context, query)
        return

    # ── Image navigation ───────────────────────────────────────────────────────
    if data.startswith("imgn:"):
        try:
            parts = data.split(":", 3)
            if len(parts) == 4:
                _, cur_idx_str, img_key, direction = parts
                cur_idx = int(cur_idx_str)
                entry = cache_get(img_key)
                images = entry.get("urls", []) if isinstance(entry, dict) else (entry or [])
                saved_caption = entry.get("caption", "") if isinstance(entry, dict) else ""

                if images and len(images) > 1:
                    step = 1 if direction == "next" else -1
                    new_idx = (cur_idx + step) % len(images)
                    new_url = images[new_idx]
                    new_kb = [
                        [InlineKeyboardButton("🔙", callback_data=f"imgn:{new_idx}:{img_key}:prev"),
                         InlineKeyboardButton("✖️", callback_data="close_message"),
                         InlineKeyboardButton("🔜", callback_data=f"imgn:{new_idx}:{img_key}:next")],
                    ]
                    if query.message and query.message.reply_markup:
                        old_rows = list(query.message.reply_markup.inline_keyboard)
                        top_rows = old_rows[:-1] if old_rows else []
                        new_kb = top_rows + new_kb
                    try:
                        if saved_caption:
                            await query.message.edit_media(
                                InputMediaPhoto(media=new_url, caption=saved_caption, parse_mode=ParseMode.HTML),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                        else:
                            await query.message.edit_media(
                                InputMediaPhoto(media=new_url),
                                reply_markup=InlineKeyboardMarkup(new_kb),
                            )
                    except Exception as exc:
                        logger.debug(f"imgn edit_media error: {exc}")
        except Exception as exc:
            logger.debug(f"imgn handler error: {exc}")
        return

    # ── Stats panel ─────────────────────────────────────────────────────────────
    if data == "admin_stats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.admin_panel import send_stats_panel
        await send_stats_panel(context, chat_id)
        return

    if data == "admin_sysstats":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.helpers import get_system_stats_text
        await safe_send_message(
            context.bot, chat_id, get_system_stats_text(),
            reply_markup=InlineKeyboardMarkup([[
                bold_button("♻️ Refresh", callback_data="admin_sysstats"), _back_btn("admin_back")
            ]]),
        )
        return

    if data == "broadcast_stats_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import broadcaststats_command
        await broadcaststats_command(update, context)
        return

    # ── Admin logs ─────────────────────────────────────────────────────────────
    if data == "admin_logs":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import _send_logs_panel
        await _send_logs_panel(context.bot, chat_id)
        return

    if data in ("admin_logs_refresh", "admin_logs_200", "admin_logs_errors",
                "admin_logs_warnings", "admin_logs_download", "admin_logs_clear"):
        if not is_admin:
            return
        from handlers.misc_cmds import _send_logs_panel
        import os, glob

        if data == "admin_logs_clear":
            try:
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    for f in glob.glob(pattern):
                        open(f, "w").close()
                await safe_answer(query, "✅ Logs cleared")
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            await _send_logs_panel(context.bot, chat_id, query=query)
            return

        if data == "admin_logs_download":
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            log_text = f.read()
                        break
                if log_text:
                    from io import BytesIO
                    doc = BytesIO(log_text.encode())
                    doc.name = "bot_logs.txt"
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_document(
                        chat_id=chat_id, document=doc,
                        caption="<b>📋 Full Bot Logs</b>", parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Back", callback_data="admin_logs_refresh"),
                            InlineKeyboardButton("✖ Close", callback_data="close_message"),
                        ]]),
                    )
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        if data == "admin_logs_errors":
            # Show only error lines
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            lines = [l for l in f if "ERROR" in l or "error" in l.lower()]
                        log_text = "".join(lines[-50:])
                        break
                if not log_text:
                    log_text = "No errors found! ✅"
                text = f"<b>🔴 Error Lines Only</b>\n\n<pre>{e(log_text[-3800:])}</pre>"
                await _smart_edit(text, InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 All Logs", callback_data="admin_logs_refresh"),
                    InlineKeyboardButton("✖ Close", callback_data="close_message"),
                ]]))
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        if data == "admin_logs_warnings":
            try:
                log_text = ""
                for pattern in ["logs/bot.log", "logs/*.log", "bot.log"]:
                    files = glob.glob(pattern)
                    if files:
                        log_file = max(files, key=os.path.getmtime)
                        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                            lines = [l for l in f if "WARNING" in l or "WARN" in l]
                        log_text = "".join(lines[-50:])
                        break
                if not log_text:
                    log_text = "No warnings found! ✅"
                text = f"<b>🟡 Warning Lines Only</b>\n\n<pre>{e(log_text[-3800:])}</pre>"
                await _smart_edit(text, InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 All Logs", callback_data="admin_logs_refresh"),
                    InlineKeyboardButton("✖ Close", callback_data="close_message"),
                ]]))
            except Exception as exc:
                await safe_answer(query, f"❌ {exc}", show_alert=True)
            return

        # admin_logs_refresh or admin_logs_200
        n = 200 if data == "admin_logs_200" else 80
        await _send_logs_panel(context.bot, chat_id, lines=n, query=query)
        return

    # ── Restart ────────────────────────────────────────────────────────────────
    if data == "admin_restart_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query, b("⚠️ Restart Bot?\n\n") + bq(b("This will restart the bot.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button("✔️ RESTART", callback_data="admin_do_restart"),
                bold_button("CANCEL", callback_data="admin_back"),
            ]]),
        )
        return

    if data == "admin_do_restart":
        if not is_admin:
            return
        await safe_answer(query, "Restarting…")
        from handlers.misc_cmds import reload_command
        await reload_command(update, context)
        return

    # ── Broadcast flow ─────────────────────────────────────────────────────────
    if data == "admin_broadcast_start":
        if not is_admin:
            return
        user_states[uid] = PENDING_BROADCAST
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("📣 Broadcast") + "\n\n"
            + bq(b("Send the message you want to broadcast to all users.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        context.user_data["bot_prompt_message_id"] = msg.message_id if msg else None
        return

    if data.startswith("broadcast_mode_"):
        if not is_admin:
            return
        mode = data[len("broadcast_mode_"):]
        context.user_data["broadcast_mode"] = mode
        await safe_edit_text(
            query, b(f"Mode: {e(mode)}\n\nSend /confirm to broadcast or /cancel to abort."),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        user_states[uid] = PENDING_BROADCAST_OPTIONS
        return

    if data == "broadcast_schedule":
        if not is_admin:
            return
        user_states[uid] = SCHEDULE_BROADCAST_DATETIME
        await safe_edit_text(
            query,
            b("📅 Schedule Broadcast") + "\n\n"
            + bq(b("Send the date and time for the broadcast:\n")
                 + b("Format: YYYY-MM-DD HH:MM (UTC)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    # ── Force-sub channels panel ───────────────────────────────────────────────
    if data == "manage_force_sub":
        if not is_admin:
            return
        from handlers.admin_panel import _show_channels_panel
        await _show_channels_panel(update, context, query)
        return

    if data == "fsub_add":
        if not is_admin:
            return
        user_states[uid] = "PENDING_CHANNEL_POST_OR_TEXT"
        # Reuse ADD_CHANNEL_USERNAME state for text input
        user_states[uid] = 0  # ADD_CHANNEL_USERNAME = 0
        try:
            await query.delete_message()
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b("➕ ADD FORCE-SUB CHANNEL") + "\n\n"
            + bq(
                b("Send @username, numeric ID, or forward a post:\n\n")
                + "• <code>@BeatAnime</code>\n"
                + "• <code>-1001234567890</code>\n"
                + "• Forward any message from the channel"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        context.user_data["bot_prompt_message_id"] = msg.message_id if msg else None
        return

    # ── JBR type selection for private channel forwarding ─────────────────────
    if data in ("new_ch_jbr_yes", "new_ch_jbr_no"):
        if not is_admin:
            return
        context.user_data["new_ch_jbr"] = (data == "new_ch_jbr_yes")
        jbr_label = "🔔 Join-Request" if data == "new_ch_jbr_yes" else "📢 Direct-Join"
        ch_name = e(context.user_data.get("new_ch_title", "this channel"))
        try:
            await query.answer(f"Mode set: {jbr_label}")
        except Exception:
            pass
        msg = await safe_send_message(
            context.bot, chat_id,
            b(f"✅ Mode: {jbr_label}") + "\n\n"
            + bq(f"Channel: <b>{ch_name}</b>\n\nNow send the display title, or /skip to use the channel name:"),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_force_sub")]]),
        )
        context.user_data["bot_prompt_message_id"] = msg.message_id if msg else None
        return

    if data == "fsub_fwd_help":
        user_states[uid] = PENDING_CHANNEL_POST
        await safe_edit_text(
            query, b("📩 METHOD 3: Forward a Post") + "\n\n"
            + bq("1. Open the channel\n2. Forward any message to this bot\n\nThe bot reads the channel ID automatically."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_add")]]),
        )
        return

    if data == "fsub_remove_menu":
        if not is_admin:
            return
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels(return_usernames_only=False)
        if not channels:
            await safe_answer(query, "No channels to remove.")
            return
        buttons = [_btn(f"{row[1] or row[0]}", f"fsub_del_{row[0]}") for row in channels]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_force_sub"), _close_btn()])
        await safe_edit_text(query, b("SELECT CHANNEL TO REMOVE"), reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("fsub_del_"):
        if not is_admin:
            return
        uname = data[len("fsub_del_"):]
        from database_dual import delete_force_sub_channel
        delete_force_sub_channel(uname)
        await safe_answer(query, f"Removed: {uname}")
        await button_handler(update, context, "manage_force_sub")
        return

    if data == "fsub_list_full":
        if not is_admin:
            return
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels(return_usernames_only=False)
        text = b(f"ALL FORCE-SUB CHANNELS ({len(channels)})") + "\n\n"
        for i, row in enumerate(channels, 1):
            uname = row[0] if len(row) > 0 else ""
            title = row[1] if len(row) > 1 else uname
            jbr   = bool(row[2]) if len(row) > 2 else False
            jbr_str = " 🔔 JBR" if jbr else ""
            text += f"<b>{i}.</b> {e(title or uname)}{jbr_str}\n    ID: <code>{e(str(uname))}</code>\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    if data == "fsub_link_stats":
        if not is_admin:
            return
        try:
            from database_dual import get_links_count
            total = get_links_count()
        except Exception:
            total = "N/A"
        from database_dual import get_all_force_sub_channels
        channels = get_all_force_sub_channels()
        await safe_answer(query, f"Total links: {total} | Channels: {len(channels)}")
        return

    if data == "generate_links":
        if not is_admin:
            return
        user_states[uid] = GENERATE_LINK_IDENTIFIER
        await safe_edit_text(
            query,
            b(small_caps("🔗 generate channel link")) + "\n\n"
            + bq(b(small_caps("send the channel @username, numeric ID, or forward a post:"))),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_back")]]),
        )
        return

    if data == "admin_show_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import backup_command
        await backup_command(update, context)
        return

    # ── Clone management ───────────────────────────────────────────────────────
    if data in ("clones_disable", "clones_enable"):
        if not is_admin:
            return
        from database_dual import set_setting
        set_setting("clones_disabled", "true" if data == "clones_disable" else "false")
        status = "disabled 🚫" if data == "clones_disable" else "enabled ✅"
        await safe_answer(query, f"Clone feature {status}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "manage_clones":
        if not is_admin:
            return
        from handlers.clones import show_clones_panel
        await show_clones_panel(update, context, query)
        return

    if data == "clone_add":
        if not is_admin:
            return
        user_states[uid] = ADD_CLONE_TOKEN
        await safe_edit_text(
            query, b("🤖 Add Clone Bot") + "\n\n" + bq(b("Send the BOT TOKEN of the clone bot.")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="manage_clones")]]),
        )
        return

    if data == "clone_remove":
        if not is_admin:
            return
        from handlers.clones import show_remove_clone_menu
        await show_remove_clone_menu(query)
        return

    if data.startswith("clone_del_"):
        if not is_admin:
            return
        uname = data[len("clone_del_"):]
        from database_dual import remove_clone_bot
        remove_clone_bot(uname)
        await safe_answer(query, f"Removed @{uname}")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_refresh_cmds":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        from telegram import Bot
        from lifecycle import _register_bot_commands_on_bot
        clones = get_all_clone_bots(active_only=True)
        count = 0
        for _, token, uname, _, _ in clones:
            try:
                clone_bot = Bot(token=token)
                await _register_bot_commands_on_bot(clone_bot)
                count += 1
            except Exception:
                pass
        await safe_answer(query, f"Commands refreshed on {count} clone(s).")
        await button_handler(update, context, "manage_clones")
        return

    if data == "clone_remove_menu":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        clones = get_all_clone_bots(active_only=True)
        if not clones:
            await safe_answer(query, "No clone bots to remove.")
            return
        buttons = [_btn(f"@{c[2]}", f"clone_del_{c[2]}") for c in clones]
        rows = _grid3(buttons)
        rows.append([_back_btn("manage_clones"), _close_btn()])
        await safe_edit_text(
            query, b("SELECT CLONE TO REMOVE"),
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data == "clone_list_full":
        if not is_admin:
            return
        from database_dual import get_all_clone_bots
        clones = get_all_clone_bots()
        text = b(f"ALL CLONE BOTS ({len(clones)})") + "\n\n"
        for i, (cid, token, uname, active, added) in enumerate(clones, 1):
            st = "🟢" if active else "🔴"
            text += f"<b>{i}.</b> {st} @{e(uname or '?')}\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    if data == "clone_move_links":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_MOVE_LINKS"
        await safe_edit_text(
            query,
            b("MOVE LINKS") + "\n\n"
            + bq("Send: <code>@from_bot @to_bot</code>\nAll links will be reassigned."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    # ── Settings ───────────────────────────────────────────────────────────────
    if data == "admin_settings":
        if not is_admin:
            return
        from handlers.admin_panel import show_settings_panel
        await show_settings_panel(update, context, query)
        return

    if data == "toggle_maintenance":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("maintenance_mode", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("maintenance_mode", new_val)
        await safe_answer(query, f"Maintenance {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "toggle_clone_redirect":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("clone_redirect_enabled", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("clone_redirect_enabled", new_val)
        await safe_answer(query, f"Clone redirect {'ON' if new_val == 'true' else 'OFF'}")
        await button_handler(update, context, "admin_settings")
        return

    # ── Auto-delete toggle ─────────────────────────────────────────────────────
    if data == "toggle_auto_delete":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("auto_delete_messages", "true")
        new = "false" if cur == "true" else "true"
        set_setting("auto_delete_messages", new)
        await safe_answer(query, small_caps(f"auto-delete: {'on' if new == 'true' else 'off'}"))
        from handlers.admin_panel import show_settings_panel
        await show_settings_panel(update, context, query)
        return

    if data == "set_dm_del_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_DM_DEL_DELAY"
        try:
            await query.delete_message()
        except Exception:
            pass
        from database_dual import get_setting
        cur = get_setting("auto_delete_dm_delay", "120")
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set dm auto-delete delay")) + "\n\n"
            + bq(
                small_caps(f"current: {cur}s") + "\n"
                + small_caps("send number of seconds (e.g. 120 = 2 min, 0 = off)\n"
                             "this applies to all bot messages in private chat")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    if data == "set_gc_del_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_GC_DEL_DELAY"
        try:
            await query.delete_message()
        except Exception:
            pass
        from database_dual import get_setting
        cur = get_setting("auto_delete_gc_delay", "60")
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set gc auto-delete delay")) + "\n\n"
            + bq(
                small_caps(f"current: {cur}s") + "\n"
                + small_caps("send number of seconds (e.g. 60 = 1 min, 0 = off)\n"
                             "posters and chatbot replies are never deleted")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    if data == "toggle_clean_gc":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("clean_gc_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("clean_gc_enabled", new_val)
        await safe_answer(query, f"Clean GC {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_link_expiry":
        if not is_admin:
            return
        from database_dual import get_setting
        current_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(f"<b>Current:</b> {current_exp} minutes\n\nSend a number (1-60):"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_settings"), _close_btn()]]),
        )
        return

    if data == "admin_watermarks_toggle":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("watermarks_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("watermarks_enabled", new_val)
        await safe_answer(query, f"Watermarks {'enabled' if new_val == 'true' else 'disabled'}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "admin_spam_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        spam_protect = get_setting("spam_protection_enabled", "true") == "true"
        flood_limit  = get_setting("flood_limit", "5")
        flood_window = get_setting("flood_window_sec", "10")
        text_sp = (
            b("SPAM PROTECTION") + "\n\n"
            + bq(
                f"<b>Status:</b> {'🟢 Enabled' if spam_protect else '🔴 Disabled'}\n"
                f"<b>Flood limit:</b> {flood_limit} msgs\n"
                f"<b>Flood window:</b> {flood_window}s\n\n"
                "Anti-spam covers:\n"
                " ✔️ Flood detection\n"
                " ✔️ Message rate limiting\n"
                " ✔️ User cooldowns on anime requests\n"
                " ✔️ Banned user blocking\n"
                " ✔️ Maintenance mode blocking"
            )
        )
        sp_grid = [
            _btn("TOGGLE " + ("🟢" if spam_protect else "🔴"), "toggle_spam_protect"),
            _btn("FLOOD LIMIT",  "set_flood_limit"),
            _btn("FLOOD WINDOW", "set_flood_window"),
        ]
        sp_rows = _grid3(sp_grid)
        sp_rows.append([_back_btn("admin_settings"), _close_btn()])
        await safe_edit_text(query, text_sp, reply_markup=InlineKeyboardMarkup(sp_rows))
        return

    if data == "toggle_spam_protect":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("spam_protection_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("spam_protection_enabled", new_val)
        await safe_answer(query, f"Spam protection {'on' if new_val == 'true' else 'off'}")
        await button_handler(update, context, "admin_spam_settings")
        return

    if data == "set_backup_channel":
        if not is_admin:
            return
        user_states[uid] = SET_BACKUP_CHANNEL
        await safe_edit_text(
            query,
            b(" Set Backup Channel URL") + "\n\n"
            + bq(b("Send the backup channel URL (e.g., https://t.me/backup_channel)")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_settings")]]),
        )
        return

    # ── Text style ─────────────────────────────────────────────────────────────
    if data == "admin_text_style":
        if not is_admin:
            return
        try:
            from text_style import build_text_style_keyboard, get_text_style_panel_text
            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id, get_text_style_panel_text(),
                reply_markup=build_text_style_keyboard(),
            )
        except Exception:
            await safe_answer(query, "Text style module unavailable.")
        return

    if data.startswith("text_style_set_"):
        if not is_admin:
            return
        style = data[len("text_style_set_"):]
        if style in ("normal", "smallcaps", "bold"):
            try:
                from text_style import set_style, build_text_style_keyboard, get_text_style_panel_text
                set_style(style)
                await safe_answer(query, f"✅ Text style: {style}")
                await safe_edit_text(
                    query, get_text_style_panel_text(), reply_markup=build_text_style_keyboard()
                )
            except Exception:
                pass
        return

    # ── Filter poster ──────────────────────────────────────────────────────────
    if data == "admin_filter_poster":
        if not is_admin:
            return
        try:
            from filter_poster import (
                build_filter_poster_settings_keyboard, get_filter_poster_settings_text
            )
            _fp_text = get_filter_poster_settings_text(chat_id)
            _fp_kb   = build_filter_poster_settings_keyboard(chat_id)
            try:
                await query.edit_message_text(_fp_text, parse_mode=ParseMode.HTML, reply_markup=_fp_kb)
            except Exception:
                try:
                    await query.edit_message_caption(caption=_fp_text, parse_mode=ParseMode.HTML, reply_markup=_fp_kb)
                except Exception:
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_message(
                        chat_id=chat_id, text=_fp_text, parse_mode=ParseMode.HTML,
                        reply_markup=_fp_kb, disable_web_page_preview=True,
                    )
        except Exception as _fpe:
            logger.debug(f"admin_filter_poster: {_fpe}")
            await safe_answer(query, "Filter poster module unavailable.")
        return

    if data.startswith("fp_toggle_"):
        if not is_admin:
            return
        try:
            fp_cid = int(data.split("_")[-1])
        except Exception:
            fp_cid = 0
        try:
            from filter_poster import (
                _get_filter_poster_enabled, _set_filter_poster_enabled,
                build_filter_poster_settings_keyboard, get_filter_poster_settings_text,
            )
            _set_filter_poster_enabled(fp_cid, not _get_filter_poster_enabled(fp_cid))
            _t = get_filter_poster_settings_text(fp_cid)
            _k = build_filter_poster_settings_keyboard(fp_cid)
            await _smart_edit(_t, _k)
        except Exception:
            pass
        return

    if data.startswith("fp_pregen_all_"):
        if not is_admin:
            return
        from jobs.scheduled import _pregen_all_filter_posters
        asyncio.create_task(_pregen_all_filter_posters(context.bot, uid, chat_id))
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🎌 poster pre-generation started!")) + "\n"
            + bq(small_caps("generating posters for all registered anime channels in background.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data.startswith("fp_tmpl_"):
        if not is_admin:
            return
        parts = data.split("_")
        if len(parts) >= 4:
            try:
                fp_chat_id = int(parts[2])
                fp_template = parts[3]
                if _FILTER_POSTER_AVAILABLE:
                    _set_default_poster_template(fp_chat_id, fp_template)
                    # Also save as global default (chat_id=0) so all chats see it
                    if fp_chat_id != 0:
                        _set_default_poster_template(0, fp_template)
                    await safe_answer(query, f"✅ Template set to {fp_template}")
                    _t2 = get_filter_poster_settings_text(fp_chat_id)
                    _k2 = build_filter_poster_settings_keyboard(fp_chat_id)
                    await _smart_edit(_t2, _k2)
            except Exception:
                pass
        return

    if data.startswith("fp_mode_toggle_"):
        if not is_admin:
            return
        try:
            fp_chat_id = int(data.split("_")[-1])
        except Exception:
            fp_chat_id = 0
        if _FILTER_POSTER_AVAILABLE:
            try:
                from filter_poster import get_filter_mode, set_filter_mode
                cur = get_filter_mode(fp_chat_id)
                new_mode = "text" if cur == "poster" else "poster"
                set_filter_mode(fp_chat_id, new_mode)
                label = "TEXT (link only)" if new_mode == "text" else "POSTER (full card)"
                await safe_answer(query, f"✔️ Mode: {label}")
                _t3 = get_filter_poster_settings_text(fp_chat_id)
                _k3 = build_filter_poster_settings_keyboard(fp_chat_id)
                await _smart_edit(_t3, _k3)
            except Exception:
                pass
        return

    if data.startswith("fp_wm_toggle_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[3]
        try:
            fp_chat_id = int(parts[4])
        except Exception:
            fp_chat_id = chat_id
        if _FILTER_POSTER_AVAILABLE:
            try:
                from filter_poster import get_wm_layer, set_wm_layer
                ldata = get_wm_layer(fp_chat_id, layer)
                ldata["enabled"] = not ldata.get("enabled", False)
                set_wm_layer(fp_chat_id, layer, ldata)
                state_str = "enabled" if ldata["enabled"] else "disabled"
                await safe_answer(query, f"✔️ Layer {layer.upper()} {state_str}")
                _t3 = get_filter_poster_settings_text(fp_chat_id)
                _k3 = build_filter_poster_settings_keyboard(fp_chat_id)
                await _smart_edit(_t3, _k3)
            except Exception:
                pass
        return

    if data.startswith("fp_wm_"):
        if not is_admin:
            return
        parts = data.split("_")
        layer = parts[2]
        try:
            fp_chat_id = int(parts[3])
        except Exception:
            fp_chat_id = chat_id
        if not _FILTER_POSTER_AVAILABLE:
            await safe_answer(query, "Filter poster module unavailable.")
            return
        try:
            from filter_poster import get_wm_layer
            ldata = get_wm_layer(fp_chat_id, layer)
        except Exception:
            ldata = {}
        pos_list = "center | bottom | top | left | right | bottom-left | bottom-right | top-left | top-right"
        layer_names = {"a": "PRIMARY TEXT", "b": "SECONDARY TEXT", "c": "STICKER / IMAGE"}
        if layer == "c":
            panel_text = (
                b("WATERMARK LAYER C — STICKER / IMAGE") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-left'))}\n"
                    f"<b>Scale:</b> {ldata.get('scale', 0.12)} (0.05–0.30)\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 200)} (0–255)\n\n"
                    "<b>To set sticker:</b> Send any Telegram sticker as a reply.\n"
                    "<b>To set image:</b> Send: <code>https://url | position | scale | opacity</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        else:
            panel_text = (
                b(f"WATERMARK LAYER {layer.upper()} — {layer_names.get(layer, '')}") + "\n\n"
                + bq(
                    f"<b>Enabled:</b> {'🟢 Yes' if ldata.get('enabled') else '🔴 No'}\n"
                    f"<b>Text:</b> {e(ldata.get('text', '—'))}\n"
                    f"<b>Position:</b> {e(ldata.get('position', 'bottom-right'))}\n"
                    f"<b>Font size:</b> {ldata.get('font_size', 24)}\n"
                    f"<b>Color:</b> {e(ldata.get('color', '#FFFFFF'))}\n"
                    f"<b>Opacity:</b> {ldata.get('opacity', 150)} (0–255)\n\n"
                    "<b>Send format:</b> <code>text | position | size | #color | opacity</code>\n"
                    "<b>Example:</b> <code>BeatAnime | bottom-right | 24 | #FFFFFF | 150</code>\n"
                    f"<b>Positions:</b> {pos_list}"
                )
            )
        user_states[uid] = f"AWAITING_WM_LAYER_{layer.upper()}_{fp_chat_id}"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id, panel_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🟢 ENABLE" if not ldata.get("enabled") else "🔴 DISABLE",
                    callback_data=f"fp_wm_toggle_{layer}_{fp_chat_id}",
                )],
                [_back_btn("admin_filter_poster"), _close_btn()],
            ]),
        )
        return

    if data == "fp_set_autodel":
        if not is_admin:
            return
        try:
            from database_dual import get_setting
            cur_del = int(get_setting(f"filter_auto_delete_{chat_id}", "300"))
        except Exception:
            cur_del = 300
        user_states[uid] = "AWAITING_FILTER_AUTODEL"
        await safe_edit_text(
            query,
            b("FILTER AUTO-DELETE TIME") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_del}s ({cur_del // 60} min)\n\n"
                "Send seconds before poster + link auto-deletes:\n"
                "• <code>0</code> = never delete\n"
                "• <code>300</code> = 5 minutes (default)\n"
                "• <code>600</code> = 10 minutes\n"
                "• <code>1800</code> = 30 minutes"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_set_linkexpiry":
        if not is_admin:
            return
        from database_dual import get_setting
        cur_exp = get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES))
        user_states[uid] = "AWAITING_LINK_EXPIRY_FP"
        await safe_edit_text(
            query,
            b("LINK EXPIRY MINUTES") + "\n\n"
            + bq(
                f"<b>Current:</b> {cur_exp} min\n\n"
                "Send minutes the join link stays valid:\n"
                "• <code>0</code> = permanent (no expiry)\n"
                "• <code>5</code> = 5 minutes (default)\n"
                "• <code>60</code> = 1 hour"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return

    if data == "fp_view_cache":
        if not is_admin:
            return
        count = _get_cache_count() if _FILTER_POSTER_AVAILABLE else 0
        await safe_answer(query, f"📦 {count} posters cached")
        return

    # ── SET CHANNEL DISPLAY NAME ──────────────────────────────────────────────
    if data == "fp_set_channel_name":
        if not is_admin:
            return
        user_states[uid] = "set_channel_display_name"
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📛 set channel display name")) + "\n\n"
            + bq(small_caps(
                "send the name you want to appear on filter posters.\n"
                "example: NARUTO VERSE DUB\n\n"
                "this will replace the watermark text automatically."
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("filter_poster_settings"), _close_btn()]]),
        )
        return

    # ── SET CAPTION TEMPLATE ───────────────────────────────────────────────────
    if data == "fp_set_caption_tmpl":
        if not is_admin:
            return
        user_states[uid] = "set_filter_caption_template"
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📝 set filter caption template")) + "\n\n"
            + bq(small_caps(
                "send your caption template. available variables:\n"
                "{title} — anime title\n"
                "{native} — japanese title\n"
                "{genres} — genres\n"
                "{channel} — your channel name\n"
                "{here_text} — \'here is your link\' text\n"
                "{info} — status/episodes info lines\n\n"
                "example:\n"
                "<b>{title}</b>\n{genres}\n\nvia {channel}"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("filter_poster_settings"), _close_btn()]]),
        )
        return

    if data == "fp_clear_cache":
        if not is_admin:
            return
        if _FILTER_POSTER_AVAILABLE:
            cleared = _clear_poster_cache()
            await safe_answer(query, f"🗑 Cleared {cleared} cached posters")
            try:
                await safe_edit_text(
                    query,
                    get_filter_poster_settings_text(chat_id),
                    reply_markup=build_filter_poster_settings_keyboard(chat_id),
                )
            except Exception:
                pass
        return

    if data == "fp_channel_info":
        if not is_admin:
            return
        try:
            from filter_poster import POSTER_DB_CHANNEL as _PDC
            if _PDC:
                await safe_answer(query, f"Poster DB Channel: {_PDC}")
            else:
                await safe_answer(query, "Set POSTER_DB_CHANNEL in env to enable poster saving")
        except Exception:
            await safe_answer(query, "Filter poster module unavailable.")
        return

    # ── Feature flags ──────────────────────────────────────────────────────────
    if data == "admin_feature_flags":
        if not is_admin:
            return
        user_states.pop(uid, None)
        from handlers.admin_panel import send_feature_flags_panel
        await send_feature_flags_panel(context, chat_id, query)
        return

    if data.startswith("flag_toggle_"):
        if not is_admin:
            return
        parts = data[len("flag_toggle_"):].rsplit("_", 1)
        if len(parts) == 2:
            from database_dual import set_setting
            flag_key, new_val = parts
            set_setting(flag_key, new_val)
            is_on = new_val in ("true", "1")
            await safe_answer(query, f"{'Enabled' if is_on else 'Disabled'}!")
            from handlers.admin_panel import send_feature_flags_panel
            await send_feature_flags_panel(context, chat_id, query)
        return

    # ── Category settings ──────────────────────────────────────────────────────
    if data == "admin_category_settings":
        if not is_admin:
            return
        keyboard = [
            [bold_button("TV SHOWS", callback_data="admin_category_settings_tvshow"),
             bold_button("MOVIES", callback_data="admin_category_settings_movie")],
            [bold_button("ANIME", callback_data="admin_category_settings_anime"),
             bold_button("MANGA", callback_data="admin_category_settings_manga")],
            [bold_button("POST SETTING", callback_data="admin_settings")],
            [bold_button("AUTO FORWARD", callback_data="admin_autoforward"),
             bold_button("POST SEARCH", callback_data="admin_cmd_list")],
            [_back_btn("admin_back")],
        ]
        await safe_edit_text(query, b("Choose the category"), reply_markup=InlineKeyboardMarkup(keyboard))
        return

    for cat_name in ("anime", "manga", "movie", "tvshow"):
        if data in (f"admin_category_settings_{cat_name}", f"settings_category_{cat_name}", f"cat_settings_{cat_name}"):
            from handlers.admin_panel import show_category_settings_menu
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_caption_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_CAPTION
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Set Caption Template for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send the caption template with placeholders like {title}, {score}, etc.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}")
                ]]),
            )
            return

        if data == f"cat_branding_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BRANDING
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f"🏷 Set Branding for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send your branding text (appended at the bottom of posts).")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Clear", callback_data=f"cat_brand_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_brand_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "branding", "")
            await safe_answer(query, "Branding cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_buttons_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_BUTTONS
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Configure Buttons for {e(cat_name.upper())}") + "\n\n"
                + bq(b("Send button config, one per line:\nFormat: Button Text - https://url")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Clear Buttons", callback_data=f"cat_btns_clear_{cat_name}"),
                    bold_button("🔙 Cancel", callback_data=f"admin_category_settings_{cat_name}"),
                ]]),
            )
            return

        if data == f"cat_btns_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "buttons", "[]")
            await safe_answer(query, "Buttons cleared.")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_font_{cat_name}":
            if not is_admin:
                return
            await safe_edit_text(
                query, b(small_caps(f"font style — {cat_name}")),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button(small_caps("normal"),     callback_data=f"cat_font_set_{cat_name}_normal"),
                     bold_button(small_caps("small caps"), callback_data=f"cat_font_set_{cat_name}_smallcaps")],
                    [_back_btn(f"cat_settings_{cat_name}"), _close_btn()],
                ]),
            )
            return

        if data == f"cat_btn_style_{cat_name}":
            if not is_admin:
                return
            try:
                from database_dual import get_setting
                cur_style = get_setting("button_style", "normal") or "normal"
            except Exception:
                cur_style = "normal"
            await safe_edit_text(
                query,
                b(small_caps(f"button caption style — {cat_name}")) + "\n\n"
                + bq(
                    small_caps("choose how button labels are styled:") + "\n"
                    + f"<b>{small_caps('Current')}:</b> <code>{e(cur_style)}</code>\n\n"
                    + small_caps("normal") + " — Standard text\n"
                    + small_caps("smallcaps") + " — sᴍᴀʟʟ ᴄᴀᴘs ᴛᴇxᴛ\n"
                    + small_caps("custom") + " — Keep exact text you type"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [bold_button(small_caps("normal"),    callback_data=f"cat_btn_style_set_{cat_name}_normal"),
                     bold_button(small_caps("smallcaps"), callback_data=f"cat_btn_style_set_{cat_name}_smallcaps")],
                    [bold_button(small_caps("custom"),    callback_data=f"cat_btn_style_set_{cat_name}_custom")],
                    [_back_btn(f"cat_settings_{cat_name}"), _close_btn()],
                ]),
            )
            return

        if data.startswith(f"cat_btn_style_set_{cat_name}_"):
            if not is_admin:
                return
            style_val = data[len(f"cat_btn_style_set_{cat_name}_"):]
            if style_val in ("normal", "smallcaps", "custom"):
                from database_dual import set_setting
                set_setting("button_style", style_val)
                await safe_answer(query, small_caps(f"button style set to {style_val}"))
                from handlers.admin_panel import show_category_settings_menu
                await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data.startswith(f"cat_font_set_{cat_name}_"):
            if not is_admin:
                return
            font_val = data[len(f"cat_font_set_{cat_name}_"):]
            from handlers.post_gen import update_category_field
            from handlers.admin_panel import show_category_settings_menu
            update_category_field(cat_name, "font_style", font_val)
            await safe_answer(query, f"Font set to {font_val}")
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

        if data == f"cat_watermark_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_WATERMARK_TEXT
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f" Watermark for {e(cat_name.upper())}") + "\n\n"
                + bq("Send watermark text.\nOptionally: <code>Text | position</code>\nPositions: center bottom top bottom-right\nSend <code>none</code> to remove."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        if data == f"cat_wm_clear_{cat_name}":
            if not is_admin:
                return
            from handlers.post_gen import update_category_field
            update_category_field(cat_name, "watermark_text", None)
            update_category_field(cat_name, "logo_file_id", None)
            await safe_answer(query, "Watermark cleared", show_alert=True)
            return

        if data == f"cat_logo_{cat_name}":
            if not is_admin:
                return
            user_states[uid] = SET_CATEGORY_LOGO
            context.user_data["editing_category"] = cat_name
            await safe_edit_text(
                query, b(f"LOGO — {e(cat_name.upper())}") + "\n\n"
                + bq("Send an image file to use as logo overlay.\nSend <code>none</code> to remove."),
                reply_markup=InlineKeyboardMarkup([[_back_btn(f"cat_settings_{cat_name}"), _close_btn()]]),
            )
            return

        if data == f"cat_preview_{cat_name}":
            await safe_answer(query, "Generating preview poster...")
            defaults = {"anime": "Naruto", "manga": "One Piece", "movie": "Avengers", "tvshow": "Breaking Bad"}
            try:
                from filter_poster import get_or_generate_poster
                asyncio.create_task(get_or_generate_poster(
                    bot=context.bot, chat_id=chat_id,
                    title=defaults.get(cat_name, "Demo"),
                    template={"anime": "ani", "manga": "anim", "movie": "ani", "tvshow": "ani"}.get(cat_name, "ani"),
                    media_type={"anime": "ANIME", "manga": "MANGA", "movie": "MOVIE", "tvshow": "TV"}.get(cat_name, "ANIME"),
                ))
            except Exception:
                pass
            return

        if data == f"cat_thumbnail_{cat_name}":
            if not is_admin:
                return
            # Show poster LAYOUT/STYLE template picker — not thumbnail URL
            try:
                from handlers.post_gen import get_category_settings
                cur_tmpl = get_category_settings(cat_name).get("template_name", "ani")
            except Exception:
                cur_tmpl = "ani"

            # All available poster visual templates
            _POSTER_TEMPLATES = {
                # Palette templates (same structure, different colours)
                "ani":    ("🎌", "ᴀɴɪᴍᴇ ᴄʟᴀssɪᴄ",    "Dark blue · AniList · Landscape bleed"),
                "dark":   ("🌑", "ᴅᴀʀᴋ ᴘᴜʀᴘʟᴇ",       "Deep dark · Purple accent · Minimal"),
                "light":  ("☀️", "ᴄʟᴇᴀɴ ʟɪɢʜᴛ",       "White BG · Blue accent · Clean look"),
                "crun":   ("🍊", "ᴄʀᴜɴᴄʜʏʀᴏʟʟ",        "Orange accent · CR logo · Warm tone"),
                "net":    ("🔴", "ɴᴇᴛꜰʟɪx",             "Pure black · Red accent · NF logo"),
                "mod":    ("✨", "ᴍᴏᴅᴇʀɴ ᴛᴇᴀʟ",        "Dark BG · Teal accent · Sleek edges"),
                "anim":   ("📗", "ᴍᴀɴɢᴀ ɢʀᴇᴇɴ",        "Dark green · AniList · Manga style"),
                "netm":   ("🟥", "ɴᴇᴛꜰʟɪx ᴍᴀɴɢᴀ",      "Netflix style for manga"),
                # Reference-image layouts (completely different structure)
                "stream": ("📺", "sᴛʀᴇᴀᴍ",             "Cover right · Episode card · Branding badge"),
                "vessel": ("🎴", "ᴠᴇssᴇʟ",             "Split panel · Portrait cover · Vertical brand"),
                "splash": ("🎞", "sᴘʟᴀsʜ",             "Full bleed · Cinematic · Title centred"),
                "od3n":   ("⬛", "ᴏᴅ3ɴ",               "Character centre · Vertical title · Info right"),
            }
            # Filter to category-relevant templates
            _CAT_TEMPLATES = {
                "anime":  ["ani", "stream", "od3n", "vessel", "splash", "dark", "light", "crun", "net", "mod"],
                "manga":  ["anim", "vessel", "splash", "netm", "dark", "light", "mod", "stream", "od3n"],
                "movie":  ["stream", "net", "od3n", "splash", "dark", "light", "vessel", "mod", "crun", "ani"],
                "tvshow": ["stream", "net", "od3n", "splash", "dark", "light", "vessel", "mod", "crun", "ani"],
            }
            tmpl_keys = _CAT_TEMPLATES.get(cat_name, list(_POSTER_TEMPLATES.keys()))

            text = (
                b(small_caps(f"🎨 poster layout — {cat_name}")) + "\n\n"
                + bq(
                    small_caps("choose a visual layout style for") + f" <b>{e(cat_name)}</b>\n"
                    + small_caps("current: ") + f"<code>{e(cur_tmpl)}</code>"
                ) + "\n\n"
            )
            for tk in tmpl_keys:
                em, lbl, desc = _POSTER_TEMPLATES.get(tk, ("🖼", tk, ""))
                active = " ✅" if tk == cur_tmpl else ""
                text += f"{em} <b>{lbl}</b>{active}\n<i>{small_caps(desc)}</i>\n\n"

            rows = []
            row = []
            for tk in tmpl_keys:
                em, lbl, _ = _POSTER_TEMPLATES.get(tk, ("🖼", tk, ""))
                active = "✅" if tk == cur_tmpl else ""
                btn_lbl = f"{em} {active}" if active else em
                row.append(bold_button(f"{btn_lbl} {small_caps(tk)}", callback_data=f"cat_tmpl_set_{cat_name}_{tk}"))
                if len(row) == 3:
                    rows.append(row); row = []
            if row: rows.append(row)
            rows.append([_back_btn(f"cat_settings_{cat_name}"), _close_btn()])

            try:
                await query.delete_message()
            except Exception:
                pass
            await safe_send_message(
                context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(rows)
            )
            return

        # ── Poster template selected ────────────────────────────────────────────
        if data.startswith(f"cat_tmpl_set_{cat_name}_"):
            if not is_admin:
                return
            new_tmpl = data[len(f"cat_tmpl_set_{cat_name}_"):]
            valid = ["ani","dark","light","crun","net","mod","anim","netm","lightm","darkm","netcr","stream","vessel","splash","od3n"]
            if new_tmpl not in valid:
                await safe_answer(query, small_caps("❌ unknown template"))
                return
            from handlers.post_gen import update_category_field
            update_category_field(cat_name, "template_name", new_tmpl)
            await safe_answer(query, small_caps(f"✅ template set to {new_tmpl}"))
            from handlers.admin_panel import show_category_settings_menu
            await show_category_settings_menu(context, chat_id, cat_name, query)
            return

    # ── User management ────────────────────────────────────────────────────────
    if data == "user_management":
        if not is_admin:
            return
        from handlers.admin_panel import show_user_management_panel
        await show_user_management_panel(update, context, query)
        return

    if data == "admin_export_users_quick":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import exportusers_command
        asyncio.create_task(exportusers_command(update, context))
        await safe_answer(query, small_caps("📤 exporting users…"))
        return

    if data == "admin_import_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_USERS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Users</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with user IDs.\n\n"
                "<b>CSV format (columns):</b>\n"
                "<code>user_id, username, first_name</code>\n\n"
                "<b>Excel:</b> First column must be <code>user_id</code>.\n\n"
                "Send the file now, or /cancel to abort."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    if data == "admin_import_links":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_IMPORT_LINKS_FILE"
        await safe_send_message(
            context.bot, chat_id,
            (
                "<b> Import Links</b>\n\n"
                "Send a <b>CSV</b> or <b>Excel (.xlsx)</b> file with link data.\n\n"
                "<b>CSV columns:</b> <code>link_id, file_name, channel_id</code>\n\n"
                "Send the file now, or /cancel to abort."
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]),
        )
        return

    if data == "um_list_users":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import listusers_command
        context.args = []
        await listusers_command(update, context)
        return

    if data == "um_search_user":
        if not is_admin:
            return
        user_states[uid] = SEARCH_USER_INPUT
        await safe_edit_text(
            query,
            b("🔍 Search User") + "\n\n" + bq(b("Send user ID or @username:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_ban_user":
        if not is_admin:
            return
        user_states[uid] = BAN_USER_INPUT
        await safe_edit_text(
            query,
            b("🚫 Ban User") + "\n\n" + bq(b("Send user ID or @username to ban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_unban_user":
        if not is_admin:
            return
        user_states[uid] = UNBAN_USER_INPUT
        await safe_edit_text(
            query,
            b("✅ Unban User") + "\n\n" + bq(b("Send user ID or @username to unban:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_delete_user":
        if not is_admin:
            return
        user_states[uid] = DELETE_USER_INPUT
        await safe_edit_text(
            query,
            b("🗑 Delete User") + "\n\n" + bq(b("Send the user ID to permanently delete from database:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="user_management")]]),
        )
        return

    if data == "um_banned_list":
        if not is_admin:
            return
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT user_id, username, first_name FROM users WHERE banned = TRUE LIMIT 20"
                )
                banned = cur.fetchall() or []
        except Exception:
            banned = []
        if not banned:
            await safe_answer(query, "No banned users.")
            return
        text = b(f"🚫 Banned Users ({len(banned)}):") + "\n\n"
        for buid, buname, bfname in banned:
            text += f"• {e(bfname or '')} @{e(buname or '')} {code(str(buid))}\n"
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup([[_back_btn("user_management")]]))
        return

    if data.startswith("user_page_"):
        if not is_admin:
            return
        offset = int(data[len("user_page_"):])
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.misc_cmds import listusers_command
        context.args = [str(offset)]
        await listusers_command(update, context)
        return

    if data.startswith("manage_user_"):
        if not is_admin:
            return
        target_uid_mu = int(data[len("manage_user_"):])
        try:
            from database_dual import get_user_info_by_id
            user_info = get_user_info_by_id(target_uid_mu)
        except Exception:
            user_info = None
        if not user_info:
            await safe_answer(query, "User not found.")
            return
        u_id, u_uname, u_fname, u_lname, u_joined, u_banned = user_info
        name = f"{u_fname or ''} {u_lname or ''}".strip() or "N/A"
        text = (
            b("👤 User Details") + "\n\n"
            f"<b>ID:</b> {code(str(u_id))}\n"
            f"<b>Name:</b> {e(name)}\n"
            f"<b>Username:</b> {'@' + e(u_uname) if u_uname else '—'}\n"
            f"<b>Joined:</b> {code(str(u_joined)[:16])}\n"
            f"<b>Status:</b> {'🚫 Banned' if u_banned else '✅ Active'}"
        )
        keyboard = []
        if u_banned:
            keyboard.append([bold_button("Unban", callback_data=f"user_unban_{u_id}")])
        else:
            keyboard.append([bold_button("🚫 Ban", callback_data=f"user_ban_{u_id}")])
        keyboard.append([bold_button("Delete", callback_data=f"user_del_{u_id}")])
        keyboard.append([_back_btn("user_management")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_list_page_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from database_dual import get_user_count, get_all_users
        offset = page * 10
        total = get_user_count()
        users = get_all_users(limit=10, offset=offset)
        text = b(f"USERS {offset+1}–{min(offset+10, total)} of {total:,}") + "\n\n"
        for uid2, uname, fname, lname, joined, banned in users:
            name = f"{fname or ''} {lname or ''}".strip() or "N/A"
            st = "🔴" if banned else "🟢"
            text += f"{st} <b>{e(name[:20])}</b> — @{e(uname or str(uid2))}\n"
        nav = []
        if page > 0:
            nav.append(_btn("PREV", f"user_list_page_{page-1}"))
        if total > offset + 10:
            nav.append(_btn("NEXT", f"user_list_page_{page+1}"))
        rows = [nav] if nav else []
        rows.append([_back_btn("user_management"), _close_btn()])
        try:
            await query.delete_message()
        except Exception:
            pass
        await _deliver_panel(context.bot, chat_id, "users", text, InlineKeyboardMarkup(rows), query=None)
        return

    for _state_name, _cb, _state_const in (
        ("user_search", "AWAITING_USER_SEARCH", "AWAITING_USER_SEARCH"),
        ("user_ban_input", "AWAITING_BAN_USER", "AWAITING_BAN_USER"),
        ("user_unban_input", "AWAITING_UNBAN_USER", "AWAITING_UNBAN_USER"),
        ("user_delete_input", "AWAITING_DELETE_USER", "AWAITING_DELETE_USER"),
    ):
        if data == _state_name:
            if not is_admin:
                return
            user_states[uid] = _state_const
            labels = {
                "user_search": "Search User", "user_ban_input": "Ban User",
                "user_unban_input": "Unban User", "user_delete_input": "Delete User",
            }
            await safe_edit_text(
                query, b(labels[data]) + "\n\n" + bq("Send @username or user ID:"),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
            return

    if data.startswith("user_ban_"):
        if not is_admin:
            return
        from database_dual import ban_user
        target_uid = int(data[len("user_ban_"):])
        if target_uid not in (ADMIN_ID, OWNER_ID):
            ban_user(target_uid)
            await safe_answer(query, "User banned.")
        return

    if data.startswith("user_unban_"):
        if not is_admin:
            return
        from database_dual import unban_user
        target_uid = int(data[len("user_unban_"):])
        unban_user(target_uid)
        await safe_answer(query, "User unbanned.")
        return

    if data.startswith("user_del_"):
        if not is_admin:
            return
        from database_dual import db_manager
        target_uid = int(data[len("user_del_"):])
        if target_uid in (ADMIN_ID, OWNER_ID):
            await safe_answer(query, "Cannot delete admin.", show_alert=True)
            return
        try:
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM users WHERE user_id = %s", (target_uid,))
        except Exception:
            pass
        await safe_answer(query, "User deleted.")
        await button_handler(update, context, "user_management")
        return

    # ── Upload manager ─────────────────────────────────────────────────────────
    if data == "upload_menu":
        if not is_admin:
            return
        from handlers.upload import load_upload_progress, show_upload_menu
        await load_upload_progress()
        try:
            await query.delete_message()
        except Exception:
            pass
        await show_upload_menu(chat_id, context)
        return

    if data == "upload_preview":
        if not is_admin:
            return
        from handlers.upload import build_caption_from_progress, get_upload_menu_markup
        cap = build_caption_from_progress()
        await safe_edit_text(query, b("👁 Caption Preview:") + "\n\n" + cap, reply_markup=get_upload_menu_markup())
        return

    if data == "upload_toggle_auto":
        if not is_admin:
            return
        from handlers.upload import save_upload_progress, show_upload_menu
        upload_progress["auto_caption_enabled"] = not upload_progress["auto_caption_enabled"]
        await save_upload_progress()
        status = "ON" if upload_progress["auto_caption_enabled"] else "OFF"
        await safe_answer(query, f"Auto-caption: {status}")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data == "upload_reset":
        if not is_admin:
            return
        from handlers.upload import save_upload_progress, show_upload_menu
        upload_progress["episode"] = 1
        upload_progress["video_count"] = 0
        await save_upload_progress()
        await safe_answer(query, "Episode reset to 1.")
        await show_upload_menu(chat_id, context, query.message)
        return

    if data.startswith("upload_toggle_q_"):
        if not is_admin:
            return
        from handlers.upload import save_upload_progress
        q_val = data[len("upload_toggle_q_"):]
        if q_val in upload_progress["selected_qualities"]:
            upload_progress["selected_qualities"].remove(q_val)
        else:
            upload_progress["selected_qualities"].append(q_val)
        await save_upload_progress()
        await safe_answer(query, f"{'Added' if q_val in upload_progress['selected_qualities'] else 'Removed'} {q_val}")
        await button_handler(update, context, "upload_quality_menu")
        return

    if data in ("upload_set_caption", "upload_set_anime_name", "upload_set_season",
                "upload_set_episode", "upload_set_total", "upload_set_channel", "upload_quality_menu",
                "upload_clear_db", "upload_confirm_clear", "upload_back"):
        if not is_admin:
            return
        from handlers.upload import show_upload_menu, save_upload_progress, get_upload_menu_markup
        from core.config import ALL_QUALITIES
        if data == "upload_set_caption":
            user_states[uid] = UPLOAD_SET_CAPTION
            await safe_edit_text(
                query, b(" Set Caption Template") + "\n\n"
                + bq(b("Send the new caption template.\nPlaceholders: {anime_name}, {season}, {episode}, {quality}")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
            )
        elif data == "upload_set_anime_name":
            user_states[uid] = UPLOAD_SET_CAPTION
            context.user_data["upload_field"] = "anime_name"
            await safe_edit_text(
                query, b("🎌 Set Anime Name") + "\n\n"
                + bq(b(f"Current: {e(upload_progress.get('anime_name', 'Anime Name'))}\n\nSend new name:")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]),
            )
        elif data == "upload_set_season":
            user_states[uid] = UPLOAD_SET_SEASON
            await safe_edit_text(query, b(f" Set Season\n\nCurrent: {upload_progress['season']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_episode":
            user_states[uid] = UPLOAD_SET_EPISODE
            await safe_edit_text(query, b(f" Set Episode\n\nCurrent: {upload_progress['episode']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_total":
            user_states[uid] = UPLOAD_SET_TOTAL
            await safe_edit_text(query, b(f" Set Total Episodes\n\nCurrent: {upload_progress['total_episode']}"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_set_channel":
            user_states[uid] = UPLOAD_SET_CHANNEL
            await safe_edit_text(query, b("📢 Set Target Channel\n\nSend @username or ID:"),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="upload_back")]]))
        elif data == "upload_quality_menu":
            keyboard = []
            row = []
            for q_val in ALL_QUALITIES:
                selected = q_val in upload_progress["selected_qualities"]
                mark = "✅ " if selected else ""
                row.append(bold_button(f"{mark}{q_val}", callback_data=f"upload_toggle_q_{q_val}"))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([_back_btn("upload_back")])
            await safe_edit_text(query, b("🎛 Quality Settings:"), reply_markup=InlineKeyboardMarkup(keyboard))
        elif data == "upload_clear_db":
            await safe_edit_text(
                query, b(" Clear Upload Database?") + "\n\n" + bq(b("This will reset all progress counters.")),
                reply_markup=InlineKeyboardMarkup([[
                    bold_button("Yes, Clear", callback_data="upload_confirm_clear"),
                    bold_button("CANCEL", callback_data="upload_back"),
                ]]),
            )
        elif data == "upload_confirm_clear":
            try:
                from database_dual import db_manager
                with db_manager.get_cursor() as cur:
                    cur.execute("DELETE FROM bot_progress WHERE id = 1")
                    cur.execute("""
                        INSERT INTO bot_progress (id, base_caption, selected_qualities, auto_caption_enabled, anime_name)
                        VALUES (1, %s, %s, %s, %s)
                    """, (
                        DEFAULT_CAPTION,
                        ",".join(upload_progress["selected_qualities"]),
                        upload_progress["auto_caption_enabled"],
                        upload_progress.get("anime_name", "Anime Name"),
                    ))
                from handlers.upload import load_upload_progress
                await load_upload_progress()
                await safe_answer(query, "Database cleared!")
                try:
                    await query.delete_message()
                except Exception:
                    pass
                await show_upload_menu(chat_id, context)
            except Exception as exc:
                await safe_answer(query, f"Error: {str(exc)[:50]}", show_alert=True)
        elif data == "upload_back":
            await show_upload_menu(chat_id, context, query.message)
        return

    # ── Auto-forward ───────────────────────────────────────────────────────────
    if data == "admin_autoforward":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoforward_menu
        await _show_autoforward_menu(context, chat_id)
        return

    if data == "af_add_connection":
        if not is_admin:
            return
        user_states[uid] = AF_ADD_CONNECTION_SOURCE
        await safe_edit_text(
            query, b("♻️ Add Auto-Forward Connection") + "\n\n"
            + bq(b("Step 1/2: SOURCE channel\n\nSend @username, -100ID, or forward a post:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoforward")]]),
        )
        return

    if data == "af_set_delay":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_DELAY"
        await safe_edit_text(
            query,
            b(small_caps("⏱ set auto-forward delay")) + "\n\n"
            + bq(small_caps("send delay in seconds (e.g. 30). send 0 for no delay.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_set_caption":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_CAPTION"
        await safe_edit_text(
            query,
            b(small_caps("✏️ set caption override")) + "\n\n"
            + bq(small_caps("send the caption text to append to all forwarded messages.\nsend /clear to remove caption override.")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_replacements_menu":
        if not is_admin:
            return
        rows = []
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("SELECT id, old_pattern, new_pattern FROM auto_forward_replacements ORDER BY id LIMIT 10")
                rows = cur.fetchall() or []
        except Exception:
            pass
        text = b(small_caps("🔄 text replacements")) + "\n\n"
        if rows:
            for r_id, old_p, new_p in rows:
                text += f"• <code>{e(old_p)}</code> → <code>{e(new_p)}</code>\n"
        else:
            text += bq(small_caps("no replacements set."))
        text += "\n\n" + bq(small_caps("to add: /autoforward replacements add old_text new_text"))
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]))
        return

    if data == "af_bulk":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_AF_BULK_COUNT"
        await safe_edit_text(
            query,
            b(small_caps("📦 bulk forward")) + "\n\n"
            + bq(small_caps("send the number of recent messages to forward from source channel (max 50).")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoforward")]]),
        )
        return

    if data == "af_filters_menu":
        if not is_admin:
            return
        dm_on = True
        grp_on = True
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT enable_in_dm, enable_in_group FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    dm_on, grp_on = bool(row[0]), bool(row[1])
        except Exception:
            pass
        dm_icon = "✅" if dm_on else "❌"
        grp_icon = "✅" if grp_on else "❌"
        ftext = (
            b("🔍 Auto-Forward Filters") + "\n\n"
            + bq(
                f"<b>Enable in DM:</b> {dm_icon}\n"
                f"<b>Enable in Group:</b> {grp_icon}\n\n"
                "<b>BLACKLIST:</b> Words that BLOCK a message from being forwarded.\n"
                "<b>WHITELIST:</b> When set, ONLY messages with a whitelisted word are forwarded.\n\n"
                "Leave whitelist empty to forward everything (except blacklisted)."
            )
        )
        fkb = [
            [bold_button(f"{dm_icon} Toggle DM", callback_data="af_toggle_dm"),
             bold_button(f"{grp_icon} Toggle Group", callback_data="af_toggle_group")],
            [bold_button("🚫 Blacklist Words", callback_data="af_blacklist"),
             bold_button("✅ Whitelist Words", callback_data="af_whitelist")],
            [bold_button("❓ Filter Guide", callback_data="af_filter_guide"),
             _back_btn("admin_autoforward")],
        ]
        await safe_edit_text(query, ftext, reply_markup=InlineKeyboardMarkup(fkb))
        return

    if data == "af_filter_guide":
        if not is_admin:
            return
        guide_text = (
            b("📖 How Filters Work") + "\n\n"
            + bq(
                "<b>Example scenario:</b>\n"
                "Forwarding from an anime channel but want to skip movie posts.\n\n"
                "<b>Step 1:</b> Add <code>movie</code> to Blacklist — any post with 'movie' is skipped.\n\n"
                "<b>Step 2 (optional):</b> Add <code>episode</code> to Whitelist — only 'episode' posts forward.\n\n"
                "<b>Note:</b> If Whitelist is EMPTY, all messages pass (except blacklisted)."
            )
        )
        await safe_edit_text(
            query, guide_text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        return

    if data in ("af_toggle_dm", "af_toggle_group"):
        if not is_admin:
            return
        col = "enable_in_dm" if data == "af_toggle_dm" else "enable_in_group"
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO auto_forward_filters (connection_id, enable_in_dm, enable_in_group)
                    VALUES (NULL, TRUE, TRUE)
                    ON CONFLICT DO NOTHING
                """)
                cur.execute(
                    f"UPDATE auto_forward_filters SET {col} = NOT {col} WHERE connection_id IS NULL"
                )
        except Exception as exc:
            logger.debug(f"af toggle error: {exc}")
        await safe_answer(query, small_caps("filter toggled!"))
        await button_handler(update, context, "af_filters_menu")
        return

    if data in ("af_blacklist", "af_whitelist"):
        if not is_admin:
            return
        kind = "Blacklist" if data == "af_blacklist" else "Whitelist"
        col = "blacklist_words" if data == "af_blacklist" else "whitelist_words"
        words = ""
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    f"SELECT {col} FROM auto_forward_filters WHERE connection_id IS NULL LIMIT 1"
                )
                row = cur.fetchone()
                if row and row[0]:
                    words = row[0]
        except Exception:
            pass
        await safe_edit_text(
            query,
            b(f" {kind} Words") + "\n\n"
            + bq(
                f"<b>Current:</b> {code(e(words or 'None'))}\n\n"
                "Send new comma-separated words to set the list:\n"
                "<i>e.g. word1, word2, word3</i>"
            ),
            reply_markup=InlineKeyboardMarkup([[_back_btn("af_filters_menu")]]),
        )
        user_states[uid] = f"af_set_{col}"
        return

    if data == "af_toggle_all":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("autoforward_enabled", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("autoforward_enabled", new_val)
        await safe_answer(query, f"Auto-Forward {'enabled' if new_val == 'true' else 'disabled'}!")
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoforward_menu
        await _show_autoforward_menu(context, chat_id)
        return

    if data == "af_list_connections":
        if not is_admin:
            return
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active, delay_seconds
                    FROM auto_forward_connections ORDER BY id DESC LIMIT 20
                """)
                conns = cur.fetchall() or []
        except Exception:
            conns = []
        text = b(f"♻️ Auto-Forward Connections ({len(conns)}):") + "\n\n"
        keyboard = []
        for cid, src, tgt, active, delay in conns:
            status = "✅" if active else "❌"
            text += f"{status} {code(str(src))} → {code(str(tgt))}\n"
            keyboard.append([bold_button(f"{status} {str(src)[:15]} → {str(tgt)[:15]}", callback_data=f"af_conn_detail_{cid}")])
        keyboard.append([_back_btn("admin_autoforward")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_detail_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_detail_"):])
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, source_chat_id, target_chat_id, active,
                           protect_content, silent, pin_message, delete_source, delay_seconds
                    FROM auto_forward_connections WHERE id = %s
                """, (conn_id,))
                conn = cur.fetchone()
        except Exception:
            conn = None
        if not conn:
            await safe_answer(query, "Connection not found.")
            return
        cid, src, tgt, active, protect, silent, pin, delete_src, delay = conn
        text = (
            b(f"♻️ Connection #{cid}") + "\n\n"
            f"<b>Source:</b> {code(str(src))}\n"
            f"<b>Target:</b> {code(str(tgt))}\n"
            f"<b>Active:</b> {'✅' if active else '❌'}\n"
            f"<b>Protect Content:</b> {'✅' if protect else '❌'}\n"
            f"<b>Silent:</b> {'✅' if silent else '❌'}\n"
            f"<b>Pin:</b> {'✅' if pin else '❌'}\n"
            f"<b>Delete Source:</b> {'✅' if delete_src else '❌'}\n"
            f"<b>Delay:</b> {code(str(delay) + 's' if delay else '0s')}"
        )
        keyboard = [
            [bold_button("Delete", callback_data=f"af_conn_del_{cid}"),
             _back_btn("af_list_connections")],
        ]
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("af_conn_del_"):
        if not is_admin:
            return
        conn_id = int(data[len("af_conn_del_"):])
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("DELETE FROM auto_forward_connections WHERE id = %s", (conn_id,))
        except Exception:
            pass
        await safe_answer(query, f"Connection #{conn_id} deleted.")
        await button_handler(update, context, "af_list_connections")
        return

    # ── Auto manga update ──────────────────────────────────────────────────────
    if data == "admin_autoupdate":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.autoforward import _show_autoupdate_menu
        await _show_autoupdate_menu(context, chat_id)
        return

    if data == "au_add_manga":
        if not is_admin:
            return
        user_states[uid] = AU_ADD_MANGA_TITLE
        await safe_edit_text(
            query, b("📚 Track New Manga") + "\n\n" + bq(b("Send the manga title to search on MangaDex:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    if data.startswith("au_stop_"):
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        manga_id = data[len("au_stop_"):]
        MangaTracker.remove_tracking(manga_id)
        await safe_answer(query, "Tracking stopped.")
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_list_manga":
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        text = MangaTracker.get_tracked_for_admin()
        rows = MangaTracker.get_all_tracked()
        keyboard = []
        for rec in rows:
            rec_id, manga_id, title, _, _, _, _ = rec
            keyboard.append([bold_button(f"🗑 Stop: {e(title[:20])}", callback_data=f"au_stop_{manga_id}")])
        keyboard.append([_back_btn("admin_autoupdate")])
        await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "au_remove_manga":
        if not is_admin:
            return
        await button_handler(update, context, "au_list_manga")
        return

    if data == "au_stats":
        if not is_admin:
            return
        from api.mangadex import MangaTracker
        rows = MangaTracker.get_all_tracked()
        text_au = (
            b(" Manga Tracking Stats") + "\n\n"
            f"<b>Total tracked:</b> {code(str(len(rows)))}"
        )
        await safe_edit_text(
            query, text_au,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_autoupdate")]]),
        )
        return

    if data.startswith("mdex_track_"):
        if not is_admin:
            await safe_answer(query, "Only admin can set up tracking.")
            return
        from api.mangadex import MangaDexClient
        manga_id = data[len("mdex_track_"):]
        manga = MangaDexClient.get_manga(manga_id)
        if not manga:
            await safe_answer(query, "Manga not found.")
            return
        attrs = manga.get("attributes", {}) or {}
        titles = attrs.get("title", {}) or {}
        title = titles.get("en") or next(iter(titles.values()), "Unknown")
        context.user_data["au_manga_id"] = manga_id
        context.user_data["au_manga_title"] = title
        keyboard = [
            [bold_button("Full Manga", callback_data="au_mode_full"),
             bold_button("Latest Chapters", callback_data="au_mode_latest")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + "\n\n" + bq(b("Choose delivery mode:\n\nFull Manga — all chapters\nLatest Chapters — only new ones")),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("mdex_chapter_"):
        ch_id_mc = data[len("mdex_chapter_"):]
        try:
            await query.delete_message()
        except Exception:
            pass
        try:
            from api.mangadex import MangaDexClient
            pages = MangaDexClient.get_chapter_pages(ch_id_mc)
        except Exception:
            pages = None
        text_mc = b("📖 Chapter") + "\n\n"
        if pages:
            base_url_mc, ch_hash_mc, filenames_mc = pages
            text_mc += (
                f"<b>Total Pages:</b> {code(str(len(filenames_mc)))}\n"
                f"<b>Chapter ID:</b> {code(ch_id_mc)}\n\n"
                + bq(b("Read this chapter online at MangaDex for the best experience."))
            )
        else:
            text_mc += b("Could not load chapter page info.")
        await safe_send_message(
            context.bot, chat_id, text_mc,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Read Now", url=f"https://mangadex.org/chapter/{ch_id_mc}")
            ]]),
        )
        return

    if data in ("au_mode_full", "au_mode_latest"):
        if not is_admin:
            return
        mode = "full" if data == "au_mode_full" else "latest"
        context.user_data["au_manga_mode"] = mode
        title = context.user_data.get("au_manga_title", "Unknown")
        keyboard = [
            [bold_button("5 min", callback_data="au_interval_5"),
             bold_button("10 min", callback_data="au_interval_10")],
            [bold_button("Random (5-10 min)", callback_data="au_interval_random"),
             bold_button("Custom", callback_data="au_interval_custom")],
            [bold_button("🔙 Cancel", callback_data="admin_autoupdate")],
        ]
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()}\n\n" + bq(b("Choose check interval:")),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if data.startswith("au_interval_"):
        if not is_admin:
            return
        interval_key = data[len("au_interval_"):]
        if interval_key == "custom":
            from core.state_machine import AU_CUSTOM_INTERVAL
            user_states[uid] = AU_CUSTOM_INTERVAL
            await safe_edit_text(
                query, b("📚 Custom Interval") + "\n\n" + bq(b("Send interval in minutes:")),
                reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
            )
            return
        interval_map = {"5": 5, "10": 10, "random": -1}
        interval_minutes = interval_map.get(interval_key, 10)
        context.user_data["au_manga_interval"] = interval_minutes
        title = context.user_data.get("au_manga_title", "Unknown")
        mode = context.user_data.get("au_manga_mode", "latest")
        user_states[uid] = AU_ADD_MANGA_TARGET
        await safe_edit_text(
            query, b(f"📚 {e(title)}") + f"\n<b>Mode:</b> {mode.title()} | <b>Interval:</b> {interval_minutes if interval_minutes > 0 else 'Random 5–10'} min\n\n"
            + bq(b("Send the target channel @username, numeric ID, or forward a post:")),
            reply_markup=InlineKeyboardMarkup([[bold_button("🔙 Cancel", callback_data="admin_autoupdate")]]),
        )
        return

    # ── Search results ─────────────────────────────────────────────────────────
    if data.startswith("search_result_"):
        rest = data[len("search_result_"):]
        for cat_key in ("mangadex", "anime", "manga", "movie", "tvshow"):
            if rest.startswith(f"{cat_key}_"):
                raw_id = rest[len(f"{cat_key}_"):]
                try:
                    await query.delete_message()
                except Exception:
                    pass
                if cat_key == "mangadex":
                    from api.mangadex import MangaDexClient
                    manga = MangaDexClient.get_manga(raw_id)
                    if manga:
                        caption_text, cover_url = MangaDexClient.format_manga_info(manga)
                        markup = InlineKeyboardMarkup([[
                            InlineKeyboardButton("📖 Read on MangaDex", url=f"https://mangadex.org/title/{raw_id}"),
                        ], [bold_button("Track This Manga", callback_data=f"mdex_track_{raw_id}")]])
                        if cover_url:
                            await safe_send_photo(context.bot, chat_id, cover_url, caption=caption_text, reply_markup=markup)
                        else:
                            await safe_send_message(context.bot, chat_id, caption_text, reply_markup=markup)
                    else:
                        await safe_send_message(context.bot, chat_id, b("❌ Manga not found."))
                else:
                    try:
                        mid = int(raw_id)
                    except ValueError:
                        mid = None
                    from handlers.post_gen import generate_and_send_post
                    await generate_and_send_post(context, chat_id, cat_key, media_id=mid)
                return

    # ── ENV variables panel ────────────────────────────────────────────────────
    if data == "admin_env_panel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass

        from handlers.admin_panel import show_env_panel
        await show_env_panel(context, chat_id)
        return

    # ── Set Main Channel (for send-to-main-channel feature) ───────────────────
    if data == "admin_set_main_channel":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        user_states[uid] = "AWAITING_MAIN_CHANNEL_ID"
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📢 set main channel")) + "\n\n"
            + bq(small_caps(
                "forward any message from the channel, or send the channel @username / numeric ID.\n\n"
                "this channel will receive posters when 'send to main channel' is tapped."
            )),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_settings")
            ]]),
        )
        return

    # ── pe_send_main: poster_engine send-to-main-channel callback ─────────────
    if data.startswith("pe_send_main:"):
        if not is_admin:
            return

        import json as _json
        from database_dual import get_setting

        # Get stored poster data
        try:
            raw = get_setting(f"last_poster_{uid}", "")
            pdata = _json.loads(raw) if raw else {}
        except Exception:
            pdata = {}

        src_chat = pdata.get("chat_id")
        src_msg  = pdata.get("msg_id")
        caption  = pdata.get("caption", "")

        if not src_chat or not src_msg:
            await safe_answer(query, "❌ Poster not found — regenerate and try again", show_alert=True)
            return

        # Check if default main channel is configured
        main_ch_raw = get_setting("main_channel_id", "") or ""
        main_ch_title = get_setting("main_channel_title", "") or "Default Channel"

        # Build keyboard: "Send to default" (if set) + "Enter ID/username" + cancel
        kb_rows = []
        if main_ch_raw.strip():
            kb_rows.append([InlineKeyboardButton(
                f"📢 Send to: {main_ch_title}",
                callback_data=f"pe_do_send:{src_chat}:{src_msg}:{main_ch_raw.strip()}"
            )])
        kb_rows.append([InlineKeyboardButton(
            "✏️ Enter Channel ID/Username",
            callback_data=f"pe_send_ask_id:{src_chat}:{src_msg}"
        )])
        kb_rows.append([InlineKeyboardButton("✖ Cancel", callback_data="close_message")])

        await _smart_edit(
            b("📤 Send Poster to Channel") + "\n\n"
            + bq(
                ("Default: <code>" + main_ch_raw + "</code>\n\n" if main_ch_raw else "")
                + small_caps("choose where to send the poster:")
            ),
            InlineKeyboardMarkup(kb_rows),
        )
        return

    if data.startswith("pe_send_ask_id:"):
        if not is_admin:
            return
        parts = data.split(":", 2)
        src_chat = parts[1] if len(parts) > 1 else ""
        src_msg  = parts[2] if len(parts) > 2 else ""
        user_states[uid] = f"AWAITING_SEND_TO_CHANNEL:{src_chat}:{src_msg}"
        await _smart_edit(
            b("✏️ Send Poster to Channel") + "\n\n"
            + bq(small_caps("send the channel @username or numeric ID:\nexample: @BeatAnime or -1001234567890")),
            InlineKeyboardMarkup([[InlineKeyboardButton("✖ Cancel", callback_data="close_message")]]),
        )
        return

    if data.startswith("pe_do_send:"):
        if not is_admin:
            return
        parts = data.split(":", 3)
        src_chat_s = parts[1] if len(parts) > 1 else ""
        src_msg_s  = parts[2] if len(parts) > 2 else ""
        dest_ch    = parts[3] if len(parts) > 3 else ""
        try:
            src_chat_i = int(src_chat_s)
            src_msg_i  = int(src_msg_s)
            try:
                dest_ch_i = int(dest_ch)
            except ValueError:
                dest_ch_i = dest_ch  # username
            import json as _json
            from database_dual import get_setting
            raw  = get_setting(f"last_poster_{uid}", "")
            pdat = _json.loads(raw) if raw else {}
            cap  = pdat.get("caption", "")
            await context.bot.copy_message(
                chat_id=dest_ch_i,
                from_chat_id=src_chat_i,
                message_id=src_msg_i,
                caption=cap,
                parse_mode="HTML",
            )
            await safe_answer(query, "✅ Sent to channel!")
            try:
                await query.message.delete()
            except Exception:
                pass
        except Exception as exc:
            await safe_answer(query, f"❌ Failed: {str(exc)[:80]}", show_alert=True)
        return



    if data.startswith("env_edit_"):
        if not is_admin:
            return
        env_key = data[len("env_edit_"):]
        from database_dual import get_setting
        import os as _os
        current = get_setting(f"env_{env_key}", _os.getenv(env_key, "")) or ""
        user_states[uid] = f"AWAITING_ENV_{env_key}"
        await safe_edit_text(
            query, b(f"SET {e(env_key)}") + "\n\n"
            + bq(f"<b>Current:</b> {code(e(current[:60] or '(empty)'))}\\n\nSend new value or <code>reset</code> to use .env default:"),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_env_panel"), _close_btn()]]),
        )
        return

    # ── Panel image controls ───────────────────────────────────────────────────
    if data == "panel_img_add_urls":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_PANEL_IMG_URLS"
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.panel_image import get_panel_db_images
        total_imgs = len(get_panel_db_images())
        await safe_send_message(
            context.bot, chat_id,
            b("🖼 Add Panel Images") + "\n\n"
            + bq(
                "<b>3 ways to add panel images:</b>\n\n"
                "1️⃣ <b>Send a photo</b> — bot saves to panel DB channel\n\n"
                "2️⃣ <b>Send file_ids</b> — comma or newline separated\n\n"
                "3️⃣ <b>Send URLs</b> — direct https:// image links\n\n"
                f"<b>Currently stored: {total_imgs} image(s)</b>"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖼 View Current Images", callback_data="panel_img_manage")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data == "panel_img_toggle_source":
        if not is_admin:
            return
        try:
            from database_dual import get_setting, set_setting
            current = get_setting("panel_image_source", "url") or "url"
            new_src = "api" if current == "url" else "url"
            set_setting("panel_image_source", new_src)
            label = ("🌐 API-first (waifu.im → anilist → nekos)" if new_src == "api"
                     else "🔗 URL-first (your custom URLs / PANEL_PICS env)")
            await safe_answer(query, f"✅ Panel source: {label[:40]}", show_alert=True)
            try:
                from panel_image import clear_image_cache
                clear_image_cache()
            except Exception:
                pass
        except Exception as exc:
            logger.error(f"panel_img_toggle: {exc}")
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_clear_urls":
        if not is_admin:
            return
        try:
            from database_dual import set_setting
            set_setting("panel_image_urls", "[]")
            try:
                from panel_image import clear_image_cache
                clear_image_cache()
            except Exception:
                pass
            await safe_answer(query, "✅ Custom URL list cleared. Using PANEL_PICS env or APIs.", show_alert=True)
        except Exception as exc:
            await safe_answer(query, f"❌ {str(exc)[:60]}", show_alert=True)
        await button_handler(update, context, "admin_settings")
        return

    if data == "panel_img_manage":
        if not is_admin:
            return
        from handlers.misc_cmds import _show_panel_img_list
        await _show_panel_img_list(context.bot, chat_id, query=query, page=0)
        return

    if data.startswith("panel_img_view_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from handlers.misc_cmds import _show_panel_img_list
        await _show_panel_img_list(context.bot, chat_id, query=query, page=page)
        return

    if data.startswith("panel_img_del_"):
        if not is_admin:
            return
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from core.panel_image import get_panel_db_images, save_panel_db_images
        from core.config import PANEL_DB_CHANNEL
        items = get_panel_db_images()
        if 0 <= page < len(items):
            removed = items.pop(page)
            for i, it in enumerate(items):
                it["index"] = i + 1
            save_panel_db_images(items)
            if _PANEL_IMAGE_AVAILABLE:
                try:
                    from panel_image import clear_tg_fileid
                    clear_tg_fileid()
                except Exception:
                    pass
            if PANEL_DB_CHANNEL and removed.get("msg_id"):
                try:
                    await context.bot.delete_message(PANEL_DB_CHANNEL, removed["msg_id"])
                except Exception:
                    pass
            new_page = max(0, page - 1) if items else 0
            from handlers.misc_cmds import _show_panel_img_list
            await _show_panel_img_list(context.bot, chat_id, query=None, page=new_page)
        else:
            await safe_answer(query, "❌ Image not found", show_alert=True)
        return

    if data == "panel_img_refresh_cache":
        if not is_admin:
            return
        try:
            from panel_image import clear_image_cache
            n = clear_image_cache()
            await safe_answer(query, f"✅ Cache cleared ({n} entries).", show_alert=False)
        except Exception:
            await safe_answer(query, "✅ Cache cleared", show_alert=False)
        await button_handler(update, context, "admin_settings")
        return

    # ── Button style ───────────────────────────────────────────────────────────
    if data == "admin_btn_style":
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import BUTTON_STYLE
        current_style = get_setting("button_style", BUTTON_STYLE) or BUTTON_STYLE
        await safe_edit_text(
            query, b("BUTTON STYLE") + "\n\n"
            + bq(
                f"<b>Current:</b> {current_style}\n\n"
                "<b>Math Bold:</b> 𝗦𝗧𝗔𝗧𝗦  𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧\n"
                "<b>Small Caps:</b> ꜱᴛᴀᴛꜱ  ʙʀᴏᴀᴅᴄᴀꜱᴛ"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'mathbold' else ''}𝗠𝗔𝗧𝗛 𝗕𝗢𝗟𝗗",
                    callback_data="btn_style_set_mathbold"),
                 InlineKeyboardButton(
                    f"{'✔️ ' if current_style == 'smallcaps' else ''}ꜱᴍᴀʟʟ ᴄᴀᴘꜱ",
                    callback_data="btn_style_set_smallcaps")],
                [_back_btn("admin_settings"), _close_btn()],
            ]),
        )
        return

    if data.startswith("btn_style_set_"):
        if not is_admin:
            return
        style = data[len("btn_style_set_"):]
        if style in ("mathbold", "smallcaps"):
            from database_dual import set_setting
            from core.buttons import refresh_btn_style_cache
            set_setting("button_style", style)
            refresh_btn_style_cache()
            await safe_answer(query, f"✔️ Button style set: {style}")
            await button_handler(update, context, "admin_btn_style")
        return

    # ── DB cleanup ─────────────────────────────────────────────────────────────
    if data == "dbcleanup_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query, b(small_caps("💾 database cleanup")) + "\n\n"
            + bq(small_caps("removes expired links, old sessions, and stale cache entries.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("✅ confirm cleanup"), callback_data="dbcleanup_run"),
                _back_btn("admin_back"),
            ]]),
        )
        return

    if data == "dbcleanup_run":
        if not is_admin:
            return
        try:
            from database_dual import cleanup_expired_links
            removed = cleanup_expired_links()
            await safe_edit_text(
                query, b(small_caps("✅ cleanup done!")) + "\n" + bq(small_caps(f"removed {removed} expired entries.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back"), _close_btn()]]),
            )
        except Exception as exc:
            await safe_edit_text(query, b(small_caps(f"❌ error: {e(str(exc)[:100])}")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back")]]))
        return

    # ── User features panel ────────────────────────────────────────────────────
    # ── User features help cards (4×2 grid → tap = feature card) ─────────────
    if data.startswith("uf_help:"):
        feature = data[len("uf_help:"):]
        HELP_CARDS = {
            "anime": (
                "🎌 <b>Anime Poster</b>\n\n"
                "<code>/anime Demon Slayer</code> — generate anime poster + info\n"
                "<code>/airing Jujutsu Kaisen</code> — next episode countdown\n"
                "<code>/character Tanjiro</code> — character details\n\n"
                "<i>Searches AniList for accurate info.</i>"
            ),
            "manga": (
                "📚 <b>Manga Poster</b>\n\n"
                "<code>/manga One Piece</code> — generate manga poster\n"
                "<code>/manga Berserk</code> — poster + info from AniList\n\n"
                "<i>Also searches MangaDex for cover art.</i>"
            ),
            "movie": (
                "🎬 <b>Movie Poster</b>\n\n"
                "<code>/movie Spirited Away</code> — TMDB movie poster\n"
                "<code>/tvshow Attack on Titan</code> — TV show poster\n"
                "<code>/search Naruto</code> — search all sources at once\n\n"
                "<i>Requires TMDB API to be configured.</i>"
            ),
            "character": (
                "👤 <b>Character Info</b>\n\n"
                "<code>/character Goku</code> — character details + image\n"
                "<code>/character Mikasa Ackerman</code> — full info\n\n"
                "<i>Data from AniList character database.</i>"
            ),
            "reactions": (
                "🤗 <b>Reaction GIFs</b>\n\n"
                "<code>/hug @user</code> — send a hug GIF\n"
                "<code>/slap @user</code> — slap someone\n"
                "<code>/kiss @user</code> — send a kiss\n"
                "<code>/pat @user</code> — pat someone\n"
                "<code>/punch @user</code> — punch!\n"
                "<code>/couple</code> — couple of the day GIF\n\n"
                "<i>Reply to a message or mention @user.</i>"
            ),
            "chatbot": (
                "💬 <b>AI Chatbot</b>\n\n"
                "Just <b>mention the bot</b> or <b>reply</b> to its message in a group.\n"
                "In DM — just type anything!\n\n"
                "<i>Powered by Gemini + Groq. Remembers conversation context.</i>"
            ),
            "notes": (
                "📝 <b>Notes System</b>\n\n"
                "<code>/save notename content</code> — save a note\n"
                "<code>/get notename</code> — retrieve a note\n"
                "<code>/notes</code> — list all saved notes\n"
                "<code>#notename</code> — trigger note by hashtag\n\n"
                "<i>Notes are saved per group.</i>"
            ),
            "group": (
                "⚖️ <b>Group Management</b>\n\n"
                "<code>/warn @user reason</code> — warn a user\n"
                "<code>/warns @user</code> — check warnings\n"
                "<code>/unwarn @user</code> — remove a warning\n"
                "<code>/rules</code> — show group rules\n"
                "<code>/afk reason</code> — set AFK status\n\n"
                "<i>Most mod commands require admin rights.</i>"
            ),
        }
        card_text = HELP_CARDS.get(feature, "<b>Feature not found.</b>")
        back_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="user_features_panel"),
            InlineKeyboardButton("✖ Close", callback_data="close_message"),
        ]])
        await _smart_edit(card_text, back_kb)
        return

    if data == "user_features_panel":
        from handlers.user_features import send_user_features_panel
        await send_user_features_panel(update, context, query=query, chat_id=chat_id)
        return

    if data.startswith("user_features_"):
        try:
            page = int(data.split("_")[-1])
        except Exception:
            page = 0
        from handlers.user_features import send_user_features_panel
        await send_user_features_panel(update, context, query, chat_id, page)
        return

    if data.startswith("feat_"):
        if not is_admin:
            return
        feat_map = {
            "feat_couple":       ("/couple", "Tag two users as a couple. Usage: /couple @user1 @user2"),
            "feat_slap":         ("/slap", "Slap someone! Reply to a message with /slap"),
            "feat_hug":          ("/hug", "Hug someone! Reply to a message with /hug"),
            "feat_kiss":         ("/kiss", "Kiss someone! Reply to a message with /kiss"),
            "feat_pat":          ("/pat", "Pat someone! Reply to a message with /pat"),
            "feat_inline_search":("@Bot query", "Inline anime search — type @YourBot in any chat then anime name."),
            "feat_reactions":    ("/react", "Reaction GIFs. Reply to a message with /slap /hug /pat etc."),
            "feat_chatbot":      ("/chatbot on|off", "Toggle AI chatbot mode in a group."),
            "feat_truth_dare":   ("/truth or /dare", "Play Truth or Dare in a group!"),
            "feat_notes":        ("/save notename text", "Save group notes. Retrieve with #notename"),
            "feat_warns":        ("/warn @user", "Warn users. Also: /unwarn /warns /resetwarns"),
            "feat_muting":       ("/mute @user", "Mute users. Also: /unmute /tmute"),
            "feat_bans":         ("/ban @user", "Ban users. Also: /unban /tban /sban"),
            "feat_rules":        ("/setrules | /rules", "Set and show group rules."),
            "feat_airing":       ("/airing Demon Slayer", "Check next episode airing time from AniList."),
            "feat_character":    ("/character Tanjiro", "Get anime character info from AniList."),
            "feat_anime_info":   ("/anime Naruto", "Get landscape poster + full anime info."),
            "feat_afk":          ("/afk reason", "Set AFK status. Bot auto-replies when tagged."),
        }
        if data == "feat_chatbot":
            from database_dual import get_setting as _gs_feat, set_setting as _ss_feat
            chat_key = f"chatbot_{chat_id}"
            current_chatbot = (_gs_feat(chat_key, "true") or "true").lower()
            new_val_chatbot = "false" if current_chatbot == "true" else "true"
            _ss_feat(chat_key, new_val_chatbot)
            status_chatbot = small_caps("enabled ✅") if new_val_chatbot == "true" else small_caps("disabled 🔕")
            try:
                await query.answer(small_caps(f"chatbot {status_chatbot}"), show_alert=True)
            except Exception:
                pass
            return
        info = feat_map.get(data, (data.replace("feat_", "/"), "Feature command."))
        cmd_feat, desc_feat = info
        try:
            # Show feature help as proper panel with back button
            try:
                await query.answer()
            except Exception:
                pass
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    b(small_caps(f"✨ {cmd_feat}")) + "\n\n"
                    + bq(small_caps(desc_feat)) + "\n\n"
                    + "<i>" + small_caps("use this command in any group where bot is admin") + "</i>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 " + small_caps("back to features"), callback_data="adm_page_2")],
                    [InlineKeyboardButton("✖ " + small_caps("close"), callback_data="close_message")],
                ]),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return

    if data == "about_bot":
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.config import BOT_NAME
        text = (b(f" About {e(BOT_NAME)}") + "\n\n"
            + bq(b("🤖 Powered by @Beat_Anime_Ocean\n\n") + b("Features:\n") + "• Force-Sub channels"))
        await safe_send_message(
            context.bot, chat_id, text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎌 Anime Channel", url=PUBLIC_ANIME_CHANNEL_URL)],
                [_back_btn("user_back")],
            ]),
        )
        return

    if data == "user_back":
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.start import start
        await start(update, context)
        return

    if data == "user_help":
        from handlers.help import help_command
        await help_command(update, context)
        return

    # ── Channel welcome ────────────────────────────────────────────────────────
    if data == "admin_channel_welcome":
        if not is_admin:
            return
        from handlers.channels import show_channel_welcome_panel
        await show_channel_welcome_panel(context, chat_id, query)
        return

    if data == "cw_add":
        if not is_admin:
            return
        user_states[uid] = "CW_WAITING_CHANNEL_ID"
        await safe_edit_text(
            query, b("📣 add channel welcome") + "\n\n"
            + bq(b(small_caps("send the channel id, @username, or forward a post:"))),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_list":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("no channels configured yet."))
            return
        text = b("📋 " + small_caps("configured channel welcomes:")) + "\n\n"
        for ch_id_l, enabled_l, wtext_l in channels:
            icon = "🟢" if enabled_l else "🔴"
            text += f"{icon} <code>{ch_id_l}</code>\n"
            if wtext_l:
                text += f"   {e((wtext_l)[:60])}…\n"
        await safe_edit_text(
            query, text,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_channel_welcome"), _close_btn()]]),
        )
        return

    if data == "cw_remove_menu":
        if not is_admin:
            return
        try:
            from database_dual import get_all_channel_welcomes
            channels = get_all_channel_welcomes()
        except Exception:
            channels = []
        if not channels:
            await safe_answer(query, small_caps("nothing to remove."))
            return
        btns = [[InlineKeyboardButton(f"🗑 {ch_id_r}", callback_data=f"cw_del_{ch_id_r}")]
                for ch_id_r, _, _ in channels[:10]]
        btns.append([_back_btn("admin_channel_welcome"), _close_btn()])
        await safe_edit_text(
            query, b(small_caps("select channel to remove:")),
            reply_markup=InlineKeyboardMarkup(btns),
        )
        return

    if data.startswith("cw_edit_"):
        if not is_admin:
            return
        ch_id_ce = int(data[len("cw_edit_"):])
        try:
            from database_dual import get_channel_welcome
            s = get_channel_welcome(ch_id_ce) or {}
        except Exception:
            s = {}
        wtext_ce   = s.get("welcome_text", "")
        img_fid_ce = s.get("image_file_id", "")
        img_url_ce = s.get("image_url", "")
        btns_json  = s.get("buttons", [])
        enabled_ce = s.get("enabled", True)
        text_ce = (
            b(small_caps(f"edit channel welcome: {ch_id_ce}")) + "\n\n"
            + bq(
                f"<b>{small_caps('enabled')}:</b> {'🟢 yes' if enabled_ce else '🔴 no'}\n"
                f"<b>{small_caps('text')}:</b> {e((wtext_ce)[:60]) if wtext_ce else small_caps('not set')}\n"
                f"<b>{small_caps('image')}:</b> {'✅ set' if img_fid_ce or img_url_ce else small_caps('not set')}\n"
                f"<b>{small_caps('buttons')}:</b> {len(btns_json)} {small_caps('configured')}"
            )
        )
        context.user_data["cw_editing_channel"] = ch_id_ce
        edit_kb = [
            [InlineKeyboardButton(small_caps("✏️ set text"),    callback_data=f"cw_settext_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("🖼 set image"),   callback_data=f"cw_setimg_{ch_id_ce}")],
            [InlineKeyboardButton(small_caps("🔘 set buttons"), callback_data=f"cw_setbtns_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("⚡ toggle on/off"), callback_data=f"cw_toggle_{ch_id_ce}")],
            [InlineKeyboardButton(small_caps("👁 preview"),     callback_data=f"cw_preview_{ch_id_ce}"),
             InlineKeyboardButton(small_caps("🗑 remove"),      callback_data=f"cw_del_{ch_id_ce}")],
            [_back_btn("admin_channel_welcome"), _close_btn()],
        ]
        await safe_edit_text(query, text_ce, reply_markup=InlineKeyboardMarkup(edit_kb))
        return

    if data.startswith("cw_settext_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_settext_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_TEXT
        await safe_edit_text(
            query, b(small_caps("send the welcome text:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setbtns_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setbtns_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = CW_SET_BUTTONS
        await safe_edit_text(
            query, b(small_caps("send button config (one per line: Label - https://url):")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_setimg_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_setimg_"):])
        context.user_data["cw_editing_channel"] = ch_id
        user_states[uid] = "CW_AWAITING_IMAGE"
        await safe_edit_text(
            query, b(small_caps("send welcome image:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn(f"cw_edit_{ch_id}"), _close_btn()]]),
        )
        return

    if data.startswith("cw_preview_"):
        if not is_admin:
            return
        ch_id = int(data[len("cw_preview_"):])
        from handlers.channels import send_channel_welcome
        asyncio.create_task(send_channel_welcome(context.bot, chat_id, ch_id))
        await safe_answer(query, small_caps("preview sent to you in dm."))
        return

    if data.startswith("cw_del_"):
        if not is_admin:
            return
        try:
            from database_dual import delete_channel_welcome
            ch_id = int(data[len("cw_del_"):])
            delete_channel_welcome(ch_id)
            await safe_answer(query, small_caps(f"removed channel {ch_id}"))
            from handlers.channels import show_channel_welcome_panel
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    if data.startswith("cw_toggle_"):
        if not is_admin:
            return
        try:
            from database_dual import get_channel_welcome, set_channel_welcome
            ch_id = int(data[len("cw_toggle_"):])
            s = get_channel_welcome(ch_id)
            new_state = not (s.get("enabled", True) if s else True)
            set_channel_welcome(ch_id, enabled=new_state)
            await safe_answer(query, small_caps(f"welcome {'enabled' if new_state else 'disabled'}"))
            from handlers.channels import show_channel_welcome_panel
            await show_channel_welcome_panel(context, chat_id, query)
        except Exception as exc:
            await safe_answer(query, f"error: {str(exc)[:60]}", show_alert=True)
        return

    # ── Poster commands from panel ─────────────────────────────────────────────
    if data.startswith("poster_cmd_"):
        if not is_admin:
            return
        tmpl = data.replace("poster_cmd_", "")
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            f"<b>🖼 Poster Command:</b> <code>/{tmpl}</code>\n\n"
            f"<b>Usage:</b> /{tmpl} &lt;title&gt;\n"
            f"<b>Example:</b> <code>/{tmpl} Demon Slayer</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "admin_cmd_list":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.help import cmd_command
        await cmd_command(update, context)
        return

    # ── Anime module callbacks ─────────────────────────────────────────────────
    if data.startswith(("anpick_", "lang_", "size_", "anthmb_")):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc:
            logger.debug(f"anime callback error: {exc}")
        return

    # ── Filter settings ────────────────────────────────────────────────────────
    if data == "admin_filter_settings":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from core.filters_system import filters_config
        dm_on  = filters_config["global"].get("dm", True)
        grp_on = filters_config["global"].get("group", True)

        # Build channel+anime list from DB
        ch_lines = ""
        try:
            from database_dual import get_all_force_sub_channels, get_all_anime_channel_links
            channels = get_all_force_sub_channels() or []
            links    = get_all_anime_channel_links() or []
            # Map channel_id → anime titles
            ch_anime: dict = {}
            for row in links:
                # row = (id, anime_title, channel_id, channel_title, link_id, created_at)
                an_title = row[1] if len(row) > 1 else ""
                cid      = row[2] if len(row) > 2 else ""
                if an_title and cid:
                    ch_anime.setdefault(str(cid), []).append(an_title.title())
            for ch in channels:
                cid_v  = ch[0] if isinstance(ch, (list, tuple)) else ch.get("channel_id", "")
                cname  = ch[1] if isinstance(ch, (list, tuple)) else ch.get("channel_title", "")
                animes = ch_anime.get(str(cid_v), [])
                an_str = ", ".join(animes[:3]) if animes else small_caps("no anime linked")
                ch_lines += f"• <b>{e(str(cname))}</b>: <i>{e(an_str)}</i>\n"
        except Exception:
            ch_lines = bq(small_caps("could not load channel list"))

        text = (
            b(small_caps("🔧 filter settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('DM Filter')}:</b> {'✅ ON' if dm_on else '❌ OFF'}\n"
                f"<b>{small_caps('Group Filter')}:</b> {'✅ ON' if grp_on else '❌ OFF'}"
            )
            + (f"\n\n<b>{small_caps('📢 channels & anime:')}</b>\n" + ch_lines if ch_lines else "")
        )
        keyboard = [
            [bold_button(small_caps("toggle dm filter"),    callback_data="filter_toggle_dm"),
             bold_button(small_caps("toggle group filter"), callback_data="filter_toggle_group")],
            [bold_button(small_caps("📢 manage channels"),  callback_data="manage_force_sub")],
            [bold_button(small_caps("🎌 channel anime links"), callback_data="admin_anime_links")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_send_message(context.bot, chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "admin_anime_links":
        if not is_admin:
            return
        try:
            from database_dual import get_all_links
            raw = get_all_links(limit=100, offset=0)
            seen = set()
            rows_al = []
            for row in (raw or []):
                t = (row[2] or "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    rows_al.append(row)
        except Exception:
            rows_al = []
        text_al = b(small_caps(f"🎌 filter keywords from generated links ({len(rows_al)})")) + "\n\n"
        if rows_al:
            for row in rows_al[:20]:
                ch_id_al   = row[1]
                ch_title_al = row[2] or ch_id_al
                text_al += f"• <b>{html.escape(str(ch_title_al))}</b> → <code>{html.escape(str(ch_id_al))}</code>\n"
        else:
            text_al += bq(small_caps(
                "no links yet.\n\n"
                "use gen link in the channels panel to create one.\n"
                "the link title automatically becomes a filter keyword."
            ))
        text_al += (
            "\n\n" + bq(
                b(small_caps("how it works:")) + "\n"
                + small_caps("generate a channel link → the title becomes a filter keyword. "
                             "when any user types that title in a group, they get a poster + join button.")
            )
        )
        await safe_send_message(
            context.bot, chat_id, text_al,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    if data.startswith("del_acl_"):
        await safe_answer(query, small_caps("use /removechannel or manage links from the channels panel."), show_alert=True)
        return

    if data == "filter_toggle_dm":
        if not is_admin:
            return
        from core.filters_system import filters_config
        filters_config["global"]["dm"] = not filters_config["global"].get("dm", True)
        await safe_answer(query, f"DM filter: {'ON' if filters_config['global']['dm'] else 'OFF'}")
        await button_handler(update, context, "admin_filter_settings")
        return

    if data == "filter_toggle_group":
        if not is_admin:
            return
        from core.filters_system import filters_config
        filters_config["global"]["group"] = not filters_config["global"].get("group", True)
        await safe_answer(query, f"Group filter: {'ON' if filters_config['global']['group'] else 'OFF'}")
        await button_handler(update, context, "admin_filter_settings")
        return

    # ── Admin clear image cache ────────────────────────────────────────────────
    if data == "admin_clear_img_cache":
        if not is_admin:
            return
        try:
            from panel_image import clear_image_cache
            count = clear_image_cache()
            await safe_answer(query, f"♻️ Cleared {count} cached panel images")
        except Exception:
            await safe_answer(query, "♻️ Cache cleared")
        return

    # ── Fsub forward source ────────────────────────────────────────────────────
    if data == "fsub_fwd_source":
        if not is_admin:
            return
        try:
            await query.delete_message()
        except Exception:
            pass
        from handlers.admin_panel import show_fwd_source_panel
        await show_fwd_source_panel(context, chat_id)
        return

    if data == "fwd_set_chat":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_FWD_CHAT"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(context.bot, chat_id, b(" Set Forward Source Chat") + "\n\n"
            + bq("Send the channel/group ID or @username."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]))
        return

    if data == "fwd_set_msgid":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_FWD_MSGID"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(context.bot, chat_id, b(" Set Forward Message ID") + "\n\n"
            + bq("Send the message ID (number)."),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source")]]))
        return

    if data == "fwd_test":
        if not is_admin:
            return
        from database_dual import get_setting
        fwd_chat = get_setting("fwd_source_chat", "")
        fwd_msg_id = get_setting("fwd_source_msg_id", "")
        fwd_with_tag = get_setting("fwd_with_tag", "true") == "true"
        if not fwd_chat or not fwd_msg_id:
            await safe_answer(query, "❌ Set source chat and message ID first!", show_alert=True)
            return
        try:
            msg_id_int = int(fwd_msg_id)
            if fwd_with_tag:
                await context.bot.forward_message(chat_id=chat_id, from_chat_id=fwd_chat, message_id=msg_id_int)
            else:
                await context.bot.copy_message(chat_id=chat_id, from_chat_id=fwd_chat, message_id=msg_id_int)
            await safe_answer(query, "✅ Test forward sent!")
        except Exception as _fe:
            await safe_answer(query, f"❌ Failed: {str(_fe)[:80]}", show_alert=True)
        return

    if data == "fwd_toggle_tag":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("fwd_with_tag", "true")
        new_val = "false" if current == "true" else "true"
        set_setting("fwd_with_tag", new_val)
        await safe_answer(query, f"📨 Forward Tag: {'ON' if new_val == 'true' else 'OFF'}")
        return

    if data == "fwd_toggle_private":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        current = get_setting("fwd_private_channel", "false")
        new_val = "false" if current == "true" else "true"
        set_setting("fwd_private_channel", new_val)
        label = "ON (private channels enabled)" if new_val == "true" else "OFF"
        try:
            await query.answer(f"🔒 Private Channel: {label}", show_alert=True)
        except Exception:
            pass
        return

    # ── fp_set_join_btn_* ──────────────────────────────────────────────────────
    if data.startswith("fp_set_join_btn_"):
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import JOIN_BTN_TEXT
        current = get_setting("env_JOIN_BTN_TEXT", "") or JOIN_BTN_TEXT
        user_states[uid] = "AWAITING_JOIN_BTN_TEXT"
        await safe_edit_text(
            query, b(small_caps("✏️ set join button text")) + "\n\n"
            + bq(b(small_caps("current: ")) + f"<code>{e(current)}</code>\n\n" + small_caps("send new button text:")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_filter_poster"), _close_btn()]]),
        )
        return


    # ── Module info buttons (admin panel page 5) ───────────────────────────────
    if data.startswith("mod_"):
        if not is_admin:
            return
        # Map callback → (display name, commands list, description)
        _MOD_INFO = {
            "mod_admin":       ("Admins",          ["/pinned", "/invitelink", "/setgtitle", "/setdesc", "/setgpic"],
                                "Group admin tools — pin messages, manage group title, description, and profile picture."),
            "mod_antiflood":   ("Anti-Flood",       ["/setflood", "/flood"],
                                "Auto-kick/mute/ban users who send too many messages too fast."),
            "mod_approve":     ("Approve",          ["/approve", "/unapprove", "/approved", "/unapproveall"],
                                "Approve trusted users so they bypass blacklists and other restrictions."),
            "mod_blacklist":   ("Blacklist",        ["/addblacklist", "/unblacklist", "/blacklist"],
                                "Auto-delete messages containing banned words or phrases."),
            "mod_blsticker":   ("BL Stickers",      ["/blsticker", "/unblsticker", "/blstickermode"],
                                "Blacklist specific stickers from being sent in the group."),
            "mod_chatbot":     ("Chatbot",          ["/chatbot"],
                                "AI chatbot — responds when tagged or replied to. Toggle on/off per group."),
            "mod_cleaner":     ("Cleaner",          ["/cleanblue on/off"],
                                "Auto-delete blue text (service messages) like join/leave/pin notifications."),
            "mod_connection":  ("Connection",       ["/connect", "/disconnect", "/connection"],
                                "Connect to a group from PM to manage it without being in the chat."),
            "mod_currency":    ("Currency",         ["/cash <amount> <from> <to>"],
                                "Live currency conversion. Example: /cash 100 USD INR"),
            "mod_custfilters": ("Filters",          ["/filter <word> <reply>", "/stop <word>", "/filters"],
                                "Custom keyword auto-replies. When someone says a word, bot responds automatically."),
            "mod_globalbans":  ("Anti-Spam",        ["/gban <user>", "/ungban", "/gbanlist"],
                                "Global ban system — banned users are blocked across all groups the bot manages."),
            "mod_imdb":        ("IMDb",             ["/imdb <title>"],
                                "Search for movie/show info from IMDb with ratings, plot, and cast."),
            "mod_locks":       ("Locks",            ["/lock <type>", "/unlock <type>", "/locktypes"],
                                "Lock specific message types (media, stickers, links, polls etc.) in groups."),
            "mod_logchannel":  ("Log Channel",      ["/setlog <channel>", "/unsetlog", "/logchannel"],
                                "Set a channel to receive logs of bans, warns, and admin actions."),
            "mod_ping":        ("Ping",             ["/ping"],
                                "Check if the bot is alive and measure response latency."),
            "mod_purge":       ("Purge",            ["/purge", "/del"],
                                "Delete multiple messages at once. Reply to a message and use /purge."),
            "mod_reporting":   ("Reports",          ["/report", "/reports on/off"],
                                "Allow users to @report messages to admins. Admins can toggle this on/off."),
            "mod_sed":         ("Sed/Regex",        ["s/old/new"],
                                "Edit messages with sed-like syntax. Reply with s/old/new to correct yourself."),
            "mod_shell":       ("Shell",            ["/shell <cmd>"],
                                "Run shell commands on the server (owner only, use with caution)."),
            "mod_speedtest":   ("Speed Test",       ["/speedtest"],
                                "Run an internet speed test on the server and report download/upload speeds."),
            "mod_stickers":    ("Stickers",         ["/kang", "/stickerid", "/getsticker", "/stickers"],
                                "Steal stickers into a pack, get sticker file IDs, and manage sticker packs."),
            "mod_tagall":      ("Tag All",          ["/tagall", "/tag"],
                                "Tag all members in a group. Admins only. Use sparingly!"),
            "mod_translator":  ("Translator",       ["/tr <lang>", "/tl <lang>"],
                                "Translate messages. Reply to any message with /tr en to translate to English."),
            "mod_truthdare":   ("Truth or Dare",    ["/truth", "/dare"],
                                "Play Truth or Dare in a group! Gets questions/dares from a built-in list."),
            "mod_ud":          ("Urban Dict",       ["/ud <word>"],
                                "Look up slang definitions from Urban Dictionary."),
            "mod_wallpaper":   ("Wallpaper",        ["/wall <query>"],
                                "Search and send wallpapers from Wallhaven directly in Telegram."),
            "mod_wiki":        ("Wikipedia",        ["/wiki <query>"],
                                "Search Wikipedia and get a summary of any topic."),
            "mod_writetool":   ("Write Tool",       ["/write <text>"],
                                "Generate a handwritten-style image of any text you send."),
            "mod_animequotes": ("Anime Quotes",     ["/quote", "/animequote"],
                                "Get random inspirational quotes from famous anime characters."),
            "mod_gettime":     ("Time",             ["/time <city>"],
                                "Get the current time in any city or timezone around the world."),
            "mod_badwords":    ("Bad Words",        ["/addword", "/rmword", "/badwords", "/wordaction"],
                                "Filter profanity and custom bad words with configurable punishments."),
        }
        info = _MOD_INFO.get(data)
        if info:
            mod_label, cmds, desc = info
            cmds_text = "\n".join(f"• <code>{html.escape(c)}</code>" for c in cmds) if cmds else small_caps("see /help for commands")
            panel_msg = (
                b(f"📦 {small_caps(mod_label)}") + "\n\n"
                + bq(small_caps(desc)) + "\n\n"
                + b(small_caps("commands:")) + "\n" + cmds_text + "\n\n"
                + "<i>" + small_caps("use these commands in any connected group") + "</i>"
            )
            try:
                await query.answer()
            except Exception:
                pass
            # Delete old panel, show module card with Back button
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=chat_id,
                text=panel_msg,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 " + small_caps("back to modules"), callback_data="adm_page_4")],
                    [InlineKeyboardButton("✖ " + small_caps("close"), callback_data="close_message")],
                ]),
                disable_web_page_preview=True,
            )
        else:
            try:
                await query.answer(f"Module: {data.replace('mod_', '')}", show_alert=True)
            except Exception:
                pass
        return

    if data == "inline_anim_toggle":
        from handlers.inline_handler import get_animation_enabled, set_animation_enabled
        cur = get_animation_enabled()
        set_animation_enabled(not cur)
        status = "✅ ON" if not cur else "🔕 OFF"
        await safe_answer(query, f"Loading animation: {status}")
        # Refresh the filter poster panel so the button label updates
        try:
            from filter_poster import build_filter_poster_settings_keyboard, get_filter_poster_settings_text
            await _smart_edit(
                get_filter_poster_settings_text(chat_id),
                build_filter_poster_settings_keyboard(chat_id),
            )
        except Exception:
            pass
        return

    # ── Fast inline invite link (loading animation) ───────────────────────────
    if data.startswith("inv_loading:") or data.startswith("inv_ready:"):
        from handlers.inline_handler import handle_inv_loading_callback
        await handle_inv_loading_callback(update, context)
        return

    # ── Chatbot API key panel ─────────────────────────────────────────────────
    if (data == "admin_chatbot_panel"
            or data.startswith("chatbot_gc_view:")
            or data.startswith("chatbot_gc_toggle:")
            or data.startswith("chatbot_gender_")
            or data.startswith("chatbot_gc_assign:")
            or data.startswith("chatbot_assign_set:")
            or data.startswith("chatbot_usage_stats:")
            or data == "chatbot_sets"
            or data.startswith("chatbot_set_view:")
            or data.startswith("chatbot_add_key:")
            or data == "chatbot_new_set"
            or data.startswith("chatbot_del_key:")
            or data == "chatbot_add_gc"
            # legacy compat
            or data.startswith("chatbot_add_gemini:")
            or data.startswith("chatbot_add_groq:")
            or data.startswith("chatbot_del_gemini:")
            or data.startswith("chatbot_del_groq:")):
        from handlers.chatbot_panel import handle_chatbot_panel_callback
        await handle_chatbot_panel_callback(update, context)
        return

    # ── Inline Request (from filter poster "Not found" / "Hindi not available") ──
    if data.startswith("request_anime:") or data.startswith("request_hindi:"):
        is_hindi = data.startswith("request_hindi:")
        anime_name = data.split(":", 1)[1].strip()
        # Trigger same logic as /request command with the anime name pre-filled
        try:
            from modules.animerequest import request_cmd as _req_cmd
            # Build fake context args
            context.args = anime_name.split()
            await _req_cmd(update, context)
        except Exception:
            # Fallback: show instructions
            _prefix = "Hindi dub of " if is_hindi else ""
            try:
                await query.answer(
                    f"Type: /request {anime_name}",
                    show_alert=True,
                )
            except Exception:
                pass
            try:
                await query.message.reply_text(
                    f"📩 <b>Send your request:</b>\n"
                    f"<code>/request {_prefix}{anime_name}</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return

    # ── Flood limit / window input prompts ────────────────────────────────────
    if data == "set_flood_limit":
        if not is_admin:
            return
        from database_dual import get_setting
        cur_limit = get_setting("flood_limit", "5")
        user_states[uid] = "AWAITING_FLOOD_LIMIT"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🚦 set flood message limit")) + "\n\n"
            + bq(
                small_caps(f"current: {cur_limit} messages") + "\n"
                + small_caps("send the maximum number of messages a user can send "
                             "in the flood window before being muted/banned.\n"
                             "recommended: 5–10")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_spam_settings")
            ]]),
        )
        return

    if data == "set_flood_window":
        if not is_admin:
            return
        from database_dual import get_setting
        cur_window = get_setting("flood_window_sec", "10")
        user_states[uid] = "AWAITING_FLOOD_WINDOW"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set flood detection window")) + "\n\n"
            + bq(
                small_caps(f"current: {cur_window} seconds") + "\n"
                + small_caps("send the number of seconds for the flood detection window.\n"
                             "example: 10 = if a user sends flood_limit messages in 10s, they are punished.\n"
                             "recommended: 5–15")
            ),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_spam_settings")
            ]]),
        )
        return

    # ── Rate limit / ban duration settings ────────────────────────────────────
    if data == "admin_rate_limit_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        rl_enabled  = get_setting("rate_limit_enabled", "true") == "true"
        rl_cooldown = get_setting("rate_limit_cooldown_sec", "3")
        rl_ban_dur  = get_setting("flood_ban_duration_sec", "300")
        text_rl = (
            b(small_caps("⚙️ rate limit settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('Rate Limit')}:</b> {'✅ ON' if rl_enabled else '❌ OFF'}\n"
                f"<b>{small_caps('Per-user cooldown')}:</b> {rl_cooldown}s\n"
                f"<b>{small_caps('Flood ban duration')}:</b> {rl_ban_dur}s\n\n"
                + small_caps("rate limit prevents the same user from spamming commands. "
                             "flood ban silences users who hit the flood limit.")
            )
        )
        rl_kb = [
            [_btn(small_caps("toggle rate limit"), "toggle_rate_limit"),
             _btn(small_caps("set cooldown"), "set_rl_cooldown")],
            [_btn(small_caps("set ban duration"), "set_flood_ban_dur")],
            [_back_btn("admin_spam_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_rl, reply_markup=InlineKeyboardMarkup(rl_kb))
        return

    if data == "toggle_rate_limit":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("rate_limit_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("rate_limit_enabled", new_val)
        await safe_answer(query, small_caps(f"rate limit: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_rate_limit_settings")
        return

    if data == "set_rl_cooldown":
        if not is_admin:
            return
        from database_dual import get_setting
        cur = get_setting("rate_limit_cooldown_sec", "3")
        user_states[uid] = "AWAITING_RL_COOLDOWN"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set per-user command cooldown")) + "\n\n"
            + bq(small_caps(f"current: {cur}s\nsend seconds between allowed commands (e.g. 3):")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_rate_limit_settings")]]),
        )
        return

    if data == "set_flood_ban_dur":
        if not is_admin:
            return
        from database_dual import get_setting
        cur = get_setting("flood_ban_duration_sec", "300")
        user_states[uid] = "AWAITING_FLOOD_BAN_DUR"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🔇 set flood ban duration")) + "\n\n"
            + bq(small_caps(f"current: {cur}s\nsend seconds the mute/ban lasts (0 = permanent):")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_rate_limit_settings")]]),
        )
        return

    # ── Notification / alert settings ─────────────────────────────────────────
    if data == "admin_notification_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        notif_new_user  = get_setting("notify_new_user", "false") == "true"
        notif_ban       = get_setting("notify_ban", "true") == "true"
        notif_error     = get_setting("notify_error", "true") == "true"
        text_notif = (
            b(small_caps("🔔 notification settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('New user join')}:</b> {'✅' if notif_new_user else '❌'}\n"
                f"<b>{small_caps('Ban/unban actions')}:</b> {'✅' if notif_ban else '❌'}\n"
                f"<b>{small_caps('Error alerts')}:</b> {'✅' if notif_error else '❌'}"
            )
        )
        notif_kb = [
            [_btn(f"{'✅' if notif_new_user else '❌'} " + small_caps("new user"), "toggle_notif_new_user"),
             _btn(f"{'✅' if notif_ban else '❌'} " + small_caps("bans"), "toggle_notif_ban")],
            [_btn(f"{'✅' if notif_error else '❌'} " + small_caps("errors"), "toggle_notif_error")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_notif, reply_markup=InlineKeyboardMarkup(notif_kb))
        return

    for _notif_key, _notif_cb in (
        ("notify_new_user", "toggle_notif_new_user"),
        ("notify_ban",      "toggle_notif_ban"),
        ("notify_error",    "toggle_notif_error"),
    ):
        if data == _notif_cb:
            if not is_admin:
                return
            from database_dual import get_setting, set_setting
            _cur_n = get_setting(_notif_key, "true")
            _new_n = "false" if _cur_n == "true" else "true"
            set_setting(_notif_key, _new_n)
            await safe_answer(query, small_caps(f"{'enabled' if _new_n == 'true' else 'disabled'}!"))
            await button_handler(update, context, "admin_notification_settings")
            return

    # ── Advanced database panel ────────────────────────────────────────────────
    if data == "admin_db_panel":
        if not is_admin:
            return
        try:
            from database_dual import db_manager, get_user_count, get_links_count
            user_count = get_user_count()
            link_count = get_links_count() if callable(get_links_count) else "N/A"
        except Exception:
            user_count = link_count = "N/A"
        text_db = (
            b(small_caps("💾 database panel")) + "\n\n"
            + bq(
                f"<b>{small_caps('total users')}:</b> {code(str(user_count))}\n"
                f"<b>{small_caps('total links')}:</b> {code(str(link_count))}\n\n"
                + small_caps("choose an action:")
            )
        )
        db_kb = [
            [_btn(small_caps("🧹 cleanup expired"), "dbcleanup_confirm"),
             _btn(small_caps("📤 export users"), "admin_export_users_quick")],
            [_btn(small_caps("📥 import users"), "admin_import_users"),
             _btn(small_caps("📥 import links"), "admin_import_links")],
            [_btn(small_caps("🔍 search user"), "um_search_user"),
             _btn(small_caps("🚫 banned users"), "um_banned_list")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_db, reply_markup=InlineKeyboardMarkup(db_kb))
        return

    # ── Scheduled broadcast cancel ─────────────────────────────────────────────
    if data == "broadcast_cancel_scheduled":
        if not is_admin:
            return
        context.user_data.pop("scheduled_broadcast_time", None)
        context.user_data.pop("scheduled_broadcast_msg", None)
        user_states.pop(uid, None)
        await safe_answer(query, small_caps("scheduled broadcast cancelled."))
        from handlers.admin_panel import send_admin_menu
        await send_admin_menu(chat_id, context, query)
        return

    # ── Link management extras ─────────────────────────────────────────────────
    if data == "admin_link_manager":
        if not is_admin:
            return
        try:
            from database_dual import get_links_count, get_all_force_sub_channels
            total_links = get_links_count()
            channels = get_all_force_sub_channels()
        except Exception:
            total_links, channels = 0, []
        text_lm = (
            b(small_caps("🔗 link manager")) + "\n\n"
            + bq(
                f"<b>{small_caps('total links')}:</b> {code(str(total_links))}\n"
                f"<b>{small_caps('total channels')}:</b> {code(str(len(channels)))}"
            )
        )
        lm_kb = [
            [_btn(small_caps("🔗 generate link"), "generate_links"),
             _btn(small_caps("📋 all links"), "admin_show_links")],
            [_btn(small_caps("📊 link stats"), "fsub_link_stats"),
             _btn(small_caps("🎌 anime links"), "admin_anime_links")],
            [_btn(small_caps("📢 channels panel"), "manage_force_sub")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_lm, reply_markup=InlineKeyboardMarkup(lm_kb))
        return

    # ── Inline search settings ─────────────────────────────────────────────────
    if data == "admin_inline_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        inline_on = get_setting("inline_search_enabled", "true") == "true"
        inline_anim = True
        try:
            from handlers.inline_handler import get_animation_enabled
            inline_anim = get_animation_enabled()
        except Exception:
            pass
        text_is = (
            b(small_caps("🔍 inline search settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('inline search')}:</b> {'✅ ON' if inline_on else '❌ OFF'}\n"
                f"<b>{small_caps('loading animation')}:</b> {'✅ ON' if inline_anim else '❌ OFF'}\n\n"
                + small_caps("users can search anime in any chat by typing @BotUsername followed by a title.")
            )
        )
        is_kb = [
            [_btn(f"{'✅' if inline_on else '❌'} " + small_caps("toggle inline"),
                  "toggle_inline_search"),
             _btn(f"{'✅' if inline_anim else '❌'} " + small_caps("animation"),
                  "inline_anim_toggle")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_is, reply_markup=InlineKeyboardMarkup(is_kb))
        return

    if data == "toggle_inline_search":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("inline_search_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("inline_search_enabled", new_val)
        await safe_answer(query, small_caps(f"inline search: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_inline_settings")
        return

    # ── Welcome message settings ───────────────────────────────────────────────
    if data == "admin_welcome_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        wlc_enabled = get_setting("welcome_enabled", "true") == "true"
        wlc_text    = get_setting("welcome_text", "") or small_caps("(using default)")
        wlc_media   = get_setting("welcome_media_url", "") or small_caps("(none)")
        text_wlc = (
            b(small_caps("👋 welcome message settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('status')}:</b> {'✅ enabled' if wlc_enabled else '❌ disabled'}\n"
                f"<b>{small_caps('text preview')}:</b> {e(wlc_text[:80])}\n"
                f"<b>{small_caps('media')}:</b> {e(wlc_media[:60])}"
            )
        )
        wlc_kb = [
            [_btn(f"{'✅' if wlc_enabled else '❌'} " + small_caps("toggle"),
                  "toggle_welcome_enabled"),
             _btn(small_caps("✏️ set text"), "set_welcome_text")],
            [_btn(small_caps("🖼 set media"), "set_welcome_media"),
             _btn(small_caps("🔘 set buttons"), "set_welcome_buttons")],
            [_btn(small_caps("👁 preview"), "preview_welcome"),
             _btn(small_caps("♻️ reset default"), "reset_welcome")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_wlc, reply_markup=InlineKeyboardMarkup(wlc_kb))
        return

    if data == "toggle_welcome_enabled":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("welcome_enabled", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("welcome_enabled", new_val)
        await safe_answer(query, small_caps(f"welcome: {'enabled' if new_val == 'true' else 'disabled'}"))
        await button_handler(update, context, "admin_welcome_settings")
        return

    if data == "set_welcome_text":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_WELCOME_TEXT"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("✏️ set welcome message")) + "\n\n"
            + bq(small_caps(
                "send the welcome text. you can use html formatting.\n"
                "variables: {first_name}, {username}, {chat_title}\n\n"
                "example: welcome {first_name} to {chat_title}!"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_welcome_settings"), _close_btn()]]),
        )
        return

    if data == "set_welcome_media":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_WELCOME_MEDIA"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🖼 set welcome media")) + "\n\n"
            + bq(small_caps(
                "send a photo, gif, or video to use as welcome media.\n"
                "send /clear to remove media and use text-only welcome."
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_welcome_settings"), _close_btn()]]),
        )
        return

    if data == "set_welcome_buttons":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_WELCOME_BUTTONS"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🔘 set welcome buttons")) + "\n\n"
            + bq(small_caps(
                "send button config, one per line:\n"
                "format: Button Label - https://url\n\n"
                "example:\n"
                "join our channel - https://t.me/myChannel\n"
                "rules - https://t.me/myChannel/5"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_welcome_settings"), _close_btn()]]),
        )
        return

    if data == "preview_welcome":
        if not is_admin:
            return
        from database_dual import get_setting
        wlc_text = get_setting("welcome_text", "") or small_caps("welcome to {chat_title}, {first_name}!")
        preview = wlc_text.replace("{first_name}", "Demo User") \
                          .replace("{username}", "@demo_user") \
                          .replace("{chat_title}", "My Channel")
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("👁 welcome preview")) + "\n\n" + bq(preview),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_welcome_settings"), _close_btn()]]),
        )
        return

    if data == "reset_welcome":
        if not is_admin:
            return
        from database_dual import set_setting
        set_setting("welcome_text", "")
        set_setting("welcome_media_url", "")
        set_setting("welcome_buttons", "[]")
        await safe_answer(query, small_caps("welcome reset to default."))
        await button_handler(update, context, "admin_welcome_settings")
        return

    # ── Goodbye message settings ───────────────────────────────────────────────
    if data == "admin_goodbye_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        bye_enabled = get_setting("goodbye_enabled", "false") == "true"
        bye_text    = get_setting("goodbye_text", "") or small_caps("(using default)")
        text_bye = (
            b(small_caps("👋 goodbye message settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('status')}:</b> {'✅ enabled' if bye_enabled else '❌ disabled'}\n"
                f"<b>{small_caps('text preview')}:</b> {e(bye_text[:80])}"
            )
        )
        bye_kb = [
            [_btn(f"{'✅' if bye_enabled else '❌'} " + small_caps("toggle"),
                  "toggle_goodbye_enabled"),
             _btn(small_caps("✏️ set text"), "set_goodbye_text")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_bye, reply_markup=InlineKeyboardMarkup(bye_kb))
        return

    if data == "toggle_goodbye_enabled":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("goodbye_enabled", "false")
        new_val = "false" if cur == "true" else "true"
        set_setting("goodbye_enabled", new_val)
        await safe_answer(query, small_caps(f"goodbye: {'enabled' if new_val == 'true' else 'disabled'}"))
        await button_handler(update, context, "admin_goodbye_settings")
        return

    if data == "set_goodbye_text":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_GOODBYE_TEXT"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("✏️ set goodbye message")) + "\n\n"
            + bq(small_caps(
                "send the goodbye text. you can use html formatting.\n"
                "variables: {first_name}, {username}, {chat_title}\n\n"
                "example: goodbye {first_name}, hope to see you again!"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_goodbye_settings"), _close_btn()]]),
        )
        return

    # ── TMDB settings ──────────────────────────────────────────────────────────
    if data == "admin_tmdb_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        import os as _os
        tmdb_key = get_setting("env_TMDB_API_KEY", _os.getenv("TMDB_API_KEY", "")) or ""
        has_key = bool(tmdb_key.strip())
        text_tmdb = (
            b(small_caps("🎬 tmdb settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('TMDB API Key')}:</b> {'✅ set' if has_key else '❌ not set'}\n\n"
                + small_caps(
                    "tmdb is used for movie and tv show posters and info.\n"
                    "get a free api key at: themoviedb.org/settings/api"
                )
            )
        )
        tmdb_kb = [
            [_btn(small_caps("🔑 set api key"), "env_edit_TMDB_API_KEY"),
             _btn(small_caps("🧪 test tmdb"), "tmdb_test")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_tmdb, reply_markup=InlineKeyboardMarkup(tmdb_kb))
        return

    if data == "tmdb_test":
        if not is_admin:
            return
        await safe_answer(query, small_caps("testing tmdb..."))
        try:
            from api.tmdb import TMDBClient
            result = TMDBClient.test_connection()
            msg = small_caps("✅ tmdb connection successful!") if result else small_caps("❌ tmdb test failed. check your api key.")
        except Exception as exc:
            msg = small_caps(f"❌ error: {str(exc)[:60]}")
        await safe_answer(query, msg, show_alert=True)
        return

    # ── AniList settings ───────────────────────────────────────────────────────
    if data == "admin_anilist_settings":
        if not is_admin:
            return
        text_al = (
            b(small_caps("🎌 anilist settings")) + "\n\n"
            + bq(
                small_caps("anilist is used for anime/manga info, cover art, and character data.\n\n"
                           "anilist api is free and requires no key — just works!\n\n"
                           "if you experience rate limits, consider adding delays.")
            )
        )
        al_kb = [
            [_btn(small_caps("🧪 test anilist"), "anilist_test")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_al, reply_markup=InlineKeyboardMarkup(al_kb))
        return

    if data == "anilist_test":
        if not is_admin:
            return
        await safe_answer(query, small_caps("testing anilist..."))
        try:
            from api.anilist import AniListClient
            result = AniListClient.search_anime("Naruto", limit=1)
            msg = small_caps("✅ anilist working!") if result else small_caps("⚠️ anilist returned no results.")
        except Exception as exc:
            msg = small_caps(f"❌ error: {str(exc)[:60]}")
        await safe_answer(query, msg, show_alert=True)
        return

    # ── Content blocklist settings ─────────────────────────────────────────────
    if data == "admin_blocklist_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        bl_enabled = get_setting("content_blocklist_enabled", "false") == "true"
        bl_words   = get_setting("content_blocklist_words", "") or small_caps("(none)")
        text_bl = (
            b(small_caps("🚫 content blocklist")) + "\n\n"
            + bq(
                f"<b>{small_caps('status')}:</b> {'✅ enabled' if bl_enabled else '❌ disabled'}\n"
                f"<b>{small_caps('blocked words')}:</b> {e(bl_words[:80])}\n\n"
                + small_caps(
                    "if a search query contains a blocked word, "
                    "the bot will decline to search for it."
                )
            )
        )
        bl_kb = [
            [_btn(f"{'✅' if bl_enabled else '❌'} " + small_caps("toggle"),
                  "toggle_content_blocklist"),
             _btn(small_caps("✏️ edit words"), "set_blocklist_words")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_bl, reply_markup=InlineKeyboardMarkup(bl_kb))
        return

    if data == "toggle_content_blocklist":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("content_blocklist_enabled", "false")
        new_val = "false" if cur == "true" else "true"
        set_setting("content_blocklist_enabled", new_val)
        await safe_answer(query, small_caps(f"content blocklist: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_blocklist_settings")
        return

    if data == "set_blocklist_words":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_BLOCKLIST_WORDS"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🚫 set content blocklist words")) + "\n\n"
            + bq(small_caps(
                "send comma-separated words to block from searches:\n"
                "example: word1, word2, phrase here\n\n"
                "send /clear to remove all blocked words."
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_blocklist_settings"), _close_btn()]]),
        )
        return

    # ── Analytics / Search stats ───────────────────────────────────────────────
    if data == "admin_analytics":
        if not is_admin:
            return
        try:
            from database_dual import get_top_search_analytics
            top_searches = get_top_search_analytics(limit=5) or []
        except Exception:
            top_searches = []
        try:
            from database_dual import get_user_count
            total_users = get_user_count()
        except Exception:
            total_users = "N/A"
        text_ana = (
            b(small_caps("📊 analytics & insights")) + "\n\n"
            + bq(
                f"<b>{small_caps('total users')}:</b> {code(str(total_users))}\n\n"
                + "<b>" + small_caps("top searches (last 2 weeks):") + "</b>\n"
            )
        )
        medals = ["🥇", "🥈", "🥉"] + ["🎖️"] * 10
        for i, (title, count) in enumerate((top_searches or [])[:5]):
            text_ana += f"  {medals[i]} {e(title[:25])} — {code(str(count))}\n"
        if not top_searches:
            text_ana += "  " + small_caps("no data yet.") + "\n"
        ana_kb = [
            [_btn(small_caps("🏆 full top searches"), "top_searches_refresh"),
             _btn(small_caps("📤 export users"), "admin_export_users_quick")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_ana, reply_markup=InlineKeyboardMarkup(ana_kb))
        return

    # ── Help / documentation ───────────────────────────────────────────────────
    if data == "admin_help":
        if not is_admin:
            return
        text_help = (
            b(small_caps("❓ admin help & docs")) + "\n\n"
            + bq(
                "<b>" + small_caps("quick setup guide:") + "</b>\n"
                "1. " + small_caps("add force-sub channels via channels panel") + "\n"
                "2. " + small_caps("generate links for each channel") + "\n"
                "3. " + small_caps("configure poster template for each category") + "\n"
                "4. " + small_caps("enable filter poster for automatic anime posters") + "\n"
                "5. " + small_caps("set chatbot api keys if you want ai responses") + "\n\n"
                "<b>" + small_caps("useful commands:") + "</b>\n"
                "<code>/admin</code> — open admin panel\n"
                "<code>/stats</code> — bot statistics\n"
                "<code>/broadcast</code> — broadcast to all users\n"
                "<code>/exportusers</code> — export user list\n"
                "<code>/cleanup</code> — clean expired links\n"
                "<code>/reload</code> — restart the bot\n\n"
                "<b>" + small_caps("support:") + "</b>\n"
                + small_caps("contact @Beat_Anime_Ocean for help.")
            )
        )
        await safe_edit_text(
            query, text_help,
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_back"), _close_btn()]]),
        )
        return

    # ── Cache management ───────────────────────────────────────────────────────
    if data == "admin_cache_panel":
        if not is_admin:
            return
        poster_count  = _get_cache_count() if _FILTER_POSTER_AVAILABLE else 0
        panel_count   = 0
        try:
            from core.panel_image import get_panel_db_images
            panel_count = len(get_panel_db_images())
        except Exception:
            pass
        text_cache = (
            b(small_caps("⚡ cache management")) + "\n\n"
            + bq(
                f"<b>{small_caps('filter poster cache')}:</b> {code(str(poster_count))} entries\n"
                f"<b>{small_caps('panel image DB')}:</b> {code(str(panel_count))} images\n\n"
                + small_caps("clearing cache forces fresh generation on next request.")
            )
        )
        cache_kb = [
            [_btn(small_caps("🗑 clear poster cache"), "fp_clear_cache"),
             _btn(small_caps("♻️ refresh panel cache"), "panel_img_refresh_cache")],
            [_btn(small_caps("♻️ clear all caches"), "admin_clear_all_caches")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_cache, reply_markup=InlineKeyboardMarkup(cache_kb))
        return

    if data == "admin_clear_all_caches":
        if not is_admin:
            return
        cleared = 0
        if _FILTER_POSTER_AVAILABLE:
            cleared += _clear_poster_cache() or 0
        try:
            from panel_image import clear_image_cache
            cleared += clear_image_cache() or 0
        except Exception:
            pass
        await safe_answer(query, small_caps(f"♻️ cleared {cleared} total cache entries."))
        return

    # ── Privacy settings ───────────────────────────────────────────────────────
    if data == "admin_privacy_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        anon_stats = get_setting("anonymous_stats", "true") == "true"
        log_queries = get_setting("log_search_queries", "true") == "true"
        text_priv = (
            b(small_caps("🔒 privacy settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('anonymous stats')}:</b> {'✅ ON' if anon_stats else '❌ OFF'}\n"
                f"<b>{small_caps('log search queries')}:</b> {'✅ ON' if log_queries else '❌ OFF'}\n\n"
                + small_caps(
                    "anonymous stats: aggregate usage data only, no user tracking.\n"
                    "log search queries: used for /top searches leaderboard."
                )
            )
        )
        priv_kb = [
            [_btn(f"{'✅' if anon_stats else '❌'} " + small_caps("anon stats"),
                  "toggle_anon_stats"),
             _btn(f"{'✅' if log_queries else '❌'} " + small_caps("log queries"),
                  "toggle_log_queries")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_priv, reply_markup=InlineKeyboardMarkup(priv_kb))
        return

    if data == "toggle_anon_stats":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("anonymous_stats", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("anonymous_stats", new_val)
        await safe_answer(query, small_caps(f"anonymous stats: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_privacy_settings")
        return

    if data == "toggle_log_queries":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("log_search_queries", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("log_search_queries", new_val)
        await safe_answer(query, small_caps(f"query logging: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_privacy_settings")
        return

    # ── Bot token rotation (multi-bot support) ────────────────────────────────
    if data == "admin_bot_tokens":
        if not is_admin:
            return
        from database_dual import get_setting
        import os as _os
        main_token_masked = ("*" * 20 + _os.getenv("BOT_TOKEN", "")[-8:]) if _os.getenv("BOT_TOKEN") else small_caps("not set")
        text_bt = (
            b(small_caps("🤖 bot token management")) + "\n\n"
            + bq(
                f"<b>{small_caps('main bot token')}:</b> {code(main_token_masked)}\n\n"
                + small_caps(
                    "clone bots are managed in the clones section.\n"
                    "to change the main bot token, edit the BOT_TOKEN environment variable "
                    "and restart the bot."
                )
            )
        )
        bt_kb = [
            [_btn(small_caps("🤖 manage clones"), "manage_clones")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_bt, reply_markup=InlineKeyboardMarkup(bt_kb))
        return

    # ── Poster background settings ─────────────────────────────────────────────
    if data == "admin_poster_bg_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        bg_source = get_setting("poster_bg_source", "anilist") or "anilist"
        bg_blur   = get_setting("poster_bg_blur", "20") or "20"
        bg_darken = get_setting("poster_bg_darken", "60") or "60"
        text_bg = (
            b(small_caps("🎨 poster background settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('source')}:</b> {code(bg_source)}\n"
                f"<b>{small_caps('blur strength')}:</b> {code(bg_blur)} px\n"
                f"<b>{small_caps('darken')}:</b> {code(bg_darken)}%\n\n"
                + small_caps(
                    "source: anilist = use series banner, cover = use series cover image.\n"
                    "blur: amount of gaussian blur applied to background.\n"
                    "darken: 0 = no darken, 100 = fully black."
                )
            )
        )
        bg_kb = [
            [_btn(small_caps("🔄 toggle source"), "toggle_poster_bg_source"),
             _btn(small_caps("blur +5"), "poster_bg_blur_up"),
             _btn(small_caps("blur -5"), "poster_bg_blur_dn")],
            [_btn(small_caps("darken +10"), "poster_bg_dark_up"),
             _btn(small_caps("darken -10"), "poster_bg_dark_dn")],
            [_back_btn("admin_filter_poster"), _close_btn()],
        ]
        await safe_edit_text(query, text_bg, reply_markup=InlineKeyboardMarkup(bg_kb))
        return

    if data == "toggle_poster_bg_source":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("poster_bg_source", "anilist")
        new_val = "cover" if cur == "anilist" else "anilist"
        set_setting("poster_bg_source", new_val)
        await safe_answer(query, small_caps(f"bg source: {new_val}"))
        await button_handler(update, context, "admin_poster_bg_settings")
        return

    for _bg_key, _bg_cb, _bg_default, _bg_step in (
        ("poster_bg_blur",   "poster_bg_blur_up", "20", 5),
        ("poster_bg_blur",   "poster_bg_blur_dn", "20", -5),
        ("poster_bg_darken", "poster_bg_dark_up", "60", 10),
        ("poster_bg_darken", "poster_bg_dark_dn", "60", -10),
    ):
        if data == _bg_cb:
            if not is_admin:
                return
            from database_dual import get_setting, set_setting
            try:
                val = int(get_setting(_bg_key, _bg_default) or _bg_default)
                val = max(0, min(200, val + _bg_step))
                set_setting(_bg_key, str(val))
                await safe_answer(query, small_caps(f"{_bg_key.split('_')[-1]}: {val}"))
            except Exception:
                pass
            await button_handler(update, context, "admin_poster_bg_settings")
            return

    # ── Quick action shortcuts from start/stats panel ──────────────────────────
    if data == "quick_broadcast":
        if not is_admin:
            return
        await button_handler(update, context, "admin_broadcast_start")
        return

    if data == "quick_export":
        if not is_admin:
            return
        await button_handler(update, context, "admin_export_users_quick")
        return

    if data == "quick_stats":
        if not is_admin:
            return
        await button_handler(update, context, "admin_stats")
        return

    if data == "quick_logs":
        if not is_admin:
            return
        await button_handler(update, context, "admin_logs")
        return

    # ── Manga chapters navigation (from au_list results) ──────────────────────
    if data.startswith("mdex_chapters_page_"):
        parts = data.split("_")
        try:
            manga_id_mc = parts[-2]
            page_mc = int(parts[-1])
        except (IndexError, ValueError):
            return
        try:
            from api.mangadex import MangaDexClient
            chapters = MangaDexClient.get_manga_chapters(manga_id_mc, offset=page_mc * 10, limit=10)
        except Exception:
            chapters = []
        text_mc = b(small_caps(f"📖 chapters — page {page_mc + 1}")) + "\n\n"
        if chapters:
            for ch in chapters:
                ch_id_v  = ch.get("id", "")
                attrs_v  = ch.get("attributes", {}) or {}
                ch_num_v = attrs_v.get("chapter", "?")
                ch_ttl_v = attrs_v.get("title", "") or ""
                text_mc += f"Ch. <b>{ch_num_v}</b> {e(ch_ttl_v[:30])}\n"
        else:
            text_mc += small_caps("no chapters found.")
        nav_row = []
        if page_mc > 0:
            nav_row.append(_btn(small_caps("◀ prev"), f"mdex_chapters_page_{manga_id_mc}_{page_mc-1}"))
        if chapters and len(chapters) == 10:
            nav_row.append(_btn(small_caps("next ▶"), f"mdex_chapters_page_{manga_id_mc}_{page_mc+1}"))
        rows_mc = [nav_row] if nav_row else []
        rows_mc.append([_back_btn("au_list_manga"), _close_btn()])
        await safe_edit_text(query, text_mc, reply_markup=InlineKeyboardMarkup(rows_mc))
        return

    # ── Poster refresh (regenerate without search) ─────────────────────────────
    if data.startswith("poster_refresh_"):
        rest_pr = data[len("poster_refresh_"):]
        parts_pr = rest_pr.split("_", 1)
        if len(parts_pr) == 2:
            cat_pr, title_pr = parts_pr
            await safe_answer(query, small_caps("🔄 regenerating poster..."))
            try:
                from handlers.post_gen import generate_and_send_post
                asyncio.create_task(generate_and_send_post(
                    context, chat_id, cat_pr, title=title_pr
                ))
            except Exception:
                pass
        return

    # ── Series/character quick-share (social share button) ────────────────────
    if data.startswith("share_result_"):
        share_text = data[len("share_result_"):]
        try:
            tg_share_url = f"https://t.me/share/url?url=&text={share_text[:100]}"
            await safe_answer(
                query,
                small_caps("tap the link to share!"),
                url=tg_share_url,
            )
        except Exception:
            await safe_answer(query, small_caps("share unavailable."))
        return

    # ── Confirmation guard for destructive actions ────────────────────────────
    if data.startswith("confirm_action_"):
        if not is_admin:
            return
        action = data[len("confirm_action_"):]
        stored = context.user_data.get("pending_confirm_action")
        if stored == action:
            context.user_data.pop("pending_confirm_action", None)
            # Dispatch back as the confirmed action
            await button_handler(update, context, action)
        else:
            await safe_answer(query, small_caps("❌ confirmation expired. try again."), show_alert=True)
        return

    # ── Generic paginated list navigation ─────────────────────────────────────
    if data.startswith("paginate_"):
        # Format: paginate_<list_key>_<page>
        parts_pg = data.split("_", 2)
        if len(parts_pg) == 3:
            _, list_key_pg, page_str_pg = parts_pg
            try:
                page_pg = int(page_str_pg)
            except ValueError:
                page_pg = 0
            # Try to dispatch to a known list-refresh handler
            known_paginators = {
                "users":       "user_management",
                "clones":      "clone_list_full",
                "channels":    "manage_force_sub",
                "connections": "af_list_connections",
                "manga":       "au_list_manga",
            }
            target_pg = known_paginators.get(list_key_pg)
            if target_pg:
                await button_handler(update, context, target_pg)
        return

    # ── Poster image quality settings ─────────────────────────────────────────
    if data == "admin_poster_quality":
        if not is_admin:
            return
        from database_dual import get_setting
        p_width  = get_setting("poster_width",  "1280") or "1280"
        p_height = get_setting("poster_height", "720")  or "720"
        p_format = get_setting("poster_format", "JPEG") or "JPEG"
        p_quality= get_setting("poster_jpeg_quality", "95") or "95"
        text_pq = (
            b(small_caps("🖼 poster render quality")) + "\n\n"
            + bq(
                f"<b>{small_caps('resolution')}:</b> {code(p_width + ' × ' + p_height)}\n"
                f"<b>{small_caps('format')}:</b> {code(p_format)}\n"
                f"<b>{small_caps('jpeg quality')}:</b> {code(p_quality + '/100')}\n\n"
                + small_caps(
                    "higher resolution = better quality but larger file size.\n"
                    "jpeg quality 95 is recommended for best results."
                )
            )
        )
        pq_presets = [
            ("720p",  "1280", "720"),
            ("1080p", "1920", "1080"),
            ("4K",    "3840", "2160"),
        ]
        pq_rows = []
        for label_pq, w_pq, h_pq in pq_presets:
            active_pq = "✅ " if (p_width == w_pq and p_height == h_pq) else ""
            pq_rows.append(_btn(
                f"{active_pq}{small_caps(label_pq)}",
                f"poster_res_set_{w_pq}_{h_pq}"
            ))
        pq_btn_rows = _grid3(pq_rows)
        pq_btn_rows.append([
            _btn(small_caps("📁 PNG format"), "poster_fmt_png"),
            _btn(small_caps("📁 JPEG format"), "poster_fmt_jpeg"),
        ])
        pq_btn_rows.append([_back_btn("admin_filter_poster"), _close_btn()])
        await safe_edit_text(query, text_pq, reply_markup=InlineKeyboardMarkup(pq_btn_rows))
        return

    if data.startswith("poster_res_set_"):
        if not is_admin:
            return
        parts_prs = data[len("poster_res_set_"):].split("_")
        if len(parts_prs) == 2:
            from database_dual import set_setting
            set_setting("poster_width",  parts_prs[0])
            set_setting("poster_height", parts_prs[1])
            await safe_answer(query, small_caps(f"resolution set: {parts_prs[0]}×{parts_prs[1]}"))
            await button_handler(update, context, "admin_poster_quality")
        return

    if data in ("poster_fmt_png", "poster_fmt_jpeg"):
        if not is_admin:
            return
        from database_dual import set_setting
        fmt_val = "PNG" if data == "poster_fmt_png" else "JPEG"
        set_setting("poster_format", fmt_val)
        await safe_answer(query, small_caps(f"poster format set to {fmt_val}"))
        await button_handler(update, context, "admin_poster_quality")
        return

    # ── Join button style ──────────────────────────────────────────────────────
    if data == "admin_join_btn_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import JOIN_BTN_TEXT, HERE_IS_LINK_TEXT, REQUEST_BTN_TEXT
        cur_join  = get_setting("env_JOIN_BTN_TEXT",     "") or JOIN_BTN_TEXT
        cur_here  = get_setting("env_HERE_IS_LINK_TEXT", "") or HERE_IS_LINK_TEXT
        cur_req   = get_setting("env_REQUEST_BTN_TEXT",  "") or REQUEST_BTN_TEXT
        text_jbs = (
            b(small_caps("🔘 join button text settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('join button')}:</b> {code(e(cur_join))}\n"
                f"<b>{small_caps('here is link text')}:</b> {code(e(cur_here[:40]))}\n"
                f"<b>{small_caps('request button')}:</b> {code(e(cur_req))}\n\n"
                + small_caps(
                    "these texts appear on the inline buttons sent with every filter poster.\n"
                    "keep them short for best display."
                )
            )
        )
        jbs_kb = [
            [_btn(small_caps("✏️ join text"),  "fp_set_join_btn_join"),
             _btn(small_caps("✏️ here text"),  "fp_set_join_btn_here")],
            [_btn(small_caps("✏️ request text"), "fp_set_join_btn_req")],
            [_back_btn("admin_filter_poster"), _close_btn()],
        ]
        await safe_edit_text(query, text_jbs, reply_markup=InlineKeyboardMarkup(jbs_kb))
        return

    # ── Chatbot persona settings ───────────────────────────────────────────────
    if data == "admin_chatbot_persona":
        if not is_admin:
            return
        from database_dual import get_setting
        persona  = get_setting("chatbot_persona", "assistant") or "assistant"
        language = get_setting("chatbot_language", "en") or "en"
        ctx_len  = get_setting("chatbot_context_length", "10") or "10"
        text_cp = (
            b(small_caps("🤖 chatbot persona settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('persona')}:</b> {code(persona)}\n"
                f"<b>{small_caps('language')}:</b> {code(language)}\n"
                f"<b>{small_caps('context memory')}:</b> {code(ctx_len + ' messages')}\n\n"
                + small_caps(
                    "persona shapes how the chatbot responds.\n"
                    "context memory is how many previous messages the bot remembers per conversation."
                )
            )
        )
        cp_personas = [
            ("assistant", "🤝"),
            ("anime_fan",  "🎌"),
            ("tsundere",   "😤"),
            ("kuudere",    "🧊"),
            ("genki",      "✨"),
        ]
        cp_rows = []
        for p_key, p_em in cp_personas:
            active_cp = "✅ " if persona == p_key else ""
            cp_rows.append(_btn(f"{active_cp}{p_em} {small_caps(p_key)}", f"chatbot_persona_set_{p_key}"))
        cp_btn_rows = _grid3(cp_rows)
        cp_btn_rows.append([
            _btn(small_caps("⬆ more context +5"), "chatbot_ctx_up"),
            _btn(small_caps("⬇ less context -5"), "chatbot_ctx_dn"),
        ])
        cp_btn_rows.append([_back_btn("admin_chatbot_panel"), _close_btn()])
        await safe_edit_text(query, text_cp, reply_markup=InlineKeyboardMarkup(cp_btn_rows))
        return

    if data.startswith("chatbot_persona_set_"):
        if not is_admin:
            return
        persona_val = data[len("chatbot_persona_set_"):]
        valid_personas = {"assistant", "anime_fan", "tsundere", "kuudere", "genki"}
        if persona_val in valid_personas:
            from database_dual import set_setting
            set_setting("chatbot_persona", persona_val)
            await safe_answer(query, small_caps(f"persona set: {persona_val}"))
            await button_handler(update, context, "admin_chatbot_persona")
        return

    if data in ("chatbot_ctx_up", "chatbot_ctx_dn"):
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        try:
            cur_ctx = int(get_setting("chatbot_context_length", "10") or "10")
            step_ctx = 5 if data == "chatbot_ctx_up" else -5
            new_ctx = max(2, min(50, cur_ctx + step_ctx))
            set_setting("chatbot_context_length", str(new_ctx))
            await safe_answer(query, small_caps(f"context memory: {new_ctx} messages"))
        except Exception:
            pass
        await button_handler(update, context, "admin_chatbot_persona")
        return

    # ── Poster text / font configuration ──────────────────────────────────────
    if data == "admin_poster_text_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        font_primary   = get_setting("poster_font_primary",   "Poppins-Bold")    or "Poppins-Bold"
        font_secondary = get_setting("poster_font_secondary", "Poppins-Regular") or "Poppins-Regular"
        font_size_ttl  = get_setting("poster_font_size_title", "40")             or "40"
        font_size_info = get_setting("poster_font_size_info",  "22")             or "22"
        font_color_ttl = get_setting("poster_color_title",    "#FFFFFF")         or "#FFFFFF"
        text_pts = (
            b(small_caps("✍ poster text settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('title font')}:</b> {code(font_primary)}\n"
                f"<b>{small_caps('info font')}:</b> {code(font_secondary)}\n"
                f"<b>{small_caps('title size')}:</b> {code(font_size_ttl + ' px')}\n"
                f"<b>{small_caps('info size')}:</b> {code(font_size_info + ' px')}\n"
                f"<b>{small_caps('title color')}:</b> {code(font_color_ttl)}\n\n"
                + small_caps("fonts available: Poppins-Bold, Poppins-Regular, BebasNeue Bold, "
                             "DMSans-Bold, Overpass-Bold, Roboto-Medium")
            )
        )
        pts_kb = [
            [_btn(small_caps("✏️ title font"),    "set_poster_font_primary"),
             _btn(small_caps("✏️ info font"),     "set_poster_font_secondary")],
            [_btn(small_caps("title size +2"),    "poster_ttl_size_up"),
             _btn(small_caps("title size -2"),    "poster_ttl_size_dn")],
            [_btn(small_caps("info size +2"),     "poster_info_size_up"),
             _btn(small_caps("info size -2"),     "poster_info_size_dn")],
            [_btn(small_caps("✏️ title color"),   "set_poster_title_color")],
            [_back_btn("admin_filter_poster"), _close_btn()],
        ]
        await safe_edit_text(query, text_pts, reply_markup=InlineKeyboardMarkup(pts_kb))
        return

    for _pts_key, _pts_cb, _pts_default, _pts_step in (
        ("poster_font_size_title", "poster_ttl_size_up",  "40",  2),
        ("poster_font_size_title", "poster_ttl_size_dn",  "40", -2),
        ("poster_font_size_info",  "poster_info_size_up", "22",  2),
        ("poster_font_size_info",  "poster_info_size_dn", "22", -2),
    ):
        if data == _pts_cb:
            if not is_admin:
                return
            from database_dual import get_setting, set_setting
            try:
                val = int(get_setting(_pts_key, _pts_default) or _pts_default)
                val = max(10, min(100, val + _pts_step))
                set_setting(_pts_key, str(val))
                await safe_answer(query, small_caps(f"font size: {val}px"))
            except Exception:
                pass
            await button_handler(update, context, "admin_poster_text_settings")
            return

    if data == "set_poster_font_primary":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_POSTER_FONT_PRIMARY"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("✍ set title font")) + "\n\n"
            + bq(small_caps(
                "send the font filename (without path):\n"
                "• Poppins-Bold\n• Poppins-ExtraBold\n• BebasNeue Bold\n"
                "• DMSans-Bold\n• Overpass-Bold\n• Roboto-Medium"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_poster_text_settings"), _close_btn()]]),
        )
        return

    if data == "set_poster_font_secondary":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_POSTER_FONT_SECONDARY"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("✍ set info font")) + "\n\n"
            + bq(small_caps(
                "send the font filename (without path):\n"
                "• Poppins-Regular\n• DMSans-Regular\n• Overpass-Regular\n• Roboto-Regular"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_poster_text_settings"), _close_btn()]]),
        )
        return

    if data == "set_poster_title_color":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_POSTER_TITLE_COLOR"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🎨 set title text color")) + "\n\n"
            + bq(small_caps("send hex color code:\nexample: #FFFFFF (white), #FFD700 (gold), #FF6B6B (red)")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_poster_text_settings"), _close_btn()]]),
        )
        return

    # ── Default caption settings ───────────────────────────────────────────────
    if data == "admin_default_caption":
        if not is_admin:
            return
        from database_dual import get_setting
        from core.config import BOT_NAME
        cur_cap = get_setting("default_caption_template", "") or small_caps("(using system default)")
        text_dc = (
            b(small_caps("📝 default caption template")) + "\n\n"
            + bq(
                f"<b>{small_caps('current')}:</b> {e(cur_cap[:100])}\n\n"
                + small_caps(
                    "available variables: {title}, {genres}, {score}, {episodes}, {status}, "
                    "{studios}, {native}, {channel}\n\n"
                    "html formatting supported: <b>bold</b>, <i>italic</i>, <code>mono</code>"
                )
            )
        )
        dc_kb = [
            [_btn(small_caps("✏️ set template"), "set_default_caption"),
             _btn(small_caps("♻️ reset default"), "reset_default_caption")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_dc, reply_markup=InlineKeyboardMarkup(dc_kb))
        return

    if data == "set_default_caption":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_DEFAULT_CAPTION"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📝 set default caption template")) + "\n\n"
            + bq(small_caps(
                "send your caption template.\n"
                "variables: {title}, {native}, {genres}, {score}, {episodes}, {status}, {channel}\n\n"
                "example:\n"
                "🎌 {title}\n📊 Score: {score}\n🎭 {genres}\n\nvia {channel}"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_default_caption"), _close_btn()]]),
        )
        return

    if data == "reset_default_caption":
        if not is_admin:
            return
        from database_dual import set_setting
        set_setting("default_caption_template", "")
        await safe_answer(query, small_caps("default caption reset."))
        await button_handler(update, context, "admin_default_caption")
        return

    # ── Group management helpers ───────────────────────────────────────────────
    if data == "admin_group_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        gc_filter  = get_setting("group_filter_enabled",  "true") == "true"
        gc_chatbot = get_setting("group_chatbot_default", "true") == "true"
        gc_clean   = get_setting("clean_gc_enabled",      "true") == "true"
        text_gs = (
            b(small_caps("⚙️ group settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('filter in groups')}:</b> {'✅' if gc_filter else '❌'}\n"
                f"<b>{small_caps('chatbot default')}:</b> {'✅ on' if gc_chatbot else '❌ off'}\n"
                f"<b>{small_caps('clean service msgs')}:</b> {'✅' if gc_clean else '❌'}"
            )
        )
        gs_kb = [
            [_btn(f"{'✅' if gc_filter else '❌'} " + small_caps("group filter"),
                  "filter_toggle_group"),
             _btn(f"{'✅' if gc_chatbot else '❌'} " + small_caps("chatbot default"),
                  "toggle_group_chatbot_default")],
            [_btn(f"{'✅' if gc_clean else '❌'} " + small_caps("clean gc"),
                  "toggle_clean_gc")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_gs, reply_markup=InlineKeyboardMarkup(gs_kb))
        return

    if data == "toggle_group_chatbot_default":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("group_chatbot_default", "true")
        new_val = "false" if cur == "true" else "true"
        set_setting("group_chatbot_default", new_val)
        await safe_answer(query, small_caps(f"group chatbot default: {'on' if new_val == 'true' else 'off'}"))
        await button_handler(update, context, "admin_group_settings")
        return

    # ── Broadcast target selection ─────────────────────────────────────────────
    if data == "broadcast_target_all":
        if not is_admin:
            return
        context.user_data["broadcast_target"] = "all"
        await safe_answer(query, small_caps("target: all users"))
        await button_handler(update, context, "admin_broadcast_start")
        return

    if data == "broadcast_target_active":
        if not is_admin:
            return
        context.user_data["broadcast_target"] = "active"
        await safe_answer(query, small_caps("target: active users (last 30 days)"))
        await button_handler(update, context, "admin_broadcast_start")
        return

    if data == "broadcast_target_unbanned":
        if not is_admin:
            return
        context.user_data["broadcast_target"] = "unbanned"
        await safe_answer(query, small_caps("target: unbanned users only"))
        await button_handler(update, context, "admin_broadcast_start")
        return

    if data == "broadcast_options_panel":
        if not is_admin:
            return
        target  = context.user_data.get("broadcast_target", "all")
        pin_msg = context.user_data.get("broadcast_pin", False)
        protect = context.user_data.get("broadcast_protect", False)
        text_bo = (
            b(small_caps("📣 broadcast options")) + "\n\n"
            + bq(
                f"<b>{small_caps('target')}:</b> {code(target)}\n"
                f"<b>{small_caps('pin message')}:</b> {'✅' if pin_msg else '❌'}\n"
                f"<b>{small_caps('protect content')}:</b> {'✅' if protect else '❌'}"
            )
        )
        bo_kb = [
            [_btn(small_caps("👥 all users"), "broadcast_target_all"),
             _btn(small_caps("🟢 active only"), "broadcast_target_active")],
            [_btn(small_caps("✅ unbanned only"), "broadcast_target_unbanned")],
            [_btn(f"{'✅' if pin_msg else '❌'} " + small_caps("pin"),
                  "broadcast_toggle_pin"),
             _btn(f"{'✅' if protect else '❌'} " + small_caps("protect"),
                  "broadcast_toggle_protect")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_bo, reply_markup=InlineKeyboardMarkup(bo_kb))
        return

    if data == "broadcast_toggle_pin":
        if not is_admin:
            return
        context.user_data["broadcast_pin"] = not context.user_data.get("broadcast_pin", False)
        await safe_answer(query, small_caps(f"pin: {'on' if context.user_data['broadcast_pin'] else 'off'}"))
        await button_handler(update, context, "broadcast_options_panel")
        return

    if data == "broadcast_toggle_protect":
        if not is_admin:
            return
        context.user_data["broadcast_protect"] = not context.user_data.get("broadcast_protect", False)
        await safe_answer(query, small_caps(f"protect: {'on' if context.user_data['broadcast_protect'] else 'off'}"))
        await button_handler(update, context, "broadcast_options_panel")
        return

    # ── Clone bot health check ─────────────────────────────────────────────────
    if data == "clone_health_check":
        if not is_admin:
            return
        await safe_answer(query, small_caps("checking all clones..."))
        try:
            from database_dual import get_all_clone_bots
            from telegram import Bot as _TgBot
            clones_all = get_all_clone_bots(active_only=True)
            results_hc = []
            for _, token_hc, uname_hc, _, _ in clones_all:
                try:
                    bot_hc = _TgBot(token=token_hc)
                    me_hc = await bot_hc.get_me()
                    results_hc.append(f"🟢 @{me_hc.username}")
                except Exception as _hce:
                    results_hc.append(f"🔴 @{uname_hc}: {str(_hce)[:30]}")
            text_hc = b(small_caps("🤖 clone health check")) + "\n\n"
            if results_hc:
                text_hc += "\n".join(results_hc)
            else:
                text_hc += bq(small_caps("no active clones found."))
        except Exception as exc_hc:
            text_hc = b(small_caps(f"❌ error: {e(str(exc_hc)[:80])}"))
        await safe_send_message(
            context.bot, chat_id, text_hc,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_clones"), _close_btn()]]),
        )
        return

    # ── Link expiry bulk update ────────────────────────────────────────────────
    if data == "link_expiry_bulk_extend":
        if not is_admin:
            return
        await safe_answer(query, small_caps("extending all links by 24h..."))
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE invite_links SET expires_at = expires_at + INTERVAL '24 hours' "
                    "WHERE expires_at IS NOT NULL AND expires_at > NOW()"
                )
            await safe_answer(query, small_caps("✅ all links extended by 24 hours!"), show_alert=True)
        except Exception as exc_be:
            await safe_answer(query, small_caps(f"❌ {str(exc_be)[:60]}"), show_alert=True)
        return

    if data == "link_expiry_bulk_reset":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b(small_caps("⚠️ reset all link expiry?")) + "\n\n"
            + bq(small_caps("this will regenerate expiry times for all active links based on current settings.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("✅ confirm"), callback_data="link_expiry_bulk_reset_confirm"),
                _back_btn("admin_link_manager"),
            ]]),
        )
        return

    if data == "link_expiry_bulk_reset_confirm":
        if not is_admin:
            return
        await safe_answer(query, small_caps("resetting link expiry..."))
        try:
            from database_dual import get_setting, db_manager
            expiry_min = int(get_setting("link_expiry_override", str(LINK_EXPIRY_MINUTES)) or LINK_EXPIRY_MINUTES)
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE invite_links SET expires_at = created_at + INTERVAL '%s minutes' "
                    "WHERE expires_at IS NOT NULL", (expiry_min,)
                )
            await safe_answer(query, small_caps(f"✅ done! all links now expire in {expiry_min} minutes."), show_alert=True)
        except Exception as exc_lr:
            await safe_answer(query, small_caps(f"❌ {str(exc_lr)[:60]}"), show_alert=True)
        return

    # ── Channel member count refresh ───────────────────────────────────────────
    if data == "refresh_channel_counts":
        if not is_admin:
            return
        await safe_answer(query, small_caps("fetching member counts..."))
        try:
            from database_dual import get_all_force_sub_channels
            channels_rcc = get_all_force_sub_channels(return_usernames_only=False)
            count_results = []
            for row_rcc in channels_rcc[:10]:   # limit to 10 to avoid rate limits
                ch_id_rcc   = row_rcc[0] if len(row_rcc) > 0 else ""
                ch_name_rcc = row_rcc[1] if len(row_rcc) > 1 else ch_id_rcc
                try:
                    ch_obj = await context.bot.get_chat(ch_id_rcc)
                    member_count = await context.bot.get_chat_member_count(ch_id_rcc)
                    count_results.append(f"📢 {e(str(ch_name_rcc))}: {code(f'{member_count:,}')}")
                except Exception:
                    count_results.append(f"❌ {e(str(ch_name_rcc))}: error")
            text_rcc = b(small_caps("📊 channel member counts")) + "\n\n"
            if count_results:
                text_rcc += "\n".join(count_results)
            else:
                text_rcc += bq(small_caps("no channels configured."))
        except Exception as exc_rcc:
            text_rcc = b(small_caps(f"❌ error: {e(str(exc_rcc)[:80])}"))
        await safe_send_message(
            context.bot, chat_id, text_rcc,
            reply_markup=InlineKeyboardMarkup([[_back_btn("manage_force_sub"), _close_btn()]]),
        )
        return

    # ── Advanced search settings ───────────────────────────────────────────────
    if data == "admin_search_settings":
        if not is_admin:
            return
        from database_dual import get_setting
        fuzz_enabled  = get_setting("fuzzy_search_enabled",  "true") == "true"
        multi_src     = get_setting("multi_source_search",    "true") == "true"
        safe_mode     = get_setting("search_safe_mode",       "false") == "true"
        cache_ttl     = get_setting("search_cache_ttl_sec",   "300") or "300"
        text_ss = (
            b(small_caps("🔍 search settings")) + "\n\n"
            + bq(
                f"<b>{small_caps('fuzzy search')}:</b> {'✅ ON' if fuzz_enabled else '❌ OFF'}\n"
                f"<b>{small_caps('multi-source')}:</b> {'✅ ON' if multi_src else '❌ OFF'}\n"
                f"<b>{small_caps('safe mode')}:</b> {'✅ ON' if safe_mode else '❌ OFF'}\n"
                f"<b>{small_caps('cache TTL')}:</b> {code(cache_ttl + 's')}\n\n"
                + small_caps(
                    "fuzzy search: approximate matching for misspelt titles.\n"
                    "multi-source: search anilist + tmdb + mangadex simultaneously.\n"
                    "safe mode: exclude adult content from results."
                )
            )
        )
        ss_kb = [
            [_btn(f"{'✅' if fuzz_enabled else '❌'} " + small_caps("fuzzy"),
                  "toggle_fuzzy_search"),
             _btn(f"{'✅' if multi_src else '❌'} " + small_caps("multi-src"),
                  "toggle_multi_source")],
            [_btn(f"{'✅' if safe_mode else '❌'} " + small_caps("safe mode"),
                  "toggle_search_safe"),
             _btn(small_caps("cache TTL"), "set_search_cache_ttl")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_ss, reply_markup=InlineKeyboardMarkup(ss_kb))
        return

    for _ss_key, _ss_cb, _ss_default in (
        ("fuzzy_search_enabled",  "toggle_fuzzy_search",  "true"),
        ("multi_source_search",   "toggle_multi_source",  "true"),
        ("search_safe_mode",      "toggle_search_safe",   "false"),
    ):
        if data == _ss_cb:
            if not is_admin:
                return
            from database_dual import get_setting, set_setting
            cur = get_setting(_ss_key, _ss_default)
            new_val = "false" if cur == "true" else "true"
            set_setting(_ss_key, new_val)
            await safe_answer(query, small_caps(f"{'enabled' if new_val == 'true' else 'disabled'}!"))
            await button_handler(update, context, "admin_search_settings")
            return

    if data == "set_search_cache_ttl":
        if not is_admin:
            return
        from database_dual import get_setting
        cur = get_setting("search_cache_ttl_sec", "300")
        user_states[uid] = "AWAITING_SEARCH_CACHE_TTL"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("⏱ set search cache TTL")) + "\n\n"
            + bq(small_caps(
                f"current: {cur}s\n"
                "send cache time in seconds (0 = no cache, 300 = 5 minutes, 3600 = 1 hour):"
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_search_settings"), _close_btn()]]),
        )
        return

    # ── Post generation review mode ────────────────────────────────────────────
    if data == "admin_post_review":
        if not is_admin:
            return
        from database_dual import get_setting
        review_on = get_setting("post_review_mode", "false") == "true"
        text_pr = (
            b(small_caps("👁 post review mode")) + "\n\n"
            + bq(
                f"<b>{small_caps('status')}:</b> {'✅ enabled' if review_on else '❌ disabled'}\n\n"
                + small_caps(
                    "when enabled, generated posters are sent to the admin for review "
                    "before being forwarded to users. "
                    "admin can approve or reject each post."
                )
            )
        )
        pr_kb = [
            [_btn(f"{'✅' if review_on else '❌'} " + small_caps("toggle"),
                  "toggle_post_review")],
            [_back_btn("admin_settings"), _close_btn()],
        ]
        await safe_edit_text(query, text_pr, reply_markup=InlineKeyboardMarkup(pr_kb))
        return

    if data == "toggle_post_review":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        cur = get_setting("post_review_mode", "false")
        new_val = "false" if cur == "true" else "true"
        set_setting("post_review_mode", new_val)
        await safe_answer(query, small_caps(f"post review: {'enabled' if new_val == 'true' else 'disabled'}"))
        await button_handler(update, context, "admin_post_review")
        return

    # ── Post review approve / reject ───────────────────────────────────────────
    if data.startswith("post_review_approve_"):
        if not is_admin:
            return
        review_id = data[len("post_review_approve_"):]
        try:
            from database_dual import get_setting, db_manager
            import json as _json2
            review_data_raw = get_setting(f"pending_review_{review_id}", "")
            review_data = _json2.loads(review_data_raw) if review_data_raw else {}
            dest_chat  = review_data.get("dest_chat")
            src_chat   = review_data.get("src_chat")
            src_msg    = review_data.get("src_msg")
            cap_r      = review_data.get("caption", "")
            if dest_chat and src_chat and src_msg:
                await context.bot.copy_message(
                    chat_id=dest_chat,
                    from_chat_id=src_chat,
                    message_id=src_msg,
                    caption=cap_r,
                    parse_mode="HTML",
                )
                # Clean up pending review
                from database_dual import set_setting
                set_setting(f"pending_review_{review_id}", "")
                await safe_answer(query, small_caps("✅ post approved and sent!"))
                try:
                    await query.message.delete()
                except Exception:
                    pass
            else:
                await safe_answer(query, small_caps("❌ review data expired."), show_alert=True)
        except Exception as exc_pra:
            await safe_answer(query, small_caps(f"❌ {str(exc_pra)[:60]}"), show_alert=True)
        return

    if data.startswith("post_review_reject_"):
        if not is_admin:
            return
        review_id_rej = data[len("post_review_reject_"):]
        try:
            from database_dual import set_setting
            set_setting(f"pending_review_{review_id_rej}", "")
            await safe_answer(query, small_caps("🗑 post rejected."))
            try:
                await query.message.delete()
            except Exception:
                pass
        except Exception as exc_prr:
            await safe_answer(query, small_caps(f"❌ {str(exc_prr)[:60]}"), show_alert=True)
        return

    # ── Maintenance message to users ───────────────────────────────────────────
    if data == "send_maintenance_notice":
        if not is_admin:
            return
        from database_dual import get_setting
        maintenance_on = get_setting("maintenance_mode", "false") == "true"
        if not maintenance_on:
            await safe_answer(query, small_caps("maintenance mode is off. enable it first."), show_alert=True)
            return
        user_states[uid] = "AWAITING_MAINTENANCE_MESSAGE"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📢 send maintenance notice")) + "\n\n"
            + bq(small_caps(
                "send the maintenance message to broadcast to all users.\n\n"
                "this will be sent immediately to everyone who tries to use the bot "
                "while maintenance mode is active."
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_settings"), _close_btn()]]),
        )
        return

    # ── Super-admin / owner-only actions ──────────────────────────────────────
    if data == "admin_sudo_panel":
        if uid != OWNER_ID:
            await safe_answer(query, small_caps("owner only!"), show_alert=True)
            return
        text_sudo = (
            b(small_caps("👑 owner panel")) + "\n\n"
            + bq(small_caps(
                "these actions are restricted to the bot owner only.\n"
                "use with extreme caution."
            ))
        )
        sudo_kb = [
            [_btn(small_caps("🔑 env variables"),    "admin_env_panel"),
             _btn(small_caps("🤖 bot tokens"),       "admin_bot_tokens")],
            [_btn(small_caps("🧹 full cleanup"),     "dbcleanup_confirm"),
             _btn(small_caps("♻️ restart bot"),      "admin_restart_confirm")],
            [_btn(small_caps("📋 full logs"),        "admin_logs_200"),
             _btn(small_caps("📥 dl logs"),          "admin_logs_download")],
            [_btn(small_caps("🐚 shell access"),     "mod_shell"),
             _btn(small_caps("📊 system stats"),     "admin_sysstats")],
            [_back_btn("admin_back"), _close_btn()],
        ]
        await safe_edit_text(query, text_sudo, reply_markup=InlineKeyboardMarkup(sudo_kb))
        return

    # ── Deep link / inline join flow ──────────────────────────────────────────
    if data.startswith("deeplink_channel_"):
        ch_id_dl = data[len("deeplink_channel_"):]
        try:
            from database_dual import get_link_by_id
            link_info = get_link_by_id(ch_id_dl)
            if link_info:
                from handlers.start import handle_deep_link
                await handle_deep_link(update, context, ch_id_dl)
            else:
                await safe_send_message(
                    context.bot, chat_id,
                    b(small_caps("❌ link not found or expired.")),
                    reply_markup=InlineKeyboardMarkup([[_close_btn()]]),
                )
        except Exception as exc_dl:
            logger.debug(f"deeplink_channel error: {exc_dl}")
            await safe_answer(query, small_caps("❌ link error."), show_alert=True)
        return

    # ── User preference callbacks ──────────────────────────────────────────────
    if data == "user_set_language":
        from database_dual import get_setting
        cur_lang = get_setting(f"user_lang_{uid}", "en") or "en"
        text_ul = (
            b(small_caps("🌐 language preference")) + "\n\n"
            + bq(small_caps(f"current: {cur_lang}\n\nchoose your preferred language for bot responses:"))
        )
        lang_options = [
            ("🇺🇸 English",  "en"),
            ("🇯🇵 Japanese", "ja"),
            ("🇮🇳 Hindi",    "hi"),
            ("🇵🇭 Filipino", "tl"),
            ("🇧🇷 Portuguese", "pt"),
        ]
        lang_rows = []
        for lang_label, lang_code in lang_options:
            active_ul = "✅ " if cur_lang == lang_code else ""
            lang_rows.append(_btn(f"{active_ul}{lang_label}", f"set_user_lang_{lang_code}"))
        lang_btn_rows = _grid3(lang_rows)
        lang_btn_rows.append([_close_btn()])
        await safe_edit_text(query, text_ul, reply_markup=InlineKeyboardMarkup(lang_btn_rows))
        return

    if data.startswith("set_user_lang_"):
        lang_val = data[len("set_user_lang_"):]
        if lang_val in ("en", "ja", "hi", "tl", "pt", "es", "fr", "de", "ko", "zh"):
            from database_dual import set_setting
            set_setting(f"user_lang_{uid}", lang_val)
            await safe_answer(query, small_caps(f"language set: {lang_val}"))
            try:
                await query.message.delete()
            except Exception:
                pass
        return

    # ── User notification preferences ─────────────────────────────────────────
    if data == "user_notification_prefs":
        from database_dual import get_setting
        notif_manga = get_setting(f"user_notif_manga_{uid}", "true") == "true"
        notif_broad = get_setting(f"user_notif_broad_{uid}", "true") == "true"
        text_unp = (
            b(small_caps("🔔 notification preferences")) + "\n\n"
            + bq(
                f"<b>{small_caps('manga updates')}:</b> {'✅' if notif_manga else '❌'}\n"
                f"<b>{small_caps('broadcasts')}:</b> {'✅' if notif_broad else '❌'}"
            )
        )
        unp_kb = [
            [_btn(f"{'✅' if notif_manga else '❌'} " + small_caps("manga"),
                  "toggle_user_notif_manga"),
             _btn(f"{'✅' if notif_broad else '❌'} " + small_caps("broadcasts"),
                  "toggle_user_notif_broad")],
            [_close_btn()],
        ]
        await safe_edit_text(query, text_unp, reply_markup=InlineKeyboardMarkup(unp_kb))
        return

    for _unp_key_suffix, _unp_cb in (
        (f"manga_{uid}", "toggle_user_notif_manga"),
        (f"broad_{uid}", "toggle_user_notif_broad"),
    ):
        if data == _unp_cb:
            _unp_db_key = f"user_notif_{_unp_key_suffix}"
            from database_dual import get_setting, set_setting
            _unp_cur = get_setting(_unp_db_key, "true")
            _unp_new = "false" if _unp_cur == "true" else "true"
            set_setting(_unp_db_key, _unp_new)
            await safe_answer(query, small_caps(f"{'enabled' if _unp_new == 'true' else 'disabled'}!"))
            await button_handler(update, context, "user_notification_prefs")
            return

    # ── Auto-prune inactive users ──────────────────────────────────────────────
    if data == "admin_prune_users":
        if not is_admin:
            return
        from database_dual import get_setting
        prune_days = get_setting("prune_inactive_days", "90") or "90"
        text_apu = (
            b(small_caps("🪚 auto-prune inactive users")) + "\n\n"
            + bq(
                f"<b>{small_caps('inactive threshold')}:</b> {code(prune_days + ' days')}\n\n"
                + small_caps(
                    "pruning removes users who have not interacted with the bot "
                    "for the specified number of days.\n\n"
                    "⚠️ this action cannot be undone."
                )
            )
        )
        apu_kb = [
            [_btn(small_caps("set threshold"), "set_prune_threshold"),
             _btn(small_caps("🔍 preview count"), "preview_prune_count")],
            [bold_button(small_caps("⚠️ prune now"), callback_data="prune_users_confirm")],
            [_back_btn("user_management"), _close_btn()],
        ]
        await safe_edit_text(query, text_apu, reply_markup=InlineKeyboardMarkup(apu_kb))
        return

    if data == "set_prune_threshold":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_PRUNE_THRESHOLD"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("🪚 set prune threshold")) + "\n\n"
            + bq(small_caps("send number of days of inactivity before a user is pruned (e.g. 90):")),
            reply_markup=InlineKeyboardMarkup([[_back_btn("admin_prune_users"), _close_btn()]]),
        )
        return

    if data == "preview_prune_count":
        if not is_admin:
            return
        from database_dual import get_setting
        prune_days_pc = int(get_setting("prune_inactive_days", "90") or "90")
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM users WHERE last_seen < NOW() - INTERVAL '%s days'",
                    (prune_days_pc,)
                )
                row_pc = cur.fetchone()
                count_pc = row_pc[0] if row_pc else 0
        except Exception:
            count_pc = "unknown"
        await safe_answer(
            query,
            small_caps(f"~{count_pc} users would be pruned (inactive {prune_days_pc}+ days)."),
            show_alert=True,
        )
        return

    if data == "prune_users_confirm":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b(small_caps("⚠️ confirm user pruning")) + "\n\n"
            + bq(small_caps(
                "this will permanently delete all inactive users from the database.\n\n"
                "this action cannot be undone!"
            )),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("✅ yes, prune!"), callback_data="prune_users_execute"),
                _back_btn("admin_prune_users"),
            ]]),
        )
        return

    if data == "prune_users_execute":
        if not is_admin:
            return
        from database_dual import get_setting
        prune_days_ex = int(get_setting("prune_inactive_days", "90") or "90")
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "DELETE FROM users WHERE last_seen < NOW() - INTERVAL '%s days' "
                    "AND user_id NOT IN (%s, %s)",
                    (prune_days_ex, ADMIN_ID, OWNER_ID)
                )
                pruned_count = cur.rowcount
            await safe_edit_text(
                query,
                b(small_caps(f"✅ pruned {pruned_count} inactive users!")) + "\n\n"
                + bq(small_caps(f"removed all users inactive for {prune_days_ex}+ days.")),
                reply_markup=InlineKeyboardMarkup([[_back_btn("user_management"), _close_btn()]]),
            )
        except Exception as exc_pue:
            await safe_edit_text(
                query, b(small_caps(f"❌ error: {e(str(exc_pue)[:80])}")) ,
                reply_markup=InlineKeyboardMarkup([[_back_btn("admin_prune_users")]]),
            )
        return



    # ══════════════════════════════════════════════════════════════════════════
    # MODULE-LEVEL CALLBACKS — warns, notes, approve, connection, reporting,
    # custfilters, welcome, speedtest, db_cleanup, user_join_, beat_back,
    # nxt, style+, wlc_, fwd_*, filter_pick, alpha_filter_pick, idx_*,
    # anthmb_*, anpick_*, lang_*, size_*, broadcast_mode_*, inv_loading/ready,
    # {prefix}_module(), {prefix}_next/prev(), and namespace catch-alls
    # ══════════════════════════════════════════════════════════════════════════

    import re as _re

    # ── rm_warn(<user_id>) ─────────────────────────────────────────────────────
    _rm_warn_match = _re.match(r"^rm_warn\((.+?)\)$", data)
    if _rm_warn_match:
        target_warn_uid = _rm_warn_match.group(1)
        try:
            chat_obj = query.message.chat if query.message else None
            if chat_obj:
                member_obj = await context.bot.get_chat_member(chat_obj.id, uid)
                if member_obj.status in ("administrator", "creator") or is_admin:
                    try:
                        from modules.sql import warns_sql as _wsql
                        res = _wsql.remove_warn(target_warn_uid, chat_obj.id)
                        if res:
                            try:
                                await query.message.edit_text(
                                    f"<b>Warn removed</b> by {query.from_user.mention_html()}.",
                                    parse_mode="HTML",
                                )
                            except Exception:
                                pass
                            await safe_answer(query, "✅ Warn removed.")
                        else:
                            await safe_answer(query, "User already has no warns.", show_alert=True)
                    except Exception as exc_rw2:
                        logger.debug(f"rm_warn sql error: {exc_rw2}")
                        await safe_answer(query, "❌ Error removing warn.", show_alert=True)
                else:
                    await safe_answer(query, "Only admins can remove warns.", show_alert=True)
        except Exception as exc_rw:
            logger.debug(f"rm_warn callback error: {exc_rw}")
            await safe_answer(query, "❌ Error removing warn.", show_alert=True)
        return

    # ── notes_rmall / notes_cancel ────────────────────────────────────────────
    if data in ("notes_rmall", "notes_cancel"):
        try:
            chat_obj = query.message.chat if query.message else None
            if not chat_obj:
                return
            member_obj = await context.bot.get_chat_member(chat_obj.id, uid)
            is_creator_n = member_obj.status == "creator"
            if data == "notes_rmall":
                if is_creator_n or is_admin:
                    try:
                        from modules.sql.notes_sql import get_all_chat_notes, rm_note
                        note_list = get_all_chat_notes(chat_obj.id)
                        deleted_n = 0
                        for notename in note_list:
                            rm_note(chat_obj.id, notename.name.lower())
                            deleted_n += 1
                        try:
                            await query.message.edit_text(
                                f"<b>✅ Deleted {deleted_n} note(s).</b>", parse_mode="HTML"
                            )
                        except Exception:
                            pass
                        await safe_answer(query, f"✅ Deleted {deleted_n} notes.")
                    except Exception as exc_nr:
                        logger.debug(f"notes_rmall error: {exc_nr}")
                        await safe_answer(query, f"❌ Error: {str(exc_nr)[:50]}", show_alert=True)
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
            else:
                if is_creator_n or is_admin:
                    try:
                        await query.message.edit_text(
                            "Clearing of all notes has been <b>cancelled</b>.", parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    await safe_answer(query, "Cancelled.")
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
        except Exception as exc_notes:
            logger.debug(f"notes callback error: {exc_notes}")
            await safe_answer(query, "❌ Error.", show_alert=True)
        return

    # ── unapproveall_user / unapproveall_cancel ───────────────────────────────
    if data in ("unapproveall_user", "unapproveall_cancel"):
        try:
            chat_obj = query.message.chat if query.message else None
            if not chat_obj:
                return
            member_obj = await context.bot.get_chat_member(chat_obj.id, uid)
            is_creator_ua = member_obj.status == "creator"
            if data == "unapproveall_user":
                if is_creator_ua or is_admin:
                    try:
                        from modules.sql.approve_sql import list_approved, disapprove
                        approved_users = list_approved(chat_obj.id)
                        users_ua = [int(u.user_id) for u in approved_users]
                        for user_id_ua in users_ua:
                            disapprove(chat_obj.id, user_id_ua)
                        try:
                            await query.message.edit_text(
                                f"<b>✅ Unapproved all {len(users_ua)} user(s).</b>",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                        await safe_answer(query, f"✅ Unapproved {len(users_ua)} users.")
                    except Exception as exc_ua:
                        logger.debug(f"unapproveall error: {exc_ua}")
                        await safe_answer(query, f"❌ Error: {str(exc_ua)[:50]}", show_alert=True)
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
            else:
                if is_creator_ua or is_admin:
                    try:
                        await query.message.edit_text(
                            "Removing of all approved users has been <b>cancelled</b>.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                    await safe_answer(query, "Cancelled.")
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
        except Exception as exc_ua2:
            logger.debug(f"unapproveall callback error: {exc_ua2}")
            await safe_answer(query, "❌ Error.", show_alert=True)
        return

    # ── filters_rmall / filters_cancel ───────────────────────────────────────
    if data in ("filters_rmall", "filters_cancel"):
        try:
            chat_obj = query.message.chat if query.message else None
            if not chat_obj:
                return
            member_obj = await context.bot.get_chat_member(chat_obj.id, uid)
            is_creator_f = member_obj.status == "creator"
            if data == "filters_rmall":
                if is_creator_f or is_admin:
                    try:
                        from modules.sql.cust_filters_sql import get_chat_triggers, remove_trigger
                        all_triggers = list(get_chat_triggers(chat_obj.id))
                        count_f = 0
                        for trigger in all_triggers:
                            try:
                                remove_trigger(chat_obj.id, trigger)
                                count_f += 1
                            except Exception:
                                pass
                        try:
                            await query.message.edit_text(
                                f"<b>✅ Stopped {count_f} filter(s).</b>", parse_mode="HTML"
                            )
                        except Exception:
                            pass
                        await safe_answer(query, f"✅ Stopped {count_f} filters.")
                    except Exception as exc_fr:
                        logger.debug(f"filters_rmall error: {exc_fr}")
                        await safe_answer(query, f"❌ Error: {str(exc_fr)[:50]}", show_alert=True)
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
            else:
                if is_creator_f or is_admin:
                    try:
                        await query.message.edit_text(
                            "Clearing of all filters has been <b>cancelled</b>.", parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    await safe_answer(query, "Cancelled.")
                elif member_obj.status == "administrator":
                    await safe_answer(query, "Only the chat owner can do this.", show_alert=True)
                else:
                    await safe_answer(query, "You need to be admin to do this.", show_alert=True)
        except Exception as exc_ff:
            logger.debug(f"filters callback error: {exc_ff}")
            await safe_answer(query, "❌ Error.", show_alert=True)
        return

    # ── connect(<chat_id>) ────────────────────────────────────────────────────
    _connect_match = _re.match(r"^connect\((.+?)\)$", data)
    if _connect_match:
        connected_chat_str = _connect_match.group(1).strip()
        try:
            from modules.sql.connection_sql import connect as sql_connect
            sql_connect(uid, connected_chat_str)
            try:
                ch_obj = await context.bot.get_chat(connected_chat_str)
                ch_title = getattr(ch_obj, "title", connected_chat_str)
            except Exception:
                ch_title = connected_chat_str
            try:
                await query.message.edit_text(
                    f"<b>🔗 Connected to</b> <code>{e(str(ch_title))}</code>.",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            await safe_answer(query, f"✅ Connected to {str(ch_title)[:30]}")
        except Exception as exc_conn:
            logger.debug(f"connect() callback error: {exc_conn}")
            await safe_answer(query, f"❌ Connection failed: {str(exc_conn)[:50]}", show_alert=True)
        return

    if data == "connect_close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data == "connect_clear":
        try:
            from modules.sql.connection_sql import clear_connection_history
            clear_connection_history(uid)
            try:
                await query.message.edit_text(
                    "<b>🧹 Connection history cleared.</b>", parse_mode="HTML"
                )
            except Exception:
                pass
            await safe_answer(query, "✅ History cleared.")
        except Exception as exc_cc:
            logger.debug(f"connect_clear error: {exc_cc}")
            await safe_answer(query, "❌ Error clearing history.", show_alert=True)
        return

    if data == "connect_disconnect":
        try:
            from modules.sql.connection_sql import disconnect as sql_disconnect
            sql_disconnect(uid)
            try:
                await query.message.edit_text(
                    "<b>🔌 Disconnected from group.</b>", parse_mode="HTML"
                )
            except Exception:
                pass
            await safe_answer(query, "✅ Disconnected.")
        except Exception as exc_cd:
            logger.debug(f"connect_disconnect error: {exc_cd}")
            await safe_answer(query, "❌ Error disconnecting.", show_alert=True)
        return

    # ── report_<chat>=<action>=<uid>=<extra> ──────────────────────────────────
    if data.startswith("report_"):
        try:
            splitter = data.replace("report_", "", 1).split("=")
            if len(splitter) < 3:
                await safe_answer(query, "❌ Invalid report data.", show_alert=True)
                return
            rpt_chat_id = int(splitter[0])
            rpt_action  = splitter[1]
            rpt_uid     = int(splitter[2])
            rpt_extra   = splitter[3] if len(splitter) > 3 else ""
            member_r = await context.bot.get_chat_member(rpt_chat_id, uid)
            if member_r.status not in ("administrator", "creator") and not is_admin:
                await safe_answer(query, "Only admins can act on reports.", show_alert=True)
                return
            if rpt_action == "kick":
                await context.bot.ban_chat_member(rpt_chat_id, rpt_uid)
                await context.bot.unban_chat_member(rpt_chat_id, rpt_uid)
                await safe_answer(query, f"✅ Kicked {e(rpt_extra[:30])}")
                try:
                    await query.message.edit_text(
                        f"<b>✅ Kicked</b> {e(rpt_extra)}.", parse_mode="HTML"
                    )
                except Exception:
                    pass
            elif rpt_action == "banned":
                await context.bot.ban_chat_member(rpt_chat_id, rpt_uid)
                await safe_answer(query, f"✅ Banned {e(rpt_extra[:30])}")
                try:
                    await query.message.edit_text(
                        f"<b>🔨 Banned</b> {e(rpt_extra)}.", parse_mode="HTML"
                    )
                except Exception:
                    pass
            elif rpt_action == "delete":
                if str(rpt_extra).isdigit():
                    await context.bot.delete_message(rpt_chat_id, int(rpt_extra))
                    await safe_answer(query, "✅ Message deleted.")
                    try:
                        await query.message.edit_text(
                            "<b>✅ Message deleted.</b>", parse_mode="HTML"
                        )
                    except Exception:
                        pass
                else:
                    await safe_answer(query, "❌ No message ID.", show_alert=True)
            else:
                await safe_answer(query, f"❌ Unknown action: {rpt_action}", show_alert=True)
        except Exception as exc_rep:
            logger.debug(f"report_ callback error: {exc_rep}")
            await safe_answer(query, f"❌ Failed: {str(exc_rep)[:50]}", show_alert=True)
        return

    # ── filter_pick: / filter_pick_cancel: ───────────────────────────────────
    if data.startswith("filter_pick:") or data.startswith("filter_pick_cancel:"):
        try:
            from filter_poster import filter_pick_callback
            await filter_pick_callback(update, context)
        except ImportError:
            if data.startswith("filter_pick_cancel:"):
                try:
                    await query.message.delete()
                except Exception:
                    pass
            elif data.startswith("filter_pick:"):
                try:
                    await query.message.delete()
                except Exception:
                    pass
        except Exception as exc_fp:
            logger.debug(f"filter_pick callback error: {exc_fp}")
            try:
                await query.message.delete()
            except Exception:
                pass
        return

    # ── alpha_filter_pick: / alpha_page: / alpha_close: ──────────────────────
    if data.startswith(("alpha_filter_pick:", "alpha_page:", "alpha_close:")):
        try:
            from filter_poster import index_callback
            await index_callback(update, context)
        except Exception as exc_afp:
            logger.debug(f"alpha_* callback error: {exc_afp}")
            if data.startswith("alpha_close:"):
                try:
                    await query.message.delete()
                except Exception:
                    pass
        return

    # ── idx_sel: / idx_nav: / idx_close / idx_noop ───────────────────────────
    if data.startswith("idx_sel:") or data.startswith("idx_nav:") or data in ("idx_close", "idx_noop"):
        try:
            from filter_poster import index_callback
            await index_callback(update, context)
        except Exception as exc_idx:
            logger.debug(f"idx callback error: {exc_idx}")
            if data == "idx_close":
                try:
                    await query.message.delete()
                except Exception:
                    pass
        return

    # ── speedtest_image / speedtest_text ──────────────────────────────────────
    if data in ("speedtest_image", "speedtest_text"):
        try:
            import speedtest as _stlib
            await safe_answer(query, small_caps("running speed test… this may take ~30 seconds."))
            _loop_st = asyncio.get_event_loop()
            def _run_st():
                s = _stlib.Speedtest()
                s.get_best_server()
                s.download()
                s.upload()
                return s
            s_obj = await _loop_st.run_in_executor(None, _run_st)
            r = s_obj.results.dict()
            dl  = round(r["download"] / 1e6, 2)
            ul  = round(r["upload"]   / 1e6, 2)
            pg  = round(r["ping"], 2)
            srv = r.get("server", {})
            srv_name = f"{srv.get('name','?')}, {srv.get('country','?')}"
            isp_name = r.get("client", {}).get("isp", "?")
            st_text = (
                "<b>🌐 Speed Test Results</b>\n\n"
                f"<b>⬇ Download:</b> <code>{dl} Mbps</code>\n"
                f"<b>⬆ Upload:</b>   <code>{ul} Mbps</code>\n"
                f"<b>📶 Ping:</b>     <code>{pg} ms</code>\n"
                f"<b>🖥 Server:</b>   <code>{e(srv_name)}</code>\n"
                f"<b>📡 ISP:</b>      <code>{e(isp_name)}</code>"
            )
            if data == "speedtest_image":
                try:
                    img_url_st = s_obj.results.share()
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
                    await context.bot.send_photo(
                        chat_id=chat_id, photo=img_url_st,
                        caption=st_text, parse_mode="HTML",
                    )
                    return
                except Exception:
                    pass
            await _smart_edit(st_text)
        except ImportError:
            await safe_answer(query, "❌ speedtest library not installed.", show_alert=True)
        except Exception as exc_st:
            logger.debug(f"speedtest callback error: {exc_st}")
            await safe_answer(query, f"❌ Speed test failed: {str(exc_st)[:60]}", show_alert=True)
        return

    # ── db_cleanup ────────────────────────────────────────────────────────────
    if data == "db_cleanup":
        if not is_admin:
            await safe_answer(query, "You are not allowed to use this.", show_alert=True)
            return
        try:
            await safe_answer(query, small_caps("cleaning database…"))
            try:
                await query.message.edit_text(b(small_caps("💾 cleaning database…")), parse_mode="HTML")
            except Exception:
                pass
            cleaned_links, invalid_chats, invalid_gbans = 0, 0, 0
            try:
                from database_dual import cleanup_expired_links
                cleaned_links = cleanup_expired_links() or 0
            except Exception:
                pass
            try:
                from modules.sql.users_sql import get_invalid_chats, get_invalid_gban
                invalid_chats = get_invalid_chats(update, context, True) or 0
                invalid_gbans = get_invalid_gban(update, context, True) or 0
            except Exception:
                pass
            total_dbc = cleaned_links + invalid_chats + invalid_gbans
            result_dbc = (
                b(small_caps("✅ database cleanup complete!")) + "\n\n"
                + bq(
                    f"<b>{small_caps('expired links')}:</b> {cleaned_links}\n"
                    f"<b>{small_caps('invalid chats')}:</b> {invalid_chats}\n"
                    f"<b>{small_caps('invalid gbans')}:</b> {invalid_gbans}\n"
                    f"<b>{small_caps('total cleaned')}:</b> {total_dbc}"
                )
            )
            try:
                await query.message.edit_text(result_dbc, parse_mode="HTML")
            except Exception:
                await safe_send_message(context.bot, chat_id, result_dbc)
        except Exception as exc_dbc:
            logger.debug(f"db_cleanup callback error: {exc_dbc}")
            await safe_answer(query, f"❌ Cleanup error: {str(exc_dbc)[:60]}", show_alert=True)
        return

    # ── user_join_(<id>) — Welcome module captcha ─────────────────────────────
    _user_join_m = _re.match(r"^user_join_\((.+?)\)$", data)
    if _user_join_m:
        join_uid = _user_join_m.group(1)
        try:
            join_uid_int = int(join_uid)
            if join_uid_int == uid:
                chat_obj_uj = query.message.chat if query.message else None
                if chat_obj_uj:
                    from telegram import ChatPermissions as _CP
                    await context.bot.restrict_chat_member(
                        chat_obj_uj.id, uid,
                        permissions=_CP(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True,
                            can_invite_users=True,
                            can_pin_messages=False,
                            can_send_polls=True,
                            can_change_info=False,
                        ),
                    )
                    try:
                        from modules.sql.welcome_sql import set_human_checks
                        set_human_checks(uid, chat_obj_uj.id)
                    except Exception:
                        pass
                    await safe_answer(query, "✅ Verified! You are now unmuted. Welcome!")
                    try:
                        await query.message.delete()
                    except Exception:
                        pass
            else:
                await safe_answer(query, "❌ This button is not for you!", show_alert=True)
        except Exception as exc_uj:
            logger.debug(f"user_join_ callback error: {exc_uj}")
            await safe_answer(query, "❌ Verification error — contact an admin.", show_alert=True)
        return

    # ── beat_back ─────────────────────────────────────────────────────────────
    if data == "beat_back":
        try:
            try:
                await query.message.delete()
            except Exception:
                pass
            from handlers.start import start
            await start(update, context)
        except Exception as exc_bb:
            logger.debug(f"beat_back error: {exc_bb}")
            try:
                await query.message.delete()
            except Exception:
                pass
        return

    # ── nxt / nxt+<page> ─────────────────────────────────────────────────────
    if data == "nxt" or data.startswith("nxt+"):
        try:
            from BeatVerseProbot import nxt_handler
            await nxt_handler(update, context)
        except Exception as exc_nxt:
            logger.debug(f"nxt callback error: {exc_nxt}")
            _FONT_STYLES_P2 = [
                ("special","✨"),("squares","🟦"),("squares_bold","🟧"),
                ("andalucia","🎨"),("manga","📗"),("stinky","🐟"),
                ("bubbles","🫧"),("stop","🛑"),("tiny","🔹"),
                ("skyline","🏙"),("slash","⚡"),("birds","🐦"),
                ("cloud","☁️"),("circle_dark","⚫"),("gothic","⚔️"),
                ("gothic_bolt","🗡"),("rays","🌟"),("happy","😊"),
                ("sad","😢"),("ladybug","🐞"),("qvnes","🔮"),("sim","📱"),
            ]
            rows_nxt, row_nxt = [], []
            for sn, se in _FONT_STYLES_P2:
                row_nxt.append(InlineKeyboardButton(se, callback_data=f"style+{sn}"))
                if len(row_nxt) == 3:
                    rows_nxt.append(row_nxt)
                    row_nxt = []
            if row_nxt:
                rows_nxt.append(row_nxt)
            rows_nxt.append([
                InlineKeyboardButton("◀ Back", callback_data="beat_back"),
                InlineKeyboardButton("✖ Close", callback_data="close_message"),
            ])
            try:
                await query.message.edit_reply_markup(InlineKeyboardMarkup(rows_nxt))
            except Exception:
                pass
        return

    # ── style+<name> ──────────────────────────────────────────────────────────
    if data.startswith("style+"):
        style_key = data[len("style+"):]
        try:
            from BeatVerseProbot.utils.modules.fun_strings import Fonts as _Fonts
            _FONT_MAP = {
                "typewriter":   getattr(_Fonts,"typewriter",   None),
                "outline":      getattr(_Fonts,"outline",      None),
                "serif":        getattr(_Fonts,"serief",       None),
                "bold_cool":    getattr(_Fonts,"bold_cool",    None),
                "cool":         getattr(_Fonts,"cool",         None),
                "small_cap":    getattr(_Fonts,"smallcap",     None),
                "script":       getattr(_Fonts,"script",       None),
                "script_bolt":  getattr(_Fonts,"bold_script",  None),
                "tiny":         getattr(_Fonts,"tiny",         None),
                "comic":        getattr(_Fonts,"comic",        None),
                "sans":         getattr(_Fonts,"double_struck",None),
                "bold":         getattr(_Fonts,"math_bold",    None),
                "italic":       getattr(_Fonts,"bold_italic",  None),
                "squares":      getattr(_Fonts,"square",       None),
                "circles":      getattr(_Fonts,"circle",       None),
                "gothic":       getattr(_Fonts,"gothic",       None),
                "slant":        getattr(_Fonts,"slant",        None),
                "slant_sans":   getattr(_Fonts,"slant_sans",   None),
                "underline":    getattr(_Fonts,"underline",    None),
                "strike":       getattr(_Fonts,"strike",       None),
                "sim":          getattr(_Fonts,"sim",          None),
                "andalucia":    getattr(_Fonts,"andalucia",    None),
                "manga":        getattr(_Fonts,"manga",        None),
                "stinky":       getattr(_Fonts,"stinky",       None),
                "bubbles":      getattr(_Fonts,"bubbles",      None),
                "stop":         getattr(_Fonts,"stop",         None),
                "skyline":      getattr(_Fonts,"skyline",      None),
                "slash":        getattr(_Fonts,"slash",        None),
                "birds":        getattr(_Fonts,"birds",        None),
                "cloud":        getattr(_Fonts,"cloud",        None),
                "circle_dark":  getattr(_Fonts,"circle_dark",  None),
                "gothic_bolt":  getattr(_Fonts,"gothic_bolt",  None),
                "rays":         getattr(_Fonts,"rays",         None),
                "happy":        getattr(_Fonts,"happy",        None),
                "sad":          getattr(_Fonts,"sad",          None),
                "ladybug":      getattr(_Fonts,"ladybug",      None),
                "qvnes":        getattr(_Fonts,"qvnes",        None),
                "special":      getattr(_Fonts,"special",      None),
                "squares_bold": getattr(_Fonts,"squares_bold", None),
                "arrows":       getattr(_Fonts,"arrows",       None),
                "frozen":       getattr(_Fonts,"frozen",       None),
            }
            font_fn = _FONT_MAP.get(style_key)
            orig_text_s = context.user_data.get("style_original_text", "")
            if not orig_text_s and query.message and query.message.reply_to_message:
                orig_text_s = (query.message.reply_to_message.text or "").strip()
            if not orig_text_s:
                try:
                    raw_txt = query.message.text or query.message.caption or ""
                    orig_text_s = raw_txt.split("\n\n",1)[-1].strip() if "\n\n" in raw_txt else raw_txt.strip()
                except Exception:
                    orig_text_s = "Hello World"
            if font_fn and orig_text_s:
                try:
                    styled_result = font_fn(orig_text_s)
                except Exception:
                    styled_result = orig_text_s
            else:
                styled_result = orig_text_s
            new_text_s = f"<b>🔤 Style: {e(style_key)}</b>\n\n{e(styled_result)}"
            try:
                await query.message.edit_text(
                    new_text_s, parse_mode="HTML",
                    reply_markup=query.message.reply_markup
                )
            except Exception:
                pass
            await safe_answer(query, f"✅ Applied: {style_key}")
        except ImportError:
            await safe_answer(query, f"Style: {style_key}")
        except Exception as exc_style:
            logger.debug(f"style+ callback error: {exc_style}")
            await safe_answer(query, f"❌ Style error: {str(exc_style)[:50]}", show_alert=True)
        return

    # ── wlc_* — Welcome module ────────────────────────────────────────────────
    if data.startswith("wlc_"):
        try:
            from modules.welcome import welcome_callback_sync
            welcome_callback_sync(update, context)
        except Exception as exc_wlc:
            logger.debug(f"wlc_ callback error: {exc_wlc}")
            await safe_answer(query, small_caps("welcome setting updated."))
        return

    # ── fwd_toggle / fwd_set_dest / fwd_clear / fwd_clear_confirm ─────────────
    if data == "fwd_toggle":
        if not is_admin:
            return
        from database_dual import get_setting, set_setting
        _fwd_cur = get_setting("autoforward_enabled", "false")
        _fwd_new = "false" if _fwd_cur == "true" else "true"
        set_setting("autoforward_enabled", _fwd_new)
        await safe_answer(query, f"Auto-Forward {'enabled ✅' if _fwd_new=='true' else 'disabled 🔴'}")
        try:
            await query.delete_message()
        except Exception:
            pass
        try:
            from handlers.admin_panel import show_fwd_source_panel
            await show_fwd_source_panel(context, chat_id)
        except Exception:
            pass
        return

    if data == "fwd_set_dest":
        if not is_admin:
            return
        user_states[uid] = "AWAITING_FWD_DEST"
        try:
            await query.delete_message()
        except Exception:
            pass
        await safe_send_message(
            context.bot, chat_id,
            b(small_caps("📥 set auto-forward destination")) + "\n\n"
            + bq(small_caps(
                "send the destination channel/group @username or numeric ID.\n"
                "messages from the source will be forwarded here."
            )),
            reply_markup=InlineKeyboardMarkup([[_back_btn("fsub_fwd_source"), _close_btn()]]),
        )
        return

    if data == "fwd_clear":
        if not is_admin:
            return
        await safe_edit_text(
            query,
            b(small_caps("⚠️ clear auto-forward config?")) + "\n\n"
            + bq(small_caps("this removes the source and destination settings.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("✅ confirm"), callback_data="fwd_clear_confirm"),
                _back_btn("fsub_fwd_source"),
            ]]),
        )
        return

    if data == "fwd_clear_confirm":
        if not is_admin:
            return
        from database_dual import set_setting
        set_setting("autoforward_source_chat", "")
        set_setting("autoforward_dest_chat",   "")
        set_setting("autoforward_enabled",     "false")
        await safe_answer(query, small_caps("✅ auto-forward config cleared."))
        try:
            await query.delete_message()
        except Exception:
            pass
        try:
            from handlers.admin_panel import show_fwd_source_panel
            await show_fwd_source_panel(context, chat_id)
        except Exception:
            pass
        return

    # ── {prefix}_module({chat},{page}) — BeatVerse module paginator ───────────
    _mod_m = _re.match(r"^(.+?)_module\((\d+)(?:,(\d+))?\)$", data)
    if _mod_m:
        try:
            from BeatVerseProbot import module_button_handler
            await module_button_handler(update, context)
        except Exception as exc_mod:
            logger.debug(f"_module() callback error: {exc_mod}")
            await safe_answer(query, f"Module: {_mod_m.group(1)}")
        return

    # ── {prefix}_next({page}) / {prefix}_prev({page}) ────────────────────────
    _nav_m = _re.match(r"^(.+?)_(next|prev)\((\d+)\)$", data)
    if _nav_m:
        try:
            from BeatVerseProbot import paginator_handler
            await paginator_handler(update, context)
        except Exception as exc_nav:
            logger.debug(f"_next/_prev callback error: {exc_nav}")
            await safe_answer(query, small_caps("page navigation unavailable."))
        return

    # ── anthmb_* (explicit fallback — normally caught by anime module) ─────────
    if data.startswith("anthmb_"):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc_anthmb:
            logger.debug(f"anthmb_ fallback error: {exc_anthmb}")
            if data == "anthmb_cancel":
                try:
                    await query.message.delete()
                except Exception:
                    pass
        return

    # ── anpick_* (explicit fallback) ──────────────────────────────────────────
    if data.startswith("anpick_"):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc_anpick:
            logger.debug(f"anpick_ fallback error: {exc_anpick}")
            if data == "anpick_cancel":
                try:
                    await query.message.delete()
                except Exception:
                    pass
        return

    # ── lang_* / size_* (explicit fallback) ───────────────────────────────────
    if data.startswith("lang_") or data.startswith("size_"):
        try:
            from modules.anime import _anime_callback
            await _anime_callback(update, context)
        except Exception as exc_ls:
            logger.debug(f"lang_/size_ fallback error: {exc_ls}")
            await safe_answer(query, small_caps("processing…"))
        return

    # ── broadcast_mode_* (safety net — normally caught earlier) ───────────────
    if data.startswith("broadcast_mode_"):
        if not is_admin:
            return
        mode_bm = data[len("broadcast_mode_"):]
        context.user_data["broadcast_mode"] = mode_bm
        _BM_LABELS = {
            "normal":      "📨 Normal",
            "pin":         "📌 Pin Message",
            "silent":      "🔕 Silent",
            "auto_delete": "⏳ Auto-Delete 24h",
        }
        label_bm = _BM_LABELS.get(mode_bm, mode_bm.replace("_"," ").title())
        await safe_edit_text(
            query,
            b(f"📣 Broadcast Mode: {label_bm}") + "\n\n"
            + bq(small_caps("send /confirm to broadcast or /cancel to abort.")),
            reply_markup=InlineKeyboardMarkup([[
                bold_button(small_caps("🔙 cancel"), callback_data="admin_back")
            ]]),
        )
        user_states[uid] = PENDING_BROADCAST_OPTIONS
        return

    # ── inv_loading: / inv_ready: (explicit fallback) ─────────────────────────
    if data.startswith("inv_loading:") or data.startswith("inv_ready:"):
        try:
            from handlers.inline_handler import handle_inv_loading_callback
            await handle_inv_loading_callback(update, context)
        except Exception as exc_inv:
            logger.debug(f"inv_loading/ready fallback error: {exc_inv}")
            parts_inv = data.split(":", 2)
            if len(parts_inv) >= 3 and parts_inv[2]:
                try:
                    from handlers.start import handle_deep_link
                    await handle_deep_link(update, context, parts_inv[2])
                except Exception:
                    pass
        return

    # ══════════════════════════════════════════════════════════════════════════
    # NAMESPACE CATCH-ALLS
    # Log unrecognised callbacks in a known namespace and soft-fail them with
    # an informative toast — no button ever silently does nothing.
    # ══════════════════════════════════════════════════════════════════════════

    _NAMESPACE_CATCH_ALLS = [
        ("chatbot_",     True,  "chatbot"),
        ("fp_",          True,  "filter poster"),
        ("cat_",         True,  "category"),
        ("af_",          True,  "auto-forward"),
        ("cw_",          True,  "channel welcome"),
        ("au_",          True,  "manga tracking"),
        ("pe_",          True,  "poster engine"),
        ("clone_",       True,  "clone"),
        ("fsub_",        True,  "fsub"),
        ("search_result_",False,"search result"),
        ("mdex_",        False, "mangadex"),
        ("user_",        False, "user"),
        ("panel_img_",   True,  "panel image"),
        ("upload_",      True,  "upload"),
        ("env_",         True,  "env"),
        ("mod_",         True,  "module"),
        ("adm_",         True,  "admin"),
        ("uf_help:",     False, "feature help"),
        ("deeplink_",    False, "deeplink"),
        ("flag_toggle_", True,  "feature flag"),
        ("poster_",      True,  "poster"),
        ("imgn:",        False, "image nav"),
        ("text_style_set_",True,"text style"),
        ("btn_style_set_",True,"button style"),
        ("fp_wm_",       True,  "watermark"),
        ("fp_tmpl_",     True,  "poster template"),
        ("fp_mode_",     True,  "filter mode"),
        ("pe_send_",     True,  "poster send"),
        ("request_anime:",False,"anime request"),
        ("request_hindi:",False,"hindi request"),
    ]

    for _ns_prefix, _ns_admin_only, _ns_label in _NAMESPACE_CATCH_ALLS:
        if data.startswith(_ns_prefix):
            if _ns_admin_only and not is_admin:
                await safe_answer(query, small_caps("admin only action."), show_alert=True)
                return
            logger.warning(f"Unhandled {_ns_label} callback: {data!r} from user {uid}")
            await safe_answer(
                query,
                small_caps(f"unknown {_ns_label} action — update your bot."),
                show_alert=(_ns_admin_only),
            )
            return


    # ── add_chat(<chat_id>) / rm_chat(<chat_id>) — Chatbot module (PTB style) ──
    import re as _re2
    _add_chat_m = _re2.match(r"^add_chat\((.+?)\)$", data)
    if _add_chat_m:
        target_chat_id = _add_chat_m.group(1).strip()
        try:
            chat_obj_ac = query.message.chat if query.message else None
            if chat_obj_ac:
                member_ac = await context.bot.get_chat_member(chat_obj_ac.id, uid)
                if member_ac.status in ("administrator", "creator") or is_admin:
                    try:
                        from modules.sql.chatbot_sql import enable_chatbot
                        enable_chatbot(int(target_chat_id))
                    except ImportError:
                        from database_dual import set_setting
                        set_setting(f"chatbot_{target_chat_id}", "true")
                    bot_name = (await context.bot.get_me()).first_name
                    try:
                        await query.message.edit_text(
                            f"<b>✅ {e(bot_name)} chatbot enabled</b> by "
                            f"{query.from_user.mention_html()}.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                    await safe_answer(query, "✅ Chatbot enabled for this chat.")
                else:
                    await safe_answer(query, "Only admins can do this.", show_alert=True)
        except Exception as exc_ac:
            logger.debug(f"add_chat callback error: {exc_ac}")
            await safe_answer(query, f"❌ Error: {str(exc_ac)[:50]}", show_alert=True)
        return

    _rm_chat_m = _re2.match(r"^rm_chat\((.+?)\)$", data)
    if _rm_chat_m:
        target_chat_id_r = _rm_chat_m.group(1).strip()
        try:
            chat_obj_rc = query.message.chat if query.message else None
            if chat_obj_rc:
                member_rc = await context.bot.get_chat_member(chat_obj_rc.id, uid)
                if member_rc.status in ("administrator", "creator") or is_admin:
                    try:
                        from modules.sql.chatbot_sql import disable_chatbot
                        disable_chatbot(int(target_chat_id_r))
                    except ImportError:
                        from database_dual import set_setting
                        set_setting(f"chatbot_{target_chat_id_r}", "false")
                    bot_name_r = (await context.bot.get_me()).first_name
                    try:
                        await query.message.edit_text(
                            f"<b>❌ {e(bot_name_r)} chatbot disabled</b> by "
                            f"{query.from_user.mention_html()}.",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                    await safe_answer(query, "❌ Chatbot disabled for this chat.")
                else:
                    await safe_answer(query, "Only admins can do this.", show_alert=True)
        except Exception as exc_rc:
            logger.debug(f"rm_chat callback error: {exc_rc}")
            await safe_answer(query, f"❌ Error: {str(exc_rc)[:50]}", show_alert=True)
        return

    # ── panel_img_page_<n> — Panel image list pagination ──────────────────────
    if data.startswith("panel_img_page_"):
        if not is_admin:
            return
        try:
            page_pip = int(data.split("_")[-1])
        except (ValueError, IndexError):
            page_pip = 0
        try:
            from handlers.misc_cmds import _show_panel_img_list
            await _show_panel_img_list(context.bot, chat_id, query=query, page=page_pip)
        except Exception as exc_pip:
            logger.debug(f"panel_img_page_ error: {exc_pip}")
            # Inline fallback
            try:
                from core.panel_image import get_panel_db_images
                items = get_panel_db_images()
                PAGE_SZ = 10
                start_pip = page_pip * PAGE_SZ
                total_pip = len(items)
                page_items = items[start_pip:start_pip + PAGE_SZ]
                text_pip = (
                    b(small_caps(f"🖼 panel images — page {page_pip + 1}")) + "\n\n"
                    + bq(f"<b>{small_caps('total')}:</b> {code(str(total_pip))} images")
                )
                for item in page_items:
                    idx_pip  = item.get("index", "?")
                    fid_pip  = (item.get("file_id", "") or "")[:20]
                    text_pip += f"\n• #{idx_pip}: <code>{e(fid_pip)}…</code>"
                nav_pip = []
                if page_pip > 0:
                    nav_pip.append(_btn("🔙", f"panel_img_page_{page_pip - 1}"))
                if start_pip + PAGE_SZ < total_pip:
                    nav_pip.append(_btn("🔜", f"panel_img_page_{page_pip + 1}"))
                rows_pip = []
                if nav_pip:
                    rows_pip.append(nav_pip)
                rows_pip.append([
                    _btn(small_caps("➕ add image"), "panel_img_add_urls"),
                    _back_btn("admin_back"), _close_btn(),
                ])
                await safe_edit_text(query, text_pip, reply_markup=InlineKeyboardMarkup(rows_pip))
            except Exception as exc_pip2:
                await safe_answer(query, f"❌ Image list error: {str(exc_pip2)[:50]}", show_alert=True)
        return


    # ── FINAL UNHANDLED FALLBACK ──────────────────────────────────────────────
    logger.debug(f"Unhandled callback: {data!r} from user {uid}")

