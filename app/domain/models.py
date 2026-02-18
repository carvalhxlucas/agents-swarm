from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class AgentLifecycleStatus(StrEnum):
    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class SwarmMessageType(StrEnum):
    MISSION_CREATED = "MISSION_CREATED"
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_RESULT = "TASK_RESULT"
    HEARTBEAT = "HEARTBEAT"
    CONTROL = "CONTROL"


class Task(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    mission_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    kind: str
    payload: dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentState(BaseModel):
    agent_id: str
    role: str
    status: AgentLifecycleStatus = AgentLifecycleStatus.IDLE
    current_task_id: uuid.UUID | None = None
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SwarmMessage(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    mission_id: uuid.UUID
    task_id: uuid.UUID | None = None
    source_agent: str | None = None
    target_agent: str | None = None
    channel: str
    type: SwarmMessageType
    payload: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: uuid.UUID | None = None

