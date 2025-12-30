"use client";

import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";

interface TradePlan {
  symbol: string;
  action: string;
  current_price: number;
  entry_levels: {
    aggressive: number;
    moderate: number;
    conservative: number;
  };
  stop_levels: {
    tight: number;
    normal: number;
    loose: number;
  };
  take_profit_levels: {
    tp1: number;
    tp2: number;
    tp3: number;
  };
  reason: string;
}

interface PicksData {
  date: string;
  regime: string;
  risk_budget: number;
  is_active: boolean;
  message: string;
  picks: TradePlan[];
}

export default function PicksPage() {
  const [data, setData] = useState<PicksData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/picks`)
      .then((res) => res.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-xl text-gray-400">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-red-400 mb-2">加载失败</h2>
          <p className="text-gray-400">{error}</p>
          <p className="text-gray-500 mt-2 text-sm">
            请确保 FastAPI 服务正在运行 (端口 8000)
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">🎯 今日推荐</h1>
        <div className="text-gray-400">{data?.date}</div>
      </div>

      {/* Status Banner */}
      <div
        className={`rounded-xl p-4 mb-8 ${
          data?.is_active
            ? "bg-emerald-900/30 border border-emerald-700"
            : "bg-yellow-900/30 border border-yellow-700"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{data?.is_active ? "✅" : "⚠️"}</span>
          <div>
            <span
              className={`font-semibold ${
                data?.is_active ? "text-emerald-400" : "text-yellow-400"
              }`}
            >
              {data?.regime}
            </span>
            <span className="text-gray-400 ml-2">• {data?.message}</span>
          </div>
        </div>
      </div>

      {/* Stock Cards */}
      {data?.picks && data.picks.length > 0 ? (
        <div className="grid md:grid-cols-2 gap-6">
          {data.picks.map((pick, idx) => (
            <a
              key={pick.symbol}
              href={`/stock/${pick.symbol}`}
              className="bg-gray-800 rounded-xl p-6 border border-gray-700 hover:border-emerald-500 transition-all group"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-bold text-emerald-400">
                    #{idx + 1}
                  </span>
                  <div>
                    <h3 className="text-xl font-semibold group-hover:text-emerald-400">
                      {pick.symbol}
                    </h3>
                    <p className="text-sm text-gray-400 truncate max-w-[200px]">
                      {pick.reason}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-400">当前</div>
                  <div className="text-xl font-semibold">
                    ${pick.current_price.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* Price Levels */}
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="text-gray-400 text-xs mb-1">入场 (稳健)</div>
                  <div className="text-emerald-400 font-medium">
                    ${pick.entry_levels.moderate.toFixed(2)}
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="text-gray-400 text-xs mb-1">止损 (标准)</div>
                  <div className="text-red-400 font-medium">
                    ${pick.stop_levels.normal.toFixed(2)}
                  </div>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <div className="text-gray-400 text-xs mb-1">止盈 (TP1)</div>
                  <div className="text-blue-400 font-medium">
                    ${pick.take_profit_levels.tp1.toFixed(2)}
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div className="bg-gray-800 rounded-xl p-12 border border-gray-700 text-center">
          <div className="text-4xl mb-4">📭</div>
          <p className="text-xl text-gray-400">暂无推荐个股</p>
          <p className="text-gray-500 mt-2">当前市场状态不适合配置个股</p>
        </div>
      )}

      {/* Risk Warning */}
      <div className="mt-8 bg-gray-800/50 rounded-xl p-4 border border-gray-700">
        <h3 className="font-semibold text-yellow-400 mb-2">⚠️ 风险提示</h3>
        <ul className="text-gray-400 text-sm space-y-1">
          <li>• 个股波动远大于 ETF，建议单只仓位 ≤5%，总仓位 ≤20%</li>
          <li>• 入场后严格执行止损，到达止盈目标分批减仓</li>
          <li>• 本推荐仅供参考，不构成投资建议</li>
        </ul>
      </div>
    </div>
  );
}
