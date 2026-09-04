from __future__ import annotations
import numpy as np
from .config import ProcessingConfig
from .filters import bandpass, zscore

class QuantumPPGExtractor:
    """Primary estimator: -C/N_reference, a reference-normalized coincidence absorption signal."""
    def __init__(self, config: ProcessingConfig = ProcessingConfig()): self.config=config
    def raw(self, coincidences, reference_singles):
        c=np.asarray(coincidences,float); r=np.asarray(reference_singles,float)
        # Minus sign maps fewer transmitted pairs (more blood absorption) to positive PPG.
        return -(c / np.maximum(r, 1.0) - np.mean(c / np.maximum(r, 1.0)))
    def filtered(self, raw):
        fs=1000/self.config.bin_width_ms
        return zscore(bandpass(raw, fs, self.config.bandpass_low_hz, self.config.bandpass_high_hz, self.config.causal_filter))
