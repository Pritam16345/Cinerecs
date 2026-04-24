"""
CineRecs — Database Layer.
Async connection pool via asyncpg.
"""

import os
import logging
import asyncpg

logger = logging.getLogger("cinerecs.database")

_pool: asyncpg.Pool | None = None
DATABASE_URL = os.getenv("DATABASE_URL", "")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    tmdb_id INT PRIMARY KEY,
    title TEXT NOT NULL,
    overview TEXT,
    genres TEXT[],
    "cast" TEXT[],
    director TEXT,
    release_date DATE,
    rating FLOAT DEFAULT 0,
    popularity FLOAT DEFAULT 0,
    poster_url TEXT,
    language TEXT,
    embedding_idx INT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    movie_id INT REFERENCES movies(tmdb_id) ON DELETE CASCADE,
    rating FLOAT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, movie_id)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    movie_id INT REFERENCES movies(tmdb_id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, movie_id)
);

CREATE INDEX IF NOT EXISTS idx_movies_title ON movies USING btree (lower(title));
CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings (user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_movie ON ratings (movie_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist (user_id);
"""


async def get_pool() -> asyncpg.Pool:
    """Singleton connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def initialize_schema() -> None:
    """Setup tables and indexes."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Schema initialized")


async def close_pool() -> None:
    """Shutdown connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ── Movie Queries ──────────────────────────────────────────

async def get_movie_by_id(pool: asyncpg.Pool, tmdb_id: int):
    """Fetch movie by TMDB ID."""
    return await pool.fetchrow("SELECT * FROM movies WHERE tmdb_id = $1", tmdb_id)


async def search_movies_by_title(pool: asyncpg.Pool, query: str, limit: int = 20):
    """Title search using ILIKE."""
    return await pool.fetch(
        """
        SELECT tmdb_id, title, overview, genres, "cast", director,
               release_date, rating, popularity, poster_url, language
        FROM movies
        WHERE lower(title) LIKE '%' || lower($1) || '%'
        ORDER BY popularity DESC
        LIMIT $2
        """,
        query, limit,
    )


async def get_movie_suggestions(pool: asyncpg.Pool, query: str, limit: int = 5):
    """Prefix-matching for autocomplete."""
    # Prefix search
    results = await pool.fetch(
        """
        SELECT tmdb_id, title, poster_url, rating, release_date
        FROM movies
        WHERE lower(title) LIKE lower($1) || '%'
        ORDER BY popularity DESC
        LIMIT $2
        """,
        query, limit,
    )
    
    # Fill remaining with contains search
    if len(results) < limit:
        remaining = limit - len(results)
        exclude_ids = [r["tmdb_id"] for r in results]
        more_results = await pool.fetch(
            """
            SELECT tmdb_id, title, poster_url, rating, release_date
            FROM movies
            WHERE lower(title) LIKE '%' || lower($1) || '%'
              AND tmdb_id != ALL($2::int[])
            ORDER BY popularity DESC
            LIMIT $3
            """,
            query, exclude_ids, remaining,
        )
        results = list(results) + list(more_results)
    return results


async def get_movies_by_ids(pool: asyncpg.Pool, tmdb_ids: list[int]):
    """Fetch movies by multiple IDs."""
    if not tmdb_ids: return []
    return await pool.fetch(
        """
        SELECT tmdb_id, title, overview, genres, "cast", director,
               release_date, rating, popularity, poster_url, language
        FROM movies
        WHERE tmdb_id = ANY($1::int[])
        ORDER BY popularity DESC
        """,
        tmdb_ids,
    )


async def upsert_movie(pool: asyncpg.Pool, movie: dict) -> None:
    """Save or update movie."""
    await pool.execute(
        """
        INSERT INTO movies (tmdb_id, title, overview, genres, "cast", director,
                            release_date, rating, popularity, poster_url, language,
                            embedding_idx, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, now())
        ON CONFLICT (tmdb_id) DO UPDATE SET
            title = EXCLUDED.title,
            overview = COALESCE(EXCLUDED.overview, movies.overview),
            genres = COALESCE(EXCLUDED.genres, movies.genres),
            "cast" = COALESCE(EXCLUDED."cast", movies."cast"),
            director = COALESCE(EXCLUDED.director, movies.director),
            release_date = COALESCE(EXCLUDED.release_date, movies.release_date),
            rating = COALESCE(EXCLUDED.rating, movies.rating),
            popularity = COALESCE(EXCLUDED.popularity, movies.popularity),
            poster_url = COALESCE(EXCLUDED.poster_url, movies.poster_url),
            language = COALESCE(EXCLUDED.language, movies.language),
            embedding_idx = COALESCE(EXCLUDED.embedding_idx, movies.embedding_idx),
            updated_at = now()
        """,
        movie.get("tmdb_id"), movie.get("title"), movie.get("overview"),
        movie.get("genres", []), movie.get("cast", []), movie.get("director"),
        movie.get("release_date"), movie.get("rating", 0.0), movie.get("popularity", 0.0),
        movie.get("poster_url"), movie.get("language"), movie.get("embedding_idx"),
    )


async def batch_upsert_movies(pool: asyncpg.Pool, movies: list[dict]) -> int:
    """Batch save movies."""
    count = 0
    async with pool.acquire() as conn:
        for movie in movies:
            await conn.execute(
                """
                INSERT INTO movies (tmdb_id, title, overview, genres, "cast", director,
                                    release_date, rating, popularity, poster_url, language,
                                    embedding_idx, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, now())
                ON CONFLICT (tmdb_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    overview = COALESCE(EXCLUDED.overview, movies.overview),
                    genres = COALESCE(EXCLUDED.genres, movies.genres),
                    "cast" = COALESCE(EXCLUDED."cast", movies."cast"),
                    director = COALESCE(EXCLUDED.director, movies.director),
                    release_date = COALESCE(EXCLUDED.release_date, movies.release_date),
                    rating = COALESCE(EXCLUDED.rating, movies.rating),
                    popularity = COALESCE(EXCLUDED.popularity, movies.popularity),
                    poster_url = COALESCE(EXCLUDED.poster_url, movies.poster_url),
                    language = COALESCE(EXCLUDED.language, movies.language),
                    embedding_idx = COALESCE(EXCLUDED.embedding_idx, movies.embedding_idx),
                    updated_at = now()
                """,
                movie.get("tmdb_id"), movie.get("title"), movie.get("overview"),
                movie.get("genres", []), movie.get("cast", []), movie.get("director"),
                movie.get("release_date"), movie.get("rating", 0.0), movie.get("popularity", 0.0),
                movie.get("poster_url"), movie.get("language"), movie.get("embedding_idx"),
            )
            count += 1
    return count


async def get_all_movies_for_embedding(pool: asyncpg.Pool):
    """Fetch movie data for vector indexing."""
    return await pool.fetch("SELECT tmdb_id, title, overview, genres, \"cast\" FROM movies ORDER BY tmdb_id")


# ── User Queries ───────────────────────────────────────────

async def get_user_by_email(pool: asyncpg.Pool, email: str):
    """Fetch user by email."""
    return await pool.fetchrow("SELECT * FROM users WHERE email = $1", email)


async def get_user_by_id(pool: asyncpg.Pool, user_id: str):
    """Fetch user by UUID."""
    return await pool.fetchrow("SELECT * FROM users WHERE id = $1::uuid", user_id)


async def create_user(pool: asyncpg.Pool, email: str, password_hash: str):
    """Register new user."""
    return await pool.fetchrow(
        "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email, created_at",
        email, password_hash,
    )


# ── Rating Queries ─────────────────────────────────────────

async def get_user_ratings(pool: asyncpg.Pool, user_id: str):
    """Get all user ratings with movie info."""
    return await pool.fetch(
        """
        SELECT r.id, r.movie_id, r.rating, r.created_at,
               m.title, m.poster_url, m.genres
        FROM ratings r
        JOIN movies m ON r.movie_id = m.tmdb_id
        WHERE r.user_id = $1::uuid
        ORDER BY r.created_at DESC
        """,
        user_id,
    )


async def upsert_rating(pool: asyncpg.Pool, user_id: str, movie_id: int, rating: float):
    """Submit/update rating."""
    return await pool.fetchrow(
        """
        INSERT INTO ratings (user_id, movie_id, rating)
        VALUES ($1::uuid, $2, $3)
        ON CONFLICT (user_id, movie_id) DO UPDATE SET
            rating = EXCLUDED.rating,
            created_at = now()
        RETURNING id, user_id, movie_id, rating, created_at
        """,
        user_id, movie_id, rating,
    )


async def get_user_rating_stats(pool: asyncpg.Pool, user_id: str):
    """Get aggregate rating stats."""
    return await pool.fetchrow(
        """
        SELECT
            COUNT(*) as total_rated,
            ROUND(AVG(rating)::numeric, 2) as avg_rating,
            (SELECT unnest(m.genres) AS g
             FROM ratings r2
             JOIN movies m ON r2.movie_id = m.tmdb_id
             WHERE r2.user_id = $1::uuid
             GROUP BY g
             ORDER BY COUNT(*) DESC
             LIMIT 1) as top_genre
        FROM ratings
        WHERE user_id = $1::uuid
        """,
        user_id,
    )


# ── Collaborative Filtering Queries ───────────────────────

async def get_user_liked_movies(pool: asyncpg.Pool, user_id: str, min_rating: float = 4.0):
    """Get movie IDs rated highly by user."""
    rows = await pool.fetch("SELECT movie_id FROM ratings WHERE user_id = $1::uuid AND rating >= $2", user_id, min_rating)
    return [row["movie_id"] for row in rows]


async def get_similar_users(pool: asyncpg.Pool, movie_ids: list[int], exclude_user_id: str, min_rating: float = 4.0):
    """Find users with similar tastes."""
    if not movie_ids: return []
    return await pool.fetch(
        """
        SELECT DISTINCT user_id FROM ratings
        WHERE movie_id = ANY($1::int[]) AND rating >= $2 AND user_id != $3::uuid
        """,
        movie_ids, min_rating, exclude_user_id,
    )


async def get_movies_liked_by_users(pool: asyncpg.Pool, user_ids: list[str], exclude_movie_ids: list[int], min_rating: float = 4.0, limit: int = 50):
    """Get movies liked by similar users."""
    if not user_ids: return []
    return await pool.fetch(
        """
        SELECT r.movie_id, COUNT(*) as freq, AVG(r.rating) as avg_rating,
               m.title, m.poster_url, m.genres, m.rating as tmdb_rating, m.popularity
        FROM ratings r
        JOIN movies m ON r.movie_id = m.tmdb_id
        WHERE r.user_id = ANY($1::uuid[]) AND r.rating >= $2 AND r.movie_id != ALL($3::int[])
        GROUP BY r.movie_id, m.title, m.poster_url, m.genres, m.rating, m.popularity
        ORDER BY freq DESC, avg_rating DESC
        LIMIT $4
        """,
        [str(uid) for uid in user_ids], min_rating, exclude_movie_ids, limit,
    )


# ── Watchlist Queries ──────────────────────────────────────

async def get_user_watchlist(pool: asyncpg.Pool, user_id: str):
    """Get user watchlist with movie info."""
    return await pool.fetch(
        """
        SELECT w.id, w.movie_id, w.added_at,
               m.title, m.poster_url, m.genres, m.rating, m.overview
        FROM watchlist w
        JOIN movies m ON w.movie_id = m.tmdb_id
        WHERE w.user_id = $1::uuid
        ORDER BY w.added_at DESC
        """,
        user_id,
    )


async def add_to_watchlist(pool: asyncpg.Pool, user_id: str, movie_id: int):
    """Add movie to watchlist."""
    return await pool.fetchrow(
        "INSERT INTO watchlist (user_id, movie_id) VALUES ($1::uuid, $2) ON CONFLICT (user_id, movie_id) DO NOTHING RETURNING id, user_id, movie_id, added_at",
        user_id, movie_id,
    )


async def remove_from_watchlist(pool: asyncpg.Pool, user_id: str, movie_id: int):
    """Remove movie from watchlist."""
    result = await pool.execute("DELETE FROM watchlist WHERE user_id = $1::uuid AND movie_id = $2", user_id, movie_id)
    return result == "DELETE 1"
