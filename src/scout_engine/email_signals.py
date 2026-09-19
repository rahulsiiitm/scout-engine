from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from .models import Stage


class SignalKind(StrEnum):
    APPLICATION_CONFIRMATION = "application_confirmation"
    ASSESSMENT = "assessment"
    INTERVIEW = "interview"
    REJECTION = "rejection"
    OFFER = "offer"


@dataclass(frozen=True, slots=True)
class StageProposal:
    target_stage: Stage
    signal: SignalKind
    confidence: float
    reason: str


PATTERNS: list[tuple[SignalKind, Stage, float, tuple[str, ...]]] = [
    (SignalKind.OFFER, Stage.OFFER, 0.98, ("offer of employment", "pleased to offer", "offer letter")),
    (SignalKind.REJECTION, Stage.REJECTED, 0.96, ("will not be moving forward", "decided not to proceed", "not moving forward with your application")),
    (SignalKind.INTERVIEW, Stage.INTERVIEW, 0.94, ("schedule an interview", "interview availability", "interview invitation")),
    (SignalKind.ASSESSMENT, Stage.OA, 0.92, ("online assessment", "coding assessment", "take-home assignment", "take home assignment")),
    (SignalKind.APPLICATION_CONFIRMATION, Stage.APPLIED, 0.90, ("thank you for applying", "application received", "received your application")),
]


def propose_stage(subject: str, body: str) -> StageProposal | None:
    text = re.sub(r"\s+", " ", f"{subject} {body}").lower()
    for signal, stage, confidence, patterns in PATTERNS:
        for pattern in patterns:
            if pattern in text:
                return StageProposal(stage, signal, confidence, f"matched phrase: {pattern!r}")
    return None
