import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import settings

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - optional dependency at runtime
    Redis = None  # type: ignore[assignment]


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> dict | None:
        item = self._data.get(key)
        if not item:
            return None
        expires_at, value = item
        if time.time() > expires_at:
            self._data.pop(key, None)
            return None
        return json.loads(value)

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self._data[key] = (time.time() + ttl_seconds, json.dumps(value))


class RedisCache:
    def __init__(self, redis_client: "Redis") -> None:
        self.redis_client = redis_client

    async def get(self, key: str) -> dict | None:
        raw = await self.redis_client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        await self.redis_client.set(key, json.dumps(value), ex=ttl_seconds)


@asynccontextmanager
async def build_cache() -> AsyncIterator[MemoryCache | RedisCache]:
    if settings.redis_url and Redis is not None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            yield RedisCache(redis_client)
        finally:
            await redis_client.close()
    else:
        yield MemoryCache()
