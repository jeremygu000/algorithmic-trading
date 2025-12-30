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
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">筛选优质标的中...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-2xl p-8 text-center">
          <p className="text-rose-400 mb-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">
            🎯 智能选股推荐
          </h1>
          <p className="text-slate-400">
            基于多因子模型的每日精选 (动量 + 波动率 + 趋势)
          </p>
        </div>
        <div className="px-4 py-2 bg-slate-900 rounded-lg border border-slate-800 text-sm font-mono text-slate-400">
          📅 {data?.date}
        </div>
      </div>

      {/* Status Banner */}
      <div
        className={`rounded-xl p-4 mb-10 border ${
          data?.is_active
            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
            : "bg-amber-500/10 border-amber-500/20 text-amber-300"
        }`}
      >
        <div className="flex items-start gap-3">
          <span className="text-xl mt-0.5">
            {data?.is_active ? "✅" : "⚠️"}
          </span>
          <div>
            <div className="font-semibold mb-1">系统状态: {data?.regime}</div>
            <div className="text-sm opacity-90">{data?.message}</div>
          </div>
        </div>
      </div>

      {/* Stock Cards */}
      {data?.picks && data.picks.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-6">
          {data.picks.map((pick, idx) => (
            <a
              key={pick.symbol}
              href={`/stock/${pick.symbol}`}
              className="bg-slate-900 block rounded-xl border border-slate-800 hover:border-sky-500 transition-all duration-300 group hover:shadow-xl hover:shadow-sky-500/10"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800 text-sky-400 font-bold border border-slate-700">
                      {idx + 1}
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-white group-hover:text-sky-400 transition-colors">
                        {pick.symbol}
                      </h3>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                      现价
                    </div>
                    <div className="text-2xl font-mono font-semibold text-slate-200">
                      ${pick.current_price.toFixed(2)}
                    </div>
                  </div>
                </div>

                <p className="text-sm text-slate-400 mb-6 line-clamp-2 min-h-[2.5em]">
                  {pick.reason}
                </p>

                {/* Price Levels */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                    <div className="text-slate-500 text-[10px] uppercase mb-1">
                      入场 (稳健)
                    </div>
                    <div className="text-emerald-400 font-mono font-medium">
                      ${pick.entry_levels.moderate.toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                    <div className="text-slate-500 text-[10px] uppercase mb-1">
                      止损 (标准)
                    </div>
                    <div className="text-rose-400 font-mono font-medium">
                      ${pick.stop_levels.normal.toFixed(2)}
                    </div>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
                    <div className="text-slate-500 text-[10px] uppercase mb-1">
                      目标 (TP1)
                    </div>
                    <div className="text-sky-400 font-mono font-medium">
                      ${pick.take_profit_levels.tp1.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            </a>
          ))}
        </div>
      ) : (
        <div className="bg-slate-900 rounded-2xl p-16 border border-slate-800 text-center col-span-2">
          <div className="text-6xl mb-6 opacity-20">📭</div>
          <h3 className="text-xl font-semibold text-slate-300 mb-2">
            暂无推荐
          </h3>
          <p className="text-slate-500">
            当前市场环境下，模型未筛选出符合高胜率条件的标的。
          </p>
        </div>
      )}

      {/* Risk Warning */}
      <div className="mt-12 p-6 bg-slate-900/50 rounded-xl border border-slate-800/50">
        <h3 className="font-semibold text-sky-400 mb-3 text-sm uppercase tracking-wider">
          ⚠️ 风险提示
        </h3>
        <ul className="text-slate-500 text-sm space-y-2 list-disc list-inside">
          <li>
            个股波动风险显著高于 ETF，建议严格控制单只股票仓位（推荐 ≤5%）。
          </li>
          <li>
            请务必严格执行止损策略。当价格达到止盈目标时，建议分批减仓锁定利润。
          </li>
          <li>本系统生成的信号仅供量化研究参考，不构成具体投资建议。</li>
        </ul>
      </div>
    </div>
  );
}
