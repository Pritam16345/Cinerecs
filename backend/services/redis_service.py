"""
CineRecs — Redis caching service (Upstash-compatible).
Provides async get/set/invalidate operations with JSON serialization.
"""

import os
import json
import logging
import redis.asyncio as redis

logger = logging.getLogger("cinerecs.redis")

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL", "")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN", "")
DEFAULT_TTL = 3600  # 1 hour

_client: redis.Redis | None = None

async def get_redis() -> redis.Redis:
    """Return the singleton async Redis client."""
    global _client
    if _client is None:
        if UPSTASH_REDIS_URL:
            _client = redis.from_url(
                UPSTASH_REDIS_URL,
                password=UPSTASH_REDIS_TOKEN if UPSTASH_REDIS_TOKEN else None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        else:
            logger.warning("UPSTASH_REDIS_URL not set, Redis disabled")
            return None
    return _client


async def close_redis() -> None:
    """Close the Redis connection."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("Redis connection closed")


async def ping() -> bool:
    """Check if Redis is reachable."""
    try:
        client = await get_redis()
        if client is None:
            return False
        return await client.ping()
    except Exception:
        return False


async def get_cached(key: str):
    """
    Retrieve a cached value by key.
    Returns parsed JSON or None if not found / Redis unavailable.
    """
    try:
        client = await get_redis()
        if client is None:
            return None
        value = await client.get(key)
        if value is not None:
            return json.loads(value)
    except Exception as e:
        logger.debug(f"Cache get failed for {key}: {e}")
    return None


async def set_cached(key: str, value, ttl: int = DEFAULT_TTL) -> bool:
    """
    Store a value in cache with TTL.
    Returns True if successful, False otherwise.
    """
    try:
        client = await get_redis()
        if client is None:
            return False
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.debug(f"Cache set failed for {key}: {e}")
        return False


async def invalidate(key: str) -> bool:
    """Delete a cached key."""
    try:
        client = await get_redis()
        if client is None:
            return False
        await client.delete(key)
        return True
    except Exception as e:
        logger.debug(f"Cache invalidate failed for {key}: {e}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    try:
        client = await get_redis()
        if client is None:
            return 0
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache pattern invalidate failed for {pattern}: {e}")
        return 0
