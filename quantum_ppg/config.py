from dataclasses import dataclass, field
from quantum_source import SPDCConfig
from biosensor import BloodVolumeConfig, TissueConfig
from optical_path import OpticalPathConfig
from detectors import DetectorConfig
from signal_processing import ProcessingConfig

@dataclass(frozen=True)
class QuantumPPGConfig:
    source: SPDCConfig = field(default_factory=lambda: SPDCConfig(pair_generation_probability=.25, detector_efficiency_signal=1, detector_efficiency_idler=1, optical_transmission_signal=1, optical_transmission_idler=1, dark_count_probability=0, background_count_probability=0))
    blood: BloodVolumeConfig = field(default_factory=BloodVolumeConfig)
    tissue: TissueConfig = field(default_factory=TissueConfig)
    sensing_path: OpticalPathConfig = field(default_factory=OpticalPathConfig)
    reference_path: OpticalPathConfig = field(default_factory=OpticalPathConfig)
    signal_detector: DetectorConfig = field(default_factory=DetectorConfig)
    reference_detector: DetectorConfig = field(default_factory=DetectorConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    pump_trials_per_second: int = 20_000
    seed: int = 9001
    def __post_init__(self):
        if self.pump_trials_per_second <= 0: raise ValueError("pump_trials_per_second must be positive")
