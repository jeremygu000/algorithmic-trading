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
启动后访问 http://localhost:8000/docs 查看 Swagger 文档
"""

from __future__ import annotations

import base64
import io
from datetime import date, timedelta
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib

# 配置中文字体 (macOS)
matplotlib.rcParams['font.sans-serif'] = ['PingFang SC', 'Arial Unicode MS', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

from etf_trend.config.settings import EnvSettings, load_config
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.regime.engine import RegimeEngine
from etf_trend.selector.satellite import StockSelector, StockCandidate
from etf_trend.execution.executor import TradeExecutor, calculate_atr
from etf_trend.execution.executor import TradeExecutor, calculate_atr
from etf_trend.features.indicators import calculate_rsi, calculate_macd, calculate_bollinger_bands
from etf_trend.data.providers.yahoo_fundamentals import load_yahoo_fundamentals
from etf_trend.features.pattern_match import find_similar_patterns
from etf_trend.features.trend_pred import predict_next_trend

# 获取配置
from pathlib import Path
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"

# =============================================================================
# FastAPI 应用
# =============================================================================

app = FastAPI(
    title="ETF Trend 股票分析 API",
    description="提供美股分析、蜡烛图、多级买卖点位的 RESTful API",
    version="1.0.0",
)

# 添加 CORS 中间件 (允许 Next.js 前端访问)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
            "/api/picks": "获取今日推荐个股列表",
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
        env = EnvSettings()

        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        # 获取价格数据
        prices = load_prices_with_fallback(
            [symbol] + cfg.universe.equity_symbols,
            str(start_date),
            str(end_date),
            env.tiingo_api_key,
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
            [symbol],
            cache_enabled=cfg.cache.enabled,
            cache_dir=cfg.cache.dir
        )
        fund_data = fundamentals_map.get(symbol) or {
            "peRatio": None, "pegRatio": None, "pbRatio": None, 
            "trailingEPS": None, "marketCap": None, "sector": None
        }

        # 计算技术指标
        price_series = prices[symbol]
        current_price = float(price_series.iloc[-1])
        ma20 = float(price_series.rolling(20).mean().iloc[-1])
        ma50 = float(price_series.rolling(50).mean().iloc[-1])
        ma200 = float(price_series.rolling(200).mean().iloc[-1])
        
        # 计算动量
        mom_60d = float((price_series.iloc[-1] / price_series.iloc[-60] - 1) * 100) if len(price_series) >= 60 else 0
        
        # 计算波动率
        vol = float(price_series.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) * 100)
        
        # 计算 ATR
        atr_df = calculate_atr(prices[[symbol]], 14)
        atr = float(atr_df[symbol].iloc[-1])

        # 计算高级技术指标 (RSI, MACD, BB)
        rsi_series = calculate_rsi(price_series)
        rsi = float(rsi_series.iloc[-1])

        macd_df = calculate_macd(price_series)
        macd_val = float(macd_df['macd'].iloc[-1])
        macd_signal = float(macd_df['signal'].iloc[-1])
        macd_hist = float(macd_df['hist'].iloc[-1])

        bb_df = calculate_bollinger_bands(price_series)
        bb_upper = float(bb_df['upper'].iloc[-1])
        bb_upper = float(bb_df['upper'].iloc[-1])
        bb_lower = float(bb_df['lower'].iloc[-1])

        # =========================================================================
        # AI/ML 预测分析
        # =========================================================================
        
        # 1. 相似形态搜索 (KNN)
        ai_pattern = find_similar_patterns(
            price_series, 
            price_series.iloc[:-20], # 在历史数据中搜索 (排除最近20天以防过度拟合，其实应该搜非样本)
            window=60,
            future_window=20
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
        if macd_hist > 0 and macd_hist > macd_df['hist'].iloc[-2]:
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
        chart_df = pd.DataFrame({
            'Open': chart_data.shift(1),
            'High': chart_data.rolling(2).max(),
            'Low': chart_data.rolling(2).min(),
            'Close': chart_data,
            'Volume': 0,
        })
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
            addplots.append(mpf.make_addplot(ma20_aligned, color='blue', width=1))
        if ma50_aligned.notna().sum() > 10:
            addplots.append(mpf.make_addplot(ma50_aligned, color='orange', width=1))

        # 生成图表到内存
        buf = io.BytesIO()
        
        # 使用英文标题避免字体问题
        stock_name = StockSelector.STOCK_NAMES.get(symbol, symbol)
        # 如果是中文名称，只显示股票代码
        if any('\u4e00' <= c <= '\u9fff' for c in stock_name):
            chart_title = symbol
        else:
            chart_title = f'{symbol} - {stock_name}'
        
        # 定义关键价位水平线
        hlines_dict = dict(
            hlines=[
                # 入场价位 (绿色)
                entry_aggressive, entry_moderate, entry_conservative,
                # 止损价位 (红色)
                stop_tight, stop_normal, stop_loose,
                # 止盈目标 (蓝色)
                tp1, tp2, tp3,
            ],
            colors=[
                '#22c55e', '#22c55e', '#22c55e',  # 绿色 - 入场
                '#ef4444', '#ef4444', '#ef4444',  # 红色 - 止损
                '#3b82f6', '#3b82f6', '#3b82f6',  # 蓝色 - 止盈
            ],
            linestyle=[
                '--', '-', ':',  # 入场: 虚线/实线/点线
                '--', '-', ':',  # 止损
                '--', '-', ':',  # 止盈
            ],
            linewidths=[0.8, 1.2, 0.8, 0.8, 1.2, 0.8, 0.8, 1.2, 0.8],
        )
        
        plot_kwargs = dict(
            type='candle',
            style='charles',
            title=chart_title,
            ylabel='Price ($)',
            savefig=dict(fname=buf, dpi=150, format='png'),
            figratio=(14, 8),
            hlines=hlines_dict,
        )
        if addplots:
            plot_kwargs['addplot'] = addplots
        
        mpf.plot(chart_df, **plot_kwargs)
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.read()).decode('utf-8')
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
                "bb_upper": round(bb_upper, 2),
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


@app.get("/api/picks")
async def get_stock_picks():
    """
    获取今日推荐个股列表
    
    返回推荐的所有个股及其多级价位
    """
    try:
        cfg = load_config(str(DEFAULT_CONFIG))
        env = EnvSettings()

        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        all_symbols = (
            cfg.universe.equity_symbols
            + cfg.universe.defensive_symbols
            + StockSelector.DEFAULT_STOCK_POOL
        )
        all_symbols = list(set(all_symbols))

        prices = load_prices_with_fallback(
            all_symbols,
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

        selector = StockSelector(
            mom_windows=cfg.signal.mom_windows,
            mom_weights=cfg.signal.mom_weights,
            vol_lookback=cfg.risk.vol_lookback,
        )
        
        # 加载所有股票的基本面数据
        available_stocks = [s for s in all_symbols if s in prices.columns]
        fundamentals = load_yahoo_fundamentals(
            available_stocks,
            cache_enabled=cfg.cache.enabled,
            cache_dir=cfg.cache.dir
        )
        
        result = selector.select(
            prices, 
            regime_state, 
            use_fundamental=True, 
            fundamentals=fundamentals
        )

        executor = TradeExecutor()
        trade_plans = []
        if result.is_active and result.candidates:
            trade_plans = executor.generate_stock_plans(prices, result.candidates)

        return {
            "date": str(end_date),
            "regime": regime_state.regime,
            "risk_budget": regime_state.risk_budget,
            "is_active": result.is_active,
            "message": result.message,
            "picks": [plan.to_dict() for plan in trade_plans],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
