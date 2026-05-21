# ==============================================================================
# PLACE AT: /app/database_dual.py
# ACTION: Replace existing file
# ==============================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Pure MongoDB Database Layer
================================================
100% MongoDB — NeonDB / PostgreSQL completely removed.
Exports the EXACT same public API as the original database_dual.py so
no other file needs to change.

All tables that were in PostgreSQL are now MongoDB collections.
Auto-increment IDs use a _counters collection (atomic $inc).

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import logging
import json
import secrets
import re as _re
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB layer
# ──────────────────────────────────────────────────────────────────────────────

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import PyMongoError
    PYMONGO_OK = True
except ImportError:
    PYMONGO_OK = False


class _MG:
    db: Optional[Any] = None


# ──────────────────────────────────────────────────────────────────────────────
#  INIT
# ──────────────────────────────────────────────────────────────────────────────

def init_db(database_url: str = "", mongo_uri: str = "") -> None:
    """Initialise MongoDB.  database_url is accepted but silently ignored."""
    if not mongo_uri:
        raise RuntimeError(
            "FATAL: MONGO_DB_URI is not set. MongoDB is the only supported database."
        )
    if not PYMONGO_OK:
        raise RuntimeError("pymongo is not installed. Run: pip install pymongo")
    _init_mongo(mongo_uri)


def _init_mongo(uri: str) -> None:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.server_info()          # force connection
        try:
            _default = client.get_default_database()
        except Exception:
            _default = None
        _MG.db = _default if _default is not None else client["beataniversebot"]
        _migrate_mongo()
        logger.info("✅ [MongoDB] Connected and indexed")
    except Exception as exc:
        logger.error(f"[MongoDB] init failed: {exc}")
        raise


# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _db() -> Any:
    """Return the MongoDB database handle (raises if not initialised)."""
    if _MG.db is None:
        raise RuntimeError("MongoDB not initialised. Call init_db() first.")
    return _MG.db


def _next_id(collection_name: str) -> int:
    """Atomic auto-increment counter stored in _counters collection."""
    result = _db()["_counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB migration — create indexes
# ──────────────────────────────────────────────────────────────────────────────

def _migrate_mongo() -> None:
    db = _db()
    try:
        # Users
        db.users.create_index("user_id", unique=True)
        db.users.create_index("username")

        # Force sub
        db.force_sub_channels.create_index("channel_username", unique=True)
        db.force_sub_channels.create_index("channel_id")
        db.rqst_fsub_Channel_data.create_index("_id")

        # Generated links
        db.generated_links.create_index("link_id", unique=True)
        db.generated_links.create_index("source_bot_username")
        db.generated_links.create_index("created_time")

        # Settings
        db.bot_settings.create_index("key", unique=True)

        # Clone bots
        db.clone_bots.create_index("bot_token", unique=True)
        db.clone_bots.create_index("bot_username")

        # Category settings
        db.category_settings.create_index("category", unique=True)

        # Auto-forward
        db.auto_forward_connections.create_index("id", unique=True)
        db.auto_forward_filters.create_index("connection_id")
        db.auto_forward_replacements.create_index("connection_id")
        db.auto_forward_state.create_index("connection_id", unique=True)

        # Manga auto update
        db.manga_auto_update.create_index("id", unique=True)

        # Scheduled broadcasts
        db.scheduled_broadcasts.create_index("id", unique=True)
        db.scheduled_broadcasts.create_index([("status", ASCENDING), ("execute_at", ASCENDING)])

        # Broadcast history
        db.broadcast_history.create_index("id", unique=True)

        # Feature flags
        db.feature_flags.create_index(
            [("feature_name", ASCENDING), ("entity_id", ASCENDING), ("entity_type", ASCENDING)],
            unique=True,
        )

        # Bot progress
        db.bot_progress.create_index("id", unique=True)

        # Connected groups
        db.connected_groups.create_index("group_id", unique=True)

        # Posts cache
        db.posts_cache.create_index("anilist_id")

        # Anime channel links
        db.anime_channel_links.create_index(
            [("anime_title", ASCENDING), ("channel_id", ASCENDING)], unique=True
        )

        # Filter poster cache
        db.filter_poster_cache.create_index("cache_key", unique=True)

        # Channel welcome
        db.channel_welcome_settings.create_index("channel_id", unique=True)

        # Search analytics
        db.search_analytics.create_index(
            [("anime_title", ASCENDING), ("user_id", ASCENDING)], unique=True
        )

        # Pending deletes
        db.pending_message_deletes.create_index("id", unique=True)
        db.pending_message_deletes.create_index("delete_at")

        # Poster premium / usage / couples / chatbot (already exist)
        db.poster_premium.create_index("user_id", unique=True)
        db.poster_usage.create_index(
            [("user_id", ASCENDING), ("date", ASCENDING)], unique=True
        )
        db.couples.create_index("user_id")
        db.chatbot_data.create_index("chat_id")

        # FSub join requests (legacy: keep rqst_fsub_Channel_data too)
        db.fsub_join_requests.create_index(
            [("channel_id", ASCENDING), ("user_id", ASCENDING)], unique=True
        )

        logger.info("✅ [MongoDB] Indexes created")
    except Exception as exc:
        logger.warning(f"[MongoDB] index creation warning: {exc}")

    # Ensure bot_progress singleton exists
    try:
        db.bot_progress.update_one(
            {"id": 1},
            {"$setOnInsert": {
                "id": 1, "target_chat_id": None, "season": 1, "episode": 1,
                "total_episode": 1, "video_count": 0,
                "selected_qualities": "480p,720p,1080p",
                "base_caption": "", "auto_caption_enabled": True,
                "anime_name": "Anime Name",
            }},
            upsert=True,
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None) -> Optional[str]:
    try:
        doc = _db().bot_settings.find_one({"key": key})
        if doc:
            return doc.get("value", default)
    except Exception:
        pass
    return default


def set_setting(key: str, value: str) -> None:
    try:
        _db().bot_settings.update_one(
            {"key": key}, {"$set": {"key": key, "value": value}}, upsert=True
        )
    except Exception as exc:
        logger.error(f"set_setting({key}): {exc}")


def is_maintenance_mode() -> bool:
    return (get_setting("maintenance_mode", "false") or "false").lower() == "true"


def toggle_maintenance_mode() -> bool:
    new = not is_maintenance_mode()
    set_setting("maintenance_mode", "true" if new else "false")
    return new


# ──────────────────────────────────────────────────────────────────────────────
#  USERS
# ──────────────────────────────────────────────────────────────────────────────

def add_user(user_id: int, username: Optional[str],
             first_name: Optional[str], last_name: Optional[str]) -> None:
    clean = (username or "").lstrip("@") or None
    try:
        _db().users.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "username": clean,
                      "first_name": first_name, "last_name": last_name},
             "$setOnInsert": {"joined_date": datetime.utcnow(), "is_banned": False}},
            upsert=True,
        )
    except Exception as exc:
        logger.error(f"add_user: {exc}")


def get_user_count() -> int:
    try:
        return _db().users.count_documents({})
    except Exception:
        return 0


def get_blocked_users_count() -> int:
    try:
        return _db().users.count_documents({"is_banned": True})
    except Exception:
        return 0


def get_all_users(limit=None, offset=0) -> list:
    try:
        cursor = _db().users.find({}).sort("joined_date", DESCENDING).skip(offset)
        if limit:
            cursor = cursor.limit(limit)
        return [
            (d.get("user_id"), d.get("username"), d.get("first_name"),
             d.get("last_name"), d.get("joined_date"), d.get("is_banned", False))
            for d in cursor
        ]
    except Exception:
        return []


def get_user_info_by_id(user_id: int) -> Optional[tuple]:
    try:
        doc = _db().users.find_one({"user_id": user_id})
        if doc:
            return (doc.get("user_id"), doc.get("username"), doc.get("first_name"),
                    doc.get("last_name"), doc.get("joined_date"), doc.get("is_banned", False))
    except Exception:
        pass
    return None


def get_user_id_by_username(username: str) -> Optional[int]:
    clean = username.lstrip("@").lower()
    try:
        doc = _db().users.find_one({"username": {"$regex": f"^{clean}$", "$options": "i"}})
        if doc:
            return doc.get("user_id")
    except Exception:
        pass
    return None


def resolve_target_user_id(target_arg: str) -> Optional[int]:
    if target_arg.startswith("@"):
        return get_user_id_by_username(target_arg)
    try:
        return int(target_arg)
    except ValueError:
        return None


def is_existing_user(user_id: int) -> bool:
    try:
        return _db().users.find_one({"user_id": user_id}) is not None
    except Exception:
        return False


def ban_user(user_id: int) -> None:
    try:
        _db().users.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
    except Exception:
        pass


def unban_user(user_id: int) -> None:
    try:
        _db().users.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
    except Exception:
        pass


def is_user_banned(user_id: int) -> bool:
    try:
        doc = _db().users.find_one({"user_id": user_id})
        if doc:
            return bool(doc.get("is_banned", False))
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────────────────────────────────────
#  FORCE SUB CHANNELS
# ──────────────────────────────────────────────────────────────────────────────

def add_force_sub_channel(channel_username: str, channel_title: str,
                           join_by_request: bool = False,
                           invite_link: str = None,
                           channel_id: int = None) -> bool:
    try:
        doc = {"channel_username": channel_username, "channel_title": channel_title,
               "is_active": True, "join_by_request": join_by_request}
        if invite_link:
            doc["invite_link"] = invite_link
        if channel_id:
            doc["channel_id"] = channel_id
        _db().force_sub_channels.update_one(
            {"channel_username": channel_username},
            {"$set": doc},
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error(f"add_force_sub_channel: {exc}")
        return False


def update_force_sub_invite_link(channel_username: str, invite_link: str) -> bool:
    try:
        _db().force_sub_channels.update_one(
            {"channel_username": channel_username},
            {"$set": {"invite_link": invite_link}},
        )
        return True
    except Exception:
        return False


def record_fsub_join_request(channel_id: int, user_id: int) -> bool:
    try:
        _db().rqst_fsub_Channel_data.update_one(
            {"_id": int(channel_id)},
            {"$addToSet": {"user_ids": int(user_id)}},
            upsert=True,
        )
        # Also keep flat collection for easier queries
        _db().fsub_join_requests.update_one(
            {"channel_id": int(channel_id), "user_id": int(user_id)},
            {"$set": {"channel_id": int(channel_id), "user_id": int(user_id),
                      "channel_username": str(channel_id),
                      "requested_at": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error(f"record_fsub_join_request: {exc}")
        return False


def has_fsub_join_request(channel_id: int, user_id: int) -> bool:
    try:
        found = _db().rqst_fsub_Channel_data.find_one(
            {"_id": int(channel_id), "user_ids": int(user_id)}
        )
        return bool(found)
    except Exception:
        pass
    return False


def remove_fsub_join_request(channel_id: int, user_id: int) -> None:
    try:
        _db().rqst_fsub_Channel_data.update_one(
            {"_id": int(channel_id)},
            {"$pull": {"user_ids": int(user_id)}},
        )
        _db().fsub_join_requests.delete_one(
            {"channel_id": int(channel_id), "user_id": int(user_id)}
        )
    except Exception:
        pass


def clear_fsub_join_request(user_id: int, channel_username: str) -> None:
    """Alias kept for backwards compatibility."""
    try:
        cid = int(channel_username.lstrip("@"))
    except (ValueError, AttributeError):
        return
    remove_fsub_join_request(cid, user_id)


def is_jbr_fsub_channel(channel_id: int) -> bool:
    try:
        doc = _db().force_sub_channels.find_one(
            {"is_active": True, "join_by_request": True,
             "$or": [{"channel_id": int(channel_id)},
                     {"channel_username": str(channel_id)}]}
        )
        return bool(doc)
    except Exception:
        pass
    return False


def get_all_fsub_whitelisted_users(channel_id: int) -> list:
    try:
        doc = _db().rqst_fsub_Channel_data.find_one({"_id": int(channel_id)})
        return list(doc.get("user_ids", [])) if doc else []
    except Exception:
        return []


def get_all_force_sub_channels(return_usernames_only: bool = False) -> list:
    try:
        docs = list(_db().force_sub_channels.find({"is_active": True}))
        if return_usernames_only:
            return [d.get("channel_username") for d in docs]
        return [
            (
                d.get("channel_username", ""),
                d.get("channel_title", ""),
                bool(d.get("join_by_request", False)),
                d.get("invite_link", "") or "",
                d.get("channel_id"),
            )
            for d in docs
        ]
    except Exception:
        return []


def get_force_sub_channel_info(channel_username: str) -> Optional[tuple]:
    try:
        doc = _db().force_sub_channels.find_one(
            {"channel_username": channel_username, "is_active": True}
        )
        if not doc:
            try:
                doc = _db().force_sub_channels.find_one(
                    {"channel_id": int(channel_username), "is_active": True}
                )
            except (ValueError, TypeError):
                pass
        if doc:
            return (doc.get("channel_username"), doc.get("channel_title"),
                    bool(doc.get("join_by_request", False)))
    except Exception:
        pass
    return None


def delete_force_sub_channel(channel_username: str) -> None:
    try:
        _db().force_sub_channels.update_one(
            {"channel_username": channel_username}, {"$set": {"is_active": False}}
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  GENERATED LINKS
# ──────────────────────────────────────────────────────────────────────────────

def generate_link_id(channel_username: str, user_id: int,
                      never_expires: bool = False, channel_title: str = None,
                      source_bot_username: str = None) -> str:
    link_id = secrets.token_urlsafe(16)
    try:
        _db().generated_links.insert_one({
            "link_id": link_id, "channel_username": channel_username,
            "user_id": user_id, "never_expires": never_expires,
            "channel_title": channel_title, "source_bot_username": source_bot_username,
            "created_time": datetime.utcnow(),
        })
    except Exception as exc:
        logger.error(f"generate_link_id: {exc}")
    return link_id


def get_link_info(link_id: str) -> Optional[tuple]:
    try:
        doc = _db().generated_links.find_one({"link_id": link_id})
        if doc:
            return (doc.get("channel_username"), doc.get("user_id"),
                    doc.get("created_time"), doc.get("never_expires", False))
    except Exception:
        pass
    return None


def get_all_links(bot_username: str = None, limit: int = 50, offset: int = 0) -> list:
    try:
        filt = {"source_bot_username": bot_username} if bot_username else {}
        cursor = (
            _db().generated_links.find(filt, {"_id": 0})
            .sort("created_time", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return [
            (d.get("link_id"), d.get("channel_username"), d.get("channel_title"),
             d.get("source_bot_username"), d.get("created_time"), d.get("never_expires", False))
            for d in cursor
        ]
    except Exception:
        return []


def get_links_without_title(bot_username: str = None) -> list:
    try:
        filt: dict = {"$or": [{"channel_title": None}, {"channel_title": ""}]}
        if bot_username:
            filt["source_bot_username"] = bot_username
        cursor = _db().generated_links.find(filt).sort("created_time", DESCENDING)
        return [
            (d.get("link_id"), d.get("channel_username"), d.get("source_bot_username"))
            for d in cursor
        ]
    except Exception:
        return []


def update_link_title(link_id: str, channel_title: str) -> None:
    try:
        _db().generated_links.update_one(
            {"link_id": link_id}, {"$set": {"channel_title": channel_title}}
        )
    except Exception:
        pass


def move_links_to_bot(from_bot_username: str, to_bot_username: str) -> int:
    try:
        res = _db().generated_links.update_many(
            {"source_bot_username": from_bot_username},
            {"$set": {"source_bot_username": to_bot_username}},
        )
        return res.modified_count
    except Exception:
        return 0


def get_links_count(bot_username: str = None) -> int:
    try:
        filt = {"source_bot_username": bot_username} if bot_username else {}
        return _db().generated_links.count_documents(filt)
    except Exception:
        return 0


def cleanup_expired_links() -> None:
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        res = _db().generated_links.delete_many(
            {"created_time": {"$lt": cutoff}, "never_expires": False}
        )
        logger.info(f"[MongoDB] Cleaned {res.deleted_count} expired links")
    except Exception as exc:
        logger.error(f"cleanup_expired_links: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
#  CLONE BOTS
# ──────────────────────────────────────────────────────────────────────────────

def add_clone_bot(bot_token: str, bot_username: str) -> bool:
    try:
        _db().clone_bots.update_one(
            {"bot_token": bot_token},
            {"$set": {"bot_token": bot_token, "bot_username": bot_username, "is_active": True},
             "$setOnInsert": {"added_date": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except Exception:
        return False


def get_all_clone_bots(active_only: bool = False) -> list:
    try:
        filt = {"is_active": True} if active_only else {}
        return [
            (d.get("_id"), d.get("bot_token"), d.get("bot_username"),
             d.get("is_active", True), d.get("added_date"))
            for d in _db().clone_bots.find(filt).sort("added_date", ASCENDING)
        ]
    except Exception:
        return []


def remove_clone_bot(bot_username: str) -> bool:
    uname = bot_username.lstrip("@").lower()
    try:
        _db().clone_bots.update_one(
            {"bot_username": {"$regex": f"^{uname}$", "$options": "i"}},
            {"$set": {"is_active": False}},
        )
        return True
    except Exception:
        return False


def get_main_bot_token() -> str:
    return get_setting("main_bot_token", "") or ""


def set_main_bot_token(token: str) -> None:
    set_setting("main_bot_token", token)


def am_i_a_clone_token(bot_token: str) -> bool:
    try:
        return _db().clone_bots.find_one({"bot_token": bot_token, "is_active": True}) is not None
    except Exception:
        return False


def get_clone_bot_by_username(bot_username: str) -> Optional[tuple]:
    uname = bot_username.lstrip("@").lower()
    try:
        doc = _db().clone_bots.find_one(
            {"bot_username": {"$regex": f"^{uname}$", "$options": "i"}}
        )
        if doc:
            return (doc.get("_id"), doc.get("bot_token"), doc.get("bot_username"),
                    doc.get("is_active", True))
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  CATEGORY SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

_CATEGORY_DEFAULTS = {
    "template_name": "template1",
    "branding": "",
    "buttons": "[]",
    "caption_template": "",
    "thumbnail_url": "",
    "font_style": "normal",
    "logo_file_id": None,
    "logo_position": "bottom",
    "watermark_text": None,
    "watermark_position": "center",
}


def get_category_settings(category: str) -> dict:
    try:
        doc = _db().category_settings.find_one({"category": category})
        if not doc:
            # Insert defaults
            new = {"category": category, **_CATEGORY_DEFAULTS}
            _db().category_settings.update_one(
                {"category": category}, {"$setOnInsert": new}, upsert=True
            )
            doc = new
        raw_buttons = doc.get("buttons", "[]") or "[]"
        return {
            "template_name": doc.get("template_name") or "template1",
            "branding": doc.get("branding") or "",
            "buttons": json.loads(raw_buttons) if isinstance(raw_buttons, str) else raw_buttons,
            "caption_template": doc.get("caption_template") or "",
            "thumbnail_url": doc.get("thumbnail_url") or "",
            "font_style": doc.get("font_style") or "normal",
            "logo_file_id": doc.get("logo_file_id"),
            "logo_position": doc.get("logo_position") or "bottom",
            "watermark_text": doc.get("watermark_text"),
            "watermark_position": doc.get("watermark_position") or "center",
        }
    except Exception as exc:
        logger.error(f"get_category_settings: {exc}")
        return {
            "template_name": "template1", "branding": "", "buttons": [],
            "caption_template": "", "thumbnail_url": "", "font_style": "normal",
            "logo_file_id": None, "logo_position": "bottom",
            "watermark_text": None, "watermark_position": "center",
        }


def update_category_field(category: str, field: str, value: Any) -> bool:
    try:
        _db().category_settings.update_one(
            {"category": category},
            {"$set": {field: value}},
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error(f"update_category_field {field}: {exc}")
        return False


def update_category_template(category: str, template: str) -> None:
    update_category_field(category, "template_name", template)

def update_category_branding(category: str, branding: str) -> None:
    update_category_field(category, "branding", branding)

def update_category_buttons(category: str, buttons_json: str) -> None:
    update_category_field(category, "buttons", buttons_json)

def update_category_caption(category: str, caption: str) -> None:
    update_category_field(category, "caption_template", caption)

def update_category_thumbnail(category: str, thumbnail_url: str) -> None:
    update_category_field(category, "thumbnail_url", thumbnail_url)

def update_category_font(category: str, font_style: str) -> None:
    update_category_field(category, "font_style", font_style)

def update_category_logo(category: str, logo_file_id: str) -> None:
    update_category_field(category, "logo_file_id", logo_file_id)

def update_category_logo_position(category: str, position: str) -> None:
    update_category_field(category, "logo_position", position)


# ──────────────────────────────────────────────────────────────────────────────
#  AUTO-FORWARD
# ──────────────────────────────────────────────────────────────────────────────

def add_auto_forward_connection(source_chat_id, target_chat_id, **kwargs) -> int:
    try:
        new_id = _next_id("auto_forward_connections")
        _db().auto_forward_connections.insert_one({
            "id": new_id,
            "source_chat_id": source_chat_id,
            "source_chat_username": kwargs.get("source_chat_username"),
            "target_chat_id": target_chat_id,
            "active": True,
            "delay_seconds": kwargs.get("delay", 0),
            "protect_content": kwargs.get("protect", False),
            "silent": kwargs.get("silent", False),
            "keep_tag": kwargs.get("keep_tag", False),
            "pin_message": kwargs.get("pin", False),
            "delete_source": kwargs.get("delete_src", False),
            "created_at": datetime.utcnow(),
        })
        return new_id
    except Exception as exc:
        logger.error(f"add_auto_forward_connection: {exc}")
        return 0


def get_auto_forward_connections(active_only=True) -> list:
    try:
        filt = {"active": True} if active_only else {}
        docs = list(_db().auto_forward_connections.find(filt).sort("created_at", DESCENDING))
        # Return as tuples mirroring the original SQL column order
        # id, source_chat_id, source_chat_username, target_chat_id, active,
        # delay_seconds, protect_content, silent, keep_tag, pin_message, delete_source, created_at
        return [
            (d.get("id"), d.get("source_chat_id"), d.get("source_chat_username"),
             d.get("target_chat_id"), d.get("active", True), d.get("delay_seconds", 0),
             d.get("protect_content", False), d.get("silent", False),
             d.get("keep_tag", False), d.get("pin_message", False),
             d.get("delete_source", False), d.get("created_at"))
            for d in docs
        ]
    except Exception:
        return []


def delete_auto_forward_connection(conn_id) -> None:
    try:
        _db().auto_forward_connections.delete_one({"id": conn_id})
        _db().auto_forward_filters.delete_many({"connection_id": conn_id})
        _db().auto_forward_replacements.delete_many({"connection_id": conn_id})
        _db().auto_forward_state.delete_one({"connection_id": conn_id})
    except Exception:
        pass


def toggle_auto_forward_connection(conn_id, active) -> None:
    try:
        _db().auto_forward_connections.update_one(
            {"id": conn_id}, {"$set": {"active": active}}
        )
    except Exception:
        pass


def add_auto_forward_filter(conn_id, allowed_media=None, blacklist=None, whitelist=None) -> None:
    try:
        _db().auto_forward_filters.insert_one({
            "connection_id": conn_id,
            "allowed_media": allowed_media or [],
            "blacklist": blacklist or [],
            "whitelist": whitelist or [],
            "blacklist_words": "",
            "whitelist_words": "",
            "caption_override": "",
            "enable_in_dm": True,
            "enable_in_group": True,
        })
    except Exception:
        pass


def update_auto_forward_filter(conn_id, allowed_media=None, blacklist=None, whitelist=None) -> None:
    try:
        _db().auto_forward_filters.update_one(
            {"connection_id": conn_id},
            {"$set": {"allowed_media": allowed_media or [],
                      "blacklist": blacklist or [],
                      "whitelist": whitelist or []}},
        )
    except Exception:
        pass


def add_auto_forward_replacement(conn_id, old, new) -> None:
    try:
        _db().auto_forward_replacements.insert_one({
            "connection_id": conn_id, "old_pattern": old, "new_pattern": new,
        })
    except Exception:
        pass


def get_auto_forward_replacements(conn_id) -> list:
    try:
        return [
            (d.get("old_pattern"), d.get("new_pattern"))
            for d in _db().auto_forward_replacements.find({"connection_id": conn_id})
        ]
    except Exception:
        return []


def delete_auto_forward_replacement(conn_id, old) -> None:
    try:
        _db().auto_forward_replacements.delete_one({"connection_id": conn_id, "old_pattern": old})
    except Exception:
        pass


def set_auto_forward_last_message(conn_id, msg_id) -> None:
    try:
        _db().auto_forward_state.update_one(
            {"connection_id": conn_id},
            {"$set": {"connection_id": conn_id, "last_message_id": msg_id,
                      "updated_at": datetime.utcnow()}},
            upsert=True,
        )
    except Exception:
        pass


def get_auto_forward_last_message(conn_id) -> int:
    try:
        doc = _db().auto_forward_state.find_one({"connection_id": conn_id})
        return doc.get("last_message_id", 0) if doc else 0
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────────────────────────
#  MANGA AUTO UPDATE
# ──────────────────────────────────────────────────────────────────────────────

def add_manga_auto(title, target_chat_id, watermark=False, combine_pdf=False) -> int:
    try:
        new_id = _next_id("manga_auto_update")
        _db().manga_auto_update.insert_one({
            "id": new_id,
            "manga_title": title,
            "manga_id": None,
            "last_chapter": None,
            "target_chat_id": target_chat_id,
            "watermark": watermark,
            "combine_pdf": combine_pdf,
            "active": True,
            "last_checked": datetime.utcnow(),
            "created_at": datetime.utcnow(),
        })
        return new_id
    except Exception as exc:
        logger.error(f"add_manga_auto: {exc}")
        return 0


def get_manga_auto_list() -> list:
    try:
        return [
            (d.get("id"), d.get("manga_title"), d.get("last_chapter"),
             d.get("target_chat_id"), d.get("active", True))
            for d in _db().manga_auto_update.find({}).sort("id", ASCENDING)
        ]
    except Exception:
        return []


def delete_manga_auto(manga_id) -> None:
    try:
        _db().manga_auto_update.delete_one({"id": manga_id})
    except Exception:
        pass


def toggle_manga_auto(manga_id) -> None:
    try:
        doc = _db().manga_auto_update.find_one({"id": manga_id})
        if doc:
            _db().manga_auto_update.update_one(
                {"id": manga_id}, {"$set": {"active": not doc.get("active", True)}}
            )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  SCHEDULED BROADCASTS
# ──────────────────────────────────────────────────────────────────────────────

def add_scheduled_broadcast(admin_id, message_text, execute_at,
                             media_file_id=None, media_type=None) -> int:
    try:
        new_id = _next_id("scheduled_broadcasts")
        _db().scheduled_broadcasts.insert_one({
            "id": new_id,
            "admin_id": admin_id,
            "message_text": message_text,
            "media_file_id": media_file_id,
            "media_type": media_type,
            "execute_at": execute_at,
            "status": "pending",
            "created_at": datetime.utcnow(),
        })
        return new_id
    except Exception as exc:
        logger.error(f"add_scheduled_broadcast: {exc}")
        return 0


def get_pending_scheduled_broadcasts() -> list:
    try:
        now = datetime.utcnow()
        docs = list(_db().scheduled_broadcasts.find(
            {"status": "pending", "execute_at": {"$lte": now}}
        ))
        return [
            (d.get("id"), d.get("admin_id"), d.get("message_text"),
             d.get("media_file_id"), d.get("media_type"))
            for d in docs
        ]
    except Exception:
        return []


def mark_scheduled_broadcast_sent(b_id) -> None:
    try:
        _db().scheduled_broadcasts.update_one({"id": b_id}, {"$set": {"status": "sent"}})
    except Exception:
        pass


def mark_scheduled_broadcast_failed(b_id) -> None:
    try:
        _db().scheduled_broadcasts.update_one({"id": b_id}, {"$set": {"status": "failed"}})
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  FEATURE FLAGS
# ──────────────────────────────────────────────────────────────────────────────

def set_feature_flag(feature: str, entity_id: int, entity_type: str, enabled: bool) -> None:
    try:
        _db().feature_flags.update_one(
            {"feature_name": feature, "entity_id": entity_id, "entity_type": entity_type},
            {"$set": {"feature_name": feature, "entity_id": entity_id,
                      "entity_type": entity_type, "enabled": enabled}},
            upsert=True,
        )
    except Exception:
        pass


def get_feature_flag(feature: str, entity_id: int, entity_type: str) -> bool:
    try:
        doc = _db().feature_flags.find_one(
            {"feature_name": feature, "entity_id": entity_id, "entity_type": entity_type}
        )
        if doc is not None:
            return bool(doc.get("enabled", True))
    except Exception:
        pass
    if entity_type == "global":
        return True
    return get_feature_flag(feature, 0, "global")


# ──────────────────────────────────────────────────────────────────────────────
#  UPLOAD PROGRESS
# ──────────────────────────────────────────────────────────────────────────────

def load_upload_progress() -> dict:
    try:
        doc = _db().bot_progress.find_one({"id": 1})
        if doc:
            return {
                "target_chat_id": doc.get("target_chat_id"),
                "season": doc.get("season", 1),
                "episode": doc.get("episode", 1),
                "total_episode": doc.get("total_episode", 1),
                "video_count": doc.get("video_count", 0),
                "selected_qualities": doc.get("selected_qualities", "480p,720p,1080p").split(","),
                "base_caption": doc.get("base_caption", ""),
                "auto_caption_enabled": doc.get("auto_caption_enabled", True),
            }
    except Exception:
        pass
    return {
        "target_chat_id": None, "season": 1, "episode": 1, "total_episode": 1,
        "video_count": 0, "selected_qualities": ["480p", "720p", "1080p"],
        "base_caption": "", "auto_caption_enabled": True,
    }


def save_upload_progress(progress: dict) -> None:
    try:
        _db().bot_progress.update_one(
            {"id": 1},
            {"$set": {
                "target_chat_id": progress["target_chat_id"],
                "season": progress["season"],
                "episode": progress["episode"],
                "total_episode": progress["total_episode"],
                "video_count": progress["video_count"],
                "selected_qualities": ",".join(progress["selected_qualities"]),
                "base_caption": progress["base_caption"],
                "auto_caption_enabled": progress["auto_caption_enabled"],
            }},
            upsert=True,
        )
    except Exception as exc:
        logger.error(f"save_upload_progress: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
#  CONNECTED GROUPS
# ──────────────────────────────────────────────────────────────────────────────

def add_connected_group(group_id, group_username, group_title, connected_by) -> None:
    try:
        _db().connected_groups.update_one(
            {"group_id": group_id},
            {"$set": {"group_id": group_id, "group_username": group_username,
                      "group_title": group_title, "connected_by": connected_by,
                      "active": True},
             "$setOnInsert": {"connected_at": datetime.utcnow()}},
            upsert=True,
        )
    except Exception:
        pass


def remove_connected_group(group_id) -> None:
    try:
        _db().connected_groups.update_one(
            {"group_id": group_id}, {"$set": {"active": False}}
        )
    except Exception:
        pass


def get_connected_groups(active_only=True) -> list:
    try:
        filt = {"active": True} if active_only else {}
        return [
            (d.get("group_id"), d.get("group_username"), d.get("group_title"),
             d.get("connected_at"))
            for d in _db().connected_groups.find(filt)
        ]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
#  BROADCAST HISTORY
# ──────────────────────────────────────────────────────────────────────────────

def add_broadcast_history(admin_id, mode, total_users, message_text) -> int:
    try:
        new_id = _next_id("broadcast_history")
        _db().broadcast_history.insert_one({
            "id": new_id,
            "admin_id": admin_id,
            "mode": mode,
            "total_users": total_users,
            "success": 0,
            "blocked": 0,
            "deleted": 0,
            "failed": 0,
            "message_text": message_text,
            "started_at": datetime.utcnow(),
            "completed_at": None,
        })
        return new_id
    except Exception as exc:
        logger.error(f"add_broadcast_history: {exc}")
        return 0


def update_broadcast_history(b_id, success, blocked, deleted, failed) -> None:
    try:
        _db().broadcast_history.update_one(
            {"id": b_id},
            {"$set": {"success": success, "blocked": blocked, "deleted": deleted,
                      "failed": failed, "completed_at": datetime.utcnow()}},
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  POSTS CACHE
# ──────────────────────────────────────────────────────────────────────────────

def cache_post(category, title, anilist_id, media_data) -> None:
    try:
        _db().posts_cache.insert_one({
            "category": category,
            "title": title,
            "anilist_id": anilist_id,
            "media_data": media_data,
            "created_at": datetime.utcnow(),
        })
    except Exception as exc:
        logger.error(f"cache_post failed: {exc}")


def get_cached_post(anilist_id) -> Optional[dict]:
    try:
        doc = _db().posts_cache.find_one(
            {"anilist_id": anilist_id},
            sort=[("created_at", DESCENDING)]
        )
        if doc:
            return {"category": doc.get("category"), "title": doc.get("title"),
                    "media_data": doc.get("media_data")}
    except Exception:
        pass
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  POSTER PREMIUM  (primary: MongoDB)
# ──────────────────────────────────────────────────────────────────────────────

POSTER_TASK_LIMITS = {
    "gold": 50, "silver": 40, "bronze": 30, "default": 20,
}


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def add_poster_premium(user_id: int, rank: str,
                        expiry_time: Optional[datetime] = None) -> bool:
    try:
        _db().poster_premium.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "rank": rank, "expiry_time": expiry_time,
                      "added_at": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except Exception as exc:
        logger.error(f"add_poster_premium: {exc}")
        return False


def get_poster_premium(user_id: int) -> Optional[dict]:
    try:
        doc = _db().poster_premium.find_one({"user_id": user_id})
        if doc:
            expiry = doc.get("expiry_time")
            if expiry and expiry < datetime.utcnow():
                _db().poster_premium.delete_one({"user_id": user_id})
                return None
            return doc
    except Exception:
        pass
    return None


def remove_poster_premium(user_id: int) -> bool:
    try:
        _db().poster_premium.delete_one({"user_id": user_id})
        return True
    except Exception:
        return False


def get_all_poster_premium() -> list:
    try:
        now = datetime.utcnow()
        return list(_db().poster_premium.find(
            {"$or": [{"expiry_time": None}, {"expiry_time": {"$gt": now}}]},
            {"_id": 0}
        ))
    except Exception:
        return []


def is_poster_premium(user_id: int) -> bool:
    return get_poster_premium(user_id) is not None


def get_poster_rank(user_id: int) -> str:
    doc = get_poster_premium(user_id)
    return doc.get("rank", "default") if doc else "default"


def check_and_update_poster_usage(user_id: int, limit: int) -> bool:
    """Returns True if within limit, updates counter."""
    today = _today()
    try:
        res = _db().poster_usage.find_one_and_update(
            {"user_id": user_id, "date": today},
            {"$inc": {"count": 1}},
            upsert=True,
            return_document=True,
        )
        count = res.get("count", 1) if res else 1
        if count > limit:
            _db().poster_usage.update_one(
                {"user_id": user_id, "date": today}, {"$inc": {"count": -1}}
            )
            return False
        return True
    except Exception:
        return True


def get_poster_usage_today(user_id: int) -> int:
    today = _today()
    try:
        doc = _db().poster_usage.find_one({"user_id": user_id, "date": today})
        return doc.get("count", 0) if doc else 0
    except Exception:
        return 0


# ──────────────────────────────────────────────────────────────────────────────
#  COUPLES  (primary: MongoDB)
# ──────────────────────────────────────────────────────────────────────────────

def get_couple(user_id: int) -> Optional[dict]:
    try:
        return _db().couples.find_one({"user_id": user_id}, {"_id": 0})
    except Exception:
        return None


def set_couple(user_id: int, partner_id: int, chat_id: int) -> None:
    try:
        _db().couples.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "partner_id": partner_id,
                      "chat_id": chat_id, "since": datetime.utcnow()}},
            upsert=True,
        )
    except Exception:
        pass


def remove_couple(user_id: int) -> None:
    try:
        _db().couples.delete_many(
            {"$or": [{"user_id": user_id}, {"partner_id": user_id}]}
        )
    except Exception:
        pass


def get_couple_of_day(chat_id: int) -> Optional[tuple]:
    try:
        today = _today()
        doc = _db().couple_of_day.find_one({"chat_id": chat_id, "date": today})
        if doc:
            return (doc.get("user1_id"), doc.get("user2_id"))
    except Exception:
        pass
    return None


def set_couple_of_day(chat_id: int, user1: int, user2: int) -> None:
    try:
        today = _today()
        _db().couple_of_day.update_one(
            {"chat_id": chat_id, "date": today},
            {"$set": {"chat_id": chat_id, "date": today,
                      "user1_id": user1, "user2_id": user2}},
            upsert=True,
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  CHATBOT  (primary: MongoDB)
# ──────────────────────────────────────────────────────────────────────────────

def is_chatbot_enabled(chat_id: int) -> bool:
    try:
        doc = _db().chatbot_data.find_one({"chat_id": chat_id})
        return bool(doc and doc.get("enabled", False))
    except Exception:
        return False


def set_chatbot_enabled(chat_id: int, enabled: bool) -> None:
    try:
        _db().chatbot_data.update_one(
            {"chat_id": chat_id},
            {"$set": {"chat_id": chat_id, "enabled": enabled}},
            upsert=True,
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  ANIME CHANNEL LINKS
# ──────────────────────────────────────────────────────────────────────────────

def add_anime_channel_link(anime_title: str, channel_id: int,
                            channel_title: str = "", link_id: str = "",
                            added_by: int = 0) -> bool:
    try:
        key = anime_title.strip().lower()
        _db().anime_channel_links.update_one(
            {"anime_title": key, "channel_id": channel_id},
            {"$set": {"anime_title": key, "channel_id": channel_id,
                      "channel_title": channel_title, "link_id": link_id,
                      "added_by": added_by},
             "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )
        return True
    except Exception:
        return False


def get_anime_channel_links(anime_title: str) -> list:
    try:
        key = anime_title.strip().lower()
        docs = list(_db().anime_channel_links.find(
            {"anime_title": key}
        ).sort("created_at", DESCENDING))
        return [(d.get("channel_id"), d.get("channel_title"), d.get("link_id")) for d in docs]
    except Exception:
        return []


def get_all_anime_channel_links() -> list:
    try:
        docs = list(_db().anime_channel_links.find({}).sort("anime_title", ASCENDING))
        return [
            (d.get("_id"), d.get("anime_title"), d.get("channel_id"),
             d.get("channel_title"), d.get("link_id"), d.get("created_at"))
            for d in docs
        ]
    except Exception:
        return []


def remove_anime_channel_link(anime_title: str, channel_id: int) -> None:
    try:
        _db().anime_channel_links.delete_one(
            {"anime_title": anime_title.strip().lower(), "channel_id": channel_id}
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  FILTER POSTER CACHE
# ──────────────────────────────────────────────────────────────────────────────

def get_filter_poster_cache(cache_key: str) -> Optional[dict]:
    try:
        doc = _db().filter_poster_cache.find_one({"cache_key": cache_key})
        if doc:
            return {
                "file_id": doc.get("file_id"),
                "channel_id": doc.get("channel_id"),
                "channel_msg_id": doc.get("channel_msg_id"),
                "caption": doc.get("caption"),
                "template": doc.get("template"),
                "anime_title": doc.get("anime_title"),
            }
    except Exception:
        pass
    return None


def save_filter_poster_cache(cache_key: str, anime_title: str, template: str,
                               file_id: str, channel_id: int = 0,
                               channel_msg_id: int = 0, caption: str = "") -> None:
    try:
        _db().filter_poster_cache.update_one(
            {"cache_key": cache_key},
            {"$set": {
                "cache_key": cache_key,
                "anime_title": anime_title.lower(),
                "template": template,
                "file_id": file_id,
                "channel_id": channel_id,
                "channel_msg_id": channel_msg_id,
                "caption": caption,
                "created_at": datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
#  CHANNEL WELCOME SYSTEM
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_channel_welcome_table() -> None:
    """No-op in MongoDB — collections are created automatically."""
    pass


def get_channel_welcome(channel_id: int) -> Optional[dict]:
    try:
        doc = _db().channel_welcome_settings.find_one({"channel_id": channel_id})
        if doc:
            return {
                "enabled": bool(doc.get("enabled", True)),
                "welcome_text": doc.get("welcome_text", ""),
                "image_file_id": doc.get("image_file_id", ""),
                "image_url": doc.get("image_url", ""),
                "buttons": json.loads(doc.get("buttons_json", "[]"))
                           if isinstance(doc.get("buttons_json"), str) else doc.get("buttons", []),
            }
    except Exception:
        pass
    return None


def set_channel_welcome(channel_id: int, **kwargs) -> None:
    existing = get_channel_welcome(channel_id) or {}
    try:
        _db().channel_welcome_settings.update_one(
            {"channel_id": channel_id},
            {"$set": {
                "channel_id": channel_id,
                "enabled": kwargs.get("enabled", existing.get("enabled", True)),
                "welcome_text": kwargs.get("welcome_text", existing.get("welcome_text", "")),
                "image_file_id": kwargs.get("image_file_id", existing.get("image_file_id", "")),
                "image_url": kwargs.get("image_url", existing.get("image_url", "")),
                "buttons_json": json.dumps(kwargs.get("buttons", existing.get("buttons", []))),
                "updated_at": datetime.utcnow(),
            }},
            upsert=True,
        )
    except Exception:
        pass


def delete_channel_welcome(channel_id: int) -> None:
    try:
        _db().channel_welcome_settings.delete_one({"channel_id": channel_id})
    except Exception:
        pass


def get_all_channel_welcomes() -> list:
    try:
        return [
            (d.get("channel_id"), d.get("enabled"), d.get("welcome_text"))
            for d in _db().channel_welcome_settings.find({}).sort("channel_id", ASCENDING)
        ]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
#  DB MANAGER COMPAT (some modules import db_manager directly)
# ──────────────────────────────────────────────────────────────────────────────

class _DBManagerCompat:
    """Compatibility shim. PostgreSQL cursor API is stubbed — not used by MongoDB path."""

    @contextmanager
    def get_connection(self):
        yield None

    @contextmanager
    def get_cursor(self):
        yield None

    def close_all(self):
        pass


db_manager = _DBManagerCompat()


def extract_anime_name_from_title(channel_title: str) -> str:
    """
    Extract clean anime name from a channel title.
    Examples:
      "Demon Slayer Hindi Dubbed"  → "Demon Slayer"
      "Naruto Shippuden in Hindi"  → "Naruto Shippuden"
      "One Piece - Hindi Dub"      → "One Piece"
      "JJK Season 2 Hindi"         → "JJK Season 2"
      "Anime Channel"              → "Anime Channel" (unchanged)
    """
    if not channel_title:
        return ""
    t = channel_title.strip()
    _STRIP = [
        r"\s*[\-|:–—].*$",
        r"\s+in\s+(hindi|english|tamil|telugu|urdu|japanese|korean|chinese)\s*$",
        r"\s+(hindi|english|tamil|telugu|urdu|japanese|korean|chinese)\s+(dubbed|dub|sub|subbed|audio|version)\s*$",
        r"\s+(dubbed|dub|subbed|sub|esub|multi.?audio|multi.?sub)\s*$",
        r"\s+(official|hd|fhd|4k|720p|1080p)\s*$",
        r"\s+channel\s*$",
        r"\s+anime\s*$",
    ]
    for pat in _STRIP:
        t = _re.sub(pat, "", t, flags=_re.IGNORECASE).strip()
    return t if len(t) >= 3 else channel_title.strip()


# ──────────────────────────────────────────────────────────────────────────────
#  SEARCH ANALYTICS — /top command support
# ──────────────────────────────────────────────────────────────────────────────

def ensure_search_analytics_table() -> None:
    """No-op in MongoDB — collection is auto-created."""
    pass


def record_search_analytics(user_id: int, anime_title: str) -> None:
    if not user_id or not anime_title:
        return
    try:
        key = anime_title.strip().lower()
        two_weeks_ago = datetime.utcnow() - timedelta(weeks=2)
        doc = _db().search_analytics.find_one({"anime_title": key, "user_id": user_id})
        if doc and doc.get("last_searched") and doc["last_searched"] >= two_weeks_ago:
            return  # Already counted within 2 weeks
        _db().search_analytics.update_one(
            {"anime_title": key, "user_id": user_id},
            {"$set": {"anime_title": key, "user_id": user_id,
                      "last_searched": datetime.utcnow()}},
            upsert=True,
        )
    except Exception:
        pass


def get_top_search_analytics(limit: int = 10) -> list:
    try:
        pipeline = [
            {"$group": {"_id": "$anime_title", "cnt": {"$sum": 1}}},
            {"$sort": {"cnt": DESCENDING}},
            {"$limit": limit},
        ]
        results = list(_db().search_analytics.aggregate(pipeline))
        return [(r["_id"], r["cnt"]) for r in results]
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────────────────
#  PERSISTENT MESSAGE DELETE QUEUE
# ──────────────────────────────────────────────────────────────────────────────

def ensure_pending_deletes_table() -> None:
    """No-op in MongoDB."""
    pass


def save_pending_delete(chat_id: int, message_id: int, delay_seconds: int) -> None:
    try:
        delete_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        _db().pending_message_deletes.insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "delete_at": delete_at,
        })
    except Exception:
        pass


def remove_pending_delete(chat_id: int, message_id: int) -> None:
    try:
        _db().pending_message_deletes.delete_one(
            {"chat_id": chat_id, "message_id": message_id}
        )
    except Exception:
        pass


def pop_due_pending_deletes() -> list:
    """Atomically fetch-and-delete all rows whose delete_at <= now."""
    try:
        now = datetime.utcnow()
        docs = list(_db().pending_message_deletes.find({"delete_at": {"$lte": now}}))
        if docs:
            ids = [d["_id"] for d in docs]
            _db().pending_message_deletes.delete_many({"_id": {"$in": ids}})
        return [(int(d["chat_id"]), int(d["message_id"])) for d in docs]
    except Exception:
        return []
