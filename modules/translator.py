# ====================================================================
# PLACE AT: /app/modules/translator.py
# ACTION: Replace existing file
# ====================================================================
"""
translator.py — PTB v20 async. Blocking translate call run in executor.
"""
import asyncio
import html as _html

try:
    from gpytranslate import SyncTranslator
    _TRANS_LIB = "gpytranslate"
except ImportError:
    SyncTranslator = None
    _TRANS_LIB = None

try:
    from deep_translator import GoogleTranslator as _GT
    _TRANS_LIB = _TRANS_LIB or "deep_translator"
except ImportError:
    _GT = None


def _detect_lang_sync(text: str) -> str:
    """Best-effort language detection."""
    if SyncTranslator:
        try:
            t = SyncTranslator()
            return t.detect(text) or "auto"
        except Exception:
            pass
    return "auto"


def _translate_sync(text: str, source: str, dest: str) -> str:
    if SyncTranslator:
        try:
            t   = SyncTranslator()
            res = t(text, sourcelang=source, targetlang=dest)
            return res.text
        except Exception as e:
            return f"[translation error: {e}]"
    if _GT:
        try:
            src = "auto" if source in ("auto", "") else source
            return _GT(source=src, target=dest).translate(text)
        except Exception as e:
            return f"[translation error: {e}]"
    return "[no translation library installed — pip install gpytranslate]"


from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from beataniversebot_compat import dispatcher
from modules.disable import DisableAbleCommandHandler


async def totranslate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message   = update.effective_message
    reply_msg = message.reply_to_message

    usage = (
        "Reply to a message and use:\n"
        "• <code>/tr en</code> — auto-detect → English\n"
        "• <code>/tr hi//en</code> — Hindi → English\n"
        "• <code>/tr de</code> — auto-detect → German\n\n"
        '<a href="https://te.legra.ph/LANGUAGE-CODES-05-23-2">📋 Language Codes</a>'
    )

    if not reply_msg:
        await message.reply_text(usage, parse_mode=ParseMode.HTML,
                                 disable_web_page_preview=True)
        return

    to_translate = (reply_msg.caption or reply_msg.text or "").strip()
    if not to_translate:
        await message.reply_text("❌ Nothing to translate in that message.")
        return

    args = context.args
    loop = asyncio.get_event_loop()

    try:
        if args:
            raw = args[0].lower()
            if "//" in raw:
                source, dest = raw.split("//", 1)
            else:
                source = await loop.run_in_executor(None, _detect_lang_sync, to_translate)
                dest   = raw
        else:
            source = await loop.run_in_executor(None, _detect_lang_sync, to_translate)
            dest   = "en"
    except Exception:
        source, dest = "auto", "en"

    translated = await loop.run_in_executor(None, _translate_sync, to_translate, source, dest)

    reply = (
        f"<b>Translated</b>  <code>{_html.escape(source)}</code> → <code>{_html.escape(dest)}</code>\n\n"
        f"<code>{_html.escape(translated)}</code>"
    )
    await message.reply_text(reply, parse_mode=ParseMode.HTML)


__help__ = """
*Translator*

 ❍ /tr <lang> — translate replied-to message
 ❍ /tl <lang> — same

*Examples:*
 `/tr en` — auto-detect → English
 `/tr hi//en` — Hindi → English

[ Language Codes](https://te.legra.ph/LANGUAGE-CODES-05-23-2)
"""
__mod_name__ = "Tʀᴀɴsʟᴀᴛᴏʀ"

TRANSLATE_HANDLER = DisableAbleCommandHandler(["tr", "tl"], totranslate, run_async=True)
dispatcher.add_handler(TRANSLATE_HANDLER)

__command_list__ = ["tr", "tl"]
__handlers__     = [TRANSLATE_HANDLER]
