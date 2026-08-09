---
description: Implement one approved milestone, then stop for review.
argument-hint: <milestone name or number>
---

Implement milestone: $ARGUMENTS

Follow plan -> observe -> implement. Consult CLAUDE.md and the relevant project skills
(job-agent-architecture, ats-resume-writing, browser-automation-hitl, langgraph-agent-patterns).
Use full-output-enforcement so nothing is truncated.

Rules:
- Implement ONLY this milestone. Do not touch unrelated code or break existing behavior.
- Add tests mirroring each new module. Keep mypy strict and ruff clean.
- Honor all safety rules (never auto-submit applications; never fabricate resume data; never write real secrets).
- Do NOT run destructive commands, servers, or installs unless I ask.

When done: summarize what changed (files + why), how to test it, and any follow-ups.
End with: "MILESTONE COMPLETE — awaiting review." Then stop.