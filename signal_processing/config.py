from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessingConfig:
    bin_width_ms: float = 20.0
    bandpass_low_hz: float = 0.5
    bandpass_high_hz: float = 4.0
    causal_filter: bool = False
    normalization_epsilon: float = 1e-9
    def __post_init__(self):
        if self.bin_width_ms <= 0 or not 0 < self.bandpass_low_hz < self.bandpass_high_hz:
            raise ValueError("invalid bin/filter configuration")
