from __future__ import annotations
import numpy as np
from scipy.signal import butter, filtfilt, lfilter

def bandpass(signal, sample_rate_hz: float, low_hz: float, high_hz: float, causal: bool=False):
    data=np.asarray(signal, dtype=float)
    if len(data) < 16: return data-data.mean()
    nyquist=sample_rate_hz/2; high=min(high_hz, nyquist*.95)
    b,a=butter(2, [low_hz/nyquist, high/nyquist], btype='band')
    return lfilter(b,a,data) if causal else filtfilt(b,a,data)

def zscore(signal):
    signal=np.asarray(signal,float); std=signal.std()
    return (signal-signal.mean())/(std if std else 1.0)
