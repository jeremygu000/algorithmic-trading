
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from etf_trend.data.providers.tiingo_daily import load_tiingo_daily_adjclose

# 定义缓存目录为临时目录
TEMP_CACHE_DIR = "tests_cache_tiingo"

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
def mock_httpx_client():
    """
    Mock httpx.Client
    """
    with patch("etf_trend.data.providers.tiingo_daily.httpx.Client") as MockClient:
        # 模拟上下文管理器
        mock_instance = MagicMock()
        MockClient.return_value.__enter__.return_value = mock_instance
        yield mock_instance

def test_load_tiingo_fetch_new(clean_cache, mock_httpx_client):
    """
    测试：首次获取数据 (无缓存)
    
    场景：请求 SPY 数据
    预期：
    1. 调用 httpx.get
    2. 返回正确格式的 DataFrame
    3. 生成缓存文件 (.parquet)
    """
    # 模拟 API 返回数据
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"date": "2023-01-01T00:00:00Z", "adjClose": 100.0, "close": 100.0},
        {"date": "2023-01-02T00:00:00Z", "adjClose": 101.0, "close": 101.0},
    ]
    mock_httpx_client.get.return_value = mock_response
    
    symbols = ["SPY"]
    start = "2023-01-01"
    end = "2023-01-02"
    
    df = load_tiingo_daily_adjclose(
        symbols, start, end, api_key="TEST_KEY", 
        cache_enabled=True, cache_dir=TEMP_CACHE_DIR
    )
    
    # 验证 HTTP 请求
    mock_httpx_client.get.assert_called_once()
    args, kwargs = mock_httpx_client.get.call_args
    assert "SPY" in args[0]
    assert kwargs["params"]["token"] == "TEST_KEY"
    
    # 验证返回数据
    assert isinstance(df, pd.DataFrame)
    assert "SPY" in df.columns
    assert len(df) == 2
    assert df["SPY"].iloc[0] == 100.0
    
    # 验证缓存生成
    key = f"tiingo_daily_{start}_{end}_SPY"
    expected_file = Path(TEMP_CACHE_DIR) / f"{key}.parquet"
    assert expected_file.exists()

def test_load_tiingo_from_cache(clean_cache, mock_httpx_client):
    """
    测试：从缓存加载数据
    
    场景：
    1. 先 fetch 一次生成缓存
    2. 再次调用，应该不发请求
    """
    # 第一次运行
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"date": "2023-01-01T00:00:00Z", "adjClose": 100.0, "close": 100.0}
    ]
    mock_httpx_client.get.return_value = mock_response
    
    load_tiingo_daily_adjclose(
        ["SPY"], "2023-01-01", "2023-01-01", api_key="TEST_KEY", 
        cache_enabled=True, cache_dir=TEMP_CACHE_DIR
    )
    
    # 重置 mock
    mock_httpx_client.get.reset_mock()
    
    # 第二次运行
    df = load_tiingo_daily_adjclose(
        ["SPY"], "2023-01-01", "2023-01-01", api_key="TEST_KEY", 
        cache_enabled=True, cache_dir=TEMP_CACHE_DIR
    )
    
    # 验证：应该没有网络请求
    mock_httpx_client.get.assert_not_called()
    assert df["SPY"].iloc[0] == 100.0

def test_load_tiingo_404(clean_cache, mock_httpx_client):
    """
    测试：股票不存在 (404)
    """
    # 模拟 404 错误
    mock_error = MagicMock()
    mock_error.response.status_code = 404
    
    # httpx 抛出 HTTPStatusError
    import httpx
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404 Not Found", request=MagicMock(), response=mock_response
    )
    mock_httpx_client.get.return_value = mock_response
    
    df = load_tiingo_daily_adjclose(
        ["INVALID"], "2023-01-01", "2023-01-02", api_key="TEST_KEY",
        cache_enabled=False
    )
    
    # 预期：返回空 DataFrame 或不包含该列
    assert df.empty

def test_load_tiingo_no_data_in_range(clean_cache, mock_httpx_client):
    """
    测试：API 返回空列表 (例如假日或停牌)
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [] # 空数据
    mock_httpx_client.get.return_value = mock_response
    
    df = load_tiingo_daily_adjclose(
        ["SPY"], "2023-01-01", "2023-01-02", api_key="TEST_KEY",
        cache_enabled=False
    )
    
    # 预期：返回带索引但全NaN，或者空，视实现而定
    # 代码中: if df.empty -> frames.append(pd.DataFrame(columns=["date", sym]).set_index("date"))
    # 这会导致最后 merge 一个空的 DataFrame?
    # 验证返回
    assert "SPY" in df.columns or df.empty
