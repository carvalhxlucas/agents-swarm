from __future__ import annotations

import logging
from typing import Protocol

from openai import AsyncOpenAI


logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAILLMClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        message = response.choices[0].message.content or ""
        return message

