"""Simple guardrail checker for LLM outputs.

Usage:
  python -m agentvault_mcp.guardrail path/to/output.txt
  cat reply.txt | python -m agentvault_mcp.guardrail

Fails (exit 1) if banned phrases are present or if no patch blocks
are detected. Banned list can be overridden via env:
  AGENTVAULT_BANNED=TODO,placeholder,pseudo-code
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable, List


DEFAULT_BANNED = [
    r"\bTODO\b",
    r"\bplaceholder\b",
    r"\bskeleton\b",
    r"pseudo-?code",
    r"\.\.\.",  # ellipses
]


def _load_banned() -> List[str]:
    raw = os.getenv("AGENTVAULT_BANNED")
    if not raw:
        return DEFAULT_BANNED
    items = [x.strip() for x in raw.split(",") if x.strip()]
    return [re.escape(i) for i in items]


def check_text(text: str) -> List[str]:
    """Return a list of issues found in text.

    Issues include banned phrases and missing patch envelope.
    """
    issues: List[str] = []
    banned = _load_banned()
    for pat in banned:
        if re.search(pat, text, re.IGNORECASE):
            issues.append(f"banned phrase matched: {pat}")

    has_begin = "*** Begin Patch" in text
    has_end = "*** End Patch" in text
    if not (has_begin and has_end):
        issues.append("no unified diff patch envelope detected")
    return issues


def _read_all(paths: Iterable[str]) -> str:
    if not paths:
        return sys.stdin.read()
    buf: List[str] = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            buf.append(f.read())
    return "\n".join(buf)


def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    text = _read_all(argv)
    issues = check_text(text)
    if issues:
        for i in issues:
            print(i, file=sys.stderr)
        return 1
    print("guardrail: ok")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

