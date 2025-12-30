import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ETF Trend - 股票分析系统",
  description: "基于动量和趋势的 ETF/股票分析与推荐系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="bg-slate-950 text-slate-100 antialiased">
        <nav className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-8">
                <a
                  href="/"
                  className="text-xl font-bold bg-gradient-to-r from-sky-400 to-cyan-400 bg-clip-text text-transparent"
                >
                  📈 ETF Trend
                </a>
                <div className="flex space-x-4">
                  <a
                    href="/"
                    className="text-slate-400 hover:text-sky-400 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    首页
                  </a>
                  <a
                    href="/market"
                    className="text-slate-400 hover:text-sky-400 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    市场状态
                  </a>
                  <a
                    href="/picks"
                    className="text-slate-400 hover:text-sky-400 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    个股推荐
                  </a>
                  <a
                    href="/stock/AAPL"
                    className="text-slate-400 hover:text-sky-400 px-3 py-2 rounded-md text-sm font-medium transition-colors"
                  >
                    股票分析
                  </a>
                </div>
              </div>
            </div>
          </div>
        </nav>
        <main className="min-h-screen">{children}</main>
        <footer className="bg-slate-900 border-t border-slate-800 py-6 mt-12">
          <div className="max-w-7xl mx-auto px-4 text-center text-slate-500 text-sm">
            ETF Trend Following System • 仅供参考，不构成投资建议
          </div>
        </footer>
      </body>
    </html>
  );
}
