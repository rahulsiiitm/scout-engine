from __future__ import annotations

from .conversion import detect_conversion_signal
from .eligibility import extract_experience, extract_graduation_years, extract_internship_duration_months
from .fx import convert_compensation_to_inr
from .research import classify_research_requirement
from ..models import Opportunity, OpportunityKind


def enrich_opportunity(opportunity: Opportunity) -> Opportunity:
    text = f"{opportunity.title}\n{opportunity.description}"
    if opportunity.experience_min is None:
        lo, hi = extract_experience(text)
        opportunity.experience_min = lo
        opportunity.experience_max = hi
    if not opportunity.graduation_years:
        opportunity.graduation_years = extract_graduation_years(text)
    if opportunity.kind == OpportunityKind.INTERNSHIP and opportunity.internship_duration_months is None:
        opportunity.internship_duration_months = extract_internship_duration_months(text)

    signal, evidence = detect_conversion_signal(text)
    if signal != "unknown":
        opportunity.conversion_signal = signal
        opportunity.conversion_evidence = evidence

    research_heavy, requires_publications = classify_research_requirement(
        opportunity.title, opportunity.description
    )
    opportunity.research_heavy = opportunity.research_heavy or research_heavy
    opportunity.requires_publications = opportunity.requires_publications or requires_publications

    if opportunity.compensation and opportunity.compensation.verified:
        convert_compensation_to_inr(opportunity.compensation)
    return opportunity


__all__ = ["enrich_opportunity"]
