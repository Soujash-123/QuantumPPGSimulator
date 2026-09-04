"""Arduino-style acquisition code for the existing Uno twin."""
from __future__ import annotations
from dataclasses import dataclass, field
from arduino import INPUT, RISING

@dataclass
class ArduinoPPGSketch:
    """Counts D2/D3 pulses and samples only the physically wired A0 input."""
    board: object
    coincidence_count: int = 0
    signal_count: int = 0
    adc_samples: list[int] = field(default_factory=list)
    sample_times_ms: list[float] = field(default_factory=list)
    def setup(self):
        self.board.Serial.begin(115200); self.board.pinMode(2, INPUT); self.board.pinMode(3, INPUT)
        self.board.attachInterrupt(2, self._coincidence_isr, RISING); self.board.attachInterrupt(3, self._signal_isr, RISING)
    def _coincidence_isr(self): self.coincidence_count += 1
    def _signal_isr(self): self.signal_count += 1
    def sample(self):
        self.adc_samples.append(self.board.analogRead("A0")); self.sample_times_ms.append(self.board.millis())
    def report(self, sample_rate_hz: float):
        # This estimate is intentionally derived from A0 samples captured above,
        # not from host-side ground truth or coincidence arrays.
        from signal_processing.metrics import estimate_heart_rate_bpm
        heart_rate_bpm=estimate_heart_rate_bpm(self.adc_samples, sample_rate_hz)
        self.board.Serial.println(f"PPG samples={len(self.adc_samples)} D2={self.coincidence_count} D3={self.signal_count} HR={heart_rate_bpm if heart_rate_bpm else 'unavailable'}")
