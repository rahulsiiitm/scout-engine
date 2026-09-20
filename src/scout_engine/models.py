from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class OpportunityKind(StrEnum):
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    CONTRACT = "contract"
    COMPETITION = "competition"
    HACKATHON = "hackathon"


class Decision(StrEnum):
    DISCOVERED = "discovered"
    SURFACED = "surfaced"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


class Stage(StrEnum):
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    REVIEWING = "reviewing"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    OFFER_ACCEPTED = "offer_accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    NOT_PURSUING = "not_pursuing"


TERMINAL_STAGES = {
    Stage.OFFER_ACCEPTED,
    Stage.REJECTED,
    Stage.WITHDRAWN,
    Stage.EXPIRED,
    Stage.NOT_PURSUING,
}

ALLOWED_STAGE_TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.DISCOVERED: {Stage.QUALIFIED, Stage.NOT_PURSUING, Stage.EXPIRED},
    Stage.QUALIFIED: {Stage.REVIEWING, Stage.APPLIED, Stage.NOT_PURSUING, Stage.EXPIRED},
    Stage.REVIEWING: {Stage.QUALIFIED, Stage.APPLIED, Stage.NOT_PURSUING, Stage.EXPIRED},
    Stage.APPLIED: {Stage.OA, Stage.INTERVIEW, Stage.OFFER, Stage.REJECTED, Stage.WITHDRAWN},
    Stage.OA: {Stage.INTERVIEW, Stage.OFFER, Stage.REJECTED, Stage.WITHDRAWN},
    Stage.INTERVIEW: {Stage.OFFER, Stage.REJECTED, Stage.WITHDRAWN},
    Stage.OFFER: {Stage.OFFER_ACCEPTED, Stage.WITHDRAWN},
    Stage.OFFER_ACCEPTED: set(),
    Stage.REJECTED: set(),
    Stage.WITHDRAWN: set(),
    Stage.EXPIRED: set(),
    Stage.NOT_PURSUING: set(),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Compensation:
    currency: str = "INR"
    min_annual: float | None = None
    max_annual: float | None = None
    period: str = "year"
    verified: bool = False
    source: str | None = None
    verified_at: str | None = None
    converted_min_annual_inr: float | None = None
    converted_max_annual_inr: float | None = None
    fx_rate: float | None = None
    fx_rate_date: str | None = None
    fx_source: str | None = None

    @property
    def min_lpa_inr(self) -> float | None:
        amount = self.min_annual
        if amount is None:
            return None
        if self.period == "month":
            amount *= 12
        if self.currency.upper() == "INR":
            return amount / 100_000
        if self.converted_min_annual_inr is not None:
            return self.converted_min_annual_inr / 100_000
        return None


@dataclass(slots=True)
class Opportunity:
    id: str
    company: str
    title: str
    kind: OpportunityKind
    source: str
    canonical_url: str
    application_url: str | None = None
    description: str = ""
    location: str | None = None
    remote: bool | None = None
    skills: list[str] = field(default_factory=list)
    experience_min: float | None = None
    experience_max: float | None = None
    graduation_years: list[int] = field(default_factory=list)
    employment_type_raw: str | None = None
    workplace_type: str | None = None
    internship_duration_months: float | None = None
    deadline_utc: str | None = None
    posted_at_utc: str | None = None
    updated_at_utc: str | None = None
    first_seen_utc: str = field(default_factory=utc_now_iso)
    last_seen_utc: str = field(default_factory=utc_now_iso)
    last_verified_utc: str | None = None
    compensation: Compensation | None = None
    research_heavy: bool = False
    requires_publications: bool = False
    conversion_signal: str = "unknown"
    conversion_evidence: list[str] = field(default_factory=list)
    source_status: str = "unknown"
    extraction_method: str | None = None
    source_confidence: float = 0.80
    field_provenance: dict[str, str] = field(default_factory=dict)
    content_hash: str | None = None
    last_http_status: int | None = None
    missing_successful_scans: int = 0
    fit_score: float | None = None
    confidence_score: float | None = None
    priority_score: float | None = None
    decision: Decision = Decision.DISCOVERED
    stage: Stage = Stage.DISCOVERED
    suppression_reason: str | None = None
    issue_number: int | None = None
    source_urls: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    missing_requirements: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def transition(self, target: Stage) -> None:
        if target == self.stage:
            return
        if target not in ALLOWED_STAGE_TRANSITIONS[self.stage]:
            raise ValueError(f"Invalid stage transition: {self.stage} -> {target}")
        self.stage = target

    @property
    def is_terminal(self) -> bool:
        return self.stage in TERMINAL_STAGES

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["kind"] = self.kind.value
        raw["decision"] = self.decision.value
        raw["stage"] = self.stage.value
        return raw

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Opportunity":
        data = dict(raw)
        data["kind"] = OpportunityKind(data["kind"])
        data["decision"] = Decision(data.get("decision", Decision.DISCOVERED))
        data["stage"] = Stage(data.get("stage", Stage.DISCOVERED))
        if data.get("compensation"):
            compensation = dict(data["compensation"])
            if "min_monthly" in compensation:
                compensation.setdefault("min_annual", compensation.pop("min_monthly"))
                compensation.setdefault("period", "month")
            if "max_monthly" in compensation:
                compensation.setdefault("max_annual", compensation.pop("max_monthly"))
                compensation.setdefault("period", "month")
            data["compensation"] = Compensation(**compensation)
        return cls(**data)
