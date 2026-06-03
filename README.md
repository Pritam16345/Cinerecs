<div align="center">

# 🎬 CineRecs

### AI-Powered Movie Recommendation Engine

[![Weekly Sync](https://img.shields.io/github/actions/workflow/status/Pritam16345/Cinerecs/weekly_sync.yml?label=Weekly%20Sync&logo=githubactions&logoColor=white&style=for-the-badge)](https://github.com/Pritam16345/Cinerecs/actions/workflows/weekly_sync.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

**Discover your next favorite movie.**  
A production-grade hybrid recommendation system combining semantic vector search (FAISS) with user-based collaborative filtering, backed by 76K+ movies from the TMDB catalog.

[🔗 Live Demo](https://cinerecs-ebon.vercel.app) · [📖 API Docs](https://pritu16345-cinerecs-api.hf.space/docs) · [📡 API Health](https://pritu16345-cinerecs-api.hf.space/health)

---

</div>

## ⚡ Highlights

| Feature | Details |
|---|---|
| 🧠 **Hybrid Recommendations** | `0.6× Content-Based (FAISS)` + `0.4× Collaborative Filtering` — blended scoring for superior accuracy |
| 🔍 **Semantic Search** | Natural language queries powered by `all-MiniLM-L6-v2` sentence transformer |
| ⌨️ **Real-time Autocomplete** | Prefix-matching suggestions with `< 50ms` response times |
| 📦 **76K+ Movies** | Complete TMDB catalog with automated weekly sync via GitHub Actions |
| 🚀 **Optimized Cold Start** | Local FAISS index caching — sub-second backend restarts after first load |
| 🎨 **Premium UI** | Glassmorphism dark theme, smooth micro-animations, fully responsive design |
| 🔐 **JWT Auth with Auto-Refresh** | 30-min access tokens + 7-day refresh tokens with proactive client-side refresh |
| ⭐ **Personalization** | User ratings, watchlist management, and per-user recommendation stats |

---

## 🌐 Live Deployment

| Component | URL | Hosting |
|---|---|---|
| **Frontend** | [cinerecs-ebon.vercel.app](https://cinerecs-ebon.vercel.app) | Vercel |
| **Backend API** | [pritu16345-cinerecs-api.hf.space](https://pritu16345-cinerecs-api.hf.space) | Hugging Face Spaces |
| **API Docs (Swagger)** | [/docs](https://pritu16345-cinerecs-api.hf.space/docs) | Auto-generated |
| **API Docs (ReDoc)** | [/redoc](https://pritu16345-cinerecs-api.hf.space/redoc) | Auto-generated |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser)                        │
│                    Next.js 14 · Tailwind CSS                    │
│              Glassmorphism UI · App Router · SSR                │
└───────────────────────────┬──────────────────────────────────────┘
                            │  HTTP / JSON
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (v3.0)                     │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Auth Router │  │ Movie Router │  │  Recommendation Router │  │
│  │  /auth/*     │  │ /movies/*    │  │  /recommend/*          │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬───────────┘  │
│         │                 │                       │              │
│  ┌──────▼─────────────────▼───────────────────────▼───────────┐  │
│  │                    SERVICE LAYER                           │  │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌─────────┐ │  │
│  │  │  FAISS   │  │  TMDB API  │  │  Redis   │  │ Collab  │ │  │
│  │  │ Service  │  │  Service   │  │ Service  │  │ Service │ │  │
│  │  └────┬─────┘  └────────────┘  └────┬─────┘  └─────────┘ │  │
│  └───────┼──────────────────────────────┼────────────────────┘  │
└──────────┼──────────────────────────────┼────────────────────────┘
           │                              │
     ┌─────▼──────┐                ┌──────▼──────┐
     │ Backblaze  │                │   Upstash   │
     │    B2      │                │    Redis    │
     │  (S3/B2)   │                │   (Cache)   │
     └────────────┘                └─────────────┘
           │
     ┌─────▼──────────────┐
     │    Supabase        │
     │   (PostgreSQL)     │
     │    Cloud DB        │
     └────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 14, Tailwind CSS, React 18 | Server-side rendering, glassmorphism UI, responsive design |
| **Backend** | FastAPI, AsyncPG, Pydantic v2 | Async REST API, request validation, auto-generated OpenAPI docs |
| **ML/Search** | FAISS, Sentence-Transformers (`all-MiniLM-L6-v2`) | Semantic embeddings (384-dim), cosine similarity search |
| **Database** | Supabase (PostgreSQL) | Managed cloud PostgreSQL with 500 MB free storage |
| **Cache** | Upstash Redis | Sub-millisecond caching for search results and recommendations |
| **Object Storage** | Backblaze B2 (S3-compatible) | Persistent storage for FAISS index, embeddings, and ID maps |
| **CI/CD** | GitHub Actions | Automated weekly TMDB sync every Sunday at 2:00 AM UTC |
| **Auth** | PyJWT (HS256) + bcrypt (passlib) | Stateless JWT auth with 30-min access / 7-day refresh tokens |
| **Containerization** | Docker + Docker Compose | One-command local deployment |
| **Hosting** | Vercel (frontend) + Hugging Face Spaces (backend) | Free-tier production hosting |

---

## 🧠 How Recommendations Work

CineRecs uses a **three-strategy** recommendation engine:

### 1. Content-Based Filtering (FAISS)

Each movie is encoded into a 384-dimensional embedding vector using `all-MiniLM-L6-v2`:

```
embedding = encode(title + overview + genres + cast)
```

When you request similar movies, CineRecs performs an **inner-product similarity search** across all 76K+ vectors using Facebook's FAISS library, returning the top-k most semantically similar movies in milliseconds.

### 2. Collaborative Filtering (User-Based)

```
User A rates: Inception (5★), Interstellar (5★), The Matrix (4★)
User B rates: Inception (5★), Interstellar (4★), Arrival (5★)
→ Recommend "Arrival" to User A (similar taste profile)
```

The algorithm:
1. Find movies the target user rated ≥ 4.0
2. Find other users who also rated those movies ≥ 4.0
3. Collect movies those similar users loved that the target user hasn't seen
4. Score by `0.6 × frequency_score + 0.4 × rating_score`

### 3. Hybrid (Blended)

For users with enough rating history, CineRecs blends both strategies:

```
hybrid_score = 0.6 × content_score + 0.4 × collaborative_score
```

This mitigates the cold-start problem — new users get content-based recommendations immediately, and the system progressively incorporates collaborative signals as they rate more movies.

---

## 🔐 Authentication System

CineRecs implements a robust JWT authentication system with automatic token refresh:

| Feature | Details |
|---|---|
| **Access Token** | 30-minute expiry, contains user ID + email |
| **Refresh Token** | 7-day expiry, used to obtain new access tokens |
| **Algorithm** | HS256 with server-side secret |
| **Password Hashing** | bcrypt via passlib |
| **Auto-Refresh** | Client-side interceptor proactively refreshes tokens 60s before expiry |
| **Token Expired Response** | `{"detail": "Token expired", "code": "TOKEN_EXPIRED"}` for easy client-side handling |

**Endpoints:**
- `POST /auth/register` — Create account → returns access + refresh tokens
- `POST /auth/login` — Login → returns access + refresh tokens
- `POST /auth/refresh` — Exchange refresh token for new access token

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** — [Download](https://python.org/downloads)
- **Node.js 18+** — [Download](https://nodejs.org)
- **Docker** *(optional)* — [Download](https://docker.com/get-started)

You'll also need accounts (all have free tiers):

| Service | Purpose | Sign Up |
|---|---|---|
| **TMDB** | Movie data API | [themoviedb.org](https://www.themoviedb.org/settings/api) |
| **Supabase** | PostgreSQL database | [supabase.com](https://supabase.com) |
| **Upstash** | Redis cache | [upstash.com](https://upstash.com) |
| **Backblaze B2** | Object storage for FAISS index | [backblaze.com](https://www.backblaze.com/b2/sign-up.html) |

---

## 🚀 Getting Started

### 1. Clone & Configure

```bash
git clone https://github.com/Pritam16345/Cinerecs.git
cd Cinerecs
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
# TMDB API (required)
TMDB_API_KEY=your_tmdb_api_key

# PostgreSQL database connection string (Supabase / CockroachDB / local)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:token@endpoint:6379
UPSTASH_REDIS_TOKEN=your_upstash_token

# Object Storage (S3-compatible)
R2_ACCESS_KEY_ID=your_key_id
R2_SECRET_ACCESS_KEY=your_secret_key
R2_ENDPOINT_URL=https://s3.us-east-005.backblazeb2.com
R2_BUCKET_NAME=cinerecs

# JWT Secret (generate: openssl rand -hex 32)
JWT_SECRET=your_random_jwt_secret_at_least_32_chars

# Frontend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### 2. Populate the Database

Run the historical import to fetch ~80K movies from TMDB, store them in PostgreSQL, build the FAISS index, and upload it to B2:

```bash
pip install -r backend/requirements.txt
python scripts/historical_import.py
```

> **⏱️ Note:** The initial import takes 4–8 hours depending on your network speed (TMDB rate limit: 40 req/10s). The script supports **resume** — if interrupted, it will skip already-imported movies on the next run.

### 3. Run Locally

#### Option A — Docker (Recommended)

```bash
docker-compose up --build
```

This starts both the backend (`:8000`) and frontend (`:3000`) with hot-reload.

#### Option B — Manual

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Navigate to **[http://localhost:3000](http://localhost:3000)** — you should see the CineRecs homepage with trending movies loaded.

---

## 📁 Project Structure

```
CineRecs/
│
├── backend/
│   ├── main.py                     # FastAPI entry point, lifespan, CORS, middleware
│   ├── database.py                 # AsyncPG connection pool, all SQL queries
│   ├── auth.py                     # JWT creation/verification (access + refresh tokens)
│   ├── models.py                   # Pydantic schemas (request/response validation)
│   ├── Dockerfile                  # Python 3.11-slim container
│   ├── requirements.txt            # Pinned Python dependencies
│   │
│   ├── routers/
│   │   ├── auth.py                 # POST /auth/register, /login, /refresh
│   │   ├── movies.py               # GET /movies/trending, /search, /semantic, /{id}
│   │   ├── recommend.py            # GET /recommend/similar, /user, /hybrid
│   │   ├── ratings.py              # GET/POST /ratings, GET /ratings/stats
│   │   └── watchlist.py            # GET/POST/DELETE /watchlist
│   │
│   └── services/
│       ├── faiss_service.py        # FAISS index loading, vector search, R2 sync
│       ├── redis_service.py        # Async Redis get/set/invalidate with JSON
│       ├── tmdb_service.py         # TMDB API client with rate limiting
│       └── collab_service.py       # User-based collaborative filtering algorithm
│
├── frontend/
│   ├── app/
│   │   ├── layout.js               # Root layout (AuthProvider, Navbar, Footer)
│   │   ├── page.js                 # Homepage (trending + personalized recs)
│   │   ├── globals.css             # Design system (glassmorphism, animations)
│   │   ├── login/page.js           # Login form
│   │   ├── register/page.js        # Registration form with password confirm
│   │   ├── search/page.js          # Search page (keyword + semantic modes)
│   │   ├── movie/[id]/page.js      # Movie detail (poster, cast, rate, watchlist)
│   │   ├── recommendations/page.js # "Find similar movies" page
│   │   └── profile/page.js         # User profile (watchlist, ratings, stats)
│   │
│   ├── components/
│   │   ├── AuthProvider.js          # React context for auth state + proactive refresh
│   │   ├── Navbar.js                # Sticky nav with responsive mobile menu
│   │   ├── Footer.js                # 4-column footer with glow effects
│   │   ├── HeroSearch.js            # Animated hero section with search
│   │   ├── SearchInput.js           # Search bar with debounced autocomplete
│   │   ├── MovieCard.js             # Poster card with hover effects
│   │   ├── MovieRow.js              # Horizontal scroll row with arrow nav
│   │   ├── GenrePills.js            # Scrollable genre filter chips
│   │   └── StarRating.js            # Interactive 1-5 star rating input
│   │
│   ├── lib/
│   │   └── api.js                   # API client with auth token injection + auto-refresh
│   │
│   ├── tailwind.config.js           # Custom dark theme + animation keyframes
│   ├── next.config.mjs              # Image domains + API proxy rewrites
│   └── package.json                 # Next.js 14 + React 18
│
├── scripts/
│   ├── historical_import.py         # Full TMDB catalog import + FAISS build
│   ├── importindexonly.py           # Rebuild FAISS index from existing DB data
│   └── weekly_sync.py              # Incremental weekly sync (TMDB changes API)
│
├── hf_deploy/                       # Hugging Face Spaces deployment (backend mirror)
│
├── .github/
│   └── workflows/
│       └── weekly_sync.yml          # Cron job: 2 AM UTC every Sunday
│
├── docker-compose.yml               # Backend + Frontend containers
├── .env.example                     # Template environment variables
└── .gitignore                       # Python, Node, ML artifacts
```

---

## 🔌 API Reference

Base URL: `https://pritu16345-cinerecs-api.hf.space`

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create account → returns access + refresh JWT |
| `POST` | `/auth/login` | — | Login → returns access + refresh JWT |
| `POST` | `/auth/refresh` | — | Exchange refresh token for new access token |

### Movies

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/movies/trending` | — | Trending movies (cached 1hr) |
| `GET` | `/movies/search?q=...&limit=20` | — | Title search (ILIKE) |
| `GET` | `/movies/semantic?q=...&limit=10` | — | Semantic vector search (FAISS) |
| `GET` | `/movies/autocomplete?q=...&limit=5` | — | Fast prefix suggestions |
| `GET` | `/movies/{tmdb_id}` | — | Full movie details |

### Recommendations

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/recommend/similar/{tmdb_id}` | — | Content-based (FAISS similarity) |
| `GET` | `/recommend/user/{user_id}` | — | Collaborative filtering |
| `GET` | `/recommend/hybrid/{movie_id}/{user_id}` | — | Blended 0.6C + 0.4CF |

### Ratings & Watchlist

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/ratings` | 🔒 | Get user's ratings |
| `POST` | `/ratings` | 🔒 | Submit/update a rating (1–5) |
| `GET` | `/ratings/stats` | 🔒 | Aggregate stats (count, avg, top genre) |
| `GET` | `/watchlist` | 🔒 | Get user's watchlist |
| `POST` | `/watchlist` | 🔒 | Add movie to watchlist |
| `DELETE` | `/watchlist/{movie_id}` | 🔒 | Remove from watchlist |

### Health

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service info |
| `GET` | `/health` | DB / Redis / FAISS status |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

---

## 🔄 Weekly Sync Pipeline

CineRecs automatically stays up-to-date via a GitHub Actions cron job that runs every Sunday:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│  TMDB API   │────▶│  Fetch       │────▶│  Rebuild     │────▶│  Upload    │
│  /changes   │     │  Changed     │     │  FAISS       │     │  to B2     │
│  endpoint   │     │  Movies      │     │  Index       │     │            │
└─────────────┘     └──────────────┘     └──────────────┘     └────────────┘
     weekly at             upsert to            encode all          push 3 files:
     2:00 AM UTC           Supabase DB          76K+ movies         index, map, emb
     every Sunday
```

**Schedule:** Every Sunday at 2:00 AM UTC  
**Trigger:** Also supports manual `workflow_dispatch`  
**Script:** `scripts/weekly_sync.py`

---

## 🐳 Docker Deployment

```bash
# Build and start both services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The `docker-compose.yml` configures:
- **Backend** on port `8000` with health checks (30s interval)
- **Frontend** on port `3000` with API proxy to backend
- Hot-reload via volume mounts for development

---

## 🧪 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TMDB_API_KEY` | ✅ | TMDB API key for movie data |
| `DATABASE_URL` | ✅ | PostgreSQL connection string (Supabase / CockroachDB / local) |
| `UPSTASH_REDIS_URL` | ✅ | Redis connection URL |
| `UPSTASH_REDIS_TOKEN` | ⬜ | Redis auth token (if using Upstash) |
| `R2_ACCESS_KEY_ID` | ✅ | S3-compatible storage key ID |
| `R2_SECRET_ACCESS_KEY` | ✅ | S3-compatible storage secret |
| `R2_ENDPOINT_URL` | ✅ | S3-compatible endpoint URL |
| `R2_BUCKET_NAME` | ⬜ | Bucket name (default: `cinerecs`) |
| `JWT_SECRET` | ✅ | Secret key for JWT signing (min 32 chars) |
| `NEXT_PUBLIC_API_URL` | ⬜ | Backend URL (default: `http://localhost:8000`) |
| `FRONTEND_URL` | ⬜ | Frontend URL for CORS (default: `http://localhost:3000`) |

---

## 📊 Performance

| Metric | Value |
|---|---|
| Semantic search latency | ~80ms (after model warm-up) |
| Keyword search latency | ~15ms |
| Autocomplete latency | ~10ms |
| FAISS index size | ~116MB (76K movies, 384-dim) |
| Redis cache hit rate | ~85% for trending/search |
| Cold start (first request) | ~8s (model loading) |
| Warm start | < 500ms |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

## 🙏 Acknowledgments

- **[TMDB](https://www.themoviedb.org/)** — Movie data and poster images
- **[FAISS](https://github.com/facebookresearch/faiss)** — Efficient similarity search by Meta AI
- **[Sentence-Transformers](https://www.sbert.net/)** — Pre-trained NLP models
- **[Supabase](https://supabase.com/)** — Managed PostgreSQL database
- **[Upstash](https://upstash.com/)** — Serverless Redis
- **[Backblaze B2](https://www.backblaze.com/)** — S3-compatible object storage

---

<div align="center">

**Built with ❤️ by [Pritam](https://github.com/Pritam16345)**

*If this project helped you, consider giving it a ⭐*

</div>
