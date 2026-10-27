from __future__ import annotations

import re


EXPLICIT_PATTERNS = (
    r"\bpre[- ]placement offer\b",
    # Bare "PPO" also means proximal policy optimization in ML job descriptions.
    # Count only employment-offer language as pre-placement evidence.
    r"\bppo\b(?:\s+(?:is|may be|will be|can be))?\s+(?:available|offered|provided|possible|eligible|opportunit(?:y|ies)|conversion|potential|consideration)\b",
    r"\bppo\b\s+(?:for\s+(?:successful|top|eligible|high[- ]performing|interns?|candidates?)|after\s+(?:internship|completion)|based on\s+(?:performance|internship))\b",
    r"\b(?:receive|earn|offer(?:ed)?|provide(?:d)?|eligible for|chance of|possibility of|potential for)\s+(?:an?\s+)?ppo\b",
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
                # "No PPO is offered" is not a positive conversion promise.
                if r"\bppo\b" in pattern and re.search(
                    r"\b(?:no|without|never)\s+(?:an?\s+)?ppo\b",
                    normalized[max(0, match.start() - 16):match.end()],
                    flags=re.IGNORECASE,
                ):
                    continue
                start = max(0, match.start() - 55)
                end = min(len(normalized), match.end() + 85)
                matches.append(normalized[start:end].strip())
        if matches:
            return label, list(dict.fromkeys(matches))[:3]
    return "unknown", []
