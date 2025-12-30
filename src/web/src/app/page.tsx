"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

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
    <div className="max-w-7xl mx-auto px-4 py-16">
      {/* Hero Section */}
      <div className="text-center mb-20">
        <div className="inline-block p-2 px-4 rounded-full bg-slate-900 border border-slate-800 text-sky-400 text-sm font-medium mb-6">
          ✨ 量化交易系统 v2.0
        </div>
        <h1 className="text-5xl md:text-6xl font-bold mb-6 tracking-tight">
          <span className="text-white">发现下一个</span>
          <span className="bg-gradient-to-r from-sky-400 via-blue-500 to-cyan-400 bg-clip-text text-transparent">
            {" "}
            交易机会
          </span>
        </h1>
        <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
          基于动量和趋势的专业量化分析平台。提供多级买卖点位、ATR
          动态止损与交互式蜡烛图分析。
        </p>

        {/* Search Box */}
        <form
          onSubmit={handleSearch}
          className="max-w-xl mx-auto relative group"
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-sky-500 to-blue-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-200"></div>
          <div className="relative flex gap-2 p-2 bg-slate-900 border border-slate-700/50 rounded-xl">
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="输入股票代码 (如 AAPL, MSFT)"
              className="flex-1 px-4 py-3 bg-transparent text-white placeholder-slate-500 focus:outline-none text-lg"
            />
            <button
              type="submit"
              className="px-8 py-3 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg transition-all shadow-lg shadow-sky-500/20"
            >
              分析
            </button>
          </div>
        </form>
      </div>

      {/* Quick Links */}
      <div className="grid md:grid-cols-3 gap-6 mb-20">
        <a
          href="/market"
          className="group relative p-8 bg-slate-900 rounded-2xl border border-slate-800 hover:border-sky-500/50 transition-all hover:shadow-2xl hover:shadow-sky-500/10 overflow-hidden"
        >
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <span className="text-8xl">🌍</span>
          </div>
          <div className="relative z-10">
            <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
              🌍
            </div>
            <h3 className="text-xl font-bold mb-3 text-slate-200 group-hover:text-sky-400 transition-colors">
              市场状态
            </h3>
            <p className="text-slate-400 leading-relaxed">
              实时监控市场情绪 (Risk On/Off)，查看风险预算分配与关键市场信号。
            </p>
          </div>
        </a>

        <a
          href="/picks"
          className="group relative p-8 bg-slate-900 rounded-2xl border border-slate-800 hover:border-blue-500/50 transition-all hover:shadow-2xl hover:shadow-blue-500/10 overflow-hidden"
        >
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <span className="text-8xl">🎯</span>
          </div>
          <div className="relative z-10">
            <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
              🎯
            </div>
            <h3 className="text-xl font-bold mb-3 text-slate-200 group-hover:text-blue-400 transition-colors">
              今日推荐
            </h3>
            <p className="text-slate-400 leading-relaxed">
              AI
              筛选的高动量个股列表，包含激进/稳健/保守三级买入方案与动态止损位。
            </p>
          </div>
        </a>

        <a
          href="/stock/AAPL"
          className="group relative p-8 bg-slate-900 rounded-2xl border border-slate-800 hover:border-cyan-500/50 transition-all hover:shadow-2xl hover:shadow-cyan-500/10 overflow-hidden"
        >
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <span className="text-8xl">📊</span>
          </div>
          <div className="relative z-10">
            <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform duration-300">
              📊
            </div>
            <h3 className="text-xl font-bold mb-3 text-slate-200 group-hover:text-cyan-400 transition-colors">
              深度分析
            </h3>
            <p className="text-slate-400 leading-relaxed">
              交互式 K
              线图表，集成均线系统与关键支撑阻力位，提供完整的技术面诊断。
            </p>
          </div>
        </a>
      </div>

      {/* Popular Stocks */}
      <div className="text-center">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6">
          热门关注
        </h2>
        <div className="flex flex-wrap justify-center gap-3">
          {[
            "AAPL",
            "NVDA",
            "TSLA",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "AMD",
            "PLTR",
            "COIN",
          ].map((s) => (
            <a
              key={s}
              href={`/stock/${s}`}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-sky-500/30 rounded-lg text-sm font-medium text-slate-300 hover:text-sky-400 transition-all"
            >
              {s}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
