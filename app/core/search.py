from __future__ import annotations

import asyncio
import logging
from typing import Protocol

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float | None = None


class SearchClient(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        raise NotImplementedError


class TavilySearchClient:
    def __init__(self, api_key: str) -> None:
        try:
            from tavily import TavilyClient
        except ImportError:
            raise ImportError(
                "tavily-python não está instalado. Instale com: pip install tavily-python"
            )
        self._client = TavilyClient(api_key=api_key)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.search(
                    query=query,
                    max_results=max_results,
                    search_depth="advanced",
                ),
            )
            results = []
            for result in response.get("results", []):
                search_result = SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    score=result.get("score"),
                )
                results.append(search_result)
            logger.info(
                "search_completed",
                extra={
                    "query": query,
                    "results_count": len(results),
                },
            )
            return results
        except Exception as e:
            logger.error(
                "search_failed",
                extra={
                    "query": query,
                    "error": str(e),
                },
            )
            raise
