"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

const API_BASE = "http://localhost:8300";

type TrendDirection = "up" | "down";

interface ScannedStock {
  symbol: string;
  name: string;
  latest_price: number;
  daily_changes_pct: number[];
}

interface TrendScanData {
  date: string;
  k: number;
  trend: TrendDirection;
  trend_label: string;
  total_scanned: number;
  matched_count: number;
  stocks: ScannedStock[];
}

function calcCumulativeChange(changes: number[]): number {
  return changes.reduce((acc, pct) => acc * (1 + pct / 100), 1) - 1;
}

export default function TrendScanPage() {
  const [k, setK] = useState<number>(5);
  const [trend, setTrend] = useState<TrendDirection>("up");
  const [data, setData] = useState<TrendScanData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const handleTrendChange = (nextTrend: TrendDirection) => {
    if (nextTrend === trend) return;
    setLoading(true);
    setError(null);
    setTrend(nextTrend);
  };

  const handleKChange = (nextK: number) => {
    if (nextK === k) return;
    setLoading(true);
    setError(null);
    setK(nextK);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/stocks/trend-scan?k=${k}&t=${trend}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "趋势扫描请求失败");
        }
        return res.json() as Promise<TrendScanData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") {
          return;
        }
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [k, trend]);

  const trendStyle = useMemo(
    () =>
      trend === "up"
        ? {
            badge: "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
            cardBorder: "hover:border-emerald-500/40",
          }
        : {
            badge: "bg-rose-500/10 border-rose-500/20 text-rose-300",
            cardBorder: "hover:border-rose-500/40",
          },
    [trend]
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">📡 趋势扫描</h1>
          <p className="text-slate-400">
            按最近 K 日连续上涨/下跌形态筛选股票池，点击股票名称可进入深度分析页面。
          </p>
        </div>
        <div className="px-4 py-2 bg-slate-900 rounded-lg border border-slate-800 text-sm font-mono text-slate-400">
          📅 {data?.date || "--"}
        </div>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800 p-5 mb-8">
        <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">趋势方向</span>
            <button
              type="button"
              onClick={() => handleTrendChange("up")}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                trend === "up"
                  ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-300"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:text-emerald-300"
              }`}
            >
              上涨
            </button>
            <button
              type="button"
              onClick={() => handleTrendChange("down")}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                trend === "down"
                  ? "bg-rose-500/20 border-rose-500/30 text-rose-300"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:text-rose-300"
              }`}
            >
              下跌
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">连续天数 K</span>
            <select
              value={k}
              onChange={(e) => handleKChange(Number(e.target.value))}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {[3, 5, 7, 10].map((val) => (
                <option key={val} value={val}>
                  {val}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center min-h-[32vh]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-8 h-8 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin"></div>
            <div className="text-slate-400">扫描中...</div>
          </div>
        </div>
      )}

      {!loading && error && (
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-2xl p-8 text-center">
          <h2 className="text-xl font-semibold text-rose-400 mb-2">扫描失败</h2>
          <p className="text-slate-400 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-rose-900/50 hover:bg-rose-900 text-rose-300 rounded-lg text-sm"
          >
            重试
          </button>
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className={`rounded-xl border p-4 mb-6 ${trendStyle.badge}`}>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
              <span>
                方向: <b>{data.trend_label}</b>
              </span>
              <span>
                K: <b>{data.k}</b>
              </span>
              <span>
                扫描总数: <b>{data.total_scanned}</b>
              </span>
              <span>
                命中: <b>{data.matched_count}</b>
              </span>
            </div>
          </div>

          {data.stocks.length > 0 ? (
            <div className="grid md:grid-cols-2 gap-6">
              {data.stocks.map((stock, idx) => {
                const cumulative = calcCumulativeChange(stock.daily_changes_pct);
                const cumulativeColor =
                  cumulative >= 0 ? "text-emerald-400" : "text-rose-400";

                return (
                  <div
                    key={stock.symbol}
                    className={`bg-slate-900 rounded-xl border border-slate-800 ${trendStyle.cardBorder} transition-all duration-300 hover:shadow-xl`}
                  >
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-5">
                        <div className="flex items-center gap-4">
                          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-800 text-sky-400 font-bold border border-slate-700">
                            {idx + 1}
                          </div>
                          <div>
                            <Link
                              href={`/stock/${stock.symbol}`}
                              className={`text-2xl font-bold text-white transition-colors ${
                                trend === "up"
                                  ? "hover:text-emerald-400"
                                  : "hover:text-rose-400"
                              }`}
                            >
                              {stock.symbol}
                            </Link>
                            <div className="text-sm text-slate-400">{stock.name}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">
                            最新价
                          </div>
                          <div className="text-2xl font-mono font-semibold text-slate-200">
                            ${stock.latest_price.toFixed(2)}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between mb-4">
                        <span className="text-sm text-slate-400">
                          近 {stock.daily_changes_pct.length} 日累计变化
                        </span>
                        <span className={`text-lg font-mono font-semibold ${cumulativeColor}`}>
                          {(cumulative * 100).toFixed(2)}%
                        </span>
                      </div>

                      <div className="grid grid-cols-5 gap-2">
                        {stock.daily_changes_pct.map((dayPct, i) => (
                          <div
                            key={`${stock.symbol}-${i}`}
                            className="bg-slate-800/50 rounded-lg border border-slate-700/40 p-2 text-center"
                          >
                            <div className="text-[10px] text-slate-500 mb-1">
                              D-{stock.daily_changes_pct.length - i}
                            </div>
                            <div
                              className={`text-xs font-mono ${
                                dayPct >= 0 ? "text-emerald-400" : "text-rose-400"
                              }`}
                            >
                              {dayPct > 0 ? "+" : ""}
                              {dayPct.toFixed(2)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-slate-900 rounded-2xl p-14 border border-slate-800 text-center">
              <div className="text-6xl mb-6 opacity-20">🧭</div>
              <h3 className="text-xl font-semibold text-slate-300 mb-2">
                暂无符合条件的股票
              </h3>
              <p className="text-slate-500">
                可尝试切换趋势方向或调整 K 值后再次扫描。
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
