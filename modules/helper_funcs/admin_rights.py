from telegram import Chat, User


def user_can_promote(chat: Chat, user: User, bot_id: int) -> bool:
    try:
        member = chat.get_member(user.id)
        if hasattr(member, 'can_promote_members'):
            return bool(member.can_promote_members)
    except Exception:
        pass
    return False


def user_can_ban(chat: Chat, user: User, bot_id: int) -> bool:
    try:
        member = chat.get_member(user.id)
        if hasattr(member, 'can_restrict_members'):
            return bool(member.can_restrict_members)
    except Exception:
        pass
    return False


def user_can_pin(chat: Chat, user: User, bot_id: int) -> bool:
    try:
        member = chat.get_member(user.id)
        if hasattr(member, 'can_pin_messages'):
            return bool(member.can_pin_messages)
    except Exception:
        pass
    return False


def user_can_changeinfo(chat: Chat, user: User, bot_id: int) -> bool:
    try:
        member = chat.get_member(user.id)
        if hasattr(member, 'can_change_info'):
            return bool(member.can_change_info)
    except Exception:
        pass
    return False
