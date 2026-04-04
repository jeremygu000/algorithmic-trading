"""
统一数据获取模块
================

提供统一的数据加载接口，支持自动故障转移 (Fallback)。
优先使用本地 Parquet 数据，如果本地缺失则尝试 Tiingo API。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from etf_trend.data.providers.local_parquet import (
    DEFAULT_DATA_DIR,
    load_local_daily_adjclose,
)
from etf_trend.data.providers.tiingo_daily import load_tiingo_daily_adjclose

logger = logging.getLogger(__name__)


def load_prices_with_fallback(
    symbols: Iterable[str],
    start: str,
    end: str,
    tiingo_api_key: str | None = None,
    cache_enabled: bool = True,
    cache_dir: str = "cache",
    data_dir: str | Path = DEFAULT_DATA_DIR,
) -> pd.DataFrame:
    """
    统一加载价格数据（带 Fallback 机制）

    策略：
    1. 优先从本地 Parquet 文件读取
    2. 本地缺失的 ticker 尝试 Tiingo API 补全
    3. 自动合并数据并处理缺失值

    Args:
        symbols: 股票/ETF 代码列表
        start: 开始日期
        end: 结束日期
        tiingo_api_key: Tiingo API Key（用于补全本地缺失的 ticker）
        cache_enabled: 是否启用 Tiingo 缓存
        cache_dir: Tiingo 缓存目录
        data_dir: 本地 parquet 文件目录
    """
    symbols = list(set(symbols))
    if not symbols:
        return pd.DataFrame()

    try:
        logger.info(f"从本地 Parquet 加载 {len(symbols)} 个资产数据...")
        return load_local_daily_adjclose(symbols, start, end, data_dir=data_dir)
    except FileNotFoundError as e:
        logger.warning(f"本地 Parquet 部分缺失: {e}")
        local_missing = _parse_missing_tickers(e)

    local_available = [s for s in symbols if s not in local_missing]
    local_df = pd.DataFrame()

    if local_available:
        try:
            local_df = load_local_daily_adjclose(local_available, start, end, data_dir=data_dir)
        except FileNotFoundError:
            pass

    if not local_missing:
        return local_df

    if tiingo_api_key:
        try:
            logger.info(f"尝试从 Tiingo 补全 {len(local_missing)} 个缺失 ticker: {local_missing}")
            tiingo_df = load_tiingo_daily_adjclose(
                local_missing,
                start,
                end,
                tiingo_api_key,
                cache_enabled=cache_enabled,
                cache_dir=cache_dir,
            )
            if not tiingo_df.empty and not local_df.empty:
                return local_df.combine_first(tiingo_df)
            return tiingo_df if local_df.empty else local_df
        except Exception as e:
            logger.error(f"Tiingo 补全失败: {e}")

    if not local_df.empty:
        logger.warning(f"以下 ticker 无法获取数据: {local_missing}")
        return local_df

    raise FileNotFoundError(
        f"无法获取任何价格数据。本地缺失: {local_missing}\n"
        "请在 yahoo-finance-data 项目中添加这些 ticker，或提供 Tiingo API key。"
    )


def _parse_missing_tickers(err: FileNotFoundError) -> list[str]:
    msg = str(err)
    if "[" in msg and "]" in msg:
        import ast

        bracket_content = msg[msg.index("[") : msg.index("]") + 1]
        try:
            return ast.literal_eval(bracket_content)
        except (ValueError, SyntaxError):
            pass
    return []
