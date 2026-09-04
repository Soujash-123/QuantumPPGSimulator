"""Explicit simulation assumptions; values are not experimental specifications."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SPDCConfig:
    pair_generation_probability: float = 0.20
    detector_efficiency_signal: float = 0.85
    detector_efficiency_idler: float = 0.85
    optical_transmission_signal: float = 0.90
    optical_transmission_idler: float = 0.90
    dark_count_probability: float = 0.002
    background_count_probability: float = 0.003
    state_fidelity: float = 0.98
    coincidence_window_ns: float = 5.0
    event_period_ns: float = 100.0
    seed: int = 2026

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if name not in {"coincidence_window_ns", "event_period_ns", "seed"} and not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.coincidence_window_ns < 0 or self.event_period_ns <= 0:
            raise ValueError("timing values must be non-negative and period positive")
