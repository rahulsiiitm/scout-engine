from __future__ import annotations

import html
import re

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


class LeverAdapter(SourceAdapter):
    source_name = "lever"

    def __init__(self, company: str, site: str) -> None:
        self.company = company
        self.site = site

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://api.lever.co/v0/postings/{self.site}?mode=json")
        out: list[Opportunity] = []
        for job in data:
            title = job.get("text", "")
            lower = title.lower()
            commitment = ((job.get("categories") or {}).get("commitment") or "").lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in lower or "intern" in commitment else OpportunityKind.FULL_TIME
            location = (job.get("categories") or {}).get("location")
            description = " ".join(
                [
                    _strip_html(job.get("descriptionPlain") or job.get("description", "")),
                    " ".join(_strip_html(x.get("content", "")) for x in (job.get("lists") or [])),
                ]
            ).strip()
            out.append(
                Opportunity(
                    id=f"lever:{self.site}:{job['id']}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=job.get("hostedUrl") or job.get("applyUrl") or "",
                    description=description,
                    location=location,
                    remote="remote" in (location or "").lower(),
                    metadata={"raw_id": job["id"]},
                )
            )
        return out
