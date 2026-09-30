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
