"use client";
/**
 * Movie Details Page.
 * Displays full movie information, cast, and similar movie recommendations.
 * Allows authenticated users to rate movies and add them to their watchlist.
 */
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import MovieRow from "@/components/MovieRow";
import StarRating from "@/components/StarRating";
import { getMovie, getSimilar, submitRating, addToWatchlist } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

const FALLBACK = "https://placehold.co/500x750/1a1a2e/ffffff?text=No+Poster";

export default function MoviePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [movie, setMovie] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userRating, setUserRating] = useState(0);
  const [ratingMsg, setRatingMsg] = useState("");
  const [watchlistMsg, setWatchlistMsg] = useState("");
  const [isAdded, setIsAdded] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      getMovie(id).catch(() => null),
      getSimilar(id, 10).catch(() => ({ recommendations: [] })),
    ]).then(([movieData, simData]) => {
      setMovie(movieData);
      setSimilar(simData?.recommendations || []);
      setLoading(false);
    });
  }, [id]);

  const handleRate = async (rating) => {
    if (!user) return;
    setUserRating(rating);
    try {
      await submitRating(parseInt(id), rating);
      setRatingMsg("Rating saved!");
      setTimeout(() => setRatingMsg(""), 2000);
    } catch (err) {
      setRatingMsg("Failed to save rating");
    }
  };

  const handleWatchlist = async () => {
    if (!user || isAdded) return;
    try {
      await addToWatchlist(parseInt(id));
      setIsAdded(true);
      setWatchlistMsg("Added to watchlist!");
      setTimeout(() => setWatchlistMsg(""), 2000);
    } catch (err) {
      if (err.message?.includes("already")) {
        setIsAdded(true);
      }
      setWatchlistMsg(err.message?.includes("already") ? "Already in watchlist" : "Failed to add");
      setTimeout(() => setWatchlistMsg(""), 2000);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="flex flex-col md:flex-row gap-8 animate-pulse">
          <div className="w-72 aspect-[2/3] bg-dark-700 rounded-2xl flex-shrink-0" />
          <div className="flex-1 space-y-4">
            <div className="h-8 bg-dark-700 rounded w-2/3" />
            <div className="h-4 bg-dark-700 rounded w-1/3" />
            <div className="h-20 bg-dark-700 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-dark-100">Movie Not Found</h1>
        <p className="text-dark-300 mt-2">The movie you are looking for does not exist in our database.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 sm:py-12">
      {/* Movie Detail */}
      <div className="flex flex-col md:flex-row gap-8 animate-fade-in">
        {/* Poster */}
        <div className="flex-shrink-0 mx-auto md:mx-0">
          <div className="relative w-64 sm:w-72 aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl shadow-accent/10">
            <Image
              src={movie.poster_url || FALLBACK}
              alt={movie.title}
              fill
              className="object-cover"
              priority
            />
          </div>
        </div>

        {/* Info */}
        <div className="flex-1">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-dark-50 mb-2">
            {movie.title}
          </h1>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-3 mb-4 text-sm text-dark-300">
            {movie.release_date && (
              <span>{new Date(movie.release_date).getFullYear()}</span>
            )}
            {movie.language && (
              <span className="uppercase">{movie.language}</span>
            )}
            {movie.rating > 0 && (
              <span className="flex items-center gap-1 text-gold">
                ★ {movie.rating.toFixed(1)}
              </span>
            )}
            {movie.director && <span>Dir: {movie.director}</span>}
          </div>

          {/* Genres */}
          <div className="flex flex-wrap gap-2 mb-6">
            {movie.genres?.map((g) => (
              <span key={g} className="genre-pill">{g}</span>
            ))}
          </div>

          {/* Overview */}
          <p className="text-dark-200 leading-relaxed mb-6 max-w-2xl">
            {movie.overview || "No overview available."}
          </p>

          {/* Cast */}
          {movie.cast?.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-dark-300 uppercase mb-2">Cast</h3>
              <p className="text-dark-200 text-sm">{movie.cast.slice(0, 8).join(", ")}</p>
            </div>
          )}

          {/* Actions (logged in) */}
          {user && (
            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              {/* Rate */}
              <div className="glass-card p-4">
                <h3 className="text-sm font-semibold text-dark-300 mb-2">Rate this movie</h3>
                <StarRating value={userRating} onChange={handleRate} />
                {ratingMsg && (
                  <p className="text-xs text-success mt-1 animate-fade-in">{ratingMsg}</p>
                )}
              </div>

              {/* Watchlist */}
              <div className="glass-card p-4 flex flex-col justify-center">
                <button 
                  onClick={handleWatchlist} 
                  disabled={isAdded}
                  className={`text-sm ${isAdded ? 'btn-secondary opacity-70 cursor-default' : 'btn-primary'}`}
                >
                  {isAdded ? "✓ Added to Watchlist" : "+ Add to Watchlist"}
                </button>
                {watchlistMsg && (
                  <p className="text-xs text-accent-light mt-2 animate-fade-in">{watchlistMsg}</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Similar Movies */}
      <div className="mt-12">
        <MovieRow title="Similar Movies" movies={similar} showScore />
      </div>
    </div>
  );
}
