from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DetectionEvent:
    detector: str
    timestamp_ns: float
    parent_event_id: int | None
    polarization_outcome: int | None
    genuine_photon: bool
    dark_or_background: bool
