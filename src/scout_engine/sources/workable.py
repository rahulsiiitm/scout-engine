from __future__ import annotations

import html
import re

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


class WorkableAdapter(SourceAdapter):
    source_name = "workable"

    def __init__(self, company: str, subdomain: str) -> None:
        self.company = company
        self.subdomain = subdomain

    @property
    def source_key(self) -> str:
        return f"workable:{self.subdomain}"

    def fetch(self) -> list[Opportunity]:
        data = get_json(f"https://www.workable.com/api/accounts/{self.subdomain}?details=true")
        out: list[Opportunity] = []
        for job in data.get("jobs", []):
            title = job.get("title") or job.get("full_title") or ""
            employment = str(job.get("employment_type") or job.get("type") or "")
            lower = f"{title} {employment}".lower()
            if "intern" in lower:
                kind = OpportunityKind.INTERNSHIP
            elif "contract" in lower or "temporary" in lower:
                kind = OpportunityKind.CONTRACT
            else:
                kind = OpportunityKind.FULL_TIME
            location_parts = [job.get("city"), job.get("state"), job.get("country")]
            location = ", ".join(x for x in location_parts if x)
            url = job.get("url") or job.get("shortlink") or job.get("application_url") or ""
            shortcode = job.get("shortcode") or job.get("code") or url.rsplit("/", 1)[-1]
            workplace = job.get("workplace_type") or job.get("remote")
            out.append(
                Opportunity(
                    id=f"workable:{self.subdomain}:{shortcode}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=url,
                    application_url=job.get("application_url") or url,
                    description=_strip_html(str(job.get("description") or job.get("full_description") or "")),
                    location=location or None,
                    remote=bool(job.get("remote")) or "remote" in location.lower() or "remote" in lower,
                    employment_type_raw=employment or None,
                    workplace_type=str(workplace) if workplace is not None else None,
                    source_status="open",
                    extraction_method="official_api",
                    source_confidence=0.97,
                    field_provenance={"title": "workable", "location": "workable", "description": "workable"},
                    last_http_status=200,
                    metadata={"raw_id": shortcode, "source_key": self.source_key},
                )
            )
        return out
