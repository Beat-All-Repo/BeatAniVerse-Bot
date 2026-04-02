# ==============================================================================
# PLACE AT: /app/database_dual.py
# ACTION: Replace existing file
# ==============================================================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeatAniVerse Bot — Dual Database Layer
========================================
Exports EXACTLY the same API as database_safe.py (NeonDB/PostgreSQL),
but also initialises MongoDB when MONGO_DB_URI is set.

Priority logic:
  • PostgreSQL (NeonDB) is used for ALL SQL-based operations when DATABASE_URL is set.
  • MongoDB is used for:
      – poster premium plans  (poster_premium collection)
      – couple data           (couples collection)
      – chatbot data          (chatbot collection)
      – any function that explicitly prefers Mongo
  • If only MongoDB is set (no DATABASE_URL), SQL functions return safe empty/defaults.
  • Both can be active simultaneously — they are never in conflict.

Credits: BeatAnime | @BeatAnime | @Beat_Anime_Discussion
"""

import logging
import json
import secrets
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
#  PostgreSQL / NeonDB layer (original database_safe code, intact)
# ──────────────────────────────────────────────────────────────────────────────

try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False

# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB layer
# ──────────────────────────────────────────────────────────────────────────────

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from pymongo.errors import PyMongoError
    PYMONGO_OK = True
except ImportError:
    PYMONGO_OK = False

# ──────────────────────────────────────────────────────────────────────────────
#  Global handles
# ──────────────────────────────────────────────────────────────────────────────

class _PG:
    pool: Optional[Any] = None

class _MG:
    db: Optional[Any] = None

# ──────────────────────────────────────────────────────────────────────────────
#  INIT
# ──────────────────────────────────────────────────────────────────────────────

def init_db(database_url: str = "", mongo_uri: str = "") -> None:
    """Initialise both databases. At least one must be supplied."""
    if database_url and PSYCOPG2_OK:
        _init_pg(database_url)
    elif database_url:
        logger.error("psycopg2 not installed – skipping PostgreSQL init")

    if mongo_uri and PYMONGO_OK:
        _init_mongo(mongo_uri)
    elif mongo_uri:
        logger.error("pymongo not installed – skipping MongoDB init")

    if _PG.pool is None and _MG.db is None:
        raise RuntimeError(
            "FATAL: No database could be initialised. "
            "Check DATABASE_URL / MONGO_DB_URI and installed packages."
        )


def _init_pg(url: str) -> None:
    import time as _t
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    for attempt in range(5):
        try:
            _PG.pool = pg_pool.SimpleConnectionPool(
                1, 5, url,
                sslmode="require",
                connect_timeout=10,
                keepalives=1, keepalives_idle=30,
                keepalives_interval=10, keepalives_count=5,
            )
            _migrate_pg()
            logger.info("✅ [NeonDB] PostgreSQL connected and migrated")
            return
        except Exception as exc:
            if attempt < 4:
                logger.warning(f"[NeonDB] attempt {attempt+1}/5 failed: {exc}. Retrying…")
                _t.sleep(3)
            else:
                logger.error(f"[NeonDB] all attempts failed: {exc}")


def _init_mongo(uri: str) -> None:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.server_info()          # force connection
        # NOTE: MongoDB Database objects raise on bool() — use explicit None check
        try:
            _default = client.get_default_database()
        except Exception:
            _default = None
        _MG.db = _default if _default is not None else client["beataniversebot"]
        _migrate_mongo()
        logger.info("✅ [MongoDB] Connected and indexed")
    except Exception as exc:
        logger.error(f"[MongoDB] init failed: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
#  PostgreSQL helpers
# ──────────────────────────────────────────────────────────────────────────────

@contextmanager
def _pg():
    """Yield a psycopg2 connection from the pool, or yield None if unavailable."""
    if not _PG.pool:
        yield None
        return
    conn = None
    try:
        conn = _PG.pool.getconn()
        yield conn
        conn.commit()
    except Exception as exc:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        logger.error(f"[PG] error: {exc}")
        raise
    finally:
        if conn and _PG.pool:
            _PG.pool.putconn(conn)


def _pg_exec(sql: str, params=()) -> Optional[Any]:
    """Execute SQL, return cursor.fetchone() or None."""
    with _pg() as conn:
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(sql, params)
        try:
            row = cur.fetchone()
            # Guard: return None if empty tuple (some drivers return () instead of None)
            return row if row else None
        except Exception:
            return None


def _pg_exec_many(sql: str, params=()) -> Optional[list]:
    with _pg() as conn:
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(sql, params)
        try:
            return cur.fetchall()
        except Exception:
            return []


def _pg_run(sql: str, params=()) -> bool:
    """Execute SQL with no return value. Returns True on success."""
    with _pg() as conn:
        if conn is None:
            return False
        cur = conn.cursor()
        cur.execute(sql, params)
        return True


# ──────────────────────────────────────────────────────────────────────────────
#  PostgreSQL migration — creates all required tables
# ──────────────────────────────────────────────────────────────────────────────

def _migrate_pg() -> None:
    with _pg() as conn:
        if conn is None:
            return
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP DEFAULT NOW(),
                is_banned BOOLEAN DEFAULT FALSE
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS force_sub_channels (
                channel_username TEXT PRIMARY KEY,
                channel_title TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                join_by_request BOOLEAN DEFAULT FALSE
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS generated_links (
                link_id TEXT PRIMARY KEY,
                channel_username TEXT NOT NULL,
                user_id BIGINT,
                created_time TIMESTAMP DEFAULT NOW(),
                never_expires BOOLEAN DEFAULT TRUE,
                channel_title TEXT,
                source_bot_username TEXT
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clone_bots (
                id SERIAL PRIMARY KEY,
                bot_token TEXT UNIQUE NOT NULL,
                bot_username TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                added_date TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS category_settings (
                category TEXT PRIMARY KEY,
                template_name TEXT,
                branding TEXT,
                buttons TEXT,
                caption_template TEXT,
                thumbnail_url TEXT,
                font_style TEXT DEFAULT 'normal',
                logo_file_id TEXT,
                logo_position TEXT DEFAULT 'bottom',
                watermark_text TEXT,
                watermark_position TEXT DEFAULT 'center'
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS auto_forward_connections (
                id SERIAL PRIMARY KEY,
                source_chat_id BIGINT NOT NULL,
                source_chat_username TEXT,
                target_chat_id BIGINT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                delay_seconds INT DEFAULT 0,
                protect_content BOOLEAN DEFAULT FALSE,
                silent BOOLEAN DEFAULT FALSE,
                keep_tag BOOLEAN DEFAULT FALSE,
                pin_message BOOLEAN DEFAULT FALSE,
                delete_source BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS auto_forward_filters (
                id SERIAL PRIMARY KEY,
                connection_id INT REFERENCES auto_forward_connections(id) ON DELETE CASCADE,
                allowed_media TEXT[] DEFAULT '{}',
                blacklist TEXT[] DEFAULT '{}',
                whitelist TEXT[] DEFAULT '{}',
                blacklist_words TEXT DEFAULT '',
                whitelist_words TEXT DEFAULT '',
                caption_override TEXT DEFAULT '',
                enable_in_dm BOOLEAN DEFAULT TRUE,
                enable_in_group BOOLEAN DEFAULT TRUE
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS auto_forward_replacements (
                id SERIAL PRIMARY KEY,
                connection_id INT REFERENCES auto_forward_connections(id) ON DELETE CASCADE,
                old_pattern TEXT NOT NULL,
                new_pattern TEXT NOT NULL
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS auto_forward_state (
                connection_id INT PRIMARY KEY REFERENCES auto_forward_connections(id) ON DELETE CASCADE,
                last_message_id BIGINT,
                updated_at TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS manga_auto_update (
                id SERIAL PRIMARY KEY,
                manga_title TEXT NOT NULL,
                manga_id TEXT,
                last_chapter TEXT,
                target_chat_id BIGINT,
                watermark BOOLEAN DEFAULT FALSE,
                combine_pdf BOOLEAN DEFAULT FALSE,
                active BOOLEAN DEFAULT TRUE,
                last_checked TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                message_text TEXT,
                media_file_id TEXT,
                media_type TEXT,
                execute_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS broadcast_history (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                mode TEXT,
                total_users INT,
                success INT DEFAULT 0,
                blocked INT DEFAULT 0,
                deleted INT DEFAULT 0,
                failed INT DEFAULT 0,
                message_text TEXT,
                started_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS feature_flags (
                feature_name TEXT,
                entity_id BIGINT,
                entity_type TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                PRIMARY KEY (feature_name, entity_id, entity_type)
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_progress (
                id INTEGER PRIMARY KEY,
                target_chat_id BIGINT,
                season INTEGER DEFAULT 1,
                episode INTEGER DEFAULT 1,
                total_episode INTEGER DEFAULT 1,
                video_count INTEGER DEFAULT 0,
                selected_qualities TEXT DEFAULT '480p,720p,1080p',
                base_caption TEXT,
                auto_caption_enabled BOOLEAN DEFAULT TRUE
            )""")
        cur.execute("INSERT INTO bot_progress (id, base_caption) VALUES (1, '') ON CONFLICT (id) DO NOTHING")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS connected_groups (
                group_id BIGINT PRIMARY KEY,
                group_username TEXT,
                group_title TEXT,
                connected_by BIGINT,
                connected_at TIMESTAMP DEFAULT NOW(),
                active BOOLEAN DEFAULT TRUE
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS posts_cache (
                id SERIAL PRIMARY KEY,
                category TEXT,
                title TEXT,
                anilist_id INT,
                media_data JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS anime_channel_links (
                id SERIAL PRIMARY KEY,
                anime_title TEXT NOT NULL,
                channel_id BIGINT NOT NULL,
                channel_title TEXT,
                link_id TEXT,
                added_by BIGINT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(anime_title, channel_id)
            )""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS filter_poster_cache (
                id SERIAL PRIMARY KEY,
                cache_key TEXT UNIQUE NOT NULL,
                anime_title TEXT NOT NULL,
                template TEXT DEFAULT 'ani',
                file_id TEXT NOT NULL,
                channel_id BIGINT DEFAULT 0,
                channel_msg_id BIGINT DEFAULT 0,
                caption TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW()
            )""")

        # Idempotent column adds
        for ddl in [
            "DO $$ BEGIN ALTER TABLE generated_links ADD COLUMN channel_title TEXT; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE generated_links ADD COLUMN source_bot_username TEXT; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE force_sub_channels ADD COLUMN join_by_request BOOLEAN DEFAULT FALSE; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE bot_progress ADD COLUMN anime_name TEXT DEFAULT 'Anime Name'; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN blacklist_words TEXT DEFAULT ''; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN whitelist_words TEXT DEFAULT ''; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN caption_override TEXT DEFAULT ''; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN enable_in_dm BOOLEAN DEFAULT TRUE; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN enable_in_group BOOLEAN DEFAULT TRUE; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
            "DO $$ BEGIN ALTER TABLE auto_forward_filters ADD COLUMN allowed_media TEXT[] DEFAULT '{}'; EXCEPTION WHEN duplicate_column THEN NULL; END $$;",
        ]:
            try:
                cur.execute(ddl)
            except Exception:
                pass

    logger.info("✅ [NeonDB] Migration complete")


# ──────────────────────────────────────────────────────────────────────────────
#  MongoDB migration — create indexes
# ──────────────────────────────────────────────────────────────────────────────

def _migrate_mongo() -> None:
    db = _MG.db
    if db is None:
        return
    try:
        db.poster_premium.create_index("user_id", unique=True)
        db.poster_usage.create_index([("user_id", ASCENDING), ("date", ASCENDING)], unique=True)
        db.couples.create_index("user_id")
        db.chatbot_data.create_index("chat_id")
        db.mongo_users.create_index("user_id", unique=True)
        logger.info("✅ [MongoDB] Indexes created")
    except Exception as exc:
        logger.warning(f"[MongoDB] index creation: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
#  SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None) -> Optional[str]:
    row = _pg_exec("SELECT value FROM bot_settings WHERE key = %s", (key,))
    if row:
        return row[0]
    # Mongo fallback
    if _MG.db is not None:
        try:
            doc = _MG.db.bot_settings.find_one({"key": key})
            if doc:
                return doc.get("value", default)
        except Exception:
            pass
    return default


def set_setting(key: str, value: str) -> None:
    ok = _pg_run("""
        INSERT INTO bot_settings (key, value) VALUES (%s, %s)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, value))
    if _MG.db is not None:
        try:
            _MG.db.bot_settings.update_one(
                {"key": key}, {"$set": {"key": key, "value": value}}, upsert=True
            )
        except Exception:
            pass


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
    _pg_run("""
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
            SET username   = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name  = EXCLUDED.last_name
    """, (user_id, clean, first_name, last_name))
    if _MG.db is not None:
        try:
            _MG.db.mongo_users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "username": clean,
                          "first_name": first_name, "last_name": last_name}},
                upsert=True,
            )
        except Exception:
            pass


def get_user_count() -> int:
    row = _pg_exec("SELECT COUNT(*) FROM users")
    if row:
        return row[0]
    if _MG.db is not None:
        try:
            return _MG.db.mongo_users.count_documents({})
        except Exception:
            pass
    return 0


def get_blocked_users_count() -> int:
    row = _pg_exec("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
    return row[0] if row else 0


def get_all_users(limit=None, offset=0) -> list:
    if limit is None:
        rows = _pg_exec_many("""
            SELECT user_id, username, first_name, last_name, joined_date, is_banned
            FROM users ORDER BY joined_date DESC
        """)
    else:
        rows = _pg_exec_many("""
            SELECT user_id, username, first_name, last_name, joined_date, is_banned
            FROM users ORDER BY joined_date DESC LIMIT %s OFFSET %s
        """, (limit, offset))
    if rows is not None:
        return rows
    # Mongo fallback
    if _MG.db is not None:
        try:
            cursor = _MG.db.mongo_users.find({}, {"_id": 0}).skip(offset)
            if limit:
                cursor = cursor.limit(limit)
            return [
                (d.get("user_id"), d.get("username"), d.get("first_name"),
                 d.get("last_name"), d.get("joined_date"), d.get("is_banned", False))
                for d in cursor
            ]
        except Exception:
            pass
    return []


def get_user_info_by_id(user_id: int) -> Optional[tuple]:
    row = _pg_exec("""
        SELECT user_id, username, first_name, last_name, joined_date, is_banned
        FROM users WHERE user_id = %s
    """, (user_id,))
    if row:
        return row
    if _MG.db is not None:
        try:
            doc = _MG.db.mongo_users.find_one({"user_id": user_id})
            if doc:
                return (doc.get("user_id"), doc.get("username"), doc.get("first_name"),
                        doc.get("last_name"), doc.get("joined_date"), doc.get("is_banned", False))
        except Exception:
            pass
    return None


def get_user_id_by_username(username: str) -> Optional[int]:
    clean = username.lstrip("@").lower()
    row = _pg_exec("SELECT user_id FROM users WHERE LOWER(username) = %s", (clean,))
    if row:
        return row[0]
    if _MG.db is not None:
        try:
            doc = _MG.db.mongo_users.find_one({"username": {"$regex": f"^{clean}$", "$options": "i"}})
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
    row = _pg_exec("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
    if row:
        return True
    if _MG.db is not None:
        try:
            return _MG.db.mongo_users.find_one({"user_id": user_id}) is not None
        except Exception:
            pass
    return False


def ban_user(user_id: int) -> None:
    _pg_run("UPDATE users SET is_banned = TRUE WHERE user_id = %s", (user_id,))
    if _MG.db is not None:
        try:
            _MG.db.mongo_users.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
        except Exception:
            pass


def unban_user(user_id: int) -> None:
    _pg_run("UPDATE users SET is_banned = FALSE WHERE user_id = %s", (user_id,))
    if _MG.db is not None:
        try:
            _MG.db.mongo_users.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
        except Exception:
            pass


def is_user_banned(user_id: int) -> bool:
    row = _pg_exec("SELECT is_banned FROM users WHERE user_id = %s", (user_id,))
    if row:
        return bool(row[0])
    if _MG.db is not None:
        try:
            doc = _MG.db.mongo_users.find_one({"user_id": user_id})
            if doc:
                return bool(doc.get("is_banned", False))
        except Exception:
            pass
    return False


# ──────────────────────────────────────────────────────────────────────────────
#  FORCE SUB CHANNELS
# ──────────────────────────────────────────────────────────────────────────────

def add_force_sub_channel(channel_username: str, channel_title: str,
                           join_by_request: bool = False) -> bool:
    ok = _pg_run("""
        INSERT INTO force_sub_channels (channel_username, channel_title, is_active, join_by_request)
        VALUES (%s, %s, TRUE, %s)
        ON CONFLICT (channel_username) DO UPDATE
            SET channel_title = EXCLUDED.channel_title,
                is_active = TRUE,
                join_by_request = EXCLUDED.join_by_request
    """, (channel_username, channel_title, join_by_request))
    if _MG.db is not None:
        try:
            _MG.db.force_sub_channels.update_one(
                {"channel_username": channel_username},
                {"$set": {"channel_username": channel_username, "channel_title": channel_title,
                          "is_active": True, "join_by_request": join_by_request}},
                upsert=True,
            )
        except Exception:
            pass
    return ok


def get_all_force_sub_channels(return_usernames_only: bool = False) -> list:
    if return_usernames_only:
        rows = _pg_exec_many(
            "SELECT channel_username FROM force_sub_channels WHERE is_active = TRUE ORDER BY channel_title"
        )
        if rows is not None:
            return [r[0] for r in rows]
    else:
        rows = _pg_exec_many("""
            SELECT channel_username, channel_title, COALESCE(join_by_request, FALSE)
            FROM force_sub_channels WHERE is_active = TRUE ORDER BY channel_title
        """)
        if rows is not None:
            return rows

    # Mongo fallback
    if _MG.db is not None:
        try:
            docs = list(_MG.db.force_sub_channels.find({"is_active": True}))
            if return_usernames_only:
                return [d.get("channel_username") for d in docs]
            return [(d.get("channel_username"), d.get("channel_title"),
                     d.get("join_by_request", False)) for d in docs]
        except Exception:
            pass
    return []


def get_force_sub_channel_info(channel_username: str) -> Optional[tuple]:
    row = _pg_exec("""
        SELECT channel_username, channel_title, COALESCE(join_by_request, FALSE)
        FROM force_sub_channels WHERE channel_username = %s AND is_active = TRUE
    """, (channel_username,))
    if row:
        return row
    if _MG.db is not None:
        try:
            doc = _MG.db.force_sub_channels.find_one(
                {"channel_username": channel_username, "is_active": True}
            )
            if doc:
                return (doc.get("channel_username"), doc.get("channel_title"),
                        doc.get("join_by_request", False))
        except Exception:
            pass
    return None


def delete_force_sub_channel(channel_username: str) -> None:
    _pg_run(
        "UPDATE force_sub_channels SET is_active = FALSE WHERE channel_username = %s",
        (channel_username,)
    )
    if _MG.db is not None:
        try:
            _MG.db.force_sub_channels.update_one(
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
    _pg_run("""
        INSERT INTO generated_links
            (link_id, channel_username, user_id, never_expires, channel_title, source_bot_username)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (link_id) DO UPDATE SET channel_username = EXCLUDED.channel_username
    """, (link_id, channel_username, user_id, never_expires, channel_title, source_bot_username))
    if _MG.db is not None:
        try:
            _MG.db.generated_links.insert_one({
                "link_id": link_id, "channel_username": channel_username,
                "user_id": user_id, "never_expires": never_expires,
                "channel_title": channel_title, "source_bot_username": source_bot_username,
                "created_time": datetime.utcnow(),
            })
        except Exception:
            pass
    return link_id


def get_link_info(link_id: str) -> Optional[tuple]:
    row = _pg_exec("""
        SELECT channel_username, user_id, created_time, never_expires
        FROM generated_links WHERE link_id = %s
    """, (link_id,))
    if row:
        return row
    if _MG.db is not None:
        try:
            doc = _MG.db.generated_links.find_one({"link_id": link_id})
            if doc:
                return (doc.get("channel_username"), doc.get("user_id"),
                        doc.get("created_time"), doc.get("never_expires", False))
        except Exception:
            pass
    return None


def get_all_links(bot_username: str = None, limit: int = 50, offset: int = 0) -> list:
    if bot_username:
        rows = _pg_exec_many("""
            SELECT link_id, channel_username, channel_title, source_bot_username, created_time, never_expires
            FROM generated_links WHERE source_bot_username = %s
            ORDER BY created_time DESC LIMIT %s OFFSET %s
        """, (bot_username, limit, offset))
    else:
        rows = _pg_exec_many("""
            SELECT link_id, channel_username, channel_title, source_bot_username, created_time, never_expires
            FROM generated_links ORDER BY created_time DESC LIMIT %s OFFSET %s
        """, (limit, offset))
    if rows is not None:
        return rows
    return []


def get_links_without_title(bot_username: str = None) -> list:
    if bot_username:
        rows = _pg_exec_many("""
            SELECT link_id, channel_username, source_bot_username FROM generated_links
            WHERE (channel_title IS NULL OR channel_title = '') AND source_bot_username = %s
            ORDER BY created_time DESC
        """, (bot_username,))
    else:
        rows = _pg_exec_many("""
            SELECT link_id, channel_username, source_bot_username FROM generated_links
            WHERE channel_title IS NULL OR channel_title = ''
            ORDER BY created_time DESC
        """)
    return rows or []


def update_link_title(link_id: str, channel_title: str) -> None:
    _pg_run("UPDATE generated_links SET channel_title = %s WHERE link_id = %s",
            (channel_title, link_id))


def move_links_to_bot(from_bot_username: str, to_bot_username: str) -> int:
    with _pg() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        cur.execute("""
            UPDATE generated_links SET source_bot_username = %s
            WHERE source_bot_username = %s
        """, (to_bot_username, from_bot_username))
        return cur.rowcount


def get_links_count(bot_username: str = None) -> int:
    if bot_username:
        row = _pg_exec("SELECT COUNT(*) FROM generated_links WHERE source_bot_username = %s",
                       (bot_username,))
    else:
        row = _pg_exec("SELECT COUNT(*) FROM generated_links")
    return row[0] if row else 0


def cleanup_expired_links() -> None:
    cutoff = datetime.utcnow() - timedelta(days=7)
    with _pg() as conn:
        if conn is None:
            return
        cur = conn.cursor()
        cur.execute("DELETE FROM generated_links WHERE created_time < %s AND never_expires = FALSE",
                    (cutoff,))
        logger.info(f"[NeonDB] Cleaned {cur.rowcount} expired links")
    if _MG.db is not None:
        try:
            res = _MG.db.generated_links.delete_many(
                {"created_time": {"$lt": cutoff}, "never_expires": False}
            )
            logger.info(f"[MongoDB] Cleaned {res.deleted_count} expired links")
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  CLONE BOTS
# ──────────────────────────────────────────────────────────────────────────────

def add_clone_bot(bot_token: str, bot_username: str) -> bool:
    ok = _pg_run("""
        INSERT INTO clone_bots (bot_token, bot_username, is_active)
        VALUES (%s, %s, TRUE)
        ON CONFLICT (bot_token) DO UPDATE
            SET bot_username = EXCLUDED.bot_username, is_active = TRUE
    """, (bot_token, bot_username))
    if _MG.db is not None:
        try:
            _MG.db.clone_bots.update_one(
                {"bot_token": bot_token},
                {"$set": {"bot_token": bot_token, "bot_username": bot_username, "is_active": True}},
                upsert=True,
            )
        except Exception:
            pass
    return bool(ok)


def get_all_clone_bots(active_only: bool = False) -> list:
    if active_only:
        rows = _pg_exec_many("""
            SELECT id, bot_token, bot_username, is_active, added_date
            FROM clone_bots WHERE is_active = TRUE ORDER BY added_date
        """)
    else:
        rows = _pg_exec_many("""
            SELECT id, bot_token, bot_username, is_active, added_date
            FROM clone_bots ORDER BY added_date
        """)
    if rows is not None:
        return rows
    if _MG.db is not None:
        try:
            filt = {"is_active": True} if active_only else {}
            return [(None, d["bot_token"], d["bot_username"], d.get("is_active", True), None)
                    for d in _MG.db.clone_bots.find(filt)]
        except Exception:
            pass
    return []


def remove_clone_bot(bot_username: str) -> bool:
    uname = bot_username.lstrip("@").lower()
    with _pg() as conn:
        if conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE clone_bots SET is_active = FALSE WHERE LOWER(bot_username) = %s",
                (uname,)
            )
    if _MG.db is not None:
        try:
            _MG.db.clone_bots.update_one(
                {"bot_username": {"$regex": f"^{uname}$", "$options": "i"}},
                {"$set": {"is_active": False}},
            )
        except Exception:
            pass
    return True


def get_main_bot_token() -> str:
    return get_setting("main_bot_token", "") or ""


def set_main_bot_token(token: str) -> None:
    set_setting("main_bot_token", token)


def am_i_a_clone_token(bot_token: str) -> bool:
    row = _pg_exec(
        "SELECT 1 FROM clone_bots WHERE bot_token = %s AND is_active = TRUE",
        (bot_token,)
    )
    if row:
        return True
    if _MG.db is not None:
        try:
            return _MG.db.clone_bots.find_one({"bot_token": bot_token, "is_active": True}) is not None
        except Exception:
            pass
    return False


def get_clone_bot_by_username(bot_username: str) -> Optional[tuple]:
    uname = bot_username.lstrip("@").lower()
    row = _pg_exec("""
        SELECT id, bot_token, bot_username, is_active FROM clone_bots
        WHERE LOWER(bot_username) = %s
    """, (uname,))
    return row


# ──────────────────────────────────────────────────────────────────────────────
#  CATEGORY SETTINGS
# ──────────────────────────────────────────────────────────────────────────────

def get_category_settings(category: str) -> dict:
    row = _pg_exec("""
        SELECT template_name, branding, buttons, caption_template,
               thumbnail_url, font_style, logo_file_id, logo_position,
               watermark_text, watermark_position
        FROM category_settings WHERE category = %s
    """, (category,))
    if row:
        return {
            "template_name": row[0] or "template1",
            "branding": row[1] or "",
            "buttons": json.loads(row[2]) if row[2] else [],
            "caption_template": row[3] or "",
            "thumbnail_url": row[4] or "",
            "font_style": row[5] or "normal",
            "logo_file_id": row[6],
            "logo_position": row[7] or "bottom",
            "watermark_text": row[8],
            "watermark_position": row[9] or "center",
        }
    # Insert defaults
    _pg_run("""
        INSERT INTO category_settings
            (category, template_name, branding, buttons, caption_template,
             thumbnail_url, font_style, watermark_position)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (category) DO NOTHING
    """, (category, "template1", "", "[]", "", "", "normal", "center"))
    return {
        "template_name": "template1", "branding": "", "buttons": [],
        "caption_template": "", "thumbnail_url": "", "font_style": "normal",
        "logo_file_id": None, "logo_position": "bottom",
        "watermark_text": None, "watermark_position": "center",
    }


def update_category_field(category: str, field: str, value: Any) -> bool:
    try:
        with _pg() as conn:
            if conn is None:
                return False
            cur = conn.cursor()
            cur.execute(f"UPDATE category_settings SET {field} = %s WHERE category = %s",
                        (value, category))
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
    with _pg() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO auto_forward_connections
                (source_chat_id, target_chat_id, delay_seconds, protect_content,
                 silent, keep_tag, pin_message, delete_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (source_chat_id, target_chat_id,
              kwargs.get("delay", 0), kwargs.get("protect", False),
              kwargs.get("silent", False), kwargs.get("keep_tag", False),
              kwargs.get("pin", False), kwargs.get("delete_src", False)))
        row = cur.fetchone()
        return row[0] if row else 0

def get_auto_forward_connections(active_only=True) -> list:
    if active_only:
        rows = _pg_exec_many(
            "SELECT * FROM auto_forward_connections WHERE active = TRUE ORDER BY created_at DESC"
        )
    else:
        rows = _pg_exec_many(
            "SELECT * FROM auto_forward_connections ORDER BY created_at DESC"
        )
    return rows or []

def delete_auto_forward_connection(conn_id) -> None:
    _pg_run("DELETE FROM auto_forward_connections WHERE id = %s", (conn_id,))

def toggle_auto_forward_connection(conn_id, active) -> None:
    _pg_run("UPDATE auto_forward_connections SET active = %s WHERE id = %s", (active, conn_id))

def add_auto_forward_filter(conn_id, allowed_media=None, blacklist=None, whitelist=None) -> None:
    _pg_run("""
        INSERT INTO auto_forward_filters (connection_id, allowed_media, blacklist, whitelist)
        VALUES (%s, %s, %s, %s)
    """, (conn_id, allowed_media or [], blacklist or [], whitelist or []))

def update_auto_forward_filter(conn_id, allowed_media=None, blacklist=None, whitelist=None) -> None:
    _pg_run("""
        UPDATE auto_forward_filters SET allowed_media=%s, blacklist=%s, whitelist=%s
        WHERE connection_id=%s
    """, (allowed_media or [], blacklist or [], whitelist or [], conn_id))

def add_auto_forward_replacement(conn_id, old, new) -> None:
    _pg_run("""
        INSERT INTO auto_forward_replacements (connection_id, old_pattern, new_pattern)
        VALUES (%s, %s, %s)
    """, (conn_id, old, new))

def get_auto_forward_replacements(conn_id) -> list:
    rows = _pg_exec_many(
        "SELECT old_pattern, new_pattern FROM auto_forward_replacements WHERE connection_id=%s",
        (conn_id,)
    )
    return rows or []

def delete_auto_forward_replacement(conn_id, old) -> None:
    _pg_run(
        "DELETE FROM auto_forward_replacements WHERE connection_id=%s AND old_pattern=%s",
        (conn_id, old)
    )

def set_auto_forward_last_message(conn_id, msg_id) -> None:
    _pg_run("""
        INSERT INTO auto_forward_state (connection_id, last_message_id) VALUES (%s, %s)
        ON CONFLICT (connection_id) DO UPDATE
            SET last_message_id = EXCLUDED.last_message_id, updated_at = NOW()
    """, (conn_id, msg_id))

def get_auto_forward_last_message(conn_id) -> int:
    row = _pg_exec(
        "SELECT last_message_id FROM auto_forward_state WHERE connection_id=%s", (conn_id,)
    )
    return row[0] if row else 0


# ──────────────────────────────────────────────────────────────────────────────
#  MANGA AUTO UPDATE
# ──────────────────────────────────────────────────────────────────────────────

def add_manga_auto(title, target_chat_id, watermark=False, combine_pdf=False) -> int:
    with _pg() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO manga_auto_update (manga_title, target_chat_id, watermark, combine_pdf, active)
            VALUES (%s, %s, %s, %s, TRUE) RETURNING id
        """, (title, target_chat_id, watermark, combine_pdf))
        row = cur.fetchone()
        return row[0] if row else 0

def get_manga_auto_list() -> list:
    rows = _pg_exec_many("""
        SELECT id, manga_title, last_chapter, target_chat_id, active
        FROM manga_auto_update ORDER BY id
    """)
    return rows or []

def delete_manga_auto(manga_id) -> None:
    _pg_run("DELETE FROM manga_auto_update WHERE id=%s", (manga_id,))

def toggle_manga_auto(manga_id) -> None:
    _pg_run("UPDATE manga_auto_update SET active = NOT active WHERE id=%s", (manga_id,))


# ──────────────────────────────────────────────────────────────────────────────
#  SCHEDULED BROADCASTS
# ──────────────────────────────────────────────────────────────────────────────

def add_scheduled_broadcast(admin_id, message_text, execute_at,
                             media_file_id=None, media_type=None) -> int:
    with _pg() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO scheduled_broadcasts
                (admin_id, message_text, media_file_id, media_type, execute_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        """, (admin_id, message_text, media_file_id, media_type, execute_at))
        row = cur.fetchone()
        return row[0] if row else 0

def get_pending_scheduled_broadcasts() -> list:
    rows = _pg_exec_many("""
        SELECT id, admin_id, message_text, media_file_id, media_type
        FROM scheduled_broadcasts WHERE status='pending' AND execute_at <= NOW()
    """)
    return rows or []

def mark_scheduled_broadcast_sent(b_id) -> None:
    _pg_run("UPDATE scheduled_broadcasts SET status='sent' WHERE id=%s", (b_id,))

def mark_scheduled_broadcast_failed(b_id) -> None:
    _pg_run("UPDATE scheduled_broadcasts SET status='failed' WHERE id=%s", (b_id,))


# ──────────────────────────────────────────────────────────────────────────────
#  FEATURE FLAGS
# ──────────────────────────────────────────────────────────────────────────────

def set_feature_flag(feature: str, entity_id: int, entity_type: str, enabled: bool) -> None:
    _pg_run("""
        INSERT INTO feature_flags (feature_name, entity_id, entity_type, enabled)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (feature_name, entity_id, entity_type) DO UPDATE SET enabled=EXCLUDED.enabled
    """, (feature, entity_id, entity_type, enabled))

def get_feature_flag(feature: str, entity_id: int, entity_type: str) -> bool:
    row = _pg_exec("""
        SELECT enabled FROM feature_flags
        WHERE feature_name=%s AND entity_id=%s AND entity_type=%s
    """, (feature, entity_id, entity_type))
    if row:
        return bool(row[0])
    if entity_type == "global":
        return True
    return get_feature_flag(feature, 0, "global")


# ──────────────────────────────────────────────────────────────────────────────
#  UPLOAD PROGRESS
# ──────────────────────────────────────────────────────────────────────────────

def load_upload_progress() -> dict:
    row = _pg_exec("""
        SELECT target_chat_id, season, episode, total_episode, video_count,
               selected_qualities, base_caption, auto_caption_enabled
        FROM bot_progress WHERE id=1
    """)
    if row:
        return {
            "target_chat_id": row[0], "season": row[1], "episode": row[2],
            "total_episode": row[3], "video_count": row[4],
            "selected_qualities": row[5].split(",") if row[5] else [],
            "base_caption": row[6] or "", "auto_caption_enabled": row[7],
        }
    _pg_run("INSERT INTO bot_progress (id, base_caption, auto_caption_enabled) VALUES (1, '', TRUE)")
    return {
        "target_chat_id": None, "season": 1, "episode": 1, "total_episode": 1,
        "video_count": 0, "selected_qualities": ["480p", "720p", "1080p"],
        "base_caption": "", "auto_caption_enabled": True,
    }

def save_upload_progress(progress: dict) -> None:
    _pg_run("""
        UPDATE bot_progress SET
            target_chat_id=%s, season=%s, episode=%s, total_episode=%s,
            video_count=%s, selected_qualities=%s, base_caption=%s,
            auto_caption_enabled=%s
        WHERE id=1
    """, (
        progress["target_chat_id"], progress["season"], progress["episode"],
        progress["total_episode"], progress["video_count"],
        ",".join(progress["selected_qualities"]),
        progress["base_caption"], progress["auto_caption_enabled"],
    ))


# ──────────────────────────────────────────────────────────────────────────────
#  CONNECTED GROUPS
# ──────────────────────────────────────────────────────────────────────────────

def add_connected_group(group_id, group_username, group_title, connected_by) -> None:
    _pg_run("""
        INSERT INTO connected_groups (group_id, group_username, group_title, connected_by)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (group_id) DO UPDATE SET active=TRUE
    """, (group_id, group_username, group_title, connected_by))

def remove_connected_group(group_id) -> None:
    _pg_run("UPDATE connected_groups SET active=FALSE WHERE group_id=%s", (group_id,))

def get_connected_groups(active_only=True) -> list:
    if active_only:
        rows = _pg_exec_many(
            "SELECT group_id, group_username, group_title, connected_at FROM connected_groups WHERE active=TRUE"
        )
    else:
        rows = _pg_exec_many(
            "SELECT group_id, group_username, group_title, connected_at FROM connected_groups"
        )
    return rows or []


# ──────────────────────────────────────────────────────────────────────────────
#  BROADCAST HISTORY
# ──────────────────────────────────────────────────────────────────────────────

def add_broadcast_history(admin_id, mode, total_users, message_text) -> int:
    with _pg() as conn:
        if conn is None:
            return 0
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO broadcast_history (admin_id, mode, total_users, message_text)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (admin_id, mode, total_users, message_text))
        row = cur.fetchone()
        return row[0] if row else 0

def update_broadcast_history(b_id, success, blocked, deleted, failed) -> None:
    _pg_run("""
        UPDATE broadcast_history
        SET completed_at=NOW(), success=%s, blocked=%s, deleted=%s, failed=%s
        WHERE id=%s
    """, (success, blocked, deleted, failed, b_id))


# ──────────────────────────────────────────────────────────────────────────────
#  POSTS CACHE
# ──────────────────────────────────────────────────────────────────────────────

def cache_post(category, title, anilist_id, media_data) -> None:
    try:
        # Use psycopg2.extras.Json so large/special-char JSON is never truncated
        try:
            from psycopg2.extras import Json as _PgJson
            json_val = _PgJson(media_data)
        except ImportError:
            json_val = json.dumps(media_data, ensure_ascii=False)
        _pg_run("""
            INSERT INTO posts_cache (category, title, anilist_id, media_data)
            VALUES (%s, %s, %s, %s)
        """, (category, title, anilist_id, json_val))
    except Exception as exc:
        logger.error(f"cache_post failed: {exc}")

def get_cached_post(anilist_id) -> Optional[dict]:
    row = _pg_exec(
        "SELECT category, title, media_data FROM posts_cache WHERE anilist_id=%s ORDER BY created_at DESC LIMIT 1",
        (anilist_id,)
    )
    if row:
        return {"category": row[0], "title": row[1], "media_data": json.loads(row[2])}
    return None


# ──────────────────────────────────────────────────────────────────────────────
#  MONGODB-PRIMARY: POSTER PREMIUM
# ──────────────────────────────────────────────────────────────────────────────

POSTER_TASK_LIMITS = {
    "gold": 50, "silver": 40, "bronze": 30, "default": 20,
}

def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def add_poster_premium(user_id: int, rank: str,
                        expiry_time: Optional[datetime] = None) -> bool:
    data = {"user_id": user_id, "rank": rank, "expiry_time": expiry_time,
            "added_at": datetime.utcnow()}
    if _MG.db is not None:
        try:
            _MG.db.poster_premium.update_one(
                {"user_id": user_id}, {"$set": data}, upsert=True
            )
            return True
        except Exception as exc:
            logger.error(f"add_poster_premium: {exc}")
    # PG fallback: store in bot_settings as JSON
    try:
        import json as _j
        existing = json.loads(get_setting("poster_premium_data", "{}") or "{}")
        existing[str(user_id)] = {
            "rank": rank,
            "expiry_time": expiry_time.isoformat() if expiry_time else None,
        }
        set_setting("poster_premium_data", _j.dumps(existing))
        return True
    except Exception:
        return False


def get_poster_premium(user_id: int) -> Optional[dict]:
    if _MG.db is not None:
        try:
            doc = _MG.db.poster_premium.find_one({"user_id": user_id})
            if doc:
                expiry = doc.get("expiry_time")
                if expiry and expiry < datetime.utcnow():
                    _MG.db.poster_premium.delete_one({"user_id": user_id})
                    return None
                return doc
        except Exception:
            pass
    # PG fallback
    try:
        raw = get_setting("poster_premium_data", "{}")
        data = json.loads(raw or "{}")
        ud = data.get(str(user_id))
        if ud:
            exp = ud.get("expiry_time")
            if exp:
                exp_dt = datetime.fromisoformat(exp)
                if exp_dt < datetime.utcnow():
                    data.pop(str(user_id), None)
                    set_setting("poster_premium_data", json.dumps(data))
                    return None
            return ud
    except Exception:
        pass
    return None


def remove_poster_premium(user_id: int) -> bool:
    if _MG.db is not None:
        try:
            _MG.db.poster_premium.delete_one({"user_id": user_id})
        except Exception:
            pass
    try:
        raw = get_setting("poster_premium_data", "{}")
        data = json.loads(raw or "{}")
        data.pop(str(user_id), None)
        set_setting("poster_premium_data", json.dumps(data))
    except Exception:
        pass
    return True


def get_all_poster_premium() -> list:
    if _MG.db is not None:
        try:
            now = datetime.utcnow()
            return list(_MG.db.poster_premium.find(
                {"$or": [{"expiry_time": None}, {"expiry_time": {"$gt": now}}]},
                {"_id": 0}
            ))
        except Exception:
            pass
    return []


def is_poster_premium(user_id: int) -> bool:
    return get_poster_premium(user_id) is not None


def get_poster_rank(user_id: int) -> str:
    doc = get_poster_premium(user_id)
    return doc.get("rank", "default") if doc else "default"


def check_and_update_poster_usage(user_id: int, limit: int) -> bool:
    """Returns True if within limit, updates counter. Uses MongoDB for speed."""
    today = _today()
    if _MG.db is not None:
        try:
            res = _MG.db.poster_usage.find_one_and_update(
                {"user_id": user_id, "date": today},
                {"$inc": {"count": 1}},
                upsert=True, return_document=True,
            )
            count = res.get("count", 1) if res else 1
            if count > limit:
                # Decrement back
                _MG.db.poster_usage.update_one(
                    {"user_id": user_id, "date": today}, {"$inc": {"count": -1}}
                )
                return False
            return True
        except Exception:
            pass
    # Fallback: in-memory (no persistence)
    return True


def get_poster_usage_today(user_id: int) -> int:
    today = _today()
    if _MG.db is not None:
        try:
            doc = _MG.db.poster_usage.find_one({"user_id": user_id, "date": today})
            return doc.get("count", 0) if doc else 0
        except Exception:
            pass
    return 0


# ──────────────────────────────────────────────────────────────────────────────
#  MONGODB-PRIMARY: COUPLES
# ──────────────────────────────────────────────────────────────────────────────

def get_couple(user_id: int) -> Optional[dict]:
    if _MG.db is not None:
        try:
            return _MG.db.couples.find_one({"user_id": user_id}, {"_id": 0})
        except Exception:
            pass
    return None


def set_couple(user_id: int, partner_id: int, chat_id: int) -> None:
    if _MG.db is not None:
        try:
            _MG.db.couples.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "partner_id": partner_id,
                          "chat_id": chat_id, "since": datetime.utcnow()}},
                upsert=True,
            )
        except Exception:
            pass


def remove_couple(user_id: int) -> None:
    if _MG.db is not None:
        try:
            _MG.db.couples.delete_many(
                {"$or": [{"user_id": user_id}, {"partner_id": user_id}]}
            )
        except Exception:
            pass


def get_couple_of_day(chat_id: int) -> Optional[tuple]:
    if _MG.db is not None:
        try:
            today = _today()
            doc = _MG.db.couple_of_day.find_one({"chat_id": chat_id, "date": today})
            if doc:
                return (doc.get("user1_id"), doc.get("user2_id"))
        except Exception:
            pass
    return None


def set_couple_of_day(chat_id: int, user1: int, user2: int) -> None:
    if _MG.db is not None:
        try:
            today = _today()
            _MG.db.couple_of_day.update_one(
                {"chat_id": chat_id, "date": today},
                {"$set": {"chat_id": chat_id, "date": today,
                          "user1_id": user1, "user2_id": user2}},
                upsert=True,
            )
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  MONGODB-PRIMARY: CHATBOT
# ──────────────────────────────────────────────────────────────────────────────

def is_chatbot_enabled(chat_id: int) -> bool:
    if _MG.db is not None:
        try:
            doc = _MG.db.chatbot_data.find_one({"chat_id": chat_id})
            return bool(doc and doc.get("enabled", False))
        except Exception:
            pass
    return False


def set_chatbot_enabled(chat_id: int, enabled: bool) -> None:
    if _MG.db is not None:
        try:
            _MG.db.chatbot_data.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id, "enabled": enabled}},
                upsert=True,
            )
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  ANIME CHANNEL LINKS — maps anime title ↔ channel for filter+poster system
# ──────────────────────────────────────────────────────────────────────────────

def add_anime_channel_link(anime_title: str, channel_id: int,
                            channel_title: str = "", link_id: str = "",
                            added_by: int = 0) -> bool:
    """Store anime-title → channel mapping used for filter poster delivery."""
    ok = _pg_run("""
        INSERT INTO anime_channel_links
            (anime_title, channel_id, channel_title, link_id, added_by)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (anime_title, channel_id) DO UPDATE
            SET channel_title = EXCLUDED.channel_title,
                link_id = EXCLUDED.link_id
    """, (anime_title.strip().lower(), channel_id, channel_title, link_id, added_by))
    return bool(ok)


def get_anime_channel_links(anime_title: str) -> list:
    """Return list of (channel_id, channel_title, link_id) for given anime title."""
    rows = _pg_exec_many("""
        SELECT channel_id, channel_title, link_id
        FROM anime_channel_links WHERE anime_title = %s
        ORDER BY created_at DESC
    """, (anime_title.strip().lower(),))
    return rows or []


def get_all_anime_channel_links() -> list:
    """Return all rows: (id, anime_title, channel_id, channel_title, link_id, created_at)."""
    rows = _pg_exec_many("""
        SELECT id, anime_title, channel_id, channel_title, link_id, created_at
        FROM anime_channel_links ORDER BY anime_title
    """)
    return rows or []


def remove_anime_channel_link(anime_title: str, channel_id: int) -> None:
    _pg_run("DELETE FROM anime_channel_links WHERE anime_title = %s AND channel_id = %s",
            (anime_title.strip().lower(), channel_id))


def get_filter_poster_cache(cache_key: str) -> Optional[dict]:
    row = _pg_exec("""
        SELECT file_id, channel_id, channel_msg_id, caption, template, anime_title
        FROM filter_poster_cache WHERE cache_key = %s
    """, (cache_key,))
    if row:
        return {"file_id": row[0], "channel_id": row[1],
                "channel_msg_id": row[2], "caption": row[3],
                "template": row[4], "anime_title": row[5]}
    return None


def save_filter_poster_cache(cache_key: str, anime_title: str, template: str,
                               file_id: str, channel_id: int = 0,
                               channel_msg_id: int = 0, caption: str = "") -> None:
    _pg_run("""
        INSERT INTO filter_poster_cache
            (cache_key, anime_title, template, file_id, channel_id, channel_msg_id, caption)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cache_key) DO UPDATE
            SET file_id = EXCLUDED.file_id,
                channel_msg_id = EXCLUDED.channel_msg_id,
                created_at = NOW()
    """, (cache_key, anime_title.lower(), template, file_id,
             channel_id, channel_msg_id, caption))


# ──────────────────────────────────────────────────────────────────────────────
#  CHANNEL WELCOME SYSTEM
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_channel_welcome_table() -> None:
    _pg_run("""
        CREATE TABLE IF NOT EXISTS channel_welcome_settings (
            channel_id BIGINT PRIMARY KEY,
            enabled BOOLEAN DEFAULT TRUE,
            welcome_text TEXT DEFAULT '',
            image_file_id TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            buttons_json TEXT DEFAULT '[]',
            added_by BIGINT DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)


def get_channel_welcome(channel_id: int) -> Optional[dict]:
    """Return channel welcome settings dict, or None if not configured."""
    row = _pg_exec("""
        SELECT enabled, welcome_text, image_file_id, image_url, buttons_json
        FROM channel_welcome_settings WHERE channel_id = %s
    """, (channel_id,))
    if row:
        import json as _j
        return {
            "enabled":      bool(row[0]),
            "welcome_text": row[1] or "",
            "image_file_id": row[2] or "",
            "image_url":    row[3] or "",
            "buttons":      _j.loads(row[4]) if row[4] else [],
        }
    return None


def set_channel_welcome(channel_id: int, **kwargs) -> None:
    """Create or update channel welcome settings."""
    import json as _j
    _ensure_channel_welcome_table()
    existing = get_channel_welcome(channel_id) or {}
    _pg_run("""
        INSERT INTO channel_welcome_settings
            (channel_id, enabled, welcome_text, image_file_id, image_url, buttons_json, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (channel_id) DO UPDATE
            SET enabled       = EXCLUDED.enabled,
                welcome_text  = EXCLUDED.welcome_text,
                image_file_id = EXCLUDED.image_file_id,
                image_url     = EXCLUDED.image_url,
                buttons_json  = EXCLUDED.buttons_json,
                updated_at    = NOW()
    """, (
        channel_id,
        kwargs.get("enabled",       existing.get("enabled", True)),
        kwargs.get("welcome_text",  existing.get("welcome_text", "")),
        kwargs.get("image_file_id", existing.get("image_file_id", "")),
        kwargs.get("image_url",     existing.get("image_url", "")),
        _j.dumps(kwargs.get("buttons", existing.get("buttons", []))),
    ))


def delete_channel_welcome(channel_id: int) -> None:
    _pg_run("DELETE FROM channel_welcome_settings WHERE channel_id = %s", (channel_id,))


def get_all_channel_welcomes() -> list:
    """Return list of (channel_id, enabled, welcome_text) tuples."""
    rows = _pg_exec_many(
        "SELECT channel_id, enabled, welcome_text FROM channel_welcome_settings ORDER BY channel_id"
    )
    return rows or []


# ──────────────────────────────────────────────────────────────────────────────
#  DB MANAGER COMPAT (some modules import db_manager directly)
# ──────────────────────────────────────────────────────────────────────────────

class _DBManagerCompat:
    """Compatibility shim for code that does `db_manager.get_cursor()`."""

    @contextmanager
    def get_connection(self):
        with _pg() as conn:
            yield conn

    @contextmanager
    def get_cursor(self):
        with _pg() as conn:
            if conn is None:
                yield None
                return
            cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def close_all(self):
        if _PG.pool:
            _PG.pool.closeall()


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
    import re as _re
    if not channel_title:
        return ""
    t = channel_title.strip()
    # Remove trailing language/dub markers (case-insensitive)
    _STRIP = [
        r"\s*[\-|:–—].*$",                          # " - anything after dash"
        r"\s+in\s+(hindi|english|tamil|telugu|urdu|japanese|korean|chinese)\s*$",
        r"\s+(hindi|english|tamil|telugu|urdu|japanese|korean|chinese)\s+(dubbed|dub|sub|subbed|audio|version)\s*$",
        r"\s+(dubbed|dub|subbed|sub|esub|multi.?audio|multi.?sub)\s*$",
        r"\s+(official|hd|fhd|4k|720p|1080p)\s*$",
        r"\s+channel\s*$",
        r"\s+anime\s*$",
    ]
    for pat in _STRIP:
        t = _re.sub(pat, "", t, flags=_re.IGNORECASE).strip()
    # If result is too short (< 3 chars), return original
    return t if len(t) >= 3 else channel_title.strip()

