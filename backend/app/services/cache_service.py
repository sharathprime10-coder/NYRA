import hashlib
import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis client with graceful memory-cache fallback
# ---------------------------------------------------------------------------

_redis_client = None
_memory_cache: dict[str, str] = {}
_warned = False  # one-shot warning flag


def get_redis_client():
    global _redis_client, _warned
    if _redis_client is None:
        redis_url = getattr(settings, "REDIS_URL", None) or "redis://127.0.0.1:6379/0"
        try:
            _redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,  # don't block startup
                socket_timeout=2,
            )
            _redis_client.ping()
            logger.info("redis_connected", extra={"url": redis_url})
        except Exception:
            if not _warned:
                logger.warning(
                    "redis_unavailable_using_memory_cache",
                    extra={"url": redis_url},
                )
                _warned = True
            _redis_client = "memory"
    return _redis_client


def _generate_cache_key(query: str, user_id: int, document_id: str | None) -> str:
    """Generate a semantic hash key for the query, scoped to the user and optional document."""
    normalized_query = query.strip().lower()

    # Create a stable string representation
    key_content = f"user:{user_id}|doc:{document_id or 'none'}|query:{normalized_query}"

    # Hash it to ensure we have a safe, bounded length key
    key_hash = hashlib.sha256(key_content.encode("utf-8")).hexdigest()
    return f"nyra:cache:response:{key_hash}"


def get_cached_response(
    query: str, user_id: int, document_id: str | None
) -> dict[str, Any] | None:
    """Retrieve a cached response if it exists."""
    key = _generate_cache_key(query, user_id, document_id)
    client = get_redis_client()

    if client == "memory":
        cached_data = _memory_cache.get(key)
    else:
        try:
            cached_data = client.get(key)
        except Exception as e:
            logger.debug(f"Redis get error: {e}")
            return None

    if cached_data:
        try:
            logger.info("cache_hit", extra={"key_prefix": key[:40]})
            return json.loads(cached_data)
        except Exception:
            return None

    logger.debug("cache_miss", extra={"key_prefix": key[:40]})
    return None


def set_cached_response(
    query: str,
    user_id: int,
    document_id: str | None,
    response_data: dict[str, Any],
    ttl_seconds: int = 900,  # 15 minutes (was 1 hour — shorter is safer)
):
    """Cache the response with a time-to-live."""
    key = _generate_cache_key(query, user_id, document_id)
    client = get_redis_client()

    serialized_data = json.dumps(response_data)

    if client == "memory":
        _memory_cache[key] = serialized_data
    else:
        try:
            client.setex(name=key, time=ttl_seconds, value=serialized_data)
        except Exception as e:
            logger.debug(f"Redis set error: {e}")
