import pytest

from scout_engine.models import Opportunity, OpportunityKind, Stage


def make():
    return Opportunity(id="x",company="Example",title="AI Intern",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com")


def test_valid_lifecycle():
    o = make(); o.transition(Stage.QUALIFIED); o.transition(Stage.APPLIED); o.transition(Stage.OA); o.transition(Stage.INTERVIEW)
    assert o.stage == Stage.INTERVIEW


def test_invalid_lifecycle_is_rejected():
    with pytest.raises(ValueError):
        make().transition(Stage.INTERVIEW)
