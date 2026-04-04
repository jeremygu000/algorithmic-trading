"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Chip from "@mui/material/Chip";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";
import KlineModal from "@/components/KlineModal";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { ValueType, NameType } from "recharts/types/component/DefaultTooltipContent";

const API_BASE = "http://localhost:8300";

interface BeautyShoulderPattern {
  symbol: string;
  name: string;
  entry_price: number;
  signal_date: string;
  phase1_gain: number;
  pullback_depth: number;
  signal_candle_gain: number;
  confidence: number;
  ema20_at_signal: number;
  phase1_start: string;
  phase1_end: string;
  pullback_low_date: string;
}

interface BeautyShoulderData {
  date: string;
  total_scanned: number;
  matched_count: number;
  patterns: BeautyShoulderPattern[];
}

interface EarlyMoverSignal {
  symbol: string;
  name: string;
  gain_pct: number;
  window_start: string;
  window_end: string;
  start_price: number;
  end_price: number;
}

interface EarlyMoverData {
  date: string;
  total_scanned: number;
  matched_count: number;
  signals: EarlyMoverSignal[];
}

interface ExtendedMetrics {
  [key: string]: number | null;
}

interface MonthlyBacktestStat {
  period: string;
  total_signals: number;
  win_rate_2d: number;
  avg_return_2d: number;
  win_rate_3d: number;
  avg_return_3d: number;
  median_return_2d: number;
  median_return_3d: number;
  max_gain_2d: number;
  max_loss_2d: number;
  max_gain_3d: number;
  max_loss_3d: number;
}

interface BacktestSummary {
  total_signals: number;
  win_rate_2d: number;
  win_rate_3d: number;
  avg_return_2d: number;
  avg_return_3d: number;
  median_return_2d: number;
  median_return_3d: number;
  max_gain_2d: number;
  max_gain_3d: number;
  max_loss_2d: number;
  max_loss_3d: number;
}

interface BacktestTrade {
  symbol: string;
  signal_date: string;
  entry_price: number;
  exit_price_2d: number;
  exit_price_3d: number;
  return_2d: number;
  return_3d: number;
  phase1_gain: number;
  pullback_depth: number;
  confidence: number;
}

interface BacktestData {
  start: string;
  end: string;
  total_trades: number;
  overall: BacktestSummary | null;
  monthly: MonthlyBacktestStat[];
  extended_metrics: ExtendedMetrics | null;
  trades: BacktestTrade[];
}

function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "#36bb80";
  if (confidence >= 0.6) return "#fdbc2a";
  return "#ff7134";
}

function returnColor(value: number): string {
  return value >= 0 ? "#36bb80" : "#ff7134";
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

function LoadingState({ message }: { message: string }) {
  return (
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
      <CircularProgress size={36} />
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {message}
      </Typography>
    </Box>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Box
      sx={{
        bgcolor: "rgba(211,47,47,0.08)",
        border: "1px solid rgba(211,47,47,0.3)",
        borderRadius: 3,
        p: 5,
        textAlign: "center",
      }}
    >
      <Typography variant="h6" sx={{ color: "error.main", mb: 1 }}>
        加载失败
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
        {message}
      </Typography>
      <Button variant="outlined" color="error" size="small" onClick={onRetry}>
        重试
      </Button>
    </Box>
  );
}

function EmptyState({
  icon,
  title,
  subtitle,
}: {
  icon: string;
  title: string;
  subtitle: string;
}) {
  return (
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
      <Typography sx={{ fontSize: "3.5rem", opacity: 0.2, mb: 3 }}>
        {icon}
      </Typography>
      <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
        {title}
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {subtitle}
      </Typography>
    </Box>
  );
}

function SummaryBanner({
  items,
}: {
  items: { label: string; value: string }[];
}) {
  return (
    <Box
      sx={{
        bgcolor: "rgba(54,187,128,0.08)",
        border: "1px solid rgba(54,187,128,0.25)",
        borderRadius: 2,
        px: 3,
        py: 2,
      }}
    >
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
        {items.map(({ label, value }) => (
          <Typography key={label} variant="body2" sx={{ color: "#36bb80" }}>
            {label}:{" "}
            <Box component="b" sx={{ color: "#36bb80" }}>
              {value}
            </Box>
          </Typography>
        ))}
      </Box>
    </Box>
  );
}

const EXTENDED_METRICS_CONFIG: {
  key: string;
  label: string;
  format: (v: number) => string;
  color?: (v: number) => string;
}[] = [
  {
    key: "Sharpe",
    label: "夏普比率",
    format: (v) => v.toFixed(2),
    color: (v) => returnColor(v),
  },
  { key: "Sortino", label: "Sortino", format: (v) => v.toFixed(2), color: (v) => returnColor(v) },
  {
    key: "Max Drawdown",
    label: "最大回撤",
    format: (v) => `${(v * 100).toFixed(2)}%`,
    color: () => "#ff7134",
  },
  { key: "Calmar", label: "Calmar", format: (v) => v.toFixed(2), color: (v) => returnColor(v) },
  {
    key: "Win Rate",
    label: "胜率",
    format: (v) => `${(v * 100).toFixed(1)}%`,
    color: (v) => returnColor(v - 0.5),
  },
  {
    key: "Profit Factor",
    label: "盈亏比",
    format: (v) => v.toFixed(2),
    color: (v) => returnColor(v - 1),
  },
  {
    key: "Max DD Duration (days)",
    label: "最大回撤天数",
    format: (v) => String(Math.round(v)),
  },
  {
    key: "Ann Return",
    label: "年化收益",
    format: (v) => `${(v * 100).toFixed(2)}%`,
    color: (v) => returnColor(v),
  },
  {
    key: "Ann Vol",
    label: "年化波动",
    format: (v) => `${(v * 100).toFixed(2)}%`,
  },
  {
    key: "Tail Ratio (95/5)",
    label: "尾部比率",
    format: (v) => v.toFixed(2),
    color: (v) => returnColor(v - 1),
  },
  {
    key: "Common Sense Ratio",
    label: "常识比率",
    format: (v) => v.toFixed(2),
    color: (v) => returnColor(v - 1),
  },
];

function ExtendedMetricsSection({ metrics }: { metrics: ExtendedMetrics }) {
  const entries = EXTENDED_METRICS_CONFIG.filter(
    (cfg) => metrics[cfg.key] != null
  );

  if (entries.length === 0) return null;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: "text.primary",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontSize: "0.75rem",
          }}
        >
          🔬 扩展绩效指标
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr 1fr",
              sm: "1fr 1fr 1fr",
              md: "repeat(5, 1fr)",
            },
            gap: 1.5,
          }}
        >
          {entries.map((cfg) => {
            const raw = metrics[cfg.key] as number;
            const formatted = cfg.format(raw);
            const color = cfg.color ? cfg.color(raw) : undefined;
            return (
              <StatBox
                key={cfg.key}
                label={cfg.label}
                value={formatted}
                valueColor={color}
              />
            );
          })}
        </Box>
      </CardContent>
    </Card>
  );
}

function MonthlyChart({ monthly }: { monthly: MonthlyBacktestStat[] }) {
  if (monthly.length === 0) return null;

  const chartData = monthly.map((m) => ({
    name: m.period,
    winRate: parseFloat((m.win_rate_2d * 100).toFixed(1)),
    avgReturn: parseFloat((m.avg_return_2d * 100).toFixed(2)),
  }));

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: "text.primary",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontSize: "0.75rem",
          }}
        >
          📊 月度表现图表
        </Typography>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={chartData}
            margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
          >
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
                name === "winRate" ? "2日胜率" : "2日均收益",
              ]}
            />
            <Legend
              formatter={(value: string) =>
                value === "winRate" ? "2日胜率" : "2日均收益"
              }
              wrapperStyle={{ fontSize: "0.8rem" }}
            />
            <Bar yAxisId="left" dataKey="winRate" fill="#3b89ff" radius={[3, 3, 0, 0]} />
            <Bar yAxisId="right" dataKey="avgReturn" radius={[3, 3, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.avgReturn >= 0 ? "#36bb80" : "#ff7134"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function ReturnDistributionChart({ trades }: { trades: BacktestTrade[] }) {
  if (trades.length === 0) return null;

  const buckets = [
    { label: "<-3%", min: -Infinity, max: -0.03, color: "#ff7134" },
    { label: "-3~-1%", min: -0.03, max: -0.01, color: "#ff9966" },
    { label: "-1~0%", min: -0.01, max: 0, color: "#ffbb99" },
    { label: "0~1%", min: 0, max: 0.01, color: "#99ddbb" },
    { label: "1~3%", min: 0.01, max: 0.03, color: "#55cc99" },
    { label: ">3%", min: 0.03, max: Infinity, color: "#36bb80" },
  ];

  const chartData = buckets.map((b) => ({
    label: b.label,
    count: trades.filter((t) => t.return_2d >= b.min && t.return_2d < b.max)
      .length,
    color: b.color,
  }));

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: "text.primary",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontSize: "0.75rem",
          }}
        >
          📉 收益分布
        </Typography>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart
            data={chartData}
            margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.45)" }}
              axisLine={{ stroke: "rgba(255,255,255,0.15)" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "rgba(255,255,255,0.45)" }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1a1a2e",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8,
                fontSize: "0.8rem",
              }}
              formatter={(value: ValueType | undefined) => [value != null ? `${value} 笔` : "—", "交易数"]}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-dist-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function BeautyShoulderTab({ initialData }: { initialData?: BeautyShoulderData | null }) {
  const [data, setData] = useState<BeautyShoulderData | null>(initialData ?? null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [skipInitial] = useState(!!initialData);
  const [modalSymbol, setModalSymbol] = useState<{ symbol: string; name: string } | null>(null);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setTick((n) => n + 1);
  };

  useEffect(() => {
    if (skipInitial && tick === 0) return;

    const controller = new AbortController();

    fetch(`${API_BASE}/api/beauty-shoulder?days=90`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "美人肩扫描请求失败");
        }
        return res.json() as Promise<BeautyShoulderData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [tick, skipInitial]);

  if (loading) return <LoadingState message="扫描中..." />;
  if (error)
    return (
      <ErrorState message={error} onRetry={handleRetry} />
    );
  if (!data) return null;

  const sorted = [...(data.patterns ?? [])].sort(
    (a, b) => b.confidence - a.confidence
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <SummaryBanner
        items={[
          { label: "扫描日期", value: data.date },
          { label: "扫描总数", value: String(data.total_scanned) },
          { label: "命中数量", value: String(data.matched_count) },
        ]}
      />

      {sorted.length > 0 ? (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 3,
          }}
        >
          {sorted.map((p, idx) => (
            <Card
              key={`${p.symbol}-${p.signal_date}-${idx}`}
              variant="outlined"
              onClick={() => setModalSymbol({ symbol: p.symbol, name: p.name })}
              sx={{
                borderRadius: 3,
                cursor: "pointer",
                transition: "border-color 0.2s, box-shadow 0.2s",
                "&:hover": {
                  borderColor: "#36bb80",
                  boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    mb: 2,
                  }}
                >
                  <Box>
                    <Link
                      href={`/stock/${p.symbol}`}
                      style={{ textDecoration: "none" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 700,
                          color: "text.primary",
                          lineHeight: 1.2,
                          "&:hover": { color: "success.main" },
                          transition: "color 0.15s",
                        }}
                      >
                        {p.symbol}
                      </Typography>
                    </Link>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary" }}
                    >
                      {p.name}
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: "right" }}>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.disabled",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        display: "block",
                        mb: 0.25,
                      }}
                    >
                      入场价
                    </Typography>
                    <Typography
                      variant="h6"
                      sx={{
                        fontFamily: "monospace",
                        fontWeight: 600,
                        color: "text.primary",
                      }}
                    >
                      ${p.entry_price.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: 2,
                  }}
                >
                  <Chip
                    label={`信号日期: ${p.signal_date}`}
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.7rem",
                      color: "text.secondary",
                    }}
                  />
                  <Box sx={{ textAlign: "right" }}>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.disabled", display: "block" }}
                    >
                      置信度
                    </Typography>
                    <Typography
                      sx={{
                        fontFamily: "monospace",
                        fontWeight: 700,
                        fontSize: "0.95rem",
                        color: confidenceColor(p.confidence),
                      }}
                    >
                      {(p.confidence * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 1,
                    mb: 2,
                  }}
                >
                  <StatBox
                    label="第一段涨幅"
                    value={`+${p.phase1_gain.toFixed(1)}%`}
                    valueColor="#36bb80"
                  />
                  <StatBox
                    label="回调深度"
                    value={`-${Math.abs(p.pullback_depth).toFixed(1)}%`}
                    valueColor="#ff7134"
                  />
                  <StatBox
                    label="信号K线"
                    value={`${p.signal_candle_gain >= 0 ? "+" : ""}${p.signal_candle_gain.toFixed(2)}%`}
                    valueColor={returnColor(p.signal_candle_gain)}
                  />
                </Box>

                <Box
                  sx={{
                    bgcolor: "action.hover",
                    borderRadius: 1.5,
                    px: 2,
                    py: 1,
                    border: "1px solid",
                    borderColor: "divider",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Typography variant="caption" sx={{ color: "text.disabled" }}>
                    EMA20 参考价
                  </Typography>
                  <Typography
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.85rem",
                      color: "text.secondary",
                    }}
                  >
                    ${p.ema20_at_signal.toFixed(2)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      ) : (
        <EmptyState
          icon="📐"
          title="暂无符合条件的美人肩形态"
          subtitle="过去 90 日内未检测到有效形态，可稍后再试。"
        />
      )}
      <KlineModal
        open={modalSymbol !== null}
        onClose={() => setModalSymbol(null)}
        symbol={modalSymbol?.symbol ?? ""}
        symbolName={modalSymbol?.name}
      />
    </Box>
  );
}

function EarlyMoversTab() {
  const [data, setData] = useState<EarlyMoverData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [modalSymbol, setModalSymbol] = useState<{ symbol: string; name: string } | null>(null);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    setTick((n) => n + 1);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/early-movers?window=20&min_gain=20&max_gain=30`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "早期启动扫描请求失败");
        }
        return res.json() as Promise<EarlyMoverData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [tick]);

  if (loading) return <LoadingState message="扫描早期启动标的中..." />;
  if (error)
    return (
      <ErrorState message={error} onRetry={handleRetry} />
    );
  if (!data) return null;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <SummaryBanner
        items={[
          { label: "扫描日期", value: data.date },
          { label: "扫描总数", value: String(data.total_scanned) },
          { label: "命中数量", value: String(data.matched_count) },
          { label: "筛选窗口", value: "20日 · 涨幅 20%-30%" },
        ]}
      />

      {(data.signals ?? []).length > 0 ? (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 3,
          }}
        >
          {data.signals.map((s, idx) => (
            <Card
              key={`${s.symbol}-${s.window_end}-${idx}`}
              variant="outlined"
              onClick={() => setModalSymbol({ symbol: s.symbol, name: s.name })}
              sx={{
                borderRadius: 3,
                cursor: "pointer",
                transition: "border-color 0.2s, box-shadow 0.2s",
                "&:hover": {
                  borderColor: "#36bb80",
                  boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    mb: 2,
                  }}
                >
                  <Box>
                    <Link
                      href={`/stock/${s.symbol}`}
                      style={{ textDecoration: "none" }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Typography
                        variant="h6"
                        sx={{
                          fontWeight: 700,
                          color: "text.primary",
                          lineHeight: 1.2,
                          "&:hover": { color: "success.main" },
                          transition: "color 0.15s",
                        }}
                      >
                        {s.symbol}
                      </Typography>
                    </Link>
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary" }}
                    >
                      {s.name}
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: "right" }}>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.disabled",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        display: "block",
                        mb: 0.25,
                      }}
                    >
                      区间涨幅
                    </Typography>
                    <Typography
                      variant="h5"
                      sx={{
                        fontFamily: "monospace",
                        fontWeight: 700,
                        color: "#36bb80",
                      }}
                    >
                      +{s.gain_pct.toFixed(1)}%
                    </Typography>
                  </Box>
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mb: 2,
                  }}
                >
                  <Chip
                    label={s.window_start}
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.7rem",
                      color: "text.secondary",
                    }}
                  />
                  <Typography variant="caption" sx={{ color: "text.disabled" }}>
                    →
                  </Typography>
                  <Chip
                    label={s.window_end}
                    size="small"
                    variant="outlined"
                    sx={{
                      fontFamily: "monospace",
                      fontSize: "0.7rem",
                      color: "text.secondary",
                    }}
                  />
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 1,
                  }}
                >
                  <StatBox
                    label="起始价格"
                    value={`$${s.start_price.toFixed(2)}`}
                  />
                  <StatBox
                    label="结束价格"
                    value={`$${s.end_price.toFixed(2)}`}
                    valueColor="#36bb80"
                  />
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      ) : (
        <EmptyState
          icon="🚀"
          title="暂无早期启动标的"
          subtitle="当前窗口内未检测到满足条件的早期启动信号。"
        />
      )}
      <KlineModal
        open={modalSymbol !== null}
        onClose={() => setModalSymbol(null)}
        symbol={modalSymbol?.symbol ?? ""}
        symbolName={modalSymbol?.name}
      />
    </Box>
  );
}

function BacktestTab() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("2025-10-01");
  const [endDate, setEndDate] = useState("2026-02-01");
  const [submitted, setSubmitted] = useState(false);

  const runBacktest = () => {
    setSubmitted(true);
    setLoading(true);
    setError(null);
    setData(null);

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 300000);

    fetch(
      `${API_BASE}/api/beauty-shoulder/backtest?start=${startDate}&end=${endDate}`,
      { signal: controller.signal }
    )
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
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

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
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
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            回测区间
          </Typography>
          <TextField
            label="开始日期"
            type="date"
            size="small"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 160 }}
          />
          <Typography variant="body2" sx={{ color: "text.disabled", px: 0.5 }}>
            →
          </Typography>
          <TextField
            label="结束日期"
            type="date"
            size="small"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            sx={{ minWidth: 160 }}
          />
          <Button
            variant="contained"
            size="small"
            disabled={loading}
            onClick={runBacktest}
            sx={{
              bgcolor: "#3b89ff",
              "&:hover": { bgcolor: "#2a7af0" },
              px: 3,
            }}
          >
            运行回测
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
          <Typography sx={{ fontSize: "3rem", opacity: 0.2, mb: 3 }}>
            📊
          </Typography>
          <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
            设置日期范围后点击「运行回测」
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            系统将对美人肩信号进行历史回测，分析 2日/3日 后的表现。
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
          <CircularProgress size={36} />
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            回测中，扫描全部标的可能需要数分钟...
          </Typography>
        </Box>
      )}

      {!loading && error && (
        <Box
          sx={{
            bgcolor: "rgba(211,47,47,0.08)",
            border: "1px solid rgba(211,47,47,0.3)",
            borderRadius: 3,
            p: 5,
            textAlign: "center",
          }}
        >
          <Typography variant="h6" sx={{ color: "error.main", mb: 1 }}>
            回测失败
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
            {error}
          </Typography>
          <Button
            variant="outlined"
            color="error"
            size="small"
            onClick={runBacktest}
          >
            重试
          </Button>
        </Box>
      )}

      {!loading && !error && data && (
        <>
          {data.overall && (
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 700,
                    mb: 2,
                    color: "text.primary",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    fontSize: "0.75rem",
                  }}
                >
                  📈 综合统计
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr 1fr",
                      sm: "1fr 1fr 1fr",
                      md: "repeat(5, 1fr)",
                    },
                    gap: 1.5,
                  }}
                >
                  <StatBox
                    label="信号总数"
                    value={String(data.overall.total_signals)}
                  />
                  <StatBox
                    label="2日胜率"
                    value={`${(data.overall.win_rate_2d * 100).toFixed(1)}%`}
                    valueColor={returnColor(data.overall.win_rate_2d - 0.5)}
                  />
                  <StatBox
                    label="3日胜率"
                    value={`${(data.overall.win_rate_3d * 100).toFixed(1)}%`}
                    valueColor={returnColor(data.overall.win_rate_3d - 0.5)}
                  />
                  <StatBox
                    label="2日均收益"
                    value={`${data.overall.avg_return_2d >= 0 ? "+" : ""}${(data.overall.avg_return_2d * 100).toFixed(2)}%`}
                    valueColor={returnColor(data.overall.avg_return_2d)}
                  />
                  <StatBox
                    label="3日均收益"
                    value={`${data.overall.avg_return_3d >= 0 ? "+" : ""}${(data.overall.avg_return_3d * 100).toFixed(2)}%`}
                    valueColor={returnColor(data.overall.avg_return_3d)}
                  />
                </Box>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr 1fr",
                      sm: "1fr 1fr 1fr",
                      md: "repeat(6, 1fr)",
                    },
                    gap: 1.5,
                    mt: 1.5,
                  }}
                >
                  <StatBox
                    label="2日中位收益"
                    value={`${data.overall.median_return_2d >= 0 ? "+" : ""}${(data.overall.median_return_2d * 100).toFixed(2)}%`}
                    valueColor={returnColor(data.overall.median_return_2d)}
                  />
                  <StatBox
                    label="3日中位收益"
                    value={`${data.overall.median_return_3d >= 0 ? "+" : ""}${(data.overall.median_return_3d * 100).toFixed(2)}%`}
                    valueColor={returnColor(data.overall.median_return_3d)}
                  />
                  <StatBox
                    label="最大2日涨幅"
                    value={`+${(data.overall.max_gain_2d * 100).toFixed(2)}%`}
                    valueColor="#36bb80"
                  />
                  <StatBox
                    label="最大3日涨幅"
                    value={`+${(data.overall.max_gain_3d * 100).toFixed(2)}%`}
                    valueColor="#36bb80"
                  />
                  <StatBox
                    label="最大2日亏损"
                    value={`${(data.overall.max_loss_2d * 100).toFixed(2)}%`}
                    valueColor="#ff7134"
                  />
                  <StatBox
                    label="最大3日亏损"
                    value={`${(data.overall.max_loss_3d * 100).toFixed(2)}%`}
                    valueColor="#ff7134"
                  />
                </Box>
              </CardContent>
            </Card>
          )}

          {data.extended_metrics && (
            <ExtendedMetricsSection metrics={data.extended_metrics} />
          )}

          {(data.monthly ?? []).length > 0 && (
            <MonthlyChart monthly={data.monthly} />
          )}

          {(data.monthly ?? []).length > 0 && (
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 700,
                    mb: 2,
                    color: "text.primary",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    fontSize: "0.75rem",
                  }}
                >
                  📅 月度统计
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "1fr 1fr",
                      md: "1fr 1fr 1fr",
                    },
                    gap: 2,
                  }}
                >
                  {data.monthly.map((m) => (
                    <Box
                      key={m.period}
                      sx={{
                        bgcolor: "action.hover",
                        borderRadius: 2,
                        p: 2,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "monospace",
                          fontWeight: 700,
                          mb: 1.5,
                          color: "text.primary",
                        }}
                      >
                        {m.period}
                        <Box
                          component="span"
                          sx={{
                            ml: 1,
                            fontSize: "0.7rem",
                            color: "text.disabled",
                            fontWeight: 400,
                          }}
                        >
                          ({m.total_signals} 信号)
                        </Box>
                      </Typography>
                      <Box
                        sx={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 1,
                        }}
                      >
                        <StatBox
                          label="2日胜率"
                          value={`${(m.win_rate_2d * 100).toFixed(1)}%`}
                          valueColor={returnColor(m.win_rate_2d - 0.5)}
                        />
                        <StatBox
                          label="3日胜率"
                          value={`${(m.win_rate_3d * 100).toFixed(1)}%`}
                          valueColor={returnColor(m.win_rate_3d - 0.5)}
                        />
                        <StatBox
                          label="2日均收益"
                          value={`${m.avg_return_2d >= 0 ? "+" : ""}${(m.avg_return_2d * 100).toFixed(2)}%`}
                          valueColor={returnColor(m.avg_return_2d)}
                        />
                        <StatBox
                          label="3日均收益"
                          value={`${m.avg_return_3d >= 0 ? "+" : ""}${(m.avg_return_3d * 100).toFixed(2)}%`}
                          valueColor={returnColor(m.avg_return_3d)}
                        />
                      </Box>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {(data.trades ?? []).length > 0 && (
            <ReturnDistributionChart trades={data.trades} />
          )}

          {(data.trades ?? []).length > 0 && (
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 700,
                    mb: 2,
                    color: "text.primary",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    fontSize: "0.75rem",
                  }}
                >
                  🗂 交易明细 ({data.trades.length} 条)
                </Typography>
                <Box sx={{ overflowX: "auto" }}>
                  <Box
                    component="table"
                    sx={{
                      width: "100%",
                      borderCollapse: "collapse",
                      fontSize: "0.8rem",
                    }}
                  >
                    <Box component="thead">
                      <Box component="tr">
                        {[
                          "代码",
                          "信号日期",
                          "入场价",
                          "2日退出价",
                          "3日退出价",
                          "2日收益",
                          "3日收益",
                          "置信度",
                          "第一段涨幅",
                          "回调深度",
                        ].map((h) => (
                          <Box
                            key={h}
                            component="th"
                            sx={{
                              textAlign: "left",
                              px: 1.5,
                              py: 1,
                              borderBottom: "1px solid",
                              borderColor: "divider",
                              color: "text.disabled",
                              fontWeight: 600,
                              fontSize: "0.7rem",
                              textTransform: "uppercase",
                              letterSpacing: "0.06em",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {h}
                          </Box>
                        ))}
                      </Box>
                    </Box>
                    <Box component="tbody">
                      {data.trades.map((t, i) => (
                        <Box
                          key={`${t.symbol}-${t.signal_date}-${i}`}
                          component="tr"
                          sx={{
                            "&:hover": { bgcolor: "action.hover" },
                            borderBottom: "1px solid",
                            borderColor: "divider",
                          }}
                        >
                          <Box
                            component="td"
                            sx={{ px: 1.5, py: 1, whiteSpace: "nowrap" }}
                          >
                            <Link
                              href={`/stock/${t.symbol}`}
                              style={{ textDecoration: "none" }}
                            >
                              <Typography
                                sx={{
                                  fontWeight: 700,
                                  fontSize: "0.8rem",
                                  color: "primary.main",
                                  "&:hover": { textDecoration: "underline" },
                                }}
                              >
                                {t.symbol}
                              </Typography>
                            </Link>
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              color: "text.secondary",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {t.signal_date}
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              color: "text.primary",
                            }}
                          >
                            ${t.entry_price.toFixed(2)}
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              color: "text.secondary",
                            }}
                          >
                            ${t.exit_price_2d.toFixed(2)}
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              color: "text.secondary",
                            }}
                          >
                            ${t.exit_price_3d.toFixed(2)}
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              fontWeight: 600,
                              color: returnColor(t.return_2d),
                            }}
                          >
                            {t.return_2d >= 0 ? "+" : ""}
                            {(t.return_2d * 100).toFixed(2)}%
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              fontWeight: 600,
                              color: returnColor(t.return_3d),
                            }}
                          >
                            {t.return_3d >= 0 ? "+" : ""}
                            {(t.return_3d * 100).toFixed(2)}%
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              fontWeight: 600,
                              color: confidenceColor(t.confidence),
                            }}
                          >
                            {(t.confidence * 100).toFixed(0)}%
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              fontWeight: 600,
                              color: "#36bb80",
                            }}
                          >
                            +{t.phase1_gain.toFixed(1)}%
                          </Box>
                          <Box
                            component="td"
                            sx={{
                              px: 1.5,
                              py: 1,
                              fontFamily: "monospace",
                              fontWeight: 600,
                              color: "#ff7134",
                            }}
                          >
                            -{Math.abs(t.pullback_depth).toFixed(1)}%
                          </Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
}

export default function BeautyShoulderPage() {
  const [tab, setTab] = useState(0);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialData, setInitialData] = useState<BeautyShoulderData | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/beauty-shoulder?days=90`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error("fetch failed");
        return res.json() as Promise<BeautyShoulderData>;
      })
      .then(setInitialData)
      .catch(() => {})
      .finally(() => setInitialLoading(false));

    return () => controller.abort();
  }, []);

  if (initialLoading) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <CircularProgress size={32} />
            <Typography sx={{ color: "text.secondary" }}>扫描美人肩形态中...</Typography>
          </Box>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}
    >
      <Sidebar />
      <Box
        component="main"
        sx={{ flex: 1, overflowY: "auto", height: "100vh" }}
      >
        <HeroBanner
          title="ETF Trend"
          subtitle="美人肩扫描"
          description="识别第一段上涨 + 正常回调后的二次启动形态，捕捉高确定性入场机会"
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
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <Tabs
              value={tab}
              onChange={(_e, v: number) => setTab(v)}
              sx={{
                px: 2,
                "& .MuiTab-root": {
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  minHeight: 48,
                  textTransform: "none",
                },
                "& .Mui-selected": {
                  color: "#36bb80 !important",
                  fontWeight: 700,
                },
                "& .MuiTabs-indicator": {
                  bgcolor: "#36bb80",
                },
              }}
            >
              <Tab label="美人肩扫描" />
              <Tab label="早期启动" />
              <Tab label="历史回测" />
            </Tabs>
          </Card>

          {tab === 0 && <BeautyShoulderTab initialData={initialData} />}
          {tab === 1 && <EarlyMoversTab />}
          {tab === 2 && <BacktestTab />}
        </Box>
      </Box>
    </Box>
  );
}
