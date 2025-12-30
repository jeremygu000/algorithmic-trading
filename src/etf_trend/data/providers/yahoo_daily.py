"""
Yahoo Finance 数据获取模块
=========================

本模块使用 yfinance 从 Yahoo Finance 获取历史价格数据。

优点：
- 免费，无需 API 密钥
- 无严格的请求限制
- 支持股票、ETF、指数

使用示例：
---------
>>> from etf_trend.data.providers.yahoo_daily import load_yahoo_daily_adjclose
>>> prices = load_yahoo_daily_adjclose(["AAPL", "MSFT"], "2024-01-01", "2024-12-31")
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd
import yfinance as yf

from etf_trend.data.cache import cache_path, load_parquet, save_parquet


def load_yahoo_daily_adjclose(
    symbols: Iterable[str],
    start: str,
    end: str,
    cache_enabled: bool = True,
    cache_dir: str = "cache",
) -> pd.DataFrame:
    """
    从 Yahoo Finance 加载每日调整后收盘价

    Args:
        symbols: 股票/ETF 代码列表
        start: 开始日期 (YYYY-MM-DD)
        end: 结束日期 (YYYY-MM-DD)
        cache_enabled: 是否启用缓存
        cache_dir: 缓存目录

    Returns:
        DataFrame，index 为日期，columns 为股票代码
    """
    symbols = list(dict.fromkeys(symbols))  # 去重保序

    # 尝试从缓存加载
    cached_data = {}
    missing_symbols = []

    if cache_enabled:
        for sym in symbols:
            key = f"yahoo_daily_{start}_{end}_{sym}"
            path = cache_path(cache_dir, key)
            cached = load_parquet(path)
            if cached is not None and not cached.empty:
                cached.index = pd.to_datetime(cached.index)
                if sym in cached.columns:
                    cached_data[sym] = cached[sym]
                else:
                    missing_symbols.append(sym)
            else:
                missing_symbols.append(sym)
    else:
        missing_symbols = symbols

    # 获取缺失的数据
    if missing_symbols:
        print(f"  正在从 Yahoo Finance 获取 {len(missing_symbols)} 个资产的数据...")

        try:
            # yfinance 批量下载
            data = yf.download(
                missing_symbols,
                start=start,
                end=end,
                progress=False,
                auto_adjust=True,  # 自动调整
                threads=True,
            )

            if not data.empty:
                # 提取收盘价
                if len(missing_symbols) == 1:
                    # 单个股票时，data 的 columns 是 ['Open', 'High', 'Low', 'Close', 'Volume']
                    sym = missing_symbols[0]
                    if "Close" in data.columns:
                        prices = pd.DataFrame({sym: data["Close"]})
                    else:
                        prices = pd.DataFrame()
                else:
                    # 多个股票时，data 是 MultiIndex columns
                    if "Close" in data.columns.get_level_values(0):
                        prices = data["Close"]
                    else:
                        prices = pd.DataFrame()

                # 缓存新获取的数据
                if cache_enabled and not prices.empty:
                    for sym in missing_symbols:
                        if sym in prices.columns:
                            key = f"yahoo_daily_{start}_{end}_{sym}"
                            path = cache_path(cache_dir, key)
                            df = pd.DataFrame({sym: prices[sym]})
                            save_parquet(path, df)
                            cached_data[sym] = prices[sym]

        except Exception as e:
            print(f"  Yahoo Finance 获取失败: {e}")

    # 合并数据
    if not cached_data:
        return pd.DataFrame()

    result = pd.DataFrame(cached_data)
    result.index = pd.to_datetime(result.index)

    # 按请求的符号顺序返回
    available = [s for s in symbols if s in result.columns]
    return result[available] if available else pd.DataFrame()
