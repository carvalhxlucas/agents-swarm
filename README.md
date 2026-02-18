Agent Swarm Orchestrator
========================

Orquestrador de swarm de agentes assíncronos, focado em concorrência, gerenciamento de estado distribuído e observabilidade.

Requisitos principais:
- Supervisor-Worker baseado em Redis Pub/Sub
- FastAPI como camada HTTP
- Estado e histórico em PostgreSQL

Instalação
----------

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Execução
--------

```bash
uvicorn app.main:app --reload
```

