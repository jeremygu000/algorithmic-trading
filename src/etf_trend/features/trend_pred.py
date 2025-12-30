
import numpy as np
import pandas as pd
from typing import TypedDict
from sklearn.linear_model import LinearRegression

class TrendPrediction(TypedDict):
    current_price: float
    target_price_5d: float
    predicted_change_pct: float
    slope: float
    r_squared: float
    description: str

def predict_next_trend(
    prices: pd.Series,
    lookback_days: int = 20,
    forecast_days: int = 5
) -> TrendPrediction:
    """
    基于线性回归的短期趋势预测
    
    原理：
    对最近 lookback_days 天的价格进行线性拟合，
    并外推 forecast_days 天作为理论目标价。
    
    Args:
        prices: 价格序列
        lookback_days: 回溯天数 (默认20天，一个月)
        forecast_days: 预测天数 (默认5天，一周)
        
    Returns:
        TrendPrediction
    """
    if len(prices) < lookback_days:
        return {
            "current_price": 0.0,
            "target_price_5d": 0.0,
            "predicted_change_pct": 0.0,
            "slope": 0.0,
            "r_squared": 0.0,
            "description": "数据不足"
        }
        
    # 准备数据
    recent_prices = prices.iloc[-lookback_days:]
    y = recent_prices.values.reshape(-1, 1)
    X = np.arange(len(y)).reshape(-1, 1)
    
    # 线性回归
    model = LinearRegression()
    model.fit(X, y)
    
    # 预测
    # 下一个点是 lookback_days + forecast_days - 1
    # 但我们基准是最后一个实盘点 => index = len(X) - 1
    # 预测点是: (len(X) - 1) + forecast_days
    future_X = np.array([[len(X) - 1 + forecast_days]])
    predicted_price = float(model.predict(future_X)[0][0])
    
    current_price = float(y[-1][0])
    slope = float(model.coef_[0][0])
    score = float(model.score(X, y))
    
    change_pct = (predicted_price / current_price) - 1.0
    
    # 描述
    strength = "强" if abs(slope/current_price) > 0.005 else "弱"
    direction = "上升" if slope > 0 else "下降"
    
    if score < 0.3:
        desc = "趋势不明显(震荡)"
    else:
        desc = f"{strength}{direction}趋势 (R²={score:.2f})"
        
    return {
        "current_price": current_price,
        "target_price_5d": predicted_price,
        "predicted_change_pct": change_pct,
        "slope": slope,
        "r_squared": score,
        "description": desc
    }
