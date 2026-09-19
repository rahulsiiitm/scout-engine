from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from .ashby import AshbyAdapter
from .base import SourceAdapter, SourceError
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .smartrecruiters import SmartRecruitersAdapter
from .workable import WorkableAdapter
from ..crawl.browser import fetch_rendered_html
from ..crawl.cache import CrawlCache
from ..crawl.client import CrawlClient
from ..crawl.html import ParsedPage, parse_html_page
from ..crawl.jsonld import opportunities_from_jsonld
from ..crawl.robots import RobotsPolicy
from ..crawl.sitemap import parse_sitemap
from ..discovery.ats_fingerprint import AtsFingerprint, fingerprint_ats_links
from ..models import Opportunity, OpportunityKind


_JOB_HINTS = ("job", "jobs", "career", "careers", "opening", "openings", "position", "positions", "vacancy", "vacancies")


def _looks_job_url(url: str) -> bool:
    lower = url.lower()
    return any(f"/{hint}" in lower for hint in _JOB_HINTS)


def _same_host(a: str, b: str) -> bool:
    return (urlsplit(a).hostname or "").lower().removeprefix("www.") == (urlsplit(b).hostname or "").lower().removeprefix("www.")


def _heuristic_opportunity(company: str, source_key: str, url: str, page: ParsedPage) -> Opportunity | None:
    title = page.h1 or page.title
    title = title.split("|")[0].split("—")[0].strip()
    if not title or len(title) > 160 or not _looks_job_url(url):
        return None
    text = page.text[:25_000]
    lower = f"{title} {text[:1500]}".lower()
    if not any(token in lower for token in ("responsibil", "qualification", "requirements", "experience", "intern", "engineer", "developer")):
        return None
    kind = OpportunityKind.INTERNSHIP if "intern" in title.lower() else OpportunityKind.FULL_TIME
    digest = hashlib.sha1(f"{company}|{url}|{title}".encode()).hexdigest()[:16]
    return Opportunity(
        id=f"career:{(urlsplit(url).hostname or 'site').lower()}:{digest}",
        company=company,
        title=title,
        kind=kind,
        source="career_page",
        canonical_url=url,
        application_url=url,
        description=text,
        remote="remote" in lower,
        source_status="open",
        extraction_method="heuristic_html",
        source_confidence=0.68,
        field_provenance={"title": "official_career_html", "description": "official_career_html"},
        last_http_status=200,
        metadata={"source_key": source_key},
    )


class CareerPageAdapter(SourceAdapter):
    source_name = "career_page"

    def __init__(
        self,
        company: str,
        domain: str,
        *,
        careers_url: str | None = None,
        max_pages: int = 30,
        browser_fallback: bool = True,
        timeout_seconds: int = 20,
        user_agent: str = "ScoutEngineBot/1.0 (+https://github.com/rahulsiiitm/scout-engine)",
    ) -> None:
        self.company = company
        self.domain = domain
        self.careers_url = careers_url
        self.max_pages = max_pages
        self.browser_fallback = browser_fallback
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self._effective_keys: set[str] = {self.source_key}

    @property
    def source_key(self) -> str:
        return f"career:{self.domain.lower()}"

    def effective_source_keys(self) -> set[str]:
        return set(self._effective_keys)

    def _robots(self, client: CrawlClient, start_url: str) -> RobotsPolicy:
        parsed = urlsplit(start_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            result = client.fetch_text(robots_url)
        except Exception as exc:
            raise SourceError(f"{self.company}: robots.txt unavailable; fail closed: {exc}") from exc
        return RobotsPolicy.from_response(url=robots_url, status_code=result.status_code, text=result.text)

    def _delegate(self, fingerprint: AtsFingerprint) -> list[Opportunity]:
        mapping = {
            "greenhouse": GreenhouseAdapter(self.company, fingerprint.identifier),
            "lever": LeverAdapter(self.company, fingerprint.identifier),
            "ashby": AshbyAdapter(self.company, fingerprint.identifier),
            "workable": WorkableAdapter(self.company, fingerprint.identifier),
            "smartrecruiters": SmartRecruitersAdapter(self.company, fingerprint.identifier),
        }
        adapter = mapping[fingerprint.provider]
        self._effective_keys.add(adapter.source_key)
        items = adapter.fetch()
        for item in items:
            item.metadata["discovered_via"] = self.source_key
        return items

    def _process_page(self, url: str, html_text: str) -> tuple[list[Opportunity], ParsedPage]:
        page = parse_html_page(url, html_text)
        jobs = opportunities_from_jsonld(page.jsonld, company=self.company, page_url=url, source_key=self.source_key)
        return jobs, page

    def _rendered_detail_jobs(self, url: str) -> list[Opportunity]:
        """Render one job-detail URL and extract facts from that exact page.

        This deliberately never reuses the careers-index DOM for a different
        job URL. Browser fallback is expensive, so callers keep the candidate
        set small and only reach this method after static extraction failed.
        """
        rendered = fetch_rendered_html(url)
        structured, detail_page = self._process_page(url, rendered)
        if structured:
            return structured
        heuristic = _heuristic_opportunity(self.company, self.source_key, url, detail_page)
        return [heuristic] if heuristic else []

    def _candidate_links(self, page: ParsedPage, base_url: str) -> list[str]:
        same = [link for link in page.links if _same_host(link, base_url) and _looks_job_url(link)]
        return list(dict.fromkeys(same))[: self.max_pages]

    def _sitemap_urls(self, client: CrawlClient, policy: RobotsPolicy, start_url: str) -> list[str]:
        maps = policy.site_maps()
        if not maps:
            parsed = urlsplit(start_url)
            maps = [f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"]
        jobs: list[str] = []
        queue = list(dict.fromkeys(maps))[:3]
        visited: set[str] = set()
        while queue and len(jobs) < self.max_pages:
            sitemap_url = queue.pop(0)
            if sitemap_url in visited:
                continue
            visited.add(sitemap_url)
            if not policy.can_fetch(self.user_agent, sitemap_url):
                continue
            try:
                result = client.fetch_text(sitemap_url)
                if result.status_code >= 400:
                    continue
                parsed_map = parse_sitemap(result.text)
            except Exception:
                continue
            for nested in parsed_map.nested_sitemaps:
                if len(queue) < 10:
                    queue.append(nested.url)
            for entry in parsed_map.urls:
                if _same_host(entry.url, start_url) and _looks_job_url(entry.url):
                    jobs.append(entry.url)
                    if len(jobs) >= self.max_pages:
                        break
        return list(dict.fromkeys(jobs))

    def fetch(self) -> list[Opportunity]:
        start_url = self.careers_url or f"https://{self.domain}/"
        cache = CrawlCache()
        cached = cache.get(self.source_key)
        with CrawlClient(timeout_seconds=self.timeout_seconds, user_agent=self.user_agent) as client:
            policy = self._robots(client, start_url)
            if not policy.can_fetch(self.user_agent, start_url):
                raise SourceError(f"{self.company}: robots.txt disallows {start_url}")

            delay = policy.crawl_delay(self.user_agent)
            result = client.fetch_text(
                start_url,
                etag=cached.get("etag"),
                last_modified=cached.get("last_modified"),
            )
            if result.not_modified and cached.get("opportunities"):
                restored = [Opportunity.from_dict(item) for item in cached["opportunities"]]
                now = datetime.now(timezone.utc).isoformat()
                for item in restored:
                    item.last_seen_utc = now
                    item.last_verified_utc = now
                    item.last_http_status = 304
                return restored
            if result.status_code >= 400:
                raise SourceError(f"{self.company}: career page returned HTTP {result.status_code}")

            direct_fp = fingerprint_ats_links([result.url])
            if direct_fp:
                delegated = self._delegate(direct_fp[0])
                if delegated:
                    return delegated

            jobs, page = self._process_page(result.url, result.text)

            fingerprints = fingerprint_ats_links(page.links)
            if fingerprints:
                for fp in fingerprints:
                    try:
                        delegated = self._delegate(fp)
                    except Exception:
                        continue
                    if delegated:
                        return delegated

            links = self._candidate_links(page, result.url)
            if not self.careers_url and not jobs:
                likely_career = next((link for link in links if "career" in link.lower() or "/jobs" in link.lower()), None)
                if likely_career and likely_career != result.url and policy.can_fetch(self.user_agent, likely_career):
                    second = client.fetch_text(likely_career)
                    if second.status_code < 400:
                        jobs, page = self._process_page(second.url, second.text)
                        result = second
                        fingerprints = fingerprint_ats_links(page.links)
                        if fingerprints:
                            for fp in fingerprints:
                                try:
                                    delegated = self._delegate(fp)
                                except Exception:
                                    continue
                                if delegated:
                                    return delegated
                        links = self._candidate_links(page, second.url)

            if not links:
                links = self._sitemap_urls(client, policy, result.url)

            seen_urls: set[str] = {item.canonical_url for item in jobs}
            for link in links[: self.max_pages]:
                if link in seen_urls or not policy.can_fetch(self.user_agent, link):
                    continue
                if delay:
                    time.sleep(min(delay, 2.0))
                try:
                    detail = client.fetch_text(link)
                except Exception:
                    continue
                if detail.status_code >= 400:
                    continue
                structured, detail_page = self._process_page(detail.url, detail.text)
                if structured:
                    for item in structured:
                        if item.canonical_url not in seen_urls:
                            jobs.append(item)
                            seen_urls.add(item.canonical_url)
                    continue
                heuristic = _heuristic_opportunity(self.company, self.source_key, detail.url, detail_page)
                if heuristic and heuristic.canonical_url not in seen_urls:
                    jobs.append(heuristic)
                    seen_urls.add(heuristic.canonical_url)

            if not jobs and self.browser_fallback:
                try:
                    rendered = fetch_rendered_html(result.url)
                    structured, rendered_page = self._process_page(result.url, rendered)
                    jobs.extend(structured)

                    fingerprints = fingerprint_ats_links(rendered_page.links)
                    if not jobs and fingerprints:
                        for fp in fingerprints:
                            try:
                                delegated = self._delegate(fp)
                            except Exception:
                                continue
                            if delegated:
                                return delegated

                    if not jobs:
                        # Browser rendering is the final, expensive fallback.
                        # Render a small number of actual detail URLs, never the
                        # index page under a job URL.
                        browser_links = self._candidate_links(rendered_page, result.url)
                        for link in browser_links[: min(self.max_pages, 4)]:
                            if not policy.can_fetch(self.user_agent, link):
                                continue
                            try:
                                rendered_jobs = self._rendered_detail_jobs(link)
                            except Exception:
                                continue
                            for item in rendered_jobs:
                                if item.canonical_url not in seen_urls:
                                    jobs.append(item)
                                    seen_urls.add(item.canonical_url)
                            if jobs:
                                break
                except Exception:
                    pass

            now = datetime.now(timezone.utc).isoformat()
            for item in jobs:
                item.last_seen_utc = now
                item.last_verified_utc = now
                item.metadata.setdefault("source_key", self.source_key)
            cache.put(
                self.source_key,
                {
                    "etag": result.etag,
                    "last_modified": result.last_modified,
                    "checked_at": now,
                    "opportunities": [item.to_dict() for item in jobs],
                },
            )
            return jobs
