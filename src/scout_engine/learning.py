from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import Opportunity, Stage


@dataclass(frozen=True, slots=True)
class PreferenceWeights:
    role_weights: dict[str, float]
    source_weights: dict[str, float]


def learn_preferences(opportunities: list[Opportunity]) -> PreferenceWeights:
    """Learn small bounded ranking nudges from explicit funnel behavior.

    These weights never bypass hard eligibility gates and never alter the
    evidence-based fit score. They may only break ties in action priority.
    """
    role_acc: dict[str, list[float]] = defaultdict(list)
    source_acc: dict[str, list[float]] = defaultdict(list)

    stage_signal = {
        Stage.NOT_PURSUING: -1.0,
        Stage.WITHDRAWN: -0.5,
        Stage.QUALIFIED: 0.0,
        Stage.REVIEWING: 0.2,
        Stage.APPLIED: 0.5,
        Stage.OA: 0.8,
        Stage.INTERVIEW: 1.0,
        Stage.OFFER: 1.0,
        Stage.OFFER_ACCEPTED: 1.0,
        Stage.REJECTED: 0.25,
    }

    for o in opportunities:
        signal = stage_signal.get(o.stage)
        if signal is None:
            continue
        source_acc[o.source].append(signal)
        role_key = str(o.metadata.get("role_family", "unknown"))
        role_acc[role_key].append(signal)

    def reduce(values: dict[str, list[float]]) -> dict[str, float]:
        return {
            key: round(max(-0.5, min(0.5, sum(v) / max(4, len(v)))), 3)
            for key, v in values.items()
        }

    return PreferenceWeights(reduce(role_acc), reduce(source_acc))
