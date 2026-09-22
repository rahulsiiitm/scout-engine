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
