import json
import redis.asyncio as aioredis
from app.config import settings

CACHE_TTL = 3600

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None


def _link_key(short_code: str) -> str:
    return f"link:{short_code}"


async def cache_get_url(short_code: str) -> str | None:
    client = await get_redis()
    return await client.get(_link_key(short_code))


async def cache_set_url(short_code: str, original_url: str):
    client = await get_redis()
    await client.set(_link_key(short_code), original_url, ex=CACHE_TTL)


async def cache_invalidate(short_code: str):
    client = await get_redis()
    await client.delete(_link_key(short_code))


async def cache_get_stats(short_code: str) -> dict | None:
    client = await get_redis()
    data = await client.get(f"stats:{short_code}")
    if data:
        return json.loads(data)
    return None


async def cache_set_stats(short_code: str, stats: dict):
    client = await get_redis()
    await client.set(f"stats:{short_code}", json.dumps(stats, default=str), ex=300)


async def cache_invalidate_stats(short_code: str):
    client = await get_redis()
    await client.delete(f"stats:{short_code}")