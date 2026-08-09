---
description: Pre-commit gate — format, lint, type, test, then summarize the diff. No push.
---

Prepare a commit (do NOT push):
1. `ruff format .` then `ruff check --fix .`
2. `mypy src`
3. `pytest -q`
4. `git add -A` and show `git status` + a concise `git diff --stat`
5. Propose a Conventional Commits message.

Stop after proposing the message. I will review and commit/push manually.