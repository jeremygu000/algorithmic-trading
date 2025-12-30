
import pytest
import pandas as pd
import numpy as np
from etf_trend.features.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands

@pytest.fixture
def sample_price_series():
    """
    生成一个简单的价格序列用于测试
    """
    # 构造一个 100 天的随机漫步价格序列
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    price = 100 * np.cumprod(1 + returns)
    return pd.Series(price)

@pytest.fixture
def trend_price_series():
    """
    生成一个明显的单边趋势序列
    """
    # 线性增长：100, 101, 102...
    return pd.Series(range(100, 150), dtype=float)

# =============================================================================
# RSI 测试
# =============================================================================

def test_rsi_calculation_basic(sample_price_series):
    """
    测试 RSI 基本计算
    
    预期：
    1. 返回结果应该是 pd.Series
    2. 长度应与输入一致
    3. 值范围应在 0-100 之间
    """
    rsi = calculate_rsi(sample_price_series, window=14)
    
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == len(sample_price_series)
    assert rsi.min() >= 0
    assert rsi.max() <= 100

def test_rsi_trend_up(trend_price_series):
    """
    测试单边上涨趋势的 RSI
    
    场景：价格一直涨 100, 101, 102...
    预期：
    - Gain > 0, Loss = 0
    - RS = inf
    - RSI 应该接近 100
    """
    rsi = calculate_rsi(trend_price_series, window=14)
    
    # 稍微留点余量，因为初始阶段可能有 fillna(50) 或者平滑过程
    # 稳定后 RSI 应该是 100
    assert rsi.iloc[-1] > 99.0

# =============================================================================
# MACD 测试
# =============================================================================

def test_macd_structure(sample_price_series):
    """
    测试 MACD 返回结构
    
    预期：
    1. 返回 DataFrame
    2. 包含 'macd', 'signal', 'hist' 三列
    """
    df = calculate_macd(sample_price_series)
    
    assert isinstance(df, pd.DataFrame)
    assert 'macd' in df.columns
    assert 'signal' in df.columns
    assert 'hist' in df.columns
    assert len(df) == len(sample_price_series)

def test_macd_crossover_logic():
    """
    测试 MACD 金叉/死叉逻辑
    
    场景：构造一个先跌后涨的V型反转
    预期：
    - 下跌段：MACD < Signal (Hist < 0)
    - 上涨段：MACD > Signal (Hist > 0)
    """
    # 构造 V 型走势： 20, 19, ..., 10, 11, ..., 20
    down = np.linspace(20, 10, 20)
    up = np.linspace(10, 20, 20)
    prices = pd.Series(np.concatenate([down, up]))
    
    df = calculate_macd(prices, fast=5, slow=10, signal=5)
    
    # 在下跌末段 (例如第15天)，Hist 应该是负的
    assert df['hist'].iloc[15] < 0
    
    # 在上涨末段 (例如第35天)，Hist 应该是正的
    assert df['hist'].iloc[35] > 0

# =============================================================================
# 布林带 (Bollinger Bands) 测试
# =============================================================================

def test_bollinger_bands_logic(sample_price_series):
    """
    测试布林带逻辑关系
    
    预期：
    1. Upper > Middle > Lower
    2. Upper - Middle == Middle - Lower (对称)
    """
    df = calculate_bollinger_bands(sample_price_series, window=20, num_std=2)
    
    # 去除 NaN (前20天无法计算)
    valid_df = df.dropna()
    
    assert (valid_df['upper'] >= valid_df['middle']).all()
    assert (valid_df['middle'] >= valid_df['lower']).all()
    
    # 验证对称性 (允许浮点误差)
    upper_diff = valid_df['upper'] - valid_df['middle']
    lower_diff = valid_df['middle'] - valid_df['lower']
    
    # 判断两个 Series 是否近似相等
    pd.testing.assert_series_equal(upper_diff, lower_diff, check_names=False)

def test_bollinger_bands_width_change():
    """
    测试布林带带宽随波动率变化
    
    场景：前段平稳，后段剧烈波动
    预期：后段带宽 (Upper - Lower) > 前段带宽
    """
    # 前50天平稳 (std小)，后50天波动大 (std大)
    part1 = np.ones(50) * 100  # 极度平稳，std=0
    # 为了避免 std=0 导致计算问题，加微小噪音
    part1 += np.random.normal(0, 0.1, 50)
    
    part2 = np.random.normal(100, 5, 50) # 波动大
    
    prices = pd.Series(np.concatenate([part1, part2]))
    
    df = calculate_bollinger_bands(prices, window=10)
    
    width = df['upper'] - df['lower']
    
    avg_width_part1 = width.iloc[10:50].mean()
    avg_width_part2 = width.iloc[60:].mean()
    
    assert avg_width_part2 > avg_width_part1 * 10  # 波动率激增，带宽应显著变宽
