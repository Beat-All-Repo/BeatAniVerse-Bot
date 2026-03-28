#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Global Text Style Engine
=============================================
Allows admin to change the text style for ALL bot messages globally.

Styles:
  • normal    — plain text, no conversion
  • smallcaps — converts a-z/A-Z to Unicode small caps
                ⚠ PRESERVES all HTML tags, attributes, and link text untouched
  • bold      — wraps plain text segments in <b>…</b>
                ⚠ PRESERVES existing HTML structure

HTML Safety:
  The converter parses HTML token by token. It only transforms bare
  text nodes — never tag names, attribute names, attribute values
  (href, src, etc.), or anything inside <a>…</a> link text.

Usage:
  from text_style import apply_style, get_style, set_style

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import re
import logging
from html.parser import HTMLParser
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# ── Small caps map ─────────────────────────────────────────────────────────────
_SC = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 'ꜱ', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
}


def _char_to_sc(ch: str) -> str:
    return _SC.get(ch, ch)


def _text_to_smallcaps(text: str) -> str:
    return ''.join(_char_to_sc(c) for c in text)


# ── HTML-safe style transformer ────────────────────────────────────────────────

class _StyleTransformer(HTMLParser):
    """
    Parses HTML and transforms only text nodes (not inside <a> tags).
    Preserves all tags, attributes (especially href), and link text verbatim.
    """

    def __init__(self, style: str):
        super().__init__(convert_charrefs=False)
        self._style = style
        self._out: List[str] = []
        self._in_link = 0      # depth inside <a> tags
        self._in_code = 0      # depth inside <code> tags — never transform
        self._in_pre = 0       # depth inside <pre>

    def _transform(self, text: str) -> str:
        """Transform a plain text node according to style."""
        if self._in_link or self._in_code or self._in_pre:
            return text    # Never touch link text or code
        if self._style == 'smallcaps':
            return _text_to_smallcaps(text)
        elif self._style == 'bold':
            # Only add <b> if text has actual visible content
            stripped = text.strip()
            if not stripped:
                return text
            return text.replace(stripped, f'<b>{stripped}</b>', 1)
        return text

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        # Reconstruct the opening tag exactly as-is
        attr_str = ''
        for name, val in attrs:
            if val is None:
                attr_str += f' {name}'
            else:
                attr_str += f' {name}="{val}"'
        self._out.append(f'<{tag}{attr_str}>')
        tag_lower = tag.lower()
        if tag_lower == 'a':
            self._in_link += 1
        elif tag_lower == 'code':
            self._in_code += 1
        elif tag_lower == 'pre':
            self._in_pre += 1

    def handle_endtag(self, tag: str):
        self._out.append(f'</{tag}>')
        tag_lower = tag.lower()
        if tag_lower == 'a':
            self._in_link = max(0, self._in_link - 1)
        elif tag_lower == 'code':
            self._in_code = max(0, self._in_code - 1)
        elif tag_lower == 'pre':
            self._in_pre = max(0, self._in_pre - 1)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        # Self-closing tags like <br/>
        attr_str = ''.join(
            f' {n}="{v}"' if v is not None else f' {n}'
            for n, v in attrs
        )
        self._out.append(f'<{tag}{attr_str}/>')

    def handle_data(self, data: str):
        self._out.append(self._transform(data))

    def handle_entityref(self, name: str):
        self._out.append(f'&{name};')

    def handle_charref(self, name: str):
        self._out.append(f'&#{name};')

    def handle_comment(self, data: str):
        self._out.append(f'<!--{data}-->')

    def result(self) -> str:
        return ''.join(self._out)


def _apply_html_style(html_text: str, style: str) -> str:
    """
    Apply style to html_text safely.
    Text nodes are transformed; tags/attributes/links are preserved verbatim.
    """
    if style == 'normal' or not html_text:
        return html_text
    try:
        transformer = _StyleTransformer(style)
        transformer.feed(html_text)
        return transformer.result()
    except Exception as exc:
        logger.warning(f"text_style transform error: {exc}")
        return html_text


# ── Public API ────────────────────────────────────────────────────────────────

def get_style() -> str:
    """Get current global text style from DB. Returns 'normal', 'smallcaps', or 'bold'."""
    try:
        from database_dual import get_setting
        return get_setting("global_text_style", "normal") or "normal"
    except Exception:
        return "normal"


def set_style(style: str) -> None:
    """Set global text style. style must be 'normal', 'smallcaps', or 'bold'."""
    if style not in ("normal", "smallcaps", "bold"):
        style = "normal"
    try:
        from database_dual import set_setting
        set_setting("global_text_style", style)
    except Exception:
        pass


def apply_style(text: str) -> str:
    """Apply current global text style to text. HTML-safe."""
    style = get_style()
    return _apply_html_style(text, style)


# ── Convenience wrappers matching bot.py helper functions ─────────────────────

def styled_b(text: str) -> str:
    """Bold-wrap text, then apply global style."""
    return apply_style(f"<b>{text}</b>")


def styled_bq(content: str, expandable: bool = False) -> str:
    """Blockquote-wrap content, applying global style to the content."""
    styled = apply_style(content)
    tag = "blockquote expandable" if expandable else "blockquote"
    return f"<{tag}>{styled}</{tag.split()[0]}>"


# ── Settings panel builders ────────────────────────────────────────────────────

def build_text_style_keyboard() -> 'InlineKeyboardMarkup':
    """Build the text style selection keyboard for admin settings."""
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    current = get_style()
    styles = [
        ("normal",    "🔤 Normal",     "Default — no conversion"),
        ("smallcaps", "ꜱᴍᴀʟʟ ᴄᴀᴘꜱ", "Convert all text to small caps"),
        ("bold",      "𝗕𝗼𝗹𝗱",         "Make all text bold"),
    ]
    rows = []
    for key, label, _ in styles:
        mark = "✅ " if current == key else ""
        rows.append([InlineKeyboardButton(
            f"{mark}{label}", callback_data=f"text_style_set_{key}"
        )])
    rows.append([InlineKeyboardButton("🔙 BACK", callback_data="admin_settings")])
    return InlineKeyboardMarkup(rows)


def get_text_style_panel_text() -> str:
    current = get_style()
    previews = {
        "normal":    "Preview: <b>Bold text</b> normal text <code>code</code>",
        "smallcaps": "Preview: <b>ʙᴏʟᴅ ᴛᴇxᴛ</b> ɴᴏʀᴍᴀʟ ᴛᴇxᴛ <code>code</code>",
        "bold":      "Preview: <b><b>Bold text</b></b> <b>normal text</b> <code>code</code>",
    }
    style_names = {"normal": "Normal", "smallcaps": "Small Caps", "bold": "Bold"}
    return (
        "<b>🔤 Global Text Style</b>\n\n"
        f"<b>Current Style:</b> <code>{style_names.get(current, current)}</code>\n\n"
        f"{previews.get(current, '')}\n\n"
        "<b>Notes:</b>\n"
        "• All bot messages use this style\n"
        "• Links (<code>href</code>) are NEVER modified\n"
        "• <code>code</code> blocks are NEVER modified\n"
        "• HTML tags and attributes are preserved\n"
        "• Small caps only affects a-z letters"
    )


# ── Export helpers for other modules ─────────────────────────────────────────

def _to_smallcaps_html_safe(html_text: str) -> str:
    return _apply_html_style(html_text, "smallcaps")


def _to_bold_html_safe(html_text: str) -> str:
    return _apply_html_style(html_text, "bold")
