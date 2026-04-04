"""Stock universe builder service for picks pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from etf_trend.config.settings import AppConfig
from etf_trend.data.providers.yahoo_fundamentals import FundamentalData
from etf_trend.selector.satellite import StockSelector
from etf_trend.api.services.symbol_store import read_symbol_file


@dataclass
class StockUniverseBuildResult:
    mode: str
    input_count: int
    output_count: int
    symbols: list[str]


class StockUniverseBuilder:
    """Build stock universe for recommendation by static/dynamic policy."""

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg

    def base_candidates(self) -> list[str]:
        if self.cfg.universe.stock_universe_mode == "dynamic":
            file_symbols = read_symbol_file(self.cfg.universe.dynamic_stock_symbols_file)
            config_symbols = (
                self.cfg.universe.dynamic_stock_symbols or self.cfg.universe.stock_symbols
            )
            symbols = file_symbols + config_symbols
        else:
            symbols = self.cfg.universe.stock_symbols

        if not symbols:
            symbols = StockSelector.DEFAULT_STOCK_POOL

        # 去重并保持顺序
        return list(dict.fromkeys(symbols))

    def build(
        self,
        prices: pd.DataFrame,
        fundamentals: dict[str, FundamentalData],
    ) -> StockUniverseBuildResult:
        candidates = [s for s in self.base_candidates() if s in prices.columns]
        mode = self.cfg.universe.stock_universe_mode

        if mode == "static":
            return StockUniverseBuildResult(
                mode=mode,
                input_count=len(candidates),
                output_count=len(candidates),
                symbols=candidates,
            )

        # dynamic mode: liquidity/price/history filtering
        min_hist = self.cfg.universe.dynamic_min_history_days
        min_price = self.cfg.universe.dynamic_min_price
        min_avg_dollar_vol = self.cfg.universe.dynamic_min_avg_dollar_volume
        max_symbols = self.cfg.universe.dynamic_max_symbols

        scored: list[tuple[str, float]] = []
        for sym in candidates:
            series = prices[sym].dropna()
            if len(series) < min_hist:
                continue

            latest_price = float(series.iloc[-1])
            if latest_price < min_price:
                continue

            fund = fundamentals.get(sym) or {}
            avg_volume = fund.get("averageVolume")
            if avg_volume is None:
                continue

            try:
                dollar_vol = float(avg_volume) * latest_price
            except (TypeError, ValueError):
                continue

            if dollar_vol < min_avg_dollar_vol:
                continue

            scored.append((sym, dollar_vol))

        # 按流动性从高到低排序
        scored.sort(key=lambda x: x[1], reverse=True)
        symbols = [sym for sym, _ in scored]

        if max_symbols > 0:
            symbols = symbols[:max_symbols]

        return StockUniverseBuildResult(
            mode=mode,
            input_count=len(candidates),
            output_count=len(symbols),
            symbols=symbols,
        )
