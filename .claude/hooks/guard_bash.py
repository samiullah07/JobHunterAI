#!/usr/bin/env python3
"""PreToolUse(Bash): block destructive or secret-leaking commands."""

import json
import re
import sys

DENY = [
    (r"\brm\s+-rf\s+(/|~|\$HOME|\*)", "Refusing destructive recursive delete."),
    (r":\(\)\s*\{.*\};:", "Fork-bomb pattern blocked."),
    (r"\bmkfs\b", "Filesystem format blocked."),
    (r"\bdd\s+if=", "Raw disk write blocked."),
    (r"git\s+push\s+.*(--force|-f\b)", "Force-push blocked; push manually if intended."),
    (r"chmod\s+-R\s+777\s+/", "Recursive chmod 777 on / blocked."),
    (r"(curl|wget)\s+[^|]*\|\s*(sudo\s+)?(bash|sh)\b", "Piping remote script to shell blocked."),
    (r"cat\s+[^|]*\.env(?!\.example)\b", "Reading .env blocked (secret-leak risk)."),
    (r"(printenv|env)\s*\|\s*(curl|wget|nc)\b", "Environment exfiltration blocked."),
]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command", "")
    for pattern, message in DENY:
        if re.search(pattern, cmd, re.IGNORECASE):
            print(f"[guard_bash] {message}", file=sys.stderr)
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
