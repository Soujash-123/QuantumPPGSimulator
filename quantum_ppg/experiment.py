"""Experiments for reproducible quantum-vs-classical robustness comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from .config import QuantumPPGConfig
from .system import QuantumPPGSystem
from signal_processing.metrics import PPGMetrics


def specialized_tunings(config: QuantumPPGConfig | None = None):
    """Return labeled, non-default operating regimes with stronger separation.

    These presets model ambient interference entering the sensing channel while
    the reference channel remains shielded. They are scenario studies, not
    general claims about all environments.
    """
    base = config or QuantumPPGConfig()
    sensing_background = lambda probability: replace(
        base.signal_detector,
        background_probability_per_gate=probability,
    )
    return {
        "sensing_ambient_20pct": replace(
            base,
            signal_detector=sensing_background(0.20),
        ),
        "sensing_ambient_40pct": replace(
            base,
            signal_detector=sensing_background(0.40),
        ),
        "sensing_ambient_40pct_narrow_gate": replace(
            base,
            source=replace(base.source, coincidence_window_ns=1.0),
            signal_detector=sensing_background(0.40),
        ),
    }


@dataclass(frozen=True)
class ParameterSweepPoint:
    """Metrics for one reproducible parameter-sweep point."""

    parameter: str
    value: float
    quantum: PPGMetrics
    classical: PPGMetrics

    @property
    def snr_delta_db(self) -> float:
        """Quantum SNR minus classical SNR for this point."""
        return self.quantum.snr_db - self.classical.snr_db


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


def robustness_parameter_sweep(
    config: QuantumPPGConfig,
    *,
    background_probabilities=(0.0, 0.01, 0.05, 0.1, 0.2),
    coincidence_windows_ns=(1.0, 2.0, 5.0, 10.0),
    detector_efficiencies=(0.5, 0.78, 0.9, 0.98),
    durations_seconds=(5.0, 10.0, 20.0),
    repeats: int = 3,
):
    """Compare active operating parameters without changing the baseline.

    The sweep is one-factor-at-a-time: each point starts from ``config`` and
    changes only the named parameter. Background and detector-efficiency values
    are applied symmetrically to both detectors. Repeated runs use deterministic
    seeds derived from ``config.seed`` and are averaged before being returned.
    """
    if repeats <= 0:
        raise ValueError("repeats must be positive")

    cases = []
    for value in background_probabilities:
        if not 0 <= value <= 1:
            raise ValueError("background probabilities must be in [0, 1]")
        signal = replace(config.signal_detector, background_probability_per_gate=value)
        reference = replace(config.reference_detector, background_probability_per_gate=value)
        cases.append(("background_probability_per_gate", float(value), replace(config, signal_detector=signal, reference_detector=reference), 10.0))

    for value in coincidence_windows_ns:
        if value < 0:
            raise ValueError("coincidence windows must be non-negative")
        source = replace(config.source, coincidence_window_ns=value)
        cases.append(("coincidence_window_ns", float(value), replace(config, source=source), 10.0))

    for value in detector_efficiencies:
        if not 0 <= value <= 1:
            raise ValueError("detector efficiencies must be in [0, 1]")
        signal = replace(config.signal_detector, quantum_efficiency=value)
        reference = replace(config.reference_detector, quantum_efficiency=value)
        cases.append(("detector_quantum_efficiency", float(value), replace(config, signal_detector=signal, reference_detector=reference), 10.0))

    for value in durations_seconds:
        if value <= 0:
            raise ValueError("durations must be positive")
        cases.append(("duration_seconds", float(value), config, float(value)))

    results = []
    for parameter, value, case_config, duration in cases:
        quantum_metrics = []
        classical_metrics = []
        for repeat in range(repeats):
            run_config = replace(case_config, seed=config.seed + repeat)
            result = QuantumPPGSystem(run_config).run(duration, drive_arduino=False)
            quantum_metrics.append(result.quantum_metrics)
            classical_metrics.append(result.classical_metrics)
        results.append(
            ParameterSweepPoint(
                parameter,
                value,
                _average_metrics(quantum_metrics),
                _average_metrics(classical_metrics),
            )
        )
    return results


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
