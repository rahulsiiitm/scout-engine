# Scout Engine V3 Architecture

## Principle

GitHub Issues are the cockpit. `data/opportunities.json` is the database.

Discovery systems may change. Eligibility and lifecycle semantics should not.

## Data flow

```text
Company registry / ATS boards
            │
            ▼
       source selection
            │
     ┌──────┼─────────┐
     ▼      ▼         ▼
 ATS API  JSON-LD   career crawler
     │      │         │
     │      │    sitemap/static/browser
     └──────┴─────────┘
            ▼
       normalization
            ▼
        enrichment
      ┌─────┼─────┐
      ▼     ▼     ▼
 eligibility   FX   PPO
      └─────┼─────┘
            ▼
        hard gates
            ▼
      evidence match
            ▼
   fit / confidence / priority
            ▼
          dedupe
            ▼
      canonical history
            ▼
       GitHub lifecycle
```

## Source selection

`CareerPageAdapter` is not intended to beat structured ATS APIs.

It inspects the public employer career surface and, when it detects a supported ATS fingerprint, delegates to the native adapter:

- Greenhouse
- Lever
- Ashby
- Workable
- SmartRecruiters

If there is no supported structured source:

1. obey robots policy
2. inspect `JobPosting` JSON-LD
3. inspect same-site job/career links
4. inspect sitemap URLs
5. use static HTML heuristics
6. use Playwright only as a last fallback

## Crawler security boundary

Before every HTTP request and redirect, the URL is validated.

Allowed schemes:

- `https`
- `http`

Blocked:

- localhost
- private RFC1918 addresses
- loopback
- link-local
- multicast
- reserved/unspecified addresses
- credential-bearing URLs
- non-HTTP schemes

Responses and rendered HTML are size-capped.

The browser fallback applies the same public-network policy to subresource requests.

## robots.txt

A successful robots response is parsed with Python's robots parser.

- 2xx: obey policy
- 4xx: treat as no robots policy
- 5xx/network failure: fail closed for that company run

Crawler delays are honored with a conservative per-page cap.

## Conditional requests

Career landing pages retain:

- ETag
- Last-Modified
- last successful normalized opportunity set

A `304 Not Modified` restores that normalized set and refreshes verification time, preventing unchanged sources from being misclassified as missing.

## Provenance

`Opportunity.field_provenance` records where important values came from.

`source_confidence` describes extraction trust and is distinct from candidate fit.

## Foreign salary

`Compensation` keeps both original compensation and INR-converted values.

ECB daily reference rates are cached in `data/fx-rates.json`.

A conversion failure does not guess a rate. The normal full-time compensation gate then suppresses the opportunity.

## Stale postings

Stale handling is source-success aware.

```text
successful scan + seen
    -> open, miss counter = 0

successful scan + missing once
    -> possibly_closed

successful scan + missing twice
    -> closed
       pre-application stage -> expired
       applied/OA/interview history -> keep lifecycle, only source closes

failed source scan
    -> no stale-state mutation
```

This prevents infrastructure failures from rewriting career history.

## Extension contract

New ATS providers implement `SourceAdapter`.

New extractors produce normalized `Opportunity` objects.

Neither source adapters nor crawlers may make hiring-fit decisions. All policy decisions remain inside the engine/policies/scoring layers.
