import unittest
import numpy as np
from quantum_source import SPDCConfig, SPDCSource, BellStateModel
from quantum_source.coincidence import count_coincidences

class TestSPDCSource(unittest.TestCase):
    def test_bell_metrics(self):
        m = BellStateModel().metrics()
        self.assertAlmostEqual(m['normalization'], 1); self.assertAlmostEqual(m['purity'], 1)
        self.assertAlmostEqual(m['concurrence'], 1); np.testing.assert_allclose(m['reduced_signal'], np.eye(2)/2)
    def test_hv_probabilities(self): np.testing.assert_allclose(BellStateModel().probabilities(0,0), [[.5,0],[0,.5]], atol=1e-12)
    def test_noise_reduces_observed_correlation_and_concurrence(self):
        clean, noisy = BellStateModel(), BellStateModel(.55)
        self.assertLess(noisy.metrics()['concurrence'], clean.metrics()['concurrence'])
        self.assertLess(noisy.metrics()['correlation_hv'], clean.metrics()['correlation_hv'])
    def test_pair_rate_and_coincidences(self):
        low=SPDCSource(SPDCConfig(pair_generation_probability=.05, dark_count_probability=0, background_count_probability=0)); high=SPDCSource(SPDCConfig(pair_generation_probability=.7, dark_count_probability=0, background_count_probability=0))
        self.assertLess(sum(x.pair_generated for x in low.generate(3000)), sum(x.pair_generated for x in high.generate(3000)))
    def test_detector_noise_degrades_observed_correlation(self):
        clean=SPDCSource(SPDCConfig(pair_generation_probability=1, detector_efficiency_signal=1, detector_efficiency_idler=1, optical_transmission_signal=1, optical_transmission_idler=1, dark_count_probability=0, background_count_probability=0))
        noisy=SPDCSource(SPDCConfig(pair_generation_probability=1, detector_efficiency_signal=.5, detector_efficiency_idler=.5, optical_transmission_signal=.5, optical_transmission_idler=.5, dark_count_probability=.2, background_count_probability=.2))
        # The intrinsic state is retained; low efficiency and noise create fewer usable coincidences.
        self.assertGreater(sum(x.signal_detected and x.idler_detected for x in clean.generate(1000)), sum(x.signal_detected and x.idler_detected for x in noisy.generate(1000)))
    def test_qutip_partial_traces(self):
        try: q = BellStateModel().qutip_metrics()
        except ImportError: self.skipTest('QuTiP not installed')
        self.assertAlmostEqual(q['normalization'], 1)
        np.testing.assert_allclose(q['reduced_signal'].full(), np.eye(2)/2)
    def test_qutip_and_aer_agree(self):
        try:
            from quantum_source.measurements import qutip_probabilities, aer_sample
            p=qutip_probabilities(BellStateModel(), 0, 25); c=aer_sample(0,25,20000,7); a=np.array([[c[s,i]/20000 for i in (0,1)] for s in (0,1)])
        except ImportError: self.skipTest('Qiskit Aer and QuTiP not installed')
        self.assertLess(np.max(abs(p-a)), .025)

if __name__ == '__main__': unittest.main()
