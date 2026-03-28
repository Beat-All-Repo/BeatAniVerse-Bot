# ====================================================================
# PLACE AT: /app/BeatVerseProbot/modules/fun_strings.py
# ACTION: CREATE new file
# ====================================================================
"""BeatVerseProbot.modules.fun_strings — forward to real fun_strings module."""
try:
    from modules.fun_strings import *
    from modules.fun_strings import RUN_STRINGS
except ImportError:
    RUN_STRINGS = ("Running!", "Gone!", "Bye!")
