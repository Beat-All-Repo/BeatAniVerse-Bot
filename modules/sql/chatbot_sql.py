"""
modules/sql/chatbot_sql.py
===========================
Chatbot enable/disable persistence.

TABLE  beat_chats  — stores chats where chatbot is EXPLICITLY ENABLED.
  • chat NOT in table  → chatbot in "trigger-only" mode (keyword/mention/reply)
  • chat IN table      → chatbot fully enabled (responds to any text message)

Fixes vs original:
  ✅ Inverted semantics: table now tracks ENABLED (not disabled) chats
  ✅ is_chatbot_active()  → True  = chatbot fully enabled for this chat
  ✅ enable_chatbot()     → adds  to table
  ✅ disable_chatbot()    → removes from table
  ✅ is_chatbot_enabled() = same as is_chatbot_active() (explicit alias)
"""
import threading

from sqlalchemy import Column, String

from modules.sql import BASE, SESSION


class BeatChats(BASE):
    __tablename__ = "beat_chats"
    chat_id = Column(String(14), primary_key=True)

    def __init__(self, chat_id):
        self.chat_id = chat_id


BeatChats.__table__.create(checkfirst=True)
INSERTION_LOCK = threading.RLock()


def is_chatbot_active(chat_id: int) -> bool:
    """Return True when chatbot is FULLY ENABLED for this chat (chat is in table)."""
    try:
        chat = SESSION.query(BeatChats).get(str(chat_id))
        return bool(chat)
    finally:
        SESSION.close()


# Alias kept for compatibility
is_chatbot_enabled = is_chatbot_active


def enable_chatbot(chat_id: int) -> None:
    """Add chat to the enabled table → full chatbot mode for this chat."""
    with INSERTION_LOCK:
        row = SESSION.query(BeatChats).get(str(chat_id))
        if not row:
            row = BeatChats(str(chat_id))
            SESSION.add(row)
        SESSION.commit()


def disable_chatbot(chat_id: int) -> None:
    """Remove chat from enabled table → revert to trigger-only mode."""
    with INSERTION_LOCK:
        row = SESSION.query(BeatChats).get(str(chat_id))
        if row:
            SESSION.delete(row)
        SESSION.commit()
