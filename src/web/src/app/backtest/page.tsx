"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import type { ValueType, NameType } from "recharts/types/component/DefaultTooltipContent";

const API_BASE = "http://localhost:8300";

interface EquityCurvePoint {
  date: string;
  nav: number;
  drawdown: number;
  benchmark_nav: number | null;
}

interface ExtendedMetrics {
  [key: string]: number | null;
}

interface MonthlySummary {
  period: string;
  return_pct: number;
  win_rate: number;
  trading_days: number;
}

interface Trade {
  date: string;
  symbol: string;
  action: string;
  shares: number;
  price: number;
  cost: number;
}

interface BacktestData {
  start: string;
  end: string;
  initial_capital: number;
  cost_bps: number;
  rebalance_freq: string;
  final_nav: number;
  total_return_pct: number;
  total_trades: number;
  basic_stats: { [key: string]: number | null };
  extended_metrics: ExtendedMetrics | null;
  equity_curve: EquityCurvePoint[];
  monthly_summary: MonthlySummary[];
  trades: Trade[];
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(decimals);
}

function returnColor(v: number): string {
  return v >= 0 ? "#36bb80" : "#ff7134";
}

function StatBox({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <Box
      sx={{
        bgcolor: "action.hover",
        borderRadius: 1.5,
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        textAlign: "center",
      }}
    >
      <Typography
        sx={{
          color: "text.disabled",
          fontSize: "0.65rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          mb: 0.5,
        }}
      >
        {label}
      </Typography>
      <Typography
        sx={{
          fontFamily: "monospace",
          fontWeight: 600,
          fontSize: "0.9rem",
          color: valueColor ?? "text.primary",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function SectionHeader({ icon, title }: { icon: string; title: string }) {
  return (
    <Typography
      variant="body2"
      sx={{
        fontWeight: 700,
        color: "text.primary",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontSize: "0.75rem",
        display: "flex",
        alignItems: "center",
        gap: 0.75,
        mb: 2,
      }}
    >
      {icon} {title}
    </Typography>
  );
}

const EXTENDED_METRICS_CONFIG: {
  key: string;
  label: string;
  format: (v: number) => string;
  color?: (v: number) => string;
}[] = [
  { key: "Sharpe", label: "夏普比率", format: (v) => v.toFixed(2), color: (v) => returnColor(v) },
  { key: "Sortino", label: "Sortino", format: (v) => v.toFixed(2), color: (v) => returnColor(v) },
  { key: "Max Drawdown", label: "最大回撤", format: (v) => `${(v * 100).toFixed(2)}%`, color: () => "#ff7134" },
  { key: "Calmar", label: "Calmar", format: (v) => v.toFixed(2), color: (v) => returnColor(v) },
  { key: "Win Rate", label: "胜率", format: (v) => `${(v * 100).toFixed(1)}%`, color: (v) => returnColor(v - 0.5) },
  { key: "Profit Factor", label: "盈亏比", format: (v) => v.toFixed(2), color: (v) => returnColor(v - 1) },
  { key: "Max DD Duration (days)", label: "最大回撤天数", format: (v) => String(Math.round(v)) },
  { key: "Ann Return", label: "年化收益", format: (v) => `${(v * 100).toFixed(2)}%`, color: (v) => returnColor(v) },
  { key: "Ann Vol", label: "年化波动", format: (v) => `${(v * 100).toFixed(2)}%` },
  { key: "Tail Ratio (95/5)", label: "尾部比率", format: (v) => v.toFixed(2), color: (v) => returnColor(v - 1) },
  { key: "Common Sense Ratio", label: "常识比率", format: (v) => v.toFixed(2), color: (v) => returnColor(v - 1) },
];

function ExtendedMetricsSection({ metrics }: { metrics: ExtendedMetrics }) {
  const entries = EXTENDED_METRICS_CONFIG.filter((cfg) => metrics[cfg.key] != null);
  if (entries.length === 0) return null;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="🔬" title="扩展绩效指标" />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "1fr 1fr 1fr", md: "repeat(5, 1fr)" },
            gap: 1.5,
          }}
        >
          {entries.map((cfg) => {
            const raw = metrics[cfg.key] as number;
            const formatted = cfg.format(raw);
            const color = cfg.color ? cfg.color(raw) : undefined;
            return <StatBox key={cfg.key} label={cfg.label} value={formatted} valueColor={color} />;
          })}
        </Box>
      </CardContent>
    </Card>
  );
}

function MonthlyChart({ monthly }: { monthly: MonthlySummary[] }) {
  if (monthly.length === 0) return null;

  const chartData = monthly.map((m) => ({
    name: m.period,
    returnPct: parseFloat((m.return_pct * 100).toFixed(2)),
    winRate: parseFloat((m.win_rate * 100).toFixed(1)),
  }));

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="📊" title="月度表现" />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.45)" }}
              axisLine={{ stroke: "rgba(255,255,255,0.15)" }}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tickFormatter={(v: number) => `${v}%`}
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.45)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={(v: number) => `${v}%`}
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.45)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1a2e",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8,
                fontSize: "0.8rem",
              }}
              formatter={(value: ValueType | undefined, name: NameType | undefined) => [
                value != null ? `${value}%` : "—",
                name === "winRate" ? "胜率" : "月收益",
              ]}
            />
            <Legend
              formatter={(value: string) => (value === "winRate" ? "胜率" : "月收益")}
              wrapperStyle={{ fontSize: "0.8rem" }}
            />
            <Bar yAxisId="right" dataKey="winRate" fill="#3b89ff" radius={[3, 3, 0, 0]} />
            <Bar yAxisId="left" dataKey="returnPct" radius={[3, 3, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`monthly-cell-${index}`}
                  fill={entry.returnPct >= 0 ? "#36bb80" : "#ff7134"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

interface EquityTooltipPayload {
  value: number;
  dataKey: string;
}

interface EquityTooltipProps {
  active?: boolean;
  payload?: EquityTooltipPayload[];
  label?: string;
}

function EquityTooltipContent({ active, payload, label }: EquityTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const navEntry = payload.find((p) => p.dataKey === "nav");
  const benchEntry = payload.find((p) => p.dataKey === "benchmark_nav");
  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1.5,
        p: 1.5,
        boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "text.disabled", mb: 0.5 }}>
        {label}
      </Typography>
      {navEntry != null && (
        <Typography
          sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.9rem", color: "#3b89ff" }}
        >
          组合净值: {navEntry.value.toFixed(4)}
        </Typography>
      )}
      {benchEntry != null && benchEntry.value != null && (
        <Typography
          sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.9rem", color: "#fdbc2a" }}
        >
          SPY: {benchEntry.value.toFixed(4)}
        </Typography>
      )}
    </Box>
  );
}

function EquityCurveChart({ equityCurve }: { equityCurve: EquityCurvePoint[] }) {
  const navValues = equityCurve.map((d) => d.nav);
  const benchValues = equityCurve
    .map((d) => d.benchmark_nav)
    .filter((v): v is number => v != null);
  const allValues = [...navValues, ...benchValues];
  const minVal = allValues.length > 0 ? Math.min(...allValues) : 0;
  const maxVal = allValues.length > 0 ? Math.max(...allValues) : 2;
  const padding = (maxVal - minVal) * 0.05;
  const domainMin = Math.floor((minVal - padding) * 1000) / 1000;
  const domainMax = Math.ceil((maxVal + padding) * 1000) / 1000;
  const hasBenchmark = benchValues.length > 0;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="📈" title="净值曲线" />
        <Box sx={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <defs>
                <linearGradient id="btNavGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b89ff" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#3b89ff" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="btBenchGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#fdbc2a" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#fdbc2a" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.12)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fontFamily: "monospace", fill: "#888" }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[domainMin, domainMax]}
                tick={{ fontSize: 11, fontFamily: "monospace", fill: "#888" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => v.toFixed(2)}
                width={60}
              />
              <Tooltip content={<EquityTooltipContent />} />
              <Legend
                formatter={(value) => (
                  <span style={{ fontSize: "0.75rem", color: "inherit" }}>
                    {value === "nav" ? "组合净值" : "SPY"}
                  </span>
                )}
              />
              <Area
                type="monotone"
                dataKey="nav"
                name="nav"
                stroke="#3b89ff"
                strokeWidth={2}
                fill="url(#btNavGradient)"
                dot={false}
                activeDot={{ r: 4, fill: "#3b89ff", strokeWidth: 0 }}
              />
              {hasBenchmark && (
                <Area
                  type="monotone"
                  dataKey="benchmark_nav"
                  name="benchmark_nav"
                  stroke="#fdbc2a"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  fill="url(#btBenchGradient)"
                  dot={false}
                  activeDot={{ r: 3, fill: "#fdbc2a", strokeWidth: 0 }}
                  connectNulls
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

interface DrawdownTooltipPayload {
  value: number;
  dataKey: string;
}

interface DrawdownTooltipProps {
  active?: boolean;
  payload?: DrawdownTooltipPayload[];
  label?: string;
}

function DrawdownTooltipContent({ active, payload, label }: DrawdownTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const ddEntry = payload.find((p) => p.dataKey === "drawdown");
  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1.5,
        p: 1.5,
        boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
      }}
    >
      <Typography sx={{ fontSize: "0.75rem", color: "text.disabled", mb: 0.5 }}>
        {label}
      </Typography>
      {ddEntry != null && (
        <Typography
          sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.9rem", color: "#ff7134" }}
        >
          回撤: {(ddEntry.value * 100).toFixed(2)}%
        </Typography>
      )}
    </Box>
  );
}

function DrawdownChart({ equityCurve }: { equityCurve: EquityCurvePoint[] }) {
  const ddValues = equityCurve.map((d) => d.drawdown);
  const minDD = ddValues.length > 0 ? Math.min(...ddValues) : -1;
  const domainMin = Math.floor((minDD - 0.01) * 100) / 100;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="📉" title="回撤曲线" />
        <Box sx={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={equityCurve} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <defs>
                <linearGradient id="btDDGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff7134" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ff7134" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.12)" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fontFamily: "monospace", fill: "#888" }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[domainMin, 0]}
                tick={{ fontSize: 11, fontFamily: "monospace", fill: "#888" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                width={52}
              />
              <Tooltip content={<DrawdownTooltipContent />} />
              <Area
                type="monotone"
                dataKey="drawdown"
                name="drawdown"
                stroke="#ff7134"
                strokeWidth={1.5}
                fill="url(#btDDGradient)"
                dot={false}
                activeDot={{ r: 3, fill: "#ff7134", strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

function TradeTable({ trades }: { trades: Trade[] }) {
  if (trades.length === 0) return null;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="🗂" title={`交易明细 (${trades.length} 条)`} />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                {["日期", "代码", "操作", "股数", "价格", "费用"].map((h) => (
                  <TableCell
                    key={h}
                    sx={{
                      color: "text.disabled",
                      fontWeight: 600,
                      fontSize: "0.7rem",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      borderColor: "divider",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {trades.map((t, i) => (
                <TableRow
                  key={`${t.date}-${t.symbol}-${i}`}
                  sx={{
                    "&:hover": { bgcolor: "action.hover" },
                    "& td": { borderColor: "divider" },
                  }}
                >
                  <TableCell
                    sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.secondary" }}
                  >
                    {t.date}
                  </TableCell>
                  <TableCell
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                      color: "primary.main",
                    }}
                  >
                    {t.symbol}
                  </TableCell>
                  <TableCell>
                    <Box
                      sx={{
                        display: "inline-block",
                        px: 1,
                        py: 0.25,
                        borderRadius: 1,
                        fontSize: "0.72rem",
                        fontWeight: 700,
                        fontFamily: "monospace",
                        bgcolor:
                          t.action === "BUY"
                            ? "rgba(54,187,128,0.15)"
                            : "rgba(255,113,52,0.15)",
                        color: t.action === "BUY" ? "#36bb80" : "#ff7134",
                      }}
                    >
                      {t.action === "BUY" ? "买入" : "卖出"}
                    </Box>
                  </TableCell>
                  <TableCell
                    sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.primary" }}
                  >
                    {t.shares.toFixed(2)}
                  </TableCell>
                  <TableCell
                    sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.primary" }}
                  >
                    ${t.price.toFixed(2)}
                  </TableCell>
                  <TableCell
                    sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.secondary" }}
                  >
                    ${t.cost.toFixed(2)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}

export default function BacktestPage() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const [start, setStart] = useState("2024-06-01");
  const [end, setEnd] = useState("2026-03-01");
  const [capital, setCapital] = useState("100000");
  const [bps, setBps] = useState("10");
  const [freq, setFreq] = useState("W-FRI");

  const runBacktest = () => {
    setSubmitted(true);
    setLoading(true);
    setError(null);
    setData(null);

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 300000);

    fetch(
      `${API_BASE}/api/etf-trend/backtest?start=${start}&end=${end}&initial_capital=${capital}&cost_bps=${bps}&rebalance_freq=${encodeURIComponent(freq)}`,
      { signal: controller.signal }
    )
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "回测请求失败");
        }
        return res.json() as Promise<BacktestData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") {
          setError("请求超时（5分钟），请缩短回测时间范围后重试");
          return;
        }
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        setLoading(false);
      });
  };

  const bs = data?.basic_stats ?? {};
  const sharpe = bs["Sharpe"] ?? bs["sharpe"] ?? null;
  const maxDD = bs["Max Drawdown"] ?? bs["max_drawdown"] ?? null;
  const calmar = bs["Calmar"] ?? bs["calmar"] ?? null;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="策略回测"
          description="ETF 趋势策略回测 · 净值曲线 · 回撤分析 · 交易明细"
        />

        <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            px: 4,
            py: 5,
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: "text.primary", mb: 0.5 }}>
              ETF 趋势策略回测
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              设置参数后运行回测，查看完整的净值曲线、回撤与交易记录
            </Typography>
          </Box>

          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent
              sx={{
                display: "flex",
                flexDirection: { xs: "column", sm: "row" },
                alignItems: { sm: "center" },
                gap: 2,
                flexWrap: "wrap",
              }}
            >
              <TextField
                label="开始日期"
                type="date"
                size="small"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ minWidth: 150 }}
              />
              <TextField
                label="结束日期"
                type="date"
                size="small"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ minWidth: 150 }}
              />
              <TextField
                label="初始资金"
                type="number"
                size="small"
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                sx={{ minWidth: 130 }}
                slotProps={{ htmlInput: { min: 1000, step: 1000 } }}
              />
              <TextField
                label="费用 (bps)"
                type="number"
                size="small"
                value={bps}
                onChange={(e) => setBps(e.target.value)}
                sx={{ minWidth: 110 }}
                slotProps={{ htmlInput: { min: 0, step: 1 } }}
              />
              <TextField
                label="调仓频率"
                size="small"
                value={freq}
                onChange={(e) => setFreq(e.target.value)}
                sx={{ minWidth: 120 }}
              />
              <Button
                variant="contained"
                size="medium"
                disabled={loading}
                onClick={runBacktest}
                sx={{
                  bgcolor: "#3b89ff",
                  "&:hover": { bgcolor: "#2a7af0" },
                  px: 3,
                  fontWeight: 700,
                  whiteSpace: "nowrap",
                }}
              >
                {loading ? "运行中..." : "运行回测"}
              </Button>
            </CardContent>
          </Card>

          {!submitted && (
            <Box
              sx={{
                bgcolor: "background.paper",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 3,
                p: 8,
                textAlign: "center",
              }}
            >
              <Typography sx={{ fontSize: "3rem", opacity: 0.2, mb: 3 }}>📊</Typography>
              <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
                设置参数后点击「运行回测」
              </Typography>
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                系统将对 ETF 趋势策略进行历史回测，生成完整的净值曲线与绩效报告
              </Typography>
            </Box>
          )}

          {loading && (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "32vh",
                gap: 2,
              }}
            >
              <CircularProgress size={40} sx={{ color: "#3b89ff" }} />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                回测运行中，请稍候...
              </Typography>
            </Box>
          )}

          {!loading && error && (
            <Alert
              severity="error"
              action={
                <Button color="inherit" size="small" onClick={runBacktest} sx={{ fontWeight: 600 }}>
                  重试
                </Button>
              }
              sx={{ fontFamily: "monospace" }}
            >
              {error}
            </Alert>
          )}

          {!loading && !error && data && (
            <>
              <Card variant="outlined" sx={{ borderRadius: 2 }}>
                <CardContent sx={{ p: 3 }}>
                  <SectionHeader icon="📈" title="回测摘要" />
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: {
                        xs: "1fr 1fr",
                        sm: "1fr 1fr 1fr",
                        md: "repeat(6, 1fr)",
                      },
                      gap: 1.5,
                    }}
                  >
                    <StatBox
                      label="最终净值"
                      value={`$${data.final_nav.toFixed(2)}`}
                      valueColor={returnColor(data.final_nav - data.initial_capital)}
                    />
                    <StatBox
                      label="总收益率"
                      value={`${data.total_return_pct >= 0 ? "+" : ""}${(data.total_return_pct * 100).toFixed(2)}%`}
                      valueColor={returnColor(data.total_return_pct)}
                    />
                    <StatBox label="总交易次数" value={String(data.total_trades)} />
                    <StatBox
                      label="夏普比率"
                      value={fmtNum(sharpe)}
                      valueColor={sharpe != null ? returnColor(sharpe) : undefined}
                    />
                    <StatBox
                      label="最大回撤"
                      value={maxDD != null ? `${(maxDD * 100).toFixed(2)}%` : "—"}
                      valueColor={maxDD != null ? "#ff7134" : undefined}
                    />
                    <StatBox
                      label="Calmar"
                      value={fmtNum(calmar)}
                      valueColor={calmar != null ? returnColor(calmar) : undefined}
                    />
                  </Box>

                  {Object.keys(bs).length > 0 && (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: {
                          xs: "1fr 1fr",
                          sm: "1fr 1fr 1fr",
                          md: "repeat(4, 1fr)",
                        },
                        gap: 1.5,
                        mt: 1.5,
                      }}
                    >
                      {Object.entries(bs)
                        .filter(
                          ([k]) =>
                            !["Sharpe", "sharpe", "Max Drawdown", "max_drawdown", "Calmar", "calmar"].includes(k)
                        )
                        .map(([k, v]) => (
                          <StatBox
                            key={k}
                            label={k}
                            value={
                              v != null
                                ? Math.abs(v) < 10
                                  ? v.toFixed(4)
                                  : v.toFixed(2)
                                : "—"
                            }
                          />
                        ))}
                    </Box>
                  )}
                </CardContent>
              </Card>

              {data.equity_curve.length > 0 && (
                <EquityCurveChart equityCurve={data.equity_curve} />
              )}

              {data.equity_curve.length > 0 && (
                <DrawdownChart equityCurve={data.equity_curve} />
              )}

              {data.extended_metrics && (
                <ExtendedMetricsSection metrics={data.extended_metrics} />
              )}

              {(data.monthly_summary ?? []).length > 0 && (
                <MonthlyChart monthly={data.monthly_summary} />
              )}

              {(data.trades ?? []).length > 0 && <TradeTable trades={data.trades} />}
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
}
