from __future__ import annotations
import numpy as np
from .config import ProcessingConfig
from .filters import bandpass, zscore

class ClassicalPPGExtractor:
    """Control estimator based solely on sensing-arm singles: -N_A."""
    def __init__(self, config: ProcessingConfig = ProcessingConfig()): self.config=config
    def raw(self, signal_singles):
        x=np.asarray(signal_singles,float); return -(x/np.mean(x)-1) if np.mean(x) else x
    def filtered(self, raw):
        fs=1000/self.config.bin_width_ms
        return zscore(bandpass(raw, fs, self.config.bandpass_low_hz, self.config.bandpass_high_hz, self.config.causal_filter))
