"""
broadcast_engine.py
===================
Independent broadcast system for BeatAniVerse bot.

Key design:
  • Works even when database is down / inaccessible
  • Tracks users in a local flat file as backup (users_fallback.txt)
  • Every /start registers the user_id both in DB AND local file
  • Broadcast reads from DB first, falls back to local file
  • Runs in background — never blocks the bot
  • Handles Flood/RetryAfter automatically
  • Admin gets live progress updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Local fallback user store ─────────────────────────────────────────────────
_FALLBACK_FILE = Path(os.getenv("USERS_FALLBACK_FILE", "users_fallback.txt"))
_FALLBACK_LOCK = asyncio.Lock()


def register_user_local(user_id: int) -> None:
    """
    Always-on registration: writes user_id to local file.
    Called from /start BEFORE any DB attempt so no user is ever missed.
    Thread-safe via append mode (atomic on Linux).
    """
    try:
        with open(_FALLBACK_FILE, "a", encoding="utf-8") as f:
            f.write(f"{user_id}\n")
    except Exception as exc:
        logger.debug(f"[broadcast_engine] local register failed: {exc}")


def get_all_users_local() -> list[int]:
    """Read all unique user_ids from local fallback file."""
    if not _FALLBACK_FILE.exists():
        return []
    seen: set[int] = set()
    try:
        with open(_FALLBACK_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.lstrip("-").isdigit():
                    seen.add(int(line))
    except Exception as exc:
        logger.debug(f"[broadcast_engine] read local: {exc}")
    return list(seen)


def get_all_users_combined() -> list[int]:
    """
    Returns all known user IDs: DB + local file, deduplicated.
    Falls back gracefully if DB is down.
    """
    uids: set[int] = set()

    # 1. Try DB
    try:
        from database_dual import get_all_users
        rows = get_all_users(limit=None, offset=0) or []
        for row in rows:
            uid = row[0] if isinstance(row, (list, tuple)) else row
            if uid:
                uids.add(int(uid))
        logger.debug(f"[broadcast_engine] DB users: {len(uids)}")
    except Exception as exc:
        logger.warning(f"[broadcast_engine] DB unavailable, using local only: {exc}")

    # 2. Always also include local file (catches users registered during DB downtime)
    local = get_all_users_local()
    uids.update(local)
    logger.debug(f"[broadcast_engine] Total unique users: {len(uids)}")
    return list(uids)


# ── Broadcast execution ────────────────────────────────────────────────────────

_RATE_DELAY: float = float(os.getenv("BROADCAST_RATE_DELAY", "0.05"))
_PROGRESS_EVERY: int = 200  # send progress update every N users


async def broadcast_message(
    bot: Any,
    admin_chat_id: int,
    from_chat_id: int,
    message_id: int,
    pin: bool = False,
    silent: bool = False,
    auto_delete_hrs: int = 0,
) -> None:
    """
    Broadcast a message to all known users.
    Works independently of database state.

    Args:
        bot:            Telegram bot instance
        admin_chat_id:  Where to send progress/results
        from_chat_id:   Source chat for copy_message
        message_id:     Source message ID
        pin:            Whether to pin in each user's DM
        silent:         Silent notification
        auto_delete_hrs: Auto-delete after N hours (0 = no delete)
    """
    users = get_all_users_combined()
    total = len(users)

    if total == 0:
        try:
            await bot.send_message(
                admin_chat_id,
                "📣 <b>No users found in any store.</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    progress_msg = None
    try:
        progress_msg = await bot.send_message(
            admin_chat_id,
            f"📣 <b>Broadcasting to {total:,} users…</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    sent = failed = blocked = 0
    start_ts = time.time()

    for i, uid in enumerate(users):
        try:
            msg = await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id,
                disable_notification=silent,
            )
            sent += 1

            if pin and msg:
                try:
                    await bot.pin_chat_message(uid, msg.message_id, disable_notification=True)
                except Exception:
                    pass

            if auto_delete_hrs > 0 and msg:
                delay_secs = auto_delete_hrs * 3600
                mid = msg.message_id

                async def _del_later(cid=uid, m=mid, d=delay_secs):
                    await asyncio.sleep(d)
                    try:
                        await bot.delete_message(cid, m)
                    except Exception:
                        pass

                asyncio.create_task(_del_later())

        except Exception as exc:
            err = str(exc).lower()
            if "retry after" in err or "flood" in err:
                try:
                    import re
                    secs = int(re.search(r"retry after (\d+)", err).group(1)) + 1
                except Exception:
                    secs = 5
                await asyncio.sleep(secs)
                try:
                    await bot.copy_message(uid, from_chat_id, message_id,
                                           disable_notification=silent)
                    sent += 1
                except Exception:
                    failed += 1
            elif any(k in err for k in ("blocked", "deactivated", "not found", "forbidden")):
                blocked += 1
                failed += 1
            else:
                failed += 1

        # Progress update
        if progress_msg and (i + 1) % _PROGRESS_EVERY == 0:
            elapsed = time.time() - start_ts
            rate = (i + 1) / max(elapsed, 1)
            eta = int((total - i - 1) / max(rate, 0.01))
            try:
                await progress_msg.edit_text(
                    f"📣 <b>Broadcasting…</b> {i+1:,}/{total:,}\n"
                    f"✅ {sent:,}  ❌ {failed:,}  🚫 {blocked:,}\n"
                    f"⏱ ETA: {eta//60}m {eta%60}s",
                    parse_mode="HTML"
                )
            except Exception:
                pass

        await asyncio.sleep(_RATE_DELAY)

    elapsed_total = int(time.time() - start_ts)
    result = (
        f"📣 <b>Broadcast Complete!</b>\n\n"
        f"✅ <b>Sent:</b> {sent:,}\n"
        f"❌ <b>Failed:</b> {failed:,}\n"
        f"🚫 <b>Blocked/Inactive:</b> {blocked:,}\n"
        f"👥 <b>Total targeted:</b> {total:,}\n"
        f"⏱ <b>Time:</b> {elapsed_total//60}m {elapsed_total%60}s"
    )
    if progress_msg:
        try:
            await progress_msg.edit_text(result, parse_mode="HTML")
            return
        except Exception:
            pass
    try:
        await bot.send_message(admin_chat_id, result, parse_mode="HTML")
    except Exception:
        pass


# ── Quick helpers for bot.py / handlers ───────────────────────────────────────

def ensure_user_registered(user_id: int, username: str = "", first_name: str = "") -> None:
    """
    Called on every /start. Registers to local file immediately (no await needed),
    then tries DB in background.
    """
    register_user_local(user_id)
    # DB registration is handled by the normal flow in start.py


async def start_broadcast_task(
    bot: Any,
    admin_chat_id: int,
    from_chat_id: int,
    message_id: int,
    mode: str = "normal",
) -> None:
    """
    Kick off broadcast as a background task.
    mode: normal | pin | silent | auto_delete_24h
    """
    pin = "pin" in mode
    silent = "silent" in mode
    auto_del = 24 if "auto_delete" in mode else 0

    asyncio.create_task(
        broadcast_message(
            bot=bot,
            admin_chat_id=admin_chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            pin=pin,
            silent=silent,
            auto_delete_hrs=auto_del,
        )
    )
