from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from .models import Opportunity, OpportunityKind
from .time_utils import days_until


ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "fastapi": ("fastapi",),
    "pytorch": ("pytorch", "torch"),
    "rag": ("rag", "retrieval augmented generation", "retrieval-augmented generation"),
    "llm_orchestration": ("langchain", "langgraph", "agentic", "agents", "llm orchestration"),
    "docker": ("docker", "containerization", "containers"),
    "computer_vision": ("computer vision", "opencv", "object detection", "tracking", "yolo"),
    "cpp": ("c++", "cpp"),
    "ros": ("ros", "ros2"),
    "qdrant": ("qdrant", "vector database", "vector db"),
    "faiss": ("faiss",),
    "flask": ("flask",),
    "kubernetes": ("kubernetes", "k8s"),
}


def extract_skills(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for canonical, aliases in ALIASES.items():
        if any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lower) for alias in aliases):
            found.append(canonical)
    return found


def evidence_match(opportunity: Opportunity, profile: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    text = " ".join([opportunity.title, opportunity.description, " ".join(opportunity.skills)])
    required = extract_skills(text)
    evidence_map = profile.get("evidence", {})
    evidence: dict[str, list[str]] = {}
    missing: list[str] = []
    for skill in required:
        entries = list(evidence_map.get(skill, []) or [])
        if entries:
            evidence[skill] = entries
        else:
            missing.append(skill)
    return evidence, missing


def fit_score(opportunity: Opportunity, profile: dict[str, Any]) -> float:
    text = " ".join([opportunity.title, opportunity.description, " ".join(opportunity.skills)])
    required = set(extract_skills(text))
    strong = set(profile.get("skills", {}).get("strong", []) or [])
    working = set(profile.get("skills", {}).get("working", []) or [])

    if required:
        weighted_hits = sum(1.0 for s in required if s in strong) + sum(0.65 for s in required if s in working)
        tech = min(4.0, 4.0 * weighted_hits / max(1, len(required)))
    else:
        tech = 1.5

    evidence, _ = evidence_match(opportunity, profile)
    evidence_points = min(2.0, 0.5 * len(evidence))

    years = opportunity.experience_min
    if years is None or years <= 1:
        seniority = 2.0
    elif years <= 2:
        seniority = 1.5
    else:
        seniority = 0.0

    preferred_locations = " ".join(profile.get("locations", {}).get("preferred", [])).lower()
    loc = (opportunity.location or "").lower()
    logistics = 1.0 if opportunity.remote or any(x and x in preferred_locations for x in (loc, "remote" if opportunity.remote else "")) else 0.5

    target_roles = set(profile.get("roles", {}).get("primary", []) or []) | set(profile.get("roles", {}).get("secondary", []) or [])
    title = opportunity.title.lower()
    role_terms = {
        "applied_ai": ("applied ai", "ai engineer"),
        "ml_engineer": ("machine learning", "ml engineer"),
        "backend_engineer": ("backend", "platform engineer"),
        "sde": ("software engineer", "sde"),
        "robotics_perception": ("robotics", "perception", "autonomy", "slam"),
        "ai_reliability": ("reliability", "evaluation", "evals"),
        "ml_infrastructure": ("ml infrastructure", "mlops", "ai infrastructure"),
    }
    direction = 0.0
    for role in target_roles:
        if any(term in title for term in role_terms.get(role, ())):
            direction = 1.0
            break
    if opportunity.kind in {OpportunityKind.HACKATHON, OpportunityKind.COMPETITION}:
        direction = max(direction, 0.75)

    total = tech + evidence_points + seniority + logistics + direction
    return round(min(10.0, total), 1)


def confidence_score(opportunity: Opportunity) -> float:
    signals = [
        bool(opportunity.company),
        bool(opportunity.title),
        bool(opportunity.canonical_url),
        bool(opportunity.description.strip()),
        opportunity.last_verified_utc is not None,
        opportunity.kind is not None,
        opportunity.location is not None or opportunity.remote is not None,
        opportunity.deadline_utc is not None or opportunity.kind not in {OpportunityKind.COMPETITION, OpportunityKind.HACKATHON},
    ]
    completeness = sum(signals) / len(signals)
    source_trust = max(0.0, min(1.0, float(opportunity.source_confidence)))

    if opportunity.kind == OpportunityKind.FULL_TIME:
        comp_ok = opportunity.compensation is not None and opportunity.compensation.verified
        completeness = (completeness * len(signals) + (1.0 if comp_ok else 0.0)) / (len(signals) + 1)

    return round(completeness * 0.72 + source_trust * 0.28, 2)


def priority_score(opportunity: Opportunity, now: datetime | None = None) -> float:
    current = now or datetime.now(timezone.utc)
    fit = opportunity.fit_score or 0.0
    freshness = 0.0
    if opportunity.posted_at_utc:
        posted = datetime.fromisoformat(opportunity.posted_at_utc.replace("Z", "+00:00"))
        age_days = max(0.0, (current - posted.astimezone(timezone.utc)).total_seconds() / 86400)
        freshness = 2.0 * math.exp(-age_days / 7.0)

    urgency = 0.0
    if opportunity.deadline_utc:
        d = days_until(opportunity.deadline_utc, current)
        if d >= 0:
            urgency = 2.0 * math.exp(-d / 4.0)

    conversion_bonus = 0.0
    duration_bonus = 0.0
    if opportunity.kind == OpportunityKind.INTERNSHIP:
        if opportunity.conversion_signal == "explicit":
            conversion_bonus = 0.8
        elif opportunity.conversion_signal == "likely":
            conversion_bonus = 0.25
        if opportunity.internship_duration_months is not None and 4 <= opportunity.internship_duration_months <= 6:
            duration_bonus = 0.15

    return round(min(10.0, fit * 0.6 + freshness + urgency + conversion_bonus + duration_bonus), 1)
