from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from etf_trend.config.settings import EnvSettings, load_config

# Get the package root directory
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.data.quality import clean_prices
from etf_trend.features.momentum import momentum_score
from etf_trend.features.trend_filter import trend_on as calc_trend_on
from etf_trend.portfolio.rebalance import build_monthly_weights
from etf_trend.backtest.engine import run_backtest
from etf_trend.backtest.metrics import perf_stats
from etf_trend.report.pdf import export_report_pdf
from etf_trend.analysis.llm_analyst import analyze_backtest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=str(date.today()))
    ap.add_argument("--out", default="etf_trend_report.pdf")
    ap.add_argument("--no-ai", action="store_true", help="Skip LLM analysis")
    args = ap.parse_args()

    cfg = load_config(args.config)
    env = EnvSettings()

    print("Loading price data...")
    prices = load_prices_with_fallback(
        cfg.universe.symbols,
        args.start,
        args.end,
        env.tiingo_api_key,
        cache_enabled=cfg.cache.enabled,
        cache_dir=cfg.cache.dir,
    )

    # Clean data
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

    # Generate LLM analysis
    llm_analysis = None
    if not args.no_ai and env.llm_api_key:
        print(f"Generating AI analysis using {env.llm_provider}/{env.llm_model}...")
        llm_analysis = analyze_backtest(
            provider=env.llm_provider,
            api_key=env.llm_api_key,
            model=env.llm_model,
            stats=stats,
            bt=bt,
            prices=prices,
            benchmark_symbol="SPY",
        )
        print("AI analysis complete.")
    elif not args.no_ai:
        print("Skipping AI analysis (LLM_API_KEY not configured)")

    export_report_pdf(
        args.out,
        bt,
        prices,
        weights,
        stats,
        benchmark_symbol="SPY",
        llm_analysis=llm_analysis,
    )
    print(f"Exported: {args.out}")


if __name__ == "__main__":
    main()
