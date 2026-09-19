from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from ..models import Compensation, Opportunity, OpportunityKind
from ..time_utils import to_utc_iso
from .html import find_jobposting_nodes


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value or ""))).strip()


def _location(node: dict[str, Any]) -> tuple[str | None, bool]:
    remote = str(node.get("jobLocationType") or "").upper() == "TELECOMMUTE"
    locations = node.get("jobLocation") or []
    if isinstance(locations, dict):
        locations = [locations]
    parts: list[str] = []
    for item in locations:
        if not isinstance(item, dict):
            continue
        address = item.get("address") or {}
        if isinstance(address, str):
            parts.append(address)
            continue
        if isinstance(address, dict):
            formatted = ", ".join(
                str(address.get(key))
                for key in ("addressLocality", "addressRegion", "addressCountry")
                if address.get(key)
            )
            if formatted:
                parts.append(formatted)
    return (", ".join(dict.fromkeys(parts)) or None, remote)


def _compensation(node: dict[str, Any]) -> Compensation | None:
    base = node.get("baseSalary")
    if not isinstance(base, dict):
        return None
    currency = str(base.get("currency") or "UNKNOWN").upper()
    value = base.get("value")
    if isinstance(value, (int, float)):
        lo = hi = float(value)
        unit = "year"
    elif isinstance(value, dict):
        lo = value.get("minValue", value.get("value"))
        hi = value.get("maxValue")
        unit = str(value.get("unitText") or "YEAR").lower()
        if not isinstance(lo, (int, float)):
            return None
        lo = float(lo)
        hi = float(hi) if isinstance(hi, (int, float)) else None
    else:
        return None
    period = "month" if "month" in unit else "year"
    return Compensation(
        currency=currency,
        min_annual=lo,
        max_annual=hi,
        period=period,
        verified=True,
        source="official JobPosting JSON-LD",
        verified_at=datetime.now(timezone.utc).isoformat(),
    )


def _kind(title: str, employment: str) -> OpportunityKind:
    lower = f"{title} {employment}".lower()
    if "intern" in lower:
        return OpportunityKind.INTERNSHIP
    if "contract" in lower or "temporary" in lower:
        return OpportunityKind.CONTRACT
    return OpportunityKind.FULL_TIME


def _stable_id(company: str, url: str, title: str) -> str:
    host = (urlsplit(url).hostname or "career").lower()
    digest = hashlib.sha1(f"{company}|{url}|{title}".encode("utf-8")).hexdigest()[:16]
    return f"career:{host}:{digest}"


def opportunities_from_jsonld(
    values: list[object],
    *,
    company: str,
    page_url: str,
    source_key: str,
) -> list[Opportunity]:
    out: list[Opportunity] = []
    for node in find_jobposting_nodes(values):
        title = str(node.get("title") or node.get("name") or "").strip()
        if not title:
            continue
        hiring = node.get("hiringOrganization") or {}
        company_name = str(hiring.get("name") or company) if isinstance(hiring, dict) else company
        url = str(node.get("url") or page_url)
        location, remote = _location(node)
        employment_raw = node.get("employmentType")
        if isinstance(employment_raw, list):
            employment = ", ".join(str(x) for x in employment_raw)
        else:
            employment = str(employment_raw or "")
        posted = node.get("datePosted")
        deadline = node.get("validThrough")
        try:
            posted = to_utc_iso(str(posted)) if posted else None
        except ValueError:
            posted = None
        try:
            deadline = to_utc_iso(str(deadline)) if deadline else None
        except ValueError:
            deadline = None
        comp = _compensation(node)
        provenance = {
            "title": "jobposting_jsonld",
            "description": "jobposting_jsonld",
            "location": "jobposting_jsonld",
            "employment_type_raw": "jobposting_jsonld",
        }
        if posted:
            provenance["posted_at_utc"] = "jobposting_jsonld"
        if deadline:
            provenance["deadline_utc"] = "jobposting_jsonld"
        if comp:
            provenance["compensation"] = "jobposting_jsonld"
        out.append(
            Opportunity(
                id=_stable_id(company_name, url, title),
                company=company_name,
                title=title,
                kind=_kind(title, employment),
                source="career_page",
                canonical_url=url,
                application_url=url,
                description=_plain(str(node.get("description") or "")),
                location=location,
                remote=remote,
                employment_type_raw=employment or None,
                workplace_type="remote" if remote else None,
                posted_at_utc=posted,
                deadline_utc=deadline,
                compensation=comp,
                source_status="open",
                extraction_method="jobposting_jsonld",
                source_confidence=0.95,
                field_provenance=provenance,
                last_http_status=200,
                metadata={"source_key": source_key},
            )
        )
    return out
