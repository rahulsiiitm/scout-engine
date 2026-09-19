from datetime import datetime, timedelta, timezone

from scout_engine.engine import EngineConfig, evaluate
from scout_engine.models import Opportunity, OpportunityKind


PROFILE = {
    "skills": {"strong": [], "working": []},
    "evidence": {},
    "roles": {"primary": [], "secondary": []},
    "locations": {"preferred": ["Remote"]},
}


def test_urgent_exception_uses_lower_fit_floor():
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    o = Opportunity(
        id="urgent",
        company="Example",
        title="Student AI Challenge",
        kind=OpportunityKind.HACKATHON,
        source="test",
        canonical_url="https://example.com",
        description="General student challenge",
        location="Remote",
        remote=True,
        deadline_utc=(now + timedelta(days=2)).isoformat(),
        last_verified_utc=now.isoformat(),
    )
    result = evaluate(
        o,
        profile=PROFILE,
        existing=[],
        config=EngineConfig(minimum_score=6, urgent_score_floor=4, confidence_floor=0.5),
        now=now,
    )
    assert result.decision.value == "surfaced"
    assert result.metadata["urgent"] is True
