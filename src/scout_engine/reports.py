from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import Decision, Opportunity, OpportunityKind, Stage


IST = ZoneInfo("Asia/Kolkata")


def _active(opportunities: list[Opportunity]) -> list[Opportunity]:
    return [
        o for o in opportunities
        if o.decision == Decision.SURFACED and o.stage not in {Stage.EXPIRED, Stage.REJECTED, Stage.WITHDRAWN, Stage.NOT_PURSUING}
    ]


def render_weekly(opportunities: list[Opportunity], week_label: str) -> str:
    active = _active(opportunities)
    stages = Counter(o.stage.value for o in opportunities)
    jobs = [o for o in active if o.kind in {OpportunityKind.FULL_TIME, OpportunityKind.INTERNSHIP, OpportunityKind.CONTRACT}]
    comps = [o for o in active if o.kind in {OpportunityKind.COMPETITION, OpportunityKind.HACKATHON}]
    high_fit = [o for o in active if (o.fit_score or 0) >= 8]
    applied_denominator = sum(stages[s] for s in (Stage.APPLIED.value, Stage.OA.value, Stage.INTERVIEW.value, Stage.OFFER.value, Stage.OFFER_ACCEPTED.value, Stage.REJECTED.value))
    responses = sum(stages[s] for s in (Stage.OA.value, Stage.INTERVIEW.value, Stage.OFFER.value, Stage.OFFER_ACCEPTED.value, Stage.REJECTED.value))
    interviews = sum(stages[s] for s in (Stage.INTERVIEW.value, Stage.OFFER.value, Stage.OFFER_ACCEPTED.value))

    response_rate = "N/A" if not applied_denominator else f"{responses / applied_denominator:.0%}"
    interview_rate = "N/A" if not applied_denominator else f"{interviews / applied_denominator:.0%}"

    lines = [
        f"# Weekly Funnel — {week_label}",
        "",
        "Generated from `data/opportunities.json`, the canonical state store.",
        "",
        "## Opportunity intake",
        "",
        f"- Opportunities known: **{len(opportunities)}**",
        f"- Active surfaced opportunities: **{len(active)}**",
        f"- Active jobs / internships / contracts: **{len(jobs)}**",
        f"- Active competitions / hackathons: **{len(comps)}**",
        f"- Active high-fit (>=8): **{len(high_fit)}**",
        "",
        "## Application funnel",
        "",
        "| Stage | Count |",
        "| --- | ---: |",
        f"| Qualified / reviewing | {stages[Stage.QUALIFIED.value] + stages[Stage.REVIEWING.value]} |",
        f"| Applied | {stages[Stage.APPLIED.value]} |",
        f"| OA | {stages[Stage.OA.value]} |",
        f"| Interview | {stages[Stage.INTERVIEW.value]} |",
        f"| Offer | {stages[Stage.OFFER.value] + stages[Stage.OFFER_ACCEPTED.value]} |",
        f"| Rejected | {stages[Stage.REJECTED.value]} |",
        "",
        f"**Response rate:** {response_rate}  ",
        f"**Interview rate:** {interview_rate}",
        "",
    ]
    return "\n".join(lines)


def write_weekly(opportunities: list[Opportunity], when: datetime | None = None) -> Path:
    now = when or datetime.now(IST)
    iso = now.isocalendar()
    label = f"{iso.year}-W{iso.week:02d}"
    path = Path("weekly") / f"{label}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_weekly(opportunities, label), encoding="utf-8")
    return path
