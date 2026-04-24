"""
CineRecs — FAISS Search Service.
Handles vector search and R2 persistence.
"""

import os
import json
import logging
from pathlib import Path

import faiss
import numpy as np
import boto3
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("cinerecs.faiss")

# Configuration
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "cinerecs")

INDEX_FILE = "faiss_index.bin"
MAP_FILE = "movie_id_map.json"
EMBEDDINGS_FILE = "embeddings.npy"
MODEL_NAME = "all-MiniLM-L6-v2"


class FAISSService:
    """Semantic search via FAISS and sentence-transformers."""

    def __init__(self):
        self.index: faiss.IndexFlatIP | None = None
        self.movie_id_map: list[int] = []
        self.embeddings: np.ndarray | None = None
        self.model: SentenceTransformer | None = None
        self._loaded = False

    def load_model(self) -> None:
        """Initialize the transformer model."""
        if self.model is None:
            logger.info(f"Loading transformer: {MODEL_NAME}")
            self.model = SentenceTransformer(MODEL_NAME)

    def _get_s3_client(self):
        """Configure R2 S3 client."""
        return boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )

    def load_from_r2(self, force_refresh: bool = False) -> bool:
        """Load data from R2 or local cache."""
        if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
            logger.warning("R2 not configured, skipping load")
            return False

        try:
            s3 = self._get_s3_client()
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            index_path = data_dir / INDEX_FILE
            map_path = data_dir / MAP_FILE
            emb_path = data_dir / EMBEDDINGS_FILE

            # 1. Load FAISS index
            if not index_path.exists() or force_refresh:
                logger.info(f"Downloading {INDEX_FILE}...")
                s3.download_file(R2_BUCKET_NAME, INDEX_FILE, str(index_path))
            
            self.index = faiss.read_index(str(index_path))
            logger.info(f"FAISS loaded: {self.index.ntotal} vectors")

            # 2. Load Movie ID map
            if not map_path.exists() or force_refresh:
                logger.info(f"Downloading {MAP_FILE}...")
                s3.download_file(R2_BUCKET_NAME, MAP_FILE, str(map_path))
            
            with open(map_path, "r") as f:
                self.movie_id_map = json.load(f)

            # 3. Load Embeddings
            if not emb_path.exists() or force_refresh:
                try:
                    s3.download_file(R2_BUCKET_NAME, EMBEDDINGS_FILE, str(emb_path))
                    self.embeddings = np.load(str(emb_path))
                except Exception as e:
                    logger.warning(f"Embeddings download skipped: {e}")
            else:
                self.embeddings = np.load(str(emb_path))

            self._loaded = True
            return True

        except Exception as e:
            logger.error(f"FAISS load failed: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if service is ready."""
        return self._loaded and self.index is not None

    def encode_query(self, text: str) -> np.ndarray:
        """Convert text to normalized vector."""
        if self.model is None:
            self.load_model()
        embedding = self.model.encode([text], convert_to_numpy=True)
        faiss.normalize_L2(embedding)
        return embedding

    def search(self, query_text: str, top_k: int = 10) -> list[dict]:
        """Search by query text."""
        if not self.is_loaded():
            return []

        query_embedding = self.encode_query(query_text)
        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < 0 or idx >= len(self.movie_id_map):
                continue
            results.append({
                "tmdb_id": self.movie_id_map[idx],
                "score": float(score),
                "rank": i + 1,
            })
        return results

    def get_similar_by_id(self, tmdb_id: int, top_k: int = 10) -> list[dict]:
        """Find movies similar to target ID."""
        if not self.is_loaded():
            return []

        try:
            idx = self.movie_id_map.index(tmdb_id)
        except ValueError:
            return []

        if self.embeddings is not None:
            query_vec = self.embeddings[idx:idx + 1].copy()
        else:
            query_vec = np.zeros((1, self.index.d), dtype=np.float32)
            self.index.reconstruct(idx, query_vec[0])

        faiss.normalize_L2(query_vec)
        scores, indices = self.index.search(query_vec, top_k + 1)

        results = []
        for score, res_idx in zip(scores[0], indices[0]):
            if res_idx < 0 or res_idx >= len(self.movie_id_map):
                continue
            res_tmdb_id = self.movie_id_map[res_idx]
            if res_tmdb_id == tmdb_id:
                continue
            results.append({"tmdb_id": res_tmdb_id, "score": float(score)})
        return results[:top_k]

    def get_movie_embedding(self, tmdb_id: int) -> np.ndarray | None:
        """Fetch stored embedding."""
        if self.embeddings is None or not self.movie_id_map:
            return None
        try:
            idx = self.movie_id_map.index(tmdb_id)
            return self.embeddings[idx]
        except ValueError:
            return None


def upload_to_r2(local_path: str, r2_key: str) -> bool:
    """Push file to R2."""
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        s3.upload_file(local_path, R2_BUCKET_NAME, r2_key)
        logger.info(f"Uploaded {r2_key} to R2")
        return True
    except Exception as e:
        logger.error(f"R2 upload failed: {e}")
        return False
