"use client";
/**
 * Search Page.
 * Supports both keyword-based (ILIKE) and semantic (vector) search.
 * Includes genre filtering and responsive result grid.
 */
import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import MovieCard from "@/components/MovieCard";
import GenrePills from "@/components/GenrePills";
import { searchMovies, semanticSearch } from "@/lib/api";
import SearchInput from "@/components/SearchInput";

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const initialMode = searchParams.get("mode") || "keyword";

  const [query, setQuery] = useState(initialQuery);
  const [mode, setMode] = useState(initialMode);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [genre, setGenre] = useState("All");
  const [searched, setSearched] = useState(false);

  const doSearch = useCallback(async (searchQuery) => {
    const finalQuery = typeof searchQuery === "string" ? searchQuery : query;
    if (!finalQuery.trim()) return;
    
    setLoading(true);
    setSearched(true);
    if (typeof searchQuery === "string") setQuery(searchQuery);

    try {
      let data;
      if (mode === "semantic") {
        data = await semanticSearch(finalQuery, 30);
        setResults(data.results || []);
      } else {
        data = await searchMovies(finalQuery, 40);
        setResults(data.results || []);
      }
    } catch (err) {
      console.error("Search error:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query, mode]);

  // Auto-search if query param present
  useEffect(() => {
    if (initialQuery) doSearch();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const filteredResults =
    genre === "All"
      ? results
      : results.filter((m) => m.genres?.includes(genre));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-extrabold gradient-text mb-6">Search Movies</h1>

      {/* Search bar */}
      <SearchInput
        className="mb-6"
        value={query}
        onChange={setQuery}
        onSearch={doSearch}
        mode={mode}
        onModeChange={setMode}
        placeholder={mode === "semantic" ? "Describe what you want..." : "Search by title..."}
      />

      {/* Genre filter */}
      <GenrePills selected={genre} onSelect={setGenre} />

      {/* Results */}
      <div className="mt-6">
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i}>
                <div className="aspect-[2/3] rounded-xl bg-dark-700 animate-pulse" />
                <div className="mt-2 h-4 bg-dark-700 rounded animate-pulse w-3/4" />
              </div>
            ))}
          </div>
        ) : filteredResults.length > 0 ? (
          <>
            <p className="text-dark-300 text-sm mb-4">
              {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""}{" "}
              {genre !== "All" && `in ${genre}`}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {filteredResults.map((movie) => (
                <MovieCard key={movie.tmdb_id} movie={movie} showScore={mode === "semantic"} />
              ))}
            </div>
          </>
        ) : searched ? (
          <div className="text-center py-16">
            <p className="text-dark-300 text-lg">No movies found</p>
            <p className="text-dark-400 text-sm mt-1">Try a different search term or mode</p>
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-dark-300 text-lg">Enter a query to search</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="max-w-7xl mx-auto px-4 py-8"><p className="text-dark-300">Loading...</p></div>}>
      <SearchContent />
    </Suspense>
  );
}
