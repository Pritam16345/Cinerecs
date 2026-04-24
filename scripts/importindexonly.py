"""
CineRecs — Historical Import Script.
Populate DB from TMDB and build FAISS index.
"""

import os, sys, json, time, asyncio, logging, shutil, argparse
from datetime import date
from pathlib import Path

import httpx, asyncpg, numpy as np, faiss, boto3
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s │ %(levelname)-8s │ %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("import")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "cinerecs")
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
MODEL_NAME = "all-MiniLM-L6-v2"
_request_times: list[float] = []

# Where to save index files locally
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    tmdb_id INT PRIMARY KEY, title TEXT NOT NULL, overview TEXT,
    genres TEXT[], "cast" TEXT[], director TEXT, release_date DATE,
    rating FLOAT DEFAULT 0, popularity FLOAT DEFAULT 0,
    poster_url TEXT, language TEXT, embedding_idx INT,
    updated_at TIMESTAMPTZ DEFAULT now()
);
"""


async def rate_limit():
    now = time.time()
    while _request_times and _request_times[0] < now - 10.0:
        _request_times.pop(0)
    if len(_request_times) >= 40:
        sleep_time = _request_times[0] + 10.0 - now + 0.2
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
    _request_times.append(time.time())


async def tmdb_get(client, endpoint, params=None):
    await rate_limit()
    url = f"{TMDB_BASE}{endpoint}"
    p = {"api_key": TMDB_API_KEY}
    if params: p.update(params)
    for attempt in range(3):
        try:
            resp = await client.get(url, params=p, timeout=20.0)
            if resp.status_code == 429:
                await asyncio.sleep(5)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2: logger.warning(f"TMDB fail {endpoint}: {e}")
            await asyncio.sleep(2)
    return None


def parse_movie(data):
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
        try: rd = date.fromisoformat(data["release_date"])
        except ValueError: pass
    pp = data.get("poster_path")
    return {
        "tmdb_id": data.get("id"), "title": data.get("title", "Untitled"),
        "overview": data.get("overview", ""), "genres": genres, "cast": cast_list,
        "director": director, "release_date": rd,
        "rating": float(data.get("vote_average", 0)),
        "popularity": float(data.get("popularity", 0)),
        "poster_url": f"{POSTER_BASE}{pp}" if pp else None,
        "language": data.get("original_language", "en"),
    }


async def collect_ids(client, target=80000):
    ids = set()
    logger.info(f"Target: {target} IDs")
    current_year = date.today().year
    years = list(range(current_year, 1950, -1))
    for year in years:
        if len(ids) >= target: break
        logger.info(f"Year: {year}")
        if year >= 2015: max_pages, min_votes = 150, 1
        elif year >= 2000: max_pages, min_votes = 80, 5
        elif year >= 1980: max_pages, min_votes = 50, 20
        else: max_pages, min_votes = 20, 50
        for page in range(1, max_pages + 1):
            if len(ids) >= target: break
            data = await tmdb_get(client, "/discover/movie", {
                "page": str(page), "primary_release_year": str(year),
                "sort_by": "popularity.desc", "vote_count.gte": str(min_votes)
            })
            if not data or not data.get("results"): break
            for m in data["results"]: ids.add(m["id"])
            if page % 20 == 0: logger.info(f"  Count: {len(ids)}")
    for name, ep in [("popular", "/movie/popular"), ("top_rated", "/movie/top_rated")]:
        if len(ids) >= target + 5000: break
        logger.info(f"Filling gaps via {name}")
        for p in range(1, 51):
            data = await tmdb_get(client, ep, {"page": str(p)})
            if not data or not data.get("results"): break
            for m in data["results"]: ids.add(m["id"])
    return ids


UPSERT_SQL = """
INSERT INTO movies (tmdb_id,title,overview,genres,"cast",director,release_date,rating,popularity,poster_url,language,updated_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,now())
ON CONFLICT (tmdb_id) DO UPDATE SET title=EXCLUDED.title, overview=COALESCE(EXCLUDED.overview,movies.overview),
genres=COALESCE(EXCLUDED.genres,movies.genres), "cast"=COALESCE(EXCLUDED."cast",movies."cast"),
director=COALESCE(EXCLUDED.director,movies.director), release_date=COALESCE(EXCLUDED.release_date,movies.release_date),
rating=COALESCE(EXCLUDED.rating,movies.rating), popularity=COALESCE(EXCLUDED.popularity,movies.popularity),
poster_url=COALESCE(EXCLUDED.poster_url,movies.poster_url), language=COALESCE(EXCLUDED.language,movies.language), updated_at=now()
"""


async def fetch_and_store(pool, client, movie_ids):
    batch, count, errors, total = [], 0, 0, len(movie_ids)
    start_time = time.time()
    for i, tid in enumerate(movie_ids, 1):
        data = await tmdb_get(client, f"/movie/{tid}", {"append_to_response": "credits,keywords"})
        if data and data.get("id"): batch.append(parse_movie(data))
        else: errors += 1
        if i % 50 == 0 or i == total:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            remaining = (total - i) / rate if rate > 0 else 0
            logger.info(f"[{i}/{total}] {(i/total)*100:.1f}% | Rate: {rate:.1f} m/s | ETA: {int(remaining//60)}m")
        if len(batch) >= 200 or i == total:
            if batch:
                async with pool.acquire() as conn:
                    for m in batch:
                        try:
                            await conn.execute(UPSERT_SQL, m["tmdb_id"], m["title"], m["overview"], m["genres"], m["cast"], m["director"], m["release_date"], m["rating"], m["popularity"], m["poster_url"], m["language"])
                            count += 1
                        except Exception as e:
                            logger.warning(f"DB error: {e}"); errors += 1
                batch = []
    return count


def build_faiss_index(movies):
    logger.info(f"Indexing {len(movies)} movies...")
    model = SentenceTransformer(MODEL_NAME)
    texts, id_map = [], []
    for m in movies:
        g, c = " ".join(m.get("genres") or []), " ".join((m.get("cast") or [])[:5])
        texts.append(f"{m['title']} {m.get('overview','')} {g} {c}")
        id_map.append(m["tmdb_id"])
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, batch_size=256).astype(np.float32)
    faiss.normalize_L2(emb)
    idx = faiss.IndexFlatIP(emb.shape[1])
    idx.add(emb)
    return idx, id_map, emb


def save_locally(idx, id_map, emb):
    """Save index files to backend/data/ for git lfs push to HF."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(idx, str(LOCAL_DATA_DIR / "faiss_index.bin"))
    with open(LOCAL_DATA_DIR / "movie_id_map.json", "w") as f:
        json.dump(id_map, f)
    np.save(str(LOCAL_DATA_DIR / "embeddings.npy"), emb)
    logger.info(f"Saved index files to {LOCAL_DATA_DIR}")


def upload_r2(local_path, r2_key):
    try:
        s3 = boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, region_name="auto")
        s3.upload_file(local_path, R2_BUCKET_NAME, r2_key)
        logger.info(f"Uploaded {r2_key}")
        return True
    except Exception as e:
        logger.error(f"R2 fail {r2_key}: {e}"); return False


async def rebuild_index_only():
    """Skip TMDB fetch — just rebuild FAISS from existing DB data and save locally."""
    logger.info("=== REBUILD INDEX ONLY MODE ===")
    logger.info("Reading movies from DB...")

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10)
    rows = await pool.fetch('SELECT tmdb_id,title,overview,genres,"cast" FROM movies ORDER BY tmdb_id')
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
    logger.info(f"Found {len(movies)} movies in DB")

    if not movies:
        logger.error("No movies in DB. Run full import first.")
        await pool.close()
        return

    idx, id_map, emb = build_faiss_index(movies)

    # 1. Save locally to backend/data/
    save_locally(idx, id_map, emb)

    # 2. Update embedding_idx in DB
    logger.info("Updating embedding indices in DB...")
    async with pool.acquire() as conn:
        await conn.executemany(
            "UPDATE movies SET embedding_idx=$1 WHERE tmdb_id=$2",
            [(i, tid) for i, tid in enumerate(id_map)]
        )

    # 3. Optional R2 upload
    if all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        logger.info("R2 credentials found, uploading backup...")
        upload_r2(str(LOCAL_DATA_DIR / "faiss_index.bin"), "faiss_index.bin")
        upload_r2(str(LOCAL_DATA_DIR / "movie_id_map.json"), "movie_id_map.json")
        upload_r2(str(LOCAL_DATA_DIR / "embeddings.npy"), "embeddings.npy")
    else:
        logger.info("R2 credentials missing, skipping cloud backup.")

    await pool.close()
    logger.info("=== REBUILD COMPLETE ===")
    logger.info(f"Files saved to: {LOCAL_DATA_DIR}")
    logger.info("Next steps:")
    logger.info("  cd backend")
    logger.info("  git lfs install")
    logger.info('  git lfs track "data/embeddings.npy"')
    logger.info('  git lfs track "data/faiss_index.bin"')
    logger.info('  git lfs track "data/movie_id_map.json"')
    logger.info("  git add .gitattributes data/")
    logger.info('  git commit -m "add faiss index via git lfs"')
    logger.info("  git push hf main --force")


async def main():
    t0 = time.time()
    if not TMDB_API_KEY: sys.exit("TMDB_API_KEY missing")
    if not DATABASE_URL: sys.exit("DATABASE_URL missing")

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10)
    async with pool.acquire() as conn: await conn.execute(SCHEMA_SQL)

    async with httpx.AsyncClient() as client:
        ids = await collect_ids(client, target=80000)
        existing_rows = await pool.fetch("SELECT tmdb_id FROM movies")
        existing_ids = {row["tmdb_id"] for row in existing_rows}
        missing_ids = list(ids - existing_ids)
        logger.info(f"Resume: {len(ids & existing_ids)}/{len(ids)} in DB. Fetching {len(missing_ids)}.")
        if missing_ids: await fetch_and_store(pool, client, missing_ids)

    rows = await pool.fetch('SELECT tmdb_id,title,overview,genres,"cast" FROM movies ORDER BY tmdb_id')
    movies = [{"tmdb_id":r["tmdb_id"],"title":r["title"],"overview":r.get("overview",""),"genres":list(r.get("genres") or []),"cast":list(r.get("cast") or [])} for r in rows]

    if movies:
        idx, id_map, emb = build_faiss_index(movies)

        # 1. Save locally first
        save_locally(idx, id_map, emb)

        # 2. Update DB indices
        logger.info("Updating DB indices...")
        async with pool.acquire() as conn:
            await conn.executemany("UPDATE movies SET embedding_idx=$1 WHERE tmdb_id=$2", [(i, tid) for i, tid in enumerate(id_map)])

        # 3. Optional R2 upload
        if all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
            logger.info("R2 credentials found, uploading backup...")
            upload_r2(str(LOCAL_DATA_DIR / "faiss_index.bin"), "faiss_index.bin")
            upload_r2(str(LOCAL_DATA_DIR / "movie_id_map.json"), "movie_id_map.json")
            upload_r2(str(LOCAL_DATA_DIR / "embeddings.npy"), "embeddings.npy")
        else:
            logger.info("R2 credentials missing, skipping cloud backup.")

    await pool.close()
    logger.info(f"Done in {round(time.time()-t0,1)}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild-index-only", action="store_true",
                        help="Skip TMDB fetch, rebuild FAISS from existing DB and save locally")
    args = parser.parse_args()

    try:
        if args.rebuild_index_only:
            asyncio.run(rebuild_index_only())
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Cancelled by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")