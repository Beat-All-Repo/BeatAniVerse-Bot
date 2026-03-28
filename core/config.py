"""
core/config.py
==============
All environment variable reading and bot-wide constants.
Import this module everywhere instead of reading os.getenv directly.
"""
import os
import time

# ── Tokens ────────────────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "") or os.getenv("TOKEN", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
MONGO_DB_URI: str = os.getenv("MONGO_DB_URI", "")

# ── Admin IDs — OWNER_ID and ADMIN_ID are interchangeable ────────────────────
ADMIN_ID: int = int(os.getenv("ADMIN_ID") or os.getenv("OWNER_ID") or "0")
OWNER_ID: int = int(os.getenv("OWNER_ID") or os.getenv("ADMIN_ID") or "0")
if ADMIN_ID == 0 and OWNER_ID != 0:
    ADMIN_ID = OWNER_ID
if OWNER_ID == 0 and ADMIN_ID != 0:
    OWNER_ID = ADMIN_ID

# ── External APIs ─────────────────────────────────────────────────────────────
IMGBB_API_KEY: str = os.getenv("IMGBB_API_KEY", "")
TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")

# ── Help / Channel info ───────────────────────────────────────────────────────
HELP_TEXT_CUSTOM: str = os.getenv("HELP_TEXT_CUSTOM", "")
HELP_CHANNEL_1_URL: str = os.getenv("HELP_CHANNEL_1_URL", "")
HELP_CHANNEL_1_NAME: str = os.getenv("HELP_CHANNEL_1_NAME", " ᴀɴɪᴍᴇ ᴄʜᴀɴɴᴇʟ")
HELP_CHANNEL_2_URL: str = os.getenv("HELP_CHANNEL_2_URL", "")
HELP_CHANNEL_2_NAME: str = os.getenv("HELP_CHANNEL_2_NAME", " ᴅɪsᴄᴜssɪᴏɴ")
HELP_CHANNEL_3_URL: str = os.getenv("HELP_CHANNEL_3_URL", "")
HELP_CHANNEL_3_NAME: str = os.getenv("HELP_CHANNEL_3_NAME", " ʀᴇǫᴜᴇsᴛ")

# ── Timing ────────────────────────────────────────────────────────────────────
LINK_EXPIRY_MINUTES: int = int(os.getenv("LINK_EXPIRY_MINUTES", "5"))
BROADCAST_CHUNK_SIZE: int = int(os.getenv("BROADCAST_CHUNK_SIZE", "1000"))
BROADCAST_MIN_USERS: int = int(os.getenv("BROADCAST_MIN_USERS", "5000"))
BROADCAST_INTERVAL_MIN: int = int(os.getenv("BROADCAST_INTERVAL_MIN", "20"))
RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "0.05"))

# ── Server / Webhook ──────────────────────────────────────────────────────────
PORT: int = int(os.environ.get("PORT", 10000))
WEBHOOK_URL: str = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/") + "/"

# ── Source content ────────────────────────────────────────────────────────────
WELCOME_SOURCE_CHANNEL: int = int(os.getenv("WELCOME_SOURCE_CHANNEL", "-1002530952988"))
WELCOME_SOURCE_MESSAGE_ID: int = int(os.getenv("WELCOME_SOURCE_MESSAGE_ID", "32"))
PANEL_DB_CHANNEL: int = int(os.getenv("PANEL_DB_CHANNEL", "0"))
FALLBACK_IMAGE_CHANNEL: int = int(os.getenv("FALLBACK_IMAGE_CHANNEL", "-1003794802745"))

# ── Public links / branding ──────────────────────────────────────────────────
PUBLIC_ANIME_CHANNEL_URL: str = os.getenv("PUBLIC_ANIME_CHANNEL_URL", "https://t.me/BeatAnime")
REQUEST_CHANNEL_URL: str = os.getenv("REQUEST_CHANNEL_URL", "https://t.me/Beat_Hindi_Dubbed")
ADMIN_CONTACT_USERNAME: str = os.getenv("ADMIN_CONTACT_USERNAME", "Beat_Anime_Ocean")
BOT_NAME: str = os.getenv("BOT_NAME", "Anime Bot")

# ── Image panels ──────────────────────────────────────────────────────────────
HELP_IMAGE_URL: str = os.getenv("HELP_IMAGE_URL", "")
SETTINGS_IMAGE_URL: str = os.getenv("SETTINGS_IMAGE_URL", "")
STATS_IMAGE_URL: str = os.getenv("STATS_IMAGE_URL", "")
ADMIN_PANEL_IMAGE_URL: str = os.getenv("ADMIN_PANEL_IMAGE_URL", "")
PANEL_IMAGE_FILE_ID: str = os.getenv("PANEL_IMAGE_FILE_ID", "")
WELCOME_IMAGE_URL: str = os.getenv("WELCOME_IMAGE_URL", "")
BROADCAST_PANEL_IMAGE_URL: str = os.getenv("BROADCAST_PANEL_IMAGE_URL", "")

_PANEL_PICS_RAW: str = os.getenv("PANEL_PICS", "")
PANEL_PICS: list = [u.strip() for u in _PANEL_PICS_RAW.split(",") if u.strip().startswith("http")]

# ── Sticker ───────────────────────────────────────────────────────────────────
TRANSITION_STICKER_ID: str = os.getenv("TRANSITION_STICKER", "")

# ── Button & link text customization ──────────────────────────────────────────
JOIN_BTN_TEXT: str = os.getenv("JOIN_BTN_TEXT", "Join Now")
HERE_IS_LINK_TEXT: str = os.getenv("HERE_IS_LINK_TEXT", "ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ! ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ")
LINK_EXPIRED_TEXT: str = os.getenv("LINK_EXPIRED_TEXT", "This invite link has expired. Please click the post button again.")
ANIME_BTN_TEXT: str = os.getenv("ANIME_BTN_TEXT", "Anime Channel")
REQUEST_BTN_TEXT: str = os.getenv("REQUEST_BTN_TEXT", "Request Anime")
CONTACT_BTN_TEXT: str = os.getenv("CONTACT_BTN_TEXT", "Contact Admin")
FORCE_SUB_TEXT: str = os.getenv("FORCE_SUB_TEXT", "Please join our channels first:")
BOT_WELCOME_TEXT: str = os.getenv("BOT_WELCOME_TEXT", "")
BOT_HELP_TEXT: str = os.getenv("BOT_HELP_TEXT", "")
BUTTON_STYLE: str = os.getenv("BUTTON_STYLE", "mathbold")

# ── Runtime state (mutable globals populated after bot starts) ────────────────
BOT_USERNAME: str = ""
I_AM_CLONE: bool = False
BOT_START_TIME: float = time.time()

# ── Upload manager defaults ───────────────────────────────────────────────────
DEFAULT_CAPTION = (
    "<b>◈ {anime_name}</b>\n\n"
    "<b>- Season:</b> {season}\n"
    "<b>- Episode:</b> {episode}\n"
    "<b>- Audio track:</b> Hindi | Official\n"
    "<b>- Quality:</b> {quality}\n"
    "<blockquote>"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>POWERED BY:</b> @beeetanime\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>MAIN Channel:</b> @Beat_Hindi_Dubbed\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱\n"
    " <b>Group:</b> @Beat_Anime_Discussion\n"
    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▱▱"
    "</blockquote>"
)
ALL_QUALITIES: list = ["480p", "720p", "1080p", "4K", "2160p"]
