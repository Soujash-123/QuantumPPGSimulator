"""Time-window coincidence analysis, independent of detector implementation."""
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class CoincidenceStats:
    signal: int
    idler: int
    coincidences: int

def count_coincidences(events: Iterable, window_ns: float) -> CoincidenceStats:
    signal_times = [e.timestamp_ns for e in events if e.signal_detected]
    idler_times = [e.timestamp_ns for e in events if e.idler_detected]
    used = set(); coincidences = 0
    for s in signal_times:
        candidates = [(abs(s-i), index) for index, i in enumerate(idler_times) if index not in used and abs(s-i) <= window_ns]
        if candidates:
            _, index = min(candidates); used.add(index); coincidences += 1
    return CoincidenceStats(len(signal_times), len(idler_times), coincidences)
