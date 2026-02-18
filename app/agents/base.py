from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from app.core.event_bus import EventBus
from app.core.llm import LLMClient
from app.domain.models import SwarmMessage


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        role: str,
        event_bus: EventBus,
        llm_client: LLMClient,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self._event_bus = event_bus
        self._llm_client = llm_client

    @property
    @abstractmethod
    def input_channels(self) -> list[str]:
        raise NotImplementedError

    async def run(self) -> None:
        await asyncio.gather(*(self._listen_channel(channel) for channel in self.input_channels))

    async def _listen_channel(self, channel: str) -> None:
        async for message in self._event_bus.subscribe(channel):
            await self.handle_message(message)

    async def handle_message(self, message: SwarmMessage) -> None:
        logger.info(
            "agent_received_message",
            extra={
                "agent_id": self.agent_id,
                "role": self.role,
                "channel": message.channel,
                "message_type": message.type,
            },
        )
        thought = await self.think(message)
        await self.act(message, thought)

    @abstractmethod
    async def think(self, message: SwarmMessage) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def act(self, message: SwarmMessage, thought: Any) -> None:
        raise NotImplementedError

    async def call_llm(self, prompt: str) -> str:
        response = await self._llm_client.generate(prompt)
        return response

