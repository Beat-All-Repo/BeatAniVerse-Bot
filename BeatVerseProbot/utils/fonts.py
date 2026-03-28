# ====================================================================
# PLACE AT: /app/BeatVerseProbot/utils/fonts.py
# ACTION: CREATE new file
# ====================================================================
"""BeatVerseProbot.utils.fonts stub."""
import logging
logger = logging.getLogger(__name__)

class Fonts:
    """Stub Fonts class — font generation via pyrogram."""
    @staticmethod
    def convert(text: str, style: str = "bold") -> str:
        return text

    def __call__(self, text: str, *args, **kwargs) -> str:
        return text
