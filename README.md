# scout-engine 🛰️

Personal opportunity intelligence infrastructure for AI/ML, backend, robotics/perception, SDE roles, internships and high-signal competitions.

Scout Engine V2 is designed around an auditable pipeline:

**discover → normalize → gate → evidence-match → dedupe → prioritize → track lifecycle → learn from the funnel**

## What changed in V2

- real Python package under `src/scout_engine/`
- canonical opportunity history in `data/opportunities.json`
- lifecycle state machine instead of fragile issue checkboxes alone
- hard policy gates separated from fit scoring
- evidence-backed JD ↔ profile matching
- independent fit, confidence and action-priority signals
- cross-source fuzzy deduplication
- timezone-safe deadline normalization
- source analytics and bounded preference learning
- safe email-stage proposal parser
- Greenhouse, Lever and Ashby structured adapters
- GitHub Actions for tests, daily maintenance and weekly funnel reports
- regression tests for salary, seniority, research, deadlines, lifecycle, dedupe and scoring

## Target profile

The machine-readable profile lives in [`config/profile.yaml`](config/profile.yaml).
It contains only career-relevant information required by the matcher.

## Canonical state

**`data/opportunities.json` is the source of truth.**

GitHub Issues are the cockpit. They can be opened/closed for workflow convenience without
destroying application history. Reports are generated from canonical state, not inferred
from the set of currently open issues.

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

Applying does **not** automatically close an issue.

## Matching policy

- standard surface threshold: **6/10**
- high fit: **8/10+**
- full-time compensation: verified base pay must be **> ₹10 LPA**
- no guessing missing deadlines, compensation or eligibility
- research-heavy roles requiring publications are blocked unless the profile has that evidence
- mid/senior roles are blocked unless they explicitly accept new grads / 0–2 years

See [`SCORING.md`](SCORING.md).

## Repository map

```text
src/scout_engine/        engine, policies, scoring, lifecycle, adapters
config/profile.yaml      candidate facts and evidence
config/sources.yaml      policy + source configuration
config/boards.yaml       explicitly enabled ATS boards
data/opportunities.json  canonical opportunity history
data/source-stats.json   source yield telemetry
data/preferences.json    bounded ranking nudges
daily/                   daily snapshots
weekly/                  generated funnel reports
docs/ARCHITECTURE.md     system design
tests/                   regression suite
```

## Automation

- `tests.yml`: unit tests + canonical-state validation
- `scout-daily.yml`: **07:30 IST** daily maintenance
- `scout-weekly.yml`: weekly funnel refresh

The repo does **not** auto-apply or auto-send outreach.

## Local commands

```bash
python -m pip install -e ".[dev]"
pytest
scout-engine validate
scout-engine stats
scout-engine weekly
```

## Safety rails

- no auto-apply
- no auto-send outreach
- email parsing proposes stages only
- preference learning cannot bypass hard gates
- suppression reasons are retained for auditability
- unknown source fields stay unknown rather than being fabricated
