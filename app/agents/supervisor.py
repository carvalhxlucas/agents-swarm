from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.base import BaseAgent
from app.core.event_bus import EventBus
from app.core.llm import LLMClient
from app.domain.models import SwarmMessage, SwarmMessageType, Task, TaskStatus


logger = logging.getLogger(__name__)


SUPERVISOR_CONTROL_CHANNEL = "swarm:supervisor:control"
TASK_RESULTS_CHANNEL = "swarm:tasks:results"
RESEARCHER_TASKS_CHANNEL = "swarm:workers:researcher:tasks"
CODER_TASKS_CHANNEL = "swarm:workers:coder:tasks"


class SharedBlackboard(Protocol):
    async def create_task(self, task: Task) -> None:
        raise NotImplementedError

    async def update_task(self, task: Task) -> None:
        raise NotImplementedError

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        raise NotImplementedError


@dataclass(slots=True)
class SupervisorDecision:
    new_tasks: list[Task]
    completed_task: Task | None = None


class SupervisorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        event_bus: EventBus,
        llm_client: LLMClient,
        blackboard: SharedBlackboard,
    ) -> None:
        super().__init__(agent_id=agent_id, role="supervisor", event_bus=event_bus, llm_client=llm_client)
        self._blackboard = blackboard

    @property
    def input_channels(self) -> list[str]:
        return [SUPERVISOR_CONTROL_CHANNEL, TASK_RESULTS_CHANNEL]

    async def think(self, message: SwarmMessage) -> SupervisorDecision:
        if message.type == SwarmMessageType.MISSION_CREATED:
            goal = message.payload.get("goal", "")
            mission_id = message.mission_id
            root_task = Task(
                mission_id=mission_id,
                parent_id=None,
                kind="mission_root",
                payload={"goal": goal},
                status=TaskStatus.PENDING,
            )
            await self._blackboard.create_task(root_task)
            researcher_task = Task(
                mission_id=mission_id,
                parent_id=root_task.id,
                kind="research",
                payload={"goal": goal},
                status=TaskStatus.PENDING,
                assigned_agent="researcher",
            )
            coder_task = Task(
                mission_id=mission_id,
                parent_id=root_task.id,
                kind="implementation_plan",
                payload={"goal": goal},
                status=TaskStatus.PENDING,
                assigned_agent="coder",
            )
            await self._blackboard.create_task(researcher_task)
            await self._blackboard.create_task(coder_task)
            decision = SupervisorDecision(new_tasks=[researcher_task, coder_task])
            return decision
        if message.type == SwarmMessageType.TASK_RESULT and message.task_id is not None:
            task = await self._blackboard.get_task(message.task_id)
            if task is None:
                decision = SupervisorDecision(new_tasks=[])
                return decision
            task.status = TaskStatus.COMPLETED
            task.result = message.payload
            await self._blackboard.update_task(task)
            decision = SupervisorDecision(new_tasks=[], completed_task=task)
            return decision
        decision = SupervisorDecision(new_tasks=[])
        return decision

    async def act(self, message: SwarmMessage, thought: Any) -> None:
        if not isinstance(thought, SupervisorDecision):
            return
        for task in thought.new_tasks:
            if task.assigned_agent == "researcher":
                channel = RESEARCHER_TASKS_CHANNEL
            elif task.assigned_agent == "coder":
                channel = CODER_TASKS_CHANNEL
            else:
                channel = SUPERVISOR_CONTROL_CHANNEL
            swarm_message = SwarmMessage(
                mission_id=task.mission_id,
                task_id=task.id,
                source_agent=self.agent_id,
                target_agent=task.assigned_agent,
                channel=channel,
                type=SwarmMessageType.TASK_CREATED,
                payload={"task": task.model_dump()},
            )
            await self._event_bus.publish(channel=channel, message=swarm_message)
        if thought.completed_task is not None:
            logger.info(
                "task_completed",
                extra={
                    "agent_id": self.agent_id,
                    "task_id": str(thought.completed_task.id),
                    "mission_id": str(thought.completed_task.mission_id),
                },
            )

