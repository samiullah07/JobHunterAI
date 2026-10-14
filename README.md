# JobHunter Agent

Autonomous, human-in-the-loop AI job-hunting agent. It searches for jobs, scores them, tailors ATS-optimized resumes and cover letters, fills out applications via browser automation, and **stops before submission** for a sub-1-minute human review. It tracks applications, sends notifications, and learns from feedback over time.

---

## ⚠️ Golden Safety Rules (never violate)

- **Never auto-submit an application.** Automation prepares and stops; a human approves; only then does a separate, logged action submit.
- **Never fabricate resume/cover-letter content.** Use only verified profile data; surface gaps to the human instead of inventing details.
- **Prefer official APIs / ATS feeds over scraping gated sites.** Respect `robots.txt` and platform ToS. Never solve CAPTCHAs or create accounts automatically.
- **Never write real secrets.** `.env` is edited by humans only; secrets live in env/secret managers, never in code or logs.
- **One milestone at a time.** Plan → observe → implement. Never rewrite unrelated code or break existing behavior.

---

## Workflow

For every task: **think and plan, state assumptions, ask about ambiguities, then implement the smallest correct change with tests.**

```
/plan <milestone>       # plan a milestone, no code
/milestone <milestone>  # implement one milestone, then stop
/review                 # lint + type + test + security + simplify
/ship                   # pre-commit gate, no push
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| API | FastAPI |
| Agents | LangGraph + langchain-core |
| Validation | Pydantic v2 / pydantic-settings |
| Database | Postgres 16 (pgvector), SQLAlchemy 2 (async) + Alembic, asyncpg |
| Queue/Cache | Redis + Celery |
| HTTP | httpx |
| Browser automation | Playwright |
| Frontend | Streamlit (MVP), Next.js (later) |
| Logging | structlog |
| Retries | tenacity |
| Package manager | uv |
| LLM | Anthropic (primary), OpenAI (fallback) |
| Storage | Local (now), S3-compatible interface (later) |
| PDF generation | Playwright `page.pdf()` |

---

## Architecture

Clean Architecture — dependencies point inward. See the `job-agent-architecture` skill before creating/moving modules or adding cross-layer dependencies.

```
src/jobhunter/
├── domain/
├── application/
├── agents/
├── adapters/
│   ├── llm/
│   ├── browser/
│   ├── boards/
│   └── notifications/
├── infrastructure/
│   ├── db/
│   └── repositories/
├── api/
├── workers/
└── common/

frontend/        # UI (Streamlit MVP, Next.js later)
tests/           # mirrors src/ paths
```

---

## Standards

- SOLID / DRY / KISS
- Full type hints — **mypy strict** and **ruff** must pass
- Async for all I/O
- Repository/provider interfaces as `Protocol`, wired via dependency injection
- Every module gets a test

---

## Skills

### Project skills
| Skill | Use when |
|---|---|
| `job-agent-architecture` | Creating/moving modules or adding cross-layer deps |
| `ats-resume-writing` | Resume / cover-letter / ATS agents |
| `browser-automation-hitl` | Any Playwright / browser-use code |
| `langgraph-agent-patterns` | Any graph/node under `agents/` |

### Installed Claude Code skills
| Skill | Use when |
|---|---|
| `full-output-enforcement` | Always — code is never truncated |
| `claude-api` | Writing LLM adapter code (correct model names/params/pricing) |
| `security-review` | During `/review` and before marking a milestone done |
| `simplify` | During `/review` and refactors |
| `dataviz`, `design-taste-frontend`, `minimalist-ui` | The frontend milestone |
| `run` | Launching the app |
| `loop` | Scheduled job-search runs (later) |
| `update-config`, `fewer-permission-prompts` | Adjusting `.claude/settings.json` |

---

## MCP Servers

- `ide` (VS Code diagnostics/exec) — connected
- `github`, `filesystem`, `playwright` — pending, enable when needed

---

## Slash Commands

| Command | Description |
|---|---|
| `/plan` | Plan a milestone, no code |
| `/milestone` | Implement one milestone, then stop |
| `/review` | Lint + type + test + security + simplify |
| `/frontend` | Dashboard UI |
| `/ship` | Pre-commit gate, no push |

---

## Getting Started

> Reference only — do not auto-run.

```bash
# Install dependencies
uv sync --extra dev
uv run playwright install chromium

# Start services (requires Docker Desktop running)
docker compose up -d

# Run database migrations
uv run alembic upgrade head

# Start the API
uv run uvicorn jobhunter.main:app --reload

# Start the UI
uv run streamlit run frontend/app.py

# Run tests
uv run pytest -q
```

---

## Milestone Roadmap

| # | Milestone |
|---|---|
| M1 | Scaffold + governance *(current)* |
| M2 | Data layer (schema, models, migrations, repos) |
| M3 | User profile + master-resume ingest |
| M4 | Job search/connectors + dedup |
| M5 | Matching/scoring |
| M6 | Resume generation |
| M7 | Cover letter + ATS optimization |
| M8 | Browser automation (HITL) |
| M9 | Review UI + approval |
| M10 | Tracking + notifications |
| M11 | Learning + memory (vector) |
| M12 | Dashboard + observability + full tests |

---

## Definition of Done (per milestone)

- [ ] `ruff` clean
- [ ] `mypy` strict passes
- [ ] Tests added and green
- [ ] Safety rules honored
- [ ] No unrelated changes
- [ ] `CLAUDE.md` updated if architecture changed
