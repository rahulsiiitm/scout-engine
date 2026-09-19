from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True, slots=True)
class AtsFingerprint:
    provider: str
    identifier: str
    url: str


def fingerprint_ats_url(url: str) -> AtsFingerprint | None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return None

    if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        return AtsFingerprint("greenhouse", parts[0], url)
    if host in {"jobs.lever.co", "jobs.eu.lever.co"}:
        return AtsFingerprint("lever", parts[0], url)
    if host == "jobs.ashbyhq.com":
        return AtsFingerprint("ashby", parts[0], url)
    if host in {"apply.workable.com", "www.workable.com"} and parts:
        return AtsFingerprint("workable", parts[0], url)
    if host == "careers.smartrecruiters.com":
        return AtsFingerprint("smartrecruiters", parts[0], url)
    return None


def fingerprint_ats_links(links: list[str]) -> list[AtsFingerprint]:
    out: list[AtsFingerprint] = []
    seen: set[tuple[str, str]] = set()
    for link in links:
        item = fingerprint_ats_url(link)
        if item and (item.provider, item.identifier) not in seen:
            seen.add((item.provider, item.identifier))
            out.append(item)
    return out
