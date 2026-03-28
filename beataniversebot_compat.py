# ====================================================================
# PLACE AT: /app/beataniversebot_compat.py
# ACTION: Replace existing file
# ====================================================================
"""
beataniversebot_compat.py
==========================
Compatibility shim — BeatVerse modules import from 'BeatVerseProbot' package.
This file re-exports everything they need from the flat bot.py globals + database_dual.

All modules that had:  from BeatVerseProbot import X
now get:               from beataniversebot_compat import X
"""

import os
import logging
import time

# ── Bot identity (populated after bot starts) ─────────────────────────────────
BOT_ID: int = 0
BOT_NAME: str = os.getenv("BOT_NAME", "BeatAniVerse Bot")
BOT_USERNAME: str = ""

# ── Owner / privilege levels ──────────────────────────────────────────────────
OWNER_ID: int = int(os.getenv("OWNER_ID", "0") or "0")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0") or os.getenv("OWNER_ID", "0"))

_dragons_raw = os.getenv("DRAGONS", "")
_dev_raw     = os.getenv("DEV_USERS", "")
_demons_raw  = os.getenv("DEMONS", "")
_tigers_raw  = os.getenv("TIGERS", "")
_wolves_raw  = os.getenv("WOLVES", "")

def _ids(s): return [int(x.strip()) for x in s.split() if x.strip().lstrip('-').isdigit()]

DRAGONS:   list = _ids(_dragons_raw) + [OWNER_ID, ADMIN_ID]
DEV_USERS: list = _ids(_dev_raw)     + [OWNER_ID, ADMIN_ID]
DEMONS:    list = _ids(_demons_raw)
TIGERS:    list = _ids(_tigers_raw)
WOLVES:    list = _ids(_wolves_raw)

# ── Database URIs ─────────────────────────────────────────────────────────────
DB_URI:       str = os.getenv("DATABASE_URL", "")
MONGO_DB_URI: str = os.getenv("MONGO_DB_URI", "")

# ── Bot settings ──────────────────────────────────────────────────────────────
ALLOW_CHATS: bool = bool(os.getenv("ALLOW_CHATS", "True"))
ALLOW_EXCL:  bool = bool(os.getenv("ALLOW_EXCL",  "True"))
DEL_CMDS:    bool = bool(os.getenv("DEL_CMDS",    "True"))
STRICT_GBAN: bool = bool(os.getenv("STRICT_GBAN", "True"))
EVENT_LOGS:  int  = int(os.getenv("EVENT_LOGS", "0") or "0") or None
SUPPORT_CHAT: str = os.getenv("SUPPORT_CHAT", "Beat_Anime_Discussion")
INFOPIC:     bool = True
START_IMG:   str  = os.getenv("START_IMG", "https://telegra.ph/file/40eb1ed850cdea274693e.jpg")
TEMP_DOWNLOAD_DIRECTORY: str = os.getenv("TEMP_DOWNLOAD_DIRECTORY", "./")
WORKERS:     int  = int(os.getenv("WORKERS", "8"))
LOAD:        list = []
NO_LOAD:     list = os.getenv("NO_LOAD", "").split()

# ── Timing ────────────────────────────────────────────────────────────────────
StartTime: float = time.time()

# ── Logger ────────────────────────────────────────────────────────────────────
LOGGER = logging.getLogger("BeatAniVerse")

# ── Pyrogram / Telethon clients (stubs - real clients are in bot.py) ─────────
# Modules that use pbot (Pyrogram) for things like /couple will get the real
# client injected after bot.py starts.
class _StubClient:
    """Stub so modules don't crash at import time if pbot isn't set yet."""
    async def send_message(self, *a, **kw): pass
    async def get_users(self, *a, **kw):
        class _U:
            mention = "Unknown"
        return _U()
    async def get_chat_members(self, *a, **kw):
        return []
    def on_message(self, *a, **kw):
        def decorator(func): return func
        return decorator
    def on_callback_query(self, *a, **kw):
        def decorator(func): return func
        return decorator
    def add_event_handler(self, *a, **kw): pass   # Fix: purge module
    def add_handler(self, *a, **kw): pass          # Fix: various modules
    async def iter_chat_members(self, *a, **kw): return iter([])
    def on(self, *a, **kw):
        """Stub for telethn.on(events.X) Telethon decorator."""
        def decorator(func): return func
        return decorator
    @property
    def bot(self):
        return self
    @property
    def id(self):
        return 0
    @property
    def username(self):
        return ""
    @property
    def first_name(self):
        return "Bot"

# ── Patch SQLAlchemy to allow duplicate table definitions ─────────────────────
# Prevents: "Table 'users' is already defined for this MetaData instance"
try:
    import sqlalchemy.orm.decl_api as _decl
    _orig_meta = getattr(_decl, 'DeclarativeMeta', None)
    # Patch __init_subclass__ or use event — simpler: patch the error at SQL level
    import sqlalchemy
    _orig_Table = sqlalchemy.Table
    def _patched_Table(name, metadata, *args, **kwargs):
        if name in metadata.tables:
            kwargs.setdefault('extend_existing', True)
        return _orig_Table(name, metadata, *args, **kwargs)
    sqlalchemy.Table = _patched_Table
except Exception:
    pass

pbot = _StubClient()
telethn = _StubClient()

# ── Missing API keys expected by some modules ──────────────────────────────────
CASH_API_KEY: str = os.getenv("CASH_API_KEY", "")
TIME_API_KEY: str = os.getenv("TIME_API_KEY", "")

# ── CustomCommandHandler (used by cleaner module) ─────────────────────────────
try:
    from telegram.ext import CommandHandler as _BaseCommandHandler
    class CustomCommandHandler(_BaseCommandHandler):
        """PTB v13 CustomCommandHandler compat stub."""
        def __init__(self, *args, **kwargs):
            kwargs.pop('run_async', None)
            super().__init__(*args, **kwargs)
except Exception:
    CustomCommandHandler = None

# ── Universal run_async strip — PTB v21 removed run_async ────────────────────
# All module handlers use run_async=True (PTB v13). Silently strip it from ALL
# handler constructors so they load cleanly in PTB v21.
try:
    import telegram.ext as _tgext
    for _cls_name in (
        "CommandHandler", "MessageHandler", "CallbackQueryHandler",
        "InlineQueryHandler", "ChatJoinRequestHandler",
        "ConversationHandler", "PollAnswerHandler", "PollHandler",
        "PreCheckoutQueryHandler", "ShippingQueryHandler",
        "StringCommandHandler", "StringRegexHandler",
        "TypeHandler",
    ):
        _cls = getattr(_tgext, _cls_name, None)
        if _cls is None:
            continue
        _orig_init = _cls.__init__
        def _patched_init(self, *args, _orig=_orig_init, **kwargs):
            kwargs.pop("run_async", None)
            _orig(self, *args, **kwargs)
        _cls.__init__ = _patched_init
    del _cls_name, _cls, _orig_init, _patched_init
except Exception as _patch_exc:
    import logging
    logging.getLogger(__name__).debug(f"run_async strip patch: {_patch_exc}")

# ── Telegram dispatcher — lazy proxy (never None, queues handlers) ────────────
class _LazyDispatcher:
    """
    Proxy dispatcher: queues add_handler/add_error_handler calls made at module
    import time, then replays them onto the real dispatcher when bot.py calls
    _set_dispatcher(real_dp).
    """
    def __init__(self):
        self._real = None
        self._queue = []   # list of (method_name, args, kwargs)

    def _replay(self):
        if self._real is None:
            return
        for method, args, kwargs in self._queue:
            try:
                getattr(self._real, method)(*args, **kwargs)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).debug(f"LazyDispatcher replay {method}: {exc}")
        self._queue.clear()

    def add_handler(self, *args, **kwargs):
        if self._real is not None:
            return self._real.add_handler(*args, **kwargs)
        self._queue.append(("add_handler", args, kwargs))

    def add_error_handler(self, *args, **kwargs):
        if self._real is not None:
            return self._real.add_error_handler(*args, **kwargs)
        self._queue.append(("add_error_handler", args, kwargs))

    @property
    def bot(self):
        if self._real is not None:
            return self._real.bot
        # Return stub bot so modules don't crash with NoneType.id
        # Return stub bot with all commonly-used methods as no-ops
        _noop = lambda *a, **k: None
        return type('_StubBot', (), {
            'id': 0, 'username': '', 'first_name': 'Bot',
            'send_message':   _noop,
            'send_sticker':   _noop,
            'send_photo':     _noop,
            'send_document':  _noop,
            'send_audio':     _noop,
            'send_voice':     _noop,
            'send_video':     _noop,
            'send_animation': _noop,
            'forward_message':_noop,
            'delete_message': _noop,
            'pin_message':    _noop,
            'get_chat':       _noop,
            'get_chat_member':_noop,
            'get_chat_administrators': _noop,
            'restrict_chat_member': _noop,
            'kick_chat_member': _noop,
            'ban_chat_member':  _noop,
            'unban_chat_member': _noop,
            'promote_chat_member': _noop,
            'answer_callback_query': _noop,
            'edit_message_text': _noop,
            '__getattr__': lambda self, name: _noop,   # catch-all for any other attr
        })()

    def __getattr__(self, name):
        if self._real is not None:
            return getattr(self._real, name)
        # handlers is accessed by cleaner.py at module load — return empty dict
        if name == 'handlers':
            return {}
        # Return a no-op for unknown attrs
        def _noop(*a, **k): pass
        return _noop


dispatcher = _LazyDispatcher()

def _set_dispatcher(dp):
    global dispatcher
    dispatcher._real = dp
    dispatcher._replay()   # replay queued handlers onto real dispatcher

def _set_pbot(client):
    global pbot
    pbot = client

def _set_telethn(client):
    global telethn
    telethn = client

def _set_bot_info(bot_id, bot_name, bot_username):
    global BOT_ID, BOT_NAME, BOT_USERNAME
    BOT_ID = bot_id
    BOT_NAME = bot_name
    BOT_USERNAME = bot_username
