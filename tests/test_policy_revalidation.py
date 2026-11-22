import pytest

from scout_engine.engine import EngineConfig
from scout_engine.models import Decision, Opportunity, OpportunityKind, Stage
from scout_engine.runner import _revalidate_active_policy


def _phd_role(*, stage=Stage.QUALIFIED, kind=OpportunityKind.INTERNSHIP):
    return Opportunity(
        id="career:example.com:phd-role",
        company="Example",
        title="Research Scientist Intern, Audio and Machine Learning (PhD)",
        kind=kind,
        source="career_page",
        canonical_url="https://example.com/jobs/phd-role",
        research_heavy=False,
        requires_publications=False,
        decision=Decision.SURFACED,
        stage=stage,
        source_status="open",
        missing_successful_scans=1,
        last_seen_utc="2026-11-14T08:00:00+00:00",
        last_verified_utc="2026-11-14T08:00:00+00:00",
    )


def test_active_phd_record_is_suppressed_without_changing_lifecycle_or_closure_state():
    role = _phd_role()
    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 1
    assert reasons["role title explicitly targets PhD/doctoral candidates"] == 1
    assert role.decision == Decision.SUPPRESSED
    assert role.suppression_reason == "role title explicitly targets PhD/doctoral candidates"
    assert role.stage == Stage.QUALIFIED
    assert role.source_status == "open"
    assert role.missing_successful_scans == 1
    assert role.last_seen_utc == "2026-11-14T08:00:00+00:00"
    assert role.last_verified_utc == "2026-11-14T08:00:00+00:00"


@pytest.mark.parametrize(
    "stage",
    [
        Stage.APPLIED,
        Stage.OA,
        Stage.INTERVIEW,
        Stage.OFFER,
        Stage.OFFER_ACCEPTED,
        Stage.REJECTED,
        Stage.WITHDRAWN,
        Stage.CLOSED,
        Stage.EXPIRED,
        Stage.NOT_PURSUING,
    ],
)
def test_policy_revalidation_preserves_terminal_and_user_funnel_stages(stage):
    role = _phd_role(stage=stage)
    original_decision = role.decision
    original_reason = role.suppression_reason
    original_misses = role.missing_successful_scans

    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 0
    assert newly_suppressed == 0
    assert not reasons
    assert role.stage == stage
    assert role.decision == original_decision
    assert role.suppression_reason == original_reason
    assert role.missing_successful_scans == original_misses


def test_ordinary_research_engineering_internship_is_not_blocked():
    role = _phd_role()
    role.title = "Research Engineer Intern, Machine Learning"
    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 0
    assert not reasons
    assert role.decision == Decision.SURFACED
    assert role.stage == Stage.QUALIFIED


def test_existing_non_hard_gate_suppression_is_not_automatically_reopened():
    role = _phd_role()
    role.title = "Backend Engineer Intern"
    role.decision = Decision.SUPPRESSED
    role.suppression_reason = "fit score 5.0 below 6.0"

    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 0
    assert not reasons
    assert role.decision == Decision.SUPPRESSED
    assert role.suppression_reason == "fit score 5.0 below 6.0"


def test_competitions_are_outside_career_policy_revalidation():
    role = _phd_role(kind=OpportunityKind.COMPETITION)
    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 0
    assert newly_suppressed == 0
    assert not reasons
    assert role.decision == Decision.SURFACED


def _legacy_cad_new_grad_role():
    # Shape of a v2 recovery record: verified compensation whose flag was lost
    # in migration but whose dated INR conversion survived.
    return Opportunity.from_dict({
        "id": "ashby:zip:b5242472-5679-4084-af77-238b6335b792",
        "company": "Zip",
        "title": "Zip — Software Engineer New Grad 2027",
        "kind": "full_time",
        "source": "ashby",
        "canonical_url": "https://jobs.ashbyhq.com/zip/b5242472-5679-4084-af77-238b6335b792",
        "location": "Toronto",
        "compensation": {
            "currency": "CAD",
            "min_annual": 121000,
            "max_annual": 126000,
            "period": "year",
            "verified": False,
            "converted_min_annual_inr": 8224000.0,
            "fx_rate": 67.97,
            "fx_rate_date": "2026-09-22",
            "fx_source": "ECB",
        },
        "fit_score": 8.4,
        "confidence_score": 0.98,
        "priority_score": 8.5,
        "decision": "surfaced",
        "stage": "qualified",
        "issue_number": 50,
        "metadata": {"state_schema_normalized_from": "v2_compact_recovery"},
    })


def test_migrated_record_with_dated_fx_evidence_is_not_suppressed_as_unverified():
    role = _legacy_cad_new_grad_role()
    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 0
    assert not reasons
    assert role.decision == Decision.SURFACED
    assert role.suppression_reason is None
    assert role.stage == Stage.QUALIFIED
    assert role.issue_number == 50


def test_stale_unverified_compensation_suppression_is_retired():
    role = _legacy_cad_new_grad_role()
    role.decision = Decision.SUPPRESSED
    role.suppression_reason = "full-time compensation is missing or unverified"

    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 0
    assert not reasons
    assert role.decision == Decision.SURFACED
    assert role.suppression_reason is None


def test_genuinely_unverified_full_time_record_stays_suppressed():
    role = _legacy_cad_new_grad_role()
    role.compensation.verified = False
    role.decision = Decision.SUPPRESSED
    role.suppression_reason = "full-time compensation is missing or unverified"

    checked, newly_suppressed, reasons = _revalidate_active_policy(
        {role.id: role}, {}, EngineConfig()
    )

    assert checked == 1
    assert newly_suppressed == 0
    assert role.decision == Decision.SUPPRESSED
    assert role.suppression_reason == "full-time compensation is missing or unverified"
