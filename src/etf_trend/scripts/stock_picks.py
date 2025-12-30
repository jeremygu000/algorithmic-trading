"""
个股推荐脚本
============

本脚本输出个股候选清单，作为 ETF 核心配置的"卫星"补充。

使用方法：
---------
$ uv run python -m etf_trend.scripts.stock_picks

注意：仅在 RISK_ON 时输出个股推荐，其他市场状态不建议配置个股。
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from etf_trend.config.settings import EnvSettings, load_config
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.regime.engine import RegimeEngine
from etf_trend.selector.satellite import StockSelector
from etf_trend.execution.executor import TradeExecutor

# 获取包根目录
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"


def main():
    """输出个股推荐 (含多级价位)"""

    # -------------------------------------------------------------------------
    # 解析命令行参数
    # -------------------------------------------------------------------------
    ap = argparse.ArgumentParser(description="个股候选清单 (含多级买卖点)")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = ap.parse_args()

    # -------------------------------------------------------------------------
    # 加载配置
    # -------------------------------------------------------------------------
    cfg = load_config(args.config)
    env = EnvSettings()

    # -------------------------------------------------------------------------
    # 获取价格数据（支持自动 Fallback: Tiingo -> Yahoo）
    # -------------------------------------------------------------------------
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    # 合并 ETF + 股票
    all_symbols = (
        cfg.universe.equity_symbols
        + cfg.universe.defensive_symbols
        + StockSelector.DEFAULT_STOCK_POOL
    )
    # 去重
    all_symbols = list(set(all_symbols))

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
    # 市场状态检测
    # -------------------------------------------------------------------------
    print("正在分析市场状态...")
    regime_engine = RegimeEngine(
        ma_window=cfg.regime.ma_window,
        momentum_window=cfg.regime.momentum_window,
        vix_threshold=cfg.regime.vix_threshold,
        weight_trend=cfg.regime.weight_trend,
        weight_vix=cfg.regime.weight_vix,
        weight_momentum=cfg.regime.weight_momentum,
    )
    regime_state = regime_engine.detect(
        prices, vix=None, market_symbol=cfg.universe.market_benchmark
    )

    # -------------------------------------------------------------------------
    # 个股筛选
    # -------------------------------------------------------------------------
    print("正在筛选个股...")
    selector = StockSelector(
        mom_windows=cfg.signal.mom_windows,
        mom_weights=cfg.signal.mom_weights,
        vol_lookback=cfg.risk.vol_lookback,
    )
    result = selector.select(prices, regime_state, use_fundamental=True)

    # -------------------------------------------------------------------------
    # 生成交易计划 (多级价位)
    # -------------------------------------------------------------------------
    print("正在计算多级交易价位...")
    executor = TradeExecutor()
    trade_plans = []
    if result.is_active and result.candidates:
        trade_plans = executor.generate_stock_plans(prices, result.candidates)

    # -------------------------------------------------------------------------
    # 输出结果
    # -------------------------------------------------------------------------
    if args.json:
        import json

        output = {
            "date": str(end_date),
            "regime": result.regime,
            "is_active": result.is_active,
            "message": result.message,
            "candidates": [plan.to_dict() for plan in trade_plans],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # 显示市场状态
        regime_icons = {
            "RISK_ON": "【风险偏好 🟢】",
            "NEUTRAL": "【中性观望 🟡】",
            "RISK_OFF": "【风险厌恶 🔴】",
        }
        print("\n" + "=" * 70)
        print("             个股推荐 (含多级买卖点)")
        print("=" * 70)
        print(f"\n市场状态: {regime_icons.get(regime_state.regime, regime_state.regime)}")
        print(f"风险预算: {regime_state.risk_budget * 100:.0f}%")
        print(f"分析日期: {end_date}")

        if not result.is_active:
            print(f"\n⚠️ {result.message}")
        elif not trade_plans:
            print("\n暂无符合条件的个股推荐")
        else:
            print(f"\n📊 共筛选出 {len(trade_plans)} 只推荐个股:\n")

            for i, plan in enumerate(trade_plans, 1):
                print("-" * 70)
                print(f"[{i}] {plan.symbol}")
                print(f"    推荐理由: {plan.reason}")
                print(f"    当前价格: ${plan.current_price:.2f}")
                print()
                print("    【入场价位】")
                print(f"      • 激进入场 (MA20):     ${plan.entry_aggressive:.2f}")
                print(f"      • 稳健入场 (回调2%):   ${plan.entry_moderate:.2f}")
                print(f"      • 保守入场 (回调7%):   ${plan.entry_conservative:.2f}")
                print()
                print("    【止损价位】")
                print(f"      • 紧止损 (ATR×2):      ${plan.stop_tight:.2f}")
                print(f"      • 标准止损 (ATR×3):    ${plan.stop_normal:.2f}")
                print(f"      • 宽止损 (ATR×4):      ${plan.stop_loose:.2f}")
                print()
                print("    【止盈目标】")
                print(f"      • TP1 (ATR×3):         ${plan.tp1:.2f}")
                print(f"      • TP2 (ATR×6):         ${plan.tp2:.2f}")
                print(f"      • TP3 (ATR×10):        ${plan.tp3:.2f}")
                print()

        print("-" * 70)
        print("【风险提示】")
        print("  • 个股波动远大于 ETF，建议单只仓位 ≤5%, 总仓位 ≤20%")
        print("  • 入场后严格执行止损，到达止盈目标分批减仓")
        print("  • 本推荐仅供参考，不构成投资建议")
        print("=" * 70)


if __name__ == "__main__":
    main()
