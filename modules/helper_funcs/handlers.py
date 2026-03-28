# ====================================================================
# PLACE AT: /app/modules/helper_funcs/handlers.py
# ACTION: Replace existing file
# ====================================================================
"""
handlers.py — PTB v21 compatible.
Removed broken check_update() overrides that used removed v13 APIs:
  - message.bot  → AttributeError in v21
  - self.filters(update) → TypeError in v21
  - RegexHandler → removed, replaced with MessageHandler + Regex filter
"""
try:
    from pyrate_limiter import BucketFullException, Duration, Limiter, Rate
except ImportError:
    try:
        from pyrate_limiter import RequestRate as Rate, Duration, Limiter, BucketFullException
        if not hasattr(Duration, 'CUSTOM'):
            Duration.CUSTOM = 15
    except Exception:
        class Rate:
            def __init__(self, *a, **k): pass
        class Duration:
            CUSTOM = 15; MINUTE = 60; HOUR = 3600; DAY = 86400
        class BucketFullException(Exception): pass
        class Limiter:
            def __init__(self, *a, **k): pass
            def try_acquire(self, *a): pass

from telegram import Update
from telegram.ext import CommandHandler, MessageHandler

try:
    from telegram.ext import filters as tg_filters
except ImportError:
    pass

import modules.sql.blacklistusers_sql as sql
from beataniversebot_compat import ALLOW_EXCL, DEMONS, DEV_USERS, DRAGONS, TIGERS, WOLVES

if ALLOW_EXCL:
    CMD_STARTERS = ("/", "!")
else:
    CMD_STARTERS = "/"


class AntiSpam:
    def __init__(self):
        self.whitelist = (
            (DEV_USERS or [])
            + (DRAGONS or [])
            + (WOLVES or [])
            + (DEMONS or [])
            + (TIGERS or [])
        )
        Duration.CUSTOM = 15
        self.sec_limit  = Rate(6,    Duration.CUSTOM)
        self.min_limit  = Rate(20,   Duration.MINUTE)
        self.hour_limit = Rate(100,  Duration.HOUR)
        self.daily_limit= Rate(1000, Duration.DAY)
        self.rates  = [self.sec_limit, self.min_limit, self.hour_limit, self.daily_limit]
        self.limiter = Limiter(self.rates)

    def check_user(self, user):
        if user in self.whitelist:
            return False
        try:
            self.limiter.try_acquire(user)
            return False
        except BucketFullException:
            return True


SpamChecker = AntiSpam()
MessageHandlerChecker = AntiSpam()


class CustomCommandHandler(CommandHandler):
    """
    PTB v21 compatible CustomCommandHandler.
    Does NOT override check_update() — uses parent PTB v21 implementation.
    The broken v13 check_update used message.bot which is removed in v21.
    """
    def __init__(self, command, callback, admin_ok=False, allow_edit=False, **kwargs):
        kwargs.pop("run_async", None)
        super().__init__(command, callback, **kwargs)
        self.admin_ok   = admin_ok
        self.allow_edit = allow_edit


class CustomRegexHandler(MessageHandler):
    """PTB v21 compat: RegexHandler removed, use MessageHandler with Regex filter."""
    def __init__(self, pattern, callback, friendly="", **kwargs):
        kwargs.pop("run_async", None)
        from telegram.ext import filters as F
        super().__init__(F.Regex(pattern), callback, **kwargs)


class CustomMessageHandler(MessageHandler):
    """PTB v21 compatible CustomMessageHandler."""
    def __init__(self, filters, callback, friendly="", allow_edit=False, **kwargs):
        kwargs.pop("run_async", None)
        super().__init__(filters, callback, **kwargs)
        self.allow_edit = allow_edit


# Alias for backwards compat
RegexHandler = CustomRegexHandler
