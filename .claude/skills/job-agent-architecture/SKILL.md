---
name: job-agent-architecture
description: Enforce Clean Architecture layering and the dependency rule for the JobHunter codebase. Consult before creating or moving any module, choosing where a class lives, or adding a dependency between layers.
---

# JobHunter Architecture Rules

Layered, dependencies point INWARD only. Outer may import inner; inner must never import outer.

- domain/        Pure entities and value objects. No I/O, no framework, no LLM. Stdlib + pydantic only.
- application/   Use cases / service orchestration. Depends on domain + repository interfaces (Protocols).
- agents/        LangGraph graphs and nodes. Orchestrate use cases; never touch the DB directly.
- adapters/      Concrete integrations: llm, browser, boards, notifications. Implement interfaces defined inward.
- infrastructure/ DB engine, SQLAlchemy models, Alembic, concrete repositories.
- api/           FastAPI routers. Thin — translate HTTP to use cases.
- workers/       Celery tasks. Thin — schedule and invoke use cases.
- common/        Logging, errors, shared utils.

Rules:
- Define repository and provider INTERFACES as typing.Protocol in application or domain; implement them in adapters/infrastructure. Wire with dependency injection (constructor args), never global singletons.
- Async everywhere for I/O (async def, asyncpg, httpx.AsyncClient). No blocking calls in async paths.
- Full type hints; mypy strict must pass. Follow SOLID / DRY / KISS.
- Every new module gets a matching test under tests/ mirroring the path.
- Never import a framework (fastapi, sqlalchemy, langgraph) inside domain/.