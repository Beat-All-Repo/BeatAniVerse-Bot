"""
core/buttons.py
===============
InlineKeyboardButton factories and keyboard layout helpers.
Centralises all button building so style changes only need to be made here.
"""
import time
from typing import List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from core.text_utils import small_caps, math_bold
from core.config import BUTTON_STYLE


# ── Button style cache (60s TTL eliminates DB round-trips per panel) ──────────
_CACHED_BTN_STYLE: str = ""
_CACHED_BTN_STYLE_TS: float = 0.0
_BTN_STYLE_TTL: float = 60.0


def refresh_btn_style_cache() -> None:
    """Force-refresh button style cache (call after admin changes style)."""
    global _CACHED_BTN_STYLE, _CACHED_BTN_STYLE_TS
    _CACHED_BTN_STYLE = ""
    _CACHED_BTN_STYLE_TS = 0.0


def _style_label(label: str) -> str:
    """Apply current button style to label text. Uses 60s in-memory cache."""
    global _CACHED_BTN_STYLE, _CACHED_BTN_STYLE_TS
    now = time.monotonic()
    if not _CACHED_BTN_STYLE or (now - _CACHED_BTN_STYLE_TS) > _BTN_STYLE_TTL:
        try:
            from database_dual import get_setting
            _CACHED_BTN_STYLE = get_setting("button_style", BUTTON_STYLE) or BUTTON_STYLE
        except Exception:
            _CACHED_BTN_STYLE = BUTTON_STYLE
        _CACHED_BTN_STYLE_TS = now
    style = _CACHED_BTN_STYLE

    _ALLOWED_PFXS = (
        "◀ ", "▶ ", "✖️ ", "🔙 ", "🔜 ", "➕ ", "✔️ ", "♻️ ", "❗ ", "✨ ", "🟢 ", "🔴 ",
        "◀", "▶", "✖️", "🔙", "🔜", "➕", "✔️", "♻️", "❗", "✨", "🟢", "🔴"
    )
    prefix = ""
    clean = label
    for p in _ALLOWED_PFXS:
        if clean.startswith(p):
            prefix = p
            clean = clean[len(p):]
            break

    if style == "smallcaps":
        styled = small_caps(clean)
    else:
        styled = math_bold(clean)
    return prefix + styled


def _btn(label: str, cb: str) -> InlineKeyboardButton:
    """Panel button with dynamic style (mathbold or smallcaps)."""
    return InlineKeyboardButton(_style_label(label), callback_data=cb)


def _close_btn() -> InlineKeyboardButton:
    return InlineKeyboardButton("✖️", callback_data="close_message")


def _back_btn(cb: str = "admin_back") -> InlineKeyboardButton:
    return InlineKeyboardButton("🔙 " + _style_label("ʙᴀᴄᴋ"), callback_data=cb)


def _next_btn(cb: str) -> InlineKeyboardButton:
    return InlineKeyboardButton("🔜", callback_data=cb)


def bold_button(label: str, **kwargs) -> InlineKeyboardButton:
    """Styled button — respects BUTTON_STYLE setting."""
    return InlineKeyboardButton(_style_label(label), **kwargs)


def _grid3(items: list) -> list:
    """Arrange a flat list of InlineKeyboardButtons into rows of 3."""
    rows = []
    for i in range(0, len(items), 3):
        rows.append(items[i:i + 3])
    return rows


def _grid4(items: list) -> list:
    """Arrange a flat list of InlineKeyboardButtons into rows of 4."""
    rows = []
    for i in range(0, len(items), 4):
        rows.append(items[i:i + 4])
    return rows


def _panel_kb(
    grid_items: list,
    back_cb: str = "admin_back",
    extra_rows: list = None,
) -> InlineKeyboardMarkup:
    """
    Build a keyboard with items arranged in 3-per-row grid.
    Always appends: [🔙 BACK] [CLOSE]
    """
    rows = _grid3(grid_items)
    if extra_rows:
        rows.extend(extra_rows)
    rows.append([_back_btn(back_cb), _close_btn()])
    return InlineKeyboardMarkup(rows)


def _back_kb(data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_back_btn(data), _close_btn()]])


def _back_close_kb(back_data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_back_btn(back_data), _close_btn()]])


def build_pagination_kb(
    current_page: int,
    total_pages: int,
    base_callback: str,
    extra_buttons: Optional[List[List[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """Build a pagination keyboard row."""
    nav = []
    if current_page > 0:
        nav.append(InlineKeyboardButton(
            "🔙", callback_data=f"{base_callback}_{current_page - 1}"
        ))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(
            f"{current_page + 1}/{total_pages}", callback_data="noop"
        ))
    if current_page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "🔜", callback_data=f"{base_callback}_{current_page + 1}"
        ))
    keyboard = []
    if extra_buttons:
        keyboard.extend(extra_buttons)
    if nav:
        keyboard.append(nav)
    return InlineKeyboardMarkup(keyboard)
