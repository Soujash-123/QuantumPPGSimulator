"""Run the fully conditioned source-to-Uno interface: python -m quantum_source.arduino_demo"""
from arduino import ArduinoUno, INPUT, RISING
from arduino_connector import EntangledPhotonArduinoCircuit
from .spdc_source import SPDCSource

def main():
    board = ArduinoUno()
    observed_coincidences = []
    board.pinMode(2, INPUT)
    board.attachInterrupt(2, lambda: observed_coincidences.append(board.micros()), RISING)
    result = EntangledPhotonArduinoCircuit(SPDCSource(), board).run(1000)
    print("## ENTANGLED PHOTON SOURCE → ARDUINO UNO")
    print("Circuit: SPAD/APD → discriminator → coincidence logic → 5 V pulse stretcher → D2/INT0")
    print(f"Source coincidences: {result.source_stats.coincidences}")
    print(f"D2 interrupt pulses observed: {len(observed_coincidences)}")
    print(f"Diagnostic singles: signal={result.signal_pulses}, idler={result.idler_pulses}")
    print(f"A0 coincidence-rate monitor: {board.analogRead('A0')} / 1023")

if __name__ == "__main__":
    main()
