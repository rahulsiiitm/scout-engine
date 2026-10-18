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
