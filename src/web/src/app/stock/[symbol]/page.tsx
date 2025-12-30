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
    强烈推荐: "bg-emerald-900/50 text-emerald-400 border-emerald-600",
    推荐: "bg-blue-900/50 text-blue-400 border-blue-600",
    观望: "bg-yellow-900/50 text-yellow-400 border-yellow-600",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-xl text-gray-400">加载 {symbol} 数据中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-red-400 mb-2">加载失败</h2>
          <p className="text-gray-400">{error}</p>
          <a
            href="/"
            className="inline-block mt-4 text-emerald-400 hover:underline"
          >
            ← 返回首页
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <div>
          <h1 className="text-4xl font-bold">{data?.symbol}</h1>
          <p className="text-gray-400 text-lg">{data?.name}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-sm text-gray-400">当前价格</div>
            <div className="text-3xl font-bold">
              ${data?.current_price.toFixed(2)}
            </div>
          </div>
          <div
            className={`px-4 py-2 rounded-lg border ${
              recommendationStyle[data?.recommendation || "观望"]
            }`}
          >
            {data?.recommendation}
          </div>
        </div>
      </div>

      {/* Reason */}
      <div className="bg-gray-800 rounded-xl p-4 mb-8 border border-gray-700">
        <span className="text-gray-400">分析理由: </span>
        <span className="text-gray-200">{data?.reason}</span>
      </div>

      {/* Chart */}
      {data?.chart_base64 && (
        <div className="bg-gray-800 rounded-xl p-4 mb-8 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4">📊 蜡烛图</h2>
          <img
            src={`data:image/png;base64,${data.chart_base64}`}
            alt={`${data.symbol} 蜡烛图`}
            className="w-full rounded-lg"
          />
        </div>
      )}

      {/* Price Levels Grid */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        {/* Entry Levels */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-emerald-400 mb-4">
            📈 入场价位
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.entry_levels.aggressive_label}
              </span>
              <span className="font-semibold">
                ${data?.entry_levels.aggressive.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.entry_levels.moderate_label}
              </span>
              <span className="font-semibold">
                ${data?.entry_levels.moderate.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.entry_levels.conservative_label}
              </span>
              <span className="font-semibold">
                ${data?.entry_levels.conservative.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Stop Levels */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-red-400 mb-4">
            🛑 止损价位
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.stop_levels.tight_label}
              </span>
              <span className="font-semibold">
                ${data?.stop_levels.tight.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.stop_levels.normal_label}
              </span>
              <span className="font-semibold">
                ${data?.stop_levels.normal.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">
                {data?.stop_levels.loose_label}
              </span>
              <span className="font-semibold">
                ${data?.stop_levels.loose.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* TP Levels */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-blue-400 mb-4">
            🎯 止盈目标
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-400">{data?.tp_levels.tp1_label}</span>
              <span className="font-semibold">
                ${data?.tp_levels.tp1.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{data?.tp_levels.tp2_label}</span>
              <span className="font-semibold">
                ${data?.tp_levels.tp2.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{data?.tp_levels.tp3_label}</span>
              <span className="font-semibold">
                ${data?.tp_levels.tp3.toFixed(2)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Technical Indicators */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">📉 技术指标</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">MA20</div>
            <div className="font-semibold">
              ${data?.technicals.ma20.toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">MA50</div>
            <div className="font-semibold">
              ${data?.technicals.ma50.toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">MA200</div>
            <div className="font-semibold">
              ${data?.technicals.ma200.toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">60日动量</div>
            <div
              className={`font-semibold ${
                data?.technicals.momentum_60d &&
                data.technicals.momentum_60d > 0
                  ? "text-emerald-400"
                  : "text-red-400"
              }`}
            >
              {data?.technicals.momentum_60d.toFixed(1)}%
            </div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">年化波动率</div>
            <div className="font-semibold">
              {data?.technicals.volatility.toFixed(1)}%
            </div>
          </div>
          <div className="bg-gray-700/50 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-1">ATR</div>
            <div className="font-semibold">
              ${data?.technicals.atr.toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
