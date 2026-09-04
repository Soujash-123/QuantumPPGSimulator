"""Loss is survival probability; it does not by itself alter polarization coherence."""
def survives(rng, transmission: float) -> bool:
    return bool(rng.random() < transmission)
