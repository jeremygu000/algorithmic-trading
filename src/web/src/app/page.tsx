"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = "http://localhost:8000";

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      router.push(`/stock/${symbol.toUpperCase()}`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent">
          ETF Trend 股票分析系统
        </h1>
        <p className="text-xl text-gray-400 mb-8">
          基于动量和趋势的量化分析 • 多级买卖点位 • 蜡烛图可视化
        </p>

        {/* Search Box */}
        <form onSubmit={handleSearch} className="max-w-xl mx-auto">
          <div className="flex gap-4">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="输入股票代码 (如 AAPL, NVDA, TSLA)"
              className="flex-1 px-6 py-4 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
            />
            <button
              type="submit"
              className="px-8 py-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl transition-colors"
            >
              分析
            </button>
          </div>
        </form>
      </div>

      {/* Quick Links */}
      <div className="grid md:grid-cols-3 gap-6 mb-16">
        <a
          href="/market"
          className="group p-6 bg-gray-800 rounded-xl border border-gray-700 hover:border-emerald-500 transition-all"
        >
          <div className="text-4xl mb-4">🌍</div>
          <h3 className="text-xl font-semibold mb-2 group-hover:text-emerald-400">
            市场状态
          </h3>
          <p className="text-gray-400">
            查看当前市场状态 (RISK_ON / NEUTRAL /
            RISK_OFF)、风险预算和关键技术指标
          </p>
        </a>

        <a
          href="/picks"
          className="group p-6 bg-gray-800 rounded-xl border border-gray-700 hover:border-blue-500 transition-all"
        >
          <div className="text-4xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold mb-2 group-hover:text-blue-400">
            今日推荐
          </h3>
          <p className="text-gray-400">
            获取今日推荐个股列表，包含多级入场/止损/止盈价位
          </p>
        </a>

        <a
          href="/stock/AAPL"
          className="group p-6 bg-gray-800 rounded-xl border border-gray-700 hover:border-purple-500 transition-all"
        >
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-xl font-semibold mb-2 group-hover:text-purple-400">
            股票分析
          </h3>
          <p className="text-gray-400">
            查询任意美股的蜡烛图、技术指标和多级交易价位
          </p>
        </a>
      </div>

      {/* Popular Stocks */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h2 className="text-xl font-semibold mb-4">热门股票快速查询</h2>
        <div className="flex flex-wrap gap-3">
          {[
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "NVDA",
            "TSLA",
            "META",
            "JPM",
            "V",
            "JNJ",
          ].map((s) => (
            <a
              key={s}
              href={`/stock/${s}`}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-medium transition-colors"
            >
              {s}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
