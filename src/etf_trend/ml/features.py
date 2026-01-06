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
    rsi7_df = pd.DataFrame()
    rsi21_df = pd.DataFrame()
    for col in prices.columns:
        rsi_df[col] = calculate_rsi(prices[col], window=14)
        rsi7_df[col] = calculate_rsi(prices[col], window=7)
        rsi21_df[col] = calculate_rsi(prices[col], window=21)

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
        df["mom_5d"] = prices[symbol].pct_change(5)  # Phase 5: Short-term momentum

        # 3. Volatility
        df["vol_annual"] = vol20[symbol]
        df["atr_pct"] = atr_df[symbol] / prices[symbol]

        # 4. RSI (Multiple periods - Phase 5)
        df["rsi"] = rsi_df[symbol] / 100.0  # Normalize to 0-1
        df["rsi7"] = rsi7_df[symbol] / 100.0
        df["rsi21"] = rsi21_df[symbol] / 100.0

        # 5. MACD (Phase 5)
        from etf_trend.features.indicators import calculate_macd, calculate_bollinger_bands

        macd_df = calculate_macd(prices[symbol])
        df["macd_hist"] = macd_df["hist"] / prices[symbol]  # Normalize

        # 6. Bollinger Bands %B (Phase 5)
        bb_df = calculate_bollinger_bands(prices[symbol])
        df["bb_pct"] = (prices[symbol] - bb_df["lower"]) / (bb_df["upper"] - bb_df["lower"])

        # 7. Multi-MA Alignment (Phase 5)
        # 1 if bullish (price > ma20 > ma50 > ma200), -1 if bearish, 0 otherwise
        bullish = (prices[symbol] > ma20[symbol]) & (ma20[symbol] > ma50[symbol])
        bearish = (prices[symbol] < ma20[symbol]) & (ma20[symbol] < ma50[symbol])
        df["ma_alignment"] = bullish.astype(int) - bearish.astype(int)

        # 8. Cross-Features (Phase 5)
        df["mom_rsi"] = df["mom_1m"] * df["rsi"]  # Momentum-RSI interaction
        df["trend_vol"] = df["price_vs_ma50"] * df["vol_annual"]  # Trend-Vol interaction

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
