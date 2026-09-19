# Scout Engine V2 Architecture

Scout Engine is organized around one rule: **canonical state must be deterministic and auditable**.

```text
Sources
  │
  ▼
Normalization
  │
  ▼
Hard gates ──> Suppressions log
  │
  ▼
Evidence-backed fit scoring
  │
  ▼
Cross-source dedupe + history
  │
  ▼
Decision / lifecycle engine
  │
  ├──> GitHub Issues (human cockpit)
  ├──> Daily/weekly reports
  └──> Source and funnel analytics
```

## Canonical state

`data/opportunities.json` is the source of truth for opportunity history.

GitHub Issues are a user interface over that state, not the database. An issue may be closed while an application remains in the funnel, so reports must never count only open issues.

## Scores

Three independent signals are maintained:

- **Fit score (0–10):** evidence-backed match to the target profile.
- **Confidence (0–1):** completeness/reliability of the source data.
- **Priority (0–10):** action queue signal combining fit, freshness and deadline urgency.

Priority does not modify fit and is not a hiring-outcome prediction.

## Hard gates

Hard eligibility policies run before scoring:

1. full-time compensation,
2. seniority/new-grad eligibility,
3. research/publication expectations,
4. deadline validity.

A suppressed role is retained for auditability but never enters the active queue.

## Lifecycle

`discovered → qualified/reviewing → applied → OA → interview → offer → offer_accepted`

Terminal side paths: `rejected`, `withdrawn`, `expired`, `not_pursuing`.

Applying to a role does **not** close it automatically.

## Email signals

`email_signals.py` only proposes a lifecycle transition from message text. It does not modify state or send mail. Any future Gmail integration should keep the same proposal-before-mutation safety boundary.

## Preference learning

Preference weights are bounded tie-breakers for priority only. They never bypass hard gates, alter fit score, or interpret a rejection as personal dislike of a role category.

## Source adapters

The package includes structured adapters for Greenhouse, Lever and Ashby. Boards are explicitly configured in `config/boards.yaml` to avoid guessing board identifiers.
