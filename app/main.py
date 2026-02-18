from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel

from app.agents.researcher import ResearcherAgent
from app.agents.supervisor import SUPERVISOR_CONTROL_CHANNEL, SharedBlackboard, SupervisorAgent
from app.core.event_bus import EventBus, RedisEventBus
from app.core.llm import OpenAILLMClient
from app.core.search import TavilySearchClient
from app.domain.models import SwarmMessage, SwarmMessageType, Task


logger = logging.getLogger("agents-swarm")
logging.basicConfig(level=logging.INFO)


class InMemoryBlackboard(SharedBlackboard):
    def __init__(self) -> None:
        self._tasks: dict[uuid.UUID, Task] = {}

    async def create_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def update_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        return self._tasks.get(task_id)


class MissionRequest(BaseModel):
    goal: str


class MissionResponse(BaseModel):
    mission_id: uuid.UUID


class AppState(BaseModel):
    event_bus: EventBus
    supervisor: SupervisorAgent
    researcher: ResearcherAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")

    event_bus = RedisEventBus(redis_url=redis_url)
    llm_client = OpenAILLMClient(api_key=openai_api_key, model=openai_model)
    search_client = TavilySearchClient(api_key=tavily_api_key) if tavily_api_key else None

    blackboard: SharedBlackboard = InMemoryBlackboard()
    supervisor = SupervisorAgent(
        agent_id="supervisor-1",
        event_bus=event_bus,
        llm_client=llm_client,
        blackboard=blackboard,
    )

    if search_client is None:
        logger.warning("TAVILY_API_KEY não configurada. ResearcherAgent não será iniciado.")
        researcher = None
    else:
        researcher = ResearcherAgent(
            agent_id="researcher-1",
            event_bus=event_bus,
            llm_client=llm_client,
            search_client=search_client,
        )

    app.state.app_state = AppState(
        event_bus=event_bus,
        supervisor=supervisor,
        researcher=researcher if researcher is not None else None,
    )

    async def start_agents() -> None:
        tasks = [asyncio.create_task(supervisor.run())]
        if researcher is not None:
            tasks.append(asyncio.create_task(researcher.run()))
        await asyncio.gather(*tasks)

    agents_task = asyncio.create_task(start_agents())
    try:
        yield
    finally:
        agents_task.cancel()
        try:
            await agents_task
        except asyncio.CancelledError:
            pass
        await event_bus.close()


app = FastAPI(lifespan=lifespan)


@app.post("/missions", response_model=MissionResponse)
async def create_mission(request: MissionRequest) -> MissionResponse:
    mission_id = uuid.uuid4()
    app_state: AppState = app.state.app_state
    message = SwarmMessage(
        mission_id=mission_id,
        task_id=None,
        source_agent=None,
        target_agent="supervisor",
        channel=SUPERVISOR_CONTROL_CHANNEL,
        type=SwarmMessageType.MISSION_CREATED,
        payload={"goal": request.goal},
    )
    await app_state.event_bus.publish(channel=SUPERVISOR_CONTROL_CHANNEL, message=message)
    logger.info(
        "mission_created",
        extra={
            "mission_id": str(mission_id),
            "goal": request.goal,
        },
    )
    response = MissionResponse(mission_id=mission_id)
    return response

