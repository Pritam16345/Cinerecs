/**
 * CineRecs API client.
 * All backend API calls with auth token injection.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  const headers = { "Content-Type": "application/json", ...options.headers };

  // Inject auth token if available
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("cinerecs_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }

  return res.json();
}

// ── Movies ────────────────────────────────────────────────
export async function getTrending() {
  return apiFetch("/movies/trending");
}

export async function searchMovies(query, limit = 20) {
  return apiFetch(`/movies/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function semanticSearch(query, limit = 10) {
  return apiFetch(`/movies/semantic?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export async function getMovie(tmdbId) {
  return apiFetch(`/movies/${tmdbId}`);
}

// ── Recommendations ──────────────────────────────────────
export async function getSimilar(tmdbId, limit = 10) {
  return apiFetch(`/recommend/similar/${tmdbId}?limit=${limit}`);
}

export async function getUserRecs(userId, limit = 10) {
  return apiFetch(`/recommend/user/${userId}?limit=${limit}`);
}

export async function getHybridRecs(movieId, userId, limit = 10) {
  return apiFetch(`/recommend/hybrid/${movieId}/${userId}?limit=${limit}`);
}

// ── Auth ──────────────────────────────────────────────────
export async function login(email, password) {
  const data = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    localStorage.setItem("cinerecs_token", data.access_token);
    localStorage.setItem("cinerecs_user", JSON.stringify({
      user_id: data.user_id,
      email: data.email,
    }));
  }
  return data;
}

export async function register(email, password) {
  const data = await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    localStorage.setItem("cinerecs_token", data.access_token);
    localStorage.setItem("cinerecs_user", JSON.stringify({
      user_id: data.user_id,
      email: data.email,
    }));
  }
  return data;
}

export function logout() {
  localStorage.removeItem("cinerecs_token");
  localStorage.removeItem("cinerecs_user");
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("cinerecs_user");
  return raw ? JSON.parse(raw) : null;
}

// ── Ratings ──────────────────────────────────────────────
export async function getRatings() {
  return apiFetch("/ratings");
}

export async function submitRating(movieId, rating) {
  return apiFetch("/ratings", {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId, rating }),
  });
}

export async function getRatingStats() {
  return apiFetch("/ratings/stats");
}

// ── Watchlist ────────────────────────────────────────────
export async function getWatchlist() {
  return apiFetch("/watchlist");
}

export async function addToWatchlist(movieId) {
  return apiFetch("/watchlist", {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId }),
  });
}

export async function removeFromWatchlist(movieId) {
  return apiFetch(`/watchlist/${movieId}`, { method: "DELETE" });
}
