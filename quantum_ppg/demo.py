"""Run: ./myenv/bin/python -m quantum_ppg.demo"""
from .system import QuantumPPGSystem
from .visualization import make_system_plots
from .experiment import background_noise_sweep


def _hr_str(metrics, truth):
    hr = metrics.heart_rate_bpm
    if hr is None:
        return "unavailable"
    return f"{hr:.1f} BPM (err {hr - truth:+.1f})"


def main():
    system = QuantumPPGSystem()
    result = system.run(10.0)
    c = system.config

    print("=" * 64)
    print("  ENTANGLED PHOTON-PAIR PPG DIGITAL TWIN — DEMO RUN")
    print("=" * 64)

    print("\n[SOURCE] SPDC entangled pair source")
    print(f"  Bell state          : (|HH> + |VV>) / sqrt(2)")
    print(f"  Pair prob. / pulse  : {c.source.pair_generation_probability}")
    print(f"  State fidelity      : {c.source.state_fidelity}")
    print(f"  Pump rate           : {c.pump_trials_per_second:,} trials / s")

    print("\n[BIOLOGY] Pulsatile blood-volume model")
    print(f"  Heart rate (truth)  : {c.blood.heart_rate_bpm:.1f} BPM")
    print(f"  Pulse amplitude     : {c.blood.pulse_amplitude}")
    print(f"  Optical path        : {c.tissue.optical_path_mm} mm @ {c.tissue.wavelength_nm} nm")

    print("\n[DETECTION] SPAD singles + coincidence timing")
    print(f"  Signal  singles     : {int(result.signal_singles.sum()):,}")
    print(f"  Reference singles   : {int(result.reference_singles.sum()):,}")
    print(f"  Coincidences (total): {int(result.coincidences.sum()):,}  (genuine {int(result.genuine_coincidences.sum()):,}, accidentals {int(result.accidentals.sum()):,})")
    print(f"  Detector efficiencies: sig={c.signal_detector.quantum_efficiency}, ref={c.reference_detector.quantum_efficiency}")
    print(f"  Coincidence window  : {c.source.coincidence_window_ns} ns")

    print("\n[PPG EXTRACTION] Quantum (C/N_ref) vs Classical (-N_A)")
    print(f"  True HR             : {c.blood.heart_rate_bpm:.1f} BPM")
    print(f"  Quantum  recovered  : {_hr_str(result.quantum_metrics, c.blood.heart_rate_bpm)}")
    print(f"  Classical recovered : {_hr_str(result.classical_metrics, c.blood.heart_rate_bpm)}")
    print(f"  Quantum  SNR        : {result.quantum_metrics.snr_db:5.2f} dB   | correlation: {result.quantum_metrics.correlation:+.3f}  | RMSE: {result.quantum_metrics.rmse:.3f}")
    print(f"  Classical SNR       : {result.classical_metrics.snr_db:5.2f} dB   | correlation: {result.classical_metrics.correlation:+.3f}  | RMSE: {result.classical_metrics.rmse:.3f}")

    print("\n[ARDUINO UNO TWIN] Hardware-in-the-loop interface")
    print(f"  D2 coincidence pulses: {result.arduino_coincidence_pulses:,}")
    print(f"  A0 rate-monitor samples: {result.arduino_adc_samples}")
    print(f"  Serial report        : {result.arduino_serial.strip()}")

    print("\n[NOISE SWEEP] Background-click probability per detector per gate")
    print("  Sweeping BOTH detectors: coincidence conditioning should reject")
    print("  uncorrelated background while classical singles cannot.")
    print("  Each point is averaged over 2 independent runs to reduce Monte-Carlo noise.\n")
    print(f"  {'bg_prob':>8} | {'quantum SNR':>11} {'class. SNR':>10} | {'q corr':>7} {'c corr':>7} | verdict")
    print(f"  {'-'*8}-+-{'-'*11}-{'-'*10}-+-{'-'*7}-{'-'*7}-+-{'-'*30}")
    sweep = background_noise_sweep(c, duration_seconds=8.0, repeats=2)
    for p, q, cl in sweep:
        if p == 0.0:
            verdict = "baseline"
        elif q.correlation > cl.correlation + 0.03:
            delta = q.snr_db - cl.snr_db
            verdict = f"QUANTUM +{delta:.1f} dB SNR" if delta > 0.5 else "QUANTUM advantage"
        elif cl.correlation > q.correlation + 0.03:
            verdict = "classical advantage"
        else:
            verdict = "comparable"
        print(f"  {p:>8.4f} | {q.snr_db:>+10.2f}  {cl.snr_db:>+9.2f}  | {q.correlation:>6.3f}  {cl.correlation:>6.3f}  | {verdict}")

    print("\n[PLOTS] Writing full-system figures to quantum_ppg_output/")
    out_dir = make_system_plots(result, noise_results=sweep)
    print(f"  -> {out_dir}/01_blood_volume.png")
    print(f"  -> {out_dir}/02_tissue_transmission.png")
    print(f"  -> {out_dir}/03_detector_a_singles.png")
    print(f"  -> {out_dir}/04_detector_b_singles.png")
    print(f"  -> {out_dir}/05_coincidences.png")
    print(f"  -> {out_dir}/06_quantum_raw.png")
    print(f"  -> {out_dir}/07_quantum_filtered.png")
    print(f"  -> {out_dir}/08_classical_filtered.png")
    print(f"  -> {out_dir}/09_ppg_comparison.png")
    print(f"  -> {out_dir}/10_heart_rate.png")
    print(f"  -> {out_dir}/11_noise_robustness.png")

    print("\n" + "=" * 64)
    print("  VERDICT")
    print("=" * 64)
    qs = result.quantum_metrics.snr_db
    cs = result.classical_metrics.snr_db
    advantage = "QUANTUM" if qs > cs else ("CLASSICAL" if cs > qs else "TIE")
    print(f"  At baseline noise: quantum SNR = {qs:.2f} dB, classical SNR = {cs:.2f} dB  -> {advantage}")
    print(f"  Heart rate recovered by both methods: {result.quantum_metrics.heart_rate_bpm:.1f} vs {result.classical_metrics.heart_rate_bpm:.1f} (truth {c.blood.heart_rate_bpm:.1f} BPM)")
    print("  See 11_noise_robustness.png for the core claim of the project:")
    print("  uncorrelated background degrades the classical singles arm while")
    print("  coincidence conditioning keeps the quantum-correlated signal stable.")
    print("=" * 64)


if __name__ == "__main__":
    main()
