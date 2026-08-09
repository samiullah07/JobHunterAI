#!/usr/bin/env python3
"""PreToolUse(Write/Edit): stop the agent from writing real secret files."""

import json
import os
import sys

ALLOWED_SUFFIXES = (".example", ".template", ".sample")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    path = (data.get("tool_input") or {}).get("file_path", "")
    base = os.path.basename(path)
    if base.startswith(".env") and not base.endswith(ALLOWED_SUFFIXES):
        print(
            f"[protect_secrets] Refusing to write a real secrets file ({base}). "
            "Create/edit it manually; keep secrets out of the agent.",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
