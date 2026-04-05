from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import TypedDict
import json

import pandas as pd
import yfinance as yf

from etf_trend.data.cache import cache_path
from etf_trend.data.providers.local_fundamentals import load_local_fundamentals

logger = logging.getLogger(__name__)

# Yahoo Finance 并行获取的最大线程数
# yfinance 内部对同一 IP 有频率限制，过高并发反而触发 429。
# 8 线程是经验值：比顺序快 5-6 倍，又不容易被限流。
_YAHOO_MAX_WORKERS = 8

# 单个 ticker 的 yfinance API 超时秒数
_YAHOO_TIMEOUT_SECONDS = 15


class FundamentalData(TypedDict):
    symbol: str
    returnOnEquity: float | None
    grossMargins: float | None
    debtToEquity: float | None
    earningsGrowth: float | None
    marketCap: int | None
    averageVolume: int | None
    sector: str | None


def _fetch_single_fundamental(
    sym: str,
    cache_enabled: bool,
    cache_dir: str,
) -> tuple[str, FundamentalData]:
    """获取单个股票的基本面数据（线程安全）。"""
    try:
        ticker = yf.Ticker(sym)
        info = ticker.info

        fund_data: FundamentalData = {
            "symbol": sym,
            "peRatio": info.get("trailingPE"),
            "pegRatio": info.get("pegRatio"),
            "pbRatio": info.get("priceToBook"),
            "trailingEPS": info.get("trailingEps"),
            "returnOnEquity": info.get("returnOnEquity"),
            "grossMargins": info.get("grossMargins"),
            "debtToEquity": info.get("debtToEquity"),
            "earningsGrowth": info.get("earningsGrowth"),
            "marketCap": info.get("marketCap"),
            "averageVolume": info.get("averageVolume"),
            "sector": info.get("sector"),
        }

        # 写入缓存
        if cache_enabled:
            key = f"yahoo_fund_{sym}_{pd.Timestamp.now().strftime('%Y%m%d')}"
            path = cache_path(cache_dir, key)
            json_path = path.with_suffix(".json")
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(fund_data, f)

        return sym, fund_data

    except Exception as e:
        logger.warning(f"无法获取 {sym} 基本面数据: {e}")
        return sym, {
            "symbol": sym,
            "peRatio": None,
            "pegRatio": None,
            "pbRatio": None,
            "trailingEPS": None,
            "returnOnEquity": None,
            "grossMargins": None,
            "debtToEquity": None,
            "earningsGrowth": None,
            "marketCap": None,
            "averageVolume": None,
            "sector": None,
        }


def load_yahoo_fundamentals(
    symbols: list[str],
    cache_enabled: bool = True,
    cache_dir: str = "cache",
) -> dict[str, FundamentalData]:
    """
    加载基本面数据 (hybrid: 本地 parquet → JSON 缓存 → Yahoo Finance API)

    Args:
        symbols: 股票代码列表
        cache_enabled: 是否缓存
        cache_dir: 缓存目录

    Returns:
        dict: {symbol: FundamentalData}
    """
    result: dict[str, FundamentalData] = {}

    local_data, still_missing = load_local_fundamentals(symbols)
    result.update(local_data)

    if not still_missing:
        return result

    missing: list[str] = []

    if cache_enabled:
        for sym in still_missing:
            key = f"yahoo_fund_{sym}_{pd.Timestamp.now().strftime('%Y%m%d')}"
            path = cache_path(cache_dir, key)
            json_path = path.with_suffix(".json")
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "averageVolume" not in data:
                            missing.append(sym)
                        else:
                            result[sym] = data
                except Exception:
                    missing.append(sym)
            else:
                missing.append(sym)
    else:
        missing = list(still_missing)

    if not missing:
        return result

    logger.info(f"正在从 Yahoo Finance 并行获取 {len(missing)} 个资产的基本面数据...")

    with ThreadPoolExecutor(max_workers=min(_YAHOO_MAX_WORKERS, len(missing))) as pool:
        futures = {
            pool.submit(_fetch_single_fundamental, sym, cache_enabled, cache_dir): sym
            for sym in missing
        }
        for future in as_completed(futures, timeout=_YAHOO_TIMEOUT_SECONDS * len(missing)):
            sym = futures[future]
            try:
                _, fund_data = future.result(timeout=_YAHOO_TIMEOUT_SECONDS)
                result[sym] = fund_data
            except TimeoutError:
                logger.warning(f"获取 {sym} 基本面数据超时 ({_YAHOO_TIMEOUT_SECONDS}s)")
            except Exception as e:
                logger.warning(f"获取 {sym} 基本面数据失败: {e}")

    return result
