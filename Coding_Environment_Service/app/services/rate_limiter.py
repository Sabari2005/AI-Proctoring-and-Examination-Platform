import redis.asyncio as aioredis
from fastapi import HTTPException, status
from app.config import settings

_redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def check_rate_limit(key: str, limit: int, window_seconds: int):
    """Sliding window rate limiter using Redis INCR + EXPIRE."""
    redis_key = f"rate:{key}"
    current = await _redis.incr(redis_key)
    if current == 1:
        await _redis.expire(redis_key, window_seconds)
    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {limit} requests per {window_seconds}s.",
            headers={"Retry-After": str(window_seconds)},
        )
