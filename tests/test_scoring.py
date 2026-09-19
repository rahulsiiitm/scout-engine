from scout_engine.models import Opportunity, OpportunityKind
from scout_engine.scoring import confidence_score, evidence_match, fit_score, priority_score

PROFILE={"skills":{"strong":["python","fastapi","rag"],"working":["docker"]},"evidence":{"python":["production pipeline"],"fastapi":["API backend"],"rag":["knowledge assistant"]},"roles":{"primary":["applied_ai","backend_engineer"],"secondary":[]},"locations":{"preferred":["India","Remote"]}}

def test_evidence_backed_match():
    o=Opportunity(id="x",company="Example",title="Applied AI Engineer",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com",description="Build Python FastAPI RAG services with Docker.",location="Remote - India",remote=True,last_verified_utc="2026-09-19T00:00:00+00:00",source_confidence=0.95)
    evidence,missing=evidence_match(o,PROFILE)
    assert {"python","fastapi","rag"} <= set(evidence)
    assert "docker" in missing
    assert fit_score(o,PROFILE)>=8
    assert confidence_score(o)>=0.75


def test_explicit_conversion_increases_priority_not_fit():
    base=Opportunity(id="a",company="Example",title="AI Intern",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com/a",description="Python",remote=True)
    ppo=Opportunity(id="b",company="Example",title="AI Intern",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com/b",description="Python",remote=True,conversion_signal="explicit")
    base.fit_score=ppo.fit_score=7
    assert priority_score(ppo) > priority_score(base)
