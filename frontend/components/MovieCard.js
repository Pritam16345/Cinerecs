"use client";
/**
 * Individual Movie Card component.
 * Displays poster, rating, and recommendation scores with a hover animation.
 */
import Image from "next/image";
import Link from "next/link";

const FALLBACK = "https://placehold.co/500x750/1a1a2e/ffffff?text=No+Poster";

export default function MovieCard({ movie, showScore = false }) {
  const {
    tmdb_id,
    title,
    poster_url,
    genres = [],
    rating = 0,
    score,
  } = movie;

  return (
    <Link
      href={`/movie/${tmdb_id}`}
      className="group relative flex-shrink-0 w-44 sm:w-48 card-hover"
      id={`movie-card-${tmdb_id}`}
    >
      {/* Poster */}
      <div className="relative aspect-[2/3] rounded-xl overflow-hidden bg-dark-700">
        <Image
          src={poster_url || FALLBACK}
          alt={title}
          fill
          sizes="(max-width:640px) 176px, 192px"
          className="object-cover transition-transform duration-500 group-hover:scale-110"
        />

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-dark-900/90 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Rating badge */}
        {rating > 0 && (
          <div className="absolute top-2 right-2 flex items-center gap-1 bg-dark-900/80 backdrop-blur-sm rounded-lg px-2 py-1">
            <span className="text-gold text-xs">★</span>
            <span className="text-xs font-semibold text-dark-50">{rating.toFixed(1)}</span>
          </div>
        )}

        {/* Score badge (for recommendations) */}
        {showScore && score > 0 && (
          <div className="absolute top-2 left-2 bg-accent/90 backdrop-blur-sm rounded-lg px-2 py-1">
            <span className="text-xs font-semibold text-white">{(score * 100).toFixed(0)}%</span>
          </div>
        )}

        {/* Hover info */}
        <div className="absolute bottom-0 left-0 right-0 p-3 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
          <div className="flex flex-wrap gap-1">
            {genres.slice(0, 2).map((g) => (
              <span key={g} className="genre-pill text-[10px]">{g}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Title */}
      <h3 className="mt-2 text-sm font-medium text-dark-100 line-clamp-2 group-hover:text-accent-light transition-colors">
        {title}
      </h3>
    </Link>
  );
}
