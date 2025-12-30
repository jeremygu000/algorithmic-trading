"use client";

import { useEffect, useState } from "react";

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
    { color: string; icon: string; label: string }
  > = {
    RISK_ON: { color: "text-emerald-400", icon: "🟢", label: "风险偏好" },
    NEUTRAL: { color: "text-yellow-400", icon: "🟡", label: "中性观望" },
    RISK_OFF: { color: "text-red-400", icon: "🔴", label: "风险厌恶" },
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-xl text-gray-400">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
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

  const regime = regimeConfig[data?.regime || "NEUTRAL"];

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8">🌍 市场状态</h1>

      {/* Main Status Card */}
      <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 mb-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-gray-400 text-sm mb-1">当前市场状态</p>
            <div className={`text-4xl font-bold ${regime.color}`}>
              {regime.icon} {regime.label}
            </div>
          </div>
          <div className="text-right">
            <p className="text-gray-400 text-sm mb-1">分析日期</p>
            <div className="text-2xl font-semibold">{data?.date}</div>
          </div>
        </div>

        {/* Risk Budget Bar */}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-400 mb-2">
            <span>风险预算</span>
            <span>{((data?.risk_budget || 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-4">
            <div
              className="bg-gradient-to-r from-emerald-500 to-blue-500 h-4 rounded-full transition-all"
              style={{ width: `${(data?.risk_budget || 0) * 100}%` }}
            />
          </div>
        </div>

        {/* Interpretation */}
        <div className="bg-gray-700/50 rounded-lg p-4">
          <h3 className="font-semibold mb-2">💡 解读</h3>
          <p className="text-gray-300">
            {data?.regime === "RISK_ON" &&
              "市场处于风险偏好状态，可适当增加权益类资产配置。"}
            {data?.regime === "NEUTRAL" &&
              "市场处于中性状态，建议保持均衡配置，观望为主。"}
            {data?.regime === "RISK_OFF" &&
              "市场处于避险状态，建议降低权益敞口，增配防守资产。"}
          </p>
        </div>
      </div>

      {/* Signals Grid */}
      {data?.signals && (
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h2 className="text-xl font-semibold mb-4">📊 关键信号</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {Object.entries(data.signals).map(([key, value]) => (
              <div key={key} className="bg-gray-700/50 rounded-lg p-4">
                <div className="text-sm text-gray-400 mb-1">{key}</div>
                <div className="text-xl font-semibold">
                  {typeof value === "boolean"
                    ? value
                      ? "✅ 是"
                      : "❌ 否"
                    : typeof value === "number"
                    ? value.toFixed(2)
                    : value}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
