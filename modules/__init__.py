"""
BeatAniVerse modules package.
Loads telegram_compat FIRST to fix PTB v13 → v21 compatibility for all modules.
"""
import glob
import os
import logging

LOGGER = logging.getLogger(__name__)

# ── Import compat shim FIRST — patches telegram namespace for all modules ────
try:
    from modules.telegram_compat import *  # noqa: F401, F403
    LOGGER.info("[modules] telegram_compat loaded successfully")
except ImportError:
    try:
        from telegram_compat import *  # noqa: F401, F403
        LOGGER.info("[modules] telegram_compat loaded (fallback)")
    except ImportError:
        LOGGER.warning("[modules] telegram_compat not found — some modules may fail")

_NO_LOAD = set(os.getenv("NO_LOAD", "").split())

def _list_modules():
    mod_paths = glob.glob(os.path.dirname(__file__) + "/*.py")
    all_mods = [
        os.path.basename(f)[:-3]
        for f in mod_paths
        if f.endswith(".py") and not f.endswith("__init__.py")
           and not f.endswith("telegram_compat.py")
    ]
    return [m for m in all_mods if m not in _NO_LOAD]

ALL_MODULES = _list_modules()
__all__ = ALL_MODULES + ["ALL_MODULES"]
