from __future__ import annotations

import re


_PUBLICATION_PATTERNS = (
    r"\bpublications?\b",
    r"\bpeer[- ]reviewed\b",
    r"\bresearch track record\b",
    r"\bpublication record\b",
    r"\btop[- ]tier (?:conference|journal)s?\b",
    r"\bneurips\b",
    r"\bicml\b",
    r"\biclr\b",
    r"\bcvpr\b",
    r"\bacl\b",
)

_RESEARCH_TITLES = (
    "research scientist",
    "research engineer",
    "applied scientist",
    "researcher",
)


def classify_research_requirement(title: str, description: str) -> tuple[bool, bool]:
    text = f"{title}\n{description}".lower()
    research_heavy = any(token in title.lower() for token in _RESEARCH_TITLES)
    requires_publications = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _PUBLICATION_PATTERNS)
    return research_heavy, requires_publications
