"use client";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="bg-dark-800 border-t border-dark-400/20 pt-16 pb-8 mt-20 relative overflow-hidden">
      {/* Background glow effect */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-2xl h-[1px] bg-gradient-to-r from-transparent via-accent to-transparent opacity-50" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[100px] -translate-y-1/2 pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          {/* Brand Section */}
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center gap-3 mb-6">
              <div className="relative w-10 h-10 rounded-xl overflow-hidden bg-accent/10 border border-accent/20">
                <Image 
                  src="/logo.png" 
                  alt="CineRecs Logo" 
                  fill 
                  className="object-contain p-1.5"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.parentElement.innerHTML = '<span class="flex items-center justify-center h-full text-xl">🎬</span>';
                  }}
                />
              </div>
              <span className="text-2xl font-black tracking-tight text-white">
                Cine<span className="text-accent-light">Recs</span>
              </span>
            </div>
            <p className="text-dark-300 text-sm leading-relaxed mb-6">
              Discover your next favorite movie. Powered by advanced AI to provide
              hyper-personalized recommendations tailored precisely to your cinematic taste.
            </p>
            {/* Social Icons (Placeholders) */}
            <div className="flex gap-4">
              {['Twitter', 'GitHub', 'Discord'].map((social) => (
                <a
                  key={social}
                  href="#"
                  className="w-10 h-10 rounded-full bg-dark-700 border border-dark-400/30 flex items-center justify-center text-dark-200 hover:bg-accent/10 hover:text-accent-light hover:border-accent/30 transition-all duration-300"
                  aria-label={social}
                >
                  <div className="w-4 h-4 bg-current opacity-80" style={{ maskImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3C/svg%3E")`, WebkitMaskImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Ccircle cx='12' cy='12' r='10'/%3E%3C/svg%3E")`, maskSize: 'cover', WebkitMaskSize: 'cover' }} />
                </a>
              ))}
            </div>
          </div>

          {/* Links Section 1 */}
          <div>
            <h3 className="text-white font-semibold mb-6">Platform</h3>
            <ul className="space-y-4">
              <li><a href="/" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Home</a></li>
              <li><a href="/search" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Discover</a></li>
              <li><a href="/recommendations" className="text-dark-300 hover:text-accent-light transition-colors text-sm">AI Recommendations</a></li>
              <li><a href="/profile" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Your Watchlist</a></li>
            </ul>
          </div>

          {/* Links Section 2 */}
          <div>
            <h3 className="text-white font-semibold mb-6">Company</h3>
            <ul className="space-y-4">
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">About Us</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Careers</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Contact Support</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Partners</a></li>
            </ul>
          </div>

          {/* Links Section 3 */}
          <div>
            <h3 className="text-white font-semibold mb-6">Legal</h3>
            <ul className="space-y-4">
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Privacy Policy</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Terms of Service</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Cookie Policy</a></li>
              <li><a href="#" className="text-dark-300 hover:text-accent-light transition-colors text-sm">Data Rights</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-dark-400/20 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-dark-300 text-sm">
            © 2026 CineRecs Inc. All rights reserved.
          </p>
          <p className="text-dark-400 text-sm flex items-center gap-1">
            Data provided by 
            <a href="https://www.themoviedb.org/" target="_blank" rel="noopener noreferrer" className="text-dark-200 hover:text-accent-light transition-colors">
              TMDB
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
