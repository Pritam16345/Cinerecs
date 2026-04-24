"use client";
/**
 * Main Landing Page.
 * Displays Hero section, trending movies, and personalized recommendations.
 */
import { useState, useEffect } from "react";
import HeroSearch from "@/components/HeroSearch";
import MovieRow from "@/components/MovieRow";
import GenrePills from "@/components/GenrePills";
import { getTrending, getUserRecs } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

export default function HomePage() {
  const { user } = useAuth();
  const [trending, setTrending] = useState([]);
  const [personalized, setPersonalized] = useState([]);
  const [selectedGenre, setSelectedGenre] = useState("All");
  const [loadingTrending, setLoadingTrending] = useState(true);
  const [loadingPersonal, setLoadingPersonal] = useState(false);

  // Fetch trending
  useEffect(() => {
    async function fetchTrending() {
      try {
        const data = await getTrending();
        setTrending(Array.isArray(data) ? data : data.results || []);
      } catch (err) {
        console.error("Trending fetch failed:", err);
      } finally {
        setLoadingTrending(false);
      }
    }
    fetchTrending();
  }, []);

  // Fetch personalized recs
  useEffect(() => {
    if (!user) {
      setPersonalized([]);
      return;
    }
    async function fetchPersonal() {
      setLoadingPersonal(true);
      try {
        const data = await getUserRecs(user.user_id, 20);
        setPersonalized(data.recommendations || []);
      } catch (err) {
        console.error("Personal recs failed:", err);
      } finally {
        setLoadingPersonal(false);
      }
    }
    fetchPersonal();
  }, [user]);

  const filteredTrending = selectedGenre === "All"
      ? trending
      : trending.filter((m) => m.genres?.includes(selectedGenre));

  return (
    <div>
      <HeroSearch />

      <div className="max-w-7xl mx-auto mt-4">
        <GenrePills selected={selectedGenre} onSelect={setSelectedGenre} />
      </div>

      <div className="max-w-7xl mx-auto pb-12">
        <MovieRow
          title="🔥 Trending Today"
          movies={filteredTrending}
          loading={loadingTrending}
        />

        {user && (
          <MovieRow
            title="✨ Recommended for You"
            movies={personalized}
            showScore
            loading={loadingPersonal}
          />
        )}

        {!user && (
          <div className="mt-12 mx-4 sm:mx-0">
            <div className="glass-card p-8 text-center">
              <h3 className="text-xl font-bold gradient-text mb-2">Get Personalized Recommendations</h3>
              <p className="text-dark-300 mb-6 max-w-md mx-auto">
                Sign up to rate movies, build your watchlist, and receive AI-powered recommendations tailored just for you.
              </p>
              <a href="/register" className="btn-primary inline-block">Create Free Account</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
