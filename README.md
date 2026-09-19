# Scout Engine 🛰️

Personal opportunity intelligence infrastructure for high-signal jobs, internships, PPO/conversion paths and selected competitions.

Scout Engine V3 turns the repository into a small, auditable career-source intelligence system:

**discover → normalize → enrich → gate → evidence-match → dedupe → prioritize → track lifecycle → learn from the funnel**

## V3 architecture

Scout no longer depends on manually configured ATS boards alone.

For each tracked employer it now prefers the most structured public source available:

1. official/public ATS API
2. detected `JobPosting` JSON-LD
3. robots/sitemap-assisted static careers pages
4. static job-detail HTML
5. Playwright browser fallback only when required

If a career page points to Greenhouse, Lever, Ashby, Workable or SmartRecruiters, Scout promotes that source back into the structured adapter path rather than continuing to scrape HTML.

The crawler:

- obeys `robots.txt`
- fails closed when robots infrastructure is unavailable due server/network errors
- rejects private/local network targets and unsafe URL schemes
- caps response sizes and redirects
- never logs in, bypasses CAPTCHAs, rotates proxies, or crawls private portals
- uses conditional `ETag` / `Last-Modified` requests for cached career pages
- treats a failed source scan as **no evidence of closure**

## Candidate target

Machine-readable candidate strategy lives in [`config/profile.yaml`](config/profile.yaml).

Current daily career target:

- up to **10 new qualified career opportunities**
- roughly 5 new-grad/full-time + 5 internship/PPO/conversion when the market supports it
- never lower hard gates to fill the target
- competitions do not count toward the 10

## Source registry

[`config/companies.yaml`](config/companies.yaml) is the employer-owned careers registry.

[`config/boards.yaml`](config/boards.yaml) holds verified structured ATS identifiers.

A registry company may only need a domain. Scout can discover a career link, inspect ATS fingerprints, read public structured metadata and fall back to rendered HTML if necessary.

## Structured adapters

Native adapters:

- Greenhouse
- Lever
- Ashby
- Workable
- SmartRecruiters

The adapters now retain richer fields where available, including posting dates, workplace/employment type, application URLs and structured compensation.

## Canonical state

**`data/opportunities.json` is the source of truth.**

GitHub Issues are the human-facing cockpit. Issue open/closed state never replaces the canonical application lifecycle.

V3 state also retains:

- extraction method
- source confidence
- field-level provenance
- source open/closed status
- application URL
- PPO/full-time-conversion signal and evidence
- successful-miss counter for stale detection
- dated FX conversion metadata

## Foreign compensation

Verified non-INR base compensation is converted through the ECB daily reference-rate table while retaining the original amount and currency.

The full-time hard gate remains:

> verified minimum base compensation must be strictly greater than ₹10 LPA

If salary cannot be verified and converted safely, the full-time opportunity is not surfaced.

## Lifecycle

```text
discovered
   ↓
qualified ↔ reviewing
   ↓
applied
   ↓
OA
   ↓
interview
   ↓
offer
   ↓
offer_accepted
```

Terminal side paths: `rejected`, `withdrawn`, `expired`, `not_pursuing`.

Applying never closes an issue automatically.

A missing job is only expired after **two consecutive successful source scans** fail to see it. Source failures do not count. Applied/OA/interview history is never erased merely because the public posting closes.

## Matching policy

- standard surface threshold: **6/10**
- high fit: **8/10+**
- urgent exception floor: **4/10** only with a verified deadline within 5 days
- full-time compensation: verified base minimum **> ₹10 LPA**
- research-heavy roles requiring formal publications are blocked unless the profile contains that evidence
- mid/senior roles are blocked unless the posting explicitly accepts new-grad / 0–2 year candidates
- explicit PPO/conversion improves action priority, not evidence-based fit

See [`SCORING.md`](SCORING.md).

## Repository map

```text
src/scout_engine/
├── crawl/               safe HTTP/browser crawling primitives
├── discovery/           source registry + ATS fingerprinting
├── enrich/              eligibility, PPO signals, FX conversion
├── sources/             ATS + career-page adapters
├── engine.py            gate/score decision path
├── runner.py            daily orchestration + stale reconciliation
└── models.py            canonical data contracts

config/profile.yaml       candidate facts and constraints
config/sources.yaml       source policy + crawler limits
config/companies.yaml     employer-owned career registry
config/boards.yaml        verified ATS identifiers

data/opportunities.json   canonical opportunity history
data/crawl-cache.json     conditional-request cache
data/fx-rates.json        dated ECB rate cache
data/scan-stats.json      latest discovery diagnostics
daily/                    native daily scan snapshots
weekly/                   funnel reports
```

## Automation

- `tests.yml`: regression suite + canonical validation
- `scout-daily.yml`: **07:37 IST**, shifted away from top-of-hour GitHub Actions congestion
- `scout-weekly.yml`: weekly funnel refresh

Daily Actions install Chromium only for the browser fallback path.

## Local commands

```bash
python -m pip install -e ".[dev,browser]"
python -m playwright install chromium

pytest
scout-engine validate
scout-engine scan
scout-engine stats
scout-engine weekly
scout-engine daily
```

## Safety rails

- no auto-apply
- no auto-send outreach
- no authentication crawling
- no CAPTCHA/access-control bypass
- no proxy/stealth scraping
- no private-network requests
- no guessed salary, deadline, eligibility or PPO
- failed source scans cannot close jobs
- preference learning cannot bypass hard gates
- every important extracted field can retain provenance

Scout Engine should remain boring where boring is valuable: deterministic policy, explicit evidence, inspectable state, and small replaceable source adapters.
