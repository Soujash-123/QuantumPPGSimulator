from __future__ import annotations
from dataclasses import dataclass
from .detector_event import DetectionEvent

@dataclass(frozen=True)
class BinnedCoincidenceStats:
    signal_singles: int
    reference_singles: int
    coincidences: int
    genuine_coincidences: int
    accidentals: int

class CoincidenceProcessor:
    """External timing electronics; it precedes the Arduino and resolves ns events."""
    def __init__(self, coincidence_window_ns: float = 5.0): self.coincidence_window_ns = coincidence_window_ns
    def process(self, signal_events: list[DetectionEvent], reference_events: list[DetectionEvent]) -> BinnedCoincidenceStats:
        signal, reference = sorted(signal_events, key=lambda e:e.timestamp_ns), sorted(reference_events, key=lambda e:e.timestamp_ns)
        used=set(); coincidences=genuine=0
        for s in signal:
            candidates=[(abs(s.timestamp_ns-r.timestamp_ns), idx, r) for idx,r in enumerate(reference) if idx not in used and abs(s.timestamp_ns-r.timestamp_ns)<=self.coincidence_window_ns]
            if candidates:
                _, idx, r=min(candidates); used.add(idx); coincidences += 1
                genuine += int(s.genuine_photon and r.genuine_photon and s.parent_event_id == r.parent_event_id)
        return BinnedCoincidenceStats(len(signal), len(reference), coincidences, genuine, coincidences-genuine)
