# Match Scoring

Scout Engine V2 separates **eligibility**, **fit**, **confidence**, and **priority**.

## 1. Hard eligibility gates

These run before scoring. A failure produces a suppression record rather than a surfaced issue.

- Full-time base compensation must be verifiably **> ₹10 LPA**.
- For ranges, the minimum must be above the threshold.
- Mid/senior roles are blocked unless they explicitly accept new grads / 0–2 years.
- Research-heavy roles that materially require publications are blocked when the candidate profile lacks that evidence.
- Expired opportunities are blocked.
- Unknown data is never guessed.

## 2. Fit score — 0–10

| Component | Points | Meaning |
| --- | ---: | --- |
| Technical overlap | 0–4 | Required stack matches strong/working skills |
| Evidence | 0–2 | Concrete candidate projects/internships support those requirements |
| Seniority / eligibility | 0–2 | New-grad/intern/0–2-year compatibility |
| Logistics | 0–1 | Location/remote/timing compatibility |
| Role direction | 0–1 | Alignment with target role families |

Standard surface threshold: **6/10**. High fit: **8/10+**.

## 3. Confidence — 0–1

Confidence measures source completeness, not candidate quality. Missing descriptions,
verification timestamps, location, deadline data, or full-time compensation reduce confidence.

## 4. Priority — 0–10

Priority schedules attention using:

- fit,
- posting freshness,
- deadline urgency.

It does not change the fit score and must not be described as a probability of getting hired.

## Evidence matching

Requirements are mapped to concrete candidate evidence in `config/profile.yaml`.
For example, `RAG` can be supported by the IIT Roorkee SUTRA work while
`computer_vision` can be supported by VidChain / AgriHive / visual-analysis work.

Missing evidence is surfaced explicitly instead of being silently treated as a match.
