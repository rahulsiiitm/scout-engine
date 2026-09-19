from __future__ import annotations

from .base import SourceAdapter, get_json
from ..models import Opportunity, OpportunityKind


_RELEVANT_TITLE_TERMS = (
    "software",
    "engineer",
    "developer",
    "machine learning",
    "ml ",
    " ai ",
    "artificial intelligence",
    "backend",
    "platform",
    "infrastructure",
    "robot",
    "perception",
    "computer vision",
    "data scientist",
    "intern",
    "graduate",
    "sde",
)


def _relevant_title(title: str) -> bool:
    padded = f" {title.lower()} "
    return any(term in padded for term in _RELEVANT_TITLE_TERMS)


class SmartRecruitersAdapter(SourceAdapter):
    source_name = "smartrecruiters"

    def __init__(self, company: str, identifier: str, max_details: int = 60) -> None:
        self.company = company
        self.identifier = identifier
        self.max_details = max_details

    @property
    def source_key(self) -> str:
        return f"smartrecruiters:{self.identifier}"

    def fetch(self) -> list[Opportunity]:
        offset = 0
        candidates: list[dict] = []
        while True:
            page = get_json(
                f"https://api.smartrecruiters.com/v1/companies/{self.identifier}/postings"
                f"?limit=100&offset={offset}&destination=PUBLIC"
            )
            content = page.get("content", []) or []
            candidates.extend(job for job in content if _relevant_title(str(job.get("name") or "")))
            total = int(page.get("totalFound") or len(content))
            offset += len(content)
            if not content or offset >= total or offset >= 500:
                break

        out: list[Opportunity] = []
        for job in candidates[: self.max_details]:
            posting_id = job.get("id") or job.get("uuid")
            if not posting_id:
                continue
            details = get_json(
                f"https://api.smartrecruiters.com/v1/companies/{self.identifier}/postings/{posting_id}"
            )
            title = details.get("name") or job.get("name") or ""
            employment = str((details.get("typeOfEmployment") or {}).get("label") or "")
            kind = OpportunityKind.INTERNSHIP if "intern" in f"{title} {employment}".lower() else OpportunityKind.FULL_TIME
            loc = details.get("location") or job.get("location") or {}
            location = ", ".join(
                str(loc.get(k))
                for k in ("city", "region", "country")
                if loc.get(k)
            )
            sections = details.get("jobAd") or {}
            description = " ".join(
                str((sections.get(key) or {}).get("text") or "")
                for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation")
            ).strip()
            url = details.get("jobAdUrl") or details.get("applyUrl") or job.get("ref") or ""
            out.append(
                Opportunity(
                    id=f"smartrecruiters:{self.identifier}:{posting_id}",
                    company=self.company,
                    title=title,
                    kind=kind,
                    source=self.source_name,
                    canonical_url=url,
                    application_url=details.get("applyUrl") or url,
                    description=description,
                    location=location or None,
                    remote="remote" in location.lower() or "remote" in title.lower(),
                    employment_type_raw=employment or None,
                    source_status="open",
                    extraction_method="official_api",
                    source_confidence=0.97,
                    field_provenance={
                        "title": "smartrecruiters",
                        "description": "smartrecruiters",
                        "location": "smartrecruiters",
                    },
                    last_http_status=200,
                    metadata={"raw_id": posting_id, "source_key": self.source_key},
                )
            )
        return out
