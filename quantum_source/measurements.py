"""Measurement engines: QuTiP probability calculation and Aer shot sampling."""
from __future__ import annotations
import numpy as np
from .quantum_state import BellStateModel


def qutip_probabilities(model: BellStateModel, signal_angle: float, idler_angle: float) -> np.ndarray:
    """Born-rule probabilities evaluated through QuTiP projectors."""
    import qutip as qt
    rho = model.qutip_density()
    p = []
    for s in (0, 1):
        for i in (0, 1):
            ps = qt.Qobj(model.projector(signal_angle, s), dims=[[2], [2]])
            pi = qt.Qobj(model.projector(idler_angle, i), dims=[[2], [2]])
            p.append(float((rho * qt.tensor(ps, pi)).tr().real))
    return np.array(p).reshape(2, 2)


def aer_sample(signal_angle: float, idler_angle: float, shots: int, seed: int | None = None) -> dict[tuple[int, int], int]:
    """Prepare Phi+ with Qiskit and sample analyzer bases using Aer.

    RY(-2 theta) maps an analyzer at theta to a computational-basis measure.
    Qiskit's bit-string display is reversed, so counts are normalized to
    ``(signal, idler)`` tuple keys here.
    """
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    circuit = QuantumCircuit(2, 2)
    circuit.h(0); circuit.cx(0, 1)
    circuit.ry(-2*np.deg2rad(signal_angle), 0)
    circuit.ry(-2*np.deg2rad(idler_angle), 1)
    circuit.measure([0, 1], [0, 1])
    result = AerSimulator(seed_simulator=seed).run(circuit, shots=shots).result()
    normalized = {(0,0): 0, (0,1): 0, (1,0): 0, (1,1): 0}
    for bits, count in result.get_counts().items():
        idler, signal = (int(x) for x in bits.replace(" ", ""))
        normalized[(signal, idler)] += count
    return normalized


def correlation_from_counts(counts: dict[tuple[int, int], int]) -> float:
    total = sum(counts.values())
    return 0.0 if not total else sum((1 if s == i else -1)*n for (s, i), n in counts.items()) / total
