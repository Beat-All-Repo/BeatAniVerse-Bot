# ====================================================================
# PLACE AT: /app/modules/disasters.py
# ACTION: Replace existing file
# ====================================================================
import html
import json
import os
from typing import Optional

from telegram import ParseMode, TelegramError, Update
from telegram.ext import CallbackContext, CommandHandler
from telegram.utils.helpers import mention_html

from beataniversebot_compat import (
    DEMONS,
    DEV_USERS,
    DRAGONS,
    OWNER_ID,
    SUPPORT_CHAT,
    TIGERS,
    WOLVES,
    dispatcher,
)
from modules.helper_funcs.chat_status import (
    dev_plus,
    sudo_plus,
    whitelist_plus,
)
from modules.helper_funcs.extraction import extract_user
from modules.log_channel import gloggable

ELEVATED_USERS_FILE = os.path.join(os.getcwd(), "BeatVerseProbot/elevated_users.json")

# Auto-create the file if it doesn't exist (e.g. fresh Render deploy)
if not os.path.isfile(ELEVATED_USERS_FILE):
    with open(ELEVATED_USERS_FILE, "w") as _f:
        import json as _json
        _json.dump({"sudos": [], "supports": [], "tigers": [], "wolves": []}, _f)


def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        reply = "That...is a chat! baka ka omae?"

    elif user_id == bot.id:
        reply = "This does not work that way."

    else:
        reply = None
    return reply


@dev_plus
@gloggable
def addsudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DRAGONS:
        message.reply_text("This member is already a Dragon Disaster")
        return ""

    if user_id in DEMONS:
        rt += "Requested HA to promote a Demon Disaster to Dragon."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        rt += "Requested HA to promote a Wolf Disaster to Dragon."
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    data["sudos"].append(user_id)
    DRAGONS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt
        + "\nSuccessfully set Disaster level of {} to Dragon!".format(
            user_member.first_name
        )
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DRAGONS:
        rt += "Requested HA to demote this Dragon to Demon"
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        message.reply_text("This user is already a Demon Disaster.")
        return ""

    if user_id in WOLVES:
        rt += "Requested HA to promote this Wolf Disaster to Demon"
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    data["supports"].append(user_id)
    DEMONS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} was added as a Demon Disaster!"
    )

    log_message = (
        f"#SUPPORT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addwhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DRAGONS:
        rt += "This member is a Dragon Disaster, Demoting to Wolf."
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        rt += "This user is already a Demon Disaster, Demoting to Wolf."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        message.reply_text("This user is already a Wolf Disaster.")
        return ""

    data["whitelists"].append(user_id)
    WOLVES.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to a Wolf Disaster!"
    )

    log_message = (
        f"#WHITELIST\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@sudo_plus
@gloggable
def addtiger(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DRAGONS:
        rt += "This member is a Dragon Disaster, Demoting to Tiger."
        data["sudos"].remove(user_id)
        DRAGONS.remove(user_id)

    if user_id in DEMONS:
        rt += "This user is already a Demon Disaster, Demoting to Tiger."
        data["supports"].remove(user_id)
        DEMONS.remove(user_id)

    if user_id in WOLVES:
        rt += "This user is already a Wolf Disaster, Demoting to Tiger."
        data["whitelists"].remove(user_id)
        WOLVES.remove(user_id)

    if user_id in TIGERS:
        message.reply_text("This user is already a Tiger.")
        return ""

    data["tigers"].append(user_id)
    TIGERS.append(user_id)

    with open(ELEVATED_USERS_FILE, "w") as outfile:
        json.dump(data, outfile, indent=4)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to a Tiger Disaster!"
    )

    log_message = (
        f"#TIGER\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@dev_plus
@gloggable
def removesudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DRAGONS:
        message.reply_text("Requested HA to demote this user to Civilian")
        DRAGONS.remove(user_id)
        data["sudos"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("This user is not a Dragon Disaster!")
        return ""


@sudo_plus
@gloggable
def removesupport(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in DEMONS:
        message.reply_text("Requested HA to demote this user to Civilian")
        DEMONS.remove(user_id)
        data["supports"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNSUPPORT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("This user is not a Demon level Disaster!")
        return ""


@sudo_plus
@gloggable
def removewhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in WOLVES:
        message.reply_text("Demoting to normal user")
        WOLVES.remove(user_id)
        data["whitelists"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a Wolf Disaster!")
        return ""


@sudo_plus
@gloggable
def removetiger(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    with open(ELEVATED_USERS_FILE, "r") as infile:
        data = json.load(infile)

    if user_id in TIGERS:
        message.reply_text("Demoting to normal user")
        TIGERS.remove(user_id)
        data["tigers"].remove(user_id)

        with open(ELEVATED_USERS_FILE, "w") as outfile:
            json.dump(data, outfile, indent=4)

        log_message = (
            f"#UNTIGER\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a Tiger Disaster!")
        return ""


@whitelist_plus
def whitelistlist(update: Update, context: CallbackContext):
    reply = "<b>Known Wolf Disasters 🐺:</b>\n"
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    bot = context.bot
    for each_user in WOLVES:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def tigerlist(update: Update, context: CallbackContext):
    reply = "<b>Known Tiger Disasters 🐯:</b>\n"
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    bot = context.bot
    for each_user in TIGERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def supportlist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    reply = "<b>Known Demon Disasters 👹:</b>\n"
    for each_user in DEMONS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def sudolist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    true_sudo = list(set(DRAGONS) - set(DEV_USERS))
    reply = "<b>Known Dragon Disasters 🐉:</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


@whitelist_plus
def devlist(update: Update, context: CallbackContext):
    bot = context.bot
    m = update.effective_message.reply_text(
        "<code>Gathering intel..</code>", parse_mode=ParseMode.HTML
    )
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "✨ <b>Dev users list :</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, html.escape(user.first_name))}\n"
        except TelegramError:
            pass
    m.edit_text(reply, parse_mode=ParseMode.HTML)


__help__ = f"""
*⚠️ Notice:*
Commands listed here only work for users with special access are mainly used for troubleshooting, debugging purposes.
Group admins/group owners do not need these commands.

*List all special users:*
 ❍ /sudolist*:* Lists all Dragon disasters
 ❍ /supportlist*:* Lists all Demon disasters
 ❍ /tigers*:* Lists all Tigers disasters
 ❍ /wolves*:* Lists all Wolf disasters
 ❍ /devlist*:* Lists all Hero Association members
 ❍ /addsudo*:* Adds a user to Dragon
 ❍ /adddemon*:* Adds a user to Demon
 ❍ /addtiger*:* Adds a user to Tiger
 ❍ /addwolf*:* Adds a user to Wolf
 ❍ `Add dev doesnt exist, devs should know how to add themselves`

*Broadcast: (Bot owner only)*
*Note:* This supports basic markdown
 ❍ /broadcastall*:* Broadcasts everywhere
 ❍ /broadcastusers*:* Broadcasts too all users
 ❍ /broadcastgroups*:* Broadcasts too all groups

*Groups Info:*
 ❍ /groups*:* List the groups with Name, ID, members count as a txt
 ❍ /leave <ID>*:* Leave the group, ID must have hyphen
 ❍ /stats*:* Shows overall bot stats
 ❍ /getchats*:* Gets a list of group names the user has been seen in. Bot owner only
 ❍ /ginfo username/link/ID*:* Pulls info panel for entire group

*Access control:* 
 ❍ /ignore*:* Blacklists a user from using the bot entirely
 ❍ /lockdown <off/on>*:* Toggles bot adding to groups
 ❍ /notice*:* Removes user from blacklist
 ❍ /ignoredlist*:* Lists ignored users

*Speedtest:*
 ❍ /speedtest*:* Runs a speedtest and gives you 2 options to choose from, text or image output

*Module loading:*
 ❍ /listmodules*:* Lists names of all modules
 ❍ /load modulename*:* Loads the said module to memory without restarting.
 ❍ /unload modulename*:* Loads the said module from memory without restarting memory without restarting the bot 

*Remote commands:*
 ❍ /rban*:* user group*:* Remote ban
 ❍ /runban*:* user group*:* Remote un-ban
 ❍ /rpunch*:* user group*:* Remote punch
 ❍ /rmute*:* user group*:* Remote mute
 ❍ /runmute*:* user group*:* Remote un-mute

*Windows self hosted only:*
 ❍ /reboot*:* Restarts the bots service
 ❍ /gitpull*:* Pulls the repo and then restarts the bots service
 
*Debugging and Shell:* 
 ❍ /debug <on/off>*:* Logs commands to updates.txt
 ❍ /logs*:* Run this in support group to get logs in pm
 ❍ /eval*:* Self explanatory
 ❍ /sh*:* Runs shell command
 ❍ /shell*:* Runs shell command
 ❍ /clearlocals*:* As the name goes
 ❍ /dbcleanup*:* Removes deleted accs and groups from db
 ❍ /py*:* Runs python code
 
*Global Bans:*
 ❍ /gban <id> <reason>*:* Gbans the user, works by reply too
 ❍ /ungban*:* Ungbans the user, same usage as gban
 ❍ /gbanlist*:* Outputs a list of gbanned users

*Global Blue Text*
 ❍ /gignoreblue*:* <word>*:* Globally ignore bluetext cleaning of saved word across BeatVerse Bot.
 ❍ /ungignoreblue*:* <word>*:* Remove said command from global cleaning list

*Heroku Settings*
*Owner only*
 ❍ /usage*:* Check your heroku dyno hours remaining.
 ❍ /see var <var>*:* Get your existing varibles, use it only on your private group!
 ❍ /set var <newvar> <vavariable>*:* Add new variable or update existing value variable.
 ❍ /del var <var>*:* Delete existing variable.
 ❍ /logs Get heroku dyno logs.

`⚠️ Read from top`
Visit @{SUPPORT_CHAT} for more information.
"""

SUDO_HANDLER = CommandHandler("addsudo", addsudo, run_async=True)
SUPPORT_HANDLER = CommandHandler(("addsupport", "adddemon"), addsupport, run_async=True)
TIGER_HANDLER = CommandHandler(("addtiger"), addtiger, run_async=True)
WHITELIST_HANDLER = CommandHandler(
    ("addwhitelist", "addwolf"), addwhitelist, run_async=True
)
UNSUDO_HANDLER = CommandHandler(("removesudo", "rmsudo"), removesudo, run_async=True)
UNSUPPORT_HANDLER = CommandHandler(
    ("removesupport", "removedemon"), removesupport, run_async=True
)
UNTIGER_HANDLER = CommandHandler(("removetiger"), removetiger, run_async=True)
UNWHITELIST_HANDLER = CommandHandler(
    ("removewhitelist", "removewolf"), removewhitelist, run_async=True
)
WHITELISTLIST_HANDLER = CommandHandler(
    ["whitelistlist", "wolves"], whitelistlist, run_async=True
)
TIGERLIST_HANDLER = CommandHandler(["tigers"], tigerlist, run_async=True)
SUPPORTLIST_HANDLER = CommandHandler("supportlist", supportlist, run_async=True)
SUDOLIST_HANDLER = CommandHandler("sudolist", sudolist, run_async=True)
DEVLIST_HANDLER = CommandHandler("devlist", devlist, run_async=True)

dispatcher.add_handler(SUDO_HANDLER)
dispatcher.add_handler(SUPPORT_HANDLER)
dispatcher.add_handler(TIGER_HANDLER)
dispatcher.add_handler(WHITELIST_HANDLER)
dispatcher.add_handler(UNSUDO_HANDLER)
dispatcher.add_handler(UNSUPPORT_HANDLER)
dispatcher.add_handler(UNTIGER_HANDLER)
dispatcher.add_handler(UNWHITELIST_HANDLER)
dispatcher.add_handler(WHITELISTLIST_HANDLER)
dispatcher.add_handler(TIGERLIST_HANDLER)
dispatcher.add_handler(SUPPORTLIST_HANDLER)
dispatcher.add_handler(SUDOLIST_HANDLER)
dispatcher.add_handler(DEVLIST_HANDLER)

__mod_name__ = "Dᴇᴠs"
__handlers__ = [
    SUDO_HANDLER,
    SUPPORT_HANDLER,
    TIGER_HANDLER,
    WHITELIST_HANDLER,
    UNSUDO_HANDLER,
    UNSUPPORT_HANDLER,
    UNTIGER_HANDLER,
    UNWHITELIST_HANDLER,
    WHITELISTLIST_HANDLER,
    TIGERLIST_HANDLER,
    SUPPORTLIST_HANDLER,
    SUDOLIST_HANDLER,
    DEVLIST_HANDLER,
]
