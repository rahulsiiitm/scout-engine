import json

import pytest

from scout_engine.models import Opportunity, OpportunityKind
from scout_engine.state import OpportunityStore


def _opp(identifier: str) -> Opportunity:
    return Opportunity(
        id=identifier,
        company="Example",
        title="Software Engineer",
        kind=OpportunityKind.FULL_TIME,
        source="test",
        canonical_url=f"https://example.com/{identifier}",
    )


def test_store_refuses_accidental_ledger_shrink(tmp_path):
    path = tmp_path / "opportunities.json"
    store = OpportunityStore(path)
    store.save([_opp("a"), _opp("b")])
    with pytest.raises(RuntimeError, match="refusing to shrink"):
        store.save([_opp("a")])
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert len(raw["opportunities"]) == 2


def test_store_writes_valid_json_atomically(tmp_path):
    path = tmp_path / "opportunities.json"
    store = OpportunityStore(path)
    store.save([_opp("a")])
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 3
    assert raw["opportunities"][0]["id"] == "a"
    assert not (tmp_path / "opportunities.json.tmp").exists()


def test_recovery_migration_merges_new_records_and_preserves_richer_base(tmp_path):
    path = tmp_path / "opportunities.json"
    base = {
        "version": 3,
        "opportunities": [{
            "id": "x",
            "company": "Example",
            "title": "Senior Internal Applications Engineer",
            "kind": "full_time",
            "source": "test",
            "canonical_url": "https://example.com/x",
            "stage": "qualified",
            "decision": "surfaced",
        }],
    }
    recovery = {
        "version": 2,
        "opportunities": [
            {"id": "x", "issue": 51, "stage": "not_pursuing", "reason": "bad historical classification"},
            {"id": "y", "issue": 52, "stage": "qualified"},
        ],
    }
    path.write_text(json.dumps(base), encoding="utf-8")
    (tmp_path / "recovery-2026-09-24.json").write_text(json.dumps(recovery), encoding="utf-8")
    store = OpportunityStore(path)
    items = {item.id: item for item in store.load()}
    assert items["x"].company == "Example"
    assert items["x"].issue_number == 51
    assert items["x"].suppression_reason == "bad historical classification"
    assert items["y"].issue_number == 52
    store.save(list(items.values()))
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert "recovery-2026-09-24.json" in persisted["applied_recovery_migrations"]
