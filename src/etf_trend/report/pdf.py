from __future__ import annotations

import platform
import re
import textwrap

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd


# Mapping of emoji to Chinese-friendly symbols
EMOJI_REPLACEMENTS = {
    # Check marks and crosses
    "✅": "【√】",
    "☑️": "【√】",
    "✓": "【√】",
    "❌": "【×】",
    "✗": "【×】",
    "❎": "【×】",
    # Warning and info
    "⚠️": "【注意】",
    "⚠": "【注意】",
    "💡": "【提示】",
    "ℹ️": "【信息】",
    "❗": "【!】",
    "❓": "【?】",
    # Arrows and pointers
    "👉": "→",
    "👈": "←",
    "➡️": "→",
    "⬅️": "←",
    "🔄": "◎",
    "🔃": "◎",
    # Charts and data
    "📈": "【↑】",
    "📉": "【↓】",
    "📊": "【图】",
    "⚖️": "【衡】",
    # Stars and ratings
    "⭐": "★",
    "🌟": "★",
    "✨": "☆",
    # Numbers in circles
    "①": "(1)",
    "②": "(2)",
    "③": "(3)",
    "④": "(4)",
    "⑤": "(5)",
}

# Regex pattern to match remaining emoji
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map symbols
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U0001f900-\U0001f9ff"  # supplemental symbols
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0001fa00-\U0001faff"  # extended symbols
    "]+",
    flags=re.UNICODE,
)


def _replace_emoji(text: str) -> str:
    """Replace emoji with Chinese-friendly symbols."""
    for emoji, replacement in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, replacement)
    # Remove any remaining unsupported emoji
    return EMOJI_PATTERN.sub("", text)


def _get_cjk_font() -> str:
    """Get a CJK-compatible font based on the operating system."""
    system = platform.system()

    if system == "Darwin":  # macOS
        candidates = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
    elif system == "Windows":
        candidates = ["Microsoft YaHei", "SimHei", "SimSun"]
    else:  # Linux
        candidates = ["Noto Sans CJK SC", "WenQuanYi Micro Hei", "Droid Sans Fallback"]

    available_fonts = {f.name for f in fm.fontManager.ttflist}

    for font in candidates:
        if font in available_fonts:
            return font

    # Fallback to default
    return "DejaVu Sans"


# Get CJK font once at module load
CJK_FONT = _get_cjk_font()


def export_report_pdf(
    pdf_path: str,
    bt: pd.DataFrame,
    prices: pd.DataFrame,
    weights: pd.DataFrame,
    stats: pd.Series,
    benchmark_symbol: str = "SPY",
    llm_analysis: str | None = None,
):
    with PdfPages(pdf_path) as pdf:
        # Page 1: NAV + DD + Weights
        fig = plt.figure(figsize=(14, 10))

        ax1 = plt.subplot(3, 1, 1)
        strat = bt["nav"] / bt["nav"].iloc[0]
        bench = (
            (prices[benchmark_symbol] / prices[benchmark_symbol].iloc[0])
            .reindex(strat.index)
            .ffill()
        )
        ax1.plot(strat.index, strat.values, label="Strategy")
        ax1.plot(bench.index, bench.values, label=benchmark_symbol)
        ax1.set_title("Equity Curve: Strategy vs Benchmark")
        ax1.legend()

        ax2 = plt.subplot(3, 1, 2)
        dd = bt["drawdown"]
        ax2.fill_between(dd.index, dd.values, 0, alpha=0.6)
        ax2.set_title("Drawdown")

        ax3 = plt.subplot(3, 1, 3)
        weights.plot.area(ax=ax3, alpha=0.85)
        ax3.set_title("Portfolio Weights (Monthly)")
        ax3.set_ylabel("Weight")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: Stats (text)
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")
        lines = ["Performance Summary (Monthly Rebalance)\n"]
        for k, v in stats.items():
            lines.append(f"{k:>22}: {float(v):.4f}")
        plt.text(0.05, 0.95, "\n".join(lines), va="top", family="monospace", fontsize=14)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 3+: LLM Analysis (if available)
        if llm_analysis:
            _add_analysis_pages(pdf, llm_analysis)


def _add_analysis_pages(pdf: PdfPages, analysis: str):
    """Add LLM analysis as text pages to the PDF."""
    # Remove emoji characters that fonts don't support
    analysis = _replace_emoji(analysis)

    # Split analysis into chunks that fit on a page
    lines_per_page = 45
    wrapped_lines = []

    for line in analysis.split("\n"):
        if line.startswith("#"):
            # Add extra spacing for headers
            wrapped_lines.append("")
            wrapped_lines.append(line)
        elif len(line) > 90:
            # Wrap long lines
            wrapped_lines.extend(textwrap.wrap(line, width=90))
        else:
            wrapped_lines.append(line)

    # Split into pages
    for i in range(0, len(wrapped_lines), lines_per_page):
        chunk = wrapped_lines[i : i + lines_per_page]
        fig = plt.figure(figsize=(14, 10))
        plt.axis("off")

        page_num = i // lines_per_page + 1
        title = (
            f"AI Analysis (Page {page_num})"
            if page_num == 1
            else f"AI Analysis (Continued - Page {page_num})"
        )

        plt.title(title, fontsize=16, fontweight="bold", loc="left", pad=10, fontname=CJK_FONT)
        plt.text(
            0.02,
            0.95,
            "\n".join(chunk),
            va="top",
            ha="left",
            fontsize=10,
            fontname=CJK_FONT,
            transform=plt.gca().transAxes,
        )

        pdf.savefig(fig)
        plt.close(fig)
