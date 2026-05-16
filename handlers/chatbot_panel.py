"""
handlers/chatbot_panel.py
==========================
Admin panel for Dual AI Chatbot Engine.

Flow:
  admin_chatbot_panel          → GC selector (list known GCs + Add GC)
  chatbot_gc_view:{gc_id}      → per-GC settings (toggle, gender, assigned set)
  chatbot_gc_toggle:{gc_id}    → toggle enabled for that GC (clears cache!)
  chatbot_gender_{g}:{gc_id}   → cycle gender for GC
  chatbot_gc_assign:{gc_id}    → show set selector for that GC
  chatbot_assign_set:{gc_id}:{set_name} → assign API set to GC
  chatbot_sets                 → manage API key sets
  chatbot_set_view:{set_name}  → keys inside one set
  chatbot_add_key:{set_name}:{provider} → prompt to add key (state)
  chatbot_del_key:{set_name}:{provider}:{slot} → delete key
  chatbot_usage_stats:{gc_id}  → refresh usage for GC's assigned set
  chatbot_add_gc               → prompt admin to enter new GC chat_id (state)
"""
import html
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.config import ADMIN_ID, OWNER_ID
from core.text_utils import b, bq, small_caps, code
from core.logging_setup import logger


def _is_admin(uid: int) -> bool:
    return uid in (ADMIN_ID, OWNER_ID)


def _bar(pct: int, width: int = 14) -> str:
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    emoji = "🟢" if pct < 60 else ("🟡" if pct < 85 else "🔴")
    return f"{emoji} [{bar}] {pct}%"


# ── GC list helpers ───────────────────────────────────────────────────────────

def _get_known_gcs() -> list:
    """Return list of (chat_id, set_name) for all GCs in chatbot_chat_assign."""
    try:
        from database_dual import _pg_exec_many
        from core.chatbot_engine import CHAT_ASSIGN_TABLE
        rows = _pg_exec_many(
            f"SELECT chat_id, set_name FROM {CHAT_ASSIGN_TABLE} ORDER BY updated_at DESC LIMIT 20"
        ) or []
        return [(int(r[0]), r[1]) for r in rows]
    except Exception:
        return []


def _get_all_set_names() -> list:
    try:
        from core.chatbot_engine import get_all_sets
        sets = get_all_sets()
        return sets if sets else ["default"]
    except Exception:
        return ["default"]


# ── Main panel: GC selector ───────────────────────────────────────────────────

def _build_main_panel_text() -> str:
    gcs  = _get_known_gcs()
    sets = _get_all_set_names()
    text = (
        f"<b>🤖 {small_caps('AI Chatbot — Admin Panel')}</b>\n\n"
        "<blockquote>"
        f"🗂 <b>{small_caps('API Sets')}:</b> {len(sets)} "
        f"({', '.join('<code>' + html.escape(s) + '</code>' for s in sets[:4])})\n"
        f"📡 <b>{small_caps('Linked GCs')}:</b> {len(gcs)}\n"
        "</blockquote>\n\n"
        f"<i>{small_caps('Select a group to configure, or manage API key sets.')}</i>"
    )
    return text


def _build_main_panel_kb() -> InlineKeyboardMarkup:
    gcs  = _get_known_gcs()
    rows = []
    for gc_id, set_name in gcs[:8]:
        label = f"💬 {gc_id}  [{html.escape(set_name)}]"
        rows.append([InlineKeyboardButton(label, callback_data=f"chatbot_gc_view:{gc_id}")])
    rows.append([
        InlineKeyboardButton("➕ Add GC", callback_data="chatbot_add_gc"),
        InlineKeyboardButton("🔑 API Sets", callback_data="chatbot_sets"),
    ])
    rows.append([
        InlineKeyboardButton("🔙 Back", callback_data="admin_settings"),
        InlineKeyboardButton("✖ Close", callback_data="close_message"),
    ])
    return InlineKeyboardMarkup(rows)


# ── Per-GC panel ──────────────────────────────────────────────────────────────

def _build_gc_panel_text(gc_id: int) -> str:
    from core.chatbot_engine import (
        get_chatbot_enabled, get_gc_gender, get_set_for_chat,
        get_usage_stats, get_active_sessions,
    )
    enabled  = get_chatbot_enabled(gc_id)
    gender   = get_gc_gender(gc_id)
    set_name = get_set_for_chat(gc_id)
    active   = get_active_sessions(gc_id)
    stats    = get_usage_stats(gc_id)
    s_icon   = "🟢" if enabled else "🔴"
    g_icon   = {"boy": "👦", "girl": "👧", "bot": "🤖"}.get(gender, "🤖")

    text = (
        f"<b>💬 {small_caps('GC Settings')}</b>\n"
        f"<code>{gc_id}</code>\n\n"
        "<blockquote>"
        f"{s_icon} <b>{small_caps('Status')}:</b> {small_caps('ON' if enabled else 'OFF')}\n"
        f"{g_icon} <b>{small_caps('Personality')}:</b> {small_caps(gender.title())}\n"
        f"🗂 <b>{small_caps('API Set')}:</b> <code>{html.escape(set_name)}</code>\n"
        f"👥 <b>{small_caps('Active Sessions')}:</b> {active}\n"
        "</blockquote>\n\n"
    )
    stat_list = stats.get("stats", [])
    if stat_list:
        text += f"<b>📊 {small_caps('Usage —')} <code>{html.escape(set_name)}</code></b>\n"
        for s in stat_list:
            text += (
                f"<code>{s['provider'].title()} #{s['slot']}</code>\n"
                f"{_bar(s['pct'])}  {s['used']}/{s['limit']}\n"
            )
    else:
        text += f"<i>{small_caps('No API keys in set')} <code>{html.escape(set_name)}</code></i>\n"
    return text


def _build_gc_panel_kb(gc_id: int) -> InlineKeyboardMarkup:
    from core.chatbot_engine import get_chatbot_enabled, get_gc_gender
    enabled = get_chatbot_enabled(gc_id)
    gender  = get_gc_gender(gc_id)
    next_g  = {"boy": "girl", "girl": "bot", "bot": "boy"}
    g_lbl   = {"boy": "👦 Boy→Girl", "girl": "👧 Girl→Bot", "bot": "🤖 Bot→Boy"}
    rows = [
        [
            InlineKeyboardButton("🟢 ON→OFF" if enabled else "🔴 OFF→ON",
                                 callback_data=f"chatbot_gc_toggle:{gc_id}"),
            InlineKeyboardButton(g_lbl.get(gender, "🤖"),
                                 callback_data=f"chatbot_gender_{next_g.get(gender,'bot')}:{gc_id}"),
        ],
        [
            InlineKeyboardButton("🗂 Change API Set", callback_data=f"chatbot_gc_assign:{gc_id}"),
            InlineKeyboardButton("📊 Refresh",        callback_data=f"chatbot_usage_stats:{gc_id}"),
        ],
        [
            InlineKeyboardButton("🔙 All GCs", callback_data="admin_chatbot_panel"),
            InlineKeyboardButton("✖ Close",    callback_data="close_message"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


# ── Set selector for a GC ─────────────────────────────────────────────────────

def _build_set_selector_text(gc_id: int) -> str:
    from core.chatbot_engine import get_set_for_chat
    cur = get_set_for_chat(gc_id)
    return (
        f"<b>🗂 {small_caps('Assign API Set')}</b>\n"
        f"<code>{gc_id}</code>\n\n"
        f"<b>{small_caps('Current')}:</b> <code>{html.escape(cur)}</code>\n\n"
        f"<i>{small_caps('Tap a set to assign it to this GC:')}</i>"
    )


def _build_set_selector_kb(gc_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"🗂 {html.escape(s)}",
                                  callback_data=f"chatbot_assign_set:{gc_id}:{s}")]
            for s in _get_all_set_names()]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data=f"chatbot_gc_view:{gc_id}")])
    return InlineKeyboardMarkup(rows)


# ── Sets manager ──────────────────────────────────────────────────────────────

def _build_sets_panel_text() -> str:
    sets = _get_all_set_names()
    text = f"<b>🔑 {small_caps('API Key Sets')}</b>\n\n"
    for s in sets:
        from core.chatbot_engine import get_api_keys_for_set
        keys = get_api_keys_for_set(s)
        g_n  = len(keys.get("gemini", []))
        r_n  = len(keys.get("groq",   []))
        text += f"🗂 <code>{html.escape(s)}</code> — Gemini: {g_n}  Groq: {r_n}\n"
    return text


def _build_sets_panel_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"🗂 {html.escape(s)}", callback_data=f"chatbot_set_view:{s}")]
            for s in _get_all_set_names()]
    rows.append([InlineKeyboardButton("➕ New Set", callback_data="chatbot_new_set")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="admin_chatbot_panel")])
    return InlineKeyboardMarkup(rows)


def _build_set_view_text(set_name: str) -> str:
    from core.chatbot_engine import get_api_keys_for_set
    keys = get_api_keys_for_set(set_name)
    return (
        f"<b>🗂 {small_caps('Set')}: <code>{html.escape(set_name)}</code></b>\n\n"
        f"🔑 <b>{small_caps('Gemini')}:</b> {len(keys.get('gemini', []))}\n"
        f"⚡ <b>{small_caps('Groq')}:</b> {len(keys.get('groq', []))}\n"
    )


def _build_set_view_kb(set_name: str) -> InlineKeyboardMarkup:
    from core.chatbot_engine import get_api_keys_for_set
    keys = get_api_keys_for_set(set_name)
    rows = []
    for i, k in enumerate(keys.get("gemini", [])[:5], 1):
        rows.append([
            InlineKeyboardButton(f"🔑 Gemini #{i}: {k[:10]}…", callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"chatbot_del_key:{set_name}:gemini:{i}"),
        ])
    for i, k in enumerate(keys.get("groq", [])[:5], 1):
        rows.append([
            InlineKeyboardButton(f"⚡ Groq #{i}: {k[:10]}…", callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"chatbot_del_key:{set_name}:groq:{i}"),
        ])
    rows += [
        [
            InlineKeyboardButton("➕ Gemini", callback_data=f"chatbot_add_key:{set_name}:gemini"),
            InlineKeyboardButton("➕ Groq",   callback_data=f"chatbot_add_key:{set_name}:groq"),
        ],
        [InlineKeyboardButton("🔙 All Sets", callback_data="chatbot_sets")],
    ]
    return InlineKeyboardMarkup(rows)


# ── Safe edit helper ──────────────────────────────────────────────────────────

async def _edit(query, text: str, kb: InlineKeyboardMarkup) -> None:
    try:
        if query.message and query.message.photo:
            await query.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


# ── Main dispatcher ───────────────────────────────────────────────────────────

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

    uid = query.from_user.id if query.from_user else 0
    cb  = query.data or ""

    if not _is_admin(uid):
        try:
            await query.answer("⛔ Admin only.", show_alert=True)
        except Exception:
            pass
        return

    # ── MAIN PANEL ────────────────────────────────────────────────────────────
    if cb == "admin_chatbot_panel":
        await _edit(query, _build_main_panel_text(), _build_main_panel_kb())
        return

    # ── PER-GC VIEW ───────────────────────────────────────────────────────────
    if cb.startswith("chatbot_gc_view:"):
        gc_id = int(cb.split(":", 1)[1])
        try:
            from core.chatbot_engine import get_set_for_chat, assign_chat_to_set
            assign_chat_to_set(gc_id, get_set_for_chat(gc_id))  # ensure row exists
        except Exception:
            pass
        await _edit(query, _build_gc_panel_text(gc_id), _build_gc_panel_kb(gc_id))
        return

    # ── TOGGLE ────────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_gc_toggle:"):
        gc_id = int(cb.split(":", 1)[1])
        from core.chatbot_engine import get_chatbot_enabled, _enabled_cache
        from database_dual import set_setting
        cur     = get_chatbot_enabled(gc_id)
        new_val = "false" if cur else "true"
        set_setting(f"chatbot_{gc_id}", new_val)
        _enabled_cache.pop(gc_id, None)           # ← invalidate cache
        word = "enabled ✅" if new_val == "true" else "disabled 🔕"
        try:
            await query.answer(f"Chatbot {word}", show_alert=False)
        except Exception:
            pass
        await _edit(query, _build_gc_panel_text(gc_id), _build_gc_panel_kb(gc_id))
        return

    # ── SET GENDER ────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_gender_"):
        rest    = cb[len("chatbot_gender_"):]
        parts   = rest.split(":", 1)
        g       = parts[0]
        gc_id   = int(parts[1]) if len(parts) > 1 else uid
        from core.chatbot_engine import set_gc_gender
        set_gc_gender(gc_id, g)
        try:
            await query.answer(f"Personality → {g} ✅")
        except Exception:
            pass
        await _edit(query, _build_gc_panel_text(gc_id), _build_gc_panel_kb(gc_id))
        return

    # ── ASSIGN SET SELECTOR ───────────────────────────────────────────────────
    if cb.startswith("chatbot_gc_assign:"):
        gc_id = int(cb.split(":", 1)[1])
        await _edit(query, _build_set_selector_text(gc_id), _build_set_selector_kb(gc_id))
        return

    if cb.startswith("chatbot_assign_set:"):
        _, gc_part, set_name = cb.split(":", 2)
        gc_id = int(gc_part)
        from core.chatbot_engine import assign_chat_to_set
        assign_chat_to_set(gc_id, set_name)
        try:
            await query.answer(f"Set '{set_name}' assigned ✅")
        except Exception:
            pass
        await _edit(query, _build_gc_panel_text(gc_id), _build_gc_panel_kb(gc_id))
        return

    # ── USAGE REFRESH ─────────────────────────────────────────────────────────
    if cb.startswith("chatbot_usage_stats:"):
        gc_id = int(cb.split(":", 1)[1])
        await _edit(query, _build_gc_panel_text(gc_id), _build_gc_panel_kb(gc_id))
        return

    # ── SETS MANAGER ──────────────────────────────────────────────────────────
    if cb == "chatbot_sets":
        await _edit(query, _build_sets_panel_text(), _build_sets_panel_kb())
        return

    if cb.startswith("chatbot_set_view:"):
        set_name = cb.split(":", 1)[1]
        await _edit(query, _build_set_view_text(set_name), _build_set_view_kb(set_name))
        return

    # ── ADD KEY ───────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_add_key:"):
        parts    = cb[len("chatbot_add_key:"):].split(":", 1)
        set_name = parts[0]
        provider = parts[1] if len(parts) > 1 else "gemini"
        p_name   = "Google Gemini" if provider == "gemini" else "Groq"
        help_url = ("https://aistudio.google.com/apikey" if provider == "gemini"
                    else "https://console.groq.com/keys")
        prompt = (
            f"<b>➕ Add {html.escape(p_name)} → <code>{html.escape(set_name)}</code></b>\n\n"
            f"<i>Reply with your API key.</i>  "
            f"<a href='{help_url}'>Get key here</a>"
        )
        await _edit(query, prompt, InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Cancel", callback_data=f"chatbot_set_view:{set_name}")
        ]]))
        try:
            from core.state_machine import user_states
            user_states[uid] = f"chatbot_key:{set_name}:{provider}"
        except Exception:
            pass
        return

    # ── NEW SET ───────────────────────────────────────────────────────────────
    if cb == "chatbot_new_set":
        prompt = (
            f"<b>➕ {small_caps('Create New API Key Set')}</b>\n\n"
            f"<i>Reply with the set name (e.g. <code>group2</code>).</i>\n"
            f"Then add Gemini + Groq keys to it."
        )
        await _edit(query, prompt, InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Cancel", callback_data="chatbot_sets")
        ]]))
        try:
            from core.state_machine import user_states
            user_states[uid] = "chatbot_new_set_name"
        except Exception:
            pass
        return

    # ── DELETE KEY ────────────────────────────────────────────────────────────
    if cb.startswith("chatbot_del_key:"):
        parts    = cb[len("chatbot_del_key:"):].split(":")
        set_name = parts[0]
        provider = parts[1] if len(parts) > 1 else "gemini"
        slot     = int(parts[2]) if len(parts) > 2 else 1
        from core.chatbot_engine import delete_api_key_from_set
        delete_api_key_from_set(set_name, provider, slot)
        try:
            await query.answer(f"Key #{slot} deleted.")
        except Exception:
            pass
        await _edit(query, _build_set_view_text(set_name), _build_set_view_kb(set_name))
        return

    # ── ADD GC ────────────────────────────────────────────────────────────────
    if cb == "chatbot_add_gc":
        prompt = (
            f"<b>➕ {small_caps('Link a Group Chat')}</b>\n\n"
            f"<i>Reply with the GC's chat ID (e.g. <code>-1001234567890</code>).</i>\n"
            f"Use /id in the group to get it."
        )
        await _edit(query, prompt, InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Cancel", callback_data="admin_chatbot_panel")
        ]]))
        try:
            from core.state_machine import user_states
            user_states[uid] = "chatbot_gc_id_input"
        except Exception:
            pass
        return


# ── Input handlers (called from admin_input.py) ───────────────────────────────

async def handle_chatbot_key_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: str,
) -> bool:
    """state = chatbot_key:{set_name}:{provider}"""
    if not update.message or not update.message.text:
        return False
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return False

    parts    = state[len("chatbot_key:"):].split(":", 1)
    set_name = parts[0] if parts else "default"
    provider = parts[1] if len(parts) > 1 else "gemini"
    api_key  = update.message.text.strip()

    if not api_key or len(api_key) < 10:
        await update.message.reply_text("❌ Key too short. Send the full API key.")
        return True

    from core.chatbot_engine import get_api_keys_for_set, save_api_key_to_set
    slot = len(get_api_keys_for_set(set_name).get(provider, [])) + 1
    save_api_key_to_set(set_name, provider, api_key, slot)

    try:
        await update.message.reply_text(
            f"✅ <b>{provider.title()}</b> key #{slot} saved to "
            f"<code>{html.escape(set_name)}</code>!",
            parse_mode="HTML",
        )
    except Exception:
        pass
    try:
        from core.state_machine import user_states
        user_states.pop(uid, None)
    except Exception:
        pass
    return True


async def handle_chatbot_gc_id_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """state = chatbot_gc_id_input"""
    if not update.message or not update.message.text:
        return False
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return False

    try:
        gc_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Not a valid chat ID. Send a number like <code>-1001234567890</code>.",
            parse_mode="HTML",
        )
        return True

    from core.chatbot_engine import assign_chat_to_set, get_set_for_chat
    assign_chat_to_set(gc_id, get_set_for_chat(gc_id))
    try:
        await update.message.reply_text(
            f"✅ GC <code>{gc_id}</code> linked. Open the chatbot panel to configure it.",
            parse_mode="HTML",
        )
    except Exception:
        pass
    try:
        from core.state_machine import user_states
        user_states.pop(uid, None)
    except Exception:
        pass
    return True


async def handle_chatbot_new_set_name_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """state = chatbot_new_set_name"""
    if not update.message or not update.message.text:
        return False
    uid = update.effective_user.id if update.effective_user else 0
    if not _is_admin(uid):
        return False

    set_name = update.message.text.strip().lower().replace(" ", "_")
    if not set_name or len(set_name) > 40:
        await update.message.reply_text("❌ Invalid name. Short lowercase, no spaces.")
        return True

    try:
        await update.message.reply_text(
            f"✅ Set <code>{html.escape(set_name)}</code> ready.\n"
            f"Add keys via panel → 🔑 API Sets → select the set.",
            parse_mode="HTML",
        )
    except Exception:
        pass
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
    text = _build_main_panel_text()
    kb   = _build_main_panel_kb()
    try:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            send_to = chat_id or (update.effective_chat.id if update.effective_chat else 0)
            if send_to:
                await context.bot.send_message(send_to, text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass
