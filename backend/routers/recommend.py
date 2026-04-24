"""
CineRecs — Recommendation routes.
Content-based (FAISS), collaborative filtering, and hybrid recommendations.
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from database import get_pool, get_movie_by_id, get_movies_by_ids
from models import RecommendationItem, RecommendationResponse
from services.redis_service import get_cached, set_cached
from services.faiss_service import FAISSService
from services.collab_service import get_collaborative_recommendations

logger = logging.getLogger("cinerecs.routes.recommend")

router = APIRouter(prefix="/recommend", tags=["recommendations"])

# FAISS service reference — set by main.py
_faiss: FAISSService | None = None


def set_faiss_service(service: FAISSService):
    """Set the FAISS service instance (called from main.py)."""
    global _faiss
    _faiss = service


@router.get("/similar/{tmdb_id}", response_model=RecommendationResponse)
async def get_similar_movies(tmdb_id: int, limit: int = Query(10, ge=1, le=50)):
    """
    Content-based recommendations using FAISS vector similarity.
    Returns top N movies most similar to the given movie.
    Cached for 1 hour.
    """
    cache_key = f"rec:similar:{tmdb_id}:{limit}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return RecommendationResponse(
            recommendations=[RecommendationItem(**r) for r in cached],
            source="content",
            cached=True,
        )

    if _faiss is None or not _faiss.is_loaded():
        raise HTTPException(status_code=503, detail="Recommendation engine not available")

    # Verify movie exists
    pool = await get_pool()
    movie = await get_movie_by_id(pool, tmdb_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    # FAISS similarity search
    faiss_results = _faiss.get_similar_by_id(tmdb_id, top_k=limit)

    if not faiss_results:
        return RecommendationResponse(recommendations=[], source="content", cached=False)

    # Fetch full movie details
    result_ids = [r["tmdb_id"] for r in faiss_results]
    movies = await get_movies_by_ids(pool, result_ids)

    score_map = {r["tmdb_id"]: r["score"] for r in faiss_results}

    recommendations = []
    for m in movies:
        recommendations.append(RecommendationItem(
            tmdb_id=m["tmdb_id"],
            title=m["title"],
            poster_url=m.get("poster_url"),
            genres=list(m.get("genres") or []),
            rating=float(m.get("rating") or 0),
            popularity=float(m.get("popularity") or 0),
            score=score_map.get(m["tmdb_id"], 0),
        ))

    recommendations.sort(key=lambda x: x.score, reverse=True)

    # Cache for 1 hour
    cache_data = [r.model_dump() for r in recommendations]
    await set_cached(cache_key, cache_data, ttl=3600)

    return RecommendationResponse(
        recommendations=recommendations, source="content", cached=False
    )


@router.get("/user/{user_id}", response_model=RecommendationResponse)
async def get_user_recommendations(user_id: str, limit: int = Query(10, ge=1, le=50)):
    """
    Collaborative filtering recommendations based on user's ratings.
    Cached for 1 hour.
    """
    cache_key = f"rec:user:{user_id}:{limit}:v2"
    cached = await get_cached(cache_key)
    if cached is not None:
        return RecommendationResponse(
            recommendations=[RecommendationItem(**r) for r in cached],
            source="collaborative",
            cached=True,
        )

    pool = await get_pool()
    results = await get_collaborative_recommendations(pool, user_id, limit=limit)

    # Fallback to content-based if no collaborative results (Cold Start)
    if not results and _faiss is not None and _faiss.is_loaded():
        seed_movie = await pool.fetchrow(
            """
            SELECT movie_id as tmdb_id FROM (
                SELECT movie_id, added_at as created_at FROM watchlist WHERE user_id = $1::uuid
                UNION ALL
                SELECT movie_id, created_at FROM ratings WHERE user_id = $1::uuid
            ) combined
            ORDER BY created_at DESC LIMIT 1
            """,
            user_id
        )
        if seed_movie:
            faiss_results = _faiss.get_similar_by_id(seed_movie["tmdb_id"], top_k=limit)
            if faiss_results:
                result_ids = [r["tmdb_id"] for r in faiss_results]
                movies = await get_movies_by_ids(pool, result_ids)
                score_map = {r["tmdb_id"]: r["score"] for r in faiss_results}
                for m in movies:
                    results.append({
                        "tmdb_id": m["tmdb_id"],
                        "title": m["title"],
                        "poster_url": m.get("poster_url"),
                        "genres": list(m.get("genres") or []),
                        "rating": float(m.get("rating") or 0),
                        "popularity": float(m.get("popularity") or 0),
                        "score": score_map.get(m["tmdb_id"], 0)
                    })
                results.sort(key=lambda x: x["score"], reverse=True)

    recommendations = [
        RecommendationItem(
            tmdb_id=r["tmdb_id"],
            title=r["title"],
            poster_url=r.get("poster_url"),
            genres=r.get("genres", []),
            rating=r.get("rating", 0),
            popularity=r.get("popularity", 0),
            score=r.get("score", 0),
        )
        for r in results
    ]

    # Cache for 1 hour only if we have recommendations
    if recommendations:
        cache_data = [r.model_dump() for r in recommendations]
        await set_cached(cache_key, cache_data, ttl=3600)

    return RecommendationResponse(
        recommendations=recommendations, source="collaborative", cached=False
    )


@router.get("/hybrid/{movie_id}/{user_id}", response_model=RecommendationResponse)
async def get_hybrid_recommendations(
    movie_id: int,
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
):
    """
    Hybrid recommendations: 0.6 content-based + 0.4 collaborative.
    Cached for 1 hour.
    """
    cache_key = f"rec:hybrid:{movie_id}:{user_id}:{limit}:v2"
    cached = await get_cached(cache_key)
    if cached is not None:
        return RecommendationResponse(
            recommendations=[RecommendationItem(**r) for r in cached],
            source="hybrid",
            cached=True,
        )

    pool = await get_pool()

    # Get content-based scores
    content_scores = {}
    if _faiss is not None and _faiss.is_loaded():
        faiss_results = _faiss.get_similar_by_id(movie_id, top_k=limit * 3)
        for r in faiss_results:
            content_scores[r["tmdb_id"]] = r["score"]

    # Get collaborative scores
    collab_scores = {}
    try:
        collab_results = await get_collaborative_recommendations(pool, user_id, limit=limit * 3)
        for r in collab_results:
            collab_scores[r["tmdb_id"]] = r["score"]
    except Exception as e:
        logger.warning(f"Collaborative filtering failed for user {user_id}: {e}")

    # Merge scores: 0.6 content + 0.4 collaborative
    all_ids = set(list(content_scores.keys()) + list(collab_scores.keys()))
    merged = {}
    for tid in all_ids:
        c_score = content_scores.get(tid, 0)
        col_score = collab_scores.get(tid, 0)
        merged[tid] = 0.6 * c_score + 0.4 * col_score

    # Sort by hybrid score
    sorted_ids = sorted(merged.keys(), key=lambda x: merged[x], reverse=True)[:limit]

    if not sorted_ids:
        return RecommendationResponse(recommendations=[], source="hybrid", cached=False)

    # Fetch movie details
    movies = await get_movies_by_ids(pool, sorted_ids)
    movie_map = {m["tmdb_id"]: m for m in movies}

    recommendations = []
    for tid in sorted_ids:
        m = movie_map.get(tid)
        if m is None:
            continue
        recommendations.append(RecommendationItem(
            tmdb_id=tid,
            title=m["title"],
            poster_url=m.get("poster_url"),
            genres=list(m.get("genres") or []),
            rating=float(m.get("rating") or 0),
            popularity=float(m.get("popularity") or 0),
            score=round(merged[tid], 4),
        ))

    # Cache for 1 hour
    cache_data = [r.model_dump() for r in recommendations]
    await set_cached(cache_key, cache_data, ttl=3600)

    return RecommendationResponse(
        recommendations=recommendations, source="hybrid", cached=False
    )
