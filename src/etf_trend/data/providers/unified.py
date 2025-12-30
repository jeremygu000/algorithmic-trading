"""
统一数据获取模块
================

提供统一的数据加载接口，支持自动故障转移 (Fallback)。
默认优先使用 Tiingo，如果失败（限流或网络错误）则自动切换到 Yahoo Finance。
"""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd

from etf_trend.data.providers.tiingo_daily import load_tiingo_daily_adjclose
from etf_trend.data.providers.yahoo_daily import load_yahoo_daily_adjclose

logger = logging.getLogger(__name__)


def load_prices_with_fallback(
    symbols: Iterable[str],
    start: str,
    end: str,
    tiingo_api_key: str | None = None,
    cache_enabled: bool = True,
    cache_dir: str = "cache",
) -> pd.DataFrame:
    """
    统一加载价格数据（带 Fallback 机制）

    策略：
    1. 如果提供了 tokens 且 Tiingo 可用，尝试使用 Tiingo
    2. 如果 Tiingo 失败或未提供 key，切换到 Yahoo Finance
    3. 自动合并数据并处理缺失值

    Args:
        symbols: 股票/ETF 代码列表
        start: 开始日期
        end: 结束日期
        tiingo_api_key: Tiingo API Key (如果为 None，直接使用 Yahoo)
        cache_enabled: 是否启用缓存
        cache_dir: 缓存目录
    """
    symbols = list(set(symbols))
    if not symbols:
        return pd.DataFrame()

    # 尝试 1: Tiingo
    if tiingo_api_key:
        try:
            print(f"尝试从 Tiingo 加载 {len(symbols)} 个资产数据...")
            df = load_tiingo_daily_adjclose(
                symbols,
                start,
                end,
                tiingo_api_key,
                cache_enabled=cache_enabled,
                cache_dir=cache_dir,
            )

            # 检查是否有数据缺失
            missing = [s for s in symbols if s not in df.columns or df[s].isnull().all()]

            if not missing:
                return df

            print(f"Tiingo 缺失部分数据: {missing}，尝试使用 Yahoo Finance 补全...")

            # 部分 Fallback: 使用 Yahoo 补全缺失数据
            yahoo_df = load_yahoo_daily_adjclose(
                missing,
                start,
                end,
                cache_enabled=cache_enabled,
                cache_dir=cache_dir,
            )

            if not yahoo_df.empty:
                # 合并数据
                df = df.combine_first(yahoo_df)

            return df

        except Exception as e:
            print(f"Tiingo 加载失败 ({e})，切换到 Yahoo Finance...")

    # 尝试 2: Yahoo Finance (Fallback)
    print(f"尝试从 Yahoo Finance 加载 {len(symbols)} 个资产数据...")
    return load_yahoo_daily_adjclose(
        symbols,
        start,
        end,
        cache_enabled=cache_enabled,
        cache_dir=cache_dir,
    )
