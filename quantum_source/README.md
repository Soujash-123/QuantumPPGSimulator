# SPDC entangled photon-pair source twin

This package models the chain **pump pulse → nonlinear crystal → possible SPDC
pair → signal/idler polarization analyzers → single-photon detector clicks →
time-window coincidence counter**. It is deliberately independent of the
Arduino and any PPG/tissue model.

`BellStateModel` is the quantum-mechanical effective model: when a pair is
created, its polarization is the two-qubit state `(HH + VV)/sqrt(2)` (or that
state mixed with white noise for configurable state fidelity). QuTiP constructs
the ket/density operator, partial traces, projector measurements and
expectation values. Qiskit Aer prepares the same Bell circuit and supplies
independent shot samples.

`SPDCSource` is phenomenological rather than microscopic nonlinear optics.
It treats pair creation, optical losses, detector efficiency, dark counts and
background clicks as configurable Bernoulli processes. Its parameters are
simulation assumptions, not specifications of any particular source.

Install the optional scientific backends with:

```bash
python3 -m pip install -r requirements-quantum-source.txt
```

Then run `./myenv/bin/python -m quantum_source.demo`; plots are written to
`quantum_source_output/`. The event dataclass and standalone coincidence
counter are the future interface for detector and biosensor modules.

## Arduino interface

The source is now connected through `arduino_connector.EntangledPhotonArduinoCircuit`.
It models detector/discriminator/coincidence electronics, then sends 5 V,
10-microsecond count pulses to Uno D2/INT0 (coincidences), D3/INT1 (signal
diagnostic), and D4 (idler diagnostic), with a filtered coincidence-rate value
on A0. This is a logical hardware interface, not an assertion that an Arduino
can detect photons or resolve nanosecond events itself. Run the integration
demo with `./myenv/bin/python -m quantum_source.arduino_demo`.
