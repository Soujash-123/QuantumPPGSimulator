from dataclasses import dataclass

@dataclass(frozen=True)
class BloodVolumeConfig:
    """Physiological approximation, not a patient-specific cardiovascular model."""
    heart_rate_bpm: float = 72.0
    baseline_blood_volume: float = 1.0
    pulse_amplitude: float = 0.12
    systolic_rise_fraction: float = 0.16
    diastolic_decay_fraction: float = 0.35
    dicrotic_notch_amplitude: float = 0.18
    respiratory_modulation_fraction: float = 0.03
    respiratory_rate_bpm: float = 15.0
    baseline_drift_fraction: float = 0.01
    physiological_noise_std: float = 0.0
    seed: int = 104

@dataclass(frozen=True)
class TissueConfig:
    wavelength_nm: float = 810.0
    optical_path_mm: float = 8.0
    baseline_absorption_per_mm: float = 0.030
    # Differential arterial-volume sensitivity; baseline absorption is separate.
    blood_absorption_per_mm_per_unit: float = 0.25
    baseline_blood_volume: float = 1.0
    scattering_attenuation_per_mm: float = 0.018
    tissue_decoherence_probability: float = 0.0

    def __post_init__(self):
        if self.optical_path_mm <= 0 or self.wavelength_nm <= 0:
            raise ValueError("optical path and wavelength must be positive")
        if not 0 <= self.tissue_decoherence_probability <= 1:
            raise ValueError("tissue_decoherence_probability must be in [0, 1]")
