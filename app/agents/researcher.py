from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.core.event_bus import EventBus
from app.core.llm import LLMClient
from app.core.search import SearchClient, SearchResult
from app.domain.models import SwarmMessage, SwarmMessageType, Task, TaskStatus
from app.agents.supervisor import TASK_RESULTS_CHANNEL, RESEARCHER_TASKS_CHANNEL

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        llm_client: LLMClient,
        search_client: SearchClient,
    ) -> None:
        super().__init__(agent_id=agent_id, role="researcher", event_bus=event_bus, llm_client=llm_client)
        self._search_client = search_client

    @property
    def input_channels(self) -> list[str]:
        return [RESEARCHER_TASKS_CHANNEL]

    async def think(self, message: SwarmMessage) -> Task | None:
        if message.type != SwarmMessageType.TASK_CREATED:
            return None
        task_data = message.payload.get("task")
        if task_data is None:
            logger.warning(
                "invalid_task_message",
                extra={
                    "agent_id": self.agent_id,
                    "message_id": str(message.id),
                },
            )
            return None
        task = Task.model_validate(task_data)
        if task.kind != "research":
            logger.warning(
                "unexpected_task_kind",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": str(task.id),
                    "task_kind": task.kind,
                },
            )
            return None
        return task

    async def act(self, message: SwarmMessage, thought: Any) -> None:
        if not isinstance(thought, Task):
            return
        task = thought
        task.status = TaskStatus.RUNNING
        logger.info(
            "task_started",
            extra={
                "agent_id": self.agent_id,
                "task_id": str(task.id),
                "mission_id": str(task.mission_id),
            },
        )
        try:
            goal = task.payload.get("goal", "")
            search_query = await self._generate_search_query(goal)
            search_results = await self._search_client.search(query=search_query, max_results=5)
            research_summary = await self._synthesize_research(goal, search_results)
            result_payload = {
                "search_query": search_query,
                "sources": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "content": r.content[:500],
                    }
                    for r in search_results
                ],
                "summary": research_summary,
            }
            task.status = TaskStatus.COMPLETED
            task.result = result_payload
            logger.info(
                "task_completed",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": str(task.id),
                    "mission_id": str(task.mission_id),
                    "sources_count": len(search_results),
                },
            )
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(
                "task_failed",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": str(task.id),
                    "mission_id": str(task.mission_id),
                    "error": str(e),
                },
            )
        result_message = SwarmMessage(
            mission_id=task.mission_id,
            task_id=task.id,
            source_agent=self.agent_id,
            target_agent="supervisor",
            channel=TASK_RESULTS_CHANNEL,
            type=SwarmMessageType.TASK_RESULT,
            payload=task.result if task.result else {"error": task.error},
            correlation_id=message.id,
        )
        await self._event_bus.publish(channel=TASK_RESULTS_CHANNEL, message=result_message)

    async def _generate_search_query(self, goal: str) -> str:
        prompt = f"""Com base no objetivo abaixo, gere uma query de busca concisa e específica para encontrar informações relevantes.

Objetivo: {goal}

Retorne apenas a query de busca, sem explicações adicionais."""
        query = await self.call_llm(prompt)
        return query.strip().strip('"').strip("'")

    async def _synthesize_research(self, goal: str, search_results: list[SearchResult]) -> str:
        sources_text = "\n\n".join(
            [
                f"Fonte {i+1}: {r.title}\nURL: {r.url}\nConteúdo: {r.content[:800]}"
                for i, r in enumerate(search_results)
            ]
        )
        prompt = f"""Com base no objetivo e nas fontes encontradas, sintetize um resumo de pesquisa focado e útil.

Objetivo: {goal}

Fontes encontradas:
{sources_text}

Gere um resumo estruturado que responda ao objetivo, citando as fontes quando relevante."""
        summary = await self.call_llm(prompt)
        return summary
