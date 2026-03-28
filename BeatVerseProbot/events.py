# ====================================================================
# PLACE AT: /app/BeatVerseProbot/events.py
# ACTION: CREATE new file
# ====================================================================
"""BeatVerseProbot.events stub — provides register decorator."""
import logging
logger = logging.getLogger(__name__)

def register(*args, **kwargs):
    """Stub decorator for Pyrogram event registration."""
    def decorator(func):
        return func
    # Handle both @register and @register(filters=...)
    if args and callable(args[0]):
        return args[0]
    return decorator
