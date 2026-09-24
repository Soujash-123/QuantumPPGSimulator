# Project Description

## Overview

This project is a Python digital twin for an entangled-photon PPG (photoplethysmography)
system. It models the complete simulated chain:

1. A pulsatile blood-volume waveform is generated.
2. Fingertip tissue converts blood volume into optical transmission.
3. Entangled signal/idler photons are propagated through sensing and reference arms.
4. SPAD/APD-like detectors produce timestamped clicks, including loss, jitter, dead time,
   dark counts, and background noise.
5. External timing electronics match signal/reference clicks into coincidences.
6. Quantum-correlated and classical PPG signals are filtered and evaluated.
7. An Arduino Uno software twin receives conditioned 5 V pulse and analog-monitor inputs.
8. Demos generate console summaries and PNG plots.

The quantum model is an effective Bell-state model, not a microscopic nonlinear-optics
or semiconductor-physics simulation. Configuration values are simulation assumptions.

## Source files

### Arduino and hardware bridge

- [`arduino.py`](./arduino.py) — Self-contained Arduino Uno R3 software twin. It exposes
  Arduino-style constants and APIs such as `pinMode`, `digitalWrite`, `digitalRead`,
  `analogRead`, `analogWrite`, `attachInterrupt`, timing functions, reset, pin metadata,
  and an in-memory `SerialPort`. It supports virtual time and optional realtime delays.
  `run_sketch` can execute a Python sketch against a simulated board.
- [`arduino_connector.py`](./arduino_connector.py) — Electrical interface between the
  photon source and the Uno twin. `PhotonCircuitConfig` validates the 5 V wiring,
  pulse width, pins, and ADC scaling. `EntangledPhotonArduinoCircuit` converts detector
  singles and coincidence counts into stretched pulses on D2/D3/D4 and a rate value on A0.
  `ArduinoPhotonRun` stores run totals.

### `biosensor/`

- [`biosensor/__init__.py`](./biosensor/__init__.py) — Public exports for physiological
  configuration, blood-volume, and fingertip-tissue models.
- [`biosensor/config.py`](./biosensor/config.py) — Immutable `BloodVolumeConfig` and
  `TissueConfig` dataclasses. They define heart-rate/waveform parameters, optical
  absorption/scattering, path length, wavelength, and optional decoherence.
- [`biosensor/blood_volume.py`](./biosensor/blood_volume.py) — `BloodVolumeModel`, an
  analytic pulsatile waveform with asymmetric systolic rise, diastolic decay, dicrotic
  notch, respiratory modulation, drift, and optional physiological noise.
- [`biosensor/tissue.py`](./biosensor/tissue.py) — `FingertipTissue`, an effective
  modified Beer-Lambert model mapping blood volume to attenuation and transmission.
- [`biosensor/optical_interaction.py`](./biosensor/optical_interaction.py) — Small
  compatibility/helper interface exposing tissue transmission as `sensing_transmission`.
- [`biosensor/ppg_model.py`](./biosensor/ppg_model.py) — Compatibility module that
  re-exports `BloodVolumeModel`.

### `optical_path/`

- [`optical_path/__init__.py`](./optical_path/__init__.py) — Public exports for optical
  path configuration and sensing/reference arms.
- [`optical_path/config.py`](./optical_path/config.py) — Immutable `OpticalPathConfig`
  containing static transmission, propagation delay, background probability, and
  polarization-decoherence probability.
- [`optical_path/losses.py`](./optical_path/losses.py) — `survives`, a Bernoulli survival
  test for path transmission.
- [`optical_path/photon_path.py`](./optical_path/photon_path.py) — `PropagatedPhoton`
  dataclass containing parent event, arm, timestamp, polarization, survival, and pair
  provenance.
- [`optical_path/sensing_arm.py`](./optical_path/sensing_arm.py) — `SensingArm`, which
  applies static loss multiplied by pulsatile tissue transmission and adds propagation
  delay/decoherence.
- [`optical_path/reference_arm.py`](./optical_path/reference_arm.py) — `ReferenceArm`,
  which applies independent static loss and delay without tissue interaction.

### `detectors/`

- [`detectors/__init__.py`](./detectors/__init__.py) — Public detector and timing exports.
- [`detectors/config.py`](./detectors/config.py) — Immutable `DetectorConfig` for quantum
  efficiency, noise probabilities, timing jitter, and detector dead time.
- [`detectors/detector_event.py`](./detectors/detector_event.py) — `DetectionEvent`
  dataclass describing detector identity, timestamp, source event, polarization, and
  genuine/noise classification.
- [`detectors/spad.py`](./detectors/spad.py) — `SPADDetector`, an event-level detector
  approximation that applies efficiency, noise, jitter, and causal dead-time rejection.
- [`detectors/timing.py`](./detectors/timing.py) — `CoincidenceProcessor` and
  `BinnedCoincidenceStats`. It sorts timestamped signal/reference events, performs
  one-to-one matching within a nanosecond window, and separates genuine coincidences
  from accidentals.

### `quantum_source/`

- [`quantum_source/__init__.py`](./quantum_source/__init__.py) — Public exports for the
  SPDC configuration, source, event type, and Bell-state model.
- [`quantum_source/README.md`](./quantum_source/README.md) — Package-specific usage notes,
  model boundaries, optional backend installation, demo commands, and Arduino wiring.
- [`quantum_source/config.py`](./quantum_source/config.py) — Immutable `SPDCConfig` for
  pair generation, optical/detector efficiencies, noise, state fidelity, timing, and seed.
- [`quantum_source/quantum_state.py`](./quantum_source/quantum_state.py) — `BellStateModel`
  for the effective `(|HH> + |VV>)/sqrt(2)` state, optional white-noise mixing, analyzer
  projectors, Born-rule probabilities, density matrices, concurrence, purity, reduced
  states, and H/V correlation. QuTiP-native checks are provided when installed.
- [`quantum_source/spdc_source.py`](./quantum_source/spdc_source.py) — `SPDCSource` and
  `PhotonEvent`. Pair creation, measurement outcomes, optical loss, detector efficiency,
  dark/background clicks, timestamps, and per-event coincidence flags are sampled here.
- [`quantum_source/coincidence.py`](./quantum_source/coincidence.py) — Standalone
  `count_coincidences` function and `CoincidenceStats` dataclass for timestamp-window
  matching independent of the detector package.
- [`quantum_source/measurements.py`](./quantum_source/measurements.py) — Optional
  QuTiP Born-rule probability evaluation and Qiskit Aer Bell-circuit shot sampling.
  Results are normalized to `(signal, idler)` keys; correlations can be calculated from
  counts.
- [`quantum_source/visualization.py`](./quantum_source/visualization.py) — Noninteractive
  Matplotlib plots for state probabilities, measurement statistics, polarization
  correlations, and coincidence counts.
- [`quantum_source/demo.py`](./quantum_source/demo.py) — Standalone source demo that runs
  events, prints source/state metrics, optionally compares QuTiP with Aer, and writes plots.
- [`quantum_source/arduino_demo.py`](./quantum_source/arduino_demo.py) — Demonstrates
  source-to-Uno conditioning, D2 interrupt counting, diagnostic singles, and A0 monitoring.
- [`quantum_source/tests/test_source.py`](./quantum_source/tests/test_source.py) —
  Unit tests for Bell-state metrics, probabilities, noise behavior, pair rates, detector
  effects, and optional QuTiP/Aer agreement.
- [`quantum_source/tests/test_arduino_connector.py`](./quantum_source/tests/test_arduino_connector.py) —
  Verifies conditioned coincidence pulses, D2 interrupts, diagnostics, and ADC scaling.

### `signal_processing/`

- [`signal_processing/__init__.py`](./signal_processing/__init__.py) — Public exports for
  processing configuration, estimators, and PPG metrics.
- [`signal_processing/config.py`](./signal_processing/config.py) — Immutable
  `ProcessingConfig` for bin width, band-pass limits, causal filtering, and normalization.
- [`signal_processing/filters.py`](./signal_processing/filters.py) — Butterworth
  band-pass filtering (causal or zero-phase) and z-score normalization.
- [`signal_processing/quantum_ppg.py`](./signal_processing/quantum_ppg.py) —
  `QuantumPPGExtractor`, using reference-normalized coincidences (`-C/N_reference`) as
  the quantum-correlated absorption estimate.
- [`signal_processing/classical_ppg.py`](./signal_processing/classical_ppg.py) —
  `ClassicalPPGExtractor`, using normalized negative sensing-arm singles as a control
  estimator.
- [`signal_processing/metrics.py`](./signal_processing/metrics.py) — `PPGMetrics`,
  heart-rate estimation via a periodogram, and `evaluate_ppg` for correlation, RMSE,
  SNR, and recovered heart rate.

### `quantum_ppg/`

- [`quantum_ppg/__init__.py`](./quantum_ppg/__init__.py) — Public exports for the full
  system configuration, orchestrator, and result dataclass.
- [`quantum_ppg/config.py`](./quantum_ppg/config.py) — `QuantumPPGConfig`, composing
  source, physiology, tissue, optical paths, detectors, processing, pump rate, and seed.
- [`quantum_ppg/system.py`](./quantum_ppg/system.py) — `QuantumPPGSystem`, the main
  chronological orchestrator. It creates time bins, generates gates/pairs, propagates
  photons, detects events, performs coincidence conditioning, drives the Arduino twin,
  extracts both PPG signals, evaluates metrics, and returns `QuantumPPGResult`.
- [`quantum_ppg/experiment.py`](./quantum_ppg/experiment.py) — Runs configurable
  background-noise and one-factor-at-a-time robustness sweeps for detector
  background, coincidence window, detector efficiency, and run duration. It
  also provides labeled specialized tuning presets for sensing-arm ambient
  interference studies; these presets do not change the baseline defaults.
- [`quantum_ppg/arduino_sketch.py`](./quantum_ppg/arduino_sketch.py) — Arduino-style
  acquisition sketch. It attaches D2/D3 rising-edge interrupts, samples A0, estimates
  heart rate from captured samples, and writes a serial report.
- [`quantum_ppg/visualization.py`](./quantum_ppg/visualization.py) — Generates full-system
  PNG plots for physiology, transmission, singles, coincidences, quantum/classical PPG,
  heart-rate comparison, and optional noise robustness.
- [`quantum_ppg/demo.py`](./quantum_ppg/demo.py) — End-to-end executable demo. It runs
  the system, prints source/biology/detection/PPG/Arduino summaries, performs a noise
  sweep, and creates the full plot set.
- [`quantum_ppg/tests/__init__.py`](./quantum_ppg/tests/__init__.py) — Test package marker.
- [`quantum_ppg/tests/test_full_system.py`](./quantum_ppg/tests/test_full_system.py) —
  End-to-end tests for tissue behavior, path-loss effects, reference-arm independence,
  zero-pair/zero-efficiency behavior, heart-rate recovery, Arduino acquisition, and
  noise robustness.

## Dependencies and runtime directories

- [`requirements-quantum-source.txt`](./requirements-quantum-source.txt) — Optional
  scientific dependencies: Qiskit, Qiskit Aer, QuTiP, NumPy, SciPy, and Matplotlib.
- [`myenv/`](./myenv/) — Local Python virtual environment containing installed packages.
  It is runtime infrastructure, not project source, and should not be documented file by
  file or committed as application code.
- [`__pycache__/`](./__pycache__/) and package-level `__pycache__/` directories — Generated
  Python bytecode caches.
- [`.mplconfig/`](./.mplconfig/) — Matplotlib runtime cache/configuration data.
- [`qutip_coeffs_1.1/`](./qutip_coeffs_1.1/) — Runtime/library coefficient directory;
  it is not an authored application module.

## Generated outputs

- [`quantum_source_output/`](./quantum_source_output/) — PNGs produced by the source demo:
  state probabilities, measurement statistics, polarization correlation comparison, and
  coincidence counts.
- [`quantum_ppg_output/`](./quantum_ppg_output/) — PNGs produced by the full demo:
  blood volume, tissue transmission, detector singles, coincidences, raw/filtered
  quantum PPG, filtered classical PPG, comparison, heart rate, and noise robustness.

## Typical commands

```bash
./myenv/bin/python -m quantum_source.demo
./myenv/bin/python -m quantum_source.arduino_demo
./myenv/bin/python -m quantum_ppg.demo
```

The test modules can be run with Python's unittest discovery or the project's configured
test runner.
