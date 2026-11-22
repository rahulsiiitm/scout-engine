import pytest

from scout_engine.models import Decision, Opportunity, OpportunityKind, Stage


def make():
    return Opportunity(id="x",company="Example",title="AI Intern",kind=OpportunityKind.INTERNSHIP,source="test",canonical_url="https://example.com")


def test_valid_lifecycle():
    o = make(); o.transition(Stage.QUALIFIED); o.transition(Stage.APPLIED); o.transition(Stage.OA); o.transition(Stage.INTERVIEW)
    assert o.stage == Stage.INTERVIEW


def test_invalid_lifecycle_is_rejected():
    with pytest.raises(ValueError): make().transition(Stage.INTERVIEW)


def test_compact_recovery_title_supplies_missing_company():
    o = Opportunity.from_dict({"stable_id":"amazon:10496769","issue":36,"stage":"qualified","title":"Amazon — Data Engineer Intern 2027","kind":"internship"})
    assert o.company == "Amazon"; assert o.id == "amazon:10496769"; assert o.issue_number == 36; assert o.decision == Decision.SURFACED


def test_compact_recovery_accepts_full_historical_shape():
    o = Opportunity.from_dict({"stable_id":"legacy:42","issue":42,"status":"open","stage":"qualified","title":"Example — ML Intern","kind":"internship","fit":8.0,"confidence":0.9,"priority":8.5,"conversion":"explicit","verified_at":"2026-09-22T00:00:00+00:00","verified_open":True,"evidence_matches":["Python"]})
    assert o.company == "Example"; assert o.decision == Decision.SURFACED; assert o.metadata["verified_open"] is True


def test_monthly_compensation_recovery_is_backward_compatible():
    o = Opportunity.from_dict({"id":"x","company":"Example","title":"Intern","kind":"internship","source":"test","canonical_url":"https://example.com/jobs/x","compensation":{"currency":"INR","min_monthly":100000,"max_monthly":120000,"verified":True}})
    assert o.compensation.period == "month"; assert o.compensation.min_lpa_inr == 12


def test_compact_daily_salary_and_source_url_recovery():
    o = Opportunity.from_dict({"stable_id":"ashby:example:42","issue":42,"stage":"qualified","title":"Example — Software Engineer New Grad","kind":"full_time","source":"https://jobs.ashbyhq.com/example/42","verified_open":"2026-09-23","compensation":{"currency":"USD","min":123000,"max":158000,"min_inr_lpa":117.58,"fx_date":"2026-09-22","fx_source":"ECB","usd_inr":95.595}})
    assert o.source == "ashby"; assert o.canonical_url == "https://jobs.ashbyhq.com/example/42"; assert o.compensation.min_annual == 123000; assert o.compensation.max_annual == 158000; assert o.compensation.min_lpa_inr == pytest.approx(117.58); assert o.compensation.fx_rate == pytest.approx(95.595)


def test_dedupe_only_recovery_stub_does_not_invent_job_facts():
    o = Opportunity.from_dict({"id":"amazon:10477346","issue":2,"stage":"not_pursuing"})
    assert o.id == "amazon:10477346"
    assert o.issue_number == 2
    assert o.kind == OpportunityKind.UNKNOWN
    assert o.company == "" and o.title == "" and o.canonical_url == ""
    assert o.decision == Decision.SUPPRESSED
    assert o.metadata["dedupe_only_recovery_stub"] is True


def test_historical_recovery_stub_becomes_terminal_tombstone():
    o = Opportunity.from_dict({"id":"kaggle:legacy","issue":9,"stage":"historical"})
    assert o.stage == Stage.NOT_PURSUING
    assert o.is_terminal
    assert o.kind == OpportunityKind.UNKNOWN


def test_compact_recovery_reason_alias_is_backward_compatible():
    o = Opportunity.from_dict({
        "id": "ashby:example:senior",
        "issue": 51,
        "stage": "not_pursuing",
        "reason": "senior role misclassified as internship",
    })
    assert o.suppression_reason == "senior role misclassified as internship"
    assert o.stage == Stage.NOT_PURSUING


def test_legacy_dated_fx_conversion_restores_lost_verification_flag():
    # Only verified compensation is ever converted, so a stored dated INR
    # conversion is the verification evidence the v2 -> v3 migration dropped.
    o = Opportunity.from_dict({"id":"ashby:zip:b5242472","company":"Zip","title":"Zip — Software Engineer New Grad 2027","kind":"full_time","source":"ashby","canonical_url":"https://jobs.ashbyhq.com/zip/b5242472","compensation":{"currency":"CAD","min_annual":121000,"max_annual":126000,"period":"year","verified":False,"converted_min_annual_inr":8224000.0,"fx_rate":67.97,"fx_rate_date":"2026-09-22","fx_source":"ECB"}})
    assert o.compensation.verified is True
    assert o.compensation.source == "migrated dated FX conversion evidence"
    assert o.compensation.min_lpa_inr == pytest.approx(82.24)


def test_unconverted_compensation_is_never_promoted_to_verified():
    o = Opportunity.from_dict({"id":"career:example.com:x","company":"Example","title":"Software Engineer","kind":"full_time","source":"career_page","canonical_url":"https://example.com/jobs/x","compensation":{"currency":"CAD","min_annual":121000,"verified":False}})
    assert o.compensation.verified is False
    assert o.compensation.source is None
