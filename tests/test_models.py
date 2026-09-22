import pytest

from scout_engine.models import Decision, Opportunity, OpportunityKind, Stage


def make():
    return Opportunity(id="x",company="Example",title="AI Intern",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com")


def test_valid_lifecycle():
    o = make(); o.transition(Stage.QUALIFIED); o.transition(Stage.APPLIED); o.transition(Stage.OA); o.transition(Stage.INTERVIEW)
    assert o.stage == Stage.INTERVIEW


def test_invalid_lifecycle_is_rejected():
    with pytest.raises(ValueError):
        make().transition(Stage.INTERVIEW)


def test_compact_recovery_title_supplies_missing_company():
    o = Opportunity.from_dict({
        "stable_id": "amazon:10496769",
        "issue": 36,
        "stage": "qualified",
        "title": "Amazon — Data Engineer Intern 2027",
        "kind": "internship",
    })
    assert o.company == "Amazon"
    assert o.id == "amazon:10496769"
    assert o.issue_number == 36
    assert o.decision == Decision.SURFACED
    assert o.metadata["state_schema_normalized_from"] == "v2_compact_recovery"


def test_compact_recovery_accepts_full_historical_shape():
    o = Opportunity.from_dict({
        "stable_id": "legacy:42",
        "issue": 42,
        "status": "open",
        "stage": "qualified",
        "title": "Example — ML Intern",
        "kind": "internship",
        "fit": 8.0,
        "confidence": 0.9,
        "priority": 8.5,
        "conversion": "explicit",
        "verified_at": "2026-09-22T00:00:00+00:00",
        "verified_open": True,
        "evidence_matches": ["Python"],
    })
    assert o.company == "Example"
    assert o.decision == Decision.SURFACED
    assert o.metadata["verified_open"] is True


def test_monthly_compensation_recovery_is_backward_compatible():
    o = Opportunity.from_dict({
        "id": "x",
        "company": "Example",
        "title": "Intern",
        "kind": "internship",
        "source": "test",
        "canonical_url": "https://example.com/jobs/x",
        "compensation": {"currency": "INR", "min_monthly": 100000, "max_monthly": 120000, "verified": True},
    })
    assert o.compensation.period == "month"
    assert o.compensation.min_lpa_inr == 12
