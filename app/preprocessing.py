"""Conservative sentence ledger. Source itself is stored without normalization."""

import itertools
import re

from app.models import Sentence

MAX_SOURCE = 200000


def sentences(source: str) -> list[Sentence]:
    """Keep wrapped sentences together and retain exact offsets in unmodified source."""
    if not source.strip() or len(source) > MAX_SOURCE or "\x00" in source:
        raise ValueError("SOP must contain 1–200,000 characters and no NUL characters")
    protected = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.$", re.IGNORECASE)
    boundaries = [0]
    for match in re.finditer(
        r"[.!?](?:[\"')]+)?(?=\s|$)|\n[ \t]*\n+|\n(?=[ \t]*(?:[-•*]|\d+[.)])\s)", source
    ):
        if match.group().startswith(".") and protected.search(source[: match.end()]):
            continue
        boundaries.append(match.end())
    boundaries.append(len(source))
    result: list[Sentence] = []
    for a, b in itertools.pairwise(boundaries):
        raw = source[a:b]
        if not raw.strip():
            continue
        start = a + len(raw) - len(raw.lstrip())
        end = b - (len(raw) - len(raw.rstrip()))
        result.append(Sentence(id=f"S{len(result) + 1}", text=source[start:end], start=start, end=end))
    return result
