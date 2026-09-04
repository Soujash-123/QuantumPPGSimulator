from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.signal import periodogram
from .filters import zscore

@dataclass(frozen=True)
class PPGMetrics:
    correlation: float
    rmse: float
    snr_db: float
    heart_rate_bpm: float | None

def estimate_heart_rate_bpm(signal, sample_rate_hz: float) -> float | None:
    x=np.asarray(signal,float)
    if len(x) < 8 or not np.any(np.isfinite(x)): return None
    frequencies, power = periodogram(x-np.mean(x), fs=sample_rate_hz)
    band=(frequencies >= .5) & (frequencies <= 4.0)
    if not np.any(band) or not np.any(power[band]): return None
    return float(60*frequencies[band][np.argmax(power[band])])

def evaluate_ppg(estimate, ground_truth, sample_rate_hz: float) -> PPGMetrics:
    e,g=zscore(estimate),zscore(ground_truth)
    corr=float(np.corrcoef(e,g)[0,1]) if len(e)>1 and np.std(e)>0 and np.std(g)>0 else 0.0
    error=e-g; snr=10*np.log10((np.var(g)+1e-12)/(np.var(error)+1e-12))
    return PPGMetrics(corr, float(np.sqrt(np.mean(error**2))), float(snr), estimate_heart_rate_bpm(e,sample_rate_hz))
