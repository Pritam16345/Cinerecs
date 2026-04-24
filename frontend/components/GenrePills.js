"use client";

const GENRES = [
  "All", "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
  "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
  "Romance", "Science Fiction", "Thriller", "War", "Western",
];

export default function GenrePills({ selected = "All", onSelect }) {
  return (
    <div className="flex gap-2 overflow-x-auto hide-scrollbar py-2 px-4 sm:px-0">
      {GENRES.map((genre) => (
        <button
          key={genre}
          onClick={() => onSelect?.(genre)}
          className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-300 ${
            selected === genre
              ? "bg-accent text-white shadow-lg shadow-accent/30"
              : "bg-dark-700/60 text-dark-200 hover:bg-dark-600/80 hover:text-dark-50 border border-dark-400/20"
          }`}
        >
          {genre}
        </button>
      ))}
    </div>
  );
}
