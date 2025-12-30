from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path

from etf_trend.config.settings import EnvSettings, load_config

# Get the package root directory
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"
from etf_trend.data.providers.tiingo_daily import load_tiingo_daily_adjclose
from etf_trend.data.quality import clean_prices
from etf_trend.features.momentum import momentum_score
from etf_trend.features.trend_filter import trend_on as calc_trend_on
from etf_trend.portfolio.rebalance import build_monthly_weights
from etf_trend.backtest.engine import run_backtest
from etf_trend.backtest.plots import (
    plot_normalized,
    plot_weights,
    plot_nav_vs_benchmark,
    plot_drawdown,
)
from etf_trend.backtest.metrics import perf_stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=str(date.today()))
    args = ap.parse_args()

    cfg = load_config(args.config)
    env = EnvSettings()

    prices = load_tiingo_daily_adjclose(
        cfg.universe.symbols,
        args.start,
        args.end,
        env.tiingo_api_key,
        cache_enabled=cfg.cache.enabled,
        cache_dir=cfg.cache.dir,
    )

    # Comprehensive data cleaning with outlier detection
    prices, quality_report = clean_prices(prices)
    print(
        f"Data quality: {quality_report.final_rows} rows, {quality_report.outliers_detected} outliers fixed"
    )

    score = momentum_score(prices, cfg.signal.mom_windows, cfg.signal.mom_weights)
    t_on = calc_trend_on(prices, cfg.signal.ma_long)

    weights = build_monthly_weights(
        prices=prices,
        score=score,
        trend_on=t_on,
        vol_lookback=cfg.risk.vol_lookback,
        max_weight_single=cfg.risk.max_weight_single,
        max_weight_core=cfg.risk.max_weight_core,
        core_symbols=cfg.universe.core_symbols,
    )

    bt = run_backtest(prices, weights, cost_bps=cfg.risk.cost_bps)
    stats = perf_stats(bt)

    print(stats)

    plot_normalized(prices, "Normalized Adj Close (Tiingo)")
    plot_weights(weights, "Portfolio Weights (Monthly)")
    plot_nav_vs_benchmark(
        bt, prices[cfg.universe.symbols[0]], "Strategy vs Benchmark (first symbol)"
    )
    plot_drawdown(bt, "Drawdown")


if __name__ == "__main__":
    main()
