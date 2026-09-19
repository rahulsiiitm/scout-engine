from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import Opportunity, OpportunityKind
from .time_utils import days_until


@dataclass(frozen=True, slots=True)
class GateResult:
    passed: bool
    reason: str | None = None


def salary_gate(opportunity: Opportunity, minimum_lpa_exclusive: float = 10.0) -> GateResult:
    if opportunity.kind != OpportunityKind.FULL_TIME:
        return GateResult(True)

    comp = opportunity.compensation
    if comp is None or not comp.verified:
        return GateResult(False, "full-time compensation is missing or unverified")

    min_lpa = comp.min_lpa_inr
    if min_lpa is None:
        return GateResult(False, "full-time compensation cannot be verified in INR")
    if min_lpa <= minimum_lpa_exclusive:
        return GateResult(
            False,
            f"full-time compensation floor is {min_lpa:.2f} LPA; must be > {minimum_lpa_exclusive:.2f} LPA",
        )
    return GateResult(True)


def seniority_gate(opportunity: Opportunity, max_years_without_override: float = 2.0) -> GateResult:
    text = f"{opportunity.title} {opportunity.description}".lower()
    override = any(
        token in text
        for token in (
            "new grad",
            "new graduate",
            "freshers",
            "fresher",
            "0-2 years",
            "0–2 years",
            "students",
            "graduating",
        )
    )
    if override:
        return GateResult(True)

    if opportunity.experience_min is not None and opportunity.experience_min > max_years_without_override:
        return GateResult(
            False,
            f"minimum experience is {opportunity.experience_min:g} years with no new-grad override",
        )
    return GateResult(True)


def research_gate(opportunity: Opportunity, candidate_has_publications: bool = False) -> GateResult:
    if not opportunity.research_heavy and not opportunity.requires_publications:
        return GateResult(True)
    if opportunity.requires_publications and not candidate_has_publications:
        return GateResult(False, "role materially expects publications/research credentials")
    return GateResult(True)


def deadline_gate(opportunity: Opportunity, now: datetime | None = None) -> GateResult:
    if not opportunity.deadline_utc:
        return GateResult(True)
    if days_until(opportunity.deadline_utc, now=now or datetime.now(timezone.utc)) < 0:
        return GateResult(False, "deadline has passed")
    return GateResult(True)


def apply_hard_gates(
    opportunity: Opportunity,
    *,
    minimum_lpa_exclusive: float = 10.0,
    candidate_has_publications: bool = False,
    max_years_without_override: float = 2.0,
) -> GateResult:
    gates = (
        salary_gate(opportunity, minimum_lpa_exclusive),
        seniority_gate(opportunity, max_years_without_override),
        research_gate(opportunity, candidate_has_publications),
        deadline_gate(opportunity),
    )
    for result in gates:
        if not result.passed:
            return result
    return GateResult(True)
