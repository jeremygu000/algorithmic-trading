"""
FastAPI 股票分析服务
====================

提供 RESTful API 接口用于查询股票分析，包括：
- 蜡烛图 (K线图)
- 多级入场/止损/止盈价位
- 技术指标和推荐理由

启动方式：
---------
$ uv run uvicorn etf_trend.api.main:app --reload

API 文档：
---------
启动后访问 http://localhost:8300/docs 查看 Swagger 文档
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
import pandas as pd
import numpy as np
import matplotlib
from pydantic import BaseModel, Field

# 服务端绘图使用非交互后端，避免线程环境触发 GUI backend 错误
matplotlib.use("Agg")
import mplfinance as mpf

# 配置中文字体 (macOS)
matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

from etf_trend.config.settings import EnvSettings, load_config
from etf_trend.analysis.attribution import calculate_alpha_beta
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.data.providers.local_parquet import load_local_daily_ohlcv
from etf_trend.brokers.alpaca_client import AlpacaBroker, OrderResult
from etf_trend.api.ws_manager import ws_manager, get_trade_bridge
from etf_trend.regime.engine import RegimeEngine
from etf_trend.selector.satellite import StockSelector
from etf_trend.execution.executor import TradePlan, TradeExecutor, calculate_atr
from etf_trend.features.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands
from etf_trend.data.providers.yahoo_fundamentals import load_yahoo_fundamentals
from etf_trend.features.pattern_match import find_similar_patterns
from etf_trend.features.trend_pred import predict_next_trend
from etf_trend.api.services import (
    TrendScannerService,
    BeautyShoulderScannerService,
    StockUniverseBuilder,
    add_symbol_to_file,
    read_symbol_file,
    remove_symbol_from_file,
    resolve_symbol_file,
)
from etf_trend.backtest.beauty_shoulder_backtest import BacktestSummary
from etf_trend.backtest.metrics import extended_stats

# 获取配置
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"

# =============================================================================
# Picks 筛选配置
# =============================================================================

PickSizeBucket = Literal["all", "large", "small"]
PICKS_TIINGO_MAX_SYMBOLS = 60
PICKS_AI_MAX_SYMBOLS = 40

PICK_SIZE_ALIASES: dict[str, PickSizeBucket] = {
    "all": "all",
    "全部": "all",
    "large": "large",
    "大盘": "large",
    "大盘股": "large",
    "small": "small",
    "小盘": "small",
    "小盘股": "small",
}
PICK_SIZE_LABEL: dict[PickSizeBucket, str] = {
    "all": "全部",
    "large": "大盘股",
    "small": "小盘股",
}


def _normalize_pick_size(size: str) -> PickSizeBucket:
    normalized = PICK_SIZE_ALIASES.get(size.strip().lower())
    if normalized is None:
        raise ValueError("size 参数仅支持 all/large/small 或 全部/大盘股/小盘股")
    return normalized


def _filter_stock_pool_by_size(
    stock_pool: list[str],
    size: PickSizeBucket,
    russell_2000_symbols: set[str],
    russell_3000_symbols: set[str],
) -> list[str]:
    if size == "all":
        return stock_pool

    if not russell_2000_symbols:
        raise ValueError("Russell 2000 成分文件为空，请先运行刷新脚本")

    filtered: list[str] = []
    for sym in stock_pool:
        in_r2000 = sym in russell_2000_symbols
        in_r3000 = sym in russell_3000_symbols if russell_3000_symbols else True

        if size == "large" and in_r3000 and not in_r2000:
            filtered.append(sym)
        elif size == "small" and in_r2000:
            filtered.append(sym)

    return filtered


class WatchlistSymbolPayload(BaseModel):
    symbol: str = Field(min_length=1, max_length=15)


# =============================================================================
# FastAPI 应用
# =============================================================================

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
    """启动 Alpaca trade stream；关闭时优雅停止。"""
    env = EnvSettings()
    if env.alpaca_api_key and env.alpaca_secret_key:
        bridge = get_trade_bridge(
            api_key=env.alpaca_api_key,
            secret_key=env.alpaca_secret_key,
            paper="paper" in env.alpaca_base_url,
        )
        await bridge.start()
        logger.info("Alpaca trade stream started")
    yield
    from etf_trend.api.ws_manager import trade_bridge

    if trade_bridge is not None:
        await trade_bridge.stop()
        logger.info("Alpaca trade stream stopped")


app = FastAPI(
    title="ETF Trend 股票分析 API",
    description="提供美股分析、蜡烛图、多级买卖点位的 RESTful API",
    version="1.0.0",
    lifespan=lifespan,
)

# 添加 CORS 中间件 (允许 Next.js 前端访问)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3200",
        "http://127.0.0.1:3200",
        "http://etf-trend-frontend:3200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# 健康检查
# =============================================================================


@app.get("/health")
async def health_check():
    """Docker / load-balancer health probe."""
    return {"status": "ok"}


# =============================================================================
# API 端点
# =============================================================================


@app.get("/")
async def root():
    """API 首页"""
    return {
        "name": "ETF Trend 股票分析 API",
        "version": "1.0.0",
        "endpoints": {
            "/api/stock/{symbol}": "查询单个股票分析 (含蜡烛图)",
            "/api/market": "查询市场状态",
            "/api/picks": "获取今日推荐个股列表 (支持 size=all|large|small)",
            "/api/watchlist": "动态观察列表增删查",
            "/api/stocks/trend-scan": "扫描最近 K 日连续上涨/下跌形态的股票",
            "/api/beauty-shoulder": "扫描美人肩形态 (加速→回踩→入场信号)",
            "/api/early-movers": "扫描早期强势股 (20日窗口涨幅 20%-30%)",
            "/api/beauty-shoulder/backtest": "美人肩策略历史回测",
        },
    }


@app.get("/api/market")
async def get_market_status():
    """
    获取当前市场状态

    返回：
    - regime: RISK_ON / NEUTRAL / RISK_OFF
    - risk_budget: 风险预算 (0-1)
    - signals: 各信号值
    """
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        env = EnvSettings()

        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        prices = load_prices_with_fallback(
            cfg.universe.equity_symbols + cfg.universe.defensive_symbols,
            str(start_date),
            str(end_date),
            env.tiingo_api_key,
            cache_enabled=cfg.cache.enabled,
            cache_dir=cfg.cache.dir,
        )
        prices = prices.ffill().dropna(how="all")

        regime_engine = RegimeEngine(
            ma_window=cfg.regime.ma_window,
            momentum_window=cfg.regime.momentum_window,
            vix_threshold=cfg.regime.vix_threshold,
        )
        regime_state = regime_engine.detect(
            prices, vix=None, market_symbol=cfg.universe.market_benchmark
        )

        return {
            "date": str(end_date),
            "regime": regime_state.regime,
            "risk_budget": regime_state.risk_budget,
            "signals": regime_state.signals,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/{symbol}")
async def analyze_stock(symbol: str, days: int = 90):
    """
    单个股票详细分析

    参数：
    - symbol: 股票代码 (如 AAPL, NVDA)
    - days: 蜡烛图显示天数 (默认 90)

    返回：
    - symbol: 股票代码
    - name: 股票名称
    - current_price: 当前价格
    - recommendation: 推荐等级
    - reason: 推荐理由
    - entry_levels: 入场价位
    - stop_levels: 止损价位
    - tp_levels: 止盈目标
    - chart: Base64 编码的蜡烛图
    """
    try:
        symbol = symbol.upper()
        cfg = load_config(str(DEFAULT_CONFIG))

        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        # 个股详情页是高频交互接口，优先保证响应速度。
        # 避免 Tiingo 429 退避导致页面长时间等待，这里直接走 Yahoo 路径。
        stock_tiingo_api_key: str | None = None

        # 获取价格数据
        prices = load_prices_with_fallback(
            [symbol] + cfg.universe.equity_symbols,
            str(start_date),
            str(end_date),
            stock_tiingo_api_key,
            cache_enabled=cfg.cache.enabled,
            cache_dir=cfg.cache.dir,
        )
        prices = prices.ffill().dropna(how="all")

        if symbol not in prices.columns:
            raise HTTPException(status_code=404, detail=f"未找到股票 {symbol}")

        # 获取市场状态
        regime_engine = RegimeEngine(
            ma_window=cfg.regime.ma_window,
            momentum_window=cfg.regime.momentum_window,
            vix_threshold=cfg.regime.vix_threshold,
        )
        regime_state = regime_engine.detect(
            prices, vix=None, market_symbol=cfg.universe.market_benchmark
        )

        # 获取基本面数据
        fundamentals_map = load_yahoo_fundamentals(
            [symbol], cache_enabled=cfg.cache.enabled, cache_dir=cfg.cache.dir
        )
        fund_data = fundamentals_map.get(symbol) or {
            "peRatio": None,
            "pegRatio": None,
            "pbRatio": None,
            "trailingEPS": None,
            "marketCap": None,
            "sector": None,
        }

        # 计算技术指标
        price_series = prices[symbol]
        current_price = float(price_series.iloc[-1])
        ma20 = float(price_series.rolling(20).mean().iloc[-1])
        ma50 = float(price_series.rolling(50).mean().iloc[-1])
        ma200 = float(price_series.rolling(200).mean().iloc[-1])

        # 计算动量
        mom_60d = (
            float((price_series.iloc[-1] / price_series.iloc[-60] - 1) * 100)
            if len(price_series) >= 60
            else 0
        )

        # 计算波动率
        vol = float(price_series.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) * 100)

        # 计算 ATR
        atr_df = calculate_atr(prices[[symbol]], 14)
        atr = float(atr_df[symbol].iloc[-1])

        # 计算高级技术指标 (RSI, MACD, BB)
        rsi_series = calculate_rsi(price_series)
        rsi = float(rsi_series.iloc[-1])

        macd_df = calculate_macd(price_series)
        macd_val = float(macd_df["macd"].iloc[-1])
        macd_signal = float(macd_df["signal"].iloc[-1])
        macd_hist = float(macd_df["hist"].iloc[-1])

        bb_df = calculate_bollinger_bands(price_series)
        bb_upper = float(bb_df["upper"].iloc[-1])
        bb_upper = float(bb_df["upper"].iloc[-1])
        bb_lower = float(bb_df["lower"].iloc[-1])

        # =========================================================================
        # AI/ML 预测分析
        # =========================================================================

        # 1. 相似形态搜索 (KNN)
        ai_pattern = find_similar_patterns(
            price_series,
            price_series.iloc[
                :-20
            ],  # 在历史数据中搜索 (排除最近20天以防过度拟合，其实应该搜非样本)
            window=60,
            future_window=20,
        )

        # 2. 线性趋势预测
        ai_trend = predict_next_trend(price_series, lookback_days=20, forecast_days=5)

        # =========================================================================

        # 生成推荐理由
        reasons = []
        recommendation = "观望"

        if mom_60d > 15:
            reasons.append(f"强劲动量 ({mom_60d:.1f}%)")
        elif mom_60d > 5:
            reasons.append("良好动量")
        elif mom_60d < -10:
            reasons.append("动量较弱")

        if vol < 25:
            reasons.append("低波动高质量")
        elif vol < 35:
            reasons.append("稳健波动")
        else:
            reasons.append("高波动")

        if current_price > ma200:
            reasons.append("趋势强劲")
        else:
            reasons.append("趋势偏弱")

        # RSI 逻辑
        if rsi > 70:
            reasons.append("RSI超买")
        elif rsi < 30:
            reasons.append("RSI超卖")

        # MACD 逻辑
        if macd_hist > 0 and macd_hist > macd_df["hist"].iloc[-2]:
            reasons.append("MACD增强")
        elif macd_hist < 0:
            reasons.append("MACD走弱")

        # 基本面逻辑
        if fund_data["peRatio"] and fund_data["peRatio"] < 25:
            reasons.append(f"低估值(PE {fund_data['peRatio']:.1f})")
        if fund_data["pegRatio"] and fund_data["pegRatio"] < 1.0:
            reasons.append("PEG低估")

        # 确定推荐等级
        signal_strength = 0.5
        if mom_60d > 10 and current_price > ma200:
            signal_strength = 0.8
        elif mom_60d > 5 and current_price > ma50:
            signal_strength = 0.6
        elif mom_60d < 0 or current_price < ma200:
            signal_strength = 0.3

        if signal_strength >= 0.7:
            recommendation = "强烈推荐"
        elif signal_strength >= 0.5:
            recommendation = "推荐"
        else:
            recommendation = "观望"

        reason = f"{recommendation} | {', '.join(reasons)}"

        # 计算多级价位
        entry_moderate = current_price * 0.98
        entry_aggressive = ma20
        entry_conservative = current_price * 0.93

        stop_tight = entry_moderate - (atr * 2.0)
        stop_normal = entry_moderate - (atr * 3.0)
        stop_loose = entry_moderate - (atr * 4.0)

        tp1 = entry_moderate + (atr * 3)
        tp2 = entry_moderate + (atr * 6)
        tp3 = entry_moderate + (atr * 10)

        # 生成蜡烛图
        chart_data = prices[symbol].iloc[-days:]
        chart_df = pd.DataFrame(
            {
                "Open": chart_data.shift(1),
                "High": chart_data.rolling(2).max(),
                "Low": chart_data.rolling(2).min(),
                "Close": chart_data,
                "Volume": 0,
            }
        )
        chart_df = chart_df.dropna()
        chart_df.index = pd.DatetimeIndex(chart_df.index)

        # 计算移动平均线并对齐索引
        ma20_series = prices[symbol].rolling(20).mean()
        ma50_series = prices[symbol].rolling(50).mean()

        # 只保留 chart_df 索引范围内的数据
        ma20_aligned = ma20_series.reindex(chart_df.index)
        ma50_aligned = ma50_series.reindex(chart_df.index)

        # 添加移动平均线 (只在有足够数据时添加)
        addplots = []
        if ma20_aligned.notna().sum() > 10:
            addplots.append(mpf.make_addplot(ma20_aligned, color="blue", width=1))
        if ma50_aligned.notna().sum() > 10:
            addplots.append(mpf.make_addplot(ma50_aligned, color="orange", width=1))

        # 生成图表到内存
        buf = io.BytesIO()

        # 使用英文标题避免字体问题
        stock_name = StockSelector.STOCK_NAMES.get(symbol, symbol)
        # 如果是中文名称，只显示股票代码
        if any("\u4e00" <= c <= "\u9fff" for c in stock_name):
            chart_title = symbol
        else:
            chart_title = f"{symbol} - {stock_name}"

        # 定义关键价位水平线
        hlines_dict = dict(
            hlines=[
                # 入场价位 (绿色)
                entry_aggressive,
                entry_moderate,
                entry_conservative,
                # 止损价位 (红色)
                stop_tight,
                stop_normal,
                stop_loose,
                # 止盈目标 (蓝色)
                tp1,
                tp2,
                tp3,
            ],
            colors=[
                "#22c55e",
                "#22c55e",
                "#22c55e",  # 绿色 - 入场
                "#ef4444",
                "#ef4444",
                "#ef4444",  # 红色 - 止损
                "#3b82f6",
                "#3b82f6",
                "#3b82f6",  # 蓝色 - 止盈
            ],
            linestyle=[
                "--",
                "-",
                ":",  # 入场: 虚线/实线/点线
                "--",
                "-",
                ":",  # 止损
                "--",
                "-",
                ":",  # 止盈
            ],
            linewidths=[0.8, 1.2, 0.8, 0.8, 1.2, 0.8, 0.8, 1.2, 0.8],
        )

        plot_kwargs = dict(
            type="candle",
            style="charles",
            title=chart_title,
            ylabel="Price ($)",
            savefig=dict(fname=buf, dpi=150, format="png"),
            figratio=(14, 8),
            hlines=hlines_dict,
        )
        if addplots:
            plot_kwargs["addplot"] = addplots

        mpf.plot(chart_df, **plot_kwargs)
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()

        return {
            "symbol": symbol,
            "name": StockSelector.STOCK_NAMES.get(symbol, symbol),
            "date": str(end_date),
            "current_price": round(current_price, 2),
            "recommendation": recommendation,
            "reason": reason,
            "technicals": {
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2),
                "ma200": round(ma200, 2),
                "momentum_60d": round(mom_60d, 2),
                "volatility": round(vol, 2),
                "atr": round(atr, 2),
                "rsi": round(rsi, 2),
                "macd": round(macd_val, 2),
                "macd_signal": round(macd_signal, 2),
                "macd_hist": round(macd_hist, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
            },
            "ai_analysis": {
                "pattern_match": ai_pattern,
                "trend_prediction": ai_trend,
            },
            "fundamentals": fund_data,
            "entry_levels": {
                "aggressive": round(entry_aggressive, 2),
                "aggressive_label": "激进入场 (MA20)",
                "moderate": round(entry_moderate, 2),
                "moderate_label": "稳健入场 (回调2%)",
                "conservative": round(entry_conservative, 2),
                "conservative_label": "保守入场 (回调7%)",
            },
            "stop_levels": {
                "tight": round(stop_tight, 2),
                "tight_label": "紧止损 (ATR×2)",
                "normal": round(stop_normal, 2),
                "normal_label": "标准止损 (ATR×3)",
                "loose": round(stop_loose, 2),
                "loose_label": "宽止损 (ATR×4)",
            },
            "tp_levels": {
                "tp1": round(tp1, 2),
                "tp1_label": "TP1 (ATR×3)",
                "tp2": round(tp2, 2),
                "tp2_label": "TP2 (ATR×6)",
                "tp3": round(tp3, 2),
                "tp3_label": "TP3 (ATR×10)",
            },
            "market_regime": regime_state.regime,
            "chart_base64": chart_base64,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/watchlist")
async def get_watchlist():
    """获取动态观察列表（来源于 dynamic_stock_symbols_file）。"""
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        file_path = cfg.universe.dynamic_stock_symbols_file
        symbols = read_symbol_file(file_path)
        return {
            "file": str(resolve_symbol_file(file_path)),
            "count": len(symbols),
            "symbols": symbols,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/watchlist")
async def add_watchlist_symbol(payload: WatchlistSymbolPayload):
    """向动态观察列表添加股票代码。"""
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        file_path = cfg.universe.dynamic_stock_symbols_file
        symbols = add_symbol_to_file(file_path, payload.symbol)
        return {
            "file": str(resolve_symbol_file(file_path)),
            "count": len(symbols),
            "symbols": symbols,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/watchlist/{symbol}")
async def delete_watchlist_symbol(symbol: str):
    """从动态观察列表删除股票代码。"""
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        file_path = cfg.universe.dynamic_stock_symbols_file
        symbols = remove_symbol_from_file(file_path, symbol)
        return {
            "file": str(resolve_symbol_file(file_path)),
            "count": len(symbols),
            "symbols": symbols,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/picks")
async def get_stock_picks(
    size: str = Query(
        default="all",
        description="规模筛选: all/large/small 或 全部/大盘股/小盘股（基于 Russell 2000/3000）",
    )
):
    """
    获取今日推荐个股列表

    返回推荐的所有个股及其多级价位
    """
    try:
        pick_size = _normalize_pick_size(size)

        cfg = load_config(str(DEFAULT_CONFIG))
        env = EnvSettings()

        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        universe_builder = StockUniverseBuilder(cfg)
        base_stock_pool = universe_builder.base_candidates()

        all_symbols = (
            cfg.universe.equity_symbols
            + cfg.universe.defensive_symbols
            + base_stock_pool
            + list(StockSelector.SECTOR_ETF_MAP.values())
        )
        all_symbols = list(set(all_symbols))

        # Tiingo 免费版在批量请求时容易触发 429 限流，导致前端长时间等待。
        # 对 picks 这类大批量接口直接走 Yahoo，可显著降低首屏等待时间。
        tiingo_api_key = (
            env.tiingo_api_key
            if cfg.providers.tiingo.enabled and len(all_symbols) <= PICKS_TIINGO_MAX_SYMBOLS
            else None
        )

        prices = load_prices_with_fallback(
            all_symbols,
            str(start_date),
            str(end_date),
            tiingo_api_key,
            cache_enabled=cfg.cache.enabled,
            cache_dir=cfg.cache.dir,
        )
        prices = prices.ffill().dropna(how="all")

        regime_engine = RegimeEngine(
            ma_window=cfg.regime.ma_window,
            momentum_window=cfg.regime.momentum_window,
            vix_threshold=cfg.regime.vix_threshold,
        )
        regime_state = regime_engine.detect(
            prices, vix=None, market_symbol=cfg.universe.market_benchmark
        )

        available_stocks = [s for s in base_stock_pool if s in prices.columns]
        fundamentals_all = load_yahoo_fundamentals(
            available_stocks, cache_enabled=cfg.cache.enabled, cache_dir=cfg.cache.dir
        )
        universe_result = universe_builder.build(prices=prices, fundamentals=fundamentals_all)

        russell_2000_symbols = set(read_symbol_file(cfg.universe.russell_2000_symbols_file))
        russell_3000_symbols = set(read_symbol_file(cfg.universe.russell_3000_symbols_file))
        filtered_stock_pool = _filter_stock_pool_by_size(
            universe_result.symbols,
            pick_size,
            russell_2000_symbols=russell_2000_symbols,
            russell_3000_symbols=russell_3000_symbols,
        )

        if not filtered_stock_pool:
            return {
                "date": str(end_date),
                "regime": regime_state.regime,
                "risk_budget": regime_state.risk_budget,
                "size": pick_size,
                "size_label": PICK_SIZE_LABEL[pick_size],
                "universe_mode": universe_result.mode,
                "universe_input_count": universe_result.input_count,
                "universe_selected_count": universe_result.output_count,
                "russell2000_count": len(russell_2000_symbols),
                "russell3000_count": len(russell_3000_symbols),
                "eligible_stock_count": 0,
                "is_active": regime_state.regime == "RISK_ON",
                "message": (
                    f"当前股票池在筛选范围【{PICK_SIZE_LABEL[pick_size]}】下无可用标的。"
                    "建议扩大候选池或更新 Russell 指数成分文件。"
                ),
                "picks": [],
            }

        selector = StockSelector(
            stock_pool=filtered_stock_pool,
            mom_windows=cfg.signal.mom_windows,
            mom_weights=cfg.signal.mom_weights,
            vol_lookback=cfg.risk.vol_lookback,
        )

        # 批量进行 AI 预测
        ai_analysis_map = {}
        ai_symbols = filtered_stock_pool[:PICKS_AI_MAX_SYMBOLS]

        # 只对筛选后的前 N 只股票做 AI 预测，其余股票使用中性 AI 分数。
        for sym in ai_symbols:
            series = prices[sym].dropna()
            if len(series) < 80:  # 需要足够数据
                continue

            # 1. DTW
            pattern = find_similar_patterns(series, series.iloc[:-20], window=60, future_window=20)
            # 2. Trend
            trend = predict_next_trend(series, lookback_days=20, forecast_days=5)

            ai_analysis_map[sym] = {"pattern": pattern, "trend": trend}

        result = selector.select(
            prices,
            regime_state,
            use_fundamental=True,
            fundamentals=fundamentals_all,
            ai_analysis=ai_analysis_map,
        )

        executor = TradeExecutor()
        trade_plans = []
        if result.is_active and result.candidates:
            trade_plans = executor.generate_stock_plans(prices, result.candidates)

        return {
            "date": str(end_date),
            "regime": regime_state.regime,
            "risk_budget": regime_state.risk_budget,
            "size": pick_size,
            "size_label": PICK_SIZE_LABEL[pick_size],
            "universe_mode": universe_result.mode,
            "universe_input_count": universe_result.input_count,
            "universe_selected_count": universe_result.output_count,
            "russell2000_count": len(russell_2000_symbols),
            "russell3000_count": len(russell_3000_symbols),
            "eligible_stock_count": len(filtered_stock_pool),
            "ai_analyzed_count": len(ai_analysis_map),
            "is_active": result.is_active,
            "message": f"{result.message}（筛选范围: {PICK_SIZE_LABEL[pick_size]}）",
            "picks": [plan.to_dict() for plan in trade_plans],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/trend-scan")
async def scan_stocks_by_trend(
    k: int = Query(default=5, ge=1, description="连续形态天数，默认 5"),
    t: str = Query(default="up", description="趋势方向: up/down 或 上涨/下跌"),
):
    """
    扫描最近 K 个交易日连续上涨/下跌的股票列表

    参数:
    - k: 连续天数，默认 5
    - t: 趋势方向，支持 up/down 或 上涨/下跌
    """
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        env = EnvSettings()

        scanner = TrendScannerService(cfg, env.tiingo_api_key)
        result = scanner.scan(k=k, t=t)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/beauty-shoulder")
async def scan_beauty_shoulder(
    days: int = Query(default=90, ge=30, le=365, description="Lookback window in days"),
):
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        scanner = BeautyShoulderScannerService(cfg)
        result = scanner.scan_beauty_shoulder(lookback_days=days)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/early-movers")
async def scan_early_movers(
    window: int = Query(default=20, ge=5, le=60, description="Rolling window size in days"),
    min_gain: float = Query(default=20.0, ge=5.0, le=100.0, description="Min gain % (e.g. 20)"),
    max_gain: float = Query(default=30.0, ge=5.0, le=200.0, description="Max gain % (e.g. 30)"),
):
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        scanner = BeautyShoulderScannerService(cfg)
        result = scanner.scan_early_movers(
            window=window,
            min_gain=min_gain / 100.0,
            max_gain=max_gain / 100.0,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _compute_backtest_extended_metrics(trades: list) -> dict | None:
    if not trades:
        return None
    import numpy as np
    import pandas as pd

    rets_2d = pd.Series([t.return_2d / 100.0 for t in trades])
    nav_2d = (1 + rets_2d).cumprod()
    dd_2d = nav_2d / nav_2d.cummax() - 1

    bt_df = pd.DataFrame(
        {
            "port_ret": rets_2d,
            "net_ret": rets_2d,
            "nav": nav_2d,
            "drawdown": dd_2d,
            "turnover": 0.0,
            "cost": 0.0,
        }
    )
    stats = extended_stats(bt_df)

    result = {}
    for k, v in stats.items():
        if isinstance(v, (float, np.floating)):
            result[k] = None if np.isnan(v) or np.isinf(v) else round(float(v), 6)
        else:
            result[k] = int(v) if isinstance(v, (int, np.integer)) else v
    return result


@app.get("/api/beauty-shoulder/backtest")
async def beauty_shoulder_backtest(
    start: str = Query(default="2025-10-01", description="Backtest start date (YYYY-MM-DD)"),
    end: str = Query(default="2026-02-01", description="Backtest end date (YYYY-MM-DD)"),
):
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        scanner = BeautyShoulderScannerService(cfg)
        result = scanner.run_backtest(start=start, end=end)

        def _summary_dict(s: BacktestSummary) -> dict:
            return {
                "period": s.period,
                "total_signals": s.total_signals,
                "win_rate_2d": s.win_rate_2d,
                "win_rate_3d": s.win_rate_3d,
                "avg_return_2d": s.avg_return_2d,
                "avg_return_3d": s.avg_return_3d,
                "median_return_2d": s.median_return_2d,
                "median_return_3d": s.median_return_3d,
                "max_gain_2d": s.max_gain_2d,
                "max_loss_2d": s.max_loss_2d,
                "max_gain_3d": s.max_gain_3d,
                "max_loss_3d": s.max_loss_3d,
            }

        return {
            "start": start,
            "end": end,
            "total_trades": len(result.trades),
            "overall": _summary_dict(result.overall) if result.overall else None,
            "monthly": [_summary_dict(m) for m in result.monthly_stats],
            "extended_metrics": _compute_backtest_extended_metrics(result.trades),
            "trades": [
                {
                    "symbol": t.symbol,
                    "signal_date": t.signal_date,
                    "entry_price": t.entry_price,
                    "exit_date_2d": t.exit_date_2d,
                    "exit_price_2d": t.exit_price_2d,
                    "return_2d": t.return_2d,
                    "exit_date_3d": t.exit_date_3d,
                    "exit_price_3d": t.exit_price_3d,
                    "return_3d": t.return_3d,
                    "phase1_gain": t.phase1_gain,
                    "pullback_depth": t.pullback_depth,
                    "confidence": t.confidence,
                }
                for t in result.trades
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# OHLCV K-Line Data Endpoint
# =============================================================================


@app.get("/api/stock/{symbol}/ohlcv")
async def get_stock_ohlcv(
    symbol: str,
    interval: str = Query(
        default="daily",
        description="K-line interval: daily, weekly, monthly",
    ),
    days: int = Query(
        default=365,
        ge=30,
        le=3650,
        description="Lookback days for daily data",
    ),
):
    """
    返回股票 OHLCV K 线数据 (日K/周K/月K)

    - **symbol**: 股票代码 (e.g. AAPL)
    - **interval**: daily / weekly / monthly
    - **days**: 回看天数 (仅对 daily 有效)
    """
    symbol = symbol.upper().strip()
    if interval not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="interval must be daily, weekly, or monthly")

    try:
        end_date = date.today()
        # For weekly/monthly, load more data so resampling has enough history
        lookback_days = days if interval == "daily" else max(days, 365 * 3)
        start_date = end_date - timedelta(days=lookback_days)

        ohlcv = load_local_daily_ohlcv(
            symbols=[symbol],
            start=str(start_date),
            end=str(end_date),
        )

        if symbol not in ohlcv or ohlcv[symbol].empty:
            raise HTTPException(status_code=404, detail=f"No OHLCV data for {symbol}")

        df = ohlcv[symbol].copy()

        if interval == "weekly":
            df = (
                df.resample("W-FRI")
                .agg(
                    {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }
                )
                .dropna(subset=["Open"])
            )
        elif interval == "monthly":
            df = (
                df.resample("ME")
                .agg(
                    {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }
                )
                .dropna(subset=["Open"])
            )

        # Lightweight-charts expects { time: "YYYY-MM-DD", open, high, low, close }
        candles = []
        for idx, row in df.iterrows():
            candles.append(
                {
                    "time": str(idx.date()),
                    "open": round(float(row["Open"]), 4),
                    "high": round(float(row["High"]), 4),
                    "low": round(float(row["Low"]), 4),
                    "close": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
                }
            )

        return {
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "candles": candles,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Alpaca Trading 端点
# =============================================================================


def _get_broker() -> AlpacaBroker:
    env = EnvSettings()
    if not env.alpaca_api_key or not env.alpaca_secret_key:
        raise HTTPException(status_code=503, detail="Alpaca API keys not configured")
    return AlpacaBroker(
        api_key=env.alpaca_api_key,
        secret_key=env.alpaca_secret_key,
        paper="paper" in env.alpaca_base_url,
    )


class TradeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"] = "buy"
    qty: float = Field(gt=0)
    order_type: Literal["market", "limit", "bracket"] = "market"
    limit_price: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None


class ExecutePlanRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=10)
    order_type: Literal["market", "limit", "bracket"] = "bracket"


def _order_to_dict(r: OrderResult) -> dict:
    return {
        "order_id": r.order_id,
        "client_order_id": r.client_order_id,
        "symbol": r.symbol,
        "side": r.side,
        "order_type": r.order_type,
        "qty": r.qty,
        "status": r.status,
        "filled_qty": r.filled_qty,
        "filled_avg_price": r.filled_avg_price,
        "limit_price": r.limit_price,
        "stop_price": r.stop_price,
        "error": r.error,
    }


@app.get("/api/trade/account")
async def trade_account():
    broker = _get_broker()
    acct = broker.get_account()
    return {
        "account_id": acct.account_id,
        "status": acct.status,
        "currency": acct.currency,
        "cash": acct.cash,
        "portfolio_value": acct.portfolio_value,
        "equity": acct.equity,
        "buying_power": acct.buying_power,
        "pattern_day_trader": acct.pattern_day_trader,
        "trading_blocked": acct.trading_blocked,
    }


@app.get("/api/trade/positions")
async def trade_positions():
    broker = _get_broker()
    positions = broker.get_positions()
    return [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "avg_entry_price": p.avg_entry_price,
            "market_value": p.market_value,
            "cost_basis": p.cost_basis,
            "unrealized_pl": p.unrealized_pl,
            "unrealized_plpc": p.unrealized_plpc,
            "current_price": p.current_price,
        }
        for p in positions
    ]


@app.get("/api/trade/orders")
async def trade_orders(
    status: Literal["open", "closed", "all"] = "open",
    limit: int = Query(default=50, ge=1, le=500),
):
    broker = _get_broker()
    orders = broker.get_orders(status=status, limit=limit)
    return [_order_to_dict(o) for o in orders]


@app.post("/api/trade/execute")
async def trade_execute(req: TradeRequest):
    broker = _get_broker()

    if req.order_type == "market":
        result = broker.submit_market_order(req.symbol, req.qty, req.side)
    elif req.order_type == "limit":
        if req.limit_price is None:
            raise HTTPException(status_code=400, detail="limit_price required for limit order")
        result = broker.submit_limit_order(req.symbol, req.qty, req.limit_price, req.side)
    else:
        result = broker.submit_bracket_order(
            symbol=req.symbol,
            qty=req.qty,
            limit_price=req.limit_price,
            stop_loss_price=req.stop_loss_price,
            take_profit_price=req.take_profit_price,
            side=req.side,
        )

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    return _order_to_dict(result)


class _SimpleCandidate:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.recommendation = "BUY"
        self.reason = "Manual execution via API"
        self.hold_days = 20
        self.exit_price = None
        self.trailing_stop_pct = 0


def _generate_plan(symbol: str) -> TradePlan:
    """Generate a TradePlan for the given symbol (no execution)."""
    price_data = load_local_daily_ohlcv(
        symbols=[symbol],
        start=str((date.today() - timedelta(days=60)).isoformat()),
        end=str(date.today().isoformat()),
    )
    if symbol not in price_data:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol}")

    ohlcv_df = price_data[symbol]
    close_series = ohlcv_df["Close"]
    prices_df = pd.DataFrame({symbol: close_series})

    executor = TradeExecutor()
    plans = executor.generate_stock_plans(
        prices=prices_df,
        stock_candidates=[_SimpleCandidate(symbol)],
    )
    if not plans:
        raise HTTPException(status_code=404, detail=f"Could not generate trade plan for {symbol}")
    return plans[0]


@app.get("/api/trade/plan/{symbol}")
async def trade_plan_preview(symbol: str):
    """Preview a TradePlan without executing — for modal display."""
    plan = _generate_plan(symbol)
    return plan.to_dict()


@app.post("/api/trade/execute-plan")
async def trade_execute_plan(req: ExecutePlanRequest):
    broker = _get_broker()
    acct = broker.get_account()
    plan = _generate_plan(req.symbol)
    result = broker.execute_trade_plan(plan, acct.portfolio_value, req.order_type)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "plan": plan.to_dict(),
        "order": _order_to_dict(result),
    }


@app.delete("/api/trade/orders/{order_id}")
async def trade_cancel_order(order_id: str):
    broker = _get_broker()
    success = broker.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to cancel order {order_id}")
    return {"cancelled": True, "order_id": order_id}


@app.delete("/api/trade/positions/{symbol}")
async def trade_close_position(symbol: str):
    broker = _get_broker()
    result = broker.close_position(symbol)
    if result.error:
        raise HTTPException(status_code=400, detail=result.error)
    return _order_to_dict(result)


# =============================================================================
# Portfolio Analytics 端点
# =============================================================================


def _position_to_dict(p) -> dict:
    return {
        "symbol": p.symbol,
        "qty": float(p.qty),
        "avg_entry_price": float(p.avg_entry_price),
        "market_value": float(p.market_value),
        "cost_basis": float(p.cost_basis),
        "unrealized_pl": float(p.unrealized_pl),
        "unrealized_plpc": float(p.unrealized_plpc),
        "current_price": float(p.current_price),
    }


@app.get("/api/portfolio/analytics")
async def portfolio_analytics(days: int = Query(default=90, ge=7, le=365)):
    """
    综合 Portfolio 分析：账户概览 + 持仓分布 + 风险指标 + 历史净值曲线。

    Returns:
        account: 账户概要
        positions: 持仓列表（含权重）
        allocation: 持仓分布（饼图用）
        risk_metrics: 风险指标（Sharpe, Sortino, MaxDD 等）
        equity_curve: 历史净值曲线（折线图用）
    """
    broker = _get_broker()
    acct = broker.get_account()
    positions = broker.get_positions()

    equity = float(acct.equity)
    cash = float(acct.cash)
    portfolio_value = float(acct.portfolio_value)

    allocation = []
    positions_list = []
    total_unrealized_pl = 0.0

    for p in positions:
        mv = float(p.market_value)
        upl = float(p.unrealized_pl)
        total_unrealized_pl += upl
        weight = mv / equity if equity > 0 else 0.0
        pos_dict = _position_to_dict(p)
        pos_dict["weight"] = round(weight, 4)
        positions_list.append(pos_dict)
        allocation.append(
            {"name": p.symbol, "value": round(mv, 2), "weight": round(weight * 100, 2)}
        )

    cash_weight = cash / equity if equity > 0 else 0.0
    allocation.append(
        {"name": "现金", "value": round(cash, 2), "weight": round(cash_weight * 100, 2)}
    )

    # ── equity_curve: 加权组合净值曲线 + benchmark ──
    equity_curve: list[dict] = []
    daily_returns: list[float] = []
    benchmark_nav_series: pd.Series | None = None
    benchmark_returns_series: pd.Series | None = None

    cfg = load_config()
    benchmark_symbol = cfg.universe.market_benchmark

    if positions:
        symbols = [p.symbol for p in positions]
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        try:
            all_symbols = list(set(symbols + [benchmark_symbol]))
            price_data = load_local_daily_ohlcv(
                symbols=all_symbols,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
            )

            if price_data:
                close_frames = {}
                for sym, df in price_data.items():
                    if df is not None and not df.empty and "Close" in df.columns:
                        close_frames[sym] = df["Close"]

                # ── benchmark NAV ──
                if benchmark_symbol in close_frames:
                    bench_close = close_frames[benchmark_symbol].dropna()
                    if len(bench_close) > 1:
                        benchmark_returns_series = bench_close.pct_change().dropna()
                        benchmark_nav_series = (1 + benchmark_returns_series).cumprod()

                # 从 close_frames 中移除 benchmark（不参与持仓权重计算）
                position_close = {
                    sym: s for sym, s in close_frames.items() if sym != benchmark_symbol
                }

                if position_close:
                    close_df = pd.DataFrame(position_close).dropna()

                    if not close_df.empty:
                        returns_df = close_df.pct_change().dropna()

                        weights = {}
                        for p in positions:
                            if p.symbol in position_close:
                                w = (
                                    float(p.market_value) / portfolio_value
                                    if portfolio_value > 0
                                    else 0
                                )
                                weights[p.symbol] = w

                        if weights and not returns_df.empty:
                            weight_series = pd.Series(weights)
                            common_cols = returns_df.columns.intersection(weight_series.index)
                            if len(common_cols) > 0:
                                port_returns = (
                                    returns_df[common_cols] * weight_series[common_cols]
                                ).sum(axis=1)
                                daily_returns = port_returns.tolist()

                                nav = (1 + port_returns).cumprod()
                                for idx, val in nav.items():
                                    bench_val = None
                                    if (
                                        benchmark_nav_series is not None
                                        and idx in benchmark_nav_series.index
                                    ):
                                        bench_val = round(float(benchmark_nav_series.loc[idx]), 4)
                                    equity_curve.append(
                                        {
                                            "date": str(idx.date()),
                                            "nav": round(float(val), 4),
                                            "benchmark_nav": bench_val,
                                        }
                                    )
        except Exception:
            logger.warning("Failed to compute equity curve", exc_info=True)

    # ── risk_metrics: Sharpe / Sortino / MaxDD / Win Rate ──
    risk_metrics: dict = {
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown": None,
        "max_drawdown_duration": None,
        "annualized_return": None,
        "annualized_volatility": None,
        "win_rate": None,
        "total_unrealized_pl": round(total_unrealized_pl, 2),
        "total_unrealized_plpc": (
            round(total_unrealized_pl / (equity - total_unrealized_pl) * 100, 2)
            if (equity - total_unrealized_pl) > 0
            else 0.0
        ),
    }

    if daily_returns and len(daily_returns) >= 5:
        ret_series = pd.Series(daily_returns)
        mean_ret = ret_series.mean()
        std_ret = ret_series.std()

        ann_ret = mean_ret * 252
        ann_vol = std_ret * np.sqrt(252)

        sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else None

        downside = ret_series[ret_series < 0]
        downside_std = np.sqrt(np.mean(downside**2)) * np.sqrt(252) if len(downside) > 0 else 0
        sortino = ann_ret / downside_std if downside_std > 0 else None

        cumulative = (1 + ret_series).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_dd = float(drawdown.min())

        is_dd = drawdown < 0
        if is_dd.any():
            dd_groups = is_dd.astype(int)
            groups = dd_groups.ne(dd_groups.shift()).cumsum()
            dd_only = dd_groups[dd_groups == 1].groupby(groups)
            max_dd_dur = int(dd_only.size().max()) if len(dd_only) > 0 else 0
        else:
            max_dd_dur = 0

        win_rate = float((ret_series > 0).sum() / len(ret_series) * 100)

        risk_metrics.update(
            {
                "sharpe_ratio": round(float(sharpe), 3) if sharpe is not None else None,
                "sortino_ratio": round(float(sortino), 3) if sortino is not None else None,
                "max_drawdown": round(max_dd * 100, 2),
                "max_drawdown_duration": max_dd_dur,
                "annualized_return": round(ann_ret * 100, 2),
                "annualized_volatility": round(ann_vol * 100, 2),
                "win_rate": round(win_rate, 1),
            }
        )

    # ── benchmark_metrics: Alpha / Beta / Tracking Error / Information Ratio ──
    benchmark_metrics: dict | None = None

    if daily_returns and benchmark_returns_series is not None and len(daily_returns) >= 30:
        port_series = pd.Series(
            daily_returns,
            index=(
                benchmark_returns_series.index[: len(daily_returns)]
                if len(benchmark_returns_series) >= len(daily_returns)
                else None
            ),
        )

        aligned = pd.DataFrame({"port": port_series, "bench": benchmark_returns_series}).dropna()

        if len(aligned) >= 30:
            ab = calculate_alpha_beta(aligned["port"], aligned["bench"])

            active_ret = aligned["port"] - aligned["bench"]
            tracking_error = float(active_ret.std() * np.sqrt(252))
            mean_active = float(active_ret.mean() * 252)
            info_ratio = mean_active / tracking_error if tracking_error > 0 else None

            total_port = float((1 + aligned["port"]).prod() - 1)
            total_bench = float((1 + aligned["bench"]).prod() - 1)

            def _safe(v: float) -> float | None:
                return round(float(v), 4) if np.isfinite(v) else None

            benchmark_metrics = {
                "symbol": benchmark_symbol,
                "alpha": _safe(ab["alpha"]),
                "beta": _safe(ab["beta"]),
                "r_squared": _safe(ab["r_squared"]),
                "tracking_error": _safe(tracking_error),
                "information_ratio": _safe(info_ratio) if info_ratio is not None else None,
                "portfolio_return": _safe(total_port),
                "benchmark_return": _safe(total_bench),
                "excess_return": _safe(total_port - total_bench),
            }

    return {
        "account": {
            "account_id": acct.account_id,
            "status": acct.status,
            "currency": acct.currency,
            "cash": cash,
            "portfolio_value": portfolio_value,
            "equity": equity,
            "buying_power": float(acct.buying_power),
            "pattern_day_trader": acct.pattern_day_trader,
            "trading_blocked": acct.trading_blocked,
        },
        "positions": positions_list,
        "allocation": allocation,
        "risk_metrics": risk_metrics,
        "equity_curve": equity_curve,
        "benchmark_metrics": benchmark_metrics,
    }


# =============================================================================
# WebSocket 实时推送
# =============================================================================

HEARTBEAT_INTERVAL = 30


@app.websocket("/ws/trades")
async def ws_trades(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=HEARTBEAT_INTERVAL)
                if msg == "pong":
                    continue
            except asyncio.TimeoutError:
                await ws_manager.send_personal(
                    websocket, {"type": "ping", "ts": __import__("time").time()}
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("WS connection error", exc_info=True)
    finally:
        ws_manager.disconnect(websocket)
