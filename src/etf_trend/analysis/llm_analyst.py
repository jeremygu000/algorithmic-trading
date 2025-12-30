"""LLM-powered backtest analysis service."""

from __future__ import annotations

from openai import OpenAI
import pandas as pd

# Provider base URLs
PROVIDER_BASE_URLS = {
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai": "https://api.openai.com/v1",
}

SYSTEM_PROMPT = """你是一位专业的量化投资分析师。你的任务是分析回测报告并用清晰易懂的语言解释结果。

【重要格式要求】
- 不要使用 markdown 表格（| --- | 格式），PDF 无法正确显示
- 使用列表（-）或编号（1. 2. 3.）来组织信息
- 使用【】来强调重要内容
- 保持段落简短，便于阅读

请根据提供的数据，生成以下分析报告：

## 1. 策略表现摘要
用通俗语言总结策略的整体表现，包括收益和风险特征。

## 2. 收益分析
- 年化收益率的含义
- 与基准相比的表现
- 收益的稳定性

## 3. 风险分析
- 最大回撤的严重程度
- 波动率水平
- 夏普比率和卡玛比率的解读

## 4. 风险警示
指出策略可能存在的问题：
- 回撤是否过大
- 收益是否过低
- 策略是否在某些时期失效

## 5. 操作建议
基于分析结果给出具体建议：
- 是否适合实盘使用
- 需要注意的事项
- 可能的改进方向

请保持专业但易懂，避免过多术语，必要时用比喻解释概念。"""


def create_llm_client(provider: str, api_key: str) -> OpenAI:
    """Create OpenAI-compatible client for the specified provider."""
    base_url = PROVIDER_BASE_URLS.get(provider)
    if not base_url:
        raise ValueError(f"Unknown provider: {provider}. Use 'qwen' or 'openai'.")

    return OpenAI(api_key=api_key, base_url=base_url)


def format_backtest_data(
    stats: pd.Series,
    bt: pd.DataFrame,
    prices: pd.DataFrame,
    benchmark_symbol: str = "SPY",
) -> str:
    """Format backtest data for LLM analysis."""
    # Calculate benchmark performance
    bench_return = (prices[benchmark_symbol].iloc[-1] / prices[benchmark_symbol].iloc[0]) - 1
    strategy_return = bt["nav"].iloc[-1] - 1

    # Get date range
    start_date = bt.index[0].strftime("%Y-%m-%d")
    end_date = bt.index[-1].strftime("%Y-%m-%d")
    total_days = len(bt)

    data = f"""
## 回测基本信息
- 回测区间: {start_date} 至 {end_date} ({total_days} 个交易日)
- 基准标的: {benchmark_symbol}

## 策略绩效指标
- 年化收益率: {stats['Ann Return']:.2%}
- 年化波动率: {stats['Ann Vol']:.2%}
- 夏普比率: {stats['Sharpe']:.2f}
- 最大回撤: {stats['Max Drawdown']:.2%}
- 卡玛比率: {stats['Calmar']:.2f}
- 平均日换手率: {stats['Avg Daily Turnover']:.2%}
- 平均日交易成本: {stats['Avg Cost (bps/day)']:.2f} bps

## 策略 vs 基准
- 策略累计收益: {strategy_return:.2%}
- 基准累计收益: {bench_return:.2%}
- 超额收益: {strategy_return - bench_return:.2%}

## 回撤统计
- 最大回撤: {bt['drawdown'].min():.2%}
- 当前回撤: {bt['drawdown'].iloc[-1]:.2%}
"""
    return data


def analyze_backtest(
    provider: str,
    api_key: str,
    model: str,
    stats: pd.Series,
    bt: pd.DataFrame,
    prices: pd.DataFrame,
    benchmark_symbol: str = "SPY",
) -> str:
    """
    Generate LLM-powered analysis of backtest results.

    Args:
        provider: LLM provider ('qwen' or 'openai')
        api_key: API key for the provider
        model: Model name (e.g., 'qwen-plus', 'gpt-4o-mini')
        stats: Performance statistics Series
        bt: Backtest results DataFrame
        prices: Price data DataFrame
        benchmark_symbol: Benchmark symbol for comparison

    Returns:
        Markdown formatted analysis string
    """
    if not api_key:
        return "⚠️ 未配置 LLM API Key，无法生成智能分析。请在 .env 中设置 LLM_API_KEY。"

    client = create_llm_client(provider, api_key)
    data = format_backtest_data(stats, bt, prices, benchmark_symbol)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请分析以下回测数据:\n{data}"},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        return response.choices[0].message.content or "分析生成失败"
    except Exception as e:
        return f"⚠️ LLM 分析生成失败: {e}"
