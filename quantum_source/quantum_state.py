"""Quantum polarization state model.

This is an effective two-qubit model of polarization after SPDC pair creation,
not a microscopic nonlinear-optics simulation of a crystal and pump field.
"""
from __future__ import annotations
import numpy as np


class BellStateModel:
    """|Phi+>=(|HH>+|VV>)/sqrt(2), represented with QuTiP when installed."""
    def __init__(self, fidelity: float = 1.0):
        if not 0 <= fidelity <= 1:
            raise ValueError("fidelity must be in [0, 1]")
        self.fidelity = fidelity

    @property
    def ket_numpy(self):
        return np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)

    @property
    def density_numpy(self):
        pure = np.outer(self.ket_numpy, self.ket_numpy.conj())
        return self.fidelity * pure + (1 - self.fidelity) * np.eye(4) / 4

    def qutip_ket(self):
        import qutip as qt
        return (qt.tensor(qt.basis(2, 0), qt.basis(2, 0)) + qt.tensor(qt.basis(2, 1), qt.basis(2, 1))).unit()

    def qutip_density(self):
        import qutip as qt
        ket = self.qutip_ket()
        return self.fidelity * qt.ket2dm(ket) + (1-self.fidelity) * qt.qeye([2, 2]) / 4

    @staticmethod
    def projector(angle_deg: float, outcome: int) -> np.ndarray:
        """Linear-polarization analyzer projector; 0=transmitted, 1=orthogonal."""
        theta = np.deg2rad(angle_deg + (90 if outcome else 0))
        vector = np.array([np.cos(theta), np.sin(theta)], complex)
        return np.outer(vector, vector.conj())

    def probabilities(self, signal_angle: float, idler_angle: float) -> np.ndarray:
        rho = self.density_numpy
        return np.array([np.real(np.trace(rho @ np.kron(self.projector(signal_angle, s), self.projector(idler_angle, i))))
                         for s in (0, 1) for i in (0, 1)]).reshape(2, 2)

    def metrics(self) -> dict:
        rho = self.density_numpy
        reduced_s = np.trace(rho.reshape(2,2,2,2), axis1=1, axis2=3)
        reduced_i = np.trace(rho.reshape(2,2,2,2), axis1=0, axis2=2)
        # Wootters concurrence for this Bell state mixed with white noise.
        concurrence = max(0.0, (3*self.fidelity - 1)/2)
        zz = np.diag([1, -1])
        correlation_hv = float(np.real(np.trace(rho @ np.kron(zz, zz))))
        return {"normalization": float(np.trace(rho).real), "purity": float(np.trace(rho @ rho).real),
                "concurrence": concurrence, "correlation_hv": correlation_hv,
                "reduced_signal": reduced_s, "reduced_idler": reduced_i}

    def qutip_metrics(self) -> dict:
        """QuTiP-native state checks: density operator, partial traces and <Z⊗Z>."""
        import qutip as qt
        rho = self.qutip_density()
        z = qt.sigmaz()
        return {"normalization": float(rho.tr().real), "purity": float((rho*rho).tr().real),
                "reduced_signal": rho.ptrace(0), "reduced_idler": rho.ptrace(1),
                "correlation_hv": float(qt.expect(qt.tensor(z, z), rho).real)}
