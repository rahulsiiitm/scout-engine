from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Opportunity


_RECOVERY_MIGRATION = "recovery-2026-09-24.json"


def _record_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("stable_id") or "")


def _merge_recovery(base_items: list[dict[str, Any]], recovery_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {_record_id(item): dict(item) for item in base_items if _record_id(item)}
    for recovery in recovery_items:
        identifier = _record_id(recovery)
        if not identifier:
            continue
        prior = by_id.get(identifier)
        if prior is None:
            by_id[identifier] = dict(recovery)
            continue

        merged = dict(prior)
        # Recovery snapshots are authoritative only for lifecycle/cockpit state.
        # Keep richer canonical job facts from the full V3 ledger.
        if "stage" in recovery:
            merged["stage"] = "not_pursuing" if recovery["stage"] == "historical" else recovery["stage"]
        if "issue" in recovery:
            merged["issue_number"] = recovery["issue"]
        if "issue_number" in recovery:
            merged["issue_number"] = recovery["issue_number"]
        if "reason" in recovery:
            merged["suppression_reason"] = recovery["reason"]
        if "suppression_reason" in recovery:
            merged["suppression_reason"] = recovery["suppression_reason"]
        if "decision" in recovery:
            merged["decision"] = recovery["decision"]

        stage = str(merged.get("stage") or "")
        if stage in {"qualified", "reviewing", "applied", "oa", "interview", "offer", "offer_accepted"}:
            merged["decision"] = "surfaced"
        elif stage == "expired":
            merged["decision"] = "expired"
        elif stage in {"not_pursuing", "rejected", "withdrawn", "closed"}:
            merged["decision"] = "suppressed"
        by_id[identifier] = merged
    return list(by_id.values())


class OpportunityStore:
    def __init__(self, path: str | Path = "data/opportunities.json") -> None:
        self.path = Path(path)
        self._applied_recovery_migrations: set[str] = set()

    def load(self) -> list[Opportunity]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        items = list(raw.get("opportunities", []))
        applied = set(raw.get("applied_recovery_migrations", []) or [])

        recovery_path = self.path.parent / _RECOVERY_MIGRATION
        if recovery_path.exists() and _RECOVERY_MIGRATION not in applied:
            recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
            items = _merge_recovery(items, list(recovery.get("opportunities", [])))
            applied.add(_RECOVERY_MIGRATION)

        self._applied_recovery_migrations = applied
        return [Opportunity.from_dict(item) for item in items]

    def save(self, opportunities: list[Opportunity]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing_markers: set[str] = set()
        if self.path.exists():
            existing = json.loads(self.path.read_text(encoding="utf-8"))
            previous_count = len(existing.get("opportunities", []))
            existing_markers = set(existing.get("applied_recovery_migrations", []) or [])
            if previous_count and len(opportunities) < previous_count:
                raise RuntimeError(
                    f"refusing to shrink canonical opportunity ledger from {previous_count} to {len(opportunities)} records"
                )

        payload: dict[str, Any] = {
            "version": 3,
            "opportunities": [o.to_dict() for o in sorted(opportunities, key=lambda x: x.id)],
        }
        markers = sorted(existing_markers | self._applied_recovery_migrations)
        if markers:
            payload["applied_recovery_migrations"] = markers

        serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(serialized, encoding="utf-8")
        temporary.replace(self.path)

    def upsert(self, opportunity: Opportunity) -> list[Opportunity]:
        items = self.load()
        by_id = {item.id: item for item in items}
        by_id[opportunity.id] = opportunity
        updated = list(by_id.values())
        self.save(updated)
        return updated
