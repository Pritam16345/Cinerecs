"use client";
import { useState, useEffect, useRef } from "react";
import Image from "next/image";

/** Search Input with Autocomplete. */
export default function SearchInput({ 
  value, 
  onChange, 
  onSearch, 
  mode = "keyword", 
  onModeChange,
  placeholder = "Search movies...",
  className = "",
  showModeToggle = true,
  buttonText = "Search"
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced suggestion fetch
  useEffect(() => {
    if (mode !== "keyword" || value.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const fetchSuggestions = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/movies/autocomplete?q=${encodeURIComponent(value)}&limit=6`);
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
          setShowSuggestions(data.length > 0);
        }
      } catch (err) {
        console.error("Autocomplete failed:", err);
      } finally {
        setLoading(false);
      }
    };

    const timeoutId = setTimeout(fetchSuggestions, 300);
    return () => clearTimeout(timeoutId);
  }, [value, mode]);

  const handleSuggestionClick = (movie) => {
    setShowSuggestions(false);
    onChange(movie.title);
    setTimeout(() => onSearch?.(movie.title, movie), 0);
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    setShowSuggestions(false);
    onSearch?.(value);
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <form onSubmit={handleSubmit} className="relative z-20">
        <div className="glass-card p-2 flex items-center gap-2">
          {/* Toggle */}
          {showModeToggle && (
            <div className="hidden sm:flex items-center bg-dark-800/60 rounded-xl p-1">
              <button
                type="button"
                onClick={() => onModeChange?.("keyword")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  mode === "keyword" ? "bg-accent/20 text-accent-light" : "text-dark-300 hover:text-dark-100"
                }`}
              >
                Keyword
              </button>
              <button
                type="button"
                onClick={() => onModeChange?.("semantic")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  mode === "semantic" ? "bg-accent/20 text-accent-light" : "text-dark-300 hover:text-dark-100"
                }`}
              >
                Semantic
              </button>
            </div>
          )}

          {/* Input */}
          <div className="flex-1 relative">
            <input
              type="text"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              placeholder={placeholder}
              className="w-full bg-transparent border-none outline-none text-dark-50 placeholder-dark-300 px-3 py-2 text-sm sm:text-base"
              autoComplete="off"
            />
          </div>

          <button type="submit" className="btn-primary !py-2 !px-5 text-sm">
            <span>{buttonText}</span>
          </button>
        </div>
      </form>

      {/* Dropdown */}
      {showSuggestions && (
        <div className="absolute top-full left-0 right-0 mt-2 z-50 glass-card overflow-hidden shadow-2xl animate-fade-in border border-white/5">
          <div className="max-h-[360px] overflow-y-auto custom-scrollbar">
            {suggestions.map((movie) => (
              <button
                key={movie.tmdb_id}
                onClick={() => handleSuggestionClick(movie)}
                className="w-full flex items-center gap-4 p-3 hover:bg-white/5 transition-colors text-left group border-b border-white/5 last:border-none"
              >
                <div className="relative w-10 h-14 rounded overflow-hidden flex-shrink-0 bg-dark-800">
                  {movie.poster_url ? (
                    <Image
                      src={movie.poster_url}
                      alt={movie.title}
                      fill
                      sizes="40px"
                      className="object-cover group-hover:scale-110 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[10px] text-dark-400">N/A</div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-dark-50 truncate group-hover:text-accent-light transition-colors">
                    {movie.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-1">
                    {movie.year && (
                      <span className="text-[10px] text-dark-400 font-medium px-1.5 py-0.5 bg-dark-800 rounded">{movie.year}</span>
                    )}
                    <span className="text-[10px] text-accent-light flex items-center">⭐ {movie.rating.toFixed(1)}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
