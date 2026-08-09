---
description: Quality gate — lint, type-check, tests, security + simplification review.
---

Run the quality gate on the current changes. Report results; fix only what you find here.

1. `ruff format --check .` and `ruff check .`
2. `mypy src`
3. `pytest -q`
4. Invoke the security-review skill on new/changed code (focus: secrets handling, injection, auth, browser automation safety, the never-auto-submit rule).
5. Invoke the simplify skill to flag duplication / over-engineering.

Summarize pass/fail per step with concrete fixes. Do not push or deploy.