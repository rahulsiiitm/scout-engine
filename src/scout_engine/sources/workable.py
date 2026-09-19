from __future__ import annotations

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


class WorkableAdapter(SourceAdapter):
    """Read the public Workable account feed."""

    source_name = "workable"

    def __init__(self, company: str, subdomain: str) -> None:
        self.company = company
        self.subdomain = subdomain

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://www.workable.com/api/accounts/{self.subdomain}")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title") or job.get("full_title") or ""
            lower = title.lower()
            kind = OpportunityKind.INTERNSHIP if "intern" in lower else OpportunityKind.FULL_TIME
            location_parts = [job.get("city"), job.get("state"), job.get("country")]
            location = ", ".join(x for x in location_parts if x)
            url = job.get("url") or job.get("shortlink") or job.get("application_url") or ""
            shortcode = job.get("shortcode") or job.get("code") or url.rsplit("/", 1)[-1]
            out.append(
                Opportunity(
                    id=f"workable:{self.subdomain}:{shortcode}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=url,
                    description=str(job.get("description") or ""),
                    location=location or None,
                    remote="remote" in location.lower() or "remote" in lower,
                    metadata={"raw_id": shortcode},
                )
            )
        return out
