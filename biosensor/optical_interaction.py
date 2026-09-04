"""Causal heartbeat -> blood volume -> tissue attenuation interface."""
from .tissue import FingertipTissue

def sensing_transmission(tissue: FingertipTissue, blood_volume):
    return tissue.transmission(blood_volume)
