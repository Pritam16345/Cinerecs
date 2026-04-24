"""
CineRecs — TMDB API service.
Handles all interactions with The Movie Database API.
Includes rate limiting (40 req / 10 sec) and response parsing.
"""

import os
import time
import asyncio
import logging
from datetime import date

import httpx

logger = logging.getLogger("cinerecs.tmdb")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
FALLBACK_POSTER = "https://placehold.co/500x750/1a1a2e/ffffff?text=No+Poster"

TMDB_GENRE_MAP = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western"
}

async def _tmdb_get(endpoint: str, params: dict = None, timeout: float = 10.0) -> dict | None:
    """
    Make a GET request to the TMDB API.
    Returns parsed JSON or None on failure.
    """

    url = f"{TMDB_BASE_URL}{endpoint}"
    default_params = {"api_key": TMDB_API_KEY}
    if params:
        default_params.update(params)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=default_params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"TMDB API error {e.response.status_code} for {endpoint}")
        return None
    except Exception as e:
        logger.warning(f"TMDB request failed for {endpoint}: {e}")
        return None


def _parse_movie(data: dict) -> dict:
    """Parse a TMDB movie response into our internal format."""
    # Extract genres
    genres = []
    if "genres" in data:
        genres = [g["name"] for g in data.get("genres", [])]
    elif "genre_ids" in data:
        for gid in data.get("genre_ids", []):
            if gid in TMDB_GENRE_MAP:
                genres.append(TMDB_GENRE_MAP[gid])
            else:
                genres.append(str(gid))

    # Extract cast and director from credits
    cast_list = []
    director = None
    credits = data.get("credits", {})
    if credits:
        for person in credits.get("cast", [])[:10]:
            cast_list.append(person.get("name", ""))
        for person in credits.get("crew", []):
            if person.get("job") == "Director":
                director = person.get("name", "")
                break

    # Parse release date
    release_date = None
    rd_str = data.get("release_date", "")
    if rd_str:
        try:
            release_date = date.fromisoformat(rd_str)
        except ValueError:
            pass

    # Poster URL
    poster_path = data.get("poster_path")
    poster_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else FALLBACK_POSTER

    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Untitled"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "cast": cast_list,
        "director": director,
        "release_date": release_date,
        "rating": float(data.get("vote_average", 0)),
        "popularity": float(data.get("popularity", 0)),
        "poster_url": poster_url,
        "language": data.get("original_language", "en"),
    }


# ── Public API Methods ─────────────────────────────────────

async def get_trending(page: int = 1) -> list[dict]:
    """Fetch trending movies from TMDB (day window)."""
    data = await _tmdb_get("/trending/movie/day", {"page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def get_movie_details(tmdb_id: int) -> dict | None:
    """Fetch full movie details including credits and keywords."""
    data = await _tmdb_get(
        f"/movie/{tmdb_id}",
        {"append_to_response": "credits,keywords"},
    )
    if not data:
        return None
    return _parse_movie(data)


async def search_tmdb_movies(query: str, page: int = 1) -> list[dict]:
    """Search TMDB for movies by title."""
    data = await _tmdb_get("/search/movie", {"query": query, "page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def get_movie_changes(start_date: str = None, end_date: str = None) -> list[int]:
    """
    Get list of movie IDs that have been changed recently.
    Used by daily sync to identify which movies need updating.
    """
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    data = await _tmdb_get("/movie/changes", params)
    if not data:
        return []

    movie_ids = []
    for item in data.get("results", []):
        mid = item.get("id")
        if mid:
            movie_ids.append(mid)
    return movie_ids


async def get_popular_movies(page: int = 1) -> list[dict]:
    """Fetch popular movies from TMDB."""
    data = await _tmdb_get("/movie/popular", {"page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def get_top_rated_movies(page: int = 1) -> list[dict]:
    """Fetch top-rated movies from TMDB."""
    data = await _tmdb_get("/movie/top_rated", {"page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def get_now_playing(page: int = 1) -> list[dict]:
    """Fetch now-playing movies from TMDB."""
    data = await _tmdb_get("/movie/now_playing", {"page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def get_upcoming(page: int = 1) -> list[dict]:
    """Fetch upcoming movies from TMDB."""
    data = await _tmdb_get("/movie/upcoming", {"page": str(page)})
    if not data:
        return []
    return [_parse_movie(m) for m in data.get("results", [])]


async def discover_movies(page: int = 1, sort_by: str = "popularity.desc") -> tuple[list[dict], int]:
    """
    Discover movies with pagination. Returns (movies, total_pages).
    Used by historical import to paginate through all movies.
    """
    data = await _tmdb_get("/discover/movie", {
        "page": str(page),
        "sort_by": sort_by,
        "vote_count.gte": "10",
    })
    if not data:
        return [], 0

    total_pages = data.get("total_pages", 0)
    movies = [_parse_movie(m) for m in data.get("results", [])]
    return movies, total_pages
