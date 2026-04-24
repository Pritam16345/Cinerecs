"""
CineRecs — Pydantic models for API request/response validation.
"""

from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


# ── Auth ───────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


# ── Movies ─────────────────────────────────────────────────

class MovieOut(BaseModel):
    tmdb_id: int
    title: str
    poster_url: str | None = None
    genres: list[str] = []
    rating: float = 0
    popularity: float = 0
    language: str | None = None
    release_date: date | None = None


class MovieDetail(BaseModel):
    tmdb_id: int
    title: str
    overview: str | None = None
    genres: list[str] = []
    cast: list[str] = []
    director: str | None = None
    release_date: date | None = None
    rating: float = 0
    popularity: float = 0
    poster_url: str | None = None
    language: str | None = None


# ── Recommendations ───────────────────────────────────────

class RecommendationItem(BaseModel):
    tmdb_id: int
    title: str
    poster_url: str | None = None
    genres: list[str] = []
    rating: float = 0
    popularity: float = 0
    score: float = 0


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
    source: str = "content"
    cached: bool = False


# ── Ratings ────────────────────────────────────────────────

class RatingCreate(BaseModel):
    movie_id: int
    rating: float = Field(..., ge=1, le=5)


class RatingOut(BaseModel):
    id: str
    movie_id: int
    rating: float
    created_at: datetime
    title: str | None = None
    poster_url: str | None = None
    genres: list[str] = []


class RatingStatsOut(BaseModel):
    total_rated: int = 0
    avg_rating: float = 0
    top_genre: str | None = None


# ── Watchlist ──────────────────────────────────────────────

class WatchlistAdd(BaseModel):
    movie_id: int


class WatchlistItem(BaseModel):
    id: str
    movie_id: int
    added_at: datetime
    title: str | None = None
    poster_url: str | None = None
    genres: list[str] = []
    rating: float = 0
    overview: str | None = None


# ── Search ─────────────────────────────────────────────────

class SearchResponse(BaseModel):
    results: list[MovieOut]
    count: int
    query: str
