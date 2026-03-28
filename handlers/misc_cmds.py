"""handlers/misc_cmds.py — Admin utility commands."""
import os, sys, json, asyncio, csv
from io import StringIO, BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from core.config import ADMIN_ID, OWNER_ID, BOT_USERNAME, LINK_EXPIRY_MINUTES, TRANSITION_STICKER_ID
from core.text_utils import b, bq, e, code, format_number
from core.helpers import safe_reply, safe_send_message, safe_delete, get_uptime, get_system_stats_text
from core.buttons import _back_kb, bold_button
from core.filters_system import force_sub_required
from core.state_machine import user_states
from handlers.start import delete_update_message, delete_bot_prompt
from handlers.admin_panel import send_admin_menu, send_stats_panel

@force_sub_required
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    await send_stats_panel(context, update.effective_chat.id)

@force_sub_required
async def sysstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    await safe_reply(update, get_system_stats_text(), reply_markup=_back_kb())

@force_sub_required
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import get_user_count
        count = get_user_count()
        await safe_reply(update, b("👥 Total Registered Users:") + " " + code(format_number(count)))
    except Exception as exc:
        await safe_reply(update, b(f"❌ Error: {e(str(exc)[:100])}"))

@force_sub_required
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    from core.config import SETTINGS_IMAGE_URL
    keyboard = [
        [bold_button("ᴀɴɪᴍᴇ", callback_data="cat_settings_anime"), bold_button("ᴍᴀɴɢᴀ", callback_data="cat_settings_manga")],
        [bold_button("ᴍᴏᴠɪᴇ", callback_data="cat_settings_movie"), bold_button("ᴛᴠ sʜᴏᴡ", callback_data="cat_settings_tvshow")],
        [bold_button("🔙", callback_data="admin_back")],
    ]
    text = b("⚙️ ᴄᴀᴛᴇɢᴏʀʏ sᴇᴛᴛɪɴɢs") + "\n\n" + bq(b("sᴇʟᴇᴄᴛ ᴀ ᴄᴀᴛᴇɢᴏʀʏ ᴛᴏ ᴄᴏɴғɪɢᴜʀᴇ ɪᴛs ᴛᴇᴍᴘʟᴀᴛᴇ, ʙᴜᴛᴛᴏɴs, ᴡᴀᴛᴇʀᴍᴀʀᴋs, ᴀɴᴅ ᴍᴏʀᴇ."))
    markup = InlineKeyboardMarkup(keyboard)
    if SETTINGS_IMAGE_URL:
        from core.helpers import safe_send_photo
        sent = await safe_send_photo(context.bot, update.effective_chat.id, SETTINGS_IMAGE_URL, caption=text, reply_markup=markup)
        if sent: return
    await safe_reply(update, text, reply_markup=markup)

@force_sub_required
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    from handlers.upload import load_upload_progress, show_upload_menu
    await load_upload_progress()
    await show_upload_menu(update.effective_chat.id, context)

@force_sub_required
async def autoupdate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    from handlers.autoforward import _show_autoupdate_menu
    await _show_autoupdate_menu(context, update.effective_chat.id)

@force_sub_required
async def autoforward_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    from handlers.autoforward import _show_autoforward_menu
    await _show_autoforward_menu(context, update.effective_chat.id)

@force_sub_required
async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if len(context.args) < 1:
        await safe_reply(update, b("Usage: /addchannel @username_or_id [Title] [jbr]"))
        return
    identifier = context.args[0]
    if identifier.lstrip("-").isdigit():
        channel_lookup = int(identifier)
    else:
        channel_lookup = identifier if identifier.startswith("@") else f"@{identifier}"
    args_rest = context.args[1:]
    jbr = False
    if args_rest and args_rest[-1].lower() == "jbr":
        jbr = True
        args_rest = args_rest[:-1]
    title = " ".join(args_rest) if args_rest else None
    try:
        from database_dual import add_force_sub_channel
        chat_obj = await context.bot.get_chat(channel_lookup)
        if title is None:
            title = chat_obj.title or str(channel_lookup)
        channel_id_str = str(chat_obj.id)
        add_force_sub_channel(channel_id_str, title, join_by_request=jbr)
        jbr_str = " (Join By Request)" if jbr else ""
        await safe_reply(update, b(f"✅ Added: {e(title)} (ID: {channel_id_str}){e(jbr_str)} as force-sub channel."))
    except Exception as exc:
        await safe_reply(update, b(f"⚠️ Cannot access {e(str(identifier))}.\n\nError: {e(str(exc)[:100])}"))

@force_sub_required
async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if len(context.args) != 1:
        await safe_reply(update, b("Usage: /removechannel @username"))
        return
    from database_dual import delete_force_sub_channel
    delete_force_sub_channel(context.args[0])
    await safe_reply(update, b(f"🗑 Removed {e(context.args[0])} from force-sub channels."))

@force_sub_required
async def channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    from database_dual import get_all_force_sub_channels
    channels = get_all_force_sub_channels(return_usernames_only=False)
    if not channels:
        await safe_reply(update, b("📢 No force-sub channels configured."))
        return
    text = b(f"📢 Force-Sub Channels ({len(channels)}):") + "\n\n"
    for uname, title, jbr in channels:
        jbr_tag = " (Join By Request)" if jbr else ""
        text += f"• {b(e(title))}\n  {e(uname)}{jbr_tag}\n\n"
    await safe_reply(update, text)

@force_sub_required
async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /banuser @username_or_id"))
        return
    from database_dual import resolve_target_user_id, ban_user
    uid = resolve_target_user_id(context.args[0])
    if uid is None:
        await safe_reply(update, b(f"❌ User {e(context.args[0])} not found."))
        return
    if uid in (ADMIN_ID, OWNER_ID):
        await safe_reply(update, b("⚠️ Cannot ban admin/owner."))
        return
    ban_user(uid)
    await safe_reply(update, b(f"🚫 User ") + code(str(uid)) + b(" has been banned."))

@force_sub_required
async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /unbanuser @username_or_id"))
        return
    from database_dual import resolve_target_user_id, unban_user
    uid = resolve_target_user_id(context.args[0])
    if uid is None:
        await safe_reply(update, b(f"❌ User not found."))
        return
    unban_user(uid)
    await safe_reply(update, b(f"✅ User ") + code(str(uid)) + b(" has been unbanned."))

@force_sub_required
async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import get_user_count, get_all_users
        offset = int(context.args[0]) if context.args else 0
        total = get_user_count()
        users = get_all_users(limit=10, offset=offset)
        text = b(f"👥 Users {offset + 1}–{min(offset + 10, total)} of {format_number(total)}") + "\n\n"
        keyboard_rows = []
        for row in users:
            uid2, username, fname, lname, joined, banned = row
            name = f"{fname or ''} {lname or ''}".strip() or "N/A"
            status_icon = "🚫" if banned else "✅"
            uname_str = f"@{username}" if username else f"#{uid2}"
            text += f"{status_icon} {b(e(name[:20]))} — {e(uname_str)}\n"
        nav = []
        if offset > 0:
            nav.append(bold_button("🔙PREV", callback_data=f"user_page_{max(0, offset-10)}"))
        if total > offset + 10:
            nav.append(bold_button("NEXT🔜", callback_data=f"user_page_{offset+10}"))
        if nav: keyboard_rows.append(nav)
        keyboard_rows.append([bold_button("🔙", callback_data="user_management")])
        await safe_reply(update, text, reply_markup=InlineKeyboardMarkup(keyboard_rows))
    except Exception as exc:
        await safe_reply(update, b(f"❌ Error: {e(str(exc)[:100])}"))

@force_sub_required
async def deleteuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /deleteuser user_id"))
        return
    try:
        from database_dual import db_manager
        uid_del = int(context.args[0])
        if uid_del in (ADMIN_ID, OWNER_ID):
            await safe_reply(update, b("⚠️ Cannot delete admin/owner."))
            return
        with db_manager.get_cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s", (uid_del,))
        await safe_reply(update, b(f"✅ User ") + code(str(uid_del)) + b(" deleted from database."))
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))

@force_sub_required
async def exportusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    from core.text_utils import now_utc
    try:
        from database_dual import get_all_users
        rows = get_all_users(limit=None, offset=0)
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["user_id", "username", "first_name", "last_name", "joined_at", "banned"])
        writer.writerows(rows)
        output.seek(0)
        data_bytes = output.getvalue().encode("utf-8")
        await context.bot.send_document(
            update.effective_chat.id,
            document=BytesIO(data_bytes),
            filename=f"users_export_{now_utc().strftime('%Y%m%d_%H%M')}.csv",
            caption=b(f"📤 Exported {format_number(len(rows))} users."),
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        await safe_reply(update, b("❌ Export failed: ") + code(e(str(exc)[:200])))

@force_sub_required
async def broadcaststats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT id, mode, total_users, success, blocked, deleted, failed, created_at, completed_at FROM broadcast_history ORDER BY created_at DESC LIMIT 15")
            rows = cur.fetchall() or []
        if not rows:
            await safe_reply(update, b("📣 No broadcast history yet."), reply_markup=_back_kb())
            return
        text = b("📣 Recent Broadcasts:") + "\n\n"
        for row in rows:
            bid, mode, total, sent, blocked, deleted, failed, created, completed = row
            text += f"{b(f'ID #{bid}')} — {code(mode)}\n✅ {sent} | ❌ {failed} | 🚫 {blocked}\n📅 {str(created)[:16]}\n\n"
        await safe_reply(update, text, reply_markup=_back_kb())
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))

@force_sub_required
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import get_all_links
        links = get_all_links(bot_username=BOT_USERNAME)
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))
        return
    if not links:
        await safe_reply(update, b("🔗 No links generated yet."), reply_markup=_back_kb())
        return
    text = b(f"🔗 Generated Links ({len(links)}):") + "\n\n"
    for link_id, channel, title, src_bot, created, never_exp in links:
        line = f"• {b(e(title or channel))} — <code>t.me/{e(BOT_USERNAME)}?start={e(link_id)}</code>\n"
        if len(text) + len(line) > 3800:
            text += b("…more links truncated.")
            break
        text += line
    await safe_reply(update, text, reply_markup=_back_kb())

@force_sub_required
async def addclone_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    user_states.pop(update.effective_user.id, None)
    await delete_bot_prompt(context, update.effective_chat.id)
    if context.args:
        from handlers.clones import register_clone_token
        await register_clone_token(update, context, context.args[0].strip())
        return
    user_states[update.effective_user.id] = "ADD_CLONE_TOKEN"
    msg = await safe_reply(update, b("🤖 Add Clone Bot") + "\n\n" + bq(b("Send the BOT TOKEN of the clone bot.\n\n⚠️ Keep the token secret!")))
    from handlers.start import store_bot_prompt
    await store_bot_prompt(context, msg)

@force_sub_required
async def clones_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    from database_dual import get_all_clone_bots
    clones = get_all_clone_bots(active_only=True)
    if not clones:
        await safe_reply(update, b("🤖 No clone bots registered yet."))
        return
    text = b(f"🤖 Active Clone Bots ({len(clones)}):") + "\n\n"
    for cid, token, uname, active, added in clones:
        text += f"• @{e(uname)} — {code(str(added)[:10])}\n"
    await safe_reply(update, text)

@force_sub_required
async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    triggered_by = (update.effective_user.username or str(update.effective_user.id))
    try:
        with open("restart_message.json", "w") as f:
            json.dump({"chat_id": update.effective_chat.id, "admin_id": ADMIN_ID, "triggered_by": triggered_by}, f)
    except Exception: pass
    try: await safe_reply(update, b("♻️ Bot is restarting… Be right back!"))
    except Exception: pass
    await asyncio.sleep(1)
    sys.exit(0)

@force_sub_required
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        with open("logs/bot.log", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-60:]
        log_text = "".join(lines)
        if len(log_text) > 3900: log_text = log_text[-3900:]
        await safe_reply(update, f"<pre>{e(log_text)}</pre>")
    except Exception as exc:
        await safe_reply(update, b("❌ Error reading logs: ") + code(e(str(exc))))

@force_sub_required
async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /connect @group_or_id"))
        return
    try:
        from database_dual import db_manager
        chat = await context.bot.get_chat(context.args[0])
        if chat.type not in ("group", "supergroup"):
            await safe_reply(update, b("❌ That's not a group."))
            return
        with db_manager.get_cursor() as cur:
            cur.execute("INSERT INTO connected_groups (group_id, group_username, group_title, connected_by) VALUES (%s, %s, %s, %s) ON CONFLICT (group_id) DO UPDATE SET active = TRUE", (chat.id, chat.username, chat.title, update.effective_user.id))
        await safe_reply(update, b(f"✅ Connected to {e(chat.title)}"))
    except Exception as exc:
        from core.helpers import UserFriendlyError
        await safe_reply(update, UserFriendlyError.get_user_message(exc))

@force_sub_required
async def disconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    if not context.args:
        await safe_reply(update, b("Usage: /disconnect @group_or_id"))
        return
    try:
        from database_dual import db_manager
        chat = await context.bot.get_chat(context.args[0])
        with db_manager.get_cursor() as cur:
            cur.execute("UPDATE connected_groups SET active = FALSE WHERE group_id = %s", (chat.id,))
        await safe_reply(update, b(f"✅ Disconnected from {e(chat.title)}"))
    except Exception as exc:
        from core.helpers import UserFriendlyError
        await safe_reply(update, UserFriendlyError.get_user_message(exc))

@force_sub_required
async def connections_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import db_manager
        with db_manager.get_cursor() as cur:
            cur.execute("SELECT group_id, group_username, group_title FROM connected_groups WHERE active = TRUE")
            rows = cur.fetchall() or []
        if not rows:
            await safe_reply(update, b("🔗 No connected groups."))
            return
        text = b(f"🔗 Connected Groups ({len(rows)}):") + "\n\n"
        for gid, uname, title in rows:
            text += f"• {b(e(title or ''))} {('@' + uname) if uname else ''} {code(str(gid))}\n"
        await safe_reply(update, text)
    except Exception as exc:
        await safe_reply(update, b("❌ Error: ") + code(e(str(exc)[:200])))

async def set_loader_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    await delete_update_message(update, context)
    try:
        from database_dual import get_setting, set_setting
    except ImportError:
        return
    reply = update.message.reply_to_message if update.message else None
    args = context.args or []
    _sticker_obj = None
    if reply and reply.sticker: _sticker_obj = reply.sticker
    elif update.message and update.message.sticker: _sticker_obj = update.message.sticker
    if _sticker_obj:
        sticker_id = _sticker_obj.file_id
        set_setting("loading_sticker_id", sticker_id)
        set_setting("loading_anim_enabled", "true")
        set_setting("env_TRANSITION_STICKER", sticker_id)
        try: await context.bot.send_sticker(update.effective_chat.id, sticker_id)
        except Exception: pass
        await safe_send_message(context.bot, update.effective_chat.id, "<b>✅ Loading sticker set!</b>", parse_mode="HTML")
    elif args and args[0].lower() == "off":
        set_setting("loading_anim_enabled", "false")
        await safe_send_message(context.bot, update.effective_chat.id, "<b>✅ Loading animation disabled.</b>", parse_mode="HTML")
    elif args and args[0].lower() == "on":
        set_setting("loading_anim_enabled", "true")
        set_setting("loading_sticker_id", "")
        await safe_send_message(context.bot, update.effective_chat.id, "<b>✅ Loading animation restored to default ❗ style.</b>", parse_mode="HTML")
    else:
        enabled = get_setting("loading_anim_enabled", "true") == "true"
        sticker_id = get_setting("loading_sticker_id", "")
        status = "🟢 Enabled" if enabled else "🔴 Disabled"
        kind = f"Custom Sticker (<code>{sticker_id[:20]}…</code>)" if sticker_id else "Default ❗ Animation"
        await safe_send_message(context.bot, update.effective_chat.id, f"<b> Loading Animation</b>\n\n<b>Status:</b> {status}\n<b>Type:</b> {kind}", parse_mode="HTML")

async def addpanelimg_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    from core.panel_image import get_panel_db_images, save_panel_db_images
    from core.config import PANEL_DB_CHANNEL
    msg = update.effective_message
    chat_id = msg.chat_id
    if not PANEL_DB_CHANNEL:
        await safe_send_message(context.bot, chat_id, "❌ <b>PANEL_DB_CHANNEL not set.</b>", parse_mode="HTML")
        return
    photos = []
    if msg.reply_to_message and msg.reply_to_message.photo:
        photos = [msg.reply_to_message.photo[-1]]
    elif msg.photo:
        photos = [msg.photo[-1]]
    if not photos:
        await safe_send_message(context.bot, chat_id, "ℹ️ Send a photo with /addpanelimg or reply to a photo.")
        return
    items = get_panel_db_images()
    added = 0
    for photo in photos:
        try:
            sent = await context.bot.send_photo(chat_id=PANEL_DB_CHANNEL, photo=photo.file_id, caption=f"Panel image #{len(items)+1}")
            file_id = sent.photo[-1].file_id
            items.append({"index": len(items)+1, "msg_id": sent.message_id, "file_id": file_id})
            added += 1
        except Exception: pass
    if added:
        save_panel_db_images(items)
    await safe_send_message(context.bot, chat_id, f"✅ Added {added} image(s). Total: {len(items)}")

async def getfileid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or update.effective_user.id not in (ADMIN_ID, OWNER_ID): return
    msg = update.effective_message
    photo = None
    if msg.reply_to_message and msg.reply_to_message.photo:
        photo = msg.reply_to_message.photo[-1]
    elif msg.photo:
        photo = msg.photo[-1]
    if not photo:
        await safe_send_message(context.bot, msg.chat_id, "📎 <b>How to use:</b> Reply to any image with /getfileid.", parse_mode="HTML")
        return
    file_id = photo.file_id
    await safe_send_message(context.bot, msg.chat_id, f"✅ <b>File ID:</b>\n<code>{file_id}</code>", parse_mode="HTML")
