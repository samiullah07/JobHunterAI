#!/usr/bin/env python3
"""PostToolUse(Write/Edit): auto-format + lint-fix Python files with ruff."""

import contextlib
import json
import shutil
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    path = (data.get("tool_input") or {}).get("file_path", "")
    if not path.endswith(".py"):
        sys.exit(0)
    ruff = shutil.which("ruff")
    if not ruff:
        sys.exit(0)
    for args in (["format", path], ["check", "--fix", path]):
        with contextlib.suppress(Exception):
            subprocess.run([ruff, *args], capture_output=True, timeout=60, check=False)
    sys.exit(0)


if __name__ == "__main__":
    main()
