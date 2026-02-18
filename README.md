# Agent Swarm Orchestrator

A distributed, asynchronous multi-agent orchestration system built from the ground up. This project demonstrates advanced capabilities in concurrent programming, distributed state management, and system observability without relying on high-level frameworks like CrewAI or LangGraph.

## 🎯 Overview

The Agent Swarm Orchestrator is a production-ready system that implements a **Supervisor-Worker pattern** for coordinating multiple AI agents. It uses Redis Pub/Sub for asynchronous message passing, PostgreSQL for state persistence, and FastAPI for the HTTP interface.

### Key Features

- **🔄 Asynchronous Architecture**: Built with Python 3.11+ `asyncio` for high concurrency
- **📡 Event-Driven Communication**: Redis Pub/Sub for decoupled agent communication
- **💾 Distributed State Management**: Shared Blackboard pattern with persistent state
- **🛡️ Fault Tolerance**: Timeout handling, error recovery, and task retry mechanisms
- **🔍 Observability Ready**: Structured logging prepared for OpenTelemetry integration
- **🧩 Pluggable LLM Interface**: Abstract interface supporting multiple LLM providers
- **🚀 Production Ready**: Type hints, error handling, and clean architecture

## 🏗️ Architecture

### System Components

```
┌─────────────┐
│   FastAPI   │  HTTP API for mission creation
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│         Redis Pub/Sub Event Bus                 │
│  (swarm:supervisor:control, swarm:workers:*)    │
└──────┬──────────────────────┬───────────────────┘
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────────┐
│  Supervisor  │      │  Worker Agents   │
│    Agent     │◄─────│  (Researcher,    │
│              │      │   Coder, etc.)   │
└──────┬───────┘      └──────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│    Shared Blackboard            │
│  (PostgreSQL / Redis State)     │
└─────────────────────────────────┘
```

### Design Patterns

- **Supervisor-Worker**: Supervisor decomposes goals into subtasks and delegates to specialized workers
- **Shared Blackboard**: Centralized, serializable state accessible by all agents
- **Event-Driven**: Agents communicate via message passing through Redis channels
- **Strategy Pattern**: Pluggable LLM and search clients via Protocol interfaces

## 📋 Requirements

- **Python**: 3.11 or higher
- **Redis**: 5.0+ (for Pub/Sub messaging)
- **PostgreSQL**: 12+ (optional, for persistent state - currently uses in-memory implementation)
- **OpenAI API Key**: For LLM operations
- **Tavily API Key**: For web search functionality (optional, if using ResearcherAgent)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd agents-swarm
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -e .
```

### 4. Install development dependencies (optional)

```bash
pip install -e ".[dev]"
```

## ⚙️ Configuration

Set the following environment variables:

```bash
# Required
export REDIS_URL="redis://localhost:6379/0"
export OPENAI_API_KEY="your-openai-api-key"
export OPENAI_MODEL="gpt-4o-mini"  # or gpt-4, gpt-3.5-turbo, etc.

# Optional (for ResearcherAgent)
export TAVILY_API_KEY="your-tavily-api-key"
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection string |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for LLM operations |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `TAVILY_API_KEY` | No | - | Tavily API key for web search (required for ResearcherAgent) |

## 🎮 Usage

### Start the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Create a Mission

Send a POST request to create a new mission:

```bash
curl -X POST http://localhost:8000/missions \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Research the latest trends in artificial intelligence and create a summary"
  }'
```

**Response:**

```json
{
  "mission_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### How It Works

1. **Mission Creation**: The API receives a goal and publishes a `MISSION_CREATED` event
2. **Supervisor Processing**: The SupervisorAgent receives the event and:
   - Creates a root task
   - Decomposes the goal into subtasks (e.g., research, implementation)
   - Publishes `TASK_CREATED` events to worker channels
3. **Worker Execution**: Worker agents (e.g., ResearcherAgent) receive tasks:
   - Process the task (e.g., perform web search)
   - Generate results using LLM synthesis
   - Publish `TASK_RESULT` events back to the supervisor
4. **Result Aggregation**: The supervisor collects results and updates the blackboard

## 📁 Project Structure

```
agents-swarm/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and entry point
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   └── models.py           # Pydantic models (Task, AgentState, SwarmMessage)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── event_bus.py        # Redis Pub/Sub abstraction
│   │   ├── llm.py              # LLM client interface and OpenAI implementation
│   │   └── search.py           # Search client interface and Tavily implementation
│   │
│   └── agents/
│       ├── __init__.py
│       ├── base.py             # BaseAgent abstract class
│       ├── supervisor.py       # SupervisorAgent implementation
│       └── researcher.py       # ResearcherAgent implementation
│
├── pyproject.toml              # Project configuration and dependencies
└── README.md                   # This file
```

## 🔧 Core Components

### Domain Models (`app/domain/models.py`)

- **`Task`**: Represents a work unit with status, payload, and results
- **`AgentState`**: Tracks agent lifecycle and current task assignment
- **`SwarmMessage`**: Message format for inter-agent communication
- **Enums**: `TaskStatus`, `AgentLifecycleStatus`, `SwarmMessageType`

### Event Bus (`app/core/event_bus.py`)

Abstract interface for pub/sub messaging:

```python
class EventBus(Protocol):
    async def publish(self, channel: str, message: SwarmMessage) -> None
    async def subscribe(self, channel: str) -> AsyncIterator[SwarmMessage]
```

**Implementation**: `RedisEventBus` uses Redis Pub/Sub for distributed messaging.

### LLM Client (`app/core/llm.py`)

Pluggable LLM interface:

```python
class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str
```

**Implementation**: `OpenAILLMClient` uses OpenAI's async API.

### Search Client (`app/core/search.py`)

Pluggable search interface:

```python
class SearchClient(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]
```

**Implementation**: `TavilySearchClient` uses Tavily API for web search.

### Base Agent (`app/agents/base.py`)

Abstract base class for all agents:

- **`listen()`**: Subscribes to input channels
- **`think()`**: Processes messages (abstract method)
- **`act()`**: Executes actions based on thoughts (abstract method)
- **`call_llm()`**: Helper method for LLM calls

### Supervisor Agent (`app/agents/supervisor.py`)

Orchestrates the swarm:

- **Decomposition**: Breaks goals into subtasks
- **Delegation**: Assigns tasks to appropriate workers
- **Aggregation**: Collects and processes results

### Researcher Agent (`app/agents/researcher.py`)

Example worker implementation:

- Receives research tasks
- Generates optimized search queries using LLM
- Performs web searches via Tavily
- Synthesizes results into structured summaries

## 🔌 API Reference

### POST `/missions`

Create a new mission.

**Request Body:**
```json
{
  "goal": "string"
}
```

**Response:**
```json
{
  "mission_id": "uuid"
}
```

## 🧪 Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linter
ruff check app/

# Run type checker
mypy app/
```

### Adding a New Worker Agent

1. Create a new file in `app/agents/` (e.g., `app/agents/coder.py`)
2. Inherit from `BaseAgent`
3. Implement `input_channels`, `think()`, and `act()` methods
4. Register the agent in `app/main.py` lifespan function

**Example:**

```python
from app.agents.base import BaseAgent
from app.core.event_bus import EventBus
from app.core.llm import LLMClient

class CoderAgent(BaseAgent):
    @property
    def input_channels(self) -> list[str]:
        return ["swarm:workers:coder:tasks"]
    
    async def think(self, message: SwarmMessage) -> Any:
        # Process message logic
        pass
    
    async def act(self, message: SwarmMessage, thought: Any) -> None:
        # Execute action logic
        pass
```

## 🏛️ Architecture Decisions

### Why Not Use High-Level Frameworks?

This project intentionally avoids frameworks like CrewAI or LangGraph to demonstrate:
- Deep understanding of async/await patterns
- Custom state management implementation
- Direct control over message passing and concurrency
- Portfolio showcase of distributed systems expertise

### Why Redis Pub/Sub?

- **Decoupling**: Agents don't need direct references to each other
- **Scalability**: Multiple instances can subscribe to the same channels
- **Persistence**: Redis can optionally persist messages
- **Observability**: Easy to monitor message flow

### Why Shared Blackboard?

- **Distributed State**: State is serializable and can be shared across containers
- **Fault Tolerance**: State persists even if agents restart
- **Observability**: Centralized state is easier to monitor and debug

## 📊 Observability

The system uses structured logging throughout:

```python
logger.info(
    "task_completed",
    extra={
        "agent_id": self.agent_id,
        "task_id": str(task.id),
        "mission_id": str(task.mission_id),
    },
)
```

This format is ready for OpenTelemetry integration and log aggregation systems.

## 🚧 Roadmap

- [ ] PostgreSQL implementation for SharedBlackboard
- [ ] Additional worker agents (CoderAgent, WriterAgent, etc.)
- [ ] Task timeout and retry mechanisms
- [ ] Heartbeat monitoring for agent health
- [ ] OpenTelemetry instrumentation
- [ ] WebSocket support for real-time mission status
- [ ] Docker Compose setup for local development

## 📝 License

[Specify your license here]

## 👥 Contributing

[Add contribution guidelines if applicable]

## 🙏 Acknowledgments

Built to demonstrate advanced distributed systems and concurrent programming capabilities.