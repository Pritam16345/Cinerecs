"use client";
/**
 * Sticky Navigation Bar.
 * Handles logo, primary links, and user auth status (login/profile).
 */
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/components/AuthProvider";
import { usePathname } from "next/navigation";

export default function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-dark-900/80 backdrop-blur-xl border-b border-dark-400/20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative w-8 h-8 rounded-lg overflow-hidden group-hover:scale-110 transition-transform duration-300">
              <Image 
                src="/logo.png" 
                alt="CineRecs Logo" 
                fill 
                className="object-contain"
                onError={(e) => {
                  // Fallback if logo.png is missing
                  e.target.style.display = 'none';
                  e.target.parentElement.innerHTML = '<span class="text-2xl">🎬</span>';
                }}
              />
            </div>
            <span className="text-2xl font-black tracking-tight text-white group-hover:text-accent-light transition-colors">
              Cine<span className="text-accent-light">Recs</span>
            </span>
          </Link>

          {/* Center Nav */}
          <div className="hidden md:flex items-center gap-1">
            <NavLink href="/" active={pathname === "/"}>Home</NavLink>
            <NavLink href="/search" active={pathname === "/search"}>Search</NavLink>
            {user && (
              <>
                <NavLink href="/recommendations" active={pathname === "/recommendations"}>Recommendations</NavLink>
                <NavLink href="/profile" active={pathname === "/profile"}>Profile</NavLink>
              </>
            )}
          </div>

          {/* Right side */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <Link
                  href="/profile"
                  className="hidden sm:flex items-center gap-2 text-sm text-dark-200 hover:text-accent-light transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-emerald-600 flex items-center justify-center text-white text-xs font-bold">
                    {user.email?.[0]?.toUpperCase() || "U"}
                  </div>
                  <span className="hidden lg:inline">{user.email}</span>
                </Link>
                <button
                  onClick={logout}
                  className="btn-secondary text-sm"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/login" className="btn-secondary text-sm">
                  Sign In
                </Link>
                <Link href="/register" className="btn-primary text-sm !py-2">
                  Sign Up
                </Link>
              </div>
            )}

            {/* Mobile nav */}
            <div className="md:hidden flex items-center gap-1">
              <MobileLink href="/search">🔍</MobileLink>
              {user && (
                <>
                  <MobileLink href="/recommendations">✨</MobileLink>
                  <MobileLink href="/profile">👤</MobileLink>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function NavLink({ href, active, children }) {
  return (
    <Link
      href={href}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
        active
          ? "bg-accent/15 text-accent-light"
          : "text-dark-200 hover:text-dark-50 hover:bg-dark-600/50"
      }`}
    >
      {children}
    </Link>
  );
}

function MobileLink({ href, children }) {
  return (
    <Link href={href} className="p-2 text-lg hover:opacity-70 transition-opacity">
      {children}
    </Link>
  );
}
