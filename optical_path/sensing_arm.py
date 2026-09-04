from __future__ import annotations
from .config import OpticalPathConfig
from .photon_path import PropagatedPhoton
from .losses import survives

class SensingArm:
    """Signal arm: static path loss multiplied by pulsatile tissue transmission."""
    def __init__(self, config: OpticalPathConfig = OpticalPathConfig()): self.config = config
    def propagate(self, event_id, timestamp_ns, outcome, tissue_transmission, rng) -> PropagatedPhoton:
        survival = survives(rng, self.config.static_transmission * tissue_transmission)
        # Optional depolarizing channel is separate from loss; off by default.
        polarization = outcome if not (survival and rng.random() < self.config.polarization_decoherence_probability) else int(rng.integers(2))
        return PropagatedPhoton(event_id, "signal", timestamp_ns+self.config.propagation_delay_ns, polarization, survival, True)
