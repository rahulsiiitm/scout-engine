from __future__ import annotations

import html
import re

from .base import SourceAdapter, get_json
from ..models import Compensation, Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def _compensation(job: dict) -> Compensation | None:
    comp = job.get("compensation")
    if not isinstance(comp, dict):
        return None
    tiers = comp.get("compensationTiers") or comp.get("tiers") or []
    if not tiers and comp.get("summaryComponents"):
        tiers = [comp]
    mins, maxs = [], []
    currency = None
    for tier in tiers:
        components = tier.get("components") or tier.get("summaryComponents") or []
        for component in components:
            ctype = str(component.get("compensationType") or component.get("type") or "").lower()
            interval = str(component.get("interval") or component.get("period") or "").lower()
            if ctype and "salary" not in ctype and "base" not in ctype:
                continue
            if interval and interval not in {"year", "yearly", "annual", "annually"}:
                continue
            lo = component.get("minValue") or component.get("min")
            hi = component.get("maxValue") or component.get("max")
            currency = currency or component.get("currencyCode") or component.get("currency")
            if isinstance(lo, (int, float)):
                mins.append(float(lo))
            if isinstance(hi, (int, float)):
                maxs.append(float(hi))
    if not mins:
        return None
    return Compensation(currency=str(currency or "").upper() or "UNKNOWN", min_annual=min(mins), max_annual=max(maxs) if maxs else None, period="year", verified=True, source="Ashby public job posting API")


class AshbyAdapter(SourceAdapter):
    source_name = "ashby"

    def __init__(self, company: str, board: str) -> None:
        self.company = company
        self.board = board

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}?includeCompensation=true")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            lower = title.lower()
            employment = str(job.get("employmentType") or "").lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in lower or "intern" in employment else OpportunityKind.FULL_TIME
            location = job.get("location")
            job_url = job.get("jobUrl") or job.get("applyUrl") or ""
            raw_id = job.get("id") or job_url.rsplit("/", 1)[-1]
            out.append(Opportunity(id=f"ashby:{self.board}:{raw_id}",company=self.company,title=title,kind=kind,source=self.source_name,canonical_url=job_url,description=_strip_html(job.get("descriptionHtml") or job.get("description") or ""),location=location,remote=bool(job.get("isRemote")) or "remote" in (location or "").lower(),compensation=_compensation(job),metadata={"raw_id":raw_id}))
        return out
