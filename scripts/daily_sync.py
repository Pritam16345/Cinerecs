"""
CineRecs — Weekly Sync Script.
Fetch TMDB changes and rebuild FAISS index.
"""

import os, sys, json, time, asyncio, logging, shutil
from datetime import date, timedelta
from pathlib import Path

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
_request_times: list[float] = []

# Save index here so GitHub Actions can push to HF
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent / "backend" / "data"


async def rate_limit():
    now = time.time()
    while _request_times and _request_times[0] < now - 10.0:
        _request_times.pop(0)
    if len(_request_times) >= 40:
        sleep_time = _request_times[0] + 10.0 - now + 0.2
        if sleep_time > 0: await asyncio.sleep(sleep_time)
    _request_times.append(time.time())


async def tmdb_get(client, endpoint, params=None):
    await rate_limit()
    p = {"api_key": TMDB_API_KEY}
    if params: p.update(params)
    try:
        resp = await client.get(f"{TMDB_BASE}{endpoint}", params=p, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"TMDB error {endpoint}: {e}"); return None


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


UPSERT_SQL = """
INSERT INTO movies (tmdb_id,title,overview,genres,"cast",director,release_date,rating,popularity,poster_url,language,updated_at)
VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,now())
ON CONFLICT (tmdb_id) DO UPDATE SET title=EXCLUDED.title, overview=COALESCE(EXCLUDED.overview,movies.overview),
genres=COALESCE(EXCLUDED.genres,movies.genres), "cast"=COALESCE(EXCLUDED."cast",movies."cast"),
director=COALESCE(EXCLUDED.director,movies.director), release_date=COALESCE(EXCLUDED.release_date,movies.release_date),
rating=COALESCE(EXCLUDED.rating,movies.rating), popularity=COALESCE(EXCLUDED.popularity,movies.popularity),
poster_url=COALESCE(EXCLUDED.poster_url,movies.poster_url), language=COALESCE(EXCLUDED.language,movies.language), updated_at=now()
"""


def save_index_locally(idx, id_map, emb):
    """Save rebuilt index to backend/data/ for HF push."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(idx, str(LOCAL_DATA_DIR / "faiss_index.bin"))
    with open(LOCAL_DATA_DIR / "movie_id_map.json", "w") as f:
        json.dump(id_map, f)
    np.save(str(LOCAL_DATA_DIR / "embeddings.npy"), emb)
    logger.info(f"Index saved to {LOCAL_DATA_DIR}")


async def main():
    t0 = time.time()
    if not TMDB_API_KEY or not DATABASE_URL:
        sys.exit("Env vars missing")

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=5)

    # 1. Get changes from last 7 days (weekly sync)
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    async with httpx.AsyncClient() as client:
        logger.info(f"Syncing changes from {week_ago} to {today}")
        changed_ids, page = set(), 1
        while True:
            data = await tmdb_get(client, "/movie/changes", {
                "start_date": week_ago,
                "end_date": today,
                "page": str(page)
            })
            if not data or not data.get("results"): break
            for item in data["results"]:
                if item.get("id"): changed_ids.add(item["id"])
            if page >= data.get("total_pages", 1): break
            page += 1

        logger.info(f"Updating {len(changed_ids)} movies")

        # 2. Update DB
        count, errors = 0, 0
        for tid in changed_ids:
            data = await tmdb_get(client, f"/movie/{tid}", {"append_to_response": "credits,keywords"})
            if data and data.get("id"):
                m = parse_movie(data)
                try:
                    async with pool.acquire() as conn:
                        await conn.execute(UPSERT_SQL, m["tmdb_id"], m["title"], m["overview"],
                            m["genres"], m["cast"], m["director"], m["release_date"],
                            m["rating"], m["popularity"], m["poster_url"], m["language"])
                    count += 1
                except Exception as e:
                    logger.warning(f"DB error {tid}: {e}"); errors += 1
            else:
                errors += 1

    logger.info(f"DB update: {count} OK, {errors} FAIL")

    # 3. Rebuild FAISS index
    logger.info("Rebuilding FAISS index...")
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

    if movies:
        model = SentenceTransformer(MODEL_NAME)
        texts, id_map = [], []
        for m in movies:
            g = " ".join(m.get("genres") or [])
            c = " ".join((m.get("cast") or [])[:5])
            texts.append(f"{m['title']} {m.get('overview','')} {g} {c}")
            id_map.append(m["tmdb_id"])

        emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, batch_size=256).astype(np.float32)
        faiss.normalize_L2(emb)
        idx = faiss.IndexFlatIP(emb.shape[1])
        idx.add(emb)

        # Save locally to backend/data/ — GitHub Actions will push this to HF
        save_index_locally(idx, id_map, emb)

        # Update embedding indices in DB
        async with pool.acquire() as conn:
            for i, tid in enumerate(id_map):
                await conn.execute("UPDATE movies SET embedding_idx=$1 WHERE tmdb_id=$2", i, tid)

        # Optional R2 upload
        R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
        R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
        R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
        R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "cinerecs")

        if all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
            import boto3
            try:
                s3 = boto3.client("s3", endpoint_url=R2_ENDPOINT_URL, aws_access_key_id=R2_ACCESS_KEY_ID, aws_secret_access_key=R2_SECRET_ACCESS_KEY, region_name="auto")
                s3.upload_file(str(LOCAL_DATA_DIR / "faiss_index.bin"), R2_BUCKET_NAME, "faiss_index.bin")
                s3.upload_file(str(LOCAL_DATA_DIR / "movie_id_map.json"), R2_BUCKET_NAME, "movie_id_map.json")
                s3.upload_file(str(LOCAL_DATA_DIR / "embeddings.npy"), R2_BUCKET_NAME, "embeddings.npy")
                logger.info("Optional R2 backup successful")
            except Exception as e:
                logger.warning(f"Optional R2 backup failed: {e}")

        logger.info(f"Index rebuilt with {len(movies)} movies")

    await pool.close()
    logger.info(f"Sync complete in {round(time.time() - t0, 1)}s")


if __name__ == "__main__":
    asyncio.run(main())