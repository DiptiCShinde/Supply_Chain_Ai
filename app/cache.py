import json
import logging
import time

import redis

from app.config import settings

logger = logging.getLogger(__name__)

_memory: dict = {}
_redis = None

if settings.redis_url:
    try:
        _redis = redis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=2
        )
    except redis.RedisError as exc:
        logger.debug("Redis initialization failed, using memory cache: %s", exc)
        _redis = None


def cache_get(key: str):
    try:
        if _redis:
            value = _redis.get(key)
            if value:
                return json.loads(value)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.debug("Redis cache_get failed for key %s: %s", key, exc)
    item = _memory.get(key)
    if item and item[0] > time.time():
        return item[1]
    return None


def cache_set(key: str, value, ttl: int = 300) -> None:
    try:
        if _redis:
            _redis.setex(key, ttl, json.dumps(value))
            return
    except redis.RedisError as exc:
        logger.debug("Redis cache_set failed for key %s: %s", key, exc)
    _memory[key] = (time.time() + ttl, value)
