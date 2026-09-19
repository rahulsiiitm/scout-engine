from __future__ import annotations

import re


EXPLICIT_PATTERNS = (
    r"\bpre[- ]placement offer\b",
    r"\bppo\b",
    r"\breturn offer\b",
    r"\bfull[- ]time conversion\b",
    r"\bconvert(?:ed|ing)? to (?:a )?full[- ]time\b",
    r"\bconversion to (?:a )?full[- ]time\b",
    r"\bfull[- ]time offer(?:s)?\b",
)

LIKELY_PATTERNS = (
    r"successful interns?.{0,80}(?:employment|offer|join)",
    r"interns?.{0,80}(?:permanent|regular) (?:role|employment)",
    r"opportunity.{0,80}full[- ]time",
)


def detect_conversion_signal(text: str) -> tuple[str, list[str]]:
    normalized = " ".join(text.split())
    for label, patterns in (("explicit", EXPLICIT_PATTERNS), ("likely", LIKELY_PATTERNS)):
        matches: list[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, normalized, flags=re.IGNORECASE):
                start = max(0, match.start() - 55)
                end = min(len(normalized), match.end() + 85)
                matches.append(normalized[start:end].strip())
        if matches:
            return label, list(dict.fromkeys(matches))[:3]
    return "unknown", []
