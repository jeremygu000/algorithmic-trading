import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from etf_trend.data.providers.yahoo_fundamentals import load_yahoo_fundamentals

TEMP_CACHE_DIR = "tests_cache"

_NO_LOCAL = ({}, ["AAPL"])
_NO_LOCAL_ERROR = ({}, ["ERROR_STOCK"])


@pytest.fixture
def clean_cache():
    path = Path(TEMP_CACHE_DIR)
    if path.exists():
        shutil.rmtree(path)
    yield
    if path.exists():
        shutil.rmtree(path)


@pytest.fixture
def mock_yf_ticker():
    with patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker:
        mock_instance = MagicMock()
        mock_instance.info = {
            "trailingPE": 25.5,
            "pegRatio": 1.2,
            "priceToBook": 5.0,
            "trailingEps": 4.5,
            "marketCap": 1000000000,
            "sector": "Technology",
        }
        MockTicker.return_value = mock_instance
        yield MockTicker


@pytest.fixture
def no_local_data():
    with patch(
        "etf_trend.data.providers.yahoo_fundamentals.load_local_fundamentals",
        return_value=_NO_LOCAL,
    ):
        yield


def test_load_fundamentals_fetch_new(clean_cache, no_local_data, mock_yf_ticker):
    symbols = ["AAPL"]
    result = load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)

    mock_yf_ticker.assert_called_with("AAPL")

    data = result["AAPL"]
    assert data["symbol"] == "AAPL"
    assert data["peRatio"] == 25.5
    assert data["sector"] == "Technology"

    today = pd.Timestamp.now().strftime("%Y%m%d")
    expected_file = Path(TEMP_CACHE_DIR) / f"yahoo_fund_AAPL_{today}.json"
    assert expected_file.exists()


def test_load_fundamentals_from_cache(clean_cache, no_local_data, mock_yf_ticker):
    symbols = ["AAPL"]

    load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)
    mock_yf_ticker.reset_mock()

    result = load_yahoo_fundamentals(symbols, cache_enabled=True, cache_dir=TEMP_CACHE_DIR)

    mock_yf_ticker.assert_not_called()
    assert result["AAPL"]["peRatio"] == 25.5


def test_load_fundamentals_error_handling(clean_cache):
    with (
        patch(
            "etf_trend.data.providers.yahoo_fundamentals.load_local_fundamentals",
            return_value=_NO_LOCAL_ERROR,
        ),
        patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker,
    ):
        MockTicker.side_effect = Exception("Network Error")

        result = load_yahoo_fundamentals(["ERROR_STOCK"], cache_enabled=False)

        assert "ERROR_STOCK" in result
        assert result["ERROR_STOCK"]["peRatio"] is None
        assert result["ERROR_STOCK"]["symbol"] == "ERROR_STOCK"


def test_load_fundamentals_from_local_parquet():
    local_data = {
        "AAPL": {
            "symbol": "AAPL",
            "peRatio": 28.5,
            "pegRatio": 2.1,
            "pbRatio": 48.5,
            "trailingEPS": 6.42,
            "returnOnEquity": 1.47,
            "grossMargins": 0.45,
            "debtToEquity": 176.3,
            "earningsGrowth": 0.08,
            "marketCap": 3000000000000,
            "averageVolume": 54000000,
            "sector": "Technology",
        }
    }
    with (
        patch(
            "etf_trend.data.providers.yahoo_fundamentals.load_local_fundamentals",
            return_value=(local_data, []),
        ),
        patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker,
    ):
        result = load_yahoo_fundamentals(["AAPL"], cache_enabled=False)

        MockTicker.assert_not_called()
        assert result["AAPL"]["peRatio"] == 28.5
        assert result["AAPL"]["returnOnEquity"] == 1.47
        assert result["AAPL"]["sector"] == "Technology"


def test_load_fundamentals_hybrid_local_and_api():
    local_data = {
        "AAPL": {
            "symbol": "AAPL",
            "peRatio": 28.5,
            "returnOnEquity": 1.47,
            "grossMargins": 0.45,
            "debtToEquity": 176.3,
            "earningsGrowth": 0.08,
            "marketCap": 3000000000000,
            "averageVolume": 54000000,
            "sector": "Technology",
        }
    }
    with (
        patch(
            "etf_trend.data.providers.yahoo_fundamentals.load_local_fundamentals",
            return_value=(local_data, ["MSFT"]),
        ),
        patch("etf_trend.data.providers.yahoo_fundamentals.yf.Ticker") as MockTicker,
    ):
        mock_instance = MagicMock()
        mock_instance.info = {
            "trailingPE": 35.0,
            "pegRatio": 2.5,
            "sector": "Technology",
            "marketCap": 2500000000000,
            "averageVolume": 30000000,
        }
        MockTicker.return_value = mock_instance

        result = load_yahoo_fundamentals(["AAPL", "MSFT"], cache_enabled=False)

        MockTicker.assert_called_once_with("MSFT")
        assert result["AAPL"]["peRatio"] == 28.5
        assert result["MSFT"]["peRatio"] == 35.0
