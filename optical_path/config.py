from dataclasses import dataclass

@dataclass(frozen=True)
class OpticalPathConfig:
    static_transmission: float = 0.92
    propagation_delay_ns: float = 12.0
    background_probability_per_gate: float = 0.0005
    polarization_decoherence_probability: float = 0.0
    def __post_init__(self):
        for value in (self.static_transmission, self.background_probability_per_gate, self.polarization_decoherence_probability):
            if not 0 <= value <= 1: raise ValueError("probabilities/transmissions must be in [0, 1]")
