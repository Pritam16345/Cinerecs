"""
CineRecs — Rating routes.
Authenticated endpoints for submitting and viewing movie ratings.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from database import get_pool, get_user_ratings, upsert_rating, get_user_rating_stats, get_movie_by_id
from models import RatingCreate, RatingOut, RatingStatsOut
from auth import get_current_user
from services.redis_service import invalidate_pattern

logger = logging.getLogger("cinerecs.routes.ratings")

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.get("", response_model=list[RatingOut])
async def get_ratings(user: dict = Depends(get_current_user)):
    """
    Get all ratings for the authenticated user.
    Returns ratings sorted by most recent first.
    """
    pool = await get_pool()
    rows = await get_user_ratings(pool, user["user_id"])

    return [
        RatingOut(
            id=str(row["id"]),
            movie_id=row["movie_id"],
            rating=float(row["rating"]),
            created_at=row["created_at"],
            title=row.get("title"),
            poster_url=row.get("poster_url"),
            genres=list(row.get("genres") or []),
        )
        for row in rows
    ]


@router.post("", response_model=RatingOut)
async def submit_rating(data: RatingCreate, user: dict = Depends(get_current_user)):
    """
    Submit or update a movie rating (1-5 stars).
    Invalidates recommendation cache for this user.
    """
    pool = await get_pool()

    # Verify movie exists
    movie = await get_movie_by_id(pool, data.movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    # Upsert rating
    row = await upsert_rating(pool, user["user_id"], data.movie_id, data.rating)

    # Invalidate cached recommendations so new rating is reflected
    await invalidate_pattern(f"rec:user:{user['user_id']}:*")
    await invalidate_pattern(f"rec:hybrid:*:{user['user_id']}:*")

    return RatingOut(
        id=str(row["id"]),
        movie_id=row["movie_id"],
        rating=float(row["rating"]),
        created_at=row["created_at"],
        title=movie["title"],
        poster_url=movie.get("poster_url"),
        genres=list(movie.get("genres") or []),
    )


@router.get("/stats", response_model=RatingStatsOut)
async def get_stats(user: dict = Depends(get_current_user)):
    """
    Get rating statistics for the authenticated user.
    Returns total rated, average rating, and top genre.
    """
    pool = await get_pool()
    stats = await get_user_rating_stats(pool, user["user_id"])

    if stats is None:
        return RatingStatsOut(total_rated=0, avg_rating=0, top_genre=None)

    return RatingStatsOut(
        total_rated=int(stats.get("total_rated") or 0),
        avg_rating=float(stats.get("avg_rating") or 0),
        top_genre=stats.get("top_genre"),
    )
