"""
Beauty Shoulder backtest — scan Russell 3000 over a date range,
detect patterns, simulate equal-weight buy-and-hold for 2 and 3 days,
and produce trade-level + monthly statistics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from etf_trend.data.providers.local_parquet import DEFAULT_DATA_DIR, load_local_daily_ohlcv
from etf_trend.features.beauty_shoulder import (
    BeautyShoulderConfig,
    BeautyShoulderPattern,
    detect_beauty_shoulder,
)

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    symbol: str
    signal_date: str
    entry_price: float
    exit_date_2d: str
    exit_price_2d: float
    return_2d: float
    exit_date_3d: str
    exit_price_3d: float
    return_3d: float
    phase1_gain: float
    pullback_depth: float
    confidence: float


@dataclass
class BacktestSummary:
    period: str
    total_signals: int
    win_rate_2d: float
    win_rate_3d: float
    avg_return_2d: float
    avg_return_3d: float
    median_return_2d: float
    median_return_3d: float
    max_gain_2d: float
    max_loss_2d: float
    max_gain_3d: float
    max_loss_3d: float


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    monthly_stats: list[BacktestSummary] = field(default_factory=list)
    overall: BacktestSummary | None = None


def run_beauty_shoulder_backtest(
    symbols: list[str],
    start: str = "2025-10-01",
    end: str = "2026-02-01",
    config: BeautyShoulderConfig | None = None,
    data_dir: str | Path = DEFAULT_DATA_DIR,
) -> BacktestResult:
    """Run beauty shoulder backtest across symbols and date range.

    We need extra lookback before `start` for EMA20 warm-up and
    pattern formation, so we load data from 60 trading days earlier.
    """
    cfg = config or BeautyShoulderConfig()

    lookback_start = str((pd.Timestamp(start) - pd.Timedelta(days=90)).date())
    load_end = str((pd.Timestamp(end) + pd.Timedelta(days=10)).date())

    logger.info(f"Loading OHLCV for {len(symbols)} symbols ({lookback_start} ~ {load_end}) ...")
    ohlcv_data = load_local_daily_ohlcv(symbols, lookback_start, load_end, data_dir=data_dir)
    logger.info(f"Loaded {len(ohlcv_data)} symbols with data")

    all_trades: list[Trade] = []

    for sym, df in ohlcv_data.items():
        patterns = detect_beauty_shoulder(
            close=df["Close"],
            open_=df["Open"],
            high=df["High"],
            symbol=sym,
            config=cfg,
        )

        for pat in patterns:
            if pat.signal_date < start or pat.signal_date >= end:
                continue

            trade = _simulate_trade(pat, df)
            if trade is not None:
                all_trades.append(trade)

    logger.info(f"Total signals in [{start}, {end}): {len(all_trades)}")

    result = BacktestResult(trades=all_trades)
    result.overall = _compute_summary("overall", all_trades)
    result.monthly_stats = _compute_monthly_stats(all_trades)

    return result


def _simulate_trade(pat: BeautyShoulderPattern, df: pd.DataFrame) -> Trade | None:
    """Given a pattern signal, look up exit prices 2 and 3 days after entry."""
    close = df["Close"]
    sig_ts = pd.Timestamp(pat.signal_date)

    future = close.loc[close.index > sig_ts]
    if len(future) < 3:
        return None

    exit_2d_price = float(future.iloc[1]) if len(future) >= 2 else float(future.iloc[-1])
    exit_3d_price = float(future.iloc[2]) if len(future) >= 3 else float(future.iloc[-1])

    entry = pat.entry_price
    ret_2d = exit_2d_price / entry - 1.0
    ret_3d = exit_3d_price / entry - 1.0

    return Trade(
        symbol=pat.symbol,
        signal_date=pat.signal_date,
        entry_price=entry,
        exit_date_2d=(
            str(future.index[1].date()) if len(future) >= 2 else str(future.index[-1].date())
        ),
        exit_price_2d=round(exit_2d_price, 2),
        return_2d=round(ret_2d * 100, 4),
        exit_date_3d=(
            str(future.index[2].date()) if len(future) >= 3 else str(future.index[-1].date())
        ),
        exit_price_3d=round(exit_3d_price, 2),
        return_3d=round(ret_3d * 100, 4),
        phase1_gain=pat.phase1_gain,
        pullback_depth=pat.pullback_depth,
        confidence=pat.confidence,
    )


def _compute_summary(period: str, trades: list[Trade]) -> BacktestSummary:
    if not trades:
        return BacktestSummary(
            period=period,
            total_signals=0,
            win_rate_2d=0.0,
            win_rate_3d=0.0,
            avg_return_2d=0.0,
            avg_return_3d=0.0,
            median_return_2d=0.0,
            median_return_3d=0.0,
            max_gain_2d=0.0,
            max_loss_2d=0.0,
            max_gain_3d=0.0,
            max_loss_3d=0.0,
        )

    r2 = np.array([t.return_2d for t in trades])
    r3 = np.array([t.return_3d for t in trades])

    return BacktestSummary(
        period=period,
        total_signals=len(trades),
        win_rate_2d=round(float(np.mean(r2 > 0)) * 100, 2),
        win_rate_3d=round(float(np.mean(r3 > 0)) * 100, 2),
        avg_return_2d=round(float(np.mean(r2)), 4),
        avg_return_3d=round(float(np.mean(r3)), 4),
        median_return_2d=round(float(np.median(r2)), 4),
        median_return_3d=round(float(np.median(r3)), 4),
        max_gain_2d=round(float(np.max(r2)), 4),
        max_loss_2d=round(float(np.min(r2)), 4),
        max_gain_3d=round(float(np.max(r3)), 4),
        max_loss_3d=round(float(np.min(r3)), 4),
    )


def _compute_monthly_stats(trades: list[Trade]) -> list[BacktestSummary]:
    if not trades:
        return []

    by_month: dict[str, list[Trade]] = {}
    for t in trades:
        month_key = t.signal_date[:7]
        by_month.setdefault(month_key, []).append(t)

    return [
        _compute_summary(month, month_trades) for month, month_trades in sorted(by_month.items())
    ]


def save_backtest_report(result: BacktestResult, output_dir: str | Path = "reports") -> None:
    """Save trades CSV, monthly CSV, and text summary."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if result.trades:
        trades_df = pd.DataFrame(
            [
                {
                    "symbol": t.symbol,
                    "signal_date": t.signal_date,
                    "entry_price": t.entry_price,
                    "exit_date_2d": t.exit_date_2d,
                    "exit_price_2d": t.exit_price_2d,
                    "return_2d%": t.return_2d,
                    "exit_date_3d": t.exit_date_3d,
                    "exit_price_3d": t.exit_price_3d,
                    "return_3d%": t.return_3d,
                    "phase1_gain%": t.phase1_gain,
                    "pullback_depth%": t.pullback_depth,
                    "confidence": t.confidence,
                }
                for t in result.trades
            ]
        )
        trades_df.to_csv(out / "beauty_shoulder_trades.csv", index=False)

    if result.monthly_stats:
        monthly_df = pd.DataFrame(
            [
                {
                    "month": s.period,
                    "signals": s.total_signals,
                    "win_rate_2d%": s.win_rate_2d,
                    "win_rate_3d%": s.win_rate_3d,
                    "avg_return_2d%": s.avg_return_2d,
                    "avg_return_3d%": s.avg_return_3d,
                    "median_2d%": s.median_return_2d,
                    "median_3d%": s.median_return_3d,
                    "max_gain_2d%": s.max_gain_2d,
                    "max_loss_2d%": s.max_loss_2d,
                }
                for s in result.monthly_stats
            ]
        )
        monthly_df.to_csv(out / "beauty_shoulder_monthly.csv", index=False)

    summary_lines = ["Beauty Shoulder Backtest Summary", "=" * 40]
    if result.overall:
        o = result.overall
        summary_lines.extend(
            [
                f"Total Signals:     {o.total_signals}",
                f"Win Rate (2d):     {o.win_rate_2d}%",
                f"Win Rate (3d):     {o.win_rate_3d}%",
                f"Avg Return (2d):   {o.avg_return_2d}%",
                f"Avg Return (3d):   {o.avg_return_3d}%",
                f"Median Return (2d):{o.median_return_2d}%",
                f"Median Return (3d):{o.median_return_3d}%",
                f"Max Gain (2d):     {o.max_gain_2d}%",
                f"Max Loss (2d):     {o.max_loss_2d}%",
                f"Max Gain (3d):     {o.max_gain_3d}%",
                f"Max Loss (3d):     {o.max_loss_3d}%",
            ]
        )
    summary_lines.append("")
    summary_lines.append("Monthly Breakdown")
    summary_lines.append("-" * 40)
    for ms in result.monthly_stats:
        summary_lines.append(
            f"{ms.period}: {ms.total_signals} signals, "
            f"WR2d={ms.win_rate_2d}%, WR3d={ms.win_rate_3d}%, "
            f"Avg2d={ms.avg_return_2d}%, Avg3d={ms.avg_return_3d}%"
        )

    (out / "beauty_shoulder_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")
    logger.info(f"Reports saved to {out}/")
