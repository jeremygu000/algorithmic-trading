"""
Beauty Shoulder (美人肩) Pattern Detector
==========================================

Three-phase price pattern in strong uptrends:
  Phase 1 (Acceleration): 3-4 days, +20%~40% cumulative gain
  Phase 2 (Pullback):     4-6 days, -10%~25% from Phase 1 high, close > EMA20 every day
  Phase 3 (Entry Signal): Within 2 days of pullback low, medium bullish candle (+3%~10%)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BeautyShoulderPattern:
    symbol: str
    phase1_start: str
    phase1_end: str
    phase1_gain: float
    phase1_has_3_bullish: bool
    pullback_low_date: str
    pullback_depth: float
    pullback_days: int
    signal_date: str
    signal_candle_gain: float
    entry_price: float
    ema20_at_signal: float
    confidence: float


@dataclass
class BeautyShoulderConfig:
    # Phase 1 — acceleration
    accel_min_days: int = 3
    accel_max_days: int = 4
    accel_min_gain: float = 0.20
    accel_max_gain: float = 0.40

    # Phase 2 — pullback
    pullback_min_days: int = 4
    pullback_max_days: int = 6
    pullback_min_depth: float = 0.10
    pullback_max_depth: float = 0.25

    # Phase 3 — entry signal
    signal_window: int = 2
    signal_min_gain: float = 0.03
    signal_max_gain: float = 0.10


def detect_beauty_shoulder(
    close: pd.Series,
    open_: pd.Series,
    high: pd.Series,
    symbol: str = "",
    config: BeautyShoulderConfig | None = None,
) -> list[BeautyShoulderPattern]:
    """Scan a single stock's OHLC data for Beauty Shoulder patterns.

    Args:
        close:  Daily close prices (DatetimeIndex)
        open_:  Daily open prices
        high:   Daily high prices
        symbol: Ticker symbol (for labeling)
        config: Detection parameters (uses defaults if None)

    Returns:
        List of detected patterns, ordered by signal date.
    """
    cfg = config or BeautyShoulderConfig()

    if len(close) < cfg.accel_max_days + cfg.pullback_max_days + cfg.signal_window + 20:
        return []

    ema20 = close.ewm(span=20, adjust=False).mean()
    patterns: list[BeautyShoulderPattern] = []
    used_signal_dates: set[str] = set()

    n = len(close)
    close_arr = close.values.astype(np.float64)
    open_arr = open_.values.astype(np.float64)
    high_arr = high.values.astype(np.float64)
    ema20_arr = ema20.values.astype(np.float64)
    dates = close.index

    # Scan for Phase 1 starts
    for accel_len in range(cfg.accel_min_days, cfg.accel_max_days + 1):
        for i in range(20, n - accel_len - cfg.pullback_min_days - 1):
            start_idx = i
            end_idx = i + accel_len  # end of acceleration (inclusive)

            if end_idx >= n:
                break

            gain = close_arr[end_idx] / close_arr[start_idx] - 1.0
            if not (cfg.accel_min_gain <= gain <= cfg.accel_max_gain):
                continue

            # Optional: check 3 consecutive bullish candles
            bullish_count = 0
            for k in range(start_idx + 1, end_idx + 1):
                if close_arr[k] > open_arr[k]:
                    bullish_count += 1
            has_3_bullish = bullish_count >= 3

            phase1_high_idx = end_idx
            phase1_high_val = high_arr[end_idx]
            # Use the actual high of the acceleration phase
            for k in range(start_idx, end_idx + 1):
                if high_arr[k] > phase1_high_val:
                    phase1_high_val = high_arr[k]
                    phase1_high_idx = k

            # Phase 2: scan pullback after Phase 1 peak
            pullback_start = phase1_high_idx + 1
            if pullback_start >= n:
                continue

            best_pullback = _find_pullback(
                close_arr, ema20_arr, phase1_high_val, pullback_start, n, cfg
            )
            if best_pullback is None:
                continue

            pb_low_idx, pb_depth, pb_days = best_pullback

            # Phase 3: find entry signal candle
            signal_start = pb_low_idx + 1
            signal_end = min(pb_low_idx + cfg.signal_window + 1, n)

            for s in range(signal_start, signal_end):
                candle_gain = close_arr[s] / close_arr[s - 1] - 1.0
                if cfg.signal_min_gain <= candle_gain <= cfg.signal_max_gain:
                    sig_date_str = str(dates[s].date())
                    if sig_date_str in used_signal_dates:
                        continue
                    used_signal_dates.add(sig_date_str)

                    confidence = _compute_confidence(
                        gain, pb_depth, candle_gain, has_3_bullish, cfg
                    )

                    patterns.append(
                        BeautyShoulderPattern(
                            symbol=symbol,
                            phase1_start=str(dates[start_idx].date()),
                            phase1_end=str(dates[end_idx].date()),
                            phase1_gain=round(gain * 100, 2),
                            phase1_has_3_bullish=has_3_bullish,
                            pullback_low_date=str(dates[pb_low_idx].date()),
                            pullback_depth=round(pb_depth * 100, 2),
                            pullback_days=pb_days,
                            signal_date=sig_date_str,
                            signal_candle_gain=round(candle_gain * 100, 2),
                            entry_price=round(float(close_arr[s]), 2),
                            ema20_at_signal=round(float(ema20_arr[s]), 2),
                            confidence=round(confidence, 3),
                        )
                    )
                    break  # one signal per pullback

    patterns.sort(key=lambda p: p.signal_date)
    return patterns


def _find_pullback(
    close_arr: np.ndarray,
    ema20_arr: np.ndarray,
    phase1_high: float,
    start: int,
    n: int,
    cfg: BeautyShoulderConfig,
) -> tuple[int, float, int] | None:
    """Find the best pullback satisfying depth and EMA20 constraints.

    Returns (low_index, depth_ratio, num_days) or None.
    """
    low_val = close_arr[start]
    low_idx = start

    for day in range(start, min(start + cfg.pullback_max_days, n)):
        # Hard constraint: close must stay above EMA20
        if close_arr[day] < ema20_arr[day]:
            return None

        if close_arr[day] < low_val:
            low_val = close_arr[day]
            low_idx = day

    num_days = low_idx - start + 1
    depth = 1.0 - low_val / phase1_high

    if not (cfg.pullback_min_depth <= depth <= cfg.pullback_max_depth):
        return None
    if not (cfg.pullback_min_days <= num_days <= cfg.pullback_max_days):
        return None

    return (low_idx, depth, num_days)


def _compute_confidence(
    accel_gain: float,
    pullback_depth: float,
    signal_gain: float,
    has_3_bullish: bool,
    cfg: BeautyShoulderConfig,
) -> float:
    """Score 0-1 based on how well the pattern matches ideal parameters."""
    # Acceleration: ideal is midpoint of range
    accel_mid = (cfg.accel_min_gain + cfg.accel_max_gain) / 2
    accel_score = 1.0 - min(abs(accel_gain - accel_mid) / accel_mid, 1.0)

    # Pullback depth: ideal is midpoint
    pb_mid = (cfg.pullback_min_depth + cfg.pullback_max_depth) / 2
    pb_score = 1.0 - min(abs(pullback_depth - pb_mid) / pb_mid, 1.0)

    # Signal candle: stronger is better
    sig_range = cfg.signal_max_gain - cfg.signal_min_gain
    sig_score = min((signal_gain - cfg.signal_min_gain) / sig_range, 1.0) if sig_range > 0 else 0.5

    bullish_bonus = 0.1 if has_3_bullish else 0.0

    raw = 0.35 * accel_score + 0.30 * pb_score + 0.25 * sig_score + bullish_bonus
    return min(max(raw, 0.0), 1.0)
