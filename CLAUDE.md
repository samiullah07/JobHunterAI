# JobHunter Agent — Project Guide for Claude Code

Autonomous, **human-in-the-loop** AI job-hunting agent. It searches jobs, scores them,
tailors ATS resumes and cover letters, fills applications with browser automation, and
**stops before submission** for a <1-minute human review. It tracks applications, notifies
the user, and learns from feedback.

## Golden safety rules (never violate)
1. **Never auto-submit** an application. Automation prepares and STOPS; a human approves; only then does a separate, logged action submit.
2. **Never fabricate** resume/cover-letter content. Use only verified profile data; surface gaps to the human.
3. **Prefer official APIs / ATS feeds** over scraping gated sites. Respect robots.txt and platform ToS. Never solve CAPTCHAs or create accounts automatically.
4. **Never write real secrets.** `.env` is edited by humans only; secrets live in env/secret managers, never in code or logs.
5. **One milestone at a time.** Plan -> observe -> implement. Never rewrite unrelated code or break existing behavior.

## Workflow (every task)
First think and plan, state assumptions, ask about ambiguities, then implement the smallest correct change with tests. Use `/plan <milestone>` before `/milestone <milestone>`; finish with `/review` and `/ship`.

## Tech stack
Python 3.13, FastAPI, LangGraph + langchain-core, Pydantic v2 / pydantic-settings, SQLAlchemy 2 (async) + Alembic, asyncpg, Postgres 16 (pgvector), Redis + Celery, httpx, Playwright, Streamlit (MVP; Next.js later), structlog, tenacity. Package manager: **uv**. LLM: **Anthropic primary, OpenAI fallback**. Storage: local now, S3-compatible interface later. PDF via Playwright `page.pdf()`.

## Architecture (Clean Architecture, dependencies point inward)
See skill `job-agent-architecture`. Layout under `src/jobhunter/`: domain, application, agents, adapters/{llm,browser,boards,notifications}, infrastructure/{db,repositories}, api, workers, common. Frontend in `frontend/`, tests mirror `src/` paths.

## Standards
SOLID / DRY / KISS. Full type hints; **mypy strict** and **ruff** must pass. Async for all I/O. Repository/provider interfaces as `Protocol`, wired via dependency injection. Every module gets a test.

## Project skills — use them
- `job-agent-architecture` — before creating/moving modules or adding cross-layer deps.
- `ats-resume-writing` — resume/cover-letter/ATS agents.
- `browser-automation-hitl` — any Playwright/browser-use code.
- `langgraph-agent-patterns` — any graph/node under agents/.

## Installed Claude Code skills — when to use
- `full-output-enforcement` — always, so code is never truncated.
- `claude-api` — when writing LLM adapter code (correct model names/params/pricing).
- `security-review` — during `/review` and before marking a milestone done.
- `simplify` — during `/review` and refactors.
- `dataviz` + `design-taste-frontend` + `minimalist-ui` — the frontend milestone.
- `run` — to launch the app; `loop` — for scheduled job-search runs (later).
- `update-config` / `fewer-permission-prompts` — adjusting `.claude/settings.json`.

## MCP servers
`ide` (VS Code diagnostics/exec) connected. `github`, `filesystem`, `playwright` pending — enable when needed.

## Slash commands
`/plan` (plan a milestone, no code) · `/milestone` (implement one milestone, then stop) · `/review` (lint+type+test+security+simplify) · `/frontend` (dashboard UI) · `/ship` (pre-commit gate, no push).

## Run (reference — do not auto-run)
- Install: `uv sync --extra dev` then `uv run playwright install chromium`
- Services: `docker compose up -d` (needs Docker Desktop running)
- Migrate: `uv run alembic upgrade head`
- API: `uv run uvicorn jobhunter.main:app --reload`
- UI: `uv run streamlit run frontend/app.py`
- Tests: `uv run pytest -q`

## Milestone roadmap
M1 scaffold+governance (this) · M2 data layer (schema, models, migrations, repos) · M3 user profile + master-resume ingest · M4 job search/connectors + dedup · M5 matching/scoring · M6 resume generation · M7 cover letter + ATS optimization · M8 browser automation (HITL) · M9 review UI + approval · M10 tracking + notifications · M11 learning + memory (vector) · M12 dashboard + observability + full tests.

## Definition of done (per milestone)
ruff clean · mypy strict passes · tests added and green · safety rules honored · no unrelated changes · CLAUDE.md updated if architecture changed.