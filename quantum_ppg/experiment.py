"""Noise-sweep experiment: varies background-clicks and reports quantum-vs-classical robustness."""
from dataclasses import replace
from .config import QuantumPPGConfig
from .system import QuantumPPGSystem


def _average_metrics(metrics_list):
    """Mean of a list of PPGMetrics."""
    n = len(metrics_list)
    if n == 0:
        raise ValueError("metrics_list must be non-empty")
    from signal_processing.metrics import PPGMetrics
    return PPGMetrics(
        correlation=sum(m.correlation for m in metrics_list) / n,
        rmse=sum(m.rmse for m in metrics_list) / n,
        snr_db=sum(m.snr_db for m in metrics_list) / n,
        heart_rate_bpm=sum(m.heart_rate_bpm for m in metrics_list) / n,
    )


def background_noise_sweep(
    config: QuantumPPGConfig,
    probabilities=(0.0, 0.002, 0.01, 0.05, 0.1, 0.2),
    duration_seconds: float = 8.0,
    sweep_both_detectors: bool = True,
    repeats: int = 1,
):
    """Run the system at each background-clicks-per-gate probability.

    Parameters
    ----------
    config : QuantumPPGConfig
        Baseline configuration. The seed and other settings are preserved.
    probabilities : sequence of float
        Per-gate background-click probability to inject.
    duration_seconds : float
        Run length for each measurement; longer gives more stable metrics.
    sweep_both_detectors : bool
        If True (default), the same per-gate background rate is applied to
        signal AND reference detectors — the realistic case where ambient
        light / dark counts are seen by both arms. The quantum extractor
        rejects most of this through coincidence matching while the
        classical singles estimator does not.
    repeats : int
        Number of independent runs to average per probability point.
        Each repeat uses a different seed (derived from the base seed),
        so ``repeats > 1`` reduces Monte-Carlo noise at the cost of runtime.
    """
    results = []
    for probability in probabilities:
        signal = replace(config.signal_detector, background_probability_per_gate=probability)
        kwargs = {"signal_detector": signal}
        if sweep_both_detectors:
            reference = replace(config.reference_detector, background_probability_per_gate=probability)
            kwargs["reference_detector"] = reference
        q_list, c_list = [], []
        for rep in range(repeats):
            cfg = replace(config, seed=config.seed + rep, **kwargs) if repeats > 1 else replace(config, **kwargs)
            result = QuantumPPGSystem(cfg).run(duration_seconds, drive_arduino=False)
            q_list.append(result.quantum_metrics)
            c_list.append(result.classical_metrics)
        results.append((probability, _average_metrics(q_list), _average_metrics(c_list)))
    return results
