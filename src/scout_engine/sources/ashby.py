from __future__ import annotations

import html
import re

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


class AshbyAdapter(SourceAdapter):
    source_name = "ashby"

    def __init__(self, company: str, board: str) -> None:
        self.company = company
        self.board = board

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{self.board}")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            lower = title.lower()
            employment = str(job.get("employmentType") or "").lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in lower or "intern" in employment else OpportunityKind.FULL_TIME
            location = job.get("location")
            job_url = job.get("jobUrl") or job.get("applyUrl") or ""
            raw_id = job.get("id") or job_url.rsplit("/", 1)[-1]
            out.append(
                Opportunity(
                    id=f"ashby:{self.board}:{raw_id}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=job_url,
                    description=_strip_html(job.get("descriptionHtml") or job.get("description") or ""),
                    location=location,
                    remote=bool(job.get("isRemote")) or "remote" in (location or "").lower(),
                    metadata={"raw_id": raw_id},
                )
            )
        return out
