"""
每日市场信号脚本
================

本脚本用于每日运行，输出当前市场状态和风险预算。
可用于每日开盘前检查市场环境，决定当日操作策略。

使用方法：
---------
$ uv run python -m etf_trend.scripts.daily_signal

输出示例：
---------
========== ETF Daily Signal (2024-12-29) ==========
Regime: 【风险偏好】
Risk Budget: 85%
---------- 信号详情 ----------
  ● SPY 价格: 478.50
  ● MA200: 452.30
  ● 趋势信号: 【√】价格在均线之上
  ● VIX: 18.5 (平静)
  ● 60天动量: +5.2%
---------- 操作建议 ----------
  维持当前高仓位配置
===================================================
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from etf_trend.config.settings import EnvSettings, load_config
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.regime.engine import RegimeEngine

# 获取包根目录
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"


def main():
    """主函数：输出每日市场信号"""

    # -------------------------------------------------------------------------
    # 解析命令行参数
    # -------------------------------------------------------------------------
    ap = argparse.ArgumentParser(description="每日市场信号检测")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = ap.parse_args()

    # -------------------------------------------------------------------------
    # 加载配置和环境变量
    # -------------------------------------------------------------------------
    cfg = load_config(args.config)
    env = EnvSettings()

    # -------------------------------------------------------------------------
    # 获取价格数据
    # -------------------------------------------------------------------------
    # 为了计算 200 日均线，需要至少 250 天的数据
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    # 合并股票和防守类 ETF
    all_symbols = cfg.universe.equity_symbols + cfg.universe.defensive_symbols

    print("正在加载价格数据...")
    prices = load_prices_with_fallback(
        all_symbols,
        str(start_date),
        str(end_date),
        env.tiingo_api_key,
        cache_enabled=cfg.cache.enabled,
        cache_dir=cfg.cache.dir,
    )
    # 使用 ffill 填充缺失值，只删除全为空的行（非交易日）
    prices = prices.ffill().dropna(how="all")

    # -------------------------------------------------------------------------
    # 检测市场状态
    # -------------------------------------------------------------------------
    engine = RegimeEngine(
        ma_window=cfg.regime.ma_window,
        momentum_window=cfg.regime.momentum_window,
        vix_threshold=cfg.regime.vix_threshold,
        weight_trend=cfg.regime.weight_trend,
        weight_vix=cfg.regime.weight_vix,
        weight_momentum=cfg.regime.weight_momentum,
    )

    # 注意：目前没有 VIX 数据，后续可以添加
    state = engine.detect(prices, vix=None, market_symbol=cfg.universe.market_benchmark)

    # -------------------------------------------------------------------------
    # 输出结果
    # -------------------------------------------------------------------------
    if args.json:
        # JSON 格式输出（便于程序处理）
        import json

        output = {
            "date": str(end_date),
            "regime": state.regime,
            "risk_budget": state.risk_budget,
            "signals": state.signals,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # 人类可读格式输出
        _print_human_readable(state, end_date, engine)


def _print_human_readable(state, today, engine):
    """以人类可读的格式打印结果"""

    # 状态描述映射
    regime_icons = {
        "RISK_ON": "【风险偏好 🟢】",
        "NEUTRAL": "【中性观望 🟡】",
        "RISK_OFF": "【风险厌恶 🔴】",
    }

    signals = state.signals

    print("\n" + "=" * 55)
    print(f"        ETF Daily Signal ({today})")
    print("=" * 55)

    # 主状态
    print(f"\n📊 市场状态: {regime_icons.get(state.regime, state.regime)}")
    print(f"💰 风险预算: {state.risk_budget * 100:.0f}%")

    # 信号详情
    print("\n" + "-" * 40)
    print("               信号详情")
    print("-" * 40)

    # 价格和均线
    price = signals.get("price")
    ma = signals.get("ma200")
    if price and ma:
        trend_icon = "【√】" if signals.get("trend_above_ma") else "【×】"
        print(f"  ● {signals['market_symbol']} 价格: {price:.2f}")
        print(f"  ● MA200: {ma:.2f}")
        print(
            f"  ● 趋势信号: {trend_icon} {'价格在均线之上' if signals.get('trend_above_ma') else '价格在均线之下'}"
        )

    # VIX
    vix = signals.get("vix")
    if vix:
        vix_desc = "平静" if vix < 20 else ("担忧" if vix < 30 else "恐慌")
        print(f"  ● VIX: {vix:.1f} ({vix_desc})")
    else:
        print("  ● VIX: 无数据 (假设正常)")

    # 动量
    momentum = signals.get("momentum_60d")
    if momentum is not None:
        momentum_icon = "↑" if momentum > 0 else "↓"
        print(f"  ● 60天动量: {momentum_icon}{abs(momentum):.1f}%")

    # 操作建议
    print("\n" + "-" * 40)
    print("               操作建议")
    print("-" * 40)

    if state.regime == "RISK_ON":
        print("  → 可高仓位持有股票类 ETF")
        print("  → 重点关注动量强的行业 ETF")
    elif state.regime == "NEUTRAL":
        print("  → 建议降低总仓位至 50% 左右")
        print("  → 增加债券/黄金等防守类资产")
    else:  # RISK_OFF
        print("  → 建议大幅减少股票持仓")
        print("  → 转向国债 (TLT/IEF) 和黄金 (GLD)")

    print("\n" + "=" * 55 + "\n")


if __name__ == "__main__":
    main()
