import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata = {
  title: "CineRecs - Discover Your Next Favorite Movie",
  description:
    "CineRecs is an AI-powered movie recommendation platform. Find personalized suggestions based on your taste using advanced content analysis and collaborative filtering.",
  keywords: "movies, recommendations, AI, CineRecs, similar movies, watchlist, TMDB",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-dark-900 text-dark-50 antialiased">
        <AuthProvider>
          <Navbar />
          <main className="min-h-[calc(100vh-4rem)]">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
