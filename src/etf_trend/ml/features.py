"""
ML Feature Engineering
======================

Generate features for training ML models to predict stock returns.
Features include:
- Momentum (Roc, Slope)
- Volatility (ATR, StdDev)
- Trend (MA Distances)
- RSI
- Sector Momentum
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from etf_trend.features.indicators import calculate_rsi
from etf_trend.execution.executor import calculate_atr


def calculate_slope(series: pd.Series, window: int = 20) -> float:
    """Calculate linear regression slope normalized by price"""
    if len(series) < window:
        return 0.0
    y = series.iloc[-window:].values
    x = np.arange(len(y))
    # Simple linear regression: slope = cov(x,y) / var(x)
    # Just use polyfit for speed and simplicity
    try:
        slope, _ = np.polyfit(x, y, 1)
        return slope / series.iloc[-1] * 100  # Normalize as % of price
    except Exception:
        return 0.0


def generate_features(
    prices: pd.DataFrame, sector_map: Optional[Dict[str, str]] = None, lookback: int = 60
) -> pd.DataFrame:
    """
    Generate feature DataFrame for all stocks in prices.

    Returns:
        DataFrame with MultiIndex (Date, Symbol) or Single Index if 1 stock provided?
        Actually, let's return a DataFrame where columns are features and index is Date,
        but since we have multiple stocks, we likely process them one by one or return a long-format DF.

        Let's return a Long-format DataFrame: index=[Date, Symbol], columns=[Features...]
    """
    features_list = []

    # Pre-calculate common indicators
    atr_df = calculate_atr(prices, window=14)
    rsi_df = pd.DataFrame()
    for col in prices.columns:
        rsi_df[col] = calculate_rsi(prices[col])

    ma20 = prices.rolling(20).mean()
    ma50 = prices.rolling(50).mean()
    ma200 = prices.rolling(200).mean()

    vol20 = prices.pct_change().rolling(20).std() * np.sqrt(252)

    # Process each symbol
    for symbol in prices.columns:
        df = pd.DataFrame(index=prices.index)

        # 1. Trend Features
        df["price_vs_ma20"] = prices[symbol] / ma20[symbol] - 1
        df["price_vs_ma50"] = prices[symbol] / ma50[symbol] - 1
        df["price_vs_ma200"] = prices[symbol] / ma200[symbol] - 1

        # 2. Momentum Features
        df["mom_1m"] = prices[symbol].pct_change(20)
        df["mom_3m"] = prices[symbol].pct_change(60)
        df["mom_6m"] = prices[symbol].pct_change(120)

        # Rolling Slope (expensive, maybe optimized later)
        # For now, just vectorized approx or skip loop if possible.
        # Let's skip slope loop for speed in this MVP, rely on simple momentum.

        # 3. Volatility
        df["vol_annual"] = vol20[symbol]
        df["atr_pct"] = atr_df[symbol] / prices[symbol]

        # 4. RSI
        df["rsi"] = rsi_df[symbol] / 100.0  # Normalize to 0-1

        # 5. Sector Momentum (if map provided)
        if sector_map and symbol in sector_map:
            # We assume sector ETF prices are also in `prices` df or we need to pass them separate?
            # For simplicity, assuming sector ETFs are NOT in `prices` passed here usually,
            # unless `prices` contains everything.
            # If we don't have sector data here easily, we skip or pass it in.
            # Let's skip complex sector interaction for this base feature set for now.
            pass

        df["symbol"] = symbol
        features_list.append(df)

    full_features = pd.concat(features_list)
    # Ensure index name is 'date' for consistent reset_index
    full_features.index.name = "date"
    # Transform to [Date, Symbol] index
    full_features = full_features.reset_index().set_index(["date", "symbol"]).sort_index()

    return full_features


def create_dataset(
    prices: pd.DataFrame, forward_window: int = 20, binary_target: bool = True
) -> pd.DataFrame:
    """
    Create a dataset for training: Features + Target

    Args:
        prices: OHLCV or Close prices
        forward_window: Days to look ahead for target
        binary_target: If True, target is 1 if ret > 0 else 0.
    """
    # 1. Generate Features
    X = generate_features(prices)

    # 2. Generate Targets
    # We need to calculate forward return for each stock-date
    y_list = []

    for symbol in prices.columns:
        # Forward return: Price(t+N) / Price(t) - 1
        # Shift -N to align future value to current row
        fwd_ret = prices[symbol].shift(-forward_window) / prices[symbol] - 1

        if binary_target:
            target = (fwd_ret > 0.0).astype(int)
        else:
            target = fwd_ret

        # We lose last N rows
        target = target.to_frame(name="target")
        target["symbol"] = symbol
        target["date"] = prices.index
        y_list.append(target.set_index(["date", "symbol"]))

    y = pd.concat(y_list).sort_index()

    # 3. Combine
    dataset = X.join(y, how="inner").dropna()

    return dataset
