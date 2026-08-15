import hashlib
import json
from typing import Any

import redis

# Initialize Redis connection
# Fallback to a memory dict if redis fails to connect (graceful degradation)
_redis_client = None
_memory_cache = {}


def get_redis_client():
    global _redis_client
    if _redis_client is None:
        try:
            # Assuming standard docker-compose redis port
            _redis_client = redis.Redis(
                host="localhost", port=6379, decode_responses=True
            )
            _redis_client.ping()
        except Exception as e:
            print(
                f"Warning: Could not connect to Redis, falling back to memory cache. Error: {e}"
            )
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
            print(f"Redis get error: {e}")
            return None

    if cached_data:
        try:
            return json.loads(cached_data)
        except:
            return None
    return None


def set_cached_response(
    query: str,
    user_id: int,
    document_id: str | None,
    response_data: dict[str, Any],
    ttl_seconds: int = 3600,
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
            print(f"Redis set error: {e}")
