"""Electrical bridge between the SPDC source/detector twin and Arduino Uno.

Physical circuit represented here
-------------------------------
signal photon -> SPAD/APD -> transimpedance amplifier -> discriminator --\
                                                                     external coincidence/timing logic
idler photon  -> SPAD/APD -> transimpedance amplifier -> discriminator --/       |
                                                                              3.3 V logic
                                                                              level shifter
                                                                              pulse stretcher
                                                                                   |
Arduino Uno GND ----------------------------------------------------------- common ground
Arduino D2 / INT0 <------------------------------------------------ coincidence pulse (5 V)
Arduino D3 / INT1 <------------------------------------------------ signal diagnostic pulse (5 V)
Arduino D4        <------------------------------------------------ idler diagnostic pulse (5 V)
Arduino A0        <------------------------------------------------ filtered coincidence-rate monitor

The discriminator and coincidence logic are required hardware. An Uno cannot
directly detect single photons, accepts neither a detector's analog avalanche
output nor nanosecond coincidence timing, and cannot safely accept 3.3 V-only
logic as a guaranteed HIGH. The model therefore creates 5 V-compatible,
stretched count pulses after the external timing stage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from arduino import ArduinoUno, INPUT, LOW, HIGH
from quantum_source import SPDCSource
from quantum_source.coincidence import count_coincidences, CoincidenceStats


@dataclass(frozen=True)
class PhotonCircuitConfig:
    """Wiring and conditioning assumptions for an Uno-based counting interface."""
    coincidence_pin: int = 2       # INT0; primary count pulse
    signal_diagnostic_pin: int = 3 # INT1; optional singles diagnostic
    idler_diagnostic_pin: int = 4  # optional polled diagnostic
    rate_monitor_pin: str = "A0"
    logic_voltage: float = 5.0
    pulse_stretch_us: float = 10.0
    adc_full_scale_coincidences: int = 100

    def __post_init__(self):
        if self.logic_voltage != 5.0:
            raise ValueError("Arduino Uno interface pulses must be 5 V logic in this model")
        if self.pulse_stretch_us <= 0 or self.adc_full_scale_coincidences <= 0:
            raise ValueError("pulse width and ADC full scale must be positive")
        pins = (self.coincidence_pin, self.signal_diagnostic_pin, self.idler_diagnostic_pin)
        if len(set(pins)) != 3:
            raise ValueError("each circuit output requires a distinct Arduino pin")


@dataclass(frozen=True)
class ArduinoPhotonRun:
    trials: int
    source_stats: CoincidenceStats
    coincidence_pulses: int
    signal_pulses: int
    idler_pulses: int
    analog_rate_monitor: int


class EntangledPhotonArduinoCircuit:
    """Connect a source's detector events to an Uno through conditioning logic.

    ``run`` is deliberately event-driven: every post-logic pulse drives an Uno
    pin HIGH then LOW. A sketch can attach a RISING interrupt to D2 and count
    coincidences exactly as it would from a physical pulse stretcher.
    """
    def __init__(self, source: SPDCSource, board: ArduinoUno, config: PhotonCircuitConfig = PhotonCircuitConfig()):
        self.source, self.board, self.config = source, board, config
        self._wired = False

    def wire(self) -> None:
        """Establish the shared-ground, 5 V logic input wiring in the digital twin."""
        for pin in (self.config.coincidence_pin, self.config.signal_diagnostic_pin, self.config.idler_diagnostic_pin):
            self.board.pinMode(pin, INPUT)
            self.board.set_digital_input(pin, LOW)
        self.board.set_analog_input(self.config.rate_monitor_pin, 0)
        self._wired = True

    def _pulse(self, pin: int) -> None:
        self.board.set_digital_input(pin, HIGH)
        # This represents a hardware pulse stretcher.  Virtual time progresses
        # without sleeping unless the Arduino twin was requested in realtime.
        self.board.delay(self.config.pulse_stretch_us / 1000)
        self.board.set_digital_input(pin, LOW)

    def emit_conditioned_counts(self, signal_count: int, idler_count: int, coincidence_count: int, *, analog_value: int) -> None:
        """Deliver outputs from external timing electronics for one PPG time bin.

        The caller has already performed nanosecond timestamp matching.  This
        method models only the safe, stretched 5-V electrical interface.
        """
        if not self._wired:
            self.wire()
        if min(signal_count, idler_count, coincidence_count) < 0 or not 0 <= analog_value <= 1023:
            raise ValueError("counts must be non-negative and A0 value must be 0..1023")
        for _ in range(signal_count): self._pulse(self.config.signal_diagnostic_pin)
        for _ in range(idler_count): self._pulse(self.config.idler_diagnostic_pin)
        for _ in range(coincidence_count): self._pulse(self.config.coincidence_pin)
        self.board.set_analog_input(self.config.rate_monitor_pin, analog_value)

    def run(self, trials: int, signal_angle: float = 0.0, idler_angle: float = 0.0) -> ArduinoPhotonRun:
        if trials < 0:
            raise ValueError("trials cannot be negative")
        if not self._wired:
            self.wire()
        events = self.source.generate(trials, signal_angle, idler_angle)
        stats = count_coincidences(events, self.source.config.coincidence_window_ns)
        signal = idler = coincidence = 0
        for event in events:
            if event.signal_detected:
                self._pulse(self.config.signal_diagnostic_pin); signal += 1
            if event.idler_detected:
                self._pulse(self.config.idler_diagnostic_pin); idler += 1
            # The external coincidence unit sees detector timestamps and emits
            # one stretched pulse only when both clicks are in its time window.
            if event.signal_detected and event.idler_detected:
                self._pulse(self.config.coincidence_pin); coincidence += 1
        monitor = min(1023, round(1023 * coincidence / max(1, self.config.adc_full_scale_coincidences)))
        self.board.set_analog_input(self.config.rate_monitor_pin, monitor)
        return ArduinoPhotonRun(trials, stats, coincidence, signal, idler, monitor)
