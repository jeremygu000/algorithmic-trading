from __future__ import annotations
import pandas as pd


def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """
    计算相对强弱指标 (RSI)

    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)  # 填充初始值


def calculate_macd(
    prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """
    计算异同移动平均线 (MACD)

    Returns:
        DataFrame with columns: ['macd', 'signal', 'hist']
    """
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - signal_line

    return pd.DataFrame({"macd": macd, "signal": signal_line, "hist": hist})


def calculate_bollinger_bands(
    prices: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """
    计算布林带 (Bollinger Bands)

    Returns:
        DataFrame with columns: ['middle', 'upper', 'lower']
    """
    middle = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower})
