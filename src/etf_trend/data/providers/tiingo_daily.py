"""
Tiingo 数据获取模块
==================

本模块从 Tiingo API 获取历史价格数据。

特性：
- 顺序请求（避免触发限流）
- 自动重试（429 限流处理）
- Parquet 缓存（避免重复请求）

注意：Tiingo 免费版有严格的请求限制，本模块采用顺序请求方式。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable

import httpx
import pandas as pd

from etf_trend.data.cache import cache_path, load_parquet, save_parquet

TIINGO_BASE = "https://api.tiingo.com/tiingo/daily"

# API 限流配置
MAX_RETRIES = 5  # 最大重试次数
BASE_RETRY_DELAY = 5.0  # 基础重试延迟（秒）
REQUEST_DELAY = 1.0  # 请求间隔（秒）


def _fetch_one_sync(
    client: httpx.Client,
    symbol: str,
    start: str,
    end: str,
    api_key: str,
) -> list[Dict[str, Any]]:
    """
    同步获取单个股票的价格数据

    包含重试逻辑处理 429 限流
    """
    url = f"{TIINGO_BASE}/{symbol}/prices"
    params = {
        "startDate": start,
        "endDate": end,
        "format": "json",
        "resampleFreq": "daily",
        "token": api_key,
    }

    for attempt in range(MAX_RETRIES):
        try:
            r = client.get(url, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # 限流，指数退避重试
                import time

                wait_time = BASE_RETRY_DELAY * (2**attempt)
                print(f"    [{symbol}] API 限流，等待 {wait_time:.0f}s...")
                time.sleep(wait_time)
            elif e.response.status_code == 404:
                # 股票不存在
                print(f"    [{symbol}] 未找到数据")
                return []
            else:
                print(f"    [{symbol}] 请求错误: {e}")
                raise

    # 重试耗尽
    print(f"    [{symbol}] 重试失败，跳过")
    return []


def _load_tiingo_sequential(
    symbols: list[str],
    start: str,
    end: str,
    api_key: str,
) -> pd.DataFrame:
    """
    顺序加载多个股票的价格数据

    采用顺序请求方式，避免触发 Tiingo 的限流
    """
    import time

    frames = []

    with httpx.Client(timeout=30.0) as client:
        for i, sym in enumerate(symbols):
            print(f"    [{i + 1}/{len(symbols)}] 正在获取 {sym}...")

            # 请求间隔
            if i > 0:
                time.sleep(REQUEST_DELAY)

            rows = _fetch_one_sync(client, sym, start, end, api_key)
            df = pd.DataFrame(rows)

            if df.empty:
                frames.append(pd.DataFrame(columns=["date", sym]).set_index("date"))
            else:
                df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None)
                px = df["adjClose"] if "adjClose" in df.columns else df["close"]
                out = pd.DataFrame({"date": df["date"], sym: px.astype(float)}).set_index("date")
                frames.append(out)

    if not frames:
        return pd.DataFrame()

    prices = pd.concat(frames, axis=1).sort_index()

    # 确保所有列存在
    for s in symbols:
        if s not in prices.columns:
            prices[s] = pd.NA

    return prices[symbols]


def load_tiingo_daily_adjclose(
    symbols: Iterable[str],
    start: str,
    end: str,
    api_key: str,
    cache_enabled: bool = True,
    cache_dir: str = "cache",
) -> pd.DataFrame:
    """
    加载股票价格数据（带缓存）

    优先使用缓存数据，仅获取缺失的符号。
    """
    symbols = list(dict.fromkeys(symbols))  # 去重保序

    # 尝试从缓存加载
    cached_data = {}
    missing_symbols = []

    if cache_enabled:
        for sym in symbols:
            key = f"tiingo_daily_{start}_{end}_{sym}"
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
        print(f"  正在从 Tiingo 获取 {len(missing_symbols)} 个资产的数据...")
        new_prices = _load_tiingo_sequential(missing_symbols, start, end, api_key)

        # 缓存新获取的数据
        if cache_enabled:
            for sym in missing_symbols:
                if sym in new_prices.columns:
                    key = f"tiingo_daily_{start}_{end}_{sym}"
                    path = cache_path(cache_dir, key)
                    df = pd.DataFrame({sym: new_prices[sym]})
                    save_parquet(path, df)
                    cached_data[sym] = new_prices[sym]

    # 合并数据
    if not cached_data:
        return pd.DataFrame()

    result = pd.DataFrame(cached_data)

    # 按请求的符号顺序返回
    available = [s for s in symbols if s in result.columns]
    return result[available] if available else pd.DataFrame()


# 保留异步接口以兼容旧代码
async def load_tiingo_daily_adjclose_async(
    symbols: Iterable[str],
    start: str,
    end: str,
    api_key: str,
    concurrency: int = 1,
) -> pd.DataFrame:
    """异步接口（实际使用同步实现）"""
    return _load_tiingo_sequential(list(symbols), start, end, api_key)
