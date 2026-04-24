<div align="center">

# 🎬 CineRecs

### AI-Powered Movie Recommendation Engine

[![Daily Sync](https://img.shields.io/github/actions/workflow/status/Pritam16345/movie-recommender-app/daily_sync.yml?label=Daily%20Sync&logo=githubactions&logoColor=white&style=for-the-badge)](https://github.com/Pritam16345/movie-recommender-app/actions/workflows/daily_sync.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

**Discover your next favorite movie.**  
A production-grade hybrid recommendation system combining semantic vector search (FAISS) with user-based collaborative filtering, backed by 100K+ movies from the TMDB catalog.

[Live Demo](#) · [API Docs](#api-reference) · [Report Bug](../../issues) · [Request Feature](../../issues)

---

</div>

## ⚡ Highlights

| Feature | Details |
|---|---|
| 🧠 **Hybrid Recommendations** | `0.6× Content-Based (FAISS)` + `0.4× Collaborative Filtering` — blended scoring for superior accuracy |
| 🔍 **Semantic Search** | Natural language queries powered by `all-MiniLM-L6-v2` sentence transformer |
| ⌨️ **Real-time Autocomplete** | Prefix-matching suggestions with `< 50ms` response times |
| 📦 **100K+ Movies** | Complete TMDB catalog with automated daily sync via GitHub Actions |
| 🚀 **Optimized Cold Start** | Local FAISS index caching — sub-second backend restarts after first load |
| 🎨 **Premium UI** | Glassmorphism dark theme, smooth micro-animations, fully responsive design |
| 🔐 **Auth System** | JWT-based authentication with bcrypt password hashing (7-day token expiry) |
| ⭐ **Personalization** | User ratings, watchlist management, and per-user recommendation stats |

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
     │ Cloudflare │                │   Upstash   │
     │     R2     │                │    Redis    │
     │  (S3/B2)   │                │   (Cache)   │
     └────────────┘                └─────────────┘
           │
     ┌─────▼──────────────┐
     │   CockroachDB      │
     │   (PostgreSQL)     │
     │   Serverless       │
     └────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Next.js 14, Tailwind CSS, React 18 | Server-side rendering, glassmorphism UI, responsive design |
| **Backend** | FastAPI, AsyncPG, Pydantic v2 | Async REST API, request validation, auto-generated OpenAPI docs |
| **ML/Search** | FAISS, Sentence-Transformers (`all-MiniLM-L6-v2`) | Semantic embeddings, cosine similarity search |
| **Database** | CockroachDB (PostgreSQL-compatible) | Distributed SQL storage with serverless scaling |
| **Cache** | Upstash Redis | Sub-millisecond caching for search results and recommendations |
| **Object Storage** | Cloudflare R2 / Backblaze B2 | Persistent storage for FAISS index, embeddings, and ID maps |
| **CI/CD** | GitHub Actions | Automated daily TMDB sync at 2:00 AM UTC |
| **Auth** | JWT (python-jose) + bcrypt (passlib) | Stateless authentication with 7-day token expiry |
| **Containerization** | Docker + Docker Compose | One-command local deployment |

---

## 🧠 How Recommendations Work

CineRecs uses a **three-strategy** recommendation engine:

### 1. Content-Based Filtering (FAISS)

Each movie is encoded into a 384-dimensional embedding vector using `all-MiniLM-L6-v2`:

```
embedding = encode(title + overview + genres + cast)
```

When you request similar movies, CineRecs performs an **inner-product similarity search** across all 100K+ vectors using Facebook's FAISS library, returning the top-k most semantically similar movies in milliseconds.

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

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** — [Download](https://python.org/downloads)
- **Node.js 18+** — [Download](https://nodejs.org)
- **Docker** *(optional)* — [Download](https://docker.com/get-started)

You'll also need accounts (all have free tiers):

| Service | Purpose | Sign Up |
|---|---|---|
| **TMDB** | Movie data API | [themoviedb.org](https://www.themoviedb.org/settings/api) |
| **CockroachDB** | PostgreSQL database | [cockroachlabs.com](https://cockroachlabs.com/free-tier) |
| **Upstash** | Redis cache | [upstash.com](https://upstash.com) |
| **Cloudflare R2** / **Backblaze B2** | Object storage for FAISS | [cloudflare.com](https://dash.cloudflare.com) / [backblaze.com](https://www.backblaze.com/b2/sign-up.html) |

---

## 🚀 Getting Started

### 1. Clone & Configure

```bash
git clone https://github.com/Pritam16345/movie-recommender-app.git
cd movie-recommender-app
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
# TMDB API (required)
TMDB_API_KEY=your_tmdb_api_key

# CockroachDB connection string
DATABASE_URL=postgresql://user:password@host:26257/defaultdb?sslmode=verify-full

# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:token@endpoint:6379
UPSTASH_REDIS_TOKEN=your_upstash_token

# Object Storage (S3-compatible)
R2_ACCESS_KEY_ID=your_key_id
R2_SECRET_ACCESS_KEY=your_secret_key
R2_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
R2_BUCKET_NAME=cinerecs

# JWT Secret (generate: openssl rand -hex 32)
JWT_SECRET=your_random_jwt_secret_at_least_32_chars

# Frontend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### 2. Populate the Database

Run the historical import to fetch ~100K movies from TMDB, store them in CockroachDB, build the FAISS index, and upload it to R2:

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
│   ├── auth.py                     # JWT creation/verification, bcrypt hashing
│   ├── models.py                   # Pydantic schemas (request/response validation)
│   ├── Dockerfile                  # Python 3.11-slim container
│   ├── requirements.txt            # Pinned Python dependencies
│   │
│   ├── routers/
│   │   ├── auth.py                 # POST /auth/register, POST /auth/login
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
│   │   ├── AuthProvider.js          # React context for auth state
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
│   │   └── api.js                   # API client with auth token injection
│   │
│   ├── tailwind.config.js           # Custom dark theme + animation keyframes
│   ├── next.config.mjs              # Image domains + API proxy rewrites
│   └── package.json                 # Next.js 14 + React 18
│
├── scripts/
│   ├── historical_import.py         # Full TMDB catalog import + FAISS build
│   └── daily_sync.py                # Incremental sync (TMDB changes API)
│
├── .github/
│   └── workflows/
│       └── daily_sync.yml           # Cron job: 2 AM UTC daily
│
├── docker-compose.yml               # Backend + Frontend containers
├── .env.example                     # Template environment variables
└── .gitignore                       # Python, Node, ML artifacts
```

---

## 🔌 API Reference

Base URL: `http://localhost:8000`

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create account → returns JWT |
| `POST` | `/auth/login` | — | Login → returns JWT |

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

## 🔄 Daily Sync Pipeline

CineRecs automatically stays up-to-date via a GitHub Actions cron job:

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌────────────┐
│  TMDB API   │────▶│  Fetch       │────▶│  Rebuild     │────▶│  Upload    │
│  /changes   │     │  Changed     │     │  FAISS       │     │  to R2     │
│  endpoint   │     │  Movies      │     │  Index       │     │            │
└─────────────┘     └──────────────┘     └──────────────┘     └────────────┘
     daily at              upsert to            encode all          push 3 files:
     2:00 AM UTC           CockroachDB          100K+ movies        index, map, emb
```

**Schedule:** Every day at 2:00 AM UTC  
**Trigger:** Also supports manual `workflow_dispatch`  
**Script:** `scripts/daily_sync.py`

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
| `DATABASE_URL` | ✅ | CockroachDB/PostgreSQL connection string |
| `UPSTASH_REDIS_URL` | ✅ | Redis connection URL |
| `UPSTASH_REDIS_TOKEN` | ⬜ | Redis auth token (if using Upstash) |
| `R2_ACCESS_KEY_ID` | ✅ | S3-compatible storage key ID |
| `R2_SECRET_ACCESS_KEY` | ✅ | S3-compatible storage secret |
| `R2_ENDPOINT_URL` | ✅ | S3-compatible endpoint URL |
| `R2_BUCKET_NAME` | ⬜ | Bucket name (default: `cinerecs`) |
| `JWT_SECRET` | ✅ | Secret key for JWT signing |
| `NEXT_PUBLIC_API_URL` | ⬜ | Backend URL (default: `http://localhost:8000`) |
| `FRONTEND_URL` | ⬜ | Frontend URL for CORS (default: `http://localhost:3000`) |

---

## 📊 Performance

| Metric | Value |
|---|---|
| Semantic search latency | ~80ms (after model warm-up) |
| Keyword search latency | ~15ms |
| Autocomplete latency | ~10ms |
| FAISS index size | ~150MB (100K movies, 384-dim) |
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
- **[CockroachDB](https://www.cockroachlabs.com/)** — Distributed PostgreSQL
- **[Upstash](https://upstash.com/)** — Serverless Redis

---

<div align="center">

**Built with ❤️ by [Pritam](https://github.com/Pritam16345)**

*If this project helped you, consider giving it a ⭐*

</div>
