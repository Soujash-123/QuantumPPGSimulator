from dataclasses import dataclass

@dataclass(frozen=True)
class DetectorConfig:
    quantum_efficiency: float = 0.78
    dark_count_probability_per_gate: float = 0.0001
    background_probability_per_gate: float = 0.0005
    timing_jitter_std_ns: float = 0.35
    dead_time_ns: float = 25.0
    def __post_init__(self):
        for value in (self.quantum_efficiency, self.dark_count_probability_per_gate, self.background_probability_per_gate):
            if not 0 <= value <= 1: raise ValueError("detector probabilities must be in [0, 1]")
