"""Phenomenological single-photon detector and timestamp models."""
from .config import DetectorConfig
from .detector_event import DetectionEvent
from .spad import SPADDetector
from .timing import CoincidenceProcessor, BinnedCoincidenceStats

__all__ = ["DetectorConfig", "DetectionEvent", "SPADDetector", "CoincidenceProcessor", "BinnedCoincidenceStats"]
