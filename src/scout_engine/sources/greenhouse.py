from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from .base import SourceAdapter, get_json
from ..models import Compensation, Opportunity, OpportunityKind
from ..time_utils import to_utc_iso


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def _kind(title: str) -> OpportunityKind:
    return OpportunityKind.INTERNSHIP if "intern" in title.lower() else OpportunityKind.FULL_TIME


def _compensation(job: dict) -> Compensation | None:
    candidates = job.get("pay_transparency") or job.get("pay_input_ranges") or []
    if isinstance(candidates, dict):
        candidates = [candidates]
    mins: list[float] = []
    maxs: list[float] = []
    currency = None
    period = "year"
    for item in candidates or []:
        if not isinstance(item, dict):
            continue
        lo = item.get("min") or item.get("min_cents")
        hi = item.get("max") or item.get("max_cents")
        if item.get("min_cents") is not None and isinstance(lo, (int, float)):
            lo = float(lo) / 100
        if item.get("max_cents") is not None and isinstance(hi, (int, float)):
            hi = float(hi) / 100
        if isinstance(lo, (int, float)):
            mins.append(float(lo))
        if isinstance(hi, (int, float)):
            maxs.append(float(hi))
        currency = currency or item.get("currency") or item.get("currency_code")
        raw_period = str(item.get("period") or item.get("interval") or "").lower()
        if "month" in raw_period:
            period = "month"
    if not mins:
        return None
    return Compensation(
        currency=str(currency or "UNKNOWN").upper(),
        min_annual=min(mins),
        max_annual=max(maxs) if maxs else None,
        period=period,
        verified=True,
        source="Greenhouse public job board API",
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


class GreenhouseAdapter(SourceAdapter):
    source_name = "greenhouse"

    def __init__(self, company: str, board: str) -> None:
        self.company = company
        self.board = board

    @property
    def source_key(self) -> str:
        return f"greenhouse:{self.board}"

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs?content=true")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            location = (job.get("location") or {}).get("name")
            posted = job.get("first_published") or job.get("created_at")
            updated = job.get("updated_at")
            deadline = job.get("application_deadline")
            try:
                posted = to_utc_iso(posted) if posted else None
            except (ValueError, TypeError):
                posted = None
            try:
                updated = to_utc_iso(updated) if updated else None
            except (ValueError, TypeError):
                updated = None
            try:
                deadline = to_utc_iso(deadline) if deadline else None
            except (ValueError, TypeError):
                deadline = None
            url = job.get("absolute_url", "")
            provenance = {"title": "greenhouse", "location": "greenhouse", "description": "greenhouse"}
            if posted:
                provenance["posted_at_utc"] = "greenhouse"
            if updated:
                provenance["updated_at_utc"] = "greenhouse"
            if deadline:
                provenance["deadline_utc"] = "greenhouse"
            comp = _compensation(job)
            if comp:
                provenance["compensation"] = "greenhouse"
            out.append(
                Opportunity(
                    id=f"greenhouse:{self.board}:{job['id']}",
                    company=self.company,
                    title=title,
                    kind=_kind(title),
                    source=self.source_name,
                    canonical_url=url,
                    application_url=url,
                    description=_strip_html(job.get("content", "")),
                    location=location,
                    remote="remote" in (location or "").lower(),
                    posted_at_utc=posted,
                    updated_at_utc=updated,
                    deadline_utc=deadline,
                    compensation=comp,
                    source_status="open",
                    extraction_method="official_api",
                    source_confidence=0.98,
                    field_provenance=provenance,
                    last_http_status=200,
                    metadata={"raw_id": job["id"], "source_key": self.source_key},
                )
            )
        return out
