"""
本地 Parquet 数据获取模块
=========================

从 ~/.market_data/parquet/ 读取本地存储的 OHLCV 数据，提取 Close 列
作为调整后收盘价。数据由 yahoo-finance-data 项目维护和更新。

文件命名约定: {TICKER}_1d.parquet
Schema: DatetimeIndex(Date), MultiIndex columns (Price: Open/High/Low/Close/Volume)

使用示例:
---------
>>> from etf_trend.data.providers.local_parquet import load_local_daily_adjclose
>>> prices = load_local_daily_adjclose(["QQQ", "XLE"], "2025-01-01", "2026-01-01")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".market_data" / "parquet"


def load_local_daily_adjclose(
    symbols: Iterable[str],
    start: str,
    end: str,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    从本地 Parquet 文件加载每日收盘价

    Args:
        symbols: 股票/ETF 代码列表
        start: 开始日期 (YYYY-MM-DD)
        end: 结束日期 (YYYY-MM-DD)
        data_dir: parquet 文件所在目录，默认 ~/.market_data/parquet
        interval: 数据频率，默认 "1d"

    Returns:
        DataFrame，index 为日期，columns 为股票代码（收盘价）

    Raises:
        FileNotFoundError: 当请求的 ticker 没有对应的本地 parquet 文件时
    """
    symbols = list(dict.fromkeys(symbols))
    data_dir = Path(data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(
            f"本地数据目录不存在: {data_dir}\n" "请先使用 yahoo-finance-data 项目下载数据。"
        )

    series_dict: dict[str, pd.Series] = {}
    missing: list[str] = []

    for sym in symbols:
        parquet_path = data_dir / f"{sym}_{interval}.parquet"

        if not parquet_path.exists():
            missing.append(sym)
            continue

        try:
            df = pd.read_parquet(parquet_path)
            close = _extract_close(df, sym)

            if close is None:
                missing.append(sym)
                continue

            close.index = pd.to_datetime(close.index)
            close = close.sort_index()
            close = close.loc[start:end]

            if close.empty:
                logger.warning(f"  {sym}: 日期范围 {start}~{end} 内无数据")
                missing.append(sym)
                continue

            series_dict[sym] = close

        except Exception as e:
            logger.error(f"  {sym}: 读取 parquet 失败: {e}")
            missing.append(sym)

    if missing:
        raise FileNotFoundError(
            f"以下 ticker 缺少本地 parquet 文件: {missing}\n"
            f"数据目录: {data_dir}\n"
            "请在 yahoo-finance-data 项目中添加这些 ticker 并重新下载。"
        )

    if not series_dict:
        return pd.DataFrame()

    result = pd.DataFrame(series_dict)
    result.index = pd.to_datetime(result.index)

    available = [s for s in symbols if s in result.columns]
    return result[available] if available else pd.DataFrame()


def _extract_close(df: pd.DataFrame, sym: str) -> pd.Series | None:
    """Extract Close price series from a parquet DataFrame that may have MultiIndex columns."""
    if isinstance(df.columns, pd.MultiIndex):
        if "Close" in df.columns.get_level_values(0):
            close = df["Close"]
            return close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
        if "Close" in df.columns.get_level_values(1):
            close = df.xs("Close", axis=1, level=1)
            return close.iloc[:, 0] if isinstance(close, pd.DataFrame) else close
        logger.warning(f"  {sym}: 无法在 MultiIndex 中找到 Close 列，跳过")
        return None

    if "Close" in df.columns:
        return df["Close"]

    logger.warning(f"  {sym}: 找不到 Close 列，可用列: {list(df.columns)}")
    return None


def _extract_ohlcv(df: pd.DataFrame, sym: str) -> pd.DataFrame | None:
    """Extract OHLCV columns from a parquet DataFrame that may have MultiIndex columns.

    Returns a DataFrame with columns: Open, High, Low, Close, Volume.
    """
    cols = ["Open", "High", "Low", "Close", "Volume"]

    if isinstance(df.columns, pd.MultiIndex):
        level_values_0 = df.columns.get_level_values(0)
        level_values_1 = df.columns.get_level_values(1)

        if all(c in level_values_0 for c in cols):
            result = {}
            for c in cols:
                series = df[c]
                result[c] = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
            return pd.DataFrame(result)

        if all(c in level_values_1 for c in cols):
            result = {}
            for c in cols:
                series = df.xs(c, axis=1, level=1)
                result[c] = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
            return pd.DataFrame(result)

        logger.warning(f"  {sym}: MultiIndex 中缺少 OHLCV 列，跳过")
        return None

    if all(c in df.columns for c in cols):
        return df[cols].copy()

    logger.warning(f"  {sym}: 缺少 OHLCV 列，可用列: {list(df.columns)}")
    return None


def load_local_daily_ohlcv(
    symbols: Iterable[str],
    start: str,
    end: str,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """
    从本地 Parquet 文件加载每日 OHLCV 数据

    Args:
        symbols: 股票/ETF 代码列表
        start: 开始日期 (YYYY-MM-DD)
        end: 结束日期 (YYYY-MM-DD)
        data_dir: parquet 文件所在目录
        interval: 数据频率，默认 "1d"

    Returns:
        dict[symbol, DataFrame]  每个 DataFrame 包含 Open/High/Low/Close/Volume 列
        仅返回成功加载的 symbol，静默跳过缺失的。
    """
    symbols = list(dict.fromkeys(symbols))
    data_dir = Path(data_dir)

    if not data_dir.exists():
        raise FileNotFoundError(
            f"本地数据目录不存在: {data_dir}\n" "请先使用 yahoo-finance-data 项目下载数据。"
        )

    result: dict[str, pd.DataFrame] = {}

    for sym in symbols:
        parquet_path = data_dir / f"{sym}_{interval}.parquet"

        if not parquet_path.exists():
            continue

        try:
            df = pd.read_parquet(parquet_path)
            ohlcv = _extract_ohlcv(df, sym)

            if ohlcv is None:
                continue

            ohlcv.index = pd.to_datetime(ohlcv.index)
            ohlcv = ohlcv.sort_index()
            ohlcv = ohlcv.loc[start:end]

            if ohlcv.empty:
                continue

            result[sym] = ohlcv

        except Exception as e:
            logger.error(f"  {sym}: 读取 OHLCV parquet 失败: {e}")

    return result
