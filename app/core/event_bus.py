from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.domain.models import SwarmMessage


logger = logging.getLogger(__name__)


class EventBus(ABC):
    @abstractmethod
    async def publish(self, channel: str, message: SwarmMessage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def subscribe(self, channel: str) -> AsyncIterator[SwarmMessage]:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError


class RedisEventBus(EventBus):
    def __init__(self, redis_url: str) -> None:
        self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def publish(self, channel: str, message: SwarmMessage) -> None:
        payload = message.model_dump_json()
        await self._redis.publish(channel, payload)

    async def subscribe(self, channel: str) -> AsyncIterator[SwarmMessage]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                raw_type = raw.get("type")
                if raw_type != "message":
                    continue
                data = raw.get("data")
                if not isinstance(data, str):
                    continue
                message = SwarmMessage.model_validate_json(data)
                yield message
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def close(self) -> None:
        await self._redis.close()

