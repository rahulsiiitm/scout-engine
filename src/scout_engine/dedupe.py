from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit, urlunsplit

from .models import Opportunity


def normalize_text(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower() or "https", host, path, "", ""))


def duplicate_similarity(a: Opportunity, b: Opportunity) -> float:
    if a.id == b.id:
        return 1.0
    if canonicalize_url(a.canonical_url) == canonicalize_url(b.canonical_url):
        return 1.0

    company = SequenceMatcher(None, normalize_text(a.company), normalize_text(b.company)).ratio()
    title = SequenceMatcher(None, normalize_text(a.title), normalize_text(b.title)).ratio()
    location = SequenceMatcher(
        None,
        normalize_text(a.location or ""),
        normalize_text(b.location or ""),
    ).ratio() if (a.location or b.location) else 1.0

    return round(company * 0.45 + title * 0.45 + location * 0.10, 4)


def find_duplicate(
    candidate: Opportunity,
    existing: list[Opportunity],
    threshold: float = 0.86,
) -> Opportunity | None:
    best: tuple[float, Opportunity] | None = None
    for item in existing:
        score = duplicate_similarity(candidate, item)
        if score >= threshold and (best is None or score > best[0]):
            best = (score, item)
    return best[1] if best else None
