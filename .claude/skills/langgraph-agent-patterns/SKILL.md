---
name: langgraph-agent-patterns
description: Conventions for building the LangGraph agent graphs — state schema, checkpointing, human-approval interrupts, LLM provider selection, and cost guardrails. Consult before writing any graph or node under agents/.
---

# LangGraph Agent Patterns

Graph: discover -> evaluate/score -> tailor_resume -> write_cover_letter -> fill_application -> HUMAN_APPROVAL -> submit -> track.

State:
- One typed state object (TypedDict or pydantic) carrying job, profile, scores, artifacts, review_packet, costs. Nodes return partial updates.

Human approval:
- Use LangGraph interrupt() before submit. The graph pauses; the review UI resumes it with approve / reject / edit / regenerate / skip. Submit is unreachable without an approve.

Persistence:
- Use a Postgres checkpointer so runs survive restarts and are resumable. Thread id = application id.

LLM providers:
- Provider-agnostic interface; Anthropic primary, OpenAI fallback. When writing provider code, consult the claude-api skill for correct model names, params, and pricing — do not hardcode from memory.

Cost & reliability guardrails:
- Track token spend per run; enforce LLM_MONTHLY_BUDGET_USD and stop/alert when exceeded.
- tenacity retries with backoff on transient LLM/network errors; cap total attempts.
- Log every node transition via structlog with the thread id.