"""
每周推荐报告脚本
================

本脚本生成每周 ETF 推荐报告，包含：
1. 当前市场状态判断
2. Top-N ETF 推荐及权重
3. LLM 智能分析（可选）
4. 输出为 PDF 格式

使用方法：
---------
# 生成每周报告
$ uv run python -m etf_trend.scripts.weekly_report --out weekly.pdf

# 不使用 AI 分析
$ uv run python -m etf_trend.scripts.weekly_report --out weekly.pdf --no-ai
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd

from etf_trend.config.settings import EnvSettings, load_config
from etf_trend.data.providers.unified import load_prices_with_fallback
from etf_trend.regime.engine import RegimeEngine
from etf_trend.allocator.core import CoreAllocator
from etf_trend.selector.satellite import StockSelector
from etf_trend.execution.executor import TradeExecutor

# 获取包根目录
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "configs" / "default.yaml"


def main():
    """生成每周推荐报告"""

    # -------------------------------------------------------------------------
    # 解析命令行参数
    # -------------------------------------------------------------------------
    ap = argparse.ArgumentParser(description="每周 ETF 推荐报告")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="配置文件路径")
    ap.add_argument("--out", default="weekly_report.pdf", help="输出 PDF 路径")
    ap.add_argument("--no-ai", action="store_true", help="跳过 LLM 分析")
    args = ap.parse_args()

    # -------------------------------------------------------------------------
    # 加载配置
    # -------------------------------------------------------------------------
    cfg = load_config(args.config)
    env = EnvSettings()

    # -------------------------------------------------------------------------
    # 获取价格数据
    # -------------------------------------------------------------------------
    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    # 合并所有 ETF
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
    prices = prices.ffill().dropna(how="any")

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
    # 资产配置
    # -------------------------------------------------------------------------
    print("正在计算资产配置...")
    allocator = CoreAllocator(
        equity_symbols=cfg.universe.equity_symbols,
        defensive_symbols=cfg.universe.defensive_symbols,
        core_symbols=cfg.universe.core_symbols,
        top_n_equity=cfg.allocation.top_n_equity,
        top_n_defensive=cfg.allocation.top_n_defensive,
        vol_lookback=cfg.risk.vol_lookback,
        max_weight_single=cfg.risk.max_weight_single,
        max_weight_core=cfg.risk.max_weight_core,
        mom_windows=cfg.signal.mom_windows,
        mom_weights=cfg.signal.mom_weights,
        optimizer_method=cfg.optimizer.method,
    )

    allocation_result = allocator.allocate(prices, regime_state)

    # -------------------------------------------------------------------------
    # 个股筛选（使用统一接口，支持 Fallback）
    # -------------------------------------------------------------------------
    print("正在筛选个股...")
    # 加载个股数据
    stock_prices = load_prices_with_fallback(
        StockSelector.DEFAULT_STOCK_POOL,
        str(start_date),
        str(end_date),
        env.tiingo_api_key,
        cache_enabled=cfg.cache.enabled,
        cache_dir=cfg.cache.dir,
    )
    # 使用 ffill 填充缺失值，只删除全为空的行（非交易日）
    # 避免因某只股票上市较晚导致删除整个历史数据
    stock_prices = stock_prices.ffill().dropna(how="all")

    # 筛选个股
    selector = StockSelector(
        mom_windows=cfg.signal.mom_windows,
        mom_weights=cfg.signal.mom_weights,
        vol_lookback=cfg.risk.vol_lookback,
    )
    stock_result = selector.select(stock_prices, regime_state, use_fundamental=True)

    # -------------------------------------------------------------------------
    # 生成交易计划
    # -------------------------------------------------------------------------
    print("正在生成交易计划...")
    executor = TradeExecutor()
    trade_plans = executor.generate_trade_plans(prices, allocation_result)

    # 为推荐个股生成交易计划
    stock_trade_plans = []
    if stock_result.is_active and stock_result.candidates:
        stock_trade_plans = executor.generate_stock_plans(stock_prices, stock_result.candidates)

    # -------------------------------------------------------------------------
    # 生成 PDF 报告
    # -------------------------------------------------------------------------
    print("正在生成 PDF 报告...")
    _generate_pdf(
        pdf_path=args.out,
        prices=prices,
        regime_state=regime_state,
        allocation_result=allocation_result,
        stock_result=stock_result,
        trade_plans=trade_plans,
        stock_trade_plans=stock_trade_plans,
        regime_engine=regime_engine,
        env=env,
        skip_ai=args.no_ai,
    )

    print(f"报告已生成: {args.out}")


def _generate_pdf(
    pdf_path: str,
    prices: pd.DataFrame,
    regime_state,
    allocation_result,
    stock_result,
    trade_plans,
    stock_trade_plans,
    regime_engine,
    env,
    skip_ai: bool = False,
):
    """生成 PDF 报告"""

    # 导入中文字体处理
    from etf_trend.report.pdf import CJK_FONT, _replace_emoji

    with PdfPages(pdf_path) as pdf:
        # 设置全局字体
        plt.rcParams["font.family"] = CJK_FONT
        plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

        # =====================================================================
        # Page 1: 市场状态 + 推荐配置
        # =====================================================================
        fig = plt.figure(figsize=(14, 10))

        # 标题
        plt.suptitle(
            f"ETF 每周推荐报告 ({date.today()})",
            fontsize=18,
            fontweight="bold",
            fontname=CJK_FONT,
        )

        # 1.1 市场状态信息
        ax1 = plt.subplot(2, 2, 1)
        ax1.axis("off")

        regime_icons = {
            "RISK_ON": "风险偏好",
            "NEUTRAL": "中性观望",
            "RISK_OFF": "风险厌恶",
        }
        signals = regime_state.signals

        status_text = f"""
市场状态: 【{regime_icons.get(regime_state.regime, regime_state.regime)}】
风险预算: {regime_state.risk_budget * 100:.0f}%

信号详情:
  {signals['market_symbol']} 价格: {signals['price']:.2f}
  MA200: {signals['ma200']:.2f}
  趋势: {'在均线之上' if signals['trend_above_ma'] else '在均线之下'}
  60天动量: {signals['momentum_60d']:.1f}%
"""
        ax1.text(
            0.1,
            0.9,
            status_text,
            va="top",
            fontsize=12,
            fontname=CJK_FONT,
            transform=ax1.transAxes,
        )
        ax1.set_title("市场状态", fontsize=14, fontname=CJK_FONT, loc="left")

        # 1.2 推荐配置饼图
        ax2 = plt.subplot(2, 2, 2)
        weights = allocation_result.weights
        if weights:
            labels = list(weights.keys())
            sizes = list(weights.values())
            colors = plt.cm.Set3(range(len(labels)))
            ax2.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors)
            ax2.set_title("推荐配置", fontsize=14, fontname=CJK_FONT)

        # 1.3 ETF 近期表现
        ax3 = plt.subplot(2, 1, 2)
        # 取最近 60 天
        recent_prices = prices.tail(60)
        normalized = recent_prices / recent_prices.iloc[0] * 100

        for col in normalized.columns:
            ax3.plot(normalized.index, normalized[col], label=col, alpha=0.8)

        ax3.set_title("ETF 近 60 天表现 (归一化)", fontsize=14, fontname=CJK_FONT)
        ax3.legend(loc="upper left", ncol=4, fontsize=8)
        ax3.set_ylabel("价格 (起点=100)")
        ax3.grid(True, alpha=0.3)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        pdf.savefig(fig)
        plt.close(fig)

        # =====================================================================
        # Page 2: 推荐明细
        # =====================================================================
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")

        # 生成推荐文本
        text_lines = []
        text_lines.append("=" * 50)
        text_lines.append("       ETF 推荐配置明细")
        text_lines.append("=" * 50)
        text_lines.append("")

        # 股票类
        text_lines.append("-" * 40)
        text_lines.append("  股票类 ETF")
        text_lines.append("-" * 40)
        for symbol, weight in sorted(allocation_result.equity_weights.items(), key=lambda x: -x[1]):
            text_lines.append(f"  {symbol:8} {weight * 100:5.1f}%")

        text_lines.append("")

        # 防守类
        text_lines.append("-" * 40)
        text_lines.append("  防守类 ETF")
        text_lines.append("-" * 40)
        for symbol, weight in sorted(
            allocation_result.defensive_weights.items(), key=lambda x: -x[1]
        ):
            text_lines.append(f"  {symbol:8} {weight * 100:5.1f}%")

        text_lines.append("")

        # 总计
        total = sum(weights.values())
        cash = max(0, 1 - total)
        text_lines.append("-" * 40)
        text_lines.append(f"  总持仓: {total * 100:.1f}%")
        if cash > 0.01:
            text_lines.append(f"  现金:   {cash * 100:.1f}%")
        text_lines.append("=" * 50)

        plt.text(
            0.1,
            0.95,
            "\n".join(text_lines),
            va="top",
            fontsize=12,
            family="monospace",
            fontname=CJK_FONT,
            transform=plt.gca().transAxes,
        )

        pdf.savefig(fig)
        plt.close(fig)

        # =====================================================================
        # Page 3: 个股推荐（卫星持仓）
        # =====================================================================
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")

        stock_lines = []
        stock_lines.append("=" * 55)
        stock_lines.append("       个股候选清单 (卫星持仓)")
        stock_lines.append("=" * 55)
        stock_lines.append("")

        if not stock_result.is_active:
            stock_lines.append(f"  {stock_result.message}")
        elif not stock_result.candidates:
            stock_lines.append("  暂无符合条件的股票")
        else:
            stock_lines.append(f"  {stock_result.message}")
            stock_lines.append("")
            for i, c in enumerate(stock_result.candidates[:10], 1):  # 最多显示10个
                stock_lines.append(f"  [{i}] {c.symbol} - {c.name}")
                stock_lines.append(f"      价格: ${c.price:.2f}  |  {c.recommendation}")
                stock_lines.append(f"      原因: {c.reason}")
                stock_lines.append("")

        stock_lines.append("-" * 55)
        stock_lines.append("【风险提示】")
        stock_lines.append("  - 个股波动远大于 ETF，建议仓位控制在 20% 以内")
        stock_lines.append("  - 本清单仅供参考，不构成投资建议")
        stock_lines.append("=" * 55)

        plt.text(
            0.05,
            0.95,
            "\n".join(stock_lines),
            va="top",
            fontsize=11,
            fontname=CJK_FONT,
            transform=plt.gca().transAxes,
        )

        pdf.savefig(fig)
        plt.close(fig)

        # =====================================================================
        # Page 4: 交易执行计划 (Trade Execution Plan)
        # =====================================================================
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")

        exec_lines = []
        exec_lines.append("=" * 60)
        exec_lines.append("       📊 交易执行计划 (Trade Execution Plan)")
        exec_lines.append("=" * 60)
        exec_lines.append("")

        if trade_plans:
            for plan in trade_plans[:5]:  # 减少到5个以腾出空间
                if plan.action == "BUY":
                    exec_lines.append(f"[{plan.symbol}] {plan.reason}")
                    exec_lines.append(f"  当前: ${plan.current_price:.2f}")
                    exec_lines.append(
                        f"  入场: ${plan.entry_aggressive:.2f}(激进) / ${plan.entry_moderate:.2f}(稳健) / ${plan.entry_conservative:.2f}(保守)"
                    )
                    exec_lines.append(
                        f"  止损: ${plan.stop_tight:.2f}(紧) / ${plan.stop_normal:.2f}(标准) / ${plan.stop_loose:.2f}(宽)"
                    )
                    exec_lines.append(
                        f"  止盈: ${plan.tp1:.2f}(TP1) / ${plan.tp2:.2f}(TP2) / ${plan.tp3:.2f}(TP3)"
                    )
                else:
                    exec_lines.append(f"[{plan.symbol}] 卖出信号")
                    exec_lines.append(f"  当前: ${plan.current_price:.2f} | {plan.reason}")
                exec_lines.append("")
        else:
            exec_lines.append("  暂无交易计划")

        exec_lines.append("-" * 60)
        exec_lines.append("【多级价位说明】")
        exec_lines.append("  入场: 激进=MA20 / 稳健=回调2% / 保守=回调5%")
        exec_lines.append("  止损: 紧=ATR×1.5 / 标准=ATR×2 / 宽=ATR×3")
        exec_lines.append("  止盈: TP1=ATR×2 / TP2=ATR×4 / TP3=ATR×6")
        exec_lines.append("=" * 60)

        plt.text(
            0.05,
            0.95,
            "\n".join(exec_lines),
            va="top",
            fontsize=10,
            family="monospace",
            fontname=CJK_FONT,
            transform=plt.gca().transAxes,
        )

        pdf.savefig(fig)
        plt.close(fig)

        # =====================================================================
        # Page 5: 个股交易计划 (Stock Trade Execution)
        # =====================================================================
        if stock_trade_plans:
            fig = plt.figure(figsize=(14, 10))
            plt.axis("off")

            stock_exec_lines = []
            stock_exec_lines.append("=" * 60)
            stock_exec_lines.append("       个股交易计划 (Stock Trade Execution)")
            stock_exec_lines.append("=" * 60)
            stock_exec_lines.append("")

            for plan in stock_trade_plans[:4]:  # 减少到4个以腾出空间
                stock_exec_lines.append(f"[{plan.symbol}] {plan.reason}")
                stock_exec_lines.append(f"  当前: ${plan.current_price:.2f}")
                stock_exec_lines.append(
                    f"  入场: ${plan.entry_aggressive:.2f}(激进) / ${plan.entry_moderate:.2f}(稳健) / ${plan.entry_conservative:.2f}(保守)"
                )
                stock_exec_lines.append(
                    f"  止损: ${plan.stop_tight:.2f}(紧) / ${plan.stop_normal:.2f}(标准) / ${plan.stop_loose:.2f}(宽)"
                )
                stock_exec_lines.append(
                    f"  止盈: ${plan.tp1:.2f}(TP1) / ${plan.tp2:.2f}(TP2) / ${plan.tp3:.2f}(TP3)"
                )
                stock_exec_lines.append("")

            stock_exec_lines.append("-" * 60)
            stock_exec_lines.append("【个股多级价位说明】")
            stock_exec_lines.append("  入场: 激进=MA20 / 稳健=回调2% / 保守=回调7%")
            stock_exec_lines.append("  止损: 紧=ATR×2 / 标准=ATR×3 / 宽=ATR×4 (比ETF更宽)")
            stock_exec_lines.append("  止盈: TP1=ATR×3 / TP2=ATR×6 / TP3=ATR×10")
            stock_exec_lines.append("=" * 60)

            plt.text(
                0.05,
                0.95,
                "\n".join(stock_exec_lines),
                va="top",
                fontsize=10,
                family="monospace",
                fontname=CJK_FONT,
                transform=plt.gca().transAxes,
            )

            pdf.savefig(fig)
            plt.close(fig)

        # =====================================================================
        # Page 6+: LLM 分析（可选）
        # =====================================================================
        if not skip_ai and env.llm_api_key:
            print(f"正在生成 AI 分析 ({env.llm_provider}/{env.llm_model})...")

            # 构建分析数据
            analysis_data = f"""
## 市场状态
- 当前状态: {regime_icons.get(regime_state.regime)}
- 风险预算: {regime_state.risk_budget * 100:.0f}%
- {signals['market_symbol']} 价格: {signals['price']:.2f} (MA200: {signals['ma200']:.2f})
- 60天动量: {signals['momentum_60d']:.1f}%

## 推荐配置
股票类 ETF (总计 {sum(allocation_result.equity_weights.values()) * 100:.1f}%):
{chr(10).join([f'  - {s}: {w*100:.1f}%' for s, w in sorted(allocation_result.equity_weights.items(), key=lambda x: -x[1])])}

防守类 ETF (总计 {sum(allocation_result.defensive_weights.values()) * 100:.1f}%):
{chr(10).join([f'  - {s}: {w*100:.1f}%' for s, w in sorted(allocation_result.defensive_weights.items(), key=lambda x: -x[1])])}

## 请分析
1. 当前市场状态的含义
2. 推荐配置的逻辑
3. 需要注意的风险
4. 操作建议
"""
            from openai import OpenAI

            client = OpenAI(
                api_key=env.llm_api_key,
                base_url=(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    if env.llm_provider == "qwen"
                    else "https://api.openai.com/v1"
                ),
            )

            try:
                response = client.chat.completions.create(
                    model=env.llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是专业的量化投资分析师。请用通俗易懂的语言分析 ETF 推荐配置。不要使用表格格式，使用列表和段落。使用【】强调重要内容。",
                        },
                        {"role": "user", "content": analysis_data},
                    ],
                    temperature=0.7,
                    max_tokens=1500,
                )
                ai_analysis = response.choices[0].message.content or ""
            except Exception as e:
                ai_analysis = f"AI 分析生成失败: {e}"

            # 添加 AI 分析页面
            ai_analysis = _replace_emoji(ai_analysis)
            _add_text_page(pdf, "AI 分析", ai_analysis, CJK_FONT)


def _add_text_page(pdf: PdfPages, title: str, content: str, font: str):
    """添加文本页面"""
    import textwrap

    lines_per_page = 40
    wrapped_lines = []

    for line in content.split("\n"):
        if line.startswith("#"):
            wrapped_lines.append("")
            wrapped_lines.append(line)
        elif len(line) > 80:
            wrapped_lines.extend(textwrap.wrap(line, width=80))
        else:
            wrapped_lines.append(line)

    for i in range(0, len(wrapped_lines), lines_per_page):
        chunk = wrapped_lines[i : i + lines_per_page]
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")

        page_num = i // lines_per_page + 1
        plt.title(
            f"{title} (Page {page_num})",
            fontsize=16,
            fontweight="bold",
            loc="left",
            fontname=font,
        )
        plt.text(
            0.02,
            0.95,
            "\n".join(chunk),
            va="top",
            fontsize=10,
            fontname=font,
            transform=plt.gca().transAxes,
        )

        pdf.savefig(fig)
        plt.close(fig)


if __name__ == "__main__":
    main()
