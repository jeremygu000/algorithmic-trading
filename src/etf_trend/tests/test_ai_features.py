
import pytest
import numpy as np
import pandas as pd
from etf_trend.features.pattern_match import find_similar_patterns
from etf_trend.features.trend_pred import predict_next_trend

# =============================================================================
# 形态匹配 (Pattern Match) 测试
# =============================================================================

@pytest.fixture
def sine_wave_data():
    """
    生成一个正弦波数据作为测试用例
    包含 500 个点，周期为 50
    """
    x = np.linspace(0, 50 * np.pi, 500)
    return pd.Series(np.sin(x))

def test_pattern_match_exact_find(sine_wave_data):
    """
    测试：完全相同的形态应该被找到
    
    场景：
    - 历史数据是一个长正弦波
    - 当前数据是该正弦波的最后一段 (例如一个完整波峰)
    - 预期：算法应该在历史中找到完全一样的波峰 (距离接近0)
    """
    history = sine_wave_data
    # 取最后 60 个点作为当前形态
    current = sine_wave_data.iloc[-60:]
    
    # 搜索范围排除最后 20 天 (future_window) + 60 天 (current window)
    # 这里我们构造一个必定能找到的情况：
    # history 有很多周期，前面的周期应该和最后的周期形状一致
    
    result = find_similar_patterns(
        current_prices=current,
        history_prices=history,
        window=60,
        top_k=5,
        future_window=20
    )
    
    # 验证
    assert result["similar_patterns_count"] == 5
    assert result["confidence_score"] > 0.7  # 应该非常相似
    assert "DTW匹配" in result["projection"]

def test_pattern_match_insufficient_data():
    """
    测试：数据不足时的处理
    
    场景：
    - 当前数据长度小于窗口长度
    - 预期：返回默认空结果，不报错
    """
    short_data = pd.Series([1, 2, 3])
    result = find_similar_patterns(short_data, short_data, window=10)
    
    assert result["similar_patterns_count"] == 0
    assert result["projection"] == "数据不足"

# =============================================================================
# 趋势预测 (Trend Prediction) 测试
# =============================================================================

def test_trend_pred_upward():
    """
    测试：明显的上升趋势
    
    场景：
    - 构造一个线性上升序列 [0, 1, 2, ..., 29]
    - 预期：斜率 > 0，预测价格 > 当前价格
    """
    prices = pd.Series(range(30))
    result = predict_next_trend(prices, lookback_days=20, forecast_days=5)
    
    assert result["slope"] > 0
    assert result["target_price_5d"] > result["current_price"]
    assert "上升" in result["description"]
    assert result["r_squared"] > 0.95  # 完美线性

def test_trend_pred_downward():
    """
    测试：明显的下降趋势
    
    场景：
    - 构造一个线性下降序列 [30, 29, ..., 1]
    - 预期：斜率 < 0，预测价格 < 当前价格
    """
    prices = pd.Series(range(30, 0, -1))
    result = predict_next_trend(prices, lookback_days=20, forecast_days=5)
    
    assert result["slope"] < 0
    assert result["target_price_5d"] < result["current_price"]
    assert "下降" in result["description"]

def test_trend_pred_insufficient_data():
    """
    测试：数据不足时的处理
    """
    prices = pd.Series([1, 2, 3])
    result = predict_next_trend(prices, lookback_days=10)
    
    assert result["description"] == "数据不足"
    assert result["target_price_5d"] == 0.0
