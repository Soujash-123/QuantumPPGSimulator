import unittest
from dataclasses import replace
import numpy as np
from biosensor import BloodVolumeConfig, BloodVolumeModel, FingertipTissue, TissueConfig
from quantum_ppg import QuantumPPGConfig, QuantumPPGSystem
from quantum_ppg.experiment import background_noise_sweep
from detectors import DetectorConfig

class TestFullQuantumPPG(unittest.TestCase):
    def test_constant_blood_volume_has_constant_transmission(self):
        values=BloodVolumeModel(BloodVolumeConfig(pulse_amplitude=0, respiratory_modulation_fraction=0, baseline_drift_fraction=0)).waveform(np.linspace(0,3,50))
        transmission=FingertipTissue().transmission(values)
        self.assertAlmostEqual(float(np.ptp(transmission)), 0.0, places=12)
    def test_more_blood_means_less_transmission(self):
        tissue=FingertipTissue(); self.assertLess(tissue.transmission(np.array([1.2]))[0], tissue.transmission(np.array([1.0]))[0])
    def test_lower_sensing_transmission_reduces_singles_and_coincidences(self):
        base=QuantumPPGConfig(); low=replace(base, sensing_path=replace(base.sensing_path, static_transmission=.25))
        high_result=QuantumPPGSystem(base).run(2,drive_arduino=False); low_result=QuantumPPGSystem(low).run(2,drive_arduino=False)
        self.assertLess(low_result.signal_singles.sum(), high_result.signal_singles.sum())
        self.assertLess(low_result.coincidences.sum(), high_result.coincidences.sum())
    def test_reference_arm_has_no_tissue_transmission_dependency(self):
        base=QuantumPPGConfig(); flat=replace(base, blood=replace(base.blood, pulse_amplitude=0, respiratory_modulation_fraction=0, baseline_drift_fraction=0))
        pulsatile=QuantumPPGSystem(base).run(2,drive_arduino=False); no_pulse=QuantumPPGSystem(flat).run(2,drive_arduino=False)
        # Same seed; B has no tissue argument, so its reference counts remain identical.
        np.testing.assert_array_equal(pulsatile.reference_singles,no_pulse.reference_singles)
    def test_zero_pair_probability_has_no_genuine_coincidences(self):
        base=QuantumPPGConfig(); cfg=replace(base, source=replace(base.source,pair_generation_probability=0))
        result=QuantumPPGSystem(cfg).run(1,drive_arduino=False)
        self.assertEqual(result.genuine_coincidences.sum(),0)
    def test_zero_detector_efficiency_prevents_genuine_coincidences(self):
        base=QuantumPPGConfig(); cfg=replace(base,signal_detector=DetectorConfig(quantum_efficiency=0),reference_detector=DetectorConfig(quantum_efficiency=0))
        result=QuantumPPGSystem(cfg).run(1,drive_arduino=False)
        self.assertEqual(result.genuine_coincidences.sum(),0)
    def test_recovered_heart_rate_is_close_to_ground_truth(self):
        result=QuantumPPGSystem().run(5,drive_arduino=False)
        self.assertIsNotNone(result.quantum_metrics.heart_rate_bpm)
        self.assertLess(abs(result.quantum_metrics.heart_rate_bpm-result.true_heart_rate_bpm),6)
    def test_arduino_receives_conditioned_coincidences_and_bounded_adc(self):
        result=QuantumPPGSystem().run(1,drive_arduino=True)
        self.assertEqual(result.arduino_coincidence_pulses,int(result.coincidences.sum()))
        self.assertEqual(result.arduino_adc_samples,len(result.time_s))
    def test_coincidence_conditioning_rejects_high_uncorrelated_background_under_model(self):
        _, quantum, classical=background_noise_sweep(QuantumPPGConfig(),probabilities=(.2,),duration_seconds=5)[0]
        self.assertGreater(quantum.correlation,classical.correlation)

if __name__ == '__main__': unittest.main()
