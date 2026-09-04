"""Chronological full-system simulation using an event-driven ns/ms/sec clock.

Each 20-ms PPG bin contains random pump gates. Individual generated pairs and
detector clicks have ns timestamps; coincidence matching occurs per bin before
the bin counts reach signal processing or the Arduino interface.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from arduino import ArduinoUno
from arduino_connector import EntangledPhotonArduinoCircuit
from quantum_source import SPDCSource, PhotonEvent
from biosensor import BloodVolumeModel, FingertipTissue
from optical_path import SensingArm, ReferenceArm
from detectors import SPADDetector, CoincidenceProcessor
from signal_processing import QuantumPPGExtractor, ClassicalPPGExtractor, evaluate_ppg
from .config import QuantumPPGConfig
from .arduino_sketch import ArduinoPPGSketch

@dataclass(frozen=True)
class QuantumPPGResult:
    time_s: np.ndarray; blood_volume: np.ndarray; tissue_transmission: np.ndarray
    signal_singles: np.ndarray; reference_singles: np.ndarray; coincidences: np.ndarray
    genuine_coincidences: np.ndarray; accidentals: np.ndarray
    quantum_raw: np.ndarray; quantum_filtered: np.ndarray
    classical_raw: np.ndarray; classical_filtered: np.ndarray
    quantum_metrics: object; classical_metrics: object
    true_heart_rate_bpm: float
    arduino_coincidence_pulses: int; arduino_adc_samples: int; arduino_serial: str

class QuantumPPGSystem:
    """Coordinates source → paths → tissue → detectors → coincidence → PPG → Uno."""
    def __init__(self, config: QuantumPPGConfig = QuantumPPGConfig(), board: ArduinoUno | None = None):
        self.config=config; self.board=board or ArduinoUno()
        streams=np.random.SeedSequence(config.seed).spawn(5)
        self.rng=np.random.default_rng(streams[0])
        self._signal_path_rng=np.random.default_rng(streams[1]); self._reference_path_rng=np.random.default_rng(streams[2])
        self.source=SPDCSource(config.source); self.blood_model=BloodVolumeModel(config.blood); self.tissue=FingertipTissue(config.tissue)
        self.sensing_arm=SensingArm(config.sensing_path); self.reference_arm=ReferenceArm(config.reference_path)
        self.signal_detector=SPADDetector("A", config.signal_detector, np.random.default_rng(streams[3])); self.reference_detector=SPADDetector("B", config.reference_detector, np.random.default_rng(streams[4]))
        self.timing=CoincidenceProcessor(config.source.coincidence_window_ns)

    def run(self, duration_seconds: float = 10.0, *, drive_arduino: bool=True) -> QuantumPPGResult:
        if duration_seconds <= 0: raise ValueError("duration_seconds must be positive")
        c=self.config; bw_s=c.processing.bin_width_ms/1000; bins=int(round(duration_seconds/bw_s)); time_s=(np.arange(bins)+.5)*bw_s
        blood=self.blood_model.waveform(time_s); transmission=self.tissue.transmission(blood)
        ns_per_bin=bw_s*1e9; trials=max(1, round(c.pump_trials_per_second*bw_s)); probabilities=self.source.state.probabilities(0,0).ravel()
        singles_a=[]; singles_b=[]; coinc=[]; genuine=[]; accidentals=[]; event_id=0
        circuit=EntangledPhotonArduinoCircuit(self.source, self.board) if drive_arduino else None
        sketch=ArduinoPPGSketch(self.board) if drive_arduino else None
        if sketch: sketch.setup()
        for index in range(bins):
            a_events=[]; b_events=[]; bin_start=index*ns_per_bin
            # Detector dead time is causal, so events must arrive in timestamp order.
            for gate in bin_start + np.sort(self.rng.random(trials)*ns_per_bin):
                if self.rng.random() < c.source.pair_generation_probability:
                    pair_index=int(self.rng.choice(4,p=probabilities)); sig_out, ref_out=divmod(pair_index,2)
                    # Wrapper preserves the existing source event API at the emission boundary.
                    emission=PhotonEvent(event_id, True, sig_out, ref_out, 0, 0, False, False, gate, False)
                    sig=self.sensing_arm.propagate(emission.event_id, gate, emission.signal_outcome, float(transmission[index]), self._signal_path_rng)
                    ref=self.reference_arm.propagate(emission.event_id, gate, emission.idler_outcome, self._reference_path_rng)
                    event_id += 1
                else: sig=ref=None
                da=self.signal_detector.detect(sig, gate); db=self.reference_detector.detect(ref, gate)
                if da: a_events.append(da)
                if db: b_events.append(db)
            stats=self.timing.process(a_events,b_events)
            singles_a.append(stats.signal_singles); singles_b.append(stats.reference_singles); coinc.append(stats.coincidences); genuine.append(stats.genuine_coincidences); accidentals.append(stats.accidentals)
            if circuit:
                adc=min(1023, round(1023*stats.coincidences/max(1,trials)))
                circuit.emit_conditioned_counts(stats.signal_singles, stats.reference_singles, stats.coincidences, analog_value=adc)
                sketch.sample()
                # The external sample clock advances in milliseconds; individual
                # pulse widths were already represented by the interface stage.
                self.board.delay(c.processing.bin_width_ms)
        a=np.asarray(singles_a); b=np.asarray(singles_b); co=np.asarray(coinc); ge=np.asarray(genuine); ac=np.asarray(accidentals)
        q=QuantumPPGExtractor(c.processing); cl=ClassicalPPGExtractor(c.processing); qr=q.raw(co,b); cr=cl.raw(a); qf=q.filtered(qr); cf=cl.filtered(cr)
        ground_truth=blood-np.mean(blood); fs=1/bw_s; qm=evaluate_ppg(qf,ground_truth,fs); cm=evaluate_ppg(cf,ground_truth,fs)
        if sketch: sketch.report(fs)
        return QuantumPPGResult(time_s,blood,transmission,a,b,co,ge,ac,qr,qf,cr,cf,qm,cm,c.blood.heart_rate_bpm, sketch.coincidence_count if sketch else 0, len(sketch.adc_samples) if sketch else 0, self.board.Serial.output if sketch else "")
