from __future__ import annotations

import json
from pathlib import Path

from .models import Opportunity


class OpportunityStore:
    def __init__(self, path: str | Path = "data/opportunities.json") -> None:
        self.path = Path(path)

    def load(self) -> list[Opportunity]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [Opportunity.from_dict(item) for item in raw.get("opportunities", [])]

    def save(self, opportunities: list[Opportunity]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 3,
            "opportunities": [o.to_dict() for o in sorted(opportunities, key=lambda x: x.id)],
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def upsert(self, opportunity: Opportunity) -> list[Opportunity]:
        items = self.load()
        by_id = {item.id: item for item in items}
        by_id[opportunity.id] = opportunity
        updated = list(by_id.values())
        self.save(updated)
        return updated
