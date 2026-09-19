from __future__ import annotations

import html
import re

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


class GreenhouseAdapter(SourceAdapter):
    source_name = "greenhouse"

    def __init__(self, company: str, board: str) -> None:
        self.company = company
        self.board = board

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs?content=true")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title", "")
            lower = title.lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in lower else OpportunityKind.FULL_TIME
            location = (job.get("location") or {}).get("name")
            out.append(
                Opportunity(
                    id=f"greenhouse:{self.board}:{job['id']}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=job.get("absolute_url", ""),
                    description=_strip_html(job.get("content", "")),
                    location=location,
                    remote="remote" in (location or "").lower(),
                    metadata={"raw_id": job["id"]},
                )
            )
        return out
