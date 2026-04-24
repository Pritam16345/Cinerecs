"""
CineRecs — Collaborative filtering service.
Implements user-based collaborative filtering from the ratings table.
"""

import logging
from database import (
    get_user_liked_movies,
    get_similar_users,
    get_movies_liked_by_users,
)

logger = logging.getLogger("cinerecs.collab")


async def get_collaborative_recommendations(
    pool, user_id: str, limit: int = 10
) -> list[dict]:
    """
    Generate collaborative filtering recommendations for a user.

    Algorithm:
    1. Find all movies the user rated >= 4
    2. Find other users who rated those same movies >= 4
    3. Get movies those similar users liked that the current user hasn't seen
    4. Score by frequency (how many similar users liked it) and average rating

    Args:
        pool: asyncpg connection pool.
        user_id: UUID of the target user.
        limit: Number of recommendations to return.

    Returns:
        List of dicts with movie info and collaborative score.
    """
    # Step 1: Get movies this user likes
    liked_movie_ids = await get_user_liked_movies(pool, user_id, min_rating=4.0)

    if not liked_movie_ids:
        logger.info(f"User {user_id} has no highly-rated movies for collab filtering")
        return []

    # Step 2: Find similar users
    similar_user_rows = await get_similar_users(
        pool, liked_movie_ids, exclude_user_id=user_id, min_rating=4.0
    )

    if not similar_user_rows:
        logger.info(f"No similar users found for user {user_id}")
        return []

    similar_user_ids = [str(row["user_id"]) for row in similar_user_rows]
    logger.info(f"Found {len(similar_user_ids)} similar users for user {user_id}")

    # Step 3: Get movies liked by similar users that this user hasn't seen
    recommendations = await get_movies_liked_by_users(
        pool,
        user_ids=similar_user_ids,
        exclude_movie_ids=liked_movie_ids,
        min_rating=4.0,
        limit=limit * 2,  # Fetch extra for scoring/filtering
    )

    # Step 4: Score and rank
    results = []
    max_freq = max((r["freq"] for r in recommendations), default=1)

    for row in recommendations:
        freq = int(row["freq"])
        avg_rat = float(row["avg_rating"])

        # Normalize frequency score to 0-1
        freq_score = freq / max_freq if max_freq > 0 else 0
        # Normalize rating score to 0-1 (ratings are 1-5)
        rating_score = (avg_rat - 1) / 4.0

        # Combined collaborative score
        collab_score = 0.6 * freq_score + 0.4 * rating_score

        results.append({
            "tmdb_id": row["movie_id"],
            "title": row["title"],
            "poster_url": row.get("poster_url"),
            "genres": list(row.get("genres") or []),
            "rating": float(row.get("tmdb_rating") or 0),
            "popularity": float(row.get("popularity") or 0),
            "score": round(collab_score, 4),
            "freq": freq,
            "avg_user_rating": round(avg_rat, 2),
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
