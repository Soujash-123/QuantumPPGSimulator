from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PropagatedPhoton:
    parent_event_id: int | None
    arm: str
    timestamp_ns: float
    polarization_outcome: int | None
    survived: bool
    from_pair: bool
