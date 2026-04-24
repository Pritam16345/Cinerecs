"use client";
/**
 * User Profile Page.
 * Displays user statistics, watchlist management, and rating history.
 * Requires authentication; redirects to login if not authenticated.
 */
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import StarRating from "@/components/StarRating";
import { useAuth } from "@/components/AuthProvider";
import { getWatchlist, getRatings, getRatingStats, removeFromWatchlist, submitRating } from "@/lib/api";

const FALLBACK = "https://placehold.co/500x750/1a1a2e/ffffff?text=No+Poster";

export default function ProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState("watchlist");
  const [watchlist, setWatchlist] = useState([]);
  const [ratings, setRatings] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    Promise.all([
      getWatchlist().catch(() => []),
      getRatings().catch(() => []),
      getRatingStats().catch(() => null),
    ]).then(([wl, rt, st]) => {
      setWatchlist(Array.isArray(wl) ? wl : []);
      setRatings(Array.isArray(rt) ? rt : []);
      setStats(st);
      setLoading(false);
    });
  }, [user]);

  const handleRemoveWatchlist = async (movieId) => {
    try {
      await removeFromWatchlist(movieId);
      setWatchlist((prev) => prev.filter((w) => w.movie_id !== movieId));
    } catch (err) {
      console.error("Remove failed:", err);
    }
  };

  const handleUpdateRating = async (movieId, newRating) => {
    try {
      await submitRating(movieId, newRating);
      setRatings((prev) =>
        prev.map((r) => (r.movie_id === movieId ? { ...r, rating: newRating } : r))
      );
    } catch (err) {
      console.error("Rating update failed:", err);
    }
  };

  if (authLoading || !user) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="glass-card p-6 mb-8 flex flex-col sm:flex-row items-center gap-6">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
          {user.email?.[0]?.toUpperCase() || "U"}
        </div>
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-bold text-dark-50">{user.email}</h1>
          <p className="text-dark-300 text-sm mt-1">Member since joining CineRecs</p>
        </div>
        {stats && (
          <div className="flex gap-6 sm:ml-auto">
            <StatBlock label="Rated" value={stats.total_rated || 0} />
            <StatBlock label="Avg Rating" value={stats.avg_rating?.toFixed(1) || "0"} />
            <StatBlock label="Top Genre" value={stats.top_genre || "—"} />
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("watchlist")}
          className={`px-5 py-2 rounded-xl text-sm font-medium transition-all ${
            tab === "watchlist" ? "bg-accent text-white" : "bg-dark-700 text-dark-200 hover:bg-dark-600"
          }`}
        >
          Watchlist ({watchlist.length})
        </button>
        <button
          onClick={() => setTab("ratings")}
          className={`px-5 py-2 rounded-xl text-sm font-medium transition-all ${
            tab === "ratings" ? "bg-accent text-white" : "bg-dark-700 text-dark-200 hover:bg-dark-600"
          }`}
        >
          Ratings ({ratings.length})
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="aspect-[2/3] rounded-xl bg-dark-700 animate-pulse" />
          ))}
        </div>
      ) : tab === "watchlist" ? (
        watchlist.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {watchlist.map((item) => (
              <div key={item.movie_id} className="group relative">
                <Link href={`/movie/${item.movie_id}`}>
                  <div className="relative aspect-[2/3] rounded-xl overflow-hidden bg-dark-700 card-hover">
                    <Image
                      src={item.poster_url || FALLBACK}
                      alt={item.title || "Movie"}
                      fill
                      className="object-cover"
                    />
                  </div>
                  <h3 className="mt-2 text-sm font-medium text-dark-100 line-clamp-2">{item.title}</h3>
                </Link>
                <button
                  onClick={() => handleRemoveWatchlist(item.movie_id)}
                  className="absolute top-2 right-2 w-7 h-7 rounded-full bg-danger/80 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Remove from watchlist"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState text="Your watchlist is empty" sub="Browse movies and add them to your watchlist" />
        )
      ) : ratings.length > 0 ? (
        <div className="space-y-3">
          {ratings.map((r) => (
            <div key={r.movie_id} className="glass-card p-4 flex items-center gap-4">
              <Link href={`/movie/${r.movie_id}`} className="flex-shrink-0">
                <div className="relative w-12 h-18 rounded-lg overflow-hidden bg-dark-700">
                  <Image
                    src={r.poster_url || FALLBACK}
                    alt={r.title || "Movie"}
                    width={48}
                    height={72}
                    className="object-cover"
                  />
                </div>
              </Link>
              <div className="flex-1 min-w-0">
                <Link href={`/movie/${r.movie_id}`} className="text-sm font-medium text-dark-100 hover:text-accent-light truncate block">
                  {r.title}
                </Link>
                <p className="text-xs text-dark-400">{new Date(r.created_at).toLocaleDateString()}</p>
              </div>
              <StarRating value={r.rating} onChange={(v) => handleUpdateRating(r.movie_id, v)} size="sm" />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No ratings yet" sub="Rate movies to get personalized recommendations" />
      )}
    </div>
  );
}

function StatBlock({ label, value }) {
  return (
    <div className="text-center">
      <p className="text-lg font-bold text-dark-50">{value}</p>
      <p className="text-xs text-dark-400">{label}</p>
    </div>
  );
}

function EmptyState({ text, sub }) {
  return (
    <div className="text-center py-16">
      <p className="text-dark-300 text-lg">{text}</p>
      <p className="text-dark-400 text-sm mt-1">{sub}</p>
    </div>
  );
}
