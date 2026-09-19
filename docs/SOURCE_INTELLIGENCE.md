# Career Source Intelligence

## Why this layer exists

Scout Engine's original V2 architecture had strong filtering and lifecycle semantics but narrow native discovery coverage.

V3 solves that by making public employer careers infrastructure discoverable without turning the project into a generic internet spider.

## Rules

1. Prefer official/public structured data.
2. Crawl only employer-owned public career surfaces.
3. Do not authenticate.
4. Do not bypass access controls.
5. Do not infer policy-critical facts from reputation.
6. Preserve field provenance.
7. Do not expire roles because a source failed.
8. Browser automation is fallback, not default.

## Supported discovery modes

### Structured ATS

Best source. Native adapters normalize known fields directly.

### ATS fingerprint

Links from employer career pages are inspected for known hosted ATS patterns.

Detection does not imply scraping the hosted page. Supported providers are delegated to their API adapter.

### JobPosting JSON-LD

Official job-detail pages frequently expose Schema.org job data. V3 extracts title, organization, description, date posted, valid-through deadline, employment type, location, remote indicator, URL and structured base salary when present.

### Sitemap

robots-declared sitemaps are preferred. `/sitemap.xml` is tried conservatively if none is declared.

Only career/job-like same-site URLs are considered.

### Static HTML

Heuristic extraction is allowed only on official public career pages and gets lower source confidence. Unstructured salary text is deliberately not treated as verified compensation.

### Browser fallback

Playwright renders JavaScript-heavy career surfaces when static extraction found nothing useful.

The browser has no saved login state, and private-network/navigation checks remain active.

## Company registry

`config/companies.yaml` is deliberately small and curated.

The crawler does not recursively discover unrelated websites.

Adding another employer should normally require one registry entry, not code.

## Operational limits

Current defaults:

- 20 second request timeout
- 2 MB HTTP/rendered response cap
- 12 job-detail pages per company by default
- no repeated retry loop
- max 2 seconds honored crawl delay per detail request
- two successful missing scans before closure

These limits keep daily CI predictable.

## Confidence

Source confidence describes extraction quality, not candidate attractiveness.

An official ATS record may be very trustworthy and still score poorly for fit.

A heuristic HTML record may look attractive but remain too incomplete to pass a hard gate.

## PPO / conversion

Signals are:

- `explicit`: direct PPO, return-offer or full-time-conversion wording
- `likely`: wording suggests a post-internship employment path without making a direct promise
- `unknown`: no reliable conversion evidence

Only source text is used. Company reputation is not evidence.

## Maintenance philosophy

V3 is intended to be the architecture freeze.

Future source breakage should normally be repaired by:

- updating a career URL,
- adding/changing an ATS fingerprint,
- adding a small adapter,
- or adjusting an extractor fixture.

It should not require redesigning scoring, lifecycle or canonical state.
