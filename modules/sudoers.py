# ====================================================================
# PLACE AT: /app/modules/sudoers.py
# ACTION: Replace existing file
# ====================================================================
"""
sudoers.py — dev-only system stats.

FIXES APPLIED:
• Removed PING_HANDLER — ping.py already owns /ping.
• Changed ["stats", "botstats"] → ["botstats"] only —
  userinfo.py already owns /stats with richer output.
"""

import os
import time

import psutil
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

import modules.sql.users_sql as sql
from beataniversebot_compat import dispatcher, StartTime, DEV_USERS, DRAGONS
from modules.helper_funcs.chat_status import dev_plus
from modules.disable import DisableAbleCommandHandler


def get_readable_time(seconds: int) -> str:
    result = ""
    (days, remainder) = divmod(seconds, 86400)
    (hours, remainder) = divmod(remainder, 3600)
    (minutes, second) = divmod(remainder, 60)
    if days != 0:
        result += f"{days}d "
    if hours != 0:
        result += f"{hours}h "
    if minutes != 0:
        result += f"{minutes}m "
    result += f"{second}s"
    return result


def get_bot_stats() -> str:
    bot_uptime = int(time.time() - StartTime)
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    process = psutil.Process(os.getpid())
    bot_ram = round(process.memory_info()[0] / 1024 ** 2)

    try:
        users = sql.num_users()
        chats = sql.num_chats()
    except Exception:
        users = "N/A"
        chats = "N/A"

    stats = (
        f"<b>⚙️ System Stats</b>\n\n"
        f"<b>• Uptime:</b> <code>{get_readable_time(bot_uptime)}</code>\n"
        f"<b>• Bot RAM:</b> <code>{bot_ram} MB</code>\n"
        f"<b>• CPU:</b> <code>{cpu}%</code>\n"
        f"<b>• RAM:</b> <code>{mem}%</code>\n"
        f"<b>• Disk:</b> <code>{disk}%</code>\n"
        f"<b>• Chats:</b> <code>{chats}</code>\n"
        f"<b>• Users:</b> <code>{users}</code>"
    )
    return stats


@dev_plus
def botstats(update: Update, context: CallbackContext):
    """Dev-only extended system stats (/botstats). /stats is owned by userinfo.py."""
    update.effective_message.reply_text(
        get_bot_stats(),
        parse_mode=ParseMode.HTML,
    )


# NOTE: /ping is owned by ping.py — NOT registered here to avoid double-replies.
# NOTE: /stats is owned by userinfo.py — only /botstats is registered here.
STATS_HANDLER = DisableAbleCommandHandler("botstats", botstats, run_async=True)

dispatcher.add_handler(STATS_HANDLER)

__mod_name__ = "Sᴜᴅᴏᴇʀs"
__command_list__ = ["botstats"]
__handlers__ = [STATS_HANDLER]
