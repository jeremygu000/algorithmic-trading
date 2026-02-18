"""Trend scan service for stock list filtering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from etf_trend.config.settings import AppConfig
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.selector.satellite import StockSelector

TrendDirection = Literal["up", "down"]


@dataclass
class TrendScanMatch:
    symbol: str
    name: str
    latest_price: float
    daily_changes_pct: list[float]

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "latest_price": round(self.latest_price, 2),
            "daily_changes_pct": self.daily_changes_pct,
        }


@dataclass
class TrendScanResult:
    date: str
    k: int
    trend: TrendDirection
    total_scanned: int
    stocks: list[TrendScanMatch]

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "k": self.k,
            "trend": self.trend,
            "trend_label": "上涨" if self.trend == "up" else "下跌",
            "total_scanned": self.total_scanned,
            "matched_count": len(self.stocks),
            "stocks": [s.to_dict() for s in self.stocks],
        }


class TrendScannerService:
    """Scan stocks by continuous up/down trend in recent K trading days."""

    _TREND_ALIASES = {
        "up": "up",
        "上涨": "up",
        "rise": "up",
        "bull": "up",
        "bullish": "up",
        "down": "down",
        "下跌": "down",
        "fall": "down",
        "bear": "down",
        "bearish": "down",
    }

    def __init__(self, cfg: AppConfig, tiingo_api_key: str | None = None) -> None:
        self.cfg = cfg
        self.tiingo_api_key = tiingo_api_key

    @classmethod
    def _normalize_trend(cls, trend: str) -> TrendDirection:
        normalized = cls._TREND_ALIASES.get(trend.strip().lower())
        if normalized == "up":
            return "up"
        if normalized == "down":
            return "down"
        raise ValueError("t 参数仅支持 up/down 或 上涨/下跌")

    def _stock_universe(self) -> list[str]:
        stock_symbols = self.cfg.universe.stock_symbols or StockSelector.DEFAULT_STOCK_POOL
        return list(dict.fromkeys(stock_symbols))

    def scan(self, k: int = 5, t: str = "up") -> TrendScanResult:
        if k < 1:
            raise ValueError("k 必须是大于 0 的整数")

        trend = self._normalize_trend(t)
        symbols = self._stock_universe()
        end_date = date.today()
        start_date = end_date - timedelta(days=max(365, k * 8))

        prices = load_prices_with_fallback(
            symbols,
            str(start_date),
            str(end_date),
            self.tiingo_api_key,
            cache_enabled=self.cfg.cache.enabled,
            cache_dir=self.cfg.cache.dir,
        )
        prices = prices.ffill().dropna(how="all")

        matched: list[TrendScanMatch] = []
        total_scanned = 0

        for symbol in symbols:
            if symbol not in prices.columns:
                continue

            series = prices[symbol].dropna()
            if len(series) < k + 1:
                continue

            recent = series.iloc[-(k + 1) :]
            deltas = recent.diff().iloc[1:]
            total_scanned += 1

            if trend == "up":
                is_match = (deltas > 0).all()
            else:
                is_match = (deltas < 0).all()

            if not is_match:
                continue

            changes = recent.pct_change().iloc[1:] * 100
            matched.append(
                TrendScanMatch(
                    symbol=symbol,
                    name=StockSelector.STOCK_NAMES.get(symbol, symbol),
                    latest_price=float(series.iloc[-1]),
                    daily_changes_pct=[round(float(x), 2) for x in changes.tolist()],
                )
            )

        return TrendScanResult(
            date=str(end_date),
            k=k,
            trend=trend,
            total_scanned=total_scanned,
            stocks=matched,
        )
