"use client";
/**
 * Hero Section with Search.
 * Main entry point for searching movies with animated background effects.
 */
import { useState } from "react";
import { useRouter } from "next/navigation";
import SearchInput from "./SearchInput";

export default function HeroSearch() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("keyword");
  const router = useRouter();

  const handleSearch = (q) => {
    if (!q.trim()) return;
    router.push(`/search?q=${encodeURIComponent(q)}&mode=${mode}`);
  };

  return (
    <section className="relative py-20 sm:py-28 lg:py-36 z-30">
      {/* Animated gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-dark-900 to-emerald-900/10 overflow-hidden" />
      <div className="absolute inset-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      <div className="relative max-w-4xl mx-auto px-4 text-center">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold mb-4 animate-fade-in">
          <span className="gradient-text">Discover</span> Your Next{" "}
          <span className="gradient-text">Favorite</span> Movie
        </h1>
        <p className="text-dark-200 text-lg sm:text-xl mb-10 max-w-2xl mx-auto animate-slide-up">
          AI-powered recommendations combining content analysis and collaborative filtering
        </p>

        {/* Search form */}
        <div className="relative max-w-2xl mx-auto animate-slide-up">
          <SearchInput
            value={query}
            onChange={setQuery}
            onSearch={handleSearch}
            mode={mode}
            onModeChange={setMode}
            placeholder={
              mode === "semantic"
                ? "Describe a movie you'd like..."
                : "Search by title..."
            }
          />

          {/* Mobile mode toggle */}
          <div className="sm:hidden flex justify-center mt-3 gap-2">
            <button
              type="button"
              onClick={() => setMode("keyword")}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
                mode === "keyword" ? "bg-accent/20 text-accent-light border border-accent/30" : "text-dark-300 border border-dark-400/30"
              }`}
            >
              Keyword
            </button>
            <button
              type="button"
              onClick={() => setMode("semantic")}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${
                mode === "semantic" ? "bg-accent/20 text-accent-light border border-accent/30" : "text-dark-300 border border-dark-400/30"
              }`}
            >
              Semantic AI
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
