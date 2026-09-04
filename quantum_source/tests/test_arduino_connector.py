import unittest
from arduino import ArduinoUno, INPUT, RISING
from arduino_connector import EntangledPhotonArduinoCircuit
from quantum_source import SPDCConfig, SPDCSource

class TestArduinoPhotonCircuit(unittest.TestCase):
    def test_conditioned_coincidences_drive_int0(self):
        source = SPDCSource(SPDCConfig(pair_generation_probability=1, detector_efficiency_signal=1, detector_efficiency_idler=1, optical_transmission_signal=1, optical_transmission_idler=1, dark_count_probability=0, background_count_probability=0, seed=77))
        board = ArduinoUno(); seen = []
        board.pinMode(2, INPUT); board.attachInterrupt(2, lambda: seen.append(1), RISING)
        result = EntangledPhotonArduinoCircuit(source, board).run(200)
        self.assertEqual(result.source_stats.coincidences, 200)
        self.assertEqual(result.coincidence_pulses, 200)
        self.assertEqual(len(seen), 200)
        self.assertEqual(board.analogRead("A0"), 1023)

if __name__ == "__main__": unittest.main()
