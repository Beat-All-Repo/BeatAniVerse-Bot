"""
api/anilist.py
==============
Full AniList GraphQL API client.
"""
import hashlib
import json
import requests
from typing import Optional, Dict, List

from core.cache import cache_get, cache_set
from core.text_utils import strip_html, truncate, parse_date, format_number, e, b, bq, code
from core.logging_setup import api_logger


class AniListClient:
    BASE_URL = "https://graphql.anilist.co"

    ANIME_FIELDS = """
        id siteUrl
        title { romaji english native }
        description(asHtml: false)
        coverImage { extraLarge large medium color }
        bannerImage
        format status season seasonYear
        episodes duration averageScore popularity
        genres tags { name rank isMediaSpoiler }
        studios(isMain: true) { nodes { name siteUrl } }
        startDate { year month day }
        endDate { year month day }
        nextAiringEpisode { episode airingAt timeUntilAiring }
        relations { edges { relationType(version: 2) node { id title { romaji } type format } } }
        characters(sort: ROLE, page: 1, perPage: 5) {
            nodes { name { full } image { medium } }
        }
        staff(sort: RELEVANCE, page: 1, perPage: 3) {
            nodes { name { full } primaryOccupations }
        }
        trailer { id site }
        externalLinks { url site }
        rankings { rank type context }
        streamingEpisodes { title thumbnail url site }
        isAdult
        countryOfOrigin
    """

    MANGA_FIELDS = """
        id siteUrl
        title { romaji english native }
        description(asHtml: false)
        coverImage { extraLarge large medium color }
        bannerImage
        format status
        chapters volumes averageScore popularity
        genres tags { name rank }
        startDate { year month day }
        endDate { year month day }
        relations { edges { relationType(version: 2) node { id title { romaji } type format } } }
        characters(sort: ROLE, page: 1, perPage: 5) {
            nodes { name { full } image { medium } }
        }
        staff(sort: RELEVANCE, page: 1, perPage: 3) {
            nodes { name { full } primaryOccupations }
        }
        externalLinks { url site }
        countryOfOrigin
    """

    _EXPANSIONS = {
        "aot": "attack on titan",
        "bnha": "my hero academia",
        "mha": "my hero academia",
        "hxh": "hunter x hunter",
        "dbs": "dragon ball super",
        "dbz": "dragon ball z",
        "op": "one piece",
        "fma": "fullmetal alchemist",
        "snk": "attack on titan",
        "jjk": "jujutsu kaisen",
        "csm": "chainsaw man",
        "slime": "that time i got reincarnated as a slime",
        "rezero": "re zero starting life in another world",
    }

    @staticmethod
    def _normalize_query(query: str) -> str:
        query = " ".join(query.strip().split())
        lower = query.lower()
        return AniListClient._EXPANSIONS.get(lower, query)

    @staticmethod
    def search_anime(query: str) -> Optional[Dict]:
        normalized = AniListClient._normalize_query(query)
        q = f"""
        query($s:String){{
          Media(search:$s,type:ANIME){{
            {AniListClient.ANIME_FIELDS}
          }}
        }}
        """
        result = AniListClient._query(q, {"s": normalized})
        if not result and normalized != query:
            result = AniListClient._query(q, {"s": query})
        return result

    @staticmethod
    def search_manga(query: str) -> Optional[Dict]:
        normalized = AniListClient._normalize_query(query)
        q = f"""
        query($s:String){{
          Media(search:$s,type:MANGA){{
            {AniListClient.MANGA_FIELDS}
          }}
        }}
        """
        result = AniListClient._query(q, {"s": normalized})
        if not result and normalized != query:
            result = AniListClient._query(q, {"s": query})
        return result

    @staticmethod
    def get_by_id(media_id: int, media_type: str = "ANIME") -> Optional[Dict]:
        fields = AniListClient.ANIME_FIELDS if media_type == "ANIME" else AniListClient.MANGA_FIELDS
        q = f"""
        query($id:Int){{
          Media(id:$id,type:{media_type}){{
            {fields}
          }}
        }}
        """
        return AniListClient._query(q, {"id": media_id})

    @staticmethod
    def get_trending(media_type: str = "ANIME", limit: int = 5) -> List[Dict]:
        q = f"""
        query($type:MediaType,$perPage:Int){{
          Page(perPage:$perPage){{
            media(type:$type,sort:TRENDING_DESC,isAdult:false){{
              id title{{romaji}} coverImage{{medium}} averageScore
            }}
          }}
        }}
        """
        try:
            resp = requests.post(
                AniListClient.BASE_URL,
                json={"query": q, "variables": {"type": media_type, "perPage": limit}},
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("Page", {}).get("media", [])
        except Exception as exc:
            api_logger.debug(f"AniList trending query failed: {exc}")
        return []

    @staticmethod
    def _query(query_str: str, variables: dict) -> Optional[Dict]:
        cache_key = f"anilist:{hashlib.md5(json.dumps({'q': query_str, 'v': variables}, sort_keys=True).encode()).hexdigest()}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = requests.post(
                AniListClient.BASE_URL,
                json={"query": query_str, "variables": variables},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=12,
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("data", {}).get("Media")
                if result:
                    cache_set(cache_key, result)
                return result
            elif resp.status_code == 429:
                api_logger.warning("AniList rate limited")
                return None
            else:
                api_logger.debug(f"AniList {resp.status_code}: {resp.text[:300]}")
        except requests.Timeout:
            api_logger.debug("AniList request timed out")
        except Exception as exc:
            api_logger.debug(f"AniList request failed: {exc}")
        return None

    @staticmethod
    def format_anime_caption(data: Dict, template: Optional[str] = None) -> str:
        title_obj = data.get("title", {}) or {}
        title_romaji = title_obj.get("romaji", "")
        title_english = title_obj.get("english", "")
        title_display = title_english or title_romaji or "Unknown"

        status = (data.get("status") or "").replace("_", " ").title()
        fmt = (data.get("format") or "").replace("_", " ").title()
        episodes = data.get("episodes", "?")
        duration = data.get("duration")
        score = data.get("averageScore")
        popularity = data.get("popularity", 0)
        genres = data.get("genres", []) or []
        genres_str = ", ".join(genres[:5]) if genres else "N/A"

        season = data.get("season")
        season_year = data.get("seasonYear")
        season_str = f"{season.title() if season else ''} {season_year or ''}".strip() or "N/A"

        studios = data.get("studios", {}) or {}
        studio_nodes = studios.get("nodes", []) or []
        studio_name = studio_nodes[0].get("name", "N/A") if studio_nodes else "N/A"

        desc = strip_html(data.get("description") or "No description available.")
        desc = truncate(desc, 350)

        next_ep = data.get("nextAiringEpisode")
        next_ep_str = ""
        if next_ep:
            ep_num = next_ep.get("episode", "?")
            time_left = next_ep.get("timeUntilAiring", 0)
            days = time_left // 86400
            hrs = (time_left % 86400) // 3600
            next_ep_str = f"\n<b>Next Episode:</b> Ep.{ep_num} in {days}d {hrs}h"

        if template:
            for key, val in {
                "{title}": e(title_display), "{romaji}": e(title_romaji),
                "{status}": e(status), "{type}": e(fmt),
                "{episodes}": str(episodes), "{score}": str(score or "N/A"),
                "{genres}": e(genres_str), "{studio}": e(studio_name),
                "{synopsis}": e(desc), "{season}": e(season_str),
                "{popularity}": format_number(popularity),
                "{rating}": str(score or "N/A"),
            }.items():
                template = template.replace(key, val)
            return template

        caption = b(e(title_display)) + "\n\n"
        caption += "━━━━━━━━━━━━━━\n"
        caption += f"➤ Status: {status}\n"
        caption += f"➤ Episodes: {str(episodes)}"
        if duration:
            caption += f" × {duration}min"
        caption += "\n"
        caption += f"➤ Rating: {str(score) + '/100' if score else 'N/A'}\n"
        caption += f"➤ Genres: {e(genres_str)}\n"
        if next_ep_str:
            caption += next_ep_str + "\n"
        caption += "\n"
        caption += bq(e(desc), expandable=True)

        site_url = data.get("siteUrl", "")
        if site_url:
            caption += f"\n\n<b>AniList:</b> {site_url}"

        return caption

    @staticmethod
    def format_manga_caption(data: Dict, template: Optional[str] = None) -> str:
        title_obj = data.get("title", {}) or {}
        title_display = title_obj.get("english") or title_obj.get("romaji") or "Unknown"
        title_romaji = title_obj.get("romaji", "")

        status = (data.get("status") or "").replace("_", " ").title()
        fmt = (data.get("format") or "").replace("_", " ").title()
        chapters = data.get("chapters", "Ongoing")
        volumes = data.get("volumes", "?")
        score = data.get("averageScore")
        popularity = data.get("popularity", 0)
        genres = data.get("genres", []) or []
        genres_str = ", ".join(genres[:5]) if genres else "N/A"

        desc = strip_html(data.get("description") or "No description available.")
        desc = truncate(desc, 350)

        if template:
            for key, val in {
                "{title}": e(title_display), "{romaji}": e(title_romaji),
                "{status}": e(status), "{type}": e(fmt),
                "{chapters}": str(chapters), "{volumes}": str(volumes),
                "{score}": str(score or "N/A"), "{genres}": e(genres_str),
                "{synopsis}": e(desc),
                "{popularity}": format_number(popularity),
            }.items():
                template = template.replace(key, val)
            return template

        caption = b(e(title_display)) + "\n\n"
        caption += "━━━━━━━━━━━━━━\n"
        caption += f"➤ Chapters: {str(chapters)}\n"
        caption += f"➤ Status: {status}\n"
        caption += f"➤ Source: {e(genres_str)}\n"
        caption += "\n"
        caption += bq(e(desc), expandable=True)

        site_url = data.get("siteUrl", "")
        if site_url:
            caption += f"\n\n<b>AniList:</b> {site_url}"

        return caption
