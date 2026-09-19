from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from .base import SourceAdapter, get_json
from ..models import Compensation, Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def _compensation(job: dict) -> Compensation | None:
    salary = job.get("salaryRange")
    if not isinstance(salary, dict):
        return None
    lo, hi = salary.get("min"), salary.get("max")
    if not isinstance(lo, (int, float)):
        return None
    interval = str(salary.get("interval") or "year").lower()
    period = "month" if "month" in interval else "year"
    return Compensation(
        currency=str(salary.get("currency") or "UNKNOWN").upper(),
        min_annual=float(lo),
        max_annual=float(hi) if isinstance(hi, (int, float)) else None,
        period=period,
        verified=True,
        source="Lever public Postings API",
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


class LeverAdapter(SourceAdapter):
    source_name = "lever"

    def __init__(self, company: str, site: str) -> None:
        self.company = company
        self.site = site

    @property
    def source_key(self) -> str:
        return f"lever:{self.site}"

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://api.lever.co/v0/postings/{self.site}?mode=json")
        out: list[Opportunity] = []
        for job in data:
            title = job.get("text", "")
            commitment = ((job.get("categories") or {}).get("commitment") or "").lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in title.lower() or "intern" in commitment else OpportunityKind.FULL_TIME
            location = (job.get("categories") or {}).get("location")
            workplace = job.get("workplaceType")
            description = " ".join(
                [
                    _strip_html(job.get("descriptionPlain") or job.get("description", "")),
                    " ".join(_strip_html(x.get("content", "")) for x in (job.get("lists") or [])),
                    _strip_html(job.get("additionalPlain") or job.get("additional", "")),
                ]
            ).strip()
            hosted = job.get("hostedUrl") or ""
            apply_url = job.get("applyUrl") or hosted
            comp = _compensation(job)
            provenance = {
                "title": "lever",
                "location": "lever",
                "description": "lever",
                "workplace_type": "lever",
            }
            if comp:
                provenance["compensation"] = "lever"
            out.append(
                Opportunity(
                    id=f"lever:{self.site}:{job['id']}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=hosted or apply_url,
                    application_url=apply_url,
                    description=description,
                    location=location,
                    remote=str(workplace or "").lower() == "remote" or "remote" in (location or "").lower(),
                    employment_type_raw=(job.get("categories") or {}).get("commitment"),
                    workplace_type=workplace,
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
