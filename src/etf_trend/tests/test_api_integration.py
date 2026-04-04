import matplotlib

# 强制使用 Agg 后端，避免在测试中启动 GUI
matplotlib.use("Agg")

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
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

    df = pd.DataFrame({"AAPL": prices, "SPY": spy}, index=dates)
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
            "sector": "Technology",
        }
    }


@pytest.fixture
def trend_scan_prices():
    """构造用于趋势扫描的模拟数据 (10天)."""
    dates = pd.date_range(end=date.today(), periods=10, freq="B")
    # AAPL: 连续上涨
    aapl = np.arange(100, 110, dtype=float)
    # MSFT: 连续下跌
    msft = np.arange(200, 190, -1, dtype=float)
    # GOOGL: 震荡
    googl = np.array([50, 51, 50, 52, 51, 52, 51, 53, 52, 53], dtype=float)

    return pd.DataFrame({"AAPL": aapl, "MSFT": msft, "GOOGL": googl}, index=dates)


@pytest.fixture
def picks_size_prices():
    """构造用于 picks 市值筛选的模拟数据."""
    dates = pd.date_range(end=date.today(), periods=300, freq="B")
    aapl = np.linspace(100, 160, 300)
    jnj = np.linspace(80, 75, 300)
    spy = np.linspace(300, 320, 300)
    return pd.DataFrame({"AAPL": aapl, "JNJ": jnj, "SPY": spy}, index=dates)


@patch("etf_trend.api.main.load_prices_with_fallback")
@patch("etf_trend.api.main.load_yahoo_fundamentals")
@patch("etf_trend.api.main.RegimeEngine")
def test_analyze_stock_endpoint(
    MockRegimeEngine, mock_load_fund, mock_load_prices, mock_prices, mock_fundamentals
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
        regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0}
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

    # Check OHLCV data (replaces the old chart_base64)
    assert "ohlcv" in data
    assert isinstance(data["ohlcv"], list)


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
    MockRegimeEngine, mock_load_fund, mock_load_prices, mock_prices, mock_fundamentals
):
    """
    测试 /api/picks 端点 (基本烟雾测试)
    """
    mock_load_prices.return_value = mock_prices
    mock_load_fund.return_value = mock_fundamentals

    mock_engine_instance = MockRegimeEngine.return_value
    mock_engine_instance.detect.return_value = RegimeState(
        regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0}
    )

    response = client.get("/api/picks")

    assert response.status_code == 200
    data = response.json()

    assert data["regime"] == "RISK_ON"
    assert "picks" in data
    assert isinstance(data["picks"], list)


@patch("etf_trend.api.services.trend_scanner.load_prices_with_fallback")
def test_trend_scan_up_endpoint(mock_load_prices, trend_scan_prices):
    """测试 /api/stocks/trend-scan 上涨扫描."""
    mock_load_prices.return_value = trend_scan_prices

    response = client.get("/api/stocks/trend-scan?k=5&t=up")
    assert response.status_code == 200

    data = response.json()
    assert data["k"] == 5
    assert data["trend"] == "up"
    assert data["matched_count"] == len(data["stocks"])

    symbols = [item["symbol"] for item in data["stocks"]]
    assert "AAPL" in symbols
    assert "MSFT" not in symbols


@patch("etf_trend.api.services.trend_scanner.load_prices_with_fallback")
def test_trend_scan_down_endpoint(mock_load_prices, trend_scan_prices):
    """测试 /api/stocks/trend-scan 下跌扫描."""
    mock_load_prices.return_value = trend_scan_prices

    response = client.get("/api/stocks/trend-scan?k=5&t=down")
    assert response.status_code == 200

    data = response.json()
    assert data["k"] == 5
    assert data["trend"] == "down"

    symbols = [item["symbol"] for item in data["stocks"]]
    assert "MSFT" in symbols
    assert "AAPL" not in symbols


def test_trend_scan_invalid_trend_param():
    """测试趋势参数非法时返回 400."""
    response = client.get("/api/stocks/trend-scan?k=5&t=sideways")

    assert response.status_code == 400
    assert "t 参数" in response.json()["detail"]


@patch("etf_trend.api.main.load_prices_with_fallback")
@patch("etf_trend.api.main.load_yahoo_fundamentals")
@patch("etf_trend.api.main.RegimeEngine")
@patch("etf_trend.api.main.read_symbol_file")
def test_get_stock_picks_size_filter(
    mock_read_symbol_file,
    MockRegimeEngine,
    mock_load_fund,
    mock_load_prices,
    picks_size_prices,
):
    """测试 /api/picks 的市值筛选参数."""
    mock_load_prices.return_value = picks_size_prices
    mock_load_fund.return_value = {
        "AAPL": {"symbol": "AAPL", "marketCap": 200_000_000_000, "averageVolume": 1_000_000},
        "JNJ": {"symbol": "JNJ", "marketCap": 1_000_000_000, "averageVolume": 1_000_000},
    }
    mock_read_symbol_file.side_effect = lambda path: (
        ["JNJ"] if "russell2000" in path else (["AAPL", "JNJ"] if "russell3000" in path else [])
    )

    mock_engine_instance = MockRegimeEngine.return_value
    # 用 RISK_OFF 避免 selector 进入复杂指标计算，聚焦筛选行为
    mock_engine_instance.detect.return_value = RegimeState(
        regime="RISK_OFF", risk_budget=0.2, signals={"trend": -1.0}
    )

    response_all = client.get("/api/picks?size=all")
    response_large = client.get("/api/picks?size=large")
    response_small = client.get("/api/picks?size=small")

    assert response_all.status_code == 200
    assert response_large.status_code == 200
    assert response_small.status_code == 200

    all_data = response_all.json()
    large_data = response_large.json()
    small_data = response_small.json()

    assert all_data["size"] == "all"
    assert large_data["size"] == "large"
    assert small_data["size"] == "small"

    assert all_data["eligible_stock_count"] == 2
    assert large_data["eligible_stock_count"] == 1
    assert small_data["eligible_stock_count"] == 1


def test_get_stock_picks_invalid_size_param():
    """测试 size 参数非法时返回 400."""
    response = client.get("/api/picks?size=mega")
    assert response.status_code == 400
    assert "size 参数" in response.json()["detail"]


@patch("etf_trend.api.main.load_prices_with_fallback")
@patch("etf_trend.api.main.load_yahoo_fundamentals")
@patch("etf_trend.api.main.RegimeEngine")
@patch("etf_trend.api.main.read_symbol_file")
def test_get_stock_picks_small_empty_returns_explain_message(
    mock_read_symbol_file, MockRegimeEngine, mock_load_fund, mock_load_prices
):
    """当 small 筛选后为空时，返回清晰提示与空 picks."""
    dates = pd.date_range(end=date.today(), periods=300, freq="B")
    prices = pd.DataFrame(
        {
            "AAPL": np.linspace(100, 150, 300),
            "SPY": np.linspace(300, 350, 300),
        },
        index=dates,
    )
    mock_load_prices.return_value = prices
    # AAPL 设为大盘，small 下会被过滤掉
    mock_load_fund.return_value = {
        "AAPL": {
            "symbol": "AAPL",
            "marketCap": 2_000_000_000_000,
            "averageVolume": 1_000_000,
        },
    }
    mock_read_symbol_file.side_effect = lambda path: (
        ["XYZ"] if "russell2000" in path else (["AAPL"] if "russell3000" in path else [])
    )

    mock_engine_instance = MockRegimeEngine.return_value
    mock_engine_instance.detect.return_value = RegimeState(
        regime="RISK_ON", risk_budget=1.0, signals={"trend": 1.0}
    )

    response = client.get("/api/picks?size=small")
    assert response.status_code == 200
    data = response.json()

    assert data["size"] == "small"
    assert data["eligible_stock_count"] == 0
    assert data["picks"] == []
    assert "无可用标的" in data["message"]


@patch("etf_trend.api.main.init_db")
def test_watchlist_endpoints(mock_init_db, tmp_path):
    """测试 watchlist 增删查 API (SQLite backend)."""
    import asyncio
    from etf_trend.db.engine import init_db as real_init_db

    db_path = tmp_path / "test.db"
    asyncio.run(real_init_db(f"sqlite+aiosqlite:///{db_path}"))

    # Add
    add_resp = client.post("/api/watchlist", json={"symbol": "pltr"})
    assert add_resp.status_code == 200
    add_data = add_resp.json()
    assert add_data["count"] == 1
    assert add_data["symbols"] == ["PLTR"]

    # Get
    get_resp = client.get("/api/watchlist")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["symbols"] == ["PLTR"]

    # Delete
    del_resp = client.delete("/api/watchlist/PLTR")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["symbols"] == []
