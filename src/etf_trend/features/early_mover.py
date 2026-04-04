"""Early Mover detector — find stocks with 20%-30% gain in any 20-day window."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EarlyMoverSignal:
    symbol: str
    window_start: str
    window_end: str
    gain_pct: float
    start_price: float
    end_price: float


def detect_early_mover(
    close: pd.Series,
    symbol: str = "",
    window: int = 20,
    min_gain: float = 0.20,
    max_gain: float = 0.30,
) -> list[EarlyMoverSignal]:
    """Find all 20-day windows where cumulative gain is within [min_gain, max_gain]."""
    if len(close) < window:
        return []

    close_arr = close.values.astype(np.float64)
    dates = close.index
    n = len(close_arr)

    signals: list[EarlyMoverSignal] = []
    last_end: int = -1

    for i in range(n - window):
        j = i + window - 1
        gain = close_arr[j] / close_arr[i] - 1.0

        if min_gain <= gain <= max_gain and j > last_end:
            signals.append(
                EarlyMoverSignal(
                    symbol=symbol,
                    window_start=str(dates[i].date()),
                    window_end=str(dates[j].date()),
                    gain_pct=round(gain * 100, 2),
                    start_price=round(float(close_arr[i]), 2),
                    end_price=round(float(close_arr[j]), 2),
                )
            )
            last_end = j

    return signals
