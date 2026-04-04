"""
本地 Parquet 数据获取模块 (DuckDB 加速)
=========================================

从 ~/.market_data/parquet/ 读取本地存储的 OHLCV 数据。
使用 DuckDB 批量读取 Parquet 文件，替代逐文件 pd.read_parquet 循环，
在全量扫描 (~2,500 symbols) 场景下提速约 15-30x。

数据由 yahoo-finance-data 项目维护和更新。

文件命名约定: {TICKER}_1d.parquet
Schema: DatetimeIndex(Date), columns (Open/High/Low/Close/Volume)

使用示例:
---------
>>> from etf_trend.data.providers.local_parquet import load_local_daily_adjclose
>>> prices = load_local_daily_adjclose(["QQQ", "XLE"], "2025-01-01", "2026-01-01")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".market_data" / "parquet"

# Regex: extract ticker from filenames like "AAPL_1d.parquet", "BRK.B_1d.parquet"
_SYMBOL_RE = r"([A-Za-z0-9._-]+?)_\d+[a-z]+\.parquet$"

_SMALL_N_THRESHOLD = 20


def _build_parquet_source(
    symbols: list[str],
    data_dir: Path,
    interval: str,
) -> str | list[str]:
    """For small N, return explicit file list; for large N, return glob pattern."""
    if len(symbols) <= _SMALL_N_THRESHOLD:
        paths = []
        for sym in symbols:
            p = data_dir / f"{sym}_{interval}.parquet"
            if p.exists():
                paths.append(str(p))
        return paths if paths else str(data_dir / f"*_{interval}.parquet")
    return str(data_dir / f"*_{interval}.parquet")


def load_local_daily_adjclose(
    symbols: Iterable[str],
    start: str,
    end: str,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    从本地 Parquet 文件加载每日收盘价 (DuckDB 加速版)

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

    source = _build_parquet_source(symbols, data_dir, interval)
    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                regexp_extract(filename, '{_SYMBOL_RE}', 1) AS symbol,
                "Date",
                "Close"
            FROM read_parquet(?, filename=true)
            WHERE "Date" >= CAST(? AS DATE)
              AND "Date" <= CAST(? AS DATE)
            ORDER BY symbol, "Date"
            """,
            [source, start, end],
        ).fetchdf()
    finally:
        con.close()

    if df.empty:
        missing = [
            sym
            for sym in symbols
            if not (data_dir / f"{sym}_{interval}.parquet").exists()
        ]
        if missing:
            raise FileNotFoundError(
                f"以下 ticker 缺少本地 parquet 文件: {missing}\n"
                f"数据目录: {data_dir}\n"
                "请在 yahoo-finance-data 项目中添加这些 ticker 并重新下载。"
            )
        return pd.DataFrame()

    df = df[df["symbol"].isin(symbols)]

    if df.empty:
        missing = [
            sym
            for sym in symbols
            if not (data_dir / f"{sym}_{interval}.parquet").exists()
        ]
        if missing:
            raise FileNotFoundError(
                f"以下 ticker 缺少本地 parquet 文件: {missing}\n"
                f"数据目录: {data_dir}\n"
                "请在 yahoo-finance-data 项目中添加这些 ticker 并重新下载。"
            )
        return pd.DataFrame()

    result = df.pivot(index="Date", columns="symbol", values="Close")
    result.index = pd.to_datetime(result.index)
    result.index.name = "Date"

    loaded_symbols = set(result.columns)
    missing = [sym for sym in symbols if sym not in loaded_symbols]

    truly_missing = [
        sym
        for sym in missing
        if not (data_dir / f"{sym}_{interval}.parquet").exists()
    ]
    empty_range = [
        sym
        for sym in missing
        if sym not in truly_missing
    ]

    if empty_range:
        for sym in empty_range:
            logger.warning(f"  {sym}: 日期范围 {start}~{end} 内无数据")

    if truly_missing:
        raise FileNotFoundError(
            f"以下 ticker 缺少本地 parquet 文件: {truly_missing}\n"
            f"数据目录: {data_dir}\n"
            "请在 yahoo-finance-data 项目中添加这些 ticker 并重新下载。"
        )

    all_missing = truly_missing + empty_range
    if all_missing and not loaded_symbols:
        raise FileNotFoundError(
            f"以下 ticker 缺少本地 parquet 文件: {all_missing}\n"
            f"数据目录: {data_dir}\n"
            "请在 yahoo-finance-data 项目中添加这些 ticker 并重新下载。"
        )

    available = [s for s in symbols if s in result.columns]
    return result[available] if available else pd.DataFrame()


def load_local_daily_ohlcv(
    symbols: Iterable[str],
    start: str,
    end: str,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """
    从本地 Parquet 文件加载每日 OHLCV 数据 (DuckDB 加速版)

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

    source = _build_parquet_source(symbols, data_dir, interval)
    con = duckdb.connect()

    try:
        df = con.execute(
            f"""
            SELECT
                regexp_extract(filename, '{_SYMBOL_RE}', 1) AS symbol,
                "Date",
                "Open", "High", "Low", "Close", "Volume"
            FROM read_parquet(?, filename=true)
            WHERE "Date" >= CAST(? AS DATE)
              AND "Date" <= CAST(? AS DATE)
            ORDER BY symbol, "Date"
            """,
            [source, start, end],
        ).fetchdf()
    finally:
        con.close()

    if df.empty:
        return {}

    if symbols:
        df = df[df["symbol"].isin(symbols)]

    if df.empty:
        return {}

    result: dict[str, pd.DataFrame] = {}
    for sym, group in df.groupby("symbol"):
        ohlcv = group[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        ohlcv["Date"] = pd.to_datetime(ohlcv["Date"])
        ohlcv = ohlcv.set_index("Date").sort_index()

        if ohlcv.empty:
            continue

        result[str(sym)] = ohlcv

    return result
