# ====================================================================
# PLACE AT: /app/BeatVerseProbot/utils/mongo.py
# ACTION: CREATE new file
# ====================================================================
"""
BeatVerseProbot.utils.mongo stub.
Provides get_couple, save_couple, and db for modules that use MongoDB directly.
Falls back to database_dual's real implementation when available.
"""
import logging
from typing import Optional
logger = logging.getLogger(__name__)

# Try to use real DB implementation
def _get_db():
    try:
        from database_dual import _MG
        return _MG.db if _MG and hasattr(_MG, 'db') else None
    except Exception:
        return None

async def get_couple(chat_id: int, date: str) -> Optional[dict]:
    """Get today's couple for a chat."""
    db = _get_db()
    if db:
        try:
            return db.couples.find_one({"chat_id": chat_id, "date": date})
        except Exception:
            pass
    return None

async def save_couple(chat_id: int, date: str, couple: dict) -> bool:
    """Save today's couple for a chat."""
    db = _get_db()
    if db:
        try:
            db.couples.update_one(
                {"chat_id": chat_id, "date": date},
                {"$set": {**couple, "chat_id": chat_id, "date": date}},
                upsert=True
            )
            return True
        except Exception:
            pass
    return False

# db attribute for modules that do: from BeatVerseProbot.utils.mongo import db
class _DBProxy:
    def __getattr__(self, name):
        db = _get_db()
        if db:
            return getattr(db, name, None)
        return None

db = _DBProxy()
