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


def is_chatbot_active(chat_id):
    try:
        chat = SESSION.query(BeatChats).get(str(chat_id))
        return bool(chat)
    finally:
        SESSION.close()


def disable_chatbot(chat_id):
    with INSERTION_LOCK:
        beatchat = SESSION.query(BeatChats).get(str(chat_id))
        if not beatchat:
            beatchat = BeatChats(str(chat_id))
        SESSION.add(beatchat)
        SESSION.commit()


def enable_chatbot(chat_id):
    with INSERTION_LOCK:
        beatchat = SESSION.query(BeatChats).get(str(chat_id))
        if beatchat:
            SESSION.delete(beatchat)
        SESSION.commit()
