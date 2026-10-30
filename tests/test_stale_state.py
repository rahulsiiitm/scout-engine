from scout_engine.models import Decision, Opportunity, OpportunityKind, Stage
from scout_engine.runner import _mark_source_disappearances


def make(stage=Stage.QUALIFIED):
    return Opportunity(
        id="x",
        company="Example",
        title="AI Engineer",
        kind=OpportunityKind.INTERNSHIP,
        source="career_page",
        canonical_url="https://example.com/jobs/x",
        stage=stage,
        decision=Decision.SURFACED,
        source_status="open",
        metadata={"source_key": "career:example.com"},
    )


def test_one_successful_miss_does_not_expire():
    item = make()
    _mark_source_disappearances(
        {"x": item},
        successful_keys={"career:example.com"},
        seen_by_key={"career:example.com": set()},
        miss_limit=2,
    )
    assert item.stage == Stage.QUALIFIED
    assert item.source_status == "possibly_closed"


def test_two_successful_misses_expire_pre_application_only():
    item = make()
    item.missing_successful_scans = 1
    _mark_source_disappearances(
        {"x": item},
        successful_keys={"career:example.com"},
        seen_by_key={"career:example.com": set()},
        miss_limit=2,
    )
    assert item.stage == Stage.EXPIRED
    assert item.decision == Decision.EXPIRED

    applied = make(Stage.APPLIED)
    applied.missing_successful_scans = 1
    _mark_source_disappearances(
        {"x": applied},
        successful_keys={"career:example.com"},
        seen_by_key={"career:example.com": set()},
        miss_limit=2,
    )
    assert applied.stage == Stage.APPLIED
    assert applied.source_status == "closed"


def test_failed_source_is_not_evidence_of_closure():
    item = make()
    _mark_source_disappearances(
        {"x": item},
        successful_keys=set(),
        seen_by_key={},
        miss_limit=2,
    )
    assert item.missing_successful_scans == 0
    assert item.stage == Stage.QUALIFIED


def test_closed_opportunity_stops_accumulating_stale_updates():
    item = make(Stage.EXPIRED)
    item.missing_successful_scans = 2
    item.source_status = "closed"
    for _ in range(3):
        count = _mark_source_disappearances(
            {"x": item},
            successful_keys={"career:example.com"},
            seen_by_key={"career:example.com": set()},
            miss_limit=2,
        )
        assert count == 0
        assert item.missing_successful_scans == 2
        assert item.stage == Stage.EXPIRED


def test_reconcile_stage_not_pursuing_also_suppresses_decision(monkeypatch):
    from scout_engine import runner

    item = make()
    item.issue_number = 99
    saved = []

    class FakeClient:
        @classmethod
        def from_env(cls):
            return cls()

        def list_issues(self, state="all"):
            return [{"number": 99, "labels": [{"name": "stage/not_pursuing"}]}]

    class FakeStore:
        def load(self):
            return [item]

        def save(self, items):
            saved.extend(items)

    monkeypatch.setenv("GITHUB_TOKEN", "test")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setattr(runner, "GitHubClient", FakeClient)
    monkeypatch.setattr(runner, "OpportunityStore", FakeStore)
    assert runner.reconcile_github_stage_labels() == 2
    assert item.stage == Stage.NOT_PURSUING
    assert item.decision == Decision.SUPPRESSED
    assert saved == [item]


def test_partial_career_page_cannot_prove_disappearance():
    from scout_engine.runner import _closure_evidence_keys
    from scout_engine.sources.career_page import CareerPageAdapter

    adapter = CareerPageAdapter("Example", "example.com", max_pages=2)
    existing = make()
    existing.missing_successful_scans = 1
    existing.source_status = "possibly_closed"

    # Seeing one job on a bounded crawl cannot prove that another is gone.
    assert _closure_evidence_keys(adapter, [make()]) == set()
    changed = _mark_source_disappearances(
        {"x": existing},
        successful_keys=_closure_evidence_keys(adapter, [make()]),
        seen_by_key={adapter.source_key: {"other"}},
        miss_limit=2,
    )
    assert changed == 0
    assert existing.missing_successful_scans == 1
    assert existing.stage == Stage.QUALIFIED


def test_delegated_ats_keeps_its_own_closure_evidence():
    from scout_engine.runner import _closure_evidence_keys
    from scout_engine.sources.career_page import CareerPageAdapter
    from scout_engine.sources.greenhouse import GreenhouseAdapter

    adapter = CareerPageAdapter("Example", "example.com")
    adapter._effective_keys.add("greenhouse:example")
    assert _closure_evidence_keys(adapter, [make()]) == {"greenhouse:example"}
    assert _closure_evidence_keys(GreenhouseAdapter("Example", "example"), []) == set()


def test_enrichment_failure_cannot_complete_a_source_scan(monkeypatch, tmp_path):
    from scout_engine import runner

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    old = make()
    old.metadata["source_key"] = "greenhouse:example"
    old.missing_successful_scans = 1
    old.source_status = "possibly_closed"

    good = make()
    good.id = "new"
    good.metadata["source_key"] = "greenhouse:example"
    good.decision = Decision.SUPPRESSED
    good.suppression_reason = "test suppression"
    broken = make()
    broken.id = "broken"
    broken.metadata["source_key"] = "greenhouse:example"

    class Adapter:
        source_name = "greenhouse"
        source_key = "greenhouse:example"

        def effective_source_keys(self):
            return {self.source_key}

        def fetch(self):
            return [good, broken]

    class Store:
        def load(self):
            return [old]

        def save(self, items):
            self.saved = items

    store = Store()
    monkeypatch.setattr(runner, "OpportunityStore", lambda: store)
    monkeypatch.setattr(runner, "configured_adapters", lambda: [Adapter()])
    monkeypatch.setattr(runner, "load_profile", lambda: {})
    monkeypatch.setattr(runner, "_engine_config", lambda: object())
    monkeypatch.setattr(runner, "load_yaml", lambda path: {"crawl": {"stale_after_successful_misses": 2}})
    monkeypatch.setattr(runner, "_write_scan_snapshot", lambda *args: None)
    monkeypatch.setattr(runner, "evaluate", lambda raw, **kwargs: raw)

    def enrich(raw):
        if raw.id == "broken":
            raise RuntimeError("detail enrichment failed")
        return raw

    monkeypatch.setattr(runner, "enrich_opportunity", enrich)
    result = runner.scan_structured_sources(sync_github=False)
    assert result["errors"] == 1
    assert result["stale_updates"] == 0
    assert old.missing_successful_scans == 1
    assert old.stage == Stage.QUALIFIED


def test_reopened_inferred_closure_restores_qualified_stage():
    from scout_engine.runner import _preserve_rediscovered_lifecycle

    old = make(Stage.EXPIRED)
    old.decision = Decision.EXPIRED
    old.source_status = "closed"
    old.missing_successful_scans = 2
    current = make(Stage.EXPIRED)
    _preserve_rediscovered_lifecycle(old, current, miss_limit=2)
    assert current.stage == Stage.QUALIFIED
    assert current.decision == Decision.SURFACED
    assert current.metadata["reopened_after_inferred_closure"] is True


def test_legacy_surfaced_expired_mismatch_is_repaired():
    from scout_engine.runner import _preserve_rediscovered_lifecycle

    old = make(Stage.EXPIRED)
    old.source_status = "open"
    old.decision = Decision.SURFACED
    current = make(Stage.EXPIRED)
    _preserve_rediscovered_lifecycle(old, current, miss_limit=2)
    assert current.stage == Stage.QUALIFIED


def test_manual_expiration_is_not_reopened_by_rediscovery():
    from scout_engine.runner import _preserve_rediscovered_lifecycle

    old = make(Stage.EXPIRED)
    old.source_status = "open"
    old.decision = Decision.EXPIRED
    current = make(Stage.EXPIRED)
    _preserve_rediscovered_lifecycle(old, current, miss_limit=2)
    assert current.stage == Stage.EXPIRED
    assert current.decision == Decision.EXPIRED


def test_manual_not_pursuing_is_not_resurfaced():
    from scout_engine.runner import _preserve_rediscovered_lifecycle

    old = make(Stage.NOT_PURSUING)
    old.decision = Decision.SUPPRESSED
    old.suppression_reason = "user chose not to pursue"
    current = make(Stage.NOT_PURSUING)
    _preserve_rediscovered_lifecycle(old, current, miss_limit=2)
    assert current.stage == Stage.NOT_PURSUING
    assert current.decision == Decision.SUPPRESSED
    assert current.suppression_reason == "user chose not to pursue"


def test_reopened_job_still_requires_hard_gate_success():
    from scout_engine.runner import _preserve_rediscovered_lifecycle

    old = make(Stage.EXPIRED)
    old.decision = Decision.EXPIRED
    old.source_status = "closed"
    old.missing_successful_scans = 2
    current = make(Stage.EXPIRED)
    current.decision = Decision.SUPPRESSED
    current.suppression_reason = "graduation year mismatch"
    _preserve_rediscovered_lifecycle(old, current, miss_limit=2)
    assert current.stage == Stage.EXPIRED
    assert current.decision == Decision.SUPPRESSED
    assert current.suppression_reason == "graduation year mismatch"
