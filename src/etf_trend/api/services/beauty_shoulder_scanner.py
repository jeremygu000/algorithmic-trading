"""Beauty Shoulder & Early Mover scanner service for API layer."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from etf_trend.config.settings import AppConfig
from etf_trend.data.providers.local_parquet import DEFAULT_DATA_DIR, load_local_daily_ohlcv
from etf_trend.features.beauty_shoulder import (
    BeautyShoulderConfig,
    BeautyShoulderPattern,
    detect_beauty_shoulder,
)
from etf_trend.features.early_mover import EarlyMoverSignal, detect_early_mover
from etf_trend.backtest.beauty_shoulder_backtest import (
    BacktestResult,
    run_beauty_shoulder_backtest,
)
from etf_trend.selector.satellite import StockSelector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BeautyShoulderScanResult:
    date: str
    total_scanned: int
    patterns: list[BeautyShoulderPattern]

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_scanned": self.total_scanned,
            "matched_count": len(self.patterns),
            "patterns": [
                {
                    "symbol": p.symbol,
                    "name": StockSelector.STOCK_NAMES.get(p.symbol, p.symbol),
                    "entry_price": p.entry_price,
                    "signal_date": p.signal_date,
                    "phase1_gain": p.phase1_gain,
                    "phase1_start": p.phase1_start,
                    "phase1_end": p.phase1_end,
                    "phase1_has_3_bullish": p.phase1_has_3_bullish,
                    "pullback_depth": p.pullback_depth,
                    "pullback_days": p.pullback_days,
                    "pullback_low_date": p.pullback_low_date,
                    "signal_candle_gain": p.signal_candle_gain,
                    "ema20_at_signal": p.ema20_at_signal,
                    "confidence": p.confidence,
                }
                for p in self.patterns
            ],
        }


@dataclass
class EarlyMoverScanResult:
    date: str
    total_scanned: int
    signals: list[EarlyMoverSignal]

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_scanned": self.total_scanned,
            "matched_count": len(self.signals),
            "signals": [
                {
                    "symbol": s.symbol,
                    "name": StockSelector.STOCK_NAMES.get(s.symbol, s.symbol),
                    "gain_pct": s.gain_pct,
                    "window_start": s.window_start,
                    "window_end": s.window_end,
                    "start_price": s.start_price,
                    "end_price": s.end_price,
                }
                for s in self.signals
            ],
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BeautyShoulderScannerService:
    """Scan stocks for Beauty Shoulder patterns and Early Mover signals."""

    def __init__(
        self,
        cfg: AppConfig,
        data_dir: str | Path = DEFAULT_DATA_DIR,
    ) -> None:
        self.cfg = cfg
        self.data_dir = Path(data_dir)

    def _stock_universe(self) -> list[str]:
        """Build stock universe from all available local parquet files.

        Unlike other services that rely on config symbol lists, the beauty shoulder
        scanner needs maximum coverage — we scan every stock with local data.
        """
        symbols: list[str] = []
        if self.data_dir.exists():
            for p in sorted(self.data_dir.glob("*_1d.parquet")):
                sym = p.stem.replace("_1d", "")
                symbols.append(sym)
        if not symbols:
            stock_symbols = self.cfg.universe.stock_symbols or StockSelector.DEFAULT_STOCK_POOL
            symbols = list(dict.fromkeys(stock_symbols))
        logger.info(f"Beauty shoulder universe: {len(symbols)} symbols from {self.data_dir}")
        return symbols

    # -- Beauty Shoulder scan --------------------------------------------------

    def scan_beauty_shoulder(
        self,
        lookback_days: int = 90,
        config: BeautyShoulderConfig | None = None,
    ) -> BeautyShoulderScanResult:
        """Scan entire stock universe for recent Beauty Shoulder patterns."""
        bs_cfg = config or BeautyShoulderConfig()
        symbols = self._stock_universe()
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days + 90)

        ohlcv_data = load_local_daily_ohlcv(
            symbols, str(start_date), str(end_date), data_dir=self.data_dir
        )

        all_patterns: list[BeautyShoulderPattern] = []
        total_scanned = 0

        for sym, df in ohlcv_data.items():
            if len(df) < 30:
                continue
            total_scanned += 1

            patterns = detect_beauty_shoulder(
                close=df["Close"],
                open_=df["Open"],
                high=df["High"],
                symbol=sym,
                config=bs_cfg,
            )

            # Keep only patterns whose signal_date is within the lookback window
            cutoff = str((end_date - timedelta(days=lookback_days)))
            for p in patterns:
                if p.signal_date >= cutoff:
                    all_patterns.append(p)

        all_patterns.sort(key=lambda p: p.signal_date, reverse=True)

        return BeautyShoulderScanResult(
            date=str(end_date),
            total_scanned=total_scanned,
            patterns=all_patterns,
        )

    # -- Early Mover scan ------------------------------------------------------

    def scan_early_movers(
        self,
        window: int = 20,
        min_gain: float = 0.20,
        max_gain: float = 0.30,
    ) -> EarlyMoverScanResult:
        """Scan stock universe for Early Mover signals."""
        symbols = self._stock_universe()
        end_date = date.today()
        start_date = end_date - timedelta(days=window + 60)

        ohlcv_data = load_local_daily_ohlcv(
            symbols, str(start_date), str(end_date), data_dir=self.data_dir
        )

        all_signals: list[EarlyMoverSignal] = []
        total_scanned = 0

        for sym, df in ohlcv_data.items():
            if len(df) < window:
                continue
            total_scanned += 1

            signals = detect_early_mover(
                close=df["Close"],
                symbol=sym,
                window=window,
                min_gain=min_gain,
                max_gain=max_gain,
            )
            all_signals.extend(signals)

        # Sort by most recent window_end first
        all_signals.sort(key=lambda s: s.window_end, reverse=True)

        return EarlyMoverScanResult(
            date=str(end_date),
            total_scanned=total_scanned,
            signals=all_signals,
        )

    # -- Backtest --------------------------------------------------------------

    def run_backtest(
        self,
        start: str = "2025-10-01",
        end: str = "2026-02-01",
        config: BeautyShoulderConfig | None = None,
    ) -> BacktestResult:
        """Run historical backtest across the stock universe."""
        symbols = self._stock_universe()
        return run_beauty_shoulder_backtest(
            symbols=symbols,
            start=start,
            end=end,
            config=config,
            data_dir=self.data_dir,
        )
