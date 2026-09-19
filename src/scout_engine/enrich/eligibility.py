from __future__ import annotations

import re


_RANGE_PATTERNS = (
    re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I),
    re.compile(r"(?:minimum|min\.?|at least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\+\s*(?:years?|yrs?)", re.I),
)

_GRAD_CONTEXT = re.compile(
    r"(?:graduat(?:e|es|ed|ing|ion)|class\s+of|batch\s+of|degree\s+(?:completion|completed)|"
    r"expected\s+graduation).{0,90}?((?:20(?:2[4-9]|3\d))(?:\s*(?:,|/|or|and|to|-|–)\s*20(?:2[4-9]|3\d))*)",
    re.I,
)

_DURATION_PATTERNS = (
    re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*months?", re.I),
    re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*[- ]?months?\b", re.I),
)


def extract_experience(text: str) -> tuple[float | None, float | None]:
    first = _RANGE_PATTERNS[0].search(text)
    if first:
        return float(first.group(1)), float(first.group(2))
    for pattern in _RANGE_PATTERNS[1:]:
        match = pattern.search(text)
        if match:
            value = float(match.group(1))
            return value, None
    if re.search(r"\b(?:new grad(?:uate)?s?|freshers?|entry[- ]level|0\s*(?:-|–|to)\s*2\s*years?)\b", text, re.I):
        return 0.0, 2.0
    return None, None


def extract_graduation_years(text: str) -> list[int]:
    years: set[int] = set()
    for match in _GRAD_CONTEXT.finditer(text):
        years.update(
            int(value)
            for value in re.findall(r"20(?:2[4-9]|3\d)", match.group(1))
        )
    return sorted(years)


def extract_internship_duration_months(text: str) -> float | None:
    ranged = _DURATION_PATTERNS[0].search(text)
    if ranged:
        lo, hi = float(ranged.group(1)), float(ranged.group(2))
        return round((lo + hi) / 2, 2)
    single = _DURATION_PATTERNS[1].search(text)
    return float(single.group(1)) if single else None
