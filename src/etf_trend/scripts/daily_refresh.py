"""
Daily refresh job for stock universe and fundamentals cache.

Usage:
  # Run once immediately
  uv run python -m etf_trend.scripts.daily_refresh --once

  # Run every day at local 18:30
  uv run python -m etf_trend.scripts.daily_refresh --daemon --daily-at 18:30
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import io
import re
import time

import httpx
import pandas as pd

from etf_trend.api.services.symbol_store import read_symbol_file, write_symbol_file
from etf_trend.config.settings import load_config
from etf_trend.data.providers.yahoo_fundamentals import load_yahoo_fundamentals

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"

IWM_HOLDINGS_CSV = (
    "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
)
IWV_HOLDINGS_CSV = (
    "https://www.ishares.com/us/products/239724/ishares-russell-3000-etf/"
    "1467271812596.ajax?fileType=csv&fileName=IWV_holdings&dataType=fund"
)
TICKER_RE = re.compile(r"^[A-Z0-9.\-]{1,10}$")


def _fetch_ishares_symbols(holdings_csv_url: str) -> list[str]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(holdings_csv_url)
        resp.raise_for_status()
        text = resp.text

    lines = text.splitlines()
    header_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("Ticker,"):
            header_idx = idx
            break

    if header_idx < 0:
        raise RuntimeError("无法解析 iShares 持仓 CSV：未找到 Ticker 列")

    csv_part = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(csv_part))
    if "Ticker" not in df.columns or "Asset Class" not in df.columns:
        raise RuntimeError("无法解析 iShares 持仓 CSV：缺少 Ticker 列")

    symbols: list[str] = []
    # 只保留 Equity，过滤现金/期货/免责声明尾部文本
    equities = df[df["Asset Class"].astype(str).str.upper() == "EQUITY"]
    for raw in equities["Ticker"].dropna().astype(str).tolist():
        sym = raw.strip().upper()
        if not sym or sym in {"-", "CASH"}:
            continue
        if not TICKER_RE.match(sym):
            continue
        symbols.append(sym)

    return list(dict.fromkeys(symbols))


def _seconds_until_next_run(hhmm: str) -> float:
    now = datetime.now()
    target_h, target_m = [int(x) for x in hhmm.split(":")]
    next_run = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    if next_run <= now:
        next_run = next_run + timedelta(days=1)
    return (next_run - now).total_seconds()


def run_refresh(config_path: str, candidate_limit: int) -> None:
    cfg = load_config(config_path)

    print("=" * 72)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] 开始 daily refresh")

    # 1) Refresh Russell constituent files.
    try:
        russell_2000_symbols = _fetch_ishares_symbols(IWM_HOLDINGS_CSV)
        write_symbol_file(cfg.universe.russell_2000_symbols_file, russell_2000_symbols)
        print(f"Russell 2000 成分更新完成: {len(russell_2000_symbols)}")
    except Exception as e:
        print(f"Russell 2000 成分更新失败: {e}")

    try:
        russell_3000_symbols = _fetch_ishares_symbols(IWV_HOLDINGS_CSV)
        write_symbol_file(cfg.universe.russell_3000_symbols_file, russell_3000_symbols)
        print(f"Russell 3000 成分更新完成: {len(russell_3000_symbols)}")
    except Exception as e:
        print(f"Russell 3000 成分更新失败: {e}")

    # 2) Build candidate pool from Russell 3000 (fallback to configured pool).
    russell_3000_symbols = read_symbol_file(cfg.universe.russell_3000_symbols_file)
    source_symbols = russell_3000_symbols or cfg.universe.dynamic_stock_symbols or cfg.universe.stock_symbols
    source_symbols = list(dict.fromkeys(source_symbols))

    if candidate_limit > 0:
        source_symbols = source_symbols[:candidate_limit]

    if not source_symbols:
        print("没有可用于刷新的候选池，跳过 fundamentals 刷新")
        return

    print(f"候选池源数量: {len(source_symbols)}")

    # 3) Refresh fundamentals cache for source universe.
    fundamentals = load_yahoo_fundamentals(
        source_symbols,
        cache_enabled=cfg.cache.enabled,
        cache_dir=cfg.cache.dir,
    )
    print(f"Fundamentals 缓存刷新完成: {len(fundamentals)}")

    # 4) Rank by averageVolume and write dynamic_stock_symbols_file.
    scored: list[tuple[str, float]] = []
    for sym in source_symbols:
        fund = fundamentals.get(sym) or {}
        avg_volume = fund.get("averageVolume")
        if avg_volume is None:
            continue
        try:
            score = float(avg_volume)
        except (TypeError, ValueError):
            continue
        scored.append((sym, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    selected_symbols = [sym for sym, _ in scored]
    if cfg.universe.dynamic_max_symbols > 0:
        selected_symbols = selected_symbols[: cfg.universe.dynamic_max_symbols]

    # Keep manually maintained symbols at head to avoid accidental loss.
    existing_dynamic = read_symbol_file(cfg.universe.dynamic_stock_symbols_file)
    merged = list(dict.fromkeys(existing_dynamic + selected_symbols))
    write_symbol_file(cfg.universe.dynamic_stock_symbols_file, merged)
    print(
        f"dynamic_stock_symbols_file 更新完成: {len(merged)} "
        f"(手工列表 {len(existing_dynamic)} + 自动候选 {len(selected_symbols)})"
    )

    print(f"[{datetime.now().isoformat(timespec='seconds')}] daily refresh 完成")
    print("=" * 72)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily refresh stock universe + fundamentals cache")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="配置文件路径",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只执行一次并退出",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="以守护方式每日定时执行",
    )
    parser.add_argument(
        "--daily-at",
        default="18:30",
        help="守护模式下每日执行时间（本地时区），格式 HH:MM",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=1500,
        help="候选源最大数量（控制刷新耗时）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.daemon:
        while True:
            wait_seconds = _seconds_until_next_run(args.daily_at)
            run_at = datetime.now() + timedelta(seconds=wait_seconds)
            print(f"下次执行时间: {run_at.isoformat(timespec='seconds')}")
            time.sleep(wait_seconds)
            run_refresh(config_path=args.config, candidate_limit=args.candidate_limit)
    else:
        run_refresh(config_path=args.config, candidate_limit=args.candidate_limit)


if __name__ == "__main__":
    main()
