"""
api/mangadex.py
===============
Full MangaDex API client + MangaTracker for auto-update notifications.
"""
import requests
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from core.text_utils import strip_html, truncate, e, b, bq, code
from core.logging_setup import api_logger, db_logger


class MangaDexClient:
    BASE_URL = "https://api.mangadex.org"
    COVER_BASE = "https://uploads.mangadex.org/covers"

    @staticmethod
    def _get(endpoint: str, params: Dict = None) -> Optional[Dict]:
        try:
            resp = requests.get(
                f"{MangaDexClient.BASE_URL}{endpoint}",
                params=params or {},
                timeout=12,
            )
            if resp.status_code == 200:
                return resp.json()
            api_logger.debug(f"MangaDex {resp.status_code}: {endpoint}")
        except Exception as exc:
            api_logger.debug(f"MangaDex error: {exc}")
        return None

    @staticmethod
    def search_manga(title: str, limit: int = 10) -> List[Dict]:
        data = MangaDexClient._get("/manga", {
            "title": title,
            "limit": limit,
            "includes[]": ["cover_art", "author", "artist"],
            "availableTranslatedLanguage[]": "en",
            "order[relevance]": "desc",
        })
        if not data:
            return []
        return data.get("data", [])

    @staticmethod
    def get_manga(manga_id: str) -> Optional[Dict]:
        data = MangaDexClient._get(f"/manga/{manga_id}", {
            "includes[]": ["cover_art", "author", "artist"]
        })
        if data:
            return data.get("data")
        return None

    @staticmethod
    def get_chapters(
        manga_id: str,
        language: str = "en",
        limit: int = 10,
        offset: int = 0,
        order: str = "desc",
    ) -> Tuple[List[Dict], int]:
        data = MangaDexClient._get("/chapter", {
            "manga": manga_id,
            "translatedLanguage[]": language,
            "limit": limit,
            "offset": offset,
            f"order[chapter]": order,
            "includes[]": ["scanlation_group"],
        })
        if not data:
            return [], 0
        return data.get("data", []), data.get("total", 0)

    @staticmethod
    def get_latest_chapter(manga_id: str, language: str = "en") -> Optional[Dict]:
        chapters, total = MangaDexClient.get_chapters(manga_id, language, limit=1)
        return chapters[0] if chapters else None

    @staticmethod
    def get_chapter_pages(chapter_id: str) -> Optional[Tuple[str, str, List[str]]]:
        data = MangaDexClient._get(f"/at-home/server/{chapter_id}")
        if not data:
            return None
        chapter_data = data.get("chapter", {})
        return (
            data.get("baseUrl", ""),
            chapter_data.get("hash", ""),
            chapter_data.get("data", []),
        )

    @staticmethod
    def get_cover_url(manga_id: str, filename: str, size: int = 256) -> str:
        return f"{MangaDexClient.COVER_BASE}/{manga_id}/{filename}.{size}.jpg"

    @staticmethod
    def extract_cover_filename(manga: Dict) -> Optional[str]:
        for rel in (manga.get("relationships") or []):
            if rel.get("type") == "cover_art":
                attrs = rel.get("attributes") or {}
                return attrs.get("fileName")
        return None

    @staticmethod
    def extract_authors(manga: Dict) -> str:
        names = []
        for rel in (manga.get("relationships") or []):
            if rel.get("type") in ("author", "artist"):
                attrs = rel.get("attributes") or {}
                name = attrs.get("name")
                if name and name not in names:
                    names.append(e(name))
        return ", ".join(names) if names else "Unknown"

    @staticmethod
    def format_manga_info(manga: Dict) -> Tuple[str, str]:
        """Build manga info text and cover URL. Returns (text, cover_url)."""
        attrs = manga.get("attributes", {}) or {}
        manga_id = manga.get("id", "")

        titles = attrs.get("title", {}) or {}
        title = (
            titles.get("en") or titles.get("ja-ro") or titles.get("ja")
            or next(iter(titles.values()), "Unknown")
        )

        alt_titles_list = attrs.get("altTitles", []) or []
        alt_en = next((t.get("en") for t in alt_titles_list if "en" in t), None)

        desc_obj = attrs.get("description", {}) or {}
        desc = desc_obj.get("en") or next(iter(desc_obj.values()), "No description.")
        desc = truncate(strip_html(desc), 280)

        status = (attrs.get("status") or "unknown").title()
        year = attrs.get("year") or "?"
        content_rating = (attrs.get("contentRating") or "safe").title()
        lang_origin = (attrs.get("originalLanguage") or "").upper()

        tags = attrs.get("tags", []) or []
        tag_names = [
            t.get("attributes", {}).get("name", {}).get("en", "")
            for t in tags
            if t.get("attributes", {}).get("name", {}).get("en")
        ]
        genre_str = " • ".join(tag_names[:6]) if tag_names else "N/A"

        chapters = attrs.get("lastChapter") or "?"
        volumes = attrs.get("lastVolume") or "?"
        authors = MangaDexClient.extract_authors(manga)

        cover_fn = MangaDexClient.extract_cover_filename(manga)
        cover_url = MangaDexClient.get_cover_url(manga_id, cover_fn, 512) if cover_fn else ""

        site_url = f"https://mangadex.org/title/{manga_id}"

        lines = [b(e(title))]
        if alt_en and alt_en != title:
            lines.append(f"<i>{e(alt_en)}</i>")
        lines.append("")
        lines += [
            f"<b> Status:</b> {code(status)}",
            f"<b> Chapters:</b> {code(str(chapters))}",
            f"<b> Volumes:</b> {code(str(volumes))}",
            f"<b> Year:</b> {code(str(year))}",
            f"<b> Origin:</b> {code(lang_origin or 'N/A')}",
            f"<b> Rating:</b> {code(content_rating)}",
            f"<b> Author/Artist:</b> {authors}",
            f"<b> Genres:</b> {e(genre_str)}",
            "",
            b(" Synopsis"),
            bq(e(desc), expandable=True),
            f"\n<b> MangaDex:</b> {site_url}",
        ]

        return "\n".join(str(l) for l in lines), cover_url

    @staticmethod
    def format_chapter_info(chapter: Dict) -> str:
        attrs = chapter.get("attributes", {}) or {}
        ch_id = chapter.get("id", "")
        ch_num = attrs.get("chapter") or "?"
        title = attrs.get("title") or ""
        pages = attrs.get("pages", 0)
        lang = (attrs.get("translatedLanguage") or "?").upper()
        pub_at = attrs.get("publishAt") or attrs.get("createdAt") or ""
        if pub_at:
            try:
                pub_at = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).strftime("%d %b %Y")
            except Exception:
                pass

        groups = []
        for rel in (chapter.get("relationships") or []):
            if rel.get("type") == "scanlation_group":
                gname = (rel.get("attributes") or {}).get("name", "")
                if gname:
                    groups.append(e(gname))
        group_str = ", ".join(groups) if groups else "Unknown"

        parts = [f"<b>Chapter {ch_num}</b>"]
        if title:
            parts.append(f" — <i>{e(title)}</i>")
        lines = [" ".join(parts), ""]
        lines += [
            f"<b> Pages:</b> {code(str(pages))}",
            f"<b> Language:</b> {code(lang)}",
            f"<b> Group:</b> {group_str}",
            f"<b> Released:</b> {code(pub_at)}",
            f"<b> Read:</b> https://mangadex.org/chapter/{ch_id}",
        ]
        return "\n".join(lines)


class MangaTracker:
    """Tracks manga series for automatic new-chapter notifications."""

    @staticmethod
    def add_tracking(
        manga_id: str,
        manga_title: str,
        target_chat_id: int,
        notify_language: str = "en",
    ) -> bool:
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO manga_auto_updates
                        (manga_id, manga_title, target_chat_id, notify_language,
                         last_chapter, last_checked, active)
                    VALUES (%s, %s, %s, %s, %s, NOW(), TRUE)
                    ON CONFLICT (manga_id, target_chat_id) DO UPDATE
                        SET active = TRUE, manga_title = EXCLUDED.manga_title,
                            notify_language = EXCLUDED.notify_language
                """, (manga_id, manga_title, target_chat_id, notify_language, None))
            return True
        except Exception as exc:
            db_logger.error(f"MangaTracker.add_tracking error: {exc}")
            return False

    @staticmethod
    def remove_tracking(manga_id: str, target_chat_id: Optional[int] = None) -> bool:
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                if target_chat_id:
                    cur.execute(
                        "UPDATE manga_auto_updates SET active = FALSE "
                        "WHERE manga_id = %s AND target_chat_id = %s",
                        (manga_id, target_chat_id),
                    )
                else:
                    cur.execute(
                        "UPDATE manga_auto_updates SET active = FALSE WHERE manga_id = %s",
                        (manga_id,),
                    )
            return True
        except Exception as exc:
            db_logger.error(f"MangaTracker.remove_tracking error: {exc}")
            return False

    @staticmethod
    def get_all_tracked() -> List[Tuple]:
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute("""
                    SELECT id, manga_id, manga_title, target_chat_id,
                           notify_language, last_chapter, last_checked
                    FROM manga_auto_updates WHERE active = TRUE
                """)
                return cur.fetchall() or []
        except Exception as exc:
            db_logger.error(f"MangaTracker.get_all_tracked error: {exc}")
            return []

    @staticmethod
    def update_last_chapter(rec_id: int, chapter: str) -> None:
        try:
            from database_dual import db_manager
            with db_manager.get_cursor() as cur:
                cur.execute(
                    "UPDATE manga_auto_updates SET last_chapter = %s, last_checked = NOW() WHERE id = %s",
                    (chapter, rec_id),
                )
        except Exception as exc:
            db_logger.error(f"MangaTracker.update_last_chapter error: {exc}")

    @staticmethod
    def get_tracked_for_admin() -> str:
        rows = MangaTracker.get_all_tracked()
        if not rows:
            return b("No manga tracked yet.")
        lines = [b("📚 Tracked Manga:"), ""]
        for rec in rows:
            rec_id, manga_id, title, target_chat, lang, last_ch, last_checked = rec
            lines.append(
                f"• {b(e(title))}\n"
                f"  <b>Last Chapter:</b> {code(last_ch or 'None yet')}\n"
                f"  <b>Target:</b> <code>{target_chat}</code>\n"
                f"  <b>Lang:</b> {code(lang)}\n"
                f"  <b>Checked:</b> {code(str(last_checked)[:16])}\n"
                f"  <b>ID:</b> <code>{manga_id}</code>\n"
            )
        return "\n".join(lines)
