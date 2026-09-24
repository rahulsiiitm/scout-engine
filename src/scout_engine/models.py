from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class OpportunityKind(str, Enum):
    INTERNSHIP = "internship"
    FULL_TIME = "full_time"
    COMPETITION = "competition"
    HACKATHON = "hackathon"
    CONTRACT = "contract"
    UNKNOWN = "unknown"


class Decision(str, Enum):
    DISCOVERED = "discovered"
    SURFACED = "surfaced"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


class Stage(str, Enum):
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"
    REVIEWING = "reviewing"
    APPLIED = "applied"
    OA = "oa"
    INTERVIEW = "interview"
    OFFER = "offer"
    OFFER_ACCEPTED = "offer_accepted"
    REJECTED = "rejected"
    CLOSED = "closed"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    NOT_PURSUING = "not_pursuing"


TERMINAL_STAGES = {Stage.OFFER_ACCEPTED, Stage.REJECTED, Stage.CLOSED, Stage.EXPIRED, Stage.WITHDRAWN, Stage.NOT_PURSUING}

ALLOWED_STAGE_TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.DISCOVERED: {Stage.QUALIFIED, Stage.CLOSED, Stage.EXPIRED, Stage.NOT_PURSUING},
    Stage.QUALIFIED: {Stage.REVIEWING, Stage.APPLIED, Stage.CLOSED, Stage.EXPIRED, Stage.WITHDRAWN, Stage.NOT_PURSUING},
    Stage.REVIEWING: {Stage.APPLIED, Stage.CLOSED, Stage.EXPIRED, Stage.WITHDRAWN, Stage.NOT_PURSUING},
    Stage.APPLIED: {Stage.OA, Stage.INTERVIEW, Stage.OFFER, Stage.REJECTED, Stage.CLOSED, Stage.WITHDRAWN},
    Stage.OA: {Stage.INTERVIEW, Stage.OFFER, Stage.REJECTED, Stage.CLOSED, Stage.WITHDRAWN},
    Stage.INTERVIEW: {Stage.OFFER, Stage.REJECTED, Stage.CLOSED, Stage.WITHDRAWN},
    Stage.OFFER: {Stage.OFFER_ACCEPTED, Stage.REJECTED, Stage.CLOSED, Stage.WITHDRAWN},
    Stage.OFFER_ACCEPTED: set(), Stage.REJECTED: set(), Stage.CLOSED: set(), Stage.EXPIRED: set(), Stage.WITHDRAWN: set(), Stage.NOT_PURSUING: set(),
}


@dataclass
class Compensation:
    currency: str
    min_annual: float | None = None
    max_annual: float | None = None
    period: str = "year"
    verified: bool = False
    source_url: str | None = None
    source: str | None = None
    verified_at: str | None = None
    converted_min_annual_inr: float | None = None
    converted_max_annual_inr: float | None = None
    fx_rate: float | None = None
    fx_rate_date: str | None = None
    fx_source: str | None = None

    @property
    def min_lpa_inr(self) -> float | None:
        value = self.converted_min_annual_inr
        if value is None and self.currency.upper() == "INR" and self.min_annual is not None:
            value = float(self.min_annual) * (12.0 if self.period == "month" else 1.0)
        return None if value is None else value / 100_000.0

    @property
    def max_lpa_inr(self) -> float | None:
        value = self.converted_max_annual_inr
        if value is None and self.currency.upper() == "INR" and self.max_annual is not None:
            value = float(self.max_annual) * (12.0 if self.period == "month" else 1.0)
        return None if value is None else value / 100_000.0


@dataclass
class Opportunity:
    id: str
    company: str
    title: str
    kind: OpportunityKind
    source: str
    canonical_url: str
    application_url: str | None = None
    description: str = ""
    location: str = ""
    remote: bool = False
    skills: list[str] = field(default_factory=list)
    experience_min: int | None = None
    experience_max: int | None = None
    graduation_years: list[int] = field(default_factory=list)
    employment_type_raw: str | None = None
    workplace_type: str | None = None
    internship_duration_months: float | None = None
    deadline_utc: str | None = None
    posted_at_utc: str | None = None
    updated_at_utc: str | None = None
    first_seen_utc: str | None = None
    last_seen_utc: str | None = None
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
        if target == self.stage: return
        if target not in ALLOWED_STAGE_TRANSITIONS[self.stage]: raise ValueError(f"Invalid stage transition: {self.stage} -> {target}")
        self.stage = target

    @property
    def is_terminal(self) -> bool: return self.stage in TERMINAL_STAGES

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self); raw["kind"] = self.kind.value; raw["decision"] = self.decision.value; raw["stage"] = self.stage.value; return raw

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Opportunity":
        data = dict(raw)
        if "stable_id" in data:
            stable_id = str(data.pop("stable_id")); data.setdefault("id", stable_id)
            compact_source = data.get("source")
            if isinstance(compact_source, str) and compact_source.startswith(("http://", "https://")):
                data.setdefault("canonical_url", compact_source); data["source"] = stable_id.split(":", 1)[0]
            else:
                data.setdefault("source", stable_id.split(":", 1)[0]); data.setdefault("canonical_url", "")
            aliases = {"issue":"issue_number","fit":"fit_score","confidence":"confidence_score","priority":"priority_score","conversion":"conversion_signal","verified_at":"last_verified_utc"}
            for old,new in aliases.items():
                if old in data: data.setdefault(new, data.pop(old))
            data.pop("status", None)
            legacy_metadata = {}
            for key in ("verified_open","evidence_matches"):
                if key in data: legacy_metadata[key] = data.pop(key)
            if not data.get("company"):
                company, sep, _ = str(data.get("title") or "").partition(" — ")
                if sep and company.strip(): data["company"] = company.strip()
            metadata = dict(data.get("metadata") or {}); metadata.update(legacy_metadata); metadata.setdefault("state_schema_normalized_from","v2_compact_recovery"); data["metadata"] = metadata

        # Emergency recovery ledgers may contain ID/issue/stage only. Keep these
        # as dedupe/lifecycle tombstones without guessing job facts or allowing
        # them into scoring. A later verified source hit replaces the stub.
        required = {"company", "title", "kind", "source", "canonical_url"}
        if not required.issubset(data):
            stable_id = str(data.get("id") or data.get("stable_id") or "")
            metadata = dict(data.get("metadata") or {})
            metadata["dedupe_only_recovery_stub"] = True
            data.setdefault("company", "")
            data.setdefault("title", "")
            data.setdefault("kind", OpportunityKind.UNKNOWN.value)
            data.setdefault("source", stable_id.split(":", 1)[0] if stable_id else "recovery")
            data.setdefault("canonical_url", "")
            data["metadata"] = metadata
            if "issue" in data: data.setdefault("issue_number", data.pop("issue"))
            if data.get("stage") == "historical":
                data["stage"] = Stage.NOT_PURSUING.value
                data.setdefault("suppression_reason", "historical recovery tombstone")
            if data.get("stage") in {Stage.QUALIFIED.value, Stage.REVIEWING.value, Stage.APPLIED.value, Stage.OA.value, Stage.INTERVIEW.value, Stage.OFFER.value, Stage.OFFER_ACCEPTED.value}:
                data.setdefault("decision", Decision.SURFACED.value)
            else:
                data.setdefault("decision", Decision.SUPPRESSED.value)

        data["kind"] = OpportunityKind(data["kind"])
        data["decision"] = Decision(data.get("decision", Decision.DISCOVERED))
        data["stage"] = Stage(data.get("stage", Stage.DISCOVERED))
        if data.get("compensation"):
            compensation = dict(data["compensation"])
            if "min_monthly" in compensation: compensation.setdefault("min_annual", compensation.pop("min_monthly")); compensation.setdefault("period","month")
            if "max_monthly" in compensation: compensation.setdefault("max_annual", compensation.pop("max_monthly")); compensation.setdefault("period","month")
            if "min" in compensation: compensation.setdefault("min_annual", compensation.pop("min"))
            if "max" in compensation: compensation.setdefault("max_annual", compensation.pop("max"))
            if "min_inr_lpa" in compensation: compensation.setdefault("converted_min_annual_inr", float(compensation.pop("min_inr_lpa"))*100_000)
            if "max_inr_lpa" in compensation: compensation.setdefault("converted_max_annual_inr", float(compensation.pop("max_inr_lpa"))*100_000)
            if "fx_date" in compensation: compensation.setdefault("fx_rate_date", compensation.pop("fx_date"))
            for key in list(compensation):
                if key.endswith("_inr") and key not in {"converted_min_annual_inr","converted_max_annual_inr"}: compensation.setdefault("fx_rate", compensation.pop(key))
            data["compensation"] = Compensation(**compensation)
        aliases = {"issue":"issue_number","fit":"fit_score","confidence":"confidence_score","priority":"priority_score","conversion":"conversion_signal"}
        for old,new in aliases.items():
            if old in data: data.setdefault(new, data.pop(old))
        return cls(**data)
