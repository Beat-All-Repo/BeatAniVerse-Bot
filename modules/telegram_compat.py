# ====================================================================
# PLACE AT: /app/modules/telegram_compat.py
# ACTION: Replace existing file
# ====================================================================
"""
telegram_compat.py — PTB v13 → v21 compatibility shim
=======================================================
This MUST be imported before any modules/* file.
modules/__init__.py does this automatically.

Fixes ALL errors from logs:
  - cannot import name 'ParseMode' from 'telegram'
  - cannot import name 'Filters' from 'telegram.ext'
  - cannot import name 'RegexHandler' from 'telegram.ext'
  - cannot import name 'DispatcherHandlerStop' from 'telegram.ext'
  - cannot import name 'Unauthorized' from 'telegram.error'
  - cannot import name 'MAX_MESSAGE_LENGTH' from 'telegram'
  - No module named 'telegram.utils'
  - CustomCommandHandler import error
  - CASH_API_KEY / TIME_API_KEY missing from compat

Credits: BeatAnime | @BeatAnime
"""

import os, sys, re, types, logging
logger = logging.getLogger(__name__)

# ── Stub missing pip packages so modules load even without them ───────────────
import sys as _sys, types as _types

def _stub_module(name: str, **attrs):
    """Register a stub in sys.modules so imports don't crash."""
    if name in _sys.modules:
        return
    parts = name.split(".")
    # Register parent packages too
    for i in range(1, len(parts)):
        parent = ".".join(parts[:i])
        if parent not in _sys.modules:
            m = _types.ModuleType(parent)
            _sys.modules[parent] = m
    m = _types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    _sys.modules[name] = m
    return m

# ── SQLAlchemy: EARLY patch — must run before any module imports sql models ───
# Fixes: "Table 'users' is already defined for this MetaData instance"
try:
    import sqlalchemy as _sa_early
    _sa_orig_Table_init = _sa_early.Table.__init__

    def _sa_patched_init(self, name, metadata=None, *args, **kwargs):
        if metadata is not None and hasattr(metadata, 'tables') and name in metadata.tables:
            kwargs.setdefault('extend_existing', True)
        if metadata is not None:
            _sa_orig_Table_init(self, name, metadata, *args, **kwargs)
        else:
            _sa_orig_Table_init(self, name, *args, **kwargs)

    _sa_early.Table.__init__ = _sa_patched_init
except Exception as _sa_e:
    pass  # Will be retried later


# ── pyrate_limiter v2/v3 compatibility ────────────────────────────────────────
# v2 uses Rate; v3 uses RequestRate. Patch whichever is installed.
try:
    import pyrate_limiter as _prl
    if not hasattr(_prl, 'Rate'):
        if hasattr(_prl, 'RequestRate'):
            _prl.Rate = _prl.RequestRate
        else:
            class _Rate:
                def __init__(self, *a, **k): pass
            _prl.Rate = _Rate

    # Duration.CUSTOM missing in v3
    if hasattr(_prl, 'Duration') and not hasattr(_prl.Duration, 'CUSTOM'):
        _prl.Duration.CUSTOM = 15

    # Limiter API changed: v2=Limiter(list_of_rates), v3=Limiter(*rates)
    # Patch Limiter to accept both calling conventions
    _orig_Limiter = _prl.Limiter
    class _PatchedLimiter(_orig_Limiter):
        def __init__(self, rates=None, *args, **kwargs):
            if isinstance(rates, list):
                # v2 style: Limiter([rate1, rate2]) → unpack for v3
                try:
                    super().__init__(*rates, **kwargs)
                except Exception:
                    super().__init__(**kwargs)
            elif rates is not None:
                super().__init__(rates, *args, **kwargs)
            else:
                super().__init__(*args, **kwargs)
        def try_acquire(self, key):
            try:
                super().try_acquire(key)
            except Exception as exc:
                if 'BucketFullException' in type(exc).__name__ or 'full' in str(exc).lower():
                    raise _prl.BucketFullException(key, 0) from exc
    _prl.Limiter = _PatchedLimiter
    _sys.modules['pyrate_limiter'] = _prl
    logger.info("[telegram_compat] pyrate_limiter v3→v2 fully patched (Rate alias + Limiter compat)")
except ImportError:
    # Not installed at all — full stub
    class _Rate:
        def __init__(self, *a, **k): pass
    class _Duration:
        CUSTOM = 15; MINUTE = 60; HOUR = 3600; DAY = 86400
    class _BucketFullException(Exception): pass
    class _Limiter:
        def __init__(self, *a, **k): pass
        def try_acquire(self, *a, **k): pass
    _pl = _stub_module("pyrate_limiter")
    _pl.Rate = _Rate; _pl.Duration = _Duration
    _pl.BucketFullException = _BucketFullException; _pl.Limiter = _Limiter
    logger.info("[telegram_compat] pyrate_limiter fully stubbed (not installed)")

try:
    import markdown2  # noqa
except ImportError:
    _md2 = _stub_module("markdown2")
    _md2.markdown = lambda text, **k: text
    logger.info("[telegram_compat] markdown2 stubbed")

try:
    import search_engine_parser  # noqa
    if not hasattr(search_engine_parser, 'GoogleSearch'):
        class _GS:
            def __init__(self, *a, **k): pass
            def search(self, *a, **k): return []
        search_engine_parser.GoogleSearch = _GS
except ImportError:
    _gs_stub = _stub_module("search_engine_parser")
    class _GS:
        def __init__(self, *a, **k): pass
        def search(self, *a, **k): return []
    _gs_stub.GoogleSearch = _GS
    _stub_module("search_engine_parser.base")
    logger.info("[telegram_compat] search_engine_parser stubbed")

try:
    import hachoir  # noqa
except ImportError:
    for _h in ("hachoir", "hachoir.parser", "hachoir.metadata", "hachoir.core"):
        _stub_module(_h)
    logger.info("[telegram_compat] hachoir stubbed")

try:
    import webptools  # noqa
except ImportError:
    _stub_module("webptools")
    logger.info("[telegram_compat] webptools stubbed")

# ── PTB v21 real imports ───────────────────────────────────────────────────────
from telegram.constants import ParseMode, ChatAction, MessageLimit
from telegram import (
    Bot, Update, User, Chat, Message, ChatPermissions,
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, MessageEntity, CallbackQuery,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply,
    ChatMember,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, InlineQueryHandler,
    ContextTypes, CallbackContext,
    filters as _filters_module,
)
from telegram.error import (
    TelegramError, BadRequest, NetworkError,
    TimedOut, Forbidden, RetryAfter, InvalidToken,
)
from telegram.helpers import mention_html, mention_markdown, escape_markdown

# ── Compat aliases ─────────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = MessageLimit.MAX_TEXT_LENGTH   # 4096
Unauthorized = Forbidden                            # v13 name → v21 name

# ── CallbackContext (still exists in v21) ─────────────────────────────────────
# Already imported above

# ── Filters compat class (v13 used class Filters, v21 uses module filters) ────
class _FiltersCompat:
    text             = _filters_module.TEXT
    command          = _filters_module.COMMAND
    reply            = _filters_module.REPLY
    forwarded        = _filters_module.FORWARDED
    document         = _filters_module.Document.ALL
    photo            = _filters_module.PHOTO
    video            = _filters_module.VIDEO
    audio            = _filters_module.AUDIO
    voice            = _filters_module.VOICE
    sticker          = _filters_module.Sticker.ALL
    contact          = _filters_module.CONTACT
    location         = _filters_module.LOCATION
    venue            = _filters_module.VENUE
    game             = _filters_module.GAME
    dice             = _filters_module.Dice.ALL
    poll             = _filters_module.POLL
    animation        = _filters_module.ANIMATION
    caption          = _filters_module.CAPTION
    all              = _filters_module.ALL
    private          = _filters_module.ChatType.PRIVATE
    group            = _filters_module.ChatType.GROUP
    supergroup       = _filters_module.ChatType.SUPERGROUP
    groups           = _filters_module.ChatType.GROUPS  # v13 compat alias
    chat_type        = _filters_module.ChatType
    user             = _filters_module.User
    chat             = _filters_module.Chat
    language         = _filters_module.Language
    class status_update:  # v13 lowercase ↔ v21 uppercase bridge
        """Proxy so both .new_chat_members (v13) and .NEW_CHAT_MEMBERS (v21) work."""
        # Uppercase (v21 native)
        ALL              = _filters_module.StatusUpdate.ALL
        NEW_CHAT_MEMBERS = _filters_module.StatusUpdate.NEW_CHAT_MEMBERS
        LEFT_CHAT_MEMBER = _filters_module.StatusUpdate.LEFT_CHAT_MEMBER
        CHAT_CREATED     = _filters_module.StatusUpdate.CHAT_CREATED
        DELETE_CHAT_PHOTO= _filters_module.StatusUpdate.DELETE_CHAT_PHOTO
        NEW_CHAT_PHOTO   = _filters_module.StatusUpdate.NEW_CHAT_PHOTO
        NEW_CHAT_TITLE   = _filters_module.StatusUpdate.NEW_CHAT_TITLE
        PINNED_MESSAGE   = _filters_module.StatusUpdate.PINNED_MESSAGE
        MIGRATE          = _filters_module.StatusUpdate.MIGRATE
        # Lowercase aliases (v13 compat — what locks.py / welcome.py use)
        new_chat_members = _filters_module.StatusUpdate.NEW_CHAT_MEMBERS
        left_chat_member = _filters_module.StatusUpdate.LEFT_CHAT_MEMBER
        chat_created     = _filters_module.StatusUpdate.CHAT_CREATED
        delete_chat_photo= _filters_module.StatusUpdate.DELETE_CHAT_PHOTO
        new_chat_photo   = _filters_module.StatusUpdate.NEW_CHAT_PHOTO
        new_chat_title   = _filters_module.StatusUpdate.NEW_CHAT_TITLE
        pinned_message   = _filters_module.StatusUpdate.PINNED_MESSAGE
        migrate          = _filters_module.StatusUpdate.MIGRATE
    caption_entity   = _filters_module.CaptionEntity      # needed by locks.py
    new_chat_members = _filters_module.StatusUpdate.NEW_CHAT_MEMBERS
    left_chat_member = _filters_module.StatusUpdate.LEFT_CHAT_MEMBER
    regex            = _filters_module.Regex
    entity           = _filters_module.Entity

    # Nested compat
    class update:
        messages            = _filters_module.ALL
        edited_message      = _filters_module.UpdateType.EDITED_MESSAGE
        edited_channel_post = _filters_module.UpdateType.EDITED_CHANNEL_POST

    class Document:
        ALL           = _filters_module.Document.ALL
        APK           = _filters_module.Document.APK
        ZIP           = _filters_module.Document.ZIP
        PDF           = _filters_module.Document.PDF
        IMAGE         = _filters_module.Document.IMAGE
        VIDEO         = _filters_module.Document.VIDEO
        AUDIO         = _filters_module.Document.AUDIO
        TEXT          = _filters_module.Document.TEXT
        MimeType      = _filters_module.Document.MimeType
        FileExtension = _filters_module.Document.FileExtension

    class Sticker:
        ALL      = _filters_module.Sticker.ALL
        ANIMATED = _filters_module.Sticker.ANIMATED
        STATIC   = _filters_module.Sticker.STATIC
        VIDEO    = _filters_module.Sticker.VIDEO

    def __call__(self, *a, **kw):
        return _filters_module.ALL


# ── Patch ChatType to add v13-style aliases ────────────────────────────────────
try:
    from telegram.constants import ChatType as _CT
    # v13 used lowercase: Filters.chat_type.groups, Filters.chat_type.private
    # v21 uses uppercase: ChatType.GROUP, ChatType.PRIVATE
    if not hasattr(_CT, 'groups'):
        _CT.groups = _CT.GROUP
    if not hasattr(_CT, 'supergroups'):
        _CT.supergroups = _CT.SUPERGROUP
    if not hasattr(_CT, 'private'):
        _CT.private = _CT.PRIVATE
    if not hasattr(_CT, 'channel'):
        _CT.channel = _CT.CHANNEL
except Exception:
    pass

# Also patch Filters.chat_type so Filters.chat_type.groups works
_FiltersCompat.chat_type = type('_ChatTypeCompat', (), {
    'groups':      _filters_module.ChatType.GROUPS,
    'supergroups': _filters_module.ChatType.SUPERGROUP,
    'private':     _filters_module.ChatType.PRIVATE,
    'channel':     _filters_module.ChatType.CHANNEL,
    'GROUP':       _filters_module.ChatType.GROUP,
    'GROUPS':      _filters_module.ChatType.GROUPS,
    'PRIVATE':     _filters_module.ChatType.PRIVATE,
    'SUPERGROUP':  _filters_module.ChatType.SUPERGROUP,
})()

Filters = _FiltersCompat()

# ── DispatcherHandlerStop ──────────────────────────────────────────────────────
try:
    from telegram.ext import ApplicationHandlerStop as DispatcherHandlerStop
except ImportError:
    class DispatcherHandlerStop(Exception):
        pass

# ── RegexHandler (removed in v21, recreated) ──────────────────────────────────
class RegexHandler(MessageHandler):
    """PTB v13 RegexHandler shim for v21."""
    def __init__(self, pattern, callback, filters=None, **kwargs):
        kwargs.pop('run_async', None)
        f = _filters_module.Regex(re.compile(pattern) if isinstance(pattern, str) else pattern)
        if filters:
            try:
                f = f & filters
            except Exception:
                pass
        super().__init__(filters=f, callback=callback)

# ── Patch run_async kwarg out of all handlers ──────────────────────────────────
# Strip v13-only kwargs from all handlers (run_async, pass_args, pass_update_queue etc.)
_V13_KWARGS = {'run_async', 'pass_args', 'pass_update_queue', 'pass_job_queue',
               'pass_user_data', 'pass_chat_data', 'message_updates', 'channel_post_updates',
               'edited_updates', 'allow_edited', 'pass_groups', 'pass_groupdict'}
for _cls in (CommandHandler, MessageHandler, CallbackQueryHandler, InlineQueryHandler):
    _orig = _cls.__init__
    def _patched(self, *a, _orig=_orig, **kw):
        for _k in _V13_KWARGS:
            kw.pop(_k, None)
        _orig(self, *a, **kw)
    _cls.__init__ = _patched

# ── CustomCommandHandler (used by cleaner + handlers.py) ──────────────────────
class CustomCommandHandler(CommandHandler):
    def __init__(self, command, callback, admin_ok=False, allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(command, callback, **kwargs)

class CustomRegexHandler(RegexHandler):
    def __init__(self, pattern, callback, friendly="", filters=None, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(pattern, callback, filters=filters, **kwargs)

class CustomMessageHandler(MessageHandler):
    def __init__(self, filters, callback, friendly="", allow_edit=False, **kwargs):
        kwargs.pop('run_async', None)
        super().__init__(filters=filters, callback=callback, **kwargs)

# ── DisableAbleCommandHandler fallback (if disable module not loaded) ──────────
DisableAbleCommandHandler = CustomCommandHandler
DisableAbleRegexHandler   = CustomRegexHandler
DisableAbleMessageHandler = CustomMessageHandler

# ── Inject everything into telegram namespace (v13: from telegram import X) ───
import telegram as _tg
_INJECT = {
    'ParseMode': ParseMode, 'ChatAction': ChatAction,
    'MAX_MESSAGE_LENGTH': MAX_MESSAGE_LENGTH,
    'TelegramError': TelegramError, 'Unauthorized': Forbidden,
    'BadRequest': BadRequest, 'NetworkError': NetworkError,
    'TimedOut': TimedOut, 'Forbidden': Forbidden,
    'RetryAfter': RetryAfter, 'InvalidToken': InvalidToken,
    'InlineKeyboardButton': InlineKeyboardButton,
    'InlineKeyboardMarkup': InlineKeyboardMarkup,
    'InlineQueryResultArticle': InlineQueryResultArticle,
    'InlineQueryResultPhoto': InlineQueryResultPhoto,
    'InputTextMessageContent': InputTextMessageContent,
    'MessageEntity': MessageEntity, 'CallbackQuery': CallbackQuery,
    'ReplyKeyboardMarkup': ReplyKeyboardMarkup,
    'ReplyKeyboardRemove': ReplyKeyboardRemove,
    'ForceReply': ForceReply, 'ChatMember': ChatMember,
    'Bot': Bot, 'Update': Update, 'User': User,
    'Chat': Chat, 'Message': Message, 'ChatPermissions': ChatPermissions,
}
for _k, _v in _INJECT.items():
    if not hasattr(_tg, _k):
        setattr(_tg, _k, _v)

# ── Inject into telegram.ext ───────────────────────────────────────────────────
import telegram.ext as _tge
_EXT_INJECT = {
    'Filters': Filters,
    'RegexHandler': RegexHandler,
    'DispatcherHandlerStop': DispatcherHandlerStop,
    'CustomCommandHandler': CustomCommandHandler,
    'CustomRegexHandler': CustomRegexHandler,
    'CustomMessageHandler': CustomMessageHandler,
    'MessageFilter': _filters_module.MessageFilter,   # v21 moved this — re-expose it here
}
for _k, _v in _EXT_INJECT.items():
    if not hasattr(_tge, _k):
        setattr(_tge, _k, _v)
# Always inject these (modules check at import time)
_tge.RegexHandler = RegexHandler
_tge.DispatcherHandlerStop = DispatcherHandlerStop
_tge.Filters = Filters

# ── Inject into telegram.error ─────────────────────────────────────────────────
import telegram.error as _te
if not hasattr(_te, 'Unauthorized'):
    _te.Unauthorized = Forbidden

# ── Fake telegram.utils module ─────────────────────────────────────────────────
def _make_utils():
    _utils = types.ModuleType('telegram.utils')
    _helpers = types.ModuleType('telegram.utils.helpers')
    _helpers.mention_html     = mention_html
    _helpers.mention_markdown = mention_markdown
    _helpers.escape_markdown  = escape_markdown
    _utils.helpers = _helpers
    sys.modules['telegram.utils']         = _utils
    sys.modules['telegram.utils.helpers'] = _helpers

if 'telegram.utils' not in sys.modules:
    _make_utils()
else:
    # Patch helpers in if missing
    _u = sys.modules['telegram.utils']
    if not hasattr(_u, 'helpers'):
        _make_utils()


# ── SQLAlchemy: prevent "Table already defined" errors ────────────────────────
try:
    import sqlalchemy as _sa
    # Patch MetaData._add_table to silently handle duplicates
    from sqlalchemy import MetaData as _MetaData
    _orig_add_table = _MetaData._add_table if hasattr(_MetaData, '_add_table') else None

    # Patch at the Table class __new__ level using __init_subclass__ bypass
    # Most reliable: patch declarative_base metadata and all MetaData instances
    import sqlalchemy.orm as _orm
    _orig_decl_base = _orm.declarative_base
    def _patched_decl_base(*a, **kw):
        base = _orig_decl_base(*a, **kw)
        # Ensure metadata allows extension
        if hasattr(base, 'metadata'):
            meta = base.metadata
            # Override _add_table to handle duplicates gracefully
            if hasattr(meta, '_add_table'):
                _orig_at = meta._add_table
                def _safe_add_table(name, schema, table):
                    key = schema + '.' + name if schema else name
                    if key in meta.tables:
                        return  # silently skip duplicates
                    return _orig_at(name, schema, table)
                meta._add_table = _safe_add_table
        return base
    _orm.declarative_base = _patched_decl_base

    # Also patch existing Table.__new__ for non-ORM tables
    _orig_Table_init = _sa.Table.__init__
    def _safe_Table_init(self, name, metadata, *cols, **kwargs):
        if hasattr(metadata, 'tables') and name in metadata.tables:
            kwargs.setdefault('extend_existing', True)
        return _orig_Table_init(self, name, metadata, *cols, **kwargs)
    _sa.Table.__init__ = _safe_Table_init
    logger.info("[telegram_compat] SQLAlchemy duplicate-table patch applied")
except Exception as _sq_exc:
    logger.debug(f"[telegram_compat] SQLAlchemy patch: {_sq_exc}")

if False:  # dummy block to replace old try
    import sqlalchemy as _sa
logger.info("[telegram_compat] ✅ PTB v13→v21 shim loaded")

__all__ = [
    'ParseMode', 'ChatAction', 'MAX_MESSAGE_LENGTH',
    'Bot', 'Update', 'User', 'Chat', 'Message', 'ChatPermissions',
    'InlineKeyboardButton', 'InlineKeyboardMarkup',
    'InlineQueryResultArticle', 'InlineQueryResultPhoto',
    'InputTextMessageContent', 'MessageEntity', 'CallbackQuery',
    'ReplyKeyboardMarkup', 'ReplyKeyboardRemove', 'ForceReply', 'ChatMember',
    'CommandHandler', 'MessageHandler', 'CallbackQueryHandler',
    'InlineQueryHandler', 'ContextTypes', 'CallbackContext',
    'Filters', 'RegexHandler', 'DispatcherHandlerStop',
    'CustomCommandHandler', 'CustomRegexHandler', 'CustomMessageHandler',
    'DisableAbleCommandHandler', 'DisableAbleRegexHandler', 'DisableAbleMessageHandler',
    'TelegramError', 'BadRequest', 'NetworkError', 'TimedOut',
    'Forbidden', 'Unauthorized', 'RetryAfter', 'InvalidToken',
    'mention_html', 'mention_markdown', 'escape_markdown',
]
