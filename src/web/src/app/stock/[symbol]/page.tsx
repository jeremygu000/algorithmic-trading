"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API_BASE = "http://localhost:8000";

interface StockData {
  symbol: string;
  name: string;
  date: string;
  current_price: number;
  recommendation: string;
  reason: string;
  technicals: {
    ma20: number;
    ma50: number;
    ma200: number;
    momentum_60d: number;
    volatility: number;
    atr: number;
  };
  entry_levels: {
    aggressive: number;
    aggressive_label: string;
    moderate: number;
    moderate_label: string;
    conservative: number;
    conservative_label: string;
  };
  stop_levels: {
    tight: number;
    tight_label: string;
    normal: number;
    normal_label: string;
    loose: number;
    loose_label: string;
  };
  tp_levels: {
    tp1: number;
    tp1_label: string;
    tp2: number;
    tp2_label: string;
    tp3: number;
    tp3_label: string;
  };
  market_regime: string;
  chart_base64: string;
}

export default function StockPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase();

  const [data, setData] = useState<StockData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    setLoading(true);
    fetch(`${API_BASE}/api/stock/${symbol}`)
      .then((res) => {
        if (!res.ok) throw new Error(`股票 ${symbol} 未找到`);
        return res.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [symbol]);

  const recommendationStyle: Record<string, string> = {
    强烈推荐: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    推荐: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    观望: "bg-slate-700/30 text-slate-400 border-slate-700/50",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">正在分析 {symbol} 数据...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-2xl p-8 text-center">
          <h2 className="text-xl font-semibold text-rose-400 mb-2">查询失败</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <a
            href="/"
            className="inline-block px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors"
          >
            返回首页
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-6 border-b border-slate-800 pb-8">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <h1 className="text-5xl font-bold text-white tracking-tight">
              {data?.symbol}
            </h1>
            <div
              className={`px-3 py-1.5 rounded-full border text-sm font-medium ${
                recommendationStyle[data?.recommendation || "观望"]
              }`}
            >
              {data?.recommendation}
            </div>
          </div>
          <p className="text-slate-400 text-lg">{data?.name}</p>
        </div>
        <div className="text-right">
          <div className="text-sm text-slate-500 mb-1 uppercase tracking-wide">
            当前价格
          </div>
          <div className="text-4xl font-mono font-bold text-white">
            ${data?.current_price.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Analysis Reason */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 mb-8 flex gap-3 items-start">
        <span className="text-sky-500 text-xl">💡</span>
        <p className="text-slate-300 leading-relaxed pt-0.5">
          <span className="text-slate-500 font-medium">分析结论：</span>{" "}
          {data?.reason}
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Chart Area */}
        <div className="lg:col-span-2 space-y-8">
          {/* Chart */}
          {data?.chart_base64 && (
            <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800 shadow-xl shadow-black/20">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-slate-200">
                  📊 技术分析图表
                </h2>
                <div className="flex gap-4 text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-0.5 bg-green-500"></div>
                    <span className="text-slate-400">入场</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-0.5 bg-red-500"></div>
                    <span className="text-slate-400">止损</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-0.5 bg-blue-500"></div>
                    <span className="text-slate-400">止盈</span>
                  </div>
                </div>
              </div>
              <img
                src={`data:image/png;base64,${data.chart_base64}`}
                alt={`${data.symbol} 蜡烛图`}
                className="w-full rounded-lg"
              />
            </div>
          )}

          {/* Technical Indicators */}
          <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
            <h3 className="text-lg font-bold mb-4 text-slate-200">
              📉 技术指标详情
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  MA20 (短期趋势)
                </div>
                <div className="font-mono font-semibold text-slate-200">
                  ${data?.technicals.ma20.toFixed(2)}
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  MA50 (中期趋势)
                </div>
                <div className="font-mono font-semibold text-slate-200">
                  ${data?.technicals.ma50.toFixed(2)}
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  MA200 (长期趋势)
                </div>
                <div className="font-mono font-semibold text-slate-200">
                  ${data?.technicals.ma200.toFixed(2)}
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  60日动量
                </div>
                <div
                  className={`font-mono font-semibold ${
                    data?.technicals.momentum_60d &&
                    data.technicals.momentum_60d > 0
                      ? "text-emerald-400"
                      : "text-rose-400"
                  }`}
                >
                  {data?.technicals.momentum_60d.toFixed(1)}%
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  年化波动率
                </div>
                <div className="font-mono font-semibold text-slate-200">
                  {data?.technicals.volatility.toFixed(1)}%
                </div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div className="text-xs text-slate-500 uppercase mb-1">
                  ATR (波动幅度)
                </div>
                <div className="font-mono font-semibold text-slate-200">
                  ${data?.technicals.atr.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar: Trading Plan */}
        <div className="space-y-6">
          <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
            <div className="flex items-center gap-2 mb-4 text-emerald-400">
              <span className="text-xl">📈</span>
              <h3 className="font-bold">入场计划 (Entry)</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.entry_levels.aggressive_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.entry_levels.aggressive.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-emerald-900/20 rounded-lg border border-emerald-500/20">
                <div className="flex flex-col">
                  <span className="text-sm text-emerald-200 font-medium">
                    ✨ {data?.entry_levels.moderate_label}
                  </span>
                  <span className="text-[10px] text-emerald-400/70">
                    推荐挂单价位
                  </span>
                </div>
                <span className="font-mono font-bold text-emerald-400">
                  ${data?.entry_levels.moderate.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.entry_levels.conservative_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.entry_levels.conservative.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
            <div className="flex items-center gap-2 mb-4 text-rose-400">
              <span className="text-xl">🛑</span>
              <h3 className="font-bold">风控止损 (Stop Loss)</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.stop_levels.tight_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.stop_levels.tight.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-rose-900/10 rounded-lg border border-rose-500/20">
                <span className="text-sm text-rose-200">
                  {data?.stop_levels.normal_label}
                </span>
                <span className="font-mono font-bold text-rose-400">
                  ${data?.stop_levels.normal.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.stop_levels.loose_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.stop_levels.loose.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 rounded-2xl p-6 border border-slate-800">
            <div className="flex items-center gap-2 mb-4 text-sky-400">
              <span className="text-xl">🎯</span>
              <h3 className="font-bold">获利目标 (Take Profit)</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-sky-900/10 rounded-lg border border-sky-500/20">
                <span className="text-sm text-sky-200">
                  {data?.tp_levels.tp1_label}
                </span>
                <span className="font-mono font-bold text-sky-400">
                  ${data?.tp_levels.tp1.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.tp_levels.tp2_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.tp_levels.tp2.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-slate-700/30">
                <span className="text-sm text-slate-400">
                  {data?.tp_levels.tp3_label}
                </span>
                <span className="font-mono font-bold text-white">
                  ${data?.tp_levels.tp3.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
