"use client";

import { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import type { PieLabelRenderProps } from "recharts";

const API_BASE = "http://localhost:8300";

const DONUT_COLORS = [
  "#3b89ff",
  "#36bb80",
  "#ff7134",
  "#fdbc2a",
  "#a855f7",
  "#06b6d4",
  "#ec4899",
  "#84cc16",
  "#f97316",
  "#14b8a6",
];

interface AccountData {
  equity: number;
  cash: number;
  portfolio_value: number;
  buying_power: number;
}

interface AllocationItem {
  name: string;
  value: number;
  weight: number;
}

interface RiskMetrics {
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  max_drawdown_duration: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  win_rate: number | null;
  total_unrealized_pl: number;
  total_unrealized_plpc: number;
}

interface EquityCurvePoint {
  date: string;
  nav: number;
}

interface PortfolioAnalytics {
  account: AccountData;
  allocation: AllocationItem[];
  risk_metrics: RiskMetrics;
  equity_curve: EquityCurvePoint[];
}

function fmtMoney(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function fmtPct(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(decimals)}%`;
}

function fmtNum(value: number | null | undefined, decimals = 2): string {
  if (value == null || isNaN(value)) return "—";
  return value.toFixed(decimals);
}

function plColor(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return "text.primary";
  return value >= 0 ? "#36bb80" : "#ff7134";
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
      }}
    >
      {icon} {title}
    </Typography>
  );
}

function StatCard({
  label,
  value,
  valueColor,
  large,
}: {
  label: string;
  value: string;
  valueColor?: string;
  large?: boolean;
}) {
  return (
    <Box
      sx={{
        bgcolor: "action.hover",
        borderRadius: 1.5,
        p: large ? 2 : 1.5,
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
          fontSize: large ? "1.1rem" : "0.9rem",
          color: valueColor ?? "text.primary",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function AccountOverview({ account, risk }: { account: AccountData; risk: RiskMetrics }) {
  const unrealizedPl = risk.total_unrealized_pl;
  const unrealizedPlpc = risk.total_unrealized_plpc;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2.5 }}>
          <SectionHeader icon="💼" title="账户总览" />
        </Box>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "1fr 1fr 1fr 1fr" },
            gap: 1.5,
          }}
        >
          <StatCard label="总资产" value={fmtMoney(account.equity)} large />
          <StatCard label="持仓市值" value={fmtMoney(account.portfolio_value)} large />
          <StatCard label="现金" value={fmtMoney(account.cash)} large />
          <StatCard
            label="未实现盈亏"
            value={`${unrealizedPl >= 0 ? "+" : ""}${fmtMoney(unrealizedPl)} (${fmtPct(unrealizedPlpc)})`}
            large
            valueColor={plColor(unrealizedPl)}
          />
        </Box>
      </CardContent>
    </Card>
  );
}

interface CustomTooltipPayload {
  name: string;
  value: number;
  payload: AllocationItem;
}

interface PieTooltipProps {
  active?: boolean;
  payload?: CustomTooltipPayload[];
}

function PieTooltipContent({ active, payload }: PieTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
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
      <Typography sx={{ fontWeight: 700, fontSize: "0.85rem", color: "text.primary", mb: 0.5 }}>
        {item.name}
      </Typography>
      <Typography sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.secondary" }}>
        市值: {fmtMoney(item.value)}
      </Typography>
      <Typography sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.secondary" }}>
        占比: {(item.payload.weight * 100).toFixed(1)}%
      </Typography>
    </Box>
  );
}

interface AreaTooltipPayload {
  value: number;
  dataKey: string;
}

interface AreaTooltipProps {
  active?: boolean;
  payload?: AreaTooltipPayload[];
  label?: string;
}

function AreaTooltipContent({ active, payload, label }: AreaTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
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
      <Typography sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.9rem", color: "#3b89ff" }}>
        NAV: {fmtMoney(payload[0].value)}
      </Typography>
    </Box>
  );
}

function AllocationChart({ allocation }: { allocation: AllocationItem[] }) {
  if (allocation.length === 0) {
    return (
      <Card variant="outlined" sx={{ borderRadius: 2 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ mb: 2.5 }}>
            <SectionHeader icon="🥧" title="持仓分布" />
          </Box>
          <Box
            sx={{
              bgcolor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
            }}
          >
            <Typography sx={{ fontSize: "2.5rem", opacity: 0.2, mb: 2 }}>📭</Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              暂无持仓数据
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const renderLabel = (props: PieLabelRenderProps) => {
    const cx = props.cx as number;
    const cy = props.cy as number;
    const midAngle = props.midAngle as number;
    const innerRadius = props.innerRadius as number;
    const outerRadius = props.outerRadius as number;
    const name = props.name as string;
    const payload = props.payload as AllocationItem | undefined;
    const weight = payload?.weight ?? 0;

    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 1.4;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    if (weight < 3) return null;
    return (
      <text
        x={x}
        y={y}
        fill="#888"
        textAnchor={x > cx ? "start" : "end"}
        dominantBaseline="central"
        style={{ fontSize: "11px", fontFamily: "monospace" }}
      >
        {name} {weight.toFixed(1)}%
      </text>
    );
  };

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2.5 }}>
          <SectionHeader icon="🥧" title="持仓分布" />
        </Box>
        <Box sx={{ height: 340 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={allocation}
                cx="50%"
                cy="50%"
                innerRadius="45%"
                outerRadius="68%"
                paddingAngle={2}
                dataKey="value"
                labelLine={false}
                label={renderLabel}
              >
                {allocation.map((entry, index) => (
                  <Cell
                    key={`cell-${entry.name}`}
                    fill={DONUT_COLORS[index % DONUT_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<PieTooltipContent />} />
              <Legend
                formatter={(value) => (
                  <span style={{ fontSize: "0.75rem", color: "inherit" }}>{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

function EquityCurve({ equityCurve }: { equityCurve: EquityCurvePoint[] }) {
  const minNav = equityCurve.length > 0 ? Math.min(...equityCurve.map((d) => d.nav)) : 0;
  const maxNav = equityCurve.length > 0 ? Math.max(...equityCurve.map((d) => d.nav)) : 0;
  const padding = (maxNav - minNav) * 0.05;
  const domainMin = Math.floor((minNav - padding) * 100) / 100;
  const domainMax = Math.ceil((maxNav + padding) * 100) / 100;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2.5 }}>
          <SectionHeader icon="📈" title="净值曲线" />
        </Box>
        {equityCurve.length === 0 ? (
          <Box
            sx={{
              bgcolor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
            }}
          >
            <Typography sx={{ fontSize: "2.5rem", opacity: 0.2, mb: 2 }}>📉</Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              暂无净值历史数据
            </Typography>
          </Box>
        ) : (
          <Box sx={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityCurve} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
                <defs>
                  <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b89ff" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3b89ff" stopOpacity={0.02} />
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
                  tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                  width={72}
                />
                <Tooltip content={<AreaTooltipContent />} />
                <Area
                  type="monotone"
                  dataKey="nav"
                  stroke="#3b89ff"
                  strokeWidth={2}
                  fill="url(#navGradient)"
                  dot={false}
                  activeDot={{ r: 4, fill: "#3b89ff", strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function RiskMetricsSection({ risk }: { risk: RiskMetrics }) {
  const metrics = [
    {
      label: "Sharpe比率",
      value: risk.sharpe_ratio != null ? fmtNum(risk.sharpe_ratio, 3) : "—",
      valueColor: risk.sharpe_ratio != null ? plColor(risk.sharpe_ratio) : undefined,
    },
    {
      label: "Sortino比率",
      value: risk.sortino_ratio != null ? fmtNum(risk.sortino_ratio, 3) : "—",
      valueColor: risk.sortino_ratio != null ? plColor(risk.sortino_ratio) : undefined,
    },
    {
      label: "年化收益率",
      value: risk.annualized_return != null ? fmtPct(risk.annualized_return) : "—",
      valueColor: risk.annualized_return != null ? plColor(risk.annualized_return) : undefined,
    },
    {
      label: "年化波动率",
      value:
        risk.annualized_volatility != null
          ? `${(risk.annualized_volatility * 100).toFixed(2)}%`
          : "—",
      valueColor: undefined,
    },
    {
      label: "最大回撤",
      value: risk.max_drawdown != null ? fmtPct(risk.max_drawdown) : "—",
      valueColor: risk.max_drawdown != null ? (risk.max_drawdown <= 0 ? "#ff7134" : "#36bb80") : undefined,
    },
    {
      label: "胜率",
      value: risk.win_rate != null ? `${(risk.win_rate * 100).toFixed(1)}%` : "—",
      valueColor: risk.win_rate != null ? plColor(risk.win_rate - 0.5) : undefined,
    },
  ];

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2.5 }}>
          <SectionHeader icon="⚖️" title="风险指标" />
        </Box>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "1fr 1fr 1fr" },
            gap: 1.5,
          }}
        >
          {metrics.map((m) => (
            <StatCard
              key={m.label}
              label={m.label}
              value={m.value}
              valueColor={m.valueColor}
            />
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}

export default function PortfolioPage() {
  const [data, setData] = useState<PortfolioAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    setTick((t) => t + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/portfolio/analytics?days=90`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "Portfolio analytics 请求失败");
        }
        return res.json() as Promise<PortfolioAnalytics>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [tick]);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="投资组合分析"
          description="账户总览 · 持仓分布 · 净值曲线 · 风险指标"
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
          {loading && (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "40vh",
                gap: 2,
              }}
            >
              <CircularProgress size={40} />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                加载投资组合数据中...
              </Typography>
            </Box>
          )}

          {!loading && error && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Alert
                severity="error"
                action={
                  <Button
                    color="inherit"
                    size="small"
                    onClick={reload}
                    sx={{ fontWeight: 600 }}
                  >
                    重试
                  </Button>
                }
                sx={{ fontFamily: "monospace" }}
              >
                {error}
              </Alert>
            </Box>
          )}

          {!loading && !error && data && (
            <>
              <AccountOverview account={data.account} risk={data.risk_metrics} />

              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                  gap: 4,
                }}
              >
                <AllocationChart allocation={data.allocation} />
                <EquityCurve equityCurve={data.equity_curve} />
              </Box>

              <RiskMetricsSection risk={data.risk_metrics} />
            </>
          )}
        </Box>
      </Box>
    </Box>
  );
}
