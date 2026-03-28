"""
api/tmdb.py
===========
Full TMDB API client for movies and TV shows.
"""
import requests
from typing import Optional, Dict, List

from core.config import TMDB_API_KEY
from core.text_utils import e, b, bq, code, truncate, format_number
from core.logging_setup import api_logger


class TMDBClient:
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"

    @staticmethod
    def _get(endpoint: str, params: Dict = None) -> Optional[Dict]:
        if not TMDB_API_KEY:
            return None
        p = {"api_key": TMDB_API_KEY}
        if params:
            p.update(params)
        try:
            resp = requests.get(
                f"{TMDBClient.BASE_URL}{endpoint}", params=p, timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            api_logger.debug(f"TMDB {resp.status_code}: {endpoint}")
        except Exception as exc:
            api_logger.debug(f"TMDB error: {exc}")
        return None

    @staticmethod
    def search_movie(query: str) -> Optional[Dict]:
        data = TMDBClient._get("/search/movie", {"query": query, "language": "en-US"})
        if not data:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return TMDBClient.get_movie_details(results[0]["id"])

    @staticmethod
    def search_tv(query: str) -> Optional[Dict]:
        data = TMDBClient._get("/search/tv", {"query": query, "language": "en-US"})
        if not data:
            return None
        results = data.get("results", [])
        if not results:
            return None
        return TMDBClient.get_tv_details(results[0]["id"])

    @staticmethod
    def get_movie_details(movie_id: int) -> Optional[Dict]:
        return TMDBClient._get(
            f"/movie/{movie_id}",
            {"append_to_response": "credits,keywords,release_dates,videos", "language": "en-US"},
        )

    @staticmethod
    def get_tv_details(tv_id: int) -> Optional[Dict]:
        return TMDBClient._get(
            f"/tv/{tv_id}",
            {"append_to_response": "credits,keywords,content_ratings,videos", "language": "en-US"},
        )

    @staticmethod
    def get_trending(media_type: str = "movie", time_window: str = "week") -> List[Dict]:
        data = TMDBClient._get(f"/trending/{media_type}/{time_window}")
        return (data or {}).get("results", [])[:5]

    @staticmethod
    def get_poster_url(path: str, size: str = "w500") -> str:
        if not path:
            return ""
        return f"{TMDBClient.IMAGE_BASE}/{size}{path}"

    @staticmethod
    def get_backdrop_url(path: str, size: str = "w780") -> str:
        if not path:
            return ""
        return f"{TMDBClient.IMAGE_BASE}/{size}{path}"

    @staticmethod
    def format_movie_caption(data: Dict, template: Optional[str] = None) -> str:
        title = e(data.get("title") or data.get("name") or "Unknown")
        original_title = e(data.get("original_title") or data.get("original_name") or "")
        tagline = e(data.get("tagline") or "")
        release = e(data.get("release_date") or "Unknown")
        runtime = data.get("runtime") or 0
        runtime_str = f"{runtime // 60}h {runtime % 60}m" if runtime else "N/A"
        rating = data.get("vote_average", 0)
        vote_count = data.get("vote_count", 0)
        status = e(data.get("status") or "Unknown")
        language = e(data.get("original_language") or "N/A").upper()
        genres = [g["name"] for g in data.get("genres", []) or []]
        genres_str = " • ".join(genres[:5]) if genres else "N/A"
        budget = data.get("budget", 0)
        revenue = data.get("revenue", 0)
        overview = e(truncate(data.get("overview") or "No overview.", 300))

        credits = data.get("credits", {}) or {}
        cast = credits.get("cast", []) or []
        top_cast = ", ".join(e(c["name"]) for c in cast[:5]) if cast else "N/A"
        crew = credits.get("crew", []) or []
        directors = [c["name"] for c in crew if c.get("job") == "Director"]
        director_str = e(", ".join(directors[:2])) if directors else "N/A"

        keywords = data.get("keywords", {}) or {}
        kw_list = [k["name"] for k in (keywords.get("keywords") or [])[:5]]
        kw_str = " • ".join(kw_list) if kw_list else ""

        if template:
            for key, val in {
                "{title}": title, "{release_date}": release,
                "{rating}": str(rating), "{genres}": e(genres_str),
                "{overview}": overview, "{runtime}": runtime_str,
                "{director}": director_str, "{cast}": top_cast,
                "{status}": status, "{language}": language,
            }.items():
                template = template.replace(key, val)
            return template

        lines = [b(title)]
        if original_title and original_title != title:
            lines.append(f"<i>{original_title}</i>")
        if tagline:
            lines.append(f"<i>❝{tagline}❞</i>")
        lines.append("")
        lines += [
            f"<b> Released:</b> {code(release)}",
            f"<b> Runtime:</b> {code(runtime_str)}",
            f"<b> Status:</b> {code(status)}",
            f"<b> Rating:</b> {code(f'{rating:.1f}/10 ({format_number(vote_count)} votes)')}",
            f"<b> Language:</b> {code(language)}",
            f"<b> Genres:</b> {e(genres_str)}",
            f"<b> Director:</b> {director_str}",
            f"<b> Cast:</b> {top_cast}",
        ]
        if budget:
            lines.append(f"<b> Budget:</b> {code('$' + format_number(budget))}")
        if revenue:
            lines.append(f"<b> Revenue:</b> {code('$' + format_number(revenue))}")
        if kw_str:
            lines.append(f"<b>🏷 Keywords:</b> {e(kw_str)}")
        lines.append("")
        lines.append(b(" Overview"))
        lines.append(bq(overview, expandable=True))
        return "\n".join(str(l) for l in lines if l is not None)

    @staticmethod
    def format_tv_caption(data: Dict, template: Optional[str] = None) -> str:
        name = e(data.get("name") or "Unknown")
        original_name = e(data.get("original_name") or "")
        tagline = e(data.get("tagline") or "")
        first_air = e(data.get("first_air_date") or "Unknown")
        last_air = e(data.get("last_air_date") or "Unknown")
        status = e(data.get("status") or "Unknown")
        seasons = data.get("number_of_seasons", "?")
        episodes = data.get("number_of_episodes", "?")
        rating = data.get("vote_average", 0)
        vote_count = data.get("vote_count", 0)
        language = e(data.get("original_language") or "N/A").upper()
        genres = [g["name"] for g in data.get("genres", []) or []]
        genres_str = " • ".join(genres[:5]) if genres else "N/A"
        overview = e(truncate(data.get("overview") or "No overview.", 300))
        networks = [n["name"] for n in (data.get("networks") or [])[:3]]
        network_str = e(", ".join(networks)) if networks else "N/A"

        credits = data.get("credits", {}) or {}
        cast = credits.get("cast", []) or []
        top_cast = ", ".join(e(c["name"]) for c in cast[:5]) if cast else "N/A"
        creators = [c.get("name") for c in (data.get("created_by") or [])]
        creators_str = e(", ".join(creators[:2])) if creators else "N/A"

        if template:
            for key, val in {
                "{title}": name, "{name}": name,
                "{first_air_date}": first_air, "{status}": status,
                "{seasons}": str(seasons), "{episodes}": str(episodes),
                "{rating}": str(rating), "{genres}": e(genres_str),
                "{overview}": overview, "{network}": network_str,
            }.items():
                template = template.replace(key, val)
            return template

        lines = [b(name)]
        if original_name and original_name != name:
            lines.append(f"<i>{original_name}</i>")
        if tagline:
            lines.append(f"<i>❝{tagline}❞</i>")
        lines.append("")
        lines += [
            f"<b> Aired:</b> {code(first_air + ' → ' + last_air)}",
            f"<b> Status:</b> {code(status)}",
            f"<b> Seasons:</b> {code(str(seasons))} | <b>Episodes:</b> {code(str(episodes))}",
            f"<b> Rating:</b> {code(f'{rating:.1f}/10 ({format_number(vote_count)} votes)')}",
            f"<b> Language:</b> {code(language)}",
            f"<b> Genres:</b> {e(genres_str)}",
            f"<b> Network:</b> {network_str}",
            f"<b> Created by:</b> {creators_str}",
            f"<b> Cast:</b> {top_cast}",
        ]
        lines.append("")
        lines.append(b(" Overview"))
        lines.append(bq(overview, expandable=True))
        return "\n".join(str(l) for l in lines if l is not None)
