from __future__ import annotations
from .config import OpticalPathConfig
from .photon_path import PropagatedPhoton
from .losses import survives

class ReferenceArm:
    """Idler/reference arm: independent loss and delay, no tissue interaction."""
    def __init__(self, config: OpticalPathConfig = OpticalPathConfig()): self.config = config
    def propagate(self, event_id, timestamp_ns, outcome, rng) -> PropagatedPhoton:
        survival = survives(rng, self.config.static_transmission)
        polarization = outcome if not (survival and rng.random() < self.config.polarization_decoherence_probability) else int(rng.integers(2))
        return PropagatedPhoton(event_id, "reference", timestamp_ns+self.config.propagation_delay_ns, polarization, survival, True)
