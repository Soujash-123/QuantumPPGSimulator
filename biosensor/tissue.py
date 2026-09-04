"""Effective modified Beer--Lambert fingertip attenuation model."""
from __future__ import annotations
import numpy as np
from .config import TissueConfig

class FingertipTissue:
    """Maps blood volume to optical transmission; not Monte-Carlo tissue transport."""
    def __init__(self, config: TissueConfig = TissueConfig()): self.config = config
    def effective_attenuation_per_mm(self, blood_volume: np.ndarray) -> np.ndarray:
        c = self.config
        # Modified Beer--Lambert form: baseline terms set DC attenuation, while
        # the blood term describes pulsatile change relative to baseline volume.
        return c.baseline_absorption_per_mm + c.scattering_attenuation_per_mm + c.blood_absorption_per_mm_per_unit*(np.asarray(blood_volume)-c.baseline_blood_volume)
    def transmission(self, blood_volume: np.ndarray) -> np.ndarray:
        return np.exp(-self.effective_attenuation_per_mm(blood_volume) * self.config.optical_path_mm)
