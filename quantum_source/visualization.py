"""Plots derived entirely from source measurements; uses a noninteractive backend."""
from __future__ import annotations
import numpy as np
from .measurements import correlation_from_counts

def make_plots(source, output_dir="quantum_source_output", shots=2000):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pathlib import Path
    directory = Path(output_dir); directory.mkdir(parents=True, exist_ok=True)
    p = source.state.probabilities(0, 0)
    fig, ax = plt.subplots(); ax.imshow(p, vmin=0, vmax=.5); ax.set(title="Two-photon outcome probabilities", xlabel="Idler outcome", ylabel="Signal outcome"); fig.savefig(directory/"state_probabilities.png", dpi=140); plt.close(fig)
    events, _ = source.run(shots, 0, 0)
    signal = [sum(e.signal_detected and e.signal_outcome == outcome for e in events) for outcome in (0, 1)]
    idler = [sum(e.idler_detected and e.idler_outcome == outcome for e in events) for outcome in (0, 1)]
    fig, ax = plt.subplots(); x=np.arange(2); ax.bar(x-.18, signal, .36, label="signal"); ax.bar(x+.18, idler, .36, label="idler"); ax.set(xticks=x, xticklabels=["H / 0", "V / 1"], ylabel="Detected counts", title="Signal and idler measurement statistics"); ax.legend(); fig.savefig(directory/"measurement_statistics.png", dpi=140); plt.close(fig)
    angles = np.linspace(0, 90, 19); ideal=[]; noisy=[]; coincidence=[]
    ideal_source = type(source)(source.config.__class__(pair_generation_probability=1, detector_efficiency_signal=1, detector_efficiency_idler=1, optical_transmission_signal=1, optical_transmission_idler=1, dark_count_probability=0, background_count_probability=0, state_fidelity=1, seed=source.config.seed))
    for angle in angles:
        e, c = ideal_source.run(shots, 0, float(angle)); ideal.append(np.mean([1 if x.signal_outcome == x.idler_outcome else -1 for x in e]))
        e, c = source.run(shots, 0, float(angle)); valid=[x for x in e if x.pair_generated and x.signal_detected and x.idler_detected]; noisy.append(np.mean([1 if x.signal_outcome == x.idler_outcome else -1 for x in valid]) if valid else 0); coincidence.append(c.coincidences)
    fig, ax = plt.subplots(); ax.plot(angles, ideal, label="ideal"); ax.plot(angles, noisy, label="configured noisy"); ax.set(xlabel="Analyzer-angle difference (degrees)", ylabel="Correlation E", title="Polarization correlation",); ax.legend(); fig.savefig(directory/"correlation_comparison.png", dpi=140); plt.close(fig)
    fig, ax = plt.subplots(); ax.bar(angles, coincidence, width=3); ax.set(xlabel="Idler angle (degrees)", ylabel="Coincidences", title="Coincidence counts"); fig.savefig(directory/"coincidences.png", dpi=140); plt.close(fig)
    return directory
