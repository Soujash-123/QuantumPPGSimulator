"""SPDC source events: pump -> nonlinear crystal -> polarization-entangled pair.

Pair creation and detector effects are phenomenological Bernoulli processes;
only polarization-state measurement uses the two-qubit quantum model.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .config import SPDCConfig
from .quantum_state import BellStateModel
from .coincidence import count_coincidences

@dataclass(frozen=True)
class PhotonEvent:
    event_id: int; pair_generated: bool; signal_outcome: int | None; idler_outcome: int | None
    signal_angle_deg: float; idler_angle_deg: float; signal_detected: bool; idler_detected: bool
    timestamp_ns: float; coincidence: bool
    signal_noise_click: bool = False; idler_noise_click: bool = False

class SPDCSource:
    def __init__(self, config: SPDCConfig = SPDCConfig()):
        self.config = config; self.state = BellStateModel(config.state_fidelity); self.rng = np.random.default_rng(config.seed)

    def _detected(self, efficiency, transmission):
        genuine = self.rng.random() < efficiency * transmission
        noise = self.rng.random() < self.config.dark_count_probability + self.config.background_count_probability
        return genuine or noise, noise and not genuine

    def generate(self, trials: int, signal_angle: float = 0, idler_angle: float = 0) -> list[PhotonEvent]:
        events = []
        probs = self.state.probabilities(signal_angle, idler_angle).ravel()
        for event_id in range(trials):
            timestamp = event_id * self.config.event_period_ns
            pair = self.rng.random() < self.config.pair_generation_probability
            if pair:
                outcome = int(self.rng.choice(4, p=probs)); s, i = divmod(outcome, 2)
                sd, sn = self._detected(self.config.detector_efficiency_signal, self.config.optical_transmission_signal)
                id_, inn = self._detected(self.config.detector_efficiency_idler, self.config.optical_transmission_idler)
                # A background/dark click replaces the registered polarization bit with a random click.
                if sn: s = int(self.rng.integers(2))
                if inn: i = int(self.rng.integers(2))
            else:
                sd = self.rng.random() < self.config.dark_count_probability + self.config.background_count_probability
                id_ = self.rng.random() < self.config.dark_count_probability + self.config.background_count_probability
                sn, inn = sd, id_
                s = int(self.rng.integers(2)) if sd else None
                i = int(self.rng.integers(2)) if id_ else None
            events.append(PhotonEvent(event_id, pair, s, i, signal_angle, idler_angle, sd, id_, timestamp, sd and id_, sn, inn))
        return events

    def run(self, trials: int, signal_angle: float = 0, idler_angle: float = 0):
        events = self.generate(trials, signal_angle, idler_angle)
        return events, count_coincidences(events, self.config.coincidence_window_ns)
