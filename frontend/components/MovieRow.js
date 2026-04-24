"use client";
/**
 * Horizontal scrollable movie list.
 * Includes smooth scrolling controls and loading skeleton states.
 */
import { useRef } from "react";
import MovieCard from "./MovieCard";

export default function MovieRow({ title, movies = [], showScore = false, loading = false }) {
  const scrollRef = useRef(null);

  const scroll = (direction) => {
    if (!scrollRef.current) return;
    const amount = direction === "left" ? -600 : 600;
    scrollRef.current.scrollBy({ left: amount, behavior: "smooth" });
  };

  if (loading) {
    return (
      <section className="py-6">
        <h2 className="text-xl font-bold text-dark-50 mb-4 px-4 sm:px-0">{title}</h2>
        <div className="flex gap-4 overflow-hidden px-4 sm:px-0">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex-shrink-0 w-44 sm:w-48">
              <div className="aspect-[2/3] rounded-xl bg-dark-700 animate-pulse" />
              <div className="mt-2 h-4 bg-dark-700 rounded animate-pulse w-3/4" />
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!movies.length) return null;

  return (
    <section className="py-6 group/row">
      <div className="flex items-center justify-between mb-4 px-4 sm:px-0">
        <h2 className="text-xl font-bold text-dark-50">{title}</h2>
        <div className="hidden sm:flex gap-2 opacity-0 group-hover/row:opacity-100 transition-opacity">
          <button
            onClick={() => scroll("left")}
            className="w-8 h-8 rounded-full bg-dark-600/80 hover:bg-dark-500 flex items-center justify-center text-dark-200 transition-colors"
            aria-label="Scroll left"
          >
            ←
          </button>
          <button
            onClick={() => scroll("right")}
            className="w-8 h-8 rounded-full bg-dark-600/80 hover:bg-dark-500 flex items-center justify-center text-dark-200 transition-colors"
            aria-label="Scroll right"
          >
            →
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto hide-scrollbar px-4 sm:px-0 pb-2"
      >
        {movies.map((movie) => (
          <MovieCard key={movie.tmdb_id} movie={movie} showScore={showScore} />
        ))}
      </div>
    </section>
  );
}
