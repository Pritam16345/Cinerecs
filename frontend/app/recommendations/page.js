"use client";
/**
 * Movie-Based Recommendations Page.
 * Allows users to find movies similar to a specific title.
 * Provides a dedicated search-to-recommendation flow.
 */
import { useState } from "react";
import { searchMovies, getSimilar } from "@/lib/api";
import SearchInput from "@/components/SearchInput";
import MovieCard from "@/components/MovieCard";

export default function RecommendationsPage() {
  const [query, setQuery] = useState("");
  const [targetMovie, setTargetMovie] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async (searchQuery, suggestion = null) => {
    const finalQuery = searchQuery || query;
    if (!finalQuery.trim() && !suggestion) return;
    
    setLoading(true);
    setSearched(true);
    if (searchQuery) setQuery(searchQuery);

    try {
      let movie = suggestion;
      
      // If no suggestion provided, find the movie by title
      if (!movie) {
        const searchRes = await searchMovies(finalQuery, 1);
        if (searchRes.results && searchRes.results.length > 0) {
          movie = searchRes.results[0];
        }
      }

      if (movie) {
        setTargetMovie(movie);
        const recs = await getSimilar(movie.tmdb_id, 30);
        setRecommendations(recs.recommendations || []);
      } else {
        setTargetMovie(null);
        setRecommendations([]);
      }
    } catch (err) {
      console.error("Failed to fetch recommendations:", err);
      setTargetMovie(null);
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-10 text-center">
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">
          Movie <span className="gradient-text">Recommendations</span>
        </h1>
        <p className="text-lg text-dark-200 max-w-2xl mx-auto mb-8">
          Type the name of any movie you love, and our AI will instantly generate a list of the most similar movies to watch next!
        </p>
        
        {/* Search Bar */}
        <div className="max-w-2xl mx-auto">
          <SearchInput
            value={query}
            onChange={setQuery}
            onSearch={doSearch}
            showModeToggle={false}
            placeholder="E.g., The Dark Knight, Titanic, Inception..."
            buttonText="Get Recs"
          />
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 mt-12">
          {[...Array(10)].map((_, i) => (
            <div
              key={i}
              className="bg-dark-600/50 rounded-xl aspect-[2/3] animate-pulse"
            />
          ))}
        </div>
      ) : targetMovie && recommendations.length > 0 ? (
        <div className="mt-12 animate-fade-in">
          <div className="flex items-center gap-4 mb-8 pb-4 border-b border-dark-400/20">
            <h2 className="text-2xl text-dark-200">
              Because you searched for <span className="text-white font-bold">{targetMovie.title}</span>...
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6">
            {recommendations.map((movie) => (
              <MovieCard key={movie.tmdb_id} movie={movie} showScore />
            ))}
          </div>
        </div>
      ) : searched && !loading ? (
        <div className="text-center py-20 glass-card mt-12 animate-fade-in">
          <span className="text-6xl mb-4 block">🔍</span>
          <h3 className="text-2xl font-bold mb-2">No Recommendations Found</h3>
          <p className="text-dark-200 mb-6 max-w-md mx-auto">
            We couldn't find any direct recommendations for that search. Try checking your spelling or searching for a different movie!
          </p>
        </div>
      ) : null}
    </div>
  );
}
