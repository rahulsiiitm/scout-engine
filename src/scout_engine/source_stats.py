from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .models import Decision, Opportunity, Stage


@dataclass(slots=True)
class SourceStat:
    source: str
    known: int = 0
    surfaced: int = 0
    applied: int = 0
    interviews: int = 0
    stale_or_expired: int = 0

    @property
    def qualified_yield(self) -> float:
        return 0.0 if not self.known else self.surfaced / self.known

    def to_dict(self) -> dict:
        raw = asdict(self)
        raw["qualified_yield"] = round(self.qualified_yield, 3)
        return raw


def calculate_source_stats(opportunities: list[Opportunity]) -> list[SourceStat]:
    stats: dict[str, SourceStat] = defaultdict(lambda: SourceStat(source=""))
    for o in opportunities:
        item = stats[o.source]
        item.source = o.source
        item.known += 1
        if o.decision == Decision.SURFACED:
            item.surfaced += 1
        if o.stage in {Stage.APPLIED, Stage.OA, Stage.INTERVIEW, Stage.OFFER, Stage.OFFER_ACCEPTED, Stage.REJECTED}:
            item.applied += 1
        if o.stage in {Stage.INTERVIEW, Stage.OFFER, Stage.OFFER_ACCEPTED}:
            item.interviews += 1
        if o.stage == Stage.EXPIRED or o.decision == Decision.EXPIRED:
            item.stale_or_expired += 1
    return sorted(stats.values(), key=lambda x: (-x.qualified_yield, -x.known, x.source))
