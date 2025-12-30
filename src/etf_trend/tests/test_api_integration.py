import matplotlib
# 强制使用 Agg 后端，避免在测试中启动 GUI
matplotlib.use("Agg")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import date

# 导入 API 应用
from etf_trend.api.main import app
from etf_trend.regime.engine import RegimeState

client = TestClient(app)



@pytest.fixture
def mock_prices():
    """构造模拟价格数据 (300天)"""
    dates = pd.date_range(end=date.today(), periods=300, freq="B")
    # 构造 AAPL 上涨趋势: 100 -> 150
    prices = np.linspace(100, 150, 300)
    # 添加 SPY 供 Regime 计算: 300 -> 400
    spy = np.linspace(300, 400, 300)
    
    df = pd.DataFrame({
        "AAPL": prices,
        "SPY": spy
    }, index=dates)
    return df

@pytest.fixture
def mock_fundamentals():
    """构造模拟基本面数据"""
    return {
        "AAPL": {
            "symbol": "AAPL",
            "peRatio": 25.0,
            "pegRatio": 1.2,
            "trailingEPS": 6.0,
            "marketCap": 3000000000000,
            "sector": "Technology"
        }
    }

@patch("etf_trend.api.main.load_prices_with_fallback")
@patch("etf_trend.api.main.load_yahoo_fundamentals")
@patch("etf_trend.api.main.RegimeEngine") 
def test_analyze_stock_endpoint(
    MockRegimeEngine, 
    mock_load_fund, 
    mock_load_prices, 
    mock_prices, 
    mock_fundamentals
):
    """
    测试 /api/stock/{symbol} 端点
    
    场景：
    - 查询 AAPL
    - 确保返回结构包含: technicals, ai_analysis, entry_levels 等
    - 确保 Regime 正确 (RISK_ON)
    """
    # 1. Setup Mocks
    mock_load_prices.return_value = mock_prices
    mock_load_fund.return_value = mock_fundamentals
    
    # Mock RegimeEngine behavior
    mock_engine_instance = MockRegimeEngine.return_value
    mock_engine_instance.detect.return_value = RegimeState(
        regime="RISK_ON",
        risk_budget=1.0,
        signals={"trend": 1.0}
    )
    
    # 2. Call API
    response = client.get("/api/stock/AAPL")
    
    # 3. Assertions
    assert response.status_code == 200
    data = response.json()
    
    # Check Basic Info
    assert data["symbol"] == "AAPL"
    assert data["market_regime"] == "RISK_ON"
    assert data["current_price"] == 150.0
    
    # Check Technicals
    assert "technicals" in data
    tech = data["technicals"]
    assert "rsi" in tech
    assert "macd" in tech
    # 因为是单边上涨，RSI 应该比较高
    assert tech["rsi"] > 50 
    
    # Check AI Analysis
    assert "ai_analysis" in data
    ai = data["ai_analysis"]
    assert "pattern_match" in ai
    assert "trend_prediction" in ai
    
    # Check Fundamentals
    assert "fundamentals" in data
    fund = data["fundamentals"]
    assert fund["peRatio"] == 25.0
    
    # Check Trade Levels
    assert "entry_levels" in data
    assert "stop_levels" in data
    assert "tp_levels" in data
    
    # Check Chart
    assert "chart_base64" in data
    assert len(data["chart_base64"]) > 100 # 应该是比较长的 Base64 字符串

@patch("etf_trend.api.main.load_prices_with_fallback")
def test_stock_not_found(mock_load_prices):
    """测试查询不存在的股票"""
    # 模拟返回空 DataFrame 或不包含该 Symbol
    mock_load_prices.return_value = pd.DataFrame()
    
    response = client.get("/api/stock/INVALID")
    assert response.status_code == 404
    assert "未找到股票" in response.json()["detail"]

@patch("etf_trend.api.main.load_prices_with_fallback")
@patch("etf_trend.api.main.load_yahoo_fundamentals")
@patch("etf_trend.api.main.RegimeEngine")
def test_get_stock_picks_endpoint(
    MockRegimeEngine,
    mock_load_fund,
    mock_load_prices,
    mock_prices,
    mock_fundamentals
):
    """
    测试 /api/picks 端点 (基本烟雾测试)
    """
    mock_load_prices.return_value = mock_prices
    mock_load_fund.return_value = mock_fundamentals
    
    mock_engine_instance = MockRegimeEngine.return_value
    mock_engine_instance.detect.return_value = RegimeState(
        regime="RISK_ON",
        risk_budget=1.0,
        signals={"trend": 1.0}
    )
    
    response = client.get("/api/picks")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["regime"] == "RISK_ON"
    assert "picks" in data
    assert isinstance(data["picks"], list)
