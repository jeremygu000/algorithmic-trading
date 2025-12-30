from __future__ import annotations
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_normalized(prices: pd.DataFrame, title: str = "Normalized Adj Close"):
    (prices / prices.iloc[0]).plot(figsize=(12, 4), title=title)
    plt.show()


def plot_weights(weights: pd.DataFrame, title: str = "Portfolio Weights (Monthly)"):
    weights.plot.area(figsize=(12, 4), alpha=0.85, title=title)
    plt.ylabel("Weight")
    plt.show()


def plot_nav_vs_benchmark(
    bt: pd.DataFrame, benchmark: pd.Series, title: str = "Strategy vs Benchmark"
):
    strat = bt["nav"] / bt["nav"].iloc[0]
    bench = (benchmark / benchmark.iloc[0]).reindex(strat.index).ffill()

    plt.figure(figsize=(12, 4))
    plt.plot(strat.index, strat.values, label="Strategy")
    plt.plot(bench.index, bench.values, label="Benchmark")
    plt.title(title)
    plt.legend()
    plt.show()


def plot_drawdown(bt: pd.DataFrame, title: str = "Drawdown"):
    dd = bt["drawdown"]
    plt.figure(figsize=(12, 3))
    plt.fill_between(dd.index, dd.values, 0, alpha=0.6)
    plt.title(title)
    plt.show()
