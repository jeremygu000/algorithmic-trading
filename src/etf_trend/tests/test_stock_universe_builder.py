import pandas as pd

from etf_trend.api.services.stock_universe import StockUniverseBuilder
from etf_trend.config.settings import AppConfig


def test_stock_universe_builder_static_mode():
    cfg = AppConfig.model_validate(
        {
            "universe": {
                "stock_symbols": ["AAA", "BBB"],
                "stock_universe_mode": "static",
            }
        }
    )
    prices = pd.DataFrame({"AAA": [10, 11, 12], "BBB": [20, 21, 22]})
    builder = StockUniverseBuilder(cfg)

    result = builder.build(prices=prices, fundamentals={})

    assert result.mode == "static"
    assert result.input_count == 2
    assert result.output_count == 2
    assert result.symbols == ["AAA", "BBB"]


def test_stock_universe_builder_dynamic_filters(tmp_path):
    cfg = AppConfig.model_validate(
        {
            "universe": {
                "stock_universe_mode": "dynamic",
                "dynamic_stock_symbols": ["LQ", "ILLQ", "LOWP", "SHORT"],
                "russell_3000_symbols_file": str(tmp_path / "r3000.txt"),
                "dynamic_min_history_days": 5,
                "dynamic_min_price": 10.0,
                "dynamic_min_avg_dollar_volume": 1000.0,
                "dynamic_max_symbols": 10,
            }
        }
    )
    prices = pd.DataFrame(
        {
            "LQ": [10, 11, 12, 13, 14, 20],
            "ILLQ": [10, 11, 12, 13, 14, 20],
            "LOWP": [4, 5, 6, 7, 8, 9],
            "SHORT": [10, 11, 12, 13, None, None],
        }
    )
    fundamentals = {
        "LQ": {"averageVolume": 200},
        "ILLQ": {"averageVolume": 10},
        "LOWP": {"averageVolume": 1000},
        "SHORT": {"averageVolume": 1000},
    }
    builder = StockUniverseBuilder(cfg)

    result = builder.build(prices=prices, fundamentals=fundamentals)

    assert result.mode == "dynamic"
    assert result.input_count == 4
    assert result.output_count == 1
    assert result.symbols == ["LQ"]


def test_stock_universe_builder_dynamic_max_symbols(tmp_path):
    cfg = AppConfig.model_validate(
        {
            "universe": {
                "stock_universe_mode": "dynamic",
                "dynamic_stock_symbols": ["S1", "S2", "S3"],
                "russell_3000_symbols_file": str(tmp_path / "r3000.txt"),
                "dynamic_min_history_days": 3,
                "dynamic_min_price": 1.0,
                "dynamic_min_avg_dollar_volume": 0.0,
                "dynamic_max_symbols": 2,
            }
        }
    )
    prices = pd.DataFrame(
        {
            "S1": [10, 10, 10],
            "S2": [10, 10, 20],
            "S3": [10, 10, 30],
        }
    )
    fundamentals = {
        "S1": {"averageVolume": 100},
        "S2": {"averageVolume": 100},
        "S3": {"averageVolume": 100},
    }
    builder = StockUniverseBuilder(cfg)

    result = builder.build(prices=prices, fundamentals=fundamentals)

    # S3(3000) > S2(2000) > S1(1000), max_symbols=2
    assert result.symbols == ["S3", "S2"]
