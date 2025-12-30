from __future__ import annotations

import logging
from typing import TypedDict
import json

import pandas as pd
import yfinance as yf

from etf_trend.data.cache import cache_path

logger = logging.getLogger(__name__)


class FundamentalData(TypedDict):
    symbol: str
    peRatio: float | None
    pegRatio: float | None
    pbRatio: float | None
    trailingEPS: float | None
    marketCap: int | None
    sector: str | None


def load_yahoo_fundamentals(
    symbols: list[str],
    cache_enabled: bool = True,
    cache_dir: str = "cache",
) -> dict[str, FundamentalData]:
    """
    加载基本面数据 (使用 Yahoo Finance)

    Args:
        symbols: 股票代码列表
        cache_enabled: 是否缓存
        cache_dir: 缓存目录

    Returns:
        dict: {symbol: FundamentalData}
    """
    result = {}
    missing = []

    # 尝试从缓存加载
    if cache_enabled:
        for sym in symbols:
            # 基本面数据变化慢，可以用当周或当月作为 Key，这里简化为每天 (实际 Cache 使用 hash 或日期)
            # 由于 yfinance 的 info 是实时请求，我们假定一天缓存一次足够
            key = f"yahoo_fund_{sym}_{pd.Timestamp.now().strftime('%Y%m%d')}"
            path = cache_path(cache_dir, key)

            # 使用 JSON 存储基本面数据 (不同于 Price 的 Parquet)
            # 这里为了简单，我们还是用简单的文件读写，或者复用 Parquet 如果想起存 DF
            # 考虑到数据量极小，直接用 json 文件更方便
            # 但为了统一基础设施，我们这里稍作变通：
            # 若 utils 只有 Parquet 支持，就用 Parquet。
            # 查阅代码发现 cache_path 只是返回路径。我们自己处理 IO。

            json_path = path.with_suffix(".json")
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        result[sym] = data
                except Exception:
                    missing.append(sym)
            else:
                missing.append(sym)
    else:
        missing = symbols

    if not missing:
        return result

    # 获取缺失数据
    print(f"  正在从 Yahoo Finance 获取 {len(missing)} 个资产的基本面数据...")

    for sym in missing:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info

            fund_data: FundamentalData = {
                "symbol": sym,
                "peRatio": info.get("trailingPE"),
                "pegRatio": info.get("pegRatio"),
                "pbRatio": info.get("priceToBook"),
                "trailingEPS": info.get("trailingEps"),
                "marketCap": info.get("marketCap"),
                "sector": info.get("sector"),
            }

            result[sym] = fund_data

            # 写入缓存
            if cache_enabled:
                key = f"yahoo_fund_{sym}_{pd.Timestamp.now().strftime('%Y%m%d')}"
                path = cache_path(cache_dir, key)
                json_path = path.with_suffix(".json")

                # 确保存储目录存在
                json_path.parent.mkdir(parents=True, exist_ok=True)

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(fund_data, f)

        except Exception as e:
            logger.warning(f"无法获取 {sym} 基本面数据: {e}")
            # 填充控制避免报错
            result[sym] = {
                "symbol": sym,
                "peRatio": None,
                "pegRatio": None,
                "pbRatio": None,
                "trailingEPS": None,
                "marketCap": None,
                "sector": None,
            }

    return result
