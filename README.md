# scout-engine 🛰️

Autonomous opportunity radar for AI/ML, backend, robotics/perception, and SDE roles.

The scout runs daily at **07:30 IST**, checks high-signal job and competition sources, scores each opportunity against the target profile, deduplicates previously seen postings, and writes qualified matches to GitHub Issues.

## Target profile

- Final-year B.Tech, AI & Data Science, IIIT Manipur
- Python, FastAPI, PyTorch, LLM orchestration/RAG, Docker, Qdrant, ROS, C++, Flutter
- Applied AI experience at Magic Hour (YC W24) and IIT Roorkee Academic Affairs
- Roles: ML/AI Engineer, Applied AI, Backend Engineer, Robotics/Perception Engineer, SDE-1
- Open to 2027-compatible full-time roles, internships, and contract/freelance AI work

## Matching policy

- Exact stack match > adjacent technology > generic AI/ML mention
- Surface **score >= 6/10**
- Also surface **score >= 4/10** when a verified deadline is under 5 days away
- New-grad/intern roles have no experience penalty
- Mid/senior roles are skipped unless they explicitly accept 0–2 years or new grads
- Closed or stale postings are excluded when closure can be verified

## Labels

| Label | Meaning |
| --- | --- |
| `job` | Job, internship, or contract |
| `hackathon` | Hackathon or competition |
| `urgent` | Verified deadline in fewer than 5 days |
| `high-fit` | Match score >= 8/10 |

## State

- `tracked-companies.md` — fixed targets and monthly startup refresh
- `seen-postings.json` — lean dedupe state using stable IDs/URLs
- `run-log.md` — source failures and material run warnings
- `config/sources.yaml` — source order and scan policy
- `config/labels.yml` — desired GitHub label taxonomy
- `daily/` — daily scan snapshots
- `weekly/` — application-funnel rollups
- GitHub Issues — actionable opportunities
- **📡 Digest — Daily Scout Summary** — running daily summary thread

## Application state

Every opportunity issue starts with:

- [ ] Applied
- [x] Not Applied
- [ ] Rejected
- [ ] Interview

The weekly report uses those issue states to calculate the funnel.

## Safety rails

The scout does **not** auto-apply and does **not** auto-send outreach. For high-fit roles it may draft a three-line outreach note as an issue comment for manual review.

## Schedule

**07:30 IST every day.**
