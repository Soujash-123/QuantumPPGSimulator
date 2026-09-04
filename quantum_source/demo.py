"""Run with: python -m quantum_source.demo"""
from .config import SPDCConfig
from .spdc_source import SPDCSource
from .measurements import qutip_probabilities, aer_sample, correlation_from_counts
from .visualization import make_plots

def main():
    source = SPDCSource(SPDCConfig())
    events, stats = source.run(10000, 0, 0)
    metric = source.state.metrics()
    print("## SPDC ENTANGLED PHOTON SOURCE\n\nState: (|HH> + |VV>)/sqrt(2)")
    print(f"Pair generation probability: {source.config.pair_generation_probability}\nDetector efficiency: {source.config.detector_efficiency_signal}\nNoise level: {source.config.dark_count_probability + source.config.background_count_probability}")
    print(f"\nSignal detections: {stats.signal}\nIdler detections: {stats.idler}\nCoincidences: {stats.coincidences}")
    print(f"\nEntanglement metric (concurrence): {metric['concurrence']:.4f}\nCorrelation E(H/V): {metric['correlation_hv']:.4f}")
    try:
        qt = qutip_probabilities(source.state, 0, 30)
        aer = aer_sample(0, 30, 20000, 2026)
        aer_p = __import__('numpy').array([[aer[(s,i)]/20000 for i in (0,1)] for s in (0,1)])
        print(f"QuTiP/Aer max probability difference at 30 deg: {abs(qt-aer_p).max():.4f}")
    except ImportError as exc: print(f"Backend validation unavailable: {exc}")
    try:
        print(f"Plots: {make_plots(source)}")
    except ImportError as exc:
        print(f"Plots unavailable until Matplotlib is installed: {exc}")

if __name__ == '__main__': main()
