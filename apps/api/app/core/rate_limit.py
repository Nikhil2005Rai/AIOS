import logging
from app.cache.redis_client import RedisCache

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, cache: RedisCache) -> None:
        self.cache = cache

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """Returns True if the request is allowed, False if the limit is exceeded.
        Fails open (returns True) if Redis is unavailable."""
        count = self.cache.incr(key)
        if count is None:
            return True
        if count == 1:
            self.cache.expire(key, window_seconds)
        return count <= limit
