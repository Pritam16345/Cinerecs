/**
 * CineRecs API client.
 * All backend API calls with auth token injection and auto-refresh.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let refreshPromise = null;
let refreshTimeoutId = null;

/**
 * Custom fetch wrapper with 401 handling and auto-refresh.
 */
export async function apiFetch(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  const headers = { "Content-Type": "application/json", ...options.headers };

  // Inject auth token if available
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("cinerecs_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let res = await fetch(url, { ...options, headers });

  // Handle 401 Unauthorized
  if (res.status === 401) {
    const data = await res.json().catch(() => ({}));
    
    // Check if it's an expired token
    if (data.code === "TOKEN_EXPIRED") {
      try {
        // Try to refresh the token
        const newToken = await refreshTokens();
        
        // Retry original request with new token
        headers["Authorization"] = `Bearer ${newToken}`;
        res = await fetch(url, { ...options, headers });
      } catch (err) {
        // Refresh failed, redirect to login if we are in a browser
        if (typeof window !== "undefined") {
          logout();
          window.location.href = "/login?expired=true";
        }
        throw new Error("Session expired. Please login again.");
      }
    }
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail?.detail || err.detail || `API error ${res.status}`);
  }

  return res.json();
}

/**
 * Call /auth/refresh to get a new access token.
 */
export async function refreshTokens() {
  // Prevent multiple simultaneous refresh calls
  if (refreshPromise) return refreshPromise;

  const refreshToken = localStorage.getItem("cinerecs_refresh_token");
  if (!refreshToken) throw new Error("No refresh token available");

  refreshPromise = (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (err.detail?.code === "REFRESH_TOKEN_EXPIRED") {
          throw new Error("REFRESH_EXPIRED");
        }
        throw new Error("Refresh failed");
      }

      const data = await res.json();
      localStorage.setItem("cinerecs_token", data.access_token);
      
      // Schedule next proactive refresh
      setupProactiveRefresh(data.access_token);
      
      return data.access_token;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Schedule a proactive refresh 60s before token expires.
 */
export function setupProactiveRefresh(token) {
  if (typeof window === "undefined" || !token) return;

  // Clear existing timeout
  if (refreshTimeoutId) clearTimeout(refreshTimeoutId);

  try {
    // Decode JWT payload (middle part)
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    const payload = JSON.parse(jsonPayload);
    if (!payload.exp) return;

    const expiresInMs = payload.exp * 1000 - Date.now();
    const refreshTimeMs = expiresInMs - 60000; // 60s before expiry

    if (refreshTimeMs > 0) {
      refreshTimeoutId = setTimeout(() => {
        console.log("Proactively refreshing token...");
        refreshTokens().catch(err => console.error("Proactive refresh failed", err));
      }, refreshTimeMs);
    }
  } catch (e) {
    console.error("Failed to parse JWT for proactive refresh", e);
  }
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
    localStorage.setItem("cinerecs_refresh_token", data.refresh_token);
    localStorage.setItem("cinerecs_user", JSON.stringify({
      user_id: data.user_id,
      email: data.email,
    }));
    setupProactiveRefresh(data.access_token);
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
    localStorage.setItem("cinerecs_refresh_token", data.refresh_token);
    localStorage.setItem("cinerecs_user", JSON.stringify({
      user_id: data.user_id,
      email: data.email,
    }));
    setupProactiveRefresh(data.access_token);
  }
  return data;
}

export function logout() {
  localStorage.removeItem("cinerecs_token");
  localStorage.removeItem("cinerecs_refresh_token");
  localStorage.removeItem("cinerecs_user");
  if (refreshTimeoutId) clearTimeout(refreshTimeoutId);
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("cinerecs_user");
  return raw ? JSON.parse(raw) : null;
}

export function getStoredToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cinerecs_token");
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
