from __future__ import annotations
import numpy as np
from .config import DetectorConfig
from .detector_event import DetectionEvent

class SPADDetector:
    """Event-level SPAD/APD approximation; no avalanche semiconductor physics."""
    def __init__(self, name: str, config: DetectorConfig = DetectorConfig(), rng=None):
        self.name, self.config = name, config; self.rng = rng or np.random.default_rng(); self._last_detection_ns = -np.inf
    def detect(self, photon, gate_timestamp_ns: float) -> DetectionEvent | None:
        c = self.config
        genuine = bool(photon is not None and photon.survived and self.rng.random() < c.quantum_efficiency)
        noise = bool(not genuine and self.rng.random() < c.dark_count_probability_per_gate + c.background_probability_per_gate)
        if not (genuine or noise): return None
        timestamp = gate_timestamp_ns if noise else photon.timestamp_ns
        timestamp += self.rng.normal(0, c.timing_jitter_std_ns)
        if timestamp - self._last_detection_ns < c.dead_time_ns: return None
        self._last_detection_ns = timestamp
        return DetectionEvent(self.name, float(timestamp), photon.parent_event_id if genuine else None,
                              photon.polarization_outcome if genuine else int(self.rng.integers(2)), genuine, noise)
