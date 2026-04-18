"""
handlers/chatbot_panel.py
==========================
Admin panel for Dual AI Chatbot Engine.
Features:
  ✅ Add/remove Gemini + Groq API keys per GC (up to 5 GC slots)
  ✅ Animated API usage bar (visual progress)
  ✅ Set gender personality per GC (boy/girl/bot)
  ✅ View active sessions
  ✅ Enable/disable chatbot per GC
"""
import asyncio
import html
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.text_utils import b, bq, e, small_caps, code
from core.logging_setup import logger


def _is_admin(uid: int) -> bool:
    return uid in (ADMIN_ID, OWNER_ID)


def _bar(pct: int, width: int = 16) -> str:
    """Generate animated-style text progress bar."""
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    emoji = "🟢" if pct < 60 else ("🟡" if pct < 85 else "🔴")
    return f"{emoji} [{bar}] {pct}%"


def _build_chatbot_panel_text(chat_id: int) -> str:
    from core.chatbot_engine import (
        get_api_keys, get_usage_stats, get_gc_gender,
        get_chatbot_enabled, get_active_sessions,
    )

    enabled  = get_chatbot_enabled(chat_id)
    gender   = get_gc_gender(chat_id)
    keys     = get_api_keys(chat_id)
    active   = get_active_sessions(chat_id)
    stats    = get_usage_stats(chat_id)

    status_icon = "🟢" if enabled else "🔴"
    gender_icon = {"boy": "👦", "girl": "👧", "bot": "🤖"}.get(gender, "🤖")

    gemini_keys = keys.get("gemini", [])
    groq_keys   = keys.get("groq", [])

    text = (
        f"<b>🤖 {small_caps('AI Chatbot Engine')}</b>\n\n"
        f"<blockquote>"
        f"{status_icon} <b>{small_caps('Status')}:</b> {small_caps('ON' if enabled else 'OFF')}\n"
        f"{gender_icon} <b>{small_caps('Personality')}:</b> {small_caps(gender.title())}\n"
        f"👥 <b>{small_caps('Active Users')}:</b> {active}/3\n"
        f"🔑 <b>{small_caps('Gemini Keys')}:</b> {len(gemini_keys)}\n"
        f"⚡ <b>{small_caps('Groq Keys')}:</b> {len(groq_keys)}\n"
        f"</blockquote>\n\n"
    )

    # API usage animated bars
    stat_list = stats.get("stats", [])
    if stat_list:
        text += f"<b>📊 {small_caps('API Usage')}</b>\n"
        for s in stat_list:
            text += (
                f"<code>{s['provider'].title()} #{s['slot']}</code>\n"
                f"{_bar(s['pct'])}  {s['used']}/{s['limit']}\n"
            )
    else:
        text += f"<i>{small_caps('No API keys configured yet.')}</i>\n"

    text += f"\n<i>{small_caps('Add Gemini + Groq keys to enable chatbot.')}</i>"
    return text


def _build_chatbot_panel_kb(chat_id: int) -> InlineKeyboardMarkup:
    from core.chatbot_engine import get_chatbot_enabled, get_gc_gender, get_api_keys

    enabled = get_chatbot_enabled(chat_id)
    gender  = get_gc_gender(chat_id)
    keys    = get_api_keys(chat_id)

    toggle_label = "🟢 ON" if enabled else "🔴 OFF"
    gender_labels = {"boy": "👦 Boy", "girl": "👧 Girl", "bot": "🤖 Bot"}
    next_gender = {"boy": "girl", "girl": "bot", "bot": "boy"}

    rows = [
        [
            InlineKeyboardButton(toggle_label, callback_data=f"chatbot_gc_toggle:{chat_id}"),
            InlineKeyboardButton(
                gender_labels.get(gender, "🤖 Bot"),
                callback_data=f"chatbot_gender_{next_gender.get(gender, 'bot')}:{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton("➕ Add Gemini Key", callback_data=f"chatbot_add_gemini:{chat_id}"),
            InlineKeyboardButton("➕ Add Groq Key", callback_data=f"chatbot_add_groq:{chat_id}"),
        ],
    ]

    # Show existing keys with delete buttons
    for i, k in enumerate(keys.get("gemini", [])[:3], 1):
        rows.append([
            InlineKeyboardButton(
                f"🔑 Gemini #{i}: {k[:8]}…",
                callback_data="noop",
            ),
            InlineKeyboardButton(
                "🗑",
                callback_data=f"chatbot_del_gemini:{chat_id}:{i}",
            ),
        ])
    for i, k in enumerate(keys.get("groq", [])[:3], 1):
        rows.append([
            InlineKeyboardButton(
                f"⚡ Groq #{i}: {k[:8]}…",
                callback_data="noop",
            ),
            InlineKeyboardButton(
                "🗑",
                callback_data=f"chatbot_del_groq:{chat_id}:{i}",
            ),
        ])

    rows += [
        [InlineKeyboardButton("📊 Refresh Usage", callback_data=f"chatbot_usage_stats:{chat_id}")],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_settings"),
            InlineKeyboardButton("✖ Close", callback_data="close_message"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


async def handle_chatbot_panel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception:
        pass

    uid     = query.from_user.id if query.from_user else 0
    cb      = query.data or ""
    chat_id = query.message.chat_id if query.message else uid

    if not _is_admin(uid):
        try:
            await query.answer("⛔ Admin only.", show_alert=True)
        except Exception:
            pass
        return

    from core.chatbot_engine import (
        get_api_keys, save_api_key, delete_api_key,
        set_gc_gender, get_chatbot_enabled,
    )
    from database_dual import set_setting

    # ── MAIN PANEL ────────────────────────────────────────────────────────────
    if cb == "admin_chatbot_panel":
        text = _build_chatbot_panel_text(chat_id)
        kb   = _build_chatbot_panel_kb(chat_id)
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            try:
                await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
            except Exception:
                pass
        return

    # ── TOGGLE ENABLE ─────────────────────────────────────────────────────────
    if cb.startswith("chatbot_gc_toggle:"):
        target_chat = int(cb.split(":")[1])
        cur = (get_chatbot_enabled(target_chat))
        set_setting(f"chatbot_{target_chat}", "false" if cur else "true")
        try:
            await query.answer(f"Chatbot {'disabled' if cur else 'enabled'} ✅", show_alert=False)
        except Exception:
            pass
        # Refresh panel
        text = _build_chatbot_panel_text(target_chat)
        kb   = _build_chatbot_panel_kb(target_chat)
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        return

    # ── SET GENDER ────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_gender_"):
        # chatbot_gender_{new_gender}:{chat_id}
        parts = cb[len("chatbot_gender_"):].split(":")
        new_gender  = parts[0]
        target_chat = int(parts[1]) if len(parts) > 1 else chat_id
        set_gc_gender(target_chat, new_gender)
        try:
            await query.answer(f"Personality set to {new_gender} ✅")
        except Exception:
            pass
        text = _build_chatbot_panel_text(target_chat)
        kb   = _build_chatbot_panel_kb(target_chat)
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        return

    # ── ADD KEY — prompt for input ────────────────────────────────────────────
    if cb.startswith("chatbot_add_"):
        # chatbot_add_{provider}:{chat_id}
        parts    = cb[len("chatbot_add_"):].split(":")
        provider = parts[0]   # gemini or groq
        target   = int(parts[1]) if len(parts) > 1 else chat_id

        provider_name = "Google Gemini" if provider == "gemini" else "Groq"
        help_url = (
            "https://aistudio.google.com/apikey" if provider == "gemini"
            else "https://console.groq.com/keys"
        )

        prompt_text = (
            f"<b>➕ Add {provider_name} API Key</b>\n\n"
            f"<i>Send the API key as a reply to this message.</i>\n"
            f"Get key: <a href='{help_url}'>here</a>\n\n"
            f"<code>chatbot_pending:{provider}:{target}</code>"
        )
        try:
            await query.edit_message_text(
                prompt_text, parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Cancel", callback_data="admin_chatbot_panel")
                ]]),
            )
        except Exception:
            pass
        # Store pending state
        try:
            from core.state_machine import user_states
            user_states[uid] = f"chatbot_key:{provider}:{target}"
        except Exception:
            pass
        return

    # ── DELETE KEY ────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_del_"):
        # chatbot_del_{provider}:{chat_id}:{slot}
        parts    = cb[len("chatbot_del_"):].split(":")
        provider = parts[0]
        target   = int(parts[1]) if len(parts) > 1 else chat_id
        slot     = int(parts[2]) if len(parts) > 2 else 1
        delete_api_key(target, provider, slot)
        try:
            await query.answer(f"Key #{slot} deleted.", show_alert=False)
        except Exception:
            pass
        text = _build_chatbot_panel_text(target)
        kb   = _build_chatbot_panel_kb(target)
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        return

    # ── REFRESH USAGE STATS ───────────────────────────────────────────────────
    if cb.startswith("chatbot_usage_stats:"):
        target = int(cb.split(":")[1]) if ":" in cb else chat_id
        text = _build_chatbot_panel_text(target)
        kb   = _build_chatbot_panel_kb(target)
        try:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
        return


async def handle_chatbot_key_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    state: str,
) -> bool:
    """
    Called from admin_input.py when state starts with 'chatbot_key:'.
    Returns True if handled.
    """
    if not update.message or not update.message.text:
        return False
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return False

    # state format: chatbot_key:{provider}:{chat_id}
    parts    = state[len("chatbot_key:"):].split(":")
    provider = parts[0] if parts else "gemini"
    target   = int(parts[1]) if len(parts) > 1 else update.effective_chat.id

    api_key = update.message.text.strip()
    if not api_key or len(api_key) < 10:
        await update.message.reply_text("❌ Invalid key. Try again.")
        return True

    # Determine slot number (next available)
    from core.chatbot_engine import get_api_keys, save_api_key
    existing = get_api_keys(target).get(provider, [])
    slot = len(existing) + 1

    save_api_key(target, provider, api_key, slot)

    try:
        await update.message.reply_text(
            f"✅ {provider.title()} key #{slot} saved for chat <code>{target}</code>!",
            parse_mode="HTML",
        )
    except Exception:
        pass

    # Clear state
    try:
        from core.state_machine import user_states
        user_states.pop(uid, None)
    except Exception:
        pass

    return True


async def send_chatbot_panel(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    chat_id: Optional[int] = None,
) -> None:
    """Send the chatbot management panel."""
    if chat_id is None:
        chat_id = update.effective_chat.id if update.effective_chat else 0
    text = _build_chatbot_panel_text(chat_id)
    kb   = _build_chatbot_panel_kb(chat_id)
    try:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
