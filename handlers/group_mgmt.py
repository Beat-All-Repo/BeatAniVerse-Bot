"""handlers/group_mgmt.py — Group moderation commands (ban, mute, kick etc.)"""
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

async def _get_target(update, context):
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    if context.args:
        try:
            return await context.bot.get_chat(context.args[0])
        except Exception:
            pass
    return None

async def pin_cmd(update, context):
    if not update.message or not update.message.reply_to_message: return await update.message.reply_text("Reply to a message to pin it.")
    try: await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def unpin_cmd(update, context):
    try: await context.bot.unpin_chat_message(update.effective_chat.id)
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def del_cmd(update, context):
    if update.message and update.message.reply_to_message:
        try:
            await update.message.reply_to_message.delete()
            await update.message.delete()
        except Exception: pass

async def promote_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.promote_chat_member(update.effective_chat.id, target.id, can_manage_chat=True, can_delete_messages=True, can_restrict_members=True, can_invite_users=True, can_pin_messages=True)
        await update.message.reply_text(f"✅ Promoted {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def demote_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.promote_chat_member(update.effective_chat.id, target.id, can_manage_chat=False, can_delete_messages=False, can_restrict_members=False, can_promote_members=False, can_change_info=False, can_invite_users=False, can_pin_messages=False)
        await update.message.reply_text(f"✅ Demoted {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def mute_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False))
        await update.message.reply_text(f"🔇 Muted {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def unmute_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_documents=True, can_send_polls=True, can_invite_users=True))
        await update.message.reply_text(f"🔊 Unmuted {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def ban_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"🚫 Banned {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def unban_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"✅ Unbanned {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def kick_cmd(update, context):
    target = await _get_target(update, context)
    if not target: return await update.message.reply_text("Reply to a user or provide @username")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"👢 Kicked {target.first_name or target.id}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")

async def invitelink_cmd(update, context):
    try:
        link = await context.bot.export_chat_invite_link(update.effective_chat.id)
        await update.message.reply_text(f"🔗 Invite link:\n{link}")
    except Exception as exc: await update.message.reply_text(f"❌ {exc}")
