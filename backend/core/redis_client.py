from redis.asyncio import Redis, from_url

from .config import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = await from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


REFRESH_TOKEN_PREFIX = "refresh:"
DASHBOARD_CACHE_PREFIX = "dashboard:"
CACHE_TTL_DASHBOARD = 15 * 60  # 15 minutes


async def store_refresh_token(user_id: str, token: str) -> None:
    redis = await get_redis()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    await redis.setex(f"{REFRESH_TOKEN_PREFIX}{user_id}", ttl, token)


async def get_refresh_token(user_id: str) -> str | None:
    redis = await get_redis()
    return await redis.get(f"{REFRESH_TOKEN_PREFIX}{user_id}")


async def delete_refresh_token(user_id: str) -> None:
    redis = await get_redis()
    await redis.delete(f"{REFRESH_TOKEN_PREFIX}{user_id}")


async def cache_set(key: str, value: str, ttl: int) -> None:
    redis = await get_redis()
    await redis.setex(key, ttl, value)


async def cache_get(key: str) -> str | None:
    redis = await get_redis()
    return await redis.get(key)


async def cache_delete(key: str) -> None:
    redis = await get_redis()
    await redis.delete(key)
