from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .dedupe import find_duplicate
from .models import Decision, Opportunity, Stage
from .policies import apply_hard_gates
from .scoring import confidence_score, evidence_match, fit_score, priority_score


@dataclass(slots=True)
class EngineConfig:
    minimum_score: float = 6.0
    urgent_score_floor: float = 4.0
    high_fit_score: float = 8.0
    minimum_lpa_exclusive: float = 10.0
    candidate_has_publications: bool = False
    max_years_without_override: float = 2.0
    dedupe_threshold: float = 0.86


def evaluate(
    opportunity: Opportunity,
    *,
    profile: dict[str, Any],
    existing: list[Opportunity],
    config: EngineConfig | None = None,
    now: datetime | None = None,
) -> Opportunity:
    cfg = config or EngineConfig()
    current = now or datetime.now(timezone.utc)

    duplicate = find_duplicate(opportunity, existing, cfg.dedupe_threshold)
    if duplicate and duplicate.id != opportunity.id:
        duplicate.last_seen_utc = current.isoformat()
        duplicate.source_urls = sorted(set(duplicate.source_urls + [opportunity.canonical_url]))
        return duplicate

    gate = apply_hard_gates(
        opportunity,
        minimum_lpa_exclusive=cfg.minimum_lpa_exclusive,
        candidate_has_publications=cfg.candidate_has_publications,
        max_years_without_override=cfg.max_years_without_override,
    )
    if not gate.passed:
        opportunity.decision = Decision.SUPPRESSED
        opportunity.suppression_reason = gate.reason
        return opportunity

    opportunity.evidence, opportunity.missing_requirements = evidence_match(opportunity, profile)
    opportunity.fit_score = fit_score(opportunity, profile)
    opportunity.confidence_score = confidence_score(opportunity)
    opportunity.priority_score = priority_score(opportunity, current)

    if opportunity.fit_score >= cfg.minimum_score:
        opportunity.decision = Decision.SURFACED
        if opportunity.stage == Stage.DISCOVERED:
            opportunity.stage = Stage.QUALIFIED
    else:
        opportunity.decision = Decision.SUPPRESSED
        opportunity.suppression_reason = f"fit score {opportunity.fit_score:.1f} below {cfg.minimum_score:.1f}"

    return opportunity
