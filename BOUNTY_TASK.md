# Bounty Fix

**Reward:** $121.00
**Issue:** https://github.com/rahulsiiitm/scout-engine/issues/50
**Repo:** https://github.com/rahulsiiitm/scout-engine

---

## Issue

[Fit 8.4/10] Zip – Software Engineer New Grad 2027 – Toronto

**Type:** Full-time · New Grad 2027
**Source:** https://jobs.ashbyhq.com/zip/b5242472-5679-4084-af77-238b6335b792
**Verified open:** 2026-09-23
**Compensation:** CA$121K–CA$126K base. Minimum ≈ ₹82.4 LPA using ECB 2026-09-22 EUR/INR 109.58 and EUR/CAD 1.6122 (≈₹67.97/CAD).
**Eligibility:** Graduating Dec 2026–Jun 2027; Toronto hybrid; relocation assistance may be available.

**Fit:** Python/API/product engineering plus prior high-growth startup experience match well.
**Evidence matches:** Python, FastAPI/API development, AI products, startup internship, backend ownership.
**Missing / weaker:** React/TypeScript/GraphQL depth; Canada work authorization not stated.
**Confidence:** 0.98 · **Priority:** 8.5/10

**Status**
- [ ] Applied
- [x] Not Applied
- [ ] Rejected
- [ ] Interview

---

## Process

### 1. Orient yourself first
Before touching any code:
- Read the README and any relevant docs
- Run: find . -type f | grep -v node_modules | grep -v .git | grep -v dist | head -60
- Grep for the key terms from the issue title to find the relevant files
- Read the files around the bug — understand what's currently happening

### 2. Find and read the tests
- Look for test files near the relevant code (*.test.ts, *.spec.js, __tests__, etc.)
- Read them — they tell you what behavior is expected
- Understand what a passing fix looks like before writing a line

### 3. Implement the fix
- Make the MINIMAL change that fixes the issue — nothing more
- Do not refactor, rename, reorganize, or clean up unrelated code
- Do not add dependencies unless the issue explicitly requires it
- Do not modify config files (package.json, tsconfig.json, etc.) unless that IS the fix
- One logical change, one commit

### 4. Verify
- Run the test suite: check package.json scripts for "test", "lint", "typecheck"
  Common commands: npm test, yarn test, pnpm test, pytest, go test ./..., cargo test
- If TypeScript is present: npx tsc --noEmit
- Fix any test failures your change caused — if a test was wrong before, update it

### 5. Commit and document
- git add -A
- git commit -m "fix: [Fit 8.4/10] Zip – Software Engineer New Grad 2027 – Toronto"
- Write AGENT_SUMMARY.md with:
  - Root cause: what was wrong and why
  - Fix: what you changed and the reasoning
  - Verification: how to confirm it works
  - Concerns: anything a reviewer should know

---

## Stop conditions

If ANY of these are true, write "UNCERTAIN: [reason]" at the top of AGENT_SUMMARY.md, make NO code changes, and stop:
- The fix requires changing more than ~5 files
- You cannot determine what the correct behavior should be
- The issue requires a database migration, API key, or external service
- You find 3+ open PRs already attempting this fix (high competition)
- The repo is not in a language/framework you can reason about confidently

A clean UNCERTAIN is better than a bad PR.
