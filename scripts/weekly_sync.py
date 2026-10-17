"""
CineRecs — Weekly Sync Script.
Discover new releases, fetch TMDB metadata, update database, and incrementally rebuild FAISS index.
"""

import os, sys, json, time, asyncio, logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx, asyncpg, numpy as np, faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-8s │ %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("sync")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
MODEL_NAME = "all-MiniLM-L6-v2"

_rate_lock = asyncio.Lock()
_request_times: list[float] = []

# Save index here so GitHub Actions can push to HF
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"


async def rate_limit():
    """Stay safely under TMDB rate limit (40 req / 10s) with thread/coroutine lock."""
    async with _rate_lock:
        now = time.time()
        while _request_times and _request_times[0] < now - 10.0:
            _request_times.pop(0)
        if len(_request_times) >= 38:
            sleep_time = _request_times[0] + 10.0 - now + 0.25
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        _request_times.append(time.time())


async def tmdb_get(client: httpx.AsyncClient, endpoint: str, params: dict | None = None) -> dict | None:
    """Make rate-limited GET request to TMDB."""
    await rate_limit()
    p = {"api_key": TMDB_API_KEY}
    if params:
        p.update(params)
    try:
        resp = await client.get(f"{TMDB_BASE}{endpoint}", params=p, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"TMDB error {endpoint}: {e}")
        return None


def parse_movie(data: dict) -> dict:
    """Parse TMDB movie object into structured format."""
    genres = [g["name"] for g in data.get("genres", [])] if "genres" in data else []
    cast_list, director = [], None
    credits = data.get("credits", {})
    if credits:
        cast_list = [p.get("name", "") for p in credits.get("cast", [])[:10]]
        for p in credits.get("crew", []):
            if p.get("job") == "Director":
                director = p.get("name", "")
                break
    rd = None
    if data.get("release_date"):
        try:
            rd = date.fromisoformat(data["release_date"])
        except ValueError:
            pass
    pp = data.get("poster_path")
    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title", "Untitled"),
        "overview": data.get("overview", ""),
        "genres": genres,
        "cast": cast_list,
        "director": director,
        "release_date": rd,
        "rating": float(data.get("vote_average", 0)),
        "popularity": float(data.get("popularity", 0)),
        "poster_url": f"{POSTER_BASE}{pp}" if pp else None,
        "language": data.get("original_language", "en"),
    }


UPSERT_SQL = """
INSERT INTO movies (tmdb_id, title, overview, genres, "cast", director, release_date, rating, popularity, poster_url, language, updated_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
ON CONFLICT (tmdb_id) DO UPDATE SET
    title = EXCLUDED.title,
    overview = COALESCE(EXCLUDED.overview, movies.overview),
    genres = COALESCE(EXCLUDED.genres, movies.genres),
    "cast" = COALESCE(EXCLUDED."cast", movies."cast"),
    director = COALESCE(EXCLUDED.director, movies.director),
    release_date = COALESCE(EXCLUDED.release_date, movies.release_date),
    rating = COALESCE(EXCLUDED.rating, movies.rating),
    popularity = COALESCE(EXCLUDED.popularity, movies.popularity),
    poster_url = COALESCE(EXCLUDED.poster_url, movies.poster_url),
    language = COALESCE(EXCLUDED.language, movies.language),
    updated_at = now()
"""


def save_index_locally(idx: Any, id_map: list[int], emb: np.ndarray):
    """Save rebuilt index to backend/data/ for HF push."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(idx, str(LOCAL_DATA_DIR / "faiss_index.bin"))
    with open(LOCAL_DATA_DIR / "movie_id_map.json", "w") as f:
        json.dump(id_map, f)
    np.save(str(LOCAL_DATA_DIR / "embeddings.npy"), emb)
    logger.info(f"Index successfully saved to {LOCAL_DATA_DIR}")


async def main():
    t0 = time.time()
    if not TMDB_API_KEY or not DATABASE_URL:
        sys.exit("Critical environment variables missing (TMDB_API_KEY or DATABASE_URL)")

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=5)
    if pool is None:
        sys.exit("Failed to create database connection pool")

    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    two_months_ago = (date.today() - timedelta(days=60)).isoformat()

    async with httpx.AsyncClient() as client:
        # 1. Discover new and trending movies from TMDB
        logger.info(f"Syncing changes and discovering new movies for week of {today}")
        candidate_ids = set()

        # A. Weekly & Daily Trending
        for p in range(1, 4):
            data = await tmdb_get(client, "/trending/movie/week", {"page": str(p)})
            if data and data.get("results"):
                for m in data["results"]:
                    if m.get("id"): candidate_ids.add(m["id"])

        data = await tmdb_get(client, "/trending/movie/day", {"page": "1"})
        if data and data.get("results"):
            for m in data["results"]:
                if m.get("id"): candidate_ids.add(m["id"])

        # B. Now Playing in theaters
        for p in range(1, 4):
            data = await tmdb_get(client, "/movie/now_playing", {"page": str(p)})
            if data and data.get("results"):
                for m in data["results"]:
                    if m.get("id"): candidate_ids.add(m["id"])

        # C. Popular movies
        for p in range(1, 4):
            data = await tmdb_get(client, "/movie/popular", {"page": str(p)})
            if data and data.get("results"):
                for m in data["results"]:
                    if m.get("id"): candidate_ids.add(m["id"])

        # D. Recent releases from last 60 days
        for p in range(1, 4):
            data = await tmdb_get(client, "/discover/movie", {
                "primary_release_date.gte": two_months_ago,
                "primary_release_date.lte": today,
                "sort_by": "popularity.desc",
                "page": str(p)
            })
            if data and data.get("results"):
                for m in data["results"]:
                    if m.get("id"): candidate_ids.add(m["id"])

        logger.info(f"Discovered {len(candidate_ids)} candidate movies from trending/now_playing/popular/recent")

        # E. Also check changes for existing tracked movies (cap to 15 pages max to avoid hanging)
        existing_rows = await pool.fetch("SELECT tmdb_id FROM movies WHERE popularity > 4.0")
        existing_ids = {r["tmdb_id"] for r in existing_rows}

        changed_existing_ids = set()
        for p in range(1, 16):
            data = await tmdb_get(client, "/movie/changes", {
                "start_date": week_ago,
                "end_date": today,
                "page": str(p)
            })
            if not data or not data.get("results"): break
            for item in data["results"]:
                if item.get("id") and item["id"] in existing_ids:
                    changed_existing_ids.add(item["id"])
            if p >= data.get("total_pages", 1): break

        # Movies to sync = (all discovered new/popular/trending movies) | (tracked movies that changed)
        movies_to_sync = candidate_ids | changed_existing_ids
        new_ids = movies_to_sync - existing_ids
        logger.info(f"Targeting {len(movies_to_sync)} movies ({len(new_ids)} brand new additions, {len(movies_to_sync - new_ids)} updates)")

        # 2. Fetch full metadata in parallel batches
        semaphore = asyncio.Semaphore(6)

        async def fetch_one(tid: int):
            async with semaphore:
                data = await tmdb_get(client, f"/movie/{tid}", {"append_to_response": "credits,keywords"})
                if data and data.get("id"):
                    return parse_movie(data)
                return None

        logger.info(f"Fetching metadata for {len(movies_to_sync)} movies with pipelined workers...")
        tasks = [fetch_one(tid) for tid in movies_to_sync]
        results = await asyncio.gather(*tasks)

        parsed_movies = [m for m in results if m is not None]
        updated_tmdb_ids = {m["tmdb_id"] for m in parsed_movies}

        if parsed_movies:
            logger.info(f"Upserting {len(parsed_movies)} movies into database using single batch transaction...")
            params = [
                (
                    m["tmdb_id"], m["title"], m["overview"], m["genres"],
                    m["cast"], m["director"], m["release_date"], m["rating"],
                    m["popularity"], m["poster_url"], m["language"]
                )
                for m in parsed_movies
            ]
            async with pool.acquire() as conn:
                await conn.executemany(UPSERT_SQL, params)

        logger.info(f"DB update complete: {len(parsed_movies)} OK, {len(movies_to_sync) - len(parsed_movies)} FAIL")

    # 3. Rebuild FAISS index incrementally
    logger.info("Rebuilding FAISS vector index...")
    rows = await pool.fetch('SELECT tmdb_id, title, overview, genres, "cast" FROM movies ORDER BY tmdb_id')
    movies = [
        {
            "tmdb_id": r["tmdb_id"],
            "title": r["title"],
            "overview": r.get("overview", ""),
            "genres": list(r.get("genres") or []),
            "cast": list(r.get("cast") or [])
        }
        for r in rows
    ]

    if movies:
        existing_emb = None
        existing_map = None
        
        local_emb_path = LOCAL_DATA_DIR / "embeddings.npy"
        local_map_path = LOCAL_DATA_DIR / "movie_id_map.json"
        
        # A. Check local directory first
        if local_emb_path.exists() and local_map_path.exists():
            try:
                logger.info("Loading existing embeddings and map from local directory...")
                existing_emb = np.load(str(local_emb_path))
                with open(local_map_path, "r") as f:
                    existing_map = json.load(f)
                logger.info(f"Loaded local index files (embeddings shape: {existing_emb.shape})")
            except Exception as e:
                logger.warning(f"Failed to load local index files: {e}")
                existing_emb = None
                existing_map = None

        # B. If not local, try Cloudflare R2 bucket
        if existing_emb is None or existing_map is None:
            R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
            R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
            R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
            R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "cinerecs")
            if all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
                try:
                    import boto3
                    logger.info("Downloading existing index files from Cloudflare R2...")
                    s3 = boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, region_name="auto")
                    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
                    s3.download_file(R2_BUCKET_NAME, "embeddings.npy", str(local_emb_path))
                    s3.download_file(R2_BUCKET_NAME, "movie_id_map.json", str(local_map_path))
                    existing_emb = np.load(str(local_emb_path))
                    with open(local_map_path, "r") as f:
                        existing_map = json.load(f)
                    logger.info(f"Successfully loaded R2 index files (embeddings shape: {existing_emb.shape})")
                except Exception as e:
                    logger.warning(f"Failed to download index files from R2: {e}")

        # C. If still not loaded, download from Hugging Face Space using huggingface_hub (properly resolves Git LFS)
        if existing_emb is None or existing_map is None:
            try:
                from huggingface_hub import hf_hub_download
                logger.info("Downloading existing index files from Hugging Face Space via hf_hub_download...")
                map_file = hf_hub_download(repo_id="Pritu16345/cinerecs-api", filename="data/movie_id_map.json", repo_type="space")
                emb_file = hf_hub_download(repo_id="Pritu16345/cinerecs-api", filename="data/embeddings.npy", repo_type="space")
                with open(map_file, "r") as f:
                    existing_map = json.load(f)
                existing_emb = np.load(emb_file)
                logger.info(f"Successfully loaded HF index files (embeddings shape: {existing_emb.shape})")
            except Exception as e:
                logger.warning(f"Could not load index files via hf_hub_download: {e}")
                existing_emb = None
                existing_map = None

        # Build map of tmdb_id -> index in existing_emb
        id_to_idx = {}
        if existing_map is not None and existing_emb is not None:
            id_to_idx = {tid: idx for idx, tid in enumerate(existing_map)}

        # Prepare text representations and identify which need encoding
        id_map = []
        texts_to_encode = []
        indices_to_encode = []
        
        dim = 384  # all-MiniLM-L6-v2 dimension
        new_emb = np.zeros((len(movies), dim), dtype=np.float32)
        
        for i, m in enumerate(movies):
            tid = m["tmdb_id"]
            id_map.append(tid)
            
            g = " ".join(m.get("genres") or [])
            c = " ".join((m.get("cast") or [])[:5])
            text = f"{m['title']} {m.get('overview','')} {g} {c}"
            
            # If movie was not updated this run and exists in the loaded map
            if existing_emb is not None and tid in id_to_idx and tid not in updated_tmdb_ids:
                old_idx = id_to_idx[tid]
                new_emb[i] = existing_emb[old_idx]
            else:
                texts_to_encode.append(text)
                indices_to_encode.append(i)

        logger.info(f"Reused {len(movies) - len(indices_to_encode)} embeddings. Encoding {len(indices_to_encode)} new/updated movies.")

        # Encode new/updated movies only
        if indices_to_encode:
            logger.info(f"Generating embeddings for {len(indices_to_encode)} movies...")
            model = SentenceTransformer(MODEL_NAME)
            encoded = np.asarray(model.encode(texts_to_encode, show_progress_bar=False, convert_to_numpy=True, batch_size=128), dtype=np.float32)
            for local_idx, global_idx in enumerate(indices_to_encode):
                new_emb[global_idx] = encoded[local_idx]

        # Normalize and create FAISS index
        faiss.normalize_L2(new_emb)
        idx: Any = faiss.IndexFlatIP(new_emb.shape[1])
        idx.add(new_emb)

        # Save locally to backend/data/
        save_index_locally(idx, id_map, new_emb)

        # Update embedding indices in DB ONLY for newly added or updated movies (avoids updating 15k unchanged rows)
        new_indices = [(i, tid) for i, tid in enumerate(id_map) if tid in updated_tmdb_ids or tid in new_ids]
        if new_indices:
            logger.info(f"Updating embedding indices in DB for {len(new_indices)} new/updated movies...")
            async with pool.acquire() as conn:
                await conn.executemany(
                    "UPDATE movies SET embedding_idx=$1 WHERE tmdb_id=$2",
                    new_indices
                )

        # Optional R2 backup
        R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
        R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
        R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
        R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "cinerecs")

        if all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
            try:
                import boto3
                s3 = boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, region_name="auto")
                s3.upload_file(str(LOCAL_DATA_DIR / "faiss_index.bin"), R2_BUCKET_NAME, "faiss_index.bin")
                s3.upload_file(str(LOCAL_DATA_DIR / "movie_id_map.json"), R2_BUCKET_NAME, "movie_id_map.json")
                s3.upload_file(str(LOCAL_DATA_DIR / "embeddings.npy"), R2_BUCKET_NAME, "embeddings.npy")
                logger.info("Optional Cloudflare R2 backup successful")
            except Exception as e:
                logger.warning(f"Optional R2 backup skipped/failed: {e}")

        # Optional direct Hugging Face Space upload via HfApi (handles LFS and chunking cleanly)
        HF_TOKEN = os.getenv("HF_TOKEN")
        if HF_TOKEN:
            try:
                from huggingface_hub import HfApi
                logger.info("Uploading updated index files to Hugging Face Space via HfApi...")
                hf_api = HfApi(token=HF_TOKEN)
                hf_api.upload_folder(
                    folder_path=str(LOCAL_DATA_DIR),
                    path_in_repo="data",
                    repo_id="Pritu16345/cinerecs-api",
                    repo_type="space",
                    commit_message="weekly index update"
                )
                logger.info("Successfully pushed updated index to Hugging Face Space via HfApi")
            except Exception as e:
                logger.warning(f"HfApi upload fallback skipped: {e}")

        # Invalidate Redis cache so new trending and recommendations show up immediately
        UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
        UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN")
        if UPSTASH_REDIS_URL:
            try:
                import redis.asyncio as aioredis
                rc = aioredis.from_url(
                    UPSTASH_REDIS_URL,
                    password=UPSTASH_REDIS_TOKEN if UPSTASH_REDIS_TOKEN else None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                await rc.delete("movies:trending:v3")
                logger.info("Successfully cleared Redis trending cache")
                await rc.close()
            except Exception as e:
                logger.warning(f"Redis cache invalidation skipped/failed: {e}")

        logger.info(f"Index rebuilt successfully with {len(movies)} total movies")

    await pool.close()
    logger.info(f"Weekly sync completed successfully in {round(time.time() - t0, 1)}s")


if __name__ == "__main__":
    asyncio.run(main())