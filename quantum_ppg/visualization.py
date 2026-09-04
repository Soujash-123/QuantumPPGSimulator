"""Full-system plots, each trace derived from a QuantumPPGResult."""
from pathlib import Path
import numpy as np


def _styled(ax, title, ylabel, xlabel="Simulated time (s)"):
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.tick_params(labelsize=9)


def make_system_plots(result, output_dir="quantum_ppg_output", noise_results=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130})

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    t = result.time_s
    bin_ms = (t[1] - t[0]) * 1000.0 if len(t) > 1 else 0.0

    def simple(name, y, title, ylabel):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(t, y, color="#1f77b4", linewidth=1.6)
        _styled(ax, title, ylabel)
        fig.tight_layout()
        fig.savefig(directory / name)
        plt.close(fig)

    def layered(name, primary, others, title, ylabel):
        fig, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(t, primary, color="#1f77b4", linewidth=1.6, label="total")
        for label, values, color in others:
            ax.plot(t, values, color=color, linewidth=1.2, alpha=0.85, label=label)
        _styled(ax, title, ylabel)
        ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
        fig.tight_layout()
        fig.savefig(directory / name)
        plt.close(fig)

    simple("01_blood_volume.png", result.blood_volume,
           "Ground-truth pulsatile blood-volume waveform", "Relative blood volume (a.u.)")

    simple("02_tissue_transmission.png", result.tissue_transmission,
           f"Sensing-arm tissue transmission ({result.tissue_transmission.mean():.3f} mean)", "Transmission (fraction)")

    simple("03_detector_a_singles.png", result.signal_singles,
           f"Detector A (sensing) singles per {bin_ms:.0f} ms bin", "Counts / bin")
    simple("04_detector_b_singles.png", result.reference_singles,
           f"Detector B (reference) singles per {bin_ms:.0f} ms bin", "Counts / bin")

    layered("05_coincidences.png", result.coincidences,
            [("genuine", result.genuine_coincidences, "#2ca02c"),
             ("accidental", result.accidentals, "#d62728")],
            f"Coincidence counts per {bin_ms:.0f} ms bin", "Counts / bin")

    simple("06_quantum_raw.png", result.quantum_raw,
           "Raw quantum-correlated estimator:  -[ C / N_ref - <C / N_ref> ]",
           "Relative absorption (a.u.)")
    simple("07_quantum_filtered.png", result.quantum_filtered,
           "Filtered quantum-correlated PPG (bandpass 0.5-4 Hz, z-scored)",
           "Normalized amplitude (z)")

    simple("08_classical_filtered.png", result.classical_filtered,
           "Filtered classical singles PPG (bandpass 0.5-4 Hz, z-scored)",
           "Normalized amplitude (z)")

    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(t, result.quantum_filtered, color="#1f77b4", linewidth=1.6, label="quantum (coincidence-conditioned)")
    ax.plot(t, result.classical_filtered, color="#ff7f0e", linewidth=1.4, alpha=0.85, label="classical (sensing singles)")
    _styled(ax, "Quantum vs classical PPG (filtered, z-scored)", "Normalized amplitude (z)")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(directory / "09_ppg_comparison.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    labels = ["True", "Quantum", "Classical"]
    vals = [result.true_heart_rate_bpm, result.quantum_metrics.heart_rate_bpm, result.classical_metrics.heart_rate_bpm]
    colors = ["#2ca02c", "#1f77b4", "#ff7f0e"]
    bars = ax.bar(labels, vals, color=colors)
    for bar, v in zip(bars, vals):
        if v is not None:
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontsize=10)
    ax.set_title("Recovered heart-rate comparison", fontsize=12, fontweight="bold")
    ax.set_ylabel("Heart rate (BPM)", fontsize=10)
    ax.set_ylim(0, max(v for v in vals if v is not None) * 1.2 + 10)
    ax.grid(True, axis="y", alpha=0.3, linestyle="--")
    ax.tick_params(labelsize=10)
    fig.tight_layout()
    fig.savefig(directory / "10_heart_rate.png")
    plt.close(fig)

    if noise_results is not None and len(noise_results) > 0:
        probs = [r[0] for r in noise_results]
        q_snr = [r[1].snr_db for r in noise_results]
        c_snr = [r[2].snr_db for r in noise_results]
        q_corr = [r[1].correlation for r in noise_results]
        c_corr = [r[2].correlation for r in noise_results]

        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
        axes[0].plot(probs, q_snr, "o-", color="#1f77b4", linewidth=2, label="quantum")
        axes[0].plot(probs, c_snr, "s-", color="#ff7f0e", linewidth=2, label="classical")
        _styled(axes[0], "SNR vs background-click probability", "PPG SNR (dB)",
                xlabel="background prob. / detector / gate")
        axes[0].legend(loc="best", fontsize=10)

        axes[1].plot(probs, q_corr, "o-", color="#1f77b4", linewidth=2, label="quantum")
        axes[1].plot(probs, c_corr, "s-", color="#ff7f0e", linewidth=2, label="classical")
        _styled(axes[1], "Correlation with ground truth", "Correlation",
                xlabel="background prob. / detector / gate")
        axes[1].legend(loc="best", fontsize=10)
        axes[1].set_ylim(0, 1.0)

        fig.suptitle("Noise robustness: quantum coincidence conditioning vs classical singles",
                     fontsize=12, fontweight="bold")
        fig.tight_layout()
        fig.savefig(directory / "11_noise_robustness.png")
        plt.close(fig)

    return str(directory)
