"""A software digital twin of an Arduino Uno R3.

Write sketches with familiar Arduino calls::

    from arduino import ArduinoUno, OUTPUT, HIGH

    board = ArduinoUno()
    board.pinMode(13, OUTPUT)
    board.digitalWrite(13, HIGH)

The twin is intentionally self-contained.  ``arduino_connector`` is reserved
for wiring external sensor twins to this board.
"""

from __future__ import annotations

import argparse
import runpy
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, Union

# Arduino-compatible constants
LOW, HIGH = 0, 1
INPUT, OUTPUT, INPUT_PULLUP = 0, 1, 2
CHANGE, FALLING, RISING = 1, 2, 3


class PinMode(Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INPUT_PULLUP = "INPUT_PULLUP"


@dataclass(frozen=True)
class PinInfo:
    number: Union[int, str]
    name: str
    capabilities: tuple[str, ...]


@dataclass
class PinState:
    info: PinInfo
    mode: PinMode = PinMode.INPUT
    digital_value: int = LOW
    analog_value: int = 0
    pwm_value: int = 0


class SerialPort:
    """Small in-memory representation of Arduino's ``Serial`` object."""

    def __init__(self) -> None:
        self.baudrate: Optional[int] = None
        self._input: list[str] = []
        self._output: list[str] = []
        self._lock = threading.RLock()

    def begin(self, baudrate: int) -> None:
        self.baudrate = int(baudrate)

    def print(self, value: object = "") -> None:
        with self._lock:
            self._output.append(str(value))

    def println(self, value: object = "") -> None:
        self.print(f"{value}\n")

    def available(self) -> int:
        with self._lock:
            return len(self._input)

    def read(self) -> int:
        with self._lock:
            if not self._input:
                return -1
            return ord(self._input.pop(0)[0])

    def inject(self, data: str) -> None:
        """Feed simulated serial input into the board."""
        with self._lock:
            self._input.extend(data)

    @property
    def output(self) -> str:
        with self._lock:
            return "".join(self._output)

    def clear(self) -> None:
        with self._lock:
            self._input.clear()
            self._output.clear()


class ArduinoUno:
    """Digital twin of an Arduino Uno R3 (ATmega328P).

    Pin numbers 0--13 are digital I/O; A0--A5 are analog inputs and can also
    be addressed as digital pins 14--19.  3, 5, 6, 9, 10 and 11 support PWM.
    Supply/reference pins are represented for inspection but are not writable.
    """

    PWM_PINS = frozenset((3, 5, 6, 9, 10, 11))
    INTERRUPT_PINS = frozenset((2, 3))
    ANALOG_NAMES = ("A0", "A1", "A2", "A3", "A4", "A5")

    def __init__(self, *, name: str = "Arduino Uno R3", realtime: bool = False) -> None:
        self.name = name
        self.realtime = realtime
        self.Serial = SerialPort()
        self._started_at = time.monotonic()
        self._virtual_ms = 0.0
        self._pins: Dict[int, PinState] = {}
        self._fixed_pins: Dict[str, PinInfo] = {}
        self._interrupts: Dict[int, tuple[Callable[[], None], int]] = {}
        self._lock = threading.RLock()
        self._build_pin_map()

    def _build_pin_map(self) -> None:
        for number in range(14):
            caps = ["digital"]
            if number in self.PWM_PINS:
                caps.append("pwm")
            if number in self.INTERRUPT_PINS:
                caps.append("interrupt")
            if number in (0, 1):
                caps.append("serial")
            self._pins[number] = PinState(PinInfo(number, f"D{number}", tuple(caps)))
        for index, name in enumerate(self.ANALOG_NAMES):
            number = 14 + index
            caps = ["digital", "analog_input"]
            if name in ("A4", "A5"):
                caps.append("i2c")
            self._pins[number] = PinState(PinInfo(number, name, tuple(caps)))
        for name, capabilities in {
            "VIN": ("power_input",), "5V": ("power_output",), "3V3": ("power_output",),
            "GND": ("ground",), "RESET": ("reset",), "AREF": ("analog_reference",),
        }.items():
            self._fixed_pins[name] = PinInfo(name, name, capabilities)

    @property
    def pins(self) -> Dict[Union[int, str], PinInfo]:
        """Read-only pin metadata keyed by digital number/name and supply name."""
        result: Dict[Union[int, str], PinInfo] = {number: pin.info for number, pin in self._pins.items()}
        result.update({state.info.name: state.info for state in self._pins.values() if state.info.name.startswith("A")})
        result.update(self._fixed_pins)
        return result

    def _pin_number(self, pin: Union[int, str]) -> int:
        if isinstance(pin, str):
            label = pin.upper()
            if label in self.ANALOG_NAMES:
                return 14 + self.ANALOG_NAMES.index(label)
            if label.startswith("D") and label[1:].isdigit():
                pin = int(label[1:])
            elif label in self._fixed_pins:
                raise ValueError(f"{label} is a supply/reference pin, not programmable I/O")
            else:
                raise ValueError(f"unknown Arduino Uno pin: {pin!r}")
        if not isinstance(pin, int) or pin not in self._pins:
            raise ValueError(f"unknown Arduino Uno I/O pin: {pin!r}")
        return pin

    def pinMode(self, pin: Union[int, str], mode: Union[int, PinMode]) -> None:
        number = self._pin_number(pin)
        modes = {INPUT: PinMode.INPUT, OUTPUT: PinMode.OUTPUT, INPUT_PULLUP: PinMode.INPUT_PULLUP}
        if isinstance(mode, PinMode):
            selected = mode
        elif mode in modes:
            selected = modes[mode]
        else:
            raise ValueError("mode must be INPUT, OUTPUT, or INPUT_PULLUP")
        with self._lock:
            state = self._pins[number]
            state.mode = selected
            if selected is PinMode.INPUT_PULLUP:
                state.digital_value = HIGH

    def digitalWrite(self, pin: Union[int, str], value: int) -> None:
        number = self._pin_number(pin)
        if value not in (LOW, HIGH, False, True):
            raise ValueError("digital value must be LOW/0 or HIGH/1")
        with self._lock:
            state = self._pins[number]
            if state.mode is PinMode.INPUT:
                state.mode = PinMode.INPUT_PULLUP if value else PinMode.INPUT
            self._set_digital(number, int(bool(value)))

    def digitalRead(self, pin: Union[int, str]) -> int:
        with self._lock:
            return self._pins[self._pin_number(pin)].digital_value

    def analogRead(self, pin: Union[int, str]) -> int:
        number = self._pin_number(pin)
        with self._lock:
            return self._pins[number].analog_value

    def analogWrite(self, pin: Union[int, str], value: int) -> None:
        number = self._pin_number(pin)
        if number not in self.PWM_PINS:
            raise ValueError(f"pin {pin!r} does not support PWM on an Arduino Uno")
        if not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError("PWM value must be an integer from 0 to 255")
        with self._lock:
            state = self._pins[number]
            state.mode = PinMode.OUTPUT
            state.pwm_value = value
            self._set_digital(number, HIGH if value >= 128 else LOW)

    def set_analog_input(self, pin: Union[int, str], value: int) -> None:
        """Drive an analog input from a sensor twin (0--1023)."""
        number = self._pin_number(pin)
        if number < 14:
            raise ValueError("analog input must be A0 through A5")
        if not isinstance(value, int) or not 0 <= value <= 1023:
            raise ValueError("analog input must be an integer from 0 to 1023")
        with self._lock:
            self._pins[number].analog_value = value
            self._set_digital(number, HIGH if value >= 512 else LOW)

    def set_digital_input(self, pin: Union[int, str], value: int) -> None:
        """Drive a digital input from a sensor twin or test harness."""
        number = self._pin_number(pin)
        with self._lock:
            self._set_digital(number, HIGH if value else LOW)

    def _set_digital(self, number: int, value: int) -> None:
        previous = self._pins[number].digital_value
        self._pins[number].digital_value = value
        if previous != value and number in self._interrupts:
            callback, edge = self._interrupts[number]
            if edge == CHANGE or (edge == RISING and value == HIGH) or (edge == FALLING and value == LOW):
                callback()

    def attachInterrupt(self, pin: Union[int, str], callback: Callable[[], None], mode: int) -> None:
        number = self._pin_number(pin)
        if number not in self.INTERRUPT_PINS:
            raise ValueError("external interrupts on an Uno are available only on pins 2 and 3")
        if mode not in (CHANGE, FALLING, RISING):
            raise ValueError("interrupt mode must be CHANGE, FALLING, or RISING")
        self._interrupts[number] = (callback, mode)

    def detachInterrupt(self, pin: Union[int, str]) -> None:
        self._interrupts.pop(self._pin_number(pin), None)

    def millis(self) -> int:
        return int((time.monotonic() - self._started_at) * 1000) if self.realtime else int(self._virtual_ms)

    def micros(self) -> int:
        return self.millis() * 1000

    def delay(self, milliseconds: Union[int, float]) -> None:
        if milliseconds < 0:
            raise ValueError("delay cannot be negative")
        if self.realtime:
            time.sleep(milliseconds / 1000)
        else:
            self._virtual_ms += milliseconds

    def reset(self) -> None:
        with self._lock:
            self._started_at = time.monotonic()
            self._virtual_ms = 0.0
            self.Serial.clear()
            self._interrupts.clear()
            self._pins.clear()
            self._fixed_pins.clear()
            self._build_pin_map()

    def pin_state(self, pin: Union[int, str]) -> PinState:
        """Return a copyable state object for inspection."""
        return self._pins[self._pin_number(pin)]


def run_sketch(path: Union[str, Path], board: Optional[ArduinoUno] = None, *, iterations: Optional[int] = None) -> ArduinoUno:
    """Run a Python Arduino-style sketch containing optional ``setup`` and ``loop`` functions."""
    board = board or ArduinoUno()
    namespace = runpy.run_path(str(path), init_globals={
        "board": board, "arduino": board, "Serial": board.Serial,
        "HIGH": HIGH, "LOW": LOW, "INPUT": INPUT, "OUTPUT": OUTPUT, "INPUT_PULLUP": INPUT_PULLUP,
    })
    setup, loop = namespace.get("setup"), namespace.get("loop")
    if setup:
        setup()
    if loop:
        count = 0
        while iterations is None or count < iterations:
            loop()
            count += 1
    return board


def _main() -> None:
    parser = argparse.ArgumentParser(description="Run a Python Arduino-style sketch on an Arduino Uno R3 twin.")
    parser.add_argument("sketch", type=Path, help="Python sketch with setup() and/or loop()")
    parser.add_argument("--iterations", type=int, default=1, help="Number of loop calls (default: 1)")
    args = parser.parse_args()
    board = run_sketch(args.sketch, iterations=args.iterations)
    if board.Serial.output:
        print(board.Serial.output, end="")


if __name__ == "__main__":
    _main()
