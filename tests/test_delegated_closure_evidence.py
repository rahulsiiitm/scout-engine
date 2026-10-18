"""Regression checks: failed ATS delegation is never closure evidence."""
import pytest

from scout_engine.discovery.ats_fingerprint import AtsFingerprint
from scout_engine.models import Decision, Opportunity, OpportunityKind, Stage
from scout_engine.runner import _mark_source_disappearances
from scout_engine.sources.base import SourceError
from scout_engine.sources.career_page import CareerPageAdapter
from scout_engine.sources.greenhouse import GreenhouseAdapter


def _fp():
    return AtsFingerprint("greenhouse", "acme", "https://job-boards.greenhouse.io/acme")


def _existing():
    return Opportunity(
        id="greenhouse:acme:old",
        company="Acme",
        title="Software Engineer",
        kind=OpportunityKind.FULL_TIME,
        source="greenhouse",
        canonical_url="https://job-boards.greenhouse.io/acme/jobs/old",
        source_status="open",
        stage=Stage.QUALIFIED,
        decision=Decision.SURFACED,
        metadata={"source_key": "greenhouse:acme"},
    )


def test_failed_delegated_source_cannot_advance_successful_misses(monkeypatch):
    def failing_fetch(self):
        raise SourceError("temporary 503")

    monkeypatch.setattr(GreenhouseAdapter, "fetch", failing_fetch)
    adapter = CareerPageAdapter("Acme", "acme.com")
    with pytest.raises(SourceError):
        adapter._delegate(_fp())
    assert adapter.effective_source_keys() == {"career:acme.com"}

    existing = _existing()
    changed = _mark_source_disappearances(
        {existing.id: existing},
        successful_keys=adapter.effective_source_keys(),
        seen_by_key={"career:acme.com": {"unrelated-job"}},
        miss_limit=2,
    )
    assert changed == 0
    assert existing.missing_successful_scans == 0
    assert existing.stage == Stage.QUALIFIED


def test_empty_delegated_source_is_not_assumed_complete(monkeypatch):
    monkeypatch.setattr(GreenhouseAdapter, "fetch", lambda self: [])
    adapter = CareerPageAdapter("Acme", "acme.com")
    assert adapter._delegate(_fp()) == []
    assert adapter.effective_source_keys() == {"career:acme.com"}


def test_successful_nonempty_delegation_registers_actual_source(monkeypatch):
    item = _existing()
    monkeypatch.setattr(GreenhouseAdapter, "fetch", lambda self: [item])
    adapter = CareerPageAdapter("Acme", "acme.com")
    assert adapter._delegate(_fp()) == [item]
    assert adapter.effective_source_keys() == {"career:acme.com", "greenhouse:acme"}
    assert item.metadata["discovered_via"] == "career:acme.com"
