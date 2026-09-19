# Scout Engine Scoring Contract

Scout separates **eligibility**, **fit**, **confidence** and **priority**. These signals are intentionally not collapsed into one magic score.

## 1. Hard eligibility gates

Hard gates run before fit scoring.

### Full-time compensation

A full-time role is eligible only when:

- base compensation is explicitly published by an official/public source,
- the salary is verified,
- a salary range's minimum is used,
- and the verified minimum is strictly **> ₹10 LPA**.

Non-INR compensation is converted to INR using a dated ECB reference-rate table. The original currency, amount, FX rate, date and source are retained.

This gate does not apply to internships, contracts or competitions.

### Seniority

Roles requiring more than 2 years are blocked unless the posting explicitly allows a new graduate, fresher, student, graduating candidate or 0–2 years equivalent.

### Research

Research-heavy roles are blocked when publications or a formal research record are materially expected and the candidate profile does not contain that evidence.

### Deadline / source status

Expired deadlines are blocked.

A posting disappearing from one successful scan is not enough to expire it. Two consecutive successful misses are required unless the official source explicitly indicates closure.

A failed source scan never counts as a miss.

## 2. Fit score: 0–10

Fit measures candidate ↔ role alignment only.

- technical overlap: **0–4**
- evidence for required skills: **0–2**
- seniority alignment: **0–2**
- logistics / location: **0–1**
- target-role direction: **0–1**

PPO/conversion does **not** increase fit.

Thresholds:

- normal surface: **6/10**
- high fit: **8/10+**
- verified deadline <5 days may use urgent floor **4/10**

## 3. Source confidence: 0–1

Confidence measures trust and completeness of the extracted record.

Typical extraction trust:

- official structured ATS/API: ~0.98
- official `JobPosting` JSON-LD: ~0.95
- official static career HTML: ~0.88
- browser-rendered official page: ~0.85
- heuristic HTML extraction: ~0.68

Final confidence blends source trust with field completeness. Full-time records are additionally penalized when verified compensation is absent, although the salary hard gate will normally reject them first.

## 4. Priority score: 0–10

Priority schedules human attention. It is **not** a probability of getting hired.

It combines:

- fit
- freshness
- verified deadline urgency
- a bounded bonus for internship conversion evidence

Explicit PPO/full-time-conversion evidence receives a larger priority bonus than merely likely conversion language.

## 5. Provenance rule

Important facts should retain their extraction source, for example:

```json
{
  "title": "ashby",
  "compensation": "jobposting_jsonld",
  "deadline_utc": "greenhouse",
  "posted_at_utc": "ashby"
}
```

Unknown data stays unknown. Scout must not fill policy-critical fields by guesswork.
