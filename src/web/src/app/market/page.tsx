"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = "http://localhost:8000";

interface MarketStatus {
  date: string;
  regime: string;
  risk_budget: number;
  signals: {
    [key: string]: number | boolean | string;
  };
}

export default function MarketPage() {
  const [data, setData] = useState<MarketStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/market`)
      .then((res) => res.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const regimeConfig: Record<
    string,
    { color: string; icon: string; label: string; bg: string; border: string }
  > = {
    RISK_ON: {
      color: "text-emerald-400",
      icon: "🟢",
      label: "风险偏好 (Risk On)",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
    NEUTRAL: {
      color: "text-sky-400", // Changed to Sky for Neutral in Blue theme
      icon: "🔵",
      label: "中性观望 (Neutral)",
      bg: "bg-sky-500/10",
      border: "border-sky-500/20",
    },
    RISK_OFF: {
      color: "text-rose-400",
      icon: "🔴",
      label: "风险厌恶 (Risk Off)",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
    },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-sky-500/30 border-t-sky-500 rounded-full animate-spin"></div>
          <div className="text-slate-400">加载市场数据...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="bg-rose-950/30 border border-rose-900/50 rounded-2xl p-8 text-center">
          <h2 className="text-xl font-semibold text-rose-400 mb-2">连接失败</h2>
          <p className="text-slate-400 mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-rose-900/50 hover:bg-rose-900 text-rose-300 rounded-lg text-sm"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  const regime = regimeConfig[data?.regime || "NEUTRAL"];

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between gap-4 mb-8">
        <h1 className="text-3xl font-bold text-white">🌍 市场状态</h1>
        <Link
          href="/trend-scan"
          className="px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/20 transition-colors text-sm font-medium"
        >
          趋势扫描
        </Link>
      </div>

      {/* Main Status Card */}
      <div
        className={`rounded-2xl p-8 mb-8 border backdrop-blur-sm ${regime.bg} ${regime.border}`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
          <div>
            <p className="text-slate-400 text-sm uppercase tracking-wider font-semibold mb-2">
              当前趋势
            </p>
            <div
              className={`text-4xl font-bold ${regime.color} flex items-center gap-3`}
            >
              {regime.label}
            </div>
          </div>
          <div className="md:text-right">
            <p className="text-slate-400 text-sm uppercase tracking-wider font-semibold mb-2">
              数据更新于
            </p>
            <div className="text-2xl font-mono text-slate-200">
              {data?.date}
            </div>
          </div>
        </div>

        {/* Risk Budget Bar */}
        <div className="mb-8">
          <div className="flex justify-between text-sm text-slate-300 mb-2">
            <span>仓位建议 (Risk Budget)</span>
            <span className="font-mono">
              {((data?.risk_budget || 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-slate-900/50 rounded-full h-3 overflow-hidden border border-slate-700/30">
            <div
              className={`h-full rounded-full transition-all duration-1000 ease-out bg-gradient-to-r from-sky-500 to-blue-600`}
              style={{ width: `${(data?.risk_budget || 0) * 100}%` }}
            />
          </div>
        </div>

        {/* Interpretation */}
        <div className="bg-slate-900/40 rounded-xl p-5 border border-slate-700/30">
          <h3 className="font-semibold mb-2 text-sky-400 flex items-center gap-2">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            策略解读
          </h3>
          <p className="text-slate-300 leading-relaxed">
            {data?.regime === "RISK_ON" &&
              "市场动量强劲，处于上升趋势。系统建议增加权益类资产配置，积极参与市场机会。"}
            {data?.regime === "NEUTRAL" &&
              "市场趋势不明确或处于震荡整理。建议保持中性仓位，耐心等待趋势确认。"}
            {data?.regime === "RISK_OFF" &&
              "市场波动率上升或动量转负。系统建议大幅降低风险敞口，优先保本，增配现金或债券。"}
          </p>
        </div>
      </div>

      {/* Signals Grid */}
      {data?.signals && (
        <div>
          <h2 className="text-xl font-bold mb-6 text-slate-200 flex items-center gap-2">
            ⚙️ 核心指标详情
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {Object.entries(data.signals).map(([key, value]) => (
              <div
                key={key}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-sky-500/30 transition-colors"
              >
                <div className="text-sm text-slate-400 font-medium uppercase tracking-wide">
                  {key}
                </div>
                <div className="text-lg font-mono font-semibold text-slate-200">
                  {typeof value === "boolean" ? (
                    value ? (
                      <span className="text-emerald-400">TRUE</span>
                    ) : (
                      <span className="text-rose-400">FALSE</span>
                    )
                  ) : typeof value === "number" ? (
                    value.toFixed(2)
                  ) : (
                    value
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
