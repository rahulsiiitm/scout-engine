from __future__ import annotations

import re

from .models import OpportunityKind


_INTERN_RE = re.compile(r"\b(?:intern|internship|internships)\b", re.IGNORECASE)
_CONTRACT_RE = re.compile(r"\b(?:contract|contractor|temporary)\b", re.IGNORECASE)


def infer_opportunity_kind(title: str, employment: str = "") -> OpportunityKind:
    """Infer broad opportunity type without substring false positives."""
    text = f"{title} {employment}"
    if _INTERN_RE.search(text):
        return OpportunityKind.INTERNSHIP
    if _CONTRACT_RE.search(text):
        return OpportunityKind.CONTRACT
    return OpportunityKind.FULL_TIME
