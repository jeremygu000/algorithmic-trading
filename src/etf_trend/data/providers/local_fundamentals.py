"""
本地 Parquet 基本面数据读取模块
================================

从 ~/.market_data/parquet/fundamentals/ 读取 yahoo-finance-data 项目维护的基本面数据。
文件命名约定: {TICKER}_fundamentals.parquet
Schema: DatetimeIndex(fetched_at), 42 columns (yfinance 原始字段名)

本模块负责:
1. 读取本地 parquet 文件
2. 字段名映射 (yfinance 原始名 → 项目内部名)
3. 新鲜度检查 (fetched_at 超过阈值视为过期)
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from etf_trend.data.providers.local_parquet import DEFAULT_DATA_DIR

DEFAULT_FUNDAMENTALS_DIR = DEFAULT_DATA_DIR / "fundamentals"

logger = logging.getLogger(__name__)

STALENESS_THRESHOLD_DAYS = 7

# yfinance raw field → project FundamentalData key
_FIELD_MAP: dict[str, str] = {
    "trailingPE": "peRatio",
    "pegRatio": "pegRatio",
    "priceToBook": "pbRatio",
    "trailingEps": "trailingEPS",
    "returnOnEquity": "returnOnEquity",
    "grossMargins": "grossMargins",
    "debtToEquity": "debtToEquity",
    "earningsGrowth": "earningsGrowth",
    "marketCap": "marketCap",
    "averageVolume": "averageVolume",
    "sector": "sector",
}


def load_local_fundamentals(
    symbols: list[str],
    data_dir: str | Path = DEFAULT_FUNDAMENTALS_DIR,
    staleness_days: int = STALENESS_THRESHOLD_DAYS,
) -> tuple[dict[str, dict], list[str]]:
    data_dir = Path(data_dir)
    loaded: dict[str, dict] = {}
    missing: list[str] = []

    now = pd.Timestamp.now(tz="UTC")

    for sym in symbols:
        path = data_dir / f"{sym}_fundamentals.parquet"

        if not path.exists():
            missing.append(sym)
            continue

        try:
            df = pd.read_parquet(path)
        except Exception as e:
            logger.warning(f"读取本地基本面 parquet 失败 {sym}: {e}")
            missing.append(sym)
            continue

        if df.empty:
            missing.append(sym)
            continue

        fetched_at = df.index[0]
        if hasattr(fetched_at, "tz") and fetched_at.tz is None:
            fetched_at = fetched_at.tz_localize("UTC")
        age_days = (now - fetched_at).days

        if age_days > staleness_days:
            logger.info(
                f"本地基本面数据过期 {sym}: "
                f"fetched_at={fetched_at.date()}, age={age_days}d > {staleness_days}d"
            )
            missing.append(sym)
            continue

        row = df.iloc[0]
        fund_data: dict = {"symbol": sym}

        for src_field, dst_field in _FIELD_MAP.items():
            value = row.get(src_field)
            if pd.isna(value):
                fund_data[dst_field] = None
            elif isinstance(value, (np.integer,)):
                fund_data[dst_field] = int(value)
            elif isinstance(value, (np.floating,)):
                fund_data[dst_field] = float(value)
            else:
                fund_data[dst_field] = value

        loaded[sym] = fund_data

    if loaded:
        logger.info(
            f"从本地 parquet 加载了 {len(loaded)} 个 ticker 的基本面数据"
            f"（{len(missing)} 个缺失/过期）"
        )

    return loaded, missing
