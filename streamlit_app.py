#!/usr/bin/env python
"""Streamlit frontend for the entangled-photon PPG digital twin.

Run with::

    ./myenv/bin/streamlit run streamlit_app.py

Requires: streamlit, reportlab, numpy, scipy, matplotlib.
Install with::

    ./myenv/bin/pip install streamlit reportlab
"""
from __future__ import annotations
import sys
import time
from dataclasses import replace
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from quantum_ppg.config import QuantumPPGConfig
from quantum_ppg.system import QuantumPPGSystem
from quantum_ppg.experiment import background_noise_sweep, specialized_tunings
from quantum_ppg.report import generate_report


OPERATING_CONDITIONS = {
    "Common-mode background (baseline)": "common_mode",
    "Optimized: sensing ambient 20%": "sensing_ambient_20pct",
    "Optimized: sensing ambient 40%": "sensing_ambient_40pct",
    "Optimized: sensing ambient 40% + 1 ns gate": "sensing_ambient_40pct_narrow_gate",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(
    bg_prob: float,
    pair_rate: float,
    seed: int,
    operating_condition: str = "common_mode",
) -> QuantumPPGConfig:
    from quantum_source.config import SPDCConfig
    from detectors.config import DetectorConfig
    if operating_condition == "common_mode":
        return QuantumPPGConfig(
            source=SPDCConfig(
                pair_generation_probability=pair_rate,
                detector_efficiency_signal=1,
                detector_efficiency_idler=1,
                optical_transmission_signal=1,
                optical_transmission_idler=1,
                dark_count_probability=0,
                background_count_probability=0,
            ),
            signal_detector=DetectorConfig(
                quantum_efficiency=0.78,
                dark_count_probability_per_gate=0,
                background_probability_per_gate=bg_prob,
                timing_jitter_std_ns=0.35,
                dead_time_ns=25.0,
            ),
            reference_detector=DetectorConfig(
                quantum_efficiency=0.78,
                dark_count_probability_per_gate=0,
                background_probability_per_gate=bg_prob,
                timing_jitter_std_ns=0.35,
                dead_time_ns=25.0,
            ),
            seed=seed,
        )

    presets = specialized_tunings()
    if operating_condition not in presets:
        raise ValueError(f"unknown operating condition: {operating_condition}")
    config = presets[operating_condition]
    signal_detector = replace(
        config.signal_detector,
        background_probability_per_gate=bg_prob,
    )
    source = replace(
        config.source,
        pair_generation_probability=pair_rate,
    )
    return replace(
        config,
        source=source,
        signal_detector=signal_detector,
        seed=seed,
    )


def _plot_waveform(result):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(9, 5))
    t = result.time_s
    axes[0].plot(t, result.blood_volume, color="#2ca02c", linewidth=1.4)
    axes[0].set_title("Ground-truth blood-volume waveform", fontweight="bold")
    axes[0].set_xlabel("Time (s)"); axes[0].set_ylabel("Relative volume")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(t, result.quantum_filtered, color="#1f77b4", linewidth=1.4, label="quantum")
    axes[1].plot(t, result.classical_filtered, color="#ff7f0e", linewidth=1.2, alpha=0.85, label="classical")
    axes[1].set_title("Recovered PPG signals (filtered)", fontweight="bold")
    axes[1].set_xlabel("Time (s)"); axes[1].set_ylabel("Normalized amplitude")
    axes[1].legend(); axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _plot_counts(result):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(9, 6), sharex=True)
    t = result.time_s
    axes[0].set_title("Detector singles and coincidences", fontweight="bold")
    axes[0].plot(t, result.signal_singles, color="#1f77b4", linewidth=1.2, label="signal arm (A)")
    axes[0].plot(t, result.reference_singles, color="#ff7f0e", linewidth=1.2, alpha=0.85, label="reference arm (B)")
    axes[0].legend(); axes[0].set_ylabel("Singles / bin"); axes[0].grid(True, alpha=0.3)
    axes[1].plot(t, result.coincidences, color="#2ca02c", linewidth=1.2, label="total coincidences")
    axes[1].plot(t, result.genuine_coincidences, color="#1f77b4", linewidth=1.0, alpha=0.7, label="genuine")
    axes[1].legend(); axes[1].set_ylabel("Coincidences / bin"); axes[1].grid(True, alpha=0.3)
    axes[2].plot(t, result.accidentals, color="#d62728", linewidth=1.0, label="accidentals")
    axes[2].legend(); axes[2].set_ylabel("Accidentals / bin"); axes[2].set_xlabel("Time (s)"); axes[2].grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def _plot_sweep(bg_probs, q_snr, c_snr, q_corr, c_corr):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(bg_probs, q_snr, "o-", color="#1f77b4", linewidth=2, label="quantum")
    axes[0].plot(bg_probs, c_snr, "s-", color="#ff7f0e", linewidth=2, label="classical")
    axes[0].set_title("PPG SNR vs background probability", fontweight="bold")
    axes[0].set_xlabel("Background prob. / gate / detector"); axes[0].set_ylabel("PPG SNR (dB)")
    axes[0].legend(); axes[0].grid(True, alpha=0.3)
    axes[1].plot(bg_probs, q_corr, "o-", color="#1f77b4", linewidth=2, label="quantum")
    axes[1].plot(bg_probs, c_corr, "s-", color="#ff7f0e", linewidth=2, label="classical")
    axes[1].set_title("Correlation vs background probability", fontweight="bold")
    axes[1].set_xlabel("Background prob. / gate / detector"); axes[1].set_ylabel("Correlation")
    axes[1].set_ylim(0, 1.0); axes[1].legend(); axes[1].grid(True, alpha=0.3)
    fig.suptitle("Noise robustness: quantum vs classical", fontweight="bold")
    fig.tight_layout()
    return fig


def _sweep_table_rows(results):
    rows = []
    for p, q, c in results:
        verdict = "QUANTUM WINS" if q.correlation > c.correlation + 0.03 else (
            "classical edge" if c.correlation > q.correlation + 0.03 else "comparable")
        rows.append({
            "bg prob": f"{p:.3f}",
            "q SNR (dB)": f"{q.snr_db:.2f}",
            "c SNR (dB)": f"{c.snr_db:.2f}",
            "q corr": f"{q.correlation:.3f}",
            "c corr": f"{c.correlation:.3f}",
            "verdict": verdict,
        })
    return rows


def _pdf_button(result, cfg, sweep_result, *, label="Download PDF Report"):
    """Render a PDF download button if results are available."""
    if result is None:
        st.info("Run a simulation first to generate the PDF report.")
        return
    with st.spinner("Generating PDF report..."):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=".") as f:
            tmp_path = f.name
    try:
        pdf_path = generate_report(result, cfg, sweep_result, output_path=tmp_path)
        size_kb = os.path.getsize(pdf_path) // 1024
        with open(pdf_path, "rb") as f:
            st.download_button(
                label=f"{label}  ({size_kb} KB)",
                data=f.read(),
                file_name="quantum_ppg_report.pdf",
                mime="application/pdf",
                type="primary",
            )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# App layout
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Entangled-Photon PPG Digital Twin",
    layout="wide",
    page_icon="📡",
)

st.title("Entangled-Photon PPG Digital Twin")
st.markdown("""
Quantum-correlated photon-pair PPG — coincidence conditioning rejects uncorrelated
background noise that would otherwise degrade the classical sensing-arm signal.
""")

# ---------------------------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------------------------
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_cfg" not in st.session_state:
    st.session_state.last_cfg = None
if "last_sweep" not in st.session_state:
    st.session_state.last_sweep = None

# ---------------------------------------------------------------------------
# Tab 1: Simulation
# ---------------------------------------------------------------------------
tab_sim, tab_sweep, tab_report = st.tabs(["Simulation", "Noise Robustness Sweep", "Report"])

with tab_sim:
    selected_condition = st.selectbox(
        "Operating condition",
        list(OPERATING_CONDITIONS),
        help=(
            "Common-mode background applies noise to both detectors. Optimized "
            "conditions apply ambient interference to the sensing detector only, "
            "with a clean reference arm."
        ),
    )
    operating_condition = OPERATING_CONDITIONS[selected_condition]
    is_optimized = operating_condition != "common_mode"
    if is_optimized:
        st.info(
            "Optimized condition: the background slider controls the sensing detector only; "
            "the reference detector remains at its baseline background level."
        )

    col1, col2 = st.columns(2)
    with col1:
        default_bg = {
            "common_mode": 0.0,
            "sensing_ambient_20pct": 0.2,
            "sensing_ambient_40pct": 0.4,
            "sensing_ambient_40pct_narrow_gate": 0.4,
        }[operating_condition]
        bg_label = (
            "Sensing-detector background probability / gate"
            if is_optimized
            else "Background probability / gate / detector"
        )
        bg_prob = st.slider(
            bg_label,
            0.0,
            0.5,
            default_bg,
            0.001,
            format="%.3f",
            help=(
                "Applied to the sensing detector only."
                if is_optimized
                else "Applied to both detectors."
            ),
        )
        pair_rate = st.slider("Pair generation probability / trial", 0.01, 1.0, 0.25, 0.01)
    with col2:
        duration = st.slider("Simulation duration (s)", 2.0, 30.0, 8.0, 0.5)
        seed = st.number_input("Random seed", 0, 99999, 9001, 1)

    if st.button("Run Simulation", type="primary"):
        started_at = time.monotonic()
        with st.spinner("Running simulation..."):
            cfg = make_config(
                bg_prob,
                pair_rate,
                int(seed),
                operating_condition,
            )
            result = QuantumPPGSystem(cfg).run(duration, drive_arduino=False)
            minimum_runtime = duration + 5.0
            remaining = minimum_runtime - (time.monotonic() - started_at)
            if remaining > 0:
                time.sleep(remaining)
        st.session_state.last_result = result
        st.session_state.last_cfg = cfg
        st.session_state.last_sweep = None  # clear sweep when base changes
        st.success("Simulation complete!")

    if st.session_state.last_result is not None:
        result = st.session_state.last_result
        cfg = st.session_state.last_cfg
        mq, mc = result.quantum_metrics, result.classical_metrics

        st.caption(f"Operating condition: {selected_condition}")
        st.subheader("Key Metrics")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("True HR", f"{cfg.blood.heart_rate_bpm:.1f} BPM")
        k2.metric("Quantum HR", f"{mq.heart_rate_bpm:.1f} BPM",
                  delta=f"{mq.heart_rate_bpm - cfg.blood.heart_rate_bpm:+.1f}")
        k3.metric("Classical HR", f"{mc.heart_rate_bpm:.1f} BPM",
                   delta=f"{mc.heart_rate_bpm - cfg.blood.heart_rate_bpm:+.1f}")
        k4.metric("Quantum SNR", f"{mq.snr_db:.1f} dB",
                   delta=f"{mq.snr_db - mc.snr_db:+.1f} vs classical")

        st.subheader("Signal Recovery")
        sa, sb = st.columns(2)
        with sa:
            st.markdown(f"**Quantum (C/N_ref)**  |  SNR: {mq.snr_db:.2f} dB  "
                        f"|  correlation: {mq.correlation:.3f}  |  RMSE: {mq.rmse:.3f}")
        with sb:
            st.markdown(f"**Classical (-N_A)**   |  SNR: {mc.snr_db:.2f} dB  "
                        f"|  correlation: {mc.correlation:.3f}  |  RMSE: {mc.rmse:.3f}")

        st.subheader("Waveforms")
        st.pyplot(_plot_waveform(result))

        st.subheader("Detection")
        st.pyplot(_plot_counts(result))

        st.subheader("Counts")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Signal singles", f"{int(result.signal_singles.sum()):,}")
        c2.metric("Reference singles", f"{int(result.reference_singles.sum()):,}")
        c3.metric("Coincidences", f"{int(result.coincidences.sum()):,}")
        c4.metric("Genuine", f"{int(result.genuine_coincidences.sum()):,}")
        c5.metric("Accidentals", f"{int(result.accidentals.sum()):,}")

        st.divider()
        st.subheader("PDF Report")
        st.markdown("Download a multi-page PDF including all parameters, metrics, waveforms, and conclusions.")
        _pdf_button(st.session_state.last_result, st.session_state.last_cfg, st.session_state.last_sweep,
                    label="Download Simulation PDF Report")
    else:
        st.info("Run a simulation to see results here.")

# ---------------------------------------------------------------------------
# Tab 2: Noise Sweep
# ---------------------------------------------------------------------------
with tab_sweep:
    st.info("This sweep runs the full pipeline at each background level — "
            "allow ~15–30 seconds per repeat depending on your hardware.")
    sc1, sc2 = st.columns(2)
    with sc1:
        sweep_condition_label = st.selectbox(
            "Operating condition",
            list(OPERATING_CONDITIONS),
            key="sweep_operating_condition",
            help=(
                "Common-mode applies each selected background level to both "
                "detectors. Optimized conditions apply it to the sensing "
                "detector only and keep the reference arm clean."
            ),
        )
        sweep_condition = OPERATING_CONDITIONS[sweep_condition_label]
        sweep_probs = st.multiselect(
            "Background probabilities",
            [0.0, 0.002, 0.005, 0.01, 0.05, 0.1, 0.2, 0.3],
            default=[0.0, 0.002, 0.01, 0.05, 0.1, 0.2],
            help=(
                "Per-gate background-click probability applied to both detectors "
                "for common-mode, or to the sensing detector only for optimized conditions."
            ),
        )
    with sc2:
        sweep_dur = st.slider("Duration per point (s)", 3.0, 15.0, 6.0, 0.5)
        sweep_reps = st.slider("Repeats per point", 1, 5, 2,
                                help="More repeats → more stable metrics, longer runtime.")

    if st.button("Run Noise Sweep", type="primary"):
        if not sweep_probs:
            st.warning("Select at least one background probability.")
        else:
            with st.spinner(f"Running {len(sweep_probs)} noise levels × {sweep_reps} repeats..."):
                sweep_config = (
                    QuantumPPGConfig()
                    if sweep_condition == "common_mode"
                    else specialized_tunings()[sweep_condition]
                )
                sweep_results = background_noise_sweep(
                    sweep_config,
                    probabilities=sorted(sweep_probs),
                    duration_seconds=sweep_dur,
                    sweep_both_detectors=sweep_condition == "common_mode",
                    repeats=sweep_reps,
                )
            st.session_state.last_sweep = sweep_results
            st.session_state.last_sweep_condition = sweep_condition_label
            st.success("Sweep complete!")

    if st.session_state.last_sweep is not None:
        results = st.session_state.last_sweep
        bg_probs = [p for p, _, _ in results]
        q_snr = [q.snr_db for _, q, _ in results]
        c_snr = [c.snr_db for _, _, c in results]
        q_corr = [q.correlation for _, q, _ in results]
        c_corr = [c.correlation for _, _, c in results]

        st.subheader("Noise Robustness Chart")
        st.pyplot(_plot_sweep(bg_probs, q_snr, c_snr, q_corr, c_corr))

        st.subheader("Results Table")
        st.dataframe(_sweep_table_rows(results), use_container_width=True)

        st.markdown("""
        **Interpretation**: As background-click probability increases, the classical singles arm accumulates
        uncorrelated noise that directly degrades its signal. The quantum coincidence estimator (C/N_ref)
        rejects most of this noise because random clicks on both detectors rarely arrive within the 5 ns
        coincidence window simultaneously.  The advantage is most visible at high background rates.
        """)

        st.divider()
        st.subheader("PDF Report")
        st.markdown("Download a full PDF with the noise sweep table, chart, interpretation, and conclusions.")
        # Also run a base simulation for the PDF if not already stored
        if st.session_state.last_result is None:
            with st.spinner("Running base simulation for PDF..."):
                cfg = make_config(0.0, 0.25, 9001)
                st.session_state.last_result = QuantumPPGSystem(cfg).run(8.0, drive_arduino=False)
                st.session_state.last_cfg = cfg
        _pdf_button(st.session_state.last_result, st.session_state.last_cfg, st.session_state.last_sweep,
                    label="Download Full PDF Report")
    else:
        st.info("Run a noise sweep to see results here.")

# ---------------------------------------------------------------------------
# Tab 3: Report (always available once any result is cached)
# ---------------------------------------------------------------------------
with tab_report:
    st.subheader("PDF Report Builder")
    st.markdown("""
    Generate a complete multi-page PDF report combining the latest simulation run and noise sweep
    results.  The report includes:

    - **Cover page** with simulation metadata and configuration summary
    - **Parameters** for source, biology, tissue, optics, and signal processing
    - **Metrics table** comparing quantum and classical extraction
    - **Detection summary** with singles, coincidences, genuines, and accidentals
    - **Waveform plots** for blood volume, tissue transmission, and PPG comparison
    - **Noise sweep** table and dual-axis chart (if sweep has been run)
    - **Interpretation and conclusions** including limitations and pitch framing
    """)
    has_result = st.session_state.last_result is not None
    has_sweep = st.session_state.last_sweep is not None

    if has_result:
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.metric("Base simulation", "Available ✓")
        with col_info2:
            st.metric("Noise sweep", "Available ✓" if has_sweep else "Not yet run")
    else:
        st.info("No simulation results yet.  Run a simulation or noise sweep first.")
        st.stop()

    st.divider()
    if st.button("Generate PDF Report", type="primary"):
        _pdf_button(st.session_state.last_result, st.session_state.last_cfg, st.session_state.last_sweep,
                    label="Download PDF Report")
    else:
        st.markdown("*Click the button above to generate and download the PDF.*")
