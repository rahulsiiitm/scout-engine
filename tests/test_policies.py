from scout_engine.models import Compensation, Opportunity, OpportunityKind
from scout_engine.policies import candidate_stage_gate, graduation_gate, research_gate, role_alignment_gate, salary_gate, seniority_gate


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


def test_explicit_new_grad_autorejection_is_blocked():
    o = opp(
        title="Member of Technical Staff, Early Career",
        description="All applications from new grads and current students are being autorejected.",
    )
    result = candidate_stage_gate(o)
    assert result.passed is False


def test_generic_early_career_wording_is_not_blocked():
    assert candidate_stage_gate(opp(title="Software Engineer, Early Career")).passed is True


def test_procurement_contract_lead_is_not_an_engineering_role():
    result = role_alignment_gate(opp(title="Contract Management Lead (Procurement)", kind=OpportunityKind.CONTRACT))
    assert result.passed is False


def test_ip_licensing_intern_is_not_an_engineering_role():
    result = role_alignment_gate(opp(title="IP & Licensing - Intern", kind=OpportunityKind.INTERNSHIP))
    assert result.passed is False


def test_engineer_building_procurement_software_is_still_allowed():
    assert role_alignment_gate(opp(title="Software Engineer, Procurement Platform")).passed is True


def test_normal_ml_and_backend_roles_are_unchanged():
    assert role_alignment_gate(opp(title="ML Infrastructure Engineer")).passed is True
    assert role_alignment_gate(opp(title="Backend Developer - New Grad")).passed is True


def test_senior_title_not_overridden_by_generic_new_grads_in_description():
    role = opp(
        title="Senior Full-Stack Engineer, Internal Applications",
        description="Mentor new grads and help students grow into the team.",
        experience_min=6,
    )
    assert seniority_gate(role).passed is False


def test_early_career_role_with_explicit_grad_override_remains_allowed():
    role = opp(
        title="Software Engineer - Early Career",
        description="New graduates welcome.",
        experience_min=3,
    )
    assert seniority_gate(role).passed is True
