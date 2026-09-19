from scout_engine.models import Compensation, Opportunity, OpportunityKind
from scout_engine.policies import graduation_gate, research_gate, salary_gate, seniority_gate


def opp(**overrides):
    data = dict(id="x", company="Example", title="ML Engineer", kind=OpportunityKind.FULL_TIME, source="test", canonical_url="https://example.com/job")
    data.update(overrides)
    return Opportunity(**data)


def test_salary_range_minimum_must_exceed_threshold():
    o = opp(compensation=Compensation(currency="INR", min_annual=1_000_000, max_annual=1_800_000, verified=True))
    assert salary_gate(o, 10).passed is False


def test_salary_above_floor_passes():
    o = opp(compensation=Compensation(currency="INR", min_annual=1_100_000, verified=True))
    assert salary_gate(o, 10).passed is True


def test_foreign_verified_salary_passes_after_dated_conversion():
    o = opp(
        compensation=Compensation(
            currency="USD",
            min_annual=20_000,
            verified=True,
            converted_min_annual_inr=1_800_000,
            fx_rate=90,
            fx_rate_date="2026-09-18",
            fx_source="ECB",
        )
    )
    assert salary_gate(o, 10).passed is True


def test_internship_ignores_full_time_salary_gate():
    assert salary_gate(opp(kind=OpportunityKind.INTERNSHIP), 10).passed is True


def test_research_publication_gate_blocks_without_evidence():
    assert research_gate(opp(research_heavy=True, requires_publications=True), candidate_has_publications=False).passed is False


def test_seniority_gate_blocks_three_plus_years():
    assert seniority_gate(opp(experience_min=3)).passed is False


def test_seniority_gate_allows_explicit_new_grad_override():
    assert seniority_gate(opp(experience_min=3, description="New grad welcome; exceptional project experience accepted.")).passed is True


def test_explicit_graduation_year_mismatch_is_blocked():
    assert graduation_gate(opp(graduation_years=[2025, 2026]), 2027).passed is False


def test_explicit_2027_graduation_is_allowed():
    assert graduation_gate(opp(graduation_years=[2027]), 2027).passed is True
