
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from etf_trend.data.providers.yahoo_fundamentals import load_yahoo_fundamentals

# 定义缓存目录为临时目录
TEMP_CACHE_DIR = "tests_cache"

@pytest.fixture
def clean_cache():
    """
    清理测试用的缓存目录
    """
    path = Path(TEMP_CACHE_DIR)
    if path.exists():
        shutil.rmtree(path)
    yield
    if path.exists():
        shutil.rmtree(path)

@pytest.fixture
def mock_yf_ticker():
    """
    Mock yfinance.Ticker 对象
    """
    with patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker:
        # 创建一个 mock 实例
        mock_instance = MagicMock()
        # 设置 .info 属性的返回值
        mock_instance.info = {
            "trailingPE": 25.5,
            "pegRatio": 1.2,
            "priceToBook": 5.0,
            "trailingEps": 4.5,
            "marketCap": 1000000000,
            "sector": "Technology"
        }
        # 当调用 Ticker("AAPL") 时返回这个 mock 实例
        MockTicker.return_value = mock_instance
        yield MockTicker

def test_load_fundamentals_fetch_new(clean_cache, mock_yf_ticker):
    """
    测试：首次获取数据 (无缓存)
    
    预期：
    1. 调用 yf.Ticker
    2. 返回正确的数据结构
    3. 生成缓存文件
    """
    symbols = ["AAPL"]
    result = load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)

    # 验证是否调用了 yfinance
    mock_yf_ticker.assert_called_with("AAPL")

    # 验证返回数据
    data = result["AAPL"]
    assert data["symbol"] == "AAPL"
    assert data["peRatio"] == 25.5
    assert data["sector"] == "Technology"

    # 验证缓存文件是否生成
    # 文件名格式: yahoo_fund_AAPL_YYYYMMDD.json
    today = pd.Timestamp.now().strftime('%Y%m%d')
    expected_file = Path(TEMP_CACHE_DIR) / f"yahoo_fund_AAPL_{today}.json"
    assert expected_file.exists()

def test_load_fundamentals_from_cache(clean_cache, mock_yf_ticker):
    """
    测试：从缓存加载数据
    
    场景：
    1. 先运行一次生成缓存
    2. 再次运行，应该不调用 yfinance
    """
    symbols = ["AAPL"]

    # 第一次运行
    load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)

    # 重置 mock 调用计数
    mock_yf_ticker.reset_mock()

    # 第二次运行
    result = load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)

    # 验证：应该没有调用 yfinance
    mock_yf_ticker.assert_not_called()

    # 验证数据依然正确 (来自缓存)
    assert result["AAPL"]["peRatio"] == 25.5

def test_load_fundamentals_error_handling(clean_cache):
    """
    测试：yfinance 报错时的处理
    
    场景：Mock yf.Ticker 抛出异常
    预期：返回 None 填充的默认结构，程序不崩溃
    """
    with patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker:
        MockTicker.side_effect = Exception("Network Error")

        result = load_yahoo_fundamentals(["ERROR_STOCK"], cache_enabled=False)

        assert "ERROR_STOCK" in result
        assert result["ERROR_STOCK"]["peRatio"] is None
        assert result["ERROR_STOCK"]["symbol"] == "ERROR_STOCK"
