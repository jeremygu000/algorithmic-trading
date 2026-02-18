"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = "http://localhost:8000";
type PickSizeFilter = "all" | "large" | "small";

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
  size: PickSizeFilter;
  size_label: string;
  eligible_stock_count: number;
  is_active: boolean;
  message: string;
  picks: TradePlan[];
}

interface WatchlistData {
  count: number;
  symbols: string[];
}

export default function PicksPage() {
  const [data, setData] = useState<PicksData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sizeFilter, setSizeFilter] = useState<PickSizeFilter>("all");
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [watchInput, setWatchInput] = useState("");
  const [watchLoading, setWatchLoading] = useState(false);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const handleFilterChange = (nextFilter: PickSizeFilter) => {
    if (nextFilter === sizeFilter) return;
    setLoading(true);
    setError(null);
    setSizeFilter(nextFilter);
  };

  const loadWatchlist = () => {
    fetch(`${API_BASE}/api/watchlist`)
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "加载 watch list 失败");
        }
        return res.json() as Promise<WatchlistData>;
      })
      .then((res) => setWatchlist(res.symbols || []))
      .catch((e: unknown) => {
        setWatchError(e instanceof Error ? e.message : "加载 watch list 失败");
      });
  };

  const addWatchSymbol = (e: React.FormEvent) => {
    e.preventDefault();
    if (!watchInput.trim()) return;
    setWatchLoading(true);
    setWatchError(null);

    fetch(`${API_BASE}/api/watchlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: watchInput.trim().toUpperCase() }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "添加失败");
        }
        return res.json() as Promise<WatchlistData>;
      })
      .then((res) => {
        setWatchlist(res.symbols || []);
        setWatchInput("");
        setReloadTick((n) => n + 1);
      })
      .catch((e: unknown) => {
        setWatchError(e instanceof Error ? e.message : "添加失败");
      })
      .finally(() => setWatchLoading(false));
  };

  const removeWatchSymbol = (symbol: string) => {
    setWatchLoading(true);
    setWatchError(null);

    fetch(`${API_BASE}/api/watchlist/${symbol}`, { method: "DELETE" })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "删除失败");
        }
        return res.json() as Promise<WatchlistData>;
      })
      .then((res) => {
        setWatchlist(res.symbols || []);
        setReloadTick((n) => n + 1);
      })
      .catch((e: unknown) => {
        setWatchError(e instanceof Error ? e.message : "删除失败");
      })
      .finally(() => setWatchLoading(false));
  };

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 45000);

    fetch(`${API_BASE}/api/picks?size=${sizeFilter}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "加载推荐失败");
        }
        return res.json() as Promise<PicksData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") {
          setError("请求超时（45秒），请稍后重试或缩小筛选范围");
          return;
        }
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        setLoading(false);
      });

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [sizeFilter, reloadTick]);

  useEffect(() => {
    loadWatchlist();
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

      {/* Watch List */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 mb-6">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-300 font-medium">
              Watch List (动态候选池)
            </div>
            <div className="text-xs text-slate-500">
              当前 {watchlist.length} 只
            </div>
          </div>

          <form onSubmit={addWatchSymbol} className="flex gap-2">
            <input
              value={watchInput}
              onChange={(e) => setWatchInput(e.target.value.toUpperCase())}
              placeholder="输入股票代码，例如 PLTR"
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
            />
            <button
              type="submit"
              disabled={watchLoading}
              className="px-3 py-2 rounded-lg bg-sky-500/20 border border-sky-500/30 text-sky-300 text-sm hover:bg-sky-500/30 disabled:opacity-50"
            >
              添加
            </button>
          </form>

          {watchError && <div className="text-xs text-rose-400">{watchError}</div>}

          <div className="flex flex-wrap gap-2">
            {watchlist.length > 0 ? (
              watchlist.map((sym) => (
                <span
                  key={sym}
                  className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-slate-800 border border-slate-700 text-xs text-slate-200"
                >
                  {sym}
                  <button
                    type="button"
                    disabled={watchLoading}
                    onClick={() => removeWatchSymbol(sym)}
                    className="text-rose-400 hover:text-rose-300 disabled:opacity-50"
                    aria-label={`remove-${sym}`}
                  >
                    ×
                  </button>
                </span>
              ))
            ) : (
              <div className="text-xs text-slate-500">暂无 watch list 标的</div>
            )}
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-slate-400">规模筛选 (Russell)</span>
          <button
            type="button"
            onClick={() => handleFilterChange("all")}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              sizeFilter === "all"
                ? "bg-sky-500/20 border-sky-500/30 text-sky-300"
                : "bg-slate-800 border-slate-700 text-slate-400 hover:text-sky-300"
            }`}
          >
            全部
          </button>
          <button
            type="button"
            onClick={() => handleFilterChange("large")}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              sizeFilter === "large"
                ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-300"
                : "bg-slate-800 border-slate-700 text-slate-400 hover:text-emerald-300"
            }`}
          >
            大盘股
          </button>
          <button
            type="button"
            onClick={() => handleFilterChange("small")}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              sizeFilter === "small"
                ? "bg-amber-500/20 border-amber-500/30 text-amber-300"
                : "bg-slate-800 border-slate-700 text-slate-400 hover:text-amber-300"
            }`}
          >
            小盘股
          </button>
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
            <div className="text-xs opacity-80 mb-1">
              当前范围: {data?.size_label || "全部"} | 可参与筛选:
              {" "}
              {data?.eligible_stock_count ?? 0}
              {" "}
              只
            </div>
            <div className="text-sm opacity-90">{data?.message}</div>
          </div>
        </div>
      </div>

      {/* Stock Cards */}
      {data?.picks && data.picks.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-6">
          {data.picks.map((pick, idx) => (
            <Link
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
            </Link>
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
