"""
CineRecs — Movie Routes.
Endpoints for discovery and search.
"""

import logging
from fastapi import APIRouter, Query, HTTPException

from database import get_pool, get_movie_by_id, search_movies_by_title, get_movies_by_ids, get_movie_suggestions
from models import MovieOut, MovieDetail, SearchResponse
from services.redis_service import get_cached, set_cached
from services.tmdb_service import get_trending as tmdb_trending
from services.faiss_service import FAISSService

logger = logging.getLogger("cinerecs.routes.movies")
router = APIRouter(prefix="/movies", tags=["movies"])

_faiss: FAISSService | None = None


def set_faiss_service(service: FAISSService):
    """Inject FAISS service."""
    global _faiss
    _faiss = service


@router.get("/trending", response_model=list[MovieOut])
async def trending_movies():
    """Get trending movies (cached 1hr)."""
    cache_key = "movies:trending:v3"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    movies = await tmdb_trending(page=1)
    if movies:
        await set_cached(cache_key, movies, ttl=3600)
    return movies


@router.get("/search", response_model=SearchResponse)
async def search_movies(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search movies by title (ILIKE)."""
    pool = await get_pool()
    rows = await search_movies_by_title(pool, q, limit=limit)

    results = []
    for row in rows:
        results.append(MovieOut(
            tmdb_id=row["tmdb_id"],
            title=row["title"],
            poster_url=row.get("poster_url"),
            genres=list(row.get("genres") or []),
            rating=float(row.get("rating") or 0),
            popularity=float(row.get("popularity") or 0),
            language=row.get("language"),
            release_date=row.get("release_date"),
        ))
    return SearchResponse(results=results, count=len(results), query=q)


@router.get("/autocomplete")
async def autocomplete_movies(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(5, ge=1, le=10),
):
    """Suggestions for autocomplete."""
    pool = await get_pool()
    rows = await get_movie_suggestions(pool, q, limit=limit)
    
    results = []
    for row in rows:
        results.append({
            "tmdb_id": row["tmdb_id"],
            "title": row["title"],
            "poster_url": row.get("poster_url"),
            "rating": float(row.get("rating") or 0),
            "year": row["release_date"].year if row.get("release_date") else None,
        })
    return results


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., min_length=1, max_length=500, description="Semantic search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Vector similarity search via FAISS (cached 15min)."""
    if _faiss is None or not _faiss.is_loaded():
        raise HTTPException(status_code=503, detail="Semantic search unavailable")

    cache_key = f"semantic:{q.lower().strip()}:{limit}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return {"results": cached, "count": len(cached), "query": q, "cached": True}

    # FAISS search
    faiss_results = _faiss.search(q, top_k=limit)
    if not faiss_results:
        return {"results": [], "count": 0, "query": q, "cached": False}

    # Fetch movie details
    tmdb_ids = [r["tmdb_id"] for r in faiss_results]
    pool = await get_pool()
    movies = await get_movies_by_ids(pool, tmdb_ids)

    # Build response
    score_map = {r["tmdb_id"]: r["score"] for r in faiss_results}
    results = []
    for movie in movies:
        results.append({
            "tmdb_id": movie["tmdb_id"],
            "title": movie["title"],
            "poster_url": movie.get("poster_url"),
            "genres": list(movie.get("genres") or []),
            "rating": float(movie.get("rating") or 0),
            "popularity": float(movie.get("popularity") or 0),
            "language": movie.get("language"),
            "score": score_map.get(movie["tmdb_id"], 0),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    await set_cached(cache_key, results, ttl=900)
    return {"results": results, "count": len(results), "query": q, "cached": False}


@router.get("/{tmdb_id}", response_model=MovieDetail)
async def get_movie_detail(tmdb_id: int):
    """Fetch full movie details."""
    pool = await get_pool()
    movie = await get_movie_by_id(pool, tmdb_id)

    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    return MovieDetail(
        tmdb_id=movie["tmdb_id"],
        title=movie["title"],
        overview=movie.get("overview"),
        genres=list(movie.get("genres") or []),
        cast=list(movie.get("cast") or []),
        director=movie.get("director"),
        release_date=movie.get("release_date"),
        rating=float(movie.get("rating") or 0),
        popularity=float(movie.get("popularity") or 0),
        poster_url=movie.get("poster_url"),
        language=movie.get("language"),
    )
