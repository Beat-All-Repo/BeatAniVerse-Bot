"""
core/state_machine.py
=====================
Conversation state constants, user_states dict, and upload progress globals.
All handlers import from here so state is shared across modules.
"""
import asyncio
from typing import Dict, Any, Optional

# ── Channel states ─────────────────────────────────────────────────────────────
(
    ADD_CHANNEL_USERNAME,
    ADD_CHANNEL_TITLE,
    ADD_CHANNEL_JBR,
) = range(3)

# ── Link states ────────────────────────────────────────────────────────────────
(
    GENERATE_LINK_IDENTIFIER,
    GENERATE_LINK_TITLE,
    GENERATE_LINK_ANIME_NAME,
) = range(3, 6)

# ── Clone states ───────────────────────────────────────────────────────────────
(ADD_CLONE_TOKEN,) = range(5, 6)

# ── Backup / move ──────────────────────────────────────────────────────────────
(
    SET_BACKUP_CHANNEL,
    PENDING_MOVE_TARGET,
) = range(6, 8)

# ── Broadcast states ───────────────────────────────────────────────────────────
(
    PENDING_BROADCAST,
    PENDING_BROADCAST_OPTIONS,
    PENDING_BROADCAST_CONFIRM,
    SCHEDULE_BROADCAST_DATETIME,
    SCHEDULE_BROADCAST_MSG,
) = range(8, 13)

# ── Category settings states ───────────────────────────────────────────────────
(
    SET_CATEGORY_TEMPLATE,
    SET_CATEGORY_BRANDING,
    SET_CATEGORY_BUTTONS,
    SET_CATEGORY_CAPTION,
    SET_CATEGORY_THUMBNAIL,
    SET_CATEGORY_FONT,
    SET_CATEGORY_LOGO,
    SET_CATEGORY_LOGO_POS,
    SET_WATERMARK_TEXT,
    SET_WATERMARK_POS,
) = range(13, 23)

# ── Auto-forward states ────────────────────────────────────────────────────────
(
    AF_ADD_CONNECTION_SOURCE,
    AF_ADD_CONNECTION_TARGET,
    AF_ADD_FILTER_WORD,
    AF_ADD_BLACKLIST_WORD,
    AF_ADD_WHITELIST_WORD,
    AF_ADD_REPLACEMENT_PATTERN,
    AF_ADD_REPLACEMENT_VALUE,
    AF_SET_DELAY,
    AF_SET_CAPTION,
    AF_BULK_FORWARD_COUNT,
) = range(23, 33)

# ── Auto manga states ──────────────────────────────────────────────────────────
(
    AU_ADD_MANGA_TITLE,
    AU_ADD_MANGA_TARGET,
    AU_REMOVE_MANGA,
    AU_CUSTOM_INTERVAL,
) = range(33, 37)

# ── Upload states ──────────────────────────────────────────────────────────────
(
    UPLOAD_SET_CAPTION,
    UPLOAD_SET_SEASON,
    UPLOAD_SET_EPISODE,
    UPLOAD_SET_TOTAL,
    UPLOAD_SET_CHANNEL,
) = range(36, 41)

# ── User management states ─────────────────────────────────────────────────────
(
    BAN_USER_INPUT,
    UNBAN_USER_INPUT,
    DELETE_USER_INPUT,
    SEARCH_USER_INPUT,
) = range(41, 45)

# ── Misc states ────────────────────────────────────────────────────────────────
PENDING_FILL_TITLE = 45

(
    SET_FEATURE_FLAG,
    SET_LINK_EXPIRY,
    SET_BOT_NAME,
    SET_WELCOME_MSG,
    SET_ADMIN_CONTACT,
) = range(46, 51)

(MANGA_SEARCH_INPUT,) = range(51, 52)
(AU_MANGA_CUSTOM_INTERVAL,) = range(52, 53)
PENDING_CHANNEL_POST = 53

(
    CW_SET_TEXT,
    CW_SET_BUTTONS,
) = range(54, 56)


# ── Global runtime state dicts ─────────────────────────────────────────────────

# user_id → current state constant (or string for named states)
user_states: Dict[int, Any] = {}

# Temp data per user for multi-step conversations
user_data_temp: Dict[int, Dict[str, Any]] = {}

# Per-user debounce locks — prevents rapid-click double-processing
_panel_locks: Dict[int, asyncio.Lock] = {}


def get_panel_lock(uid: int) -> asyncio.Lock:
    """Return (creating if needed) an asyncio.Lock for this user."""
    if uid not in _panel_locks:
        _panel_locks[uid] = asyncio.Lock()
    return _panel_locks[uid]


# ── Safety anchor tracking ─────────────────────────────────────────────────────
# chat_id → message_id of anchor
_safety_anchors: Dict[int, int] = {}


# ── Upload progress (global, shared between upload handler and channel handler) ─
from core.config import DEFAULT_CAPTION, ALL_QUALITIES

upload_progress: Dict[str, Any] = {
    "target_chat_id": None,
    "anime_name": "Anime Name",
    "season": 1,
    "episode": 1,
    "total_episode": 1,
    "video_count": 0,
    "selected_qualities": ["480p", "720p", "1080p"],
    "base_caption": DEFAULT_CAPTION,
    "auto_caption_enabled": True,
    "forward_mode": "copy",
    "protect_content": False,
}

upload_lock = asyncio.Lock()


# ── Broadcast mode constants ───────────────────────────────────────────────────
class BroadcastMode:
    NORMAL = "normal"
    AUTO_DELETE = "auto_delete"
    PIN = "pin"
    DELETE_PIN = "delete_pin"
    SILENT = "silent"


# ── AFK tracking ──────────────────────────────────────────────────────────────
# uid → {reason, time}
afk_users: Dict[int, Dict[str, Any]] = {}


# ── In-memory notes store (backed by DB for persistence) ──────────────────────
# chat_id → {name: content}
notes_memory: Dict[int, Dict[str, str]] = {}


# ── In-memory warns store (backed by DB for persistence) ──────────────────────
# "chat_id:user_id" → count
warns_memory: Dict[str, int] = {}
