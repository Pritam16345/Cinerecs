"""
CineRecs — Watchlist routes.
Authenticated endpoints for managing a user's movie watchlist.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

from database import get_pool, get_user_watchlist, add_to_watchlist, remove_from_watchlist, get_movie_by_id
from models import WatchlistAdd, WatchlistItem
from auth import get_current_user
from services.redis_service import invalidate_pattern

logger = logging.getLogger("cinerecs.routes.watchlist")

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItem])
async def get_watchlist(user: dict = Depends(get_current_user)):
    """
    Get the authenticated user's watchlist with movie details.
    Returns items sorted by most recently added first.
    """
    pool = await get_pool()
    rows = await get_user_watchlist(pool, user["user_id"])

    return [
        WatchlistItem(
            id=str(row["id"]),
            movie_id=row["movie_id"],
            added_at=row["added_at"],
            title=row.get("title"),
            poster_url=row.get("poster_url"),
            genres=list(row.get("genres") or []),
            rating=float(row.get("rating") or 0),
            overview=row.get("overview"),
        )
        for row in rows
    ]


@router.post("", response_model=WatchlistItem)
async def add_movie_to_watchlist(data: WatchlistAdd, user: dict = Depends(get_current_user)):
    """
    Add a movie to the authenticated user's watchlist.
    If the movie is already in the watchlist, returns the existing entry.
    """
    pool = await get_pool()

    # Verify movie exists
    movie = await get_movie_by_id(pool, data.movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    row = await add_to_watchlist(pool, user["user_id"], data.movie_id)

    if row is None:
        # Already in watchlist — return existing
        raise HTTPException(status_code=409, detail="Movie already in watchlist")

    # Invalidate user recommendations cache
    await invalidate_pattern(f"rec:user:{user['user_id']}:*")

    return WatchlistItem(
        id=str(row["id"]),
        movie_id=row["movie_id"],
        added_at=row["added_at"],
        title=movie["title"],
        poster_url=movie.get("poster_url"),
        genres=list(movie.get("genres") or []),
        rating=float(movie.get("rating") or 0),
        overview=movie.get("overview"),
    )


@router.delete("/{movie_id}")
async def remove_movie_from_watchlist(movie_id: int, user: dict = Depends(get_current_user)):
    """
    Remove a movie from the authenticated user's watchlist.
    """
    pool = await get_pool()
    removed = await remove_from_watchlist(pool, user["user_id"], movie_id)

    if not removed:
        raise HTTPException(status_code=404, detail="Movie not in watchlist")

    # Invalidate user recommendations cache
    await invalidate_pattern(f"rec:user:{user['user_id']}:*")

    return {"message": "Removed from watchlist", "movie_id": movie_id}
