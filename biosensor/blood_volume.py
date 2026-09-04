"""Pulsatile arterial-blood-volume waveform for a fingertip PPG twin."""
from __future__ import annotations
import numpy as np
from .config import BloodVolumeConfig

class BloodVolumeModel:
    """Analytic systolic-rise/diastolic-decay pulse with optional dicrotic feature."""
    def __init__(self, config: BloodVolumeConfig = BloodVolumeConfig()):
        self.config = config
        self._rng = np.random.default_rng(config.seed)

    def waveform(self, time_s: np.ndarray) -> np.ndarray:
        c = self.config; t = np.asarray(time_s, dtype=float); period = 60.0 / c.heart_rate_bpm
        phase = np.mod(t, period) / period
        rise = max(c.systolic_rise_fraction, 1e-3)
        # Gamma-shaped systolic pulse: rapid onset, asymmetric diastolic decline.
        systolic = (phase / rise) ** 2 * np.exp(-2 * phase / rise)
        systolic /= (np.max(systolic) if np.max(systolic) else 1.0)
        notch_center = min(.95, rise + c.diastolic_decay_fraction)
        notch = c.dicrotic_notch_amplitude * np.exp(-.5 * ((phase - notch_center) / .045) ** 2)
        pulse = systolic + notch
        respiratory = c.respiratory_modulation_fraction * np.sin(2*np.pi*t*c.respiratory_rate_bpm/60.0)
        drift = c.baseline_drift_fraction * np.sin(2*np.pi*t/30.0)
        noise = self._rng.normal(0, c.physiological_noise_std, t.shape) if c.physiological_noise_std else 0.0
        return c.baseline_blood_volume + c.pulse_amplitude * pulse * (1 + respiratory) + drift + noise

    @property
    def true_heart_rate_bpm(self) -> float:
        return self.config.heart_rate_bpm
