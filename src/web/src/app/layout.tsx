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
      <body className="bg-gray-900 text-gray-100 antialiased">
        <nav className="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-8">
                <a href="/" className="text-xl font-bold text-emerald-400">
                  📈 ETF Trend
                </a>
                <div className="flex space-x-4">
                  <a
                    href="/"
                    className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    首页
                  </a>
                  <a
                    href="/market"
                    className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    市场状态
                  </a>
                  <a
                    href="/picks"
                    className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    个股推荐
                  </a>
                  <a
                    href="/stock/AAPL"
                    className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium"
                  >
                    股票分析
                  </a>
                </div>
              </div>
            </div>
          </div>
        </nav>
        <main className="min-h-screen">{children}</main>
        <footer className="bg-gray-800 border-t border-gray-700 py-6">
          <div className="max-w-7xl mx-auto px-4 text-center text-gray-400 text-sm">
            ETF Trend Following System • 仅供参考，不构成投资建议
          </div>
        </footer>
      </body>
    </html>
  );
}
