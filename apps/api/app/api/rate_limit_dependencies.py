from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.api.dependencies import get_current_user
from app.cache.redis_client import build_redis_cache
from app.core.rate_limit import RateLimiter
from app.domain.entities import User


def rate_limit_by_user(bucket: str, limit: int, window_seconds: int):
    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        cache = build_redis_cache()
        if cache is None:
            return
        limiter = RateLimiter(cache)
        key = f"ratelimit:{bucket}:{current_user.id}"
        if not limiter.check(key, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a moment.",
            )
    return dependency


def rate_limit_by_ip(bucket: str, limit: int, window_seconds: int):
    def dependency(request: Request) -> None:
        cache = build_redis_cache()
        if cache is None:
            return
        limiter = RateLimiter(cache)
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{bucket}:{client_ip}"
        if not limiter.check(key, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a moment.",
            )
    return dependency
