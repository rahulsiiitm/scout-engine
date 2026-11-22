# Agent Summary — Issue #50 (Zip, Software Engineer New Grad 2027, Toronto)

## Root cause

Issue #50 tracks a `full_time` opportunity with a verified Ashby compensation range
(CA$121K–CA$126K, ≈₹82.24 LPA via ECB 2026-09-22). The canonical ledger had it as
`decision: surfaced` / `stage: qualified` — but as of the `chore: refresh scout state`
run on 2026-11-16 (`7e954fa`) it flipped to:

```
"decision": "suppressed",
"suppression_reason": "full-time compensation is missing or unverified"
```

Two things combined to cause that.

1. **The v2 → v3 migration silently dropped compensation verification.**
   `data/recovery-2026-09-24.json` and the compact v2 records it rebuilt stored
   compensation as e.g. `{"currency":"CAD","min":121000,"max":126000,
   "min_inr_lpa":82.24,"fx_date":"2026-09-22","fx_source":"ECB","cad_inr":67.97}` —
   there is no `verified` key in that schema. `Opportunity.from_dict` passes the
   normalized dict straight into `Compensation(**compensation)`, whose `verified`
   field defaults to `False`. So every migrated record came back as *unverified*
   even though its range came from an official ATS API.

2. **A later change made that latent defect fatal.** Commit `4c1691c`
   ("fix(state): revalidate active opportunities after hard-gate changes") added
   `_revalidate_active_policy`, which re-applies `apply_hard_gates` to active career
   records. `salary_gate` rejects any full-time role whose `compensation.verified`
   is falsy. The first run after that commit therefore suppressed **17** already-
   surfaced, genuinely-verified opportunities — issue #50 among them.

The decisive detail: `enrich_opportunity` only calls `convert_compensation_to_inr`
when `compensation.verified` is `True`. **A stored dated INR conversion can only
exist on compensation that passed verification.** All 17 suppressed records carry
`converted_min_annual_inr` + `fx_rate` + `fx_rate_date`, and all 17 are legacy
recovery records (`state_schema_normalized_from: v2_compact_recovery` or
`dedupe_only_recovery_stub: true`) that are never re-crawled — Zip is not in
`config/boards.yaml`, so no live scan could ever repair them.

The 3 records the same run suppressed as PhD-targeted are unaffected and stay
suppressed: they are live-crawled records (`source_status: open`,
`extraction_method` set) and that suppression is correct.

## Fix

Three small edits, 15 lines of source.

**`src/scout_engine/models.py`** — in the compensation-compatibility block of
`Opportunity.from_dict`, restore the flag the migration lost, reading the dated FX
conversion as what it is: proof of prior verification.

```python
if not compensation.get("verified") and compensation.get("fx_rate_date") and compensation.get("converted_min_annual_inr") is not None:
    compensation["verified"]=True;compensation["source"]=compensation.get("source") or "migrated dated FX conversion evidence"
```

Provenance is recorded rather than silently flipped, so a restored record reads
`CAD 121,000–126,000 (migrated dated FX conversion evidence)` in its issue body
instead of the generic `(verified source)`.

**`src/scout_engine/policies.py`** — lifted the gate reason into
`UNVERIFIED_COMPENSATION_REASON` so it can be referenced rather than re-typed.
No behavior change.

**`src/scout_engine/runner.py`** — the migration repair alone is not enough: the
17 records are *already* `suppressed` on disk, and `_revalidate_active_policy`
deliberately never unsuppresses. Narrowed that rule by exactly one case — a record
whose stored reason is `UNVERIFIED_COMPENSATION_REASON` and which now passes every
hard gate. Scoring-based suppressions carry their own distinct reasons
(`"fit score … below …"`, `"source confidence … below …"`), so that string can only
have come from this gate, and keeping it after the evidence is readable again is a
stale verdict. Every other gate and every scoring suppression still stick.

## Verification

Full suite: **140 passed** (`python -m pytest -q`). 136 before, 4 added.

Added regression tests — confirmed to fail on the pre-fix code (3 of 4; the other
two are guard tests that must pass in both directions):

- `tests/test_models.py::test_legacy_dated_fx_conversion_restores_lost_verification_flag` — the issue-#50 record shape round-trips to `verified=True`, ₹82.24 LPA.
- `tests/test_models.py::test_unconverted_compensation_is_never_promoted_to_verified` — **guard**: compensation with no FX conversion is never promoted.
- `tests/test_policy_revalidation.py::test_migrated_record_with_dated_fx_evidence_is_not_suppressed_as_unverified`
- `tests/test_policy_revalidation.py::test_stale_unverified_compensation_suppression_is_retired`
- `tests/test_policy_revalidation.py::test_genuinely_unverified_full_time_record_stays_suppressed` — **guard**: a record with no FX evidence stays suppressed.

The pre-existing `test_existing_non_hard_gate_suppression_is_not_automatically_reopened`
(fit-score suppression must survive revalidation) still passes.

End-to-end against the real 2,438-record ledger:

```
$ python -c "...load store, run _revalidate_active_policy..."
checked: 1533   newly suppressed: 0   reasons: {}
records changed by revalidation: 17   (all suppressed -> surfaced)
Zip #50: surfaced None qualified | verified: True | LPA: 82.24
```

Exactly the 17 wrongly-suppressed records are restored, every other record is
untouched, and nothing new is suppressed.

## Concerns for a reviewer

- **`data/opportunities.json` is intentionally not edited.** It is bot-generated
  state; the next `scan_structured_sources` run loads, repairs and re-saves the 17
  records. If you want the ledger corrected immediately, run a scan — don't
  hand-edit it.
- **The `runner.py` change narrows a deliberate rule.** The docstring said a passing
  gate never unsuppresses, because fit/confidence may have been the real blocker.
  That reasoning holds for every suppression whose reason came from scoring; it does
  not hold when the stored reason is verbatim the compensation gate's. I updated the
  docstring to state the exception and its justification. If you'd rather not relax
  it at all, drop that hunk — the `models.py` fix alone stops the bleeding for all
  future records, but leaves the 17 existing ones suppressed forever.
- **Breadth of the restore.** The repair is keyed on a self-contradictory state
  (dated FX conversion present, `verified` false) that is unreachable through the
  live pipeline. I audited all 2,438 records: 17 match, all legacy recovery records,
  all suppressed/qualified. No live-crawled record matches.
- **Line endings.** The working tree arrived with CRLF while the repo index is LF,
  so `git status` showed ~45 unrelated files as fully modified. I committed only the
  5 files I actually changed, normalized back to LF, so the commit is a clean
  113-line content diff. `git add -A` (as the task text suggested) would have swept
  in the whitespace churn plus `BOUNTY_TASK.md`; those are left in the working tree.
