"""
core/text_utils.py
==================
Text formatting utilities: small_caps, math_bold, HTML helpers,
number formatting, date parsing, pagination, etc.
"""
import html
import re
import math
import calendar
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List


# ── Unicode character maps ────────────────────────────────────────────────────

SMALL_CAPS_MAP: Dict[str, str] = {
    "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ғ", "g": "ɢ",
    "h": "ʜ", "i": "ɪ", "j": "ᴊ", "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ",
    "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ", "u": "ᴜ",
    "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}
SMALL_CAPS_MAP.update({k.upper(): v for k, v in SMALL_CAPS_MAP.items()})

MATH_BOLD_MAP: Dict[str, str] = {
    "A": "𝗔", "B": "𝗕", "C": "𝗖", "D": "𝗗", "E": "𝗘", "F": "𝗙", "G": "𝗚",
    "H": "𝗛", "I": "𝗜", "J": "𝗝", "K": "𝗞", "L": "𝗟", "M": "𝗠", "N": "𝗡",
    "O": "𝗢", "P": "𝗣", "Q": "𝗤", "R": "𝗥", "S": "𝗦", "T": "𝗧", "U": "𝗨",
    "V": "𝗩", "W": "𝗪", "X": "𝗫", "Y": "𝗬", "Z": "𝗭",
    "a": "𝗮", "b": "𝗯", "c": "𝗰", "d": "𝗱", "e": "𝗲", "f": "𝗳", "g": "𝗴",
    "h": "𝗵", "i": "𝗶", "j": "𝗷", "k": "𝗸", "l": "𝗹", "m": "𝗺", "n": "𝗻",
    "o": "𝗼", "p": "𝗽", "q": "𝗾", "r": "𝗿", "s": "𝘀", "t": "𝘁", "u": "𝘂",
    "v": "𝘃", "w": "𝘄", "x": "𝘅", "y": "𝘆", "z": "𝘇",
    "0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯", "4": "𝟰",
    "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵",
}


# ── Text converters ────────────────────────────────────────────────────────────

def small_caps(text: str) -> str:
    """
    Convert ASCII letters to Unicode small caps.
    Skips: HTML tags, @mentions, /commands, http(s):// URLs, <code>...</code>.
    Numbers and punctuation are passed through unchanged.
    """
    if not text:
        return text
    result: list = []
    i = 0
    n = len(text)
    in_tag = False
    in_code = False

    while i < n:
        ch = text[i]
        if ch == "<" and not in_code:
            in_tag = True
            rest = text[i:].lower()
            if rest.startswith("<code"):
                in_code = True
            elif rest.startswith("</code"):
                in_code = False
            result.append(ch)
            i += 1
            continue
        if ch == ">" and in_tag:
            in_tag = False
            result.append(ch)
            i += 1
            continue
        if in_tag:
            result.append(ch)
            i += 1
            continue
        if in_code:
            result.append(ch)
            i += 1
            continue
        if ch == "@":
            result.append(ch)
            i += 1
            while i < n and (text[i].isalnum() or text[i] == "_"):
                result.append(text[i])
                i += 1
            continue
        if ch == "/" and (i == 0 or not text[i - 1].isalnum()):
            i += 1
            while i < n and (text[i].isalnum() or text[i] == "_"):
                result.append(text[i])
                i += 1
            continue
        if text[i:i + 7] in ("https:/", "http://") or text[i:i + 8] == "https://":
            while i < n and text[i] not in (" ", "\n", "\t", "<", ">"):
                result.append(text[i])
                i += 1
            continue
        result.append(SMALL_CAPS_MAP.get(ch, ch))
        i += 1
    return "".join(result)


def math_bold(text: str) -> str:
    """Convert text to Unicode math bold for button labels."""
    return "".join(MATH_BOLD_MAP.get(ch, ch) for ch in text)


# ── HTML helpers ──────────────────────────────────────────────────────────────

def b(text: str) -> str:
    """Wrap text in HTML bold tags, auto-applying small caps."""
    return f"<b>{small_caps(text)}</b>"


def code(text: str) -> str:
    """Wrap text in HTML code tags."""
    return f"<code>{text}</code>"


def bq(content: str, expandable: bool = True) -> str:
    """Wrap text in an expandable HTML blockquote (collapsed by default)."""
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{content}</{tag.split()[0]}>"


def e(text: str) -> str:
    """HTML-escape text safely."""
    return html.escape(str(text))


def strip_html(text: str) -> str:
    """Strip all HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", str(text))


def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    """Truncate text to max_len characters."""
    t = str(text)
    return t if len(t) <= max_len else t[: max_len - len(suffix)] + suffix


# ── Number / size formatters ──────────────────────────────────────────────────

def format_number(n: int) -> str:
    """Format large numbers with commas."""
    return f"{n:,}"


def format_size(bytes_val: int) -> str:
    """Human-readable file size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val //= 1024
    return f"{bytes_val:.2f} PB"


def format_duration(seconds: int) -> str:
    """Format seconds into h m s string."""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


# ── Date / time helpers ───────────────────────────────────────────────────────

def parse_date(d: Optional[Dict]) -> str:
    """Parse AniList date dict {'year':x,'month':y,'day':z} to readable string."""
    if not d:
        return "Unknown"
    try:
        parts = []
        if d.get("day"):
            parts.append(str(d["day"]))
        if d.get("month"):
            parts.append(calendar.month_abbr[d["month"]])
        if d.get("year"):
            parts.append(str(d["year"]))
        return " ".join(parts) if parts else "Unknown"
    except Exception:
        return "Unknown"


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Pagination helper ─────────────────────────────────────────────────────────

def paginate(items: list, page: int, per_page: int = 10) -> Tuple[list, int, int]:
    """Return (page_items, total_pages, current_page)."""
    total = len(items)
    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    return items[start: start + per_page], total_pages, page
