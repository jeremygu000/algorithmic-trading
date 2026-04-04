"use client";

import { useState, useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
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
} from "recharts";

const API_BASE = "http://localhost:8300";

// ── colors ──

const PRESET_COLORS = ["#3b89ff", "#36bb80", "#ff7134", "#fdbc2a", "#c678dd", "#56b6c2"];

// ── types ──

interface EquityCurvePoint {
  date: string;
  nav: number;
  drawdown: number;
  benchmark_nav: number | null;
}

interface ExtendedMetrics {
  [key: string]: number | null;
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
}

interface PresetConfig {
  id: string;
  label: string;
  capital: string;
  bps: string;
  freq: string;
  color: string;
}

interface PresetResult {
  id: string;
  data: BacktestData | null;
  loading: boolean;
  error: string | null;
}

// ── helpers ──

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(decimals);
}

function fmtPct(v: number | null | undefined, decimals = 2): string {
  if (v == null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(decimals)}%`;
}

function returnColor(v: number): string {
  return v >= 0 ? "#36bb80" : "#ff7134";
}

let presetCounter = 0;
function nextPresetId(): string {
  presetCounter += 1;
  return `preset-${presetCounter}`;
}

// ── shared ui ──

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

// ── default presets ──

function makeDefaultPresets(): PresetConfig[] {
  return [
    {
      id: nextPresetId(),
      label: "保守型",
      capital: "100000",
      bps: "10",
      freq: "M",
      color: PRESET_COLORS[0],
    },
    {
      id: nextPresetId(),
      label: "均衡型",
      capital: "100000",
      bps: "10",
      freq: "W-FRI",
      color: PRESET_COLORS[1],
    },
    {
      id: nextPresetId(),
      label: "激进型",
      capital: "100000",
      bps: "5",
      freq: "W-FRI",
      color: PRESET_COLORS[2],
    },
  ];
}

// ── equity curve tooltip ──

interface CompareTooltipPayload {
  value: number;
  dataKey: string;
  color: string;
  name: string;
}

interface CompareTooltipProps {
  active?: boolean;
  payload?: CompareTooltipPayload[];
  label?: string;
}

function CompareEquityTooltip({ active, payload, label }: CompareTooltipProps) {
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
      {payload.map((entry) => (
        <Typography
          key={entry.dataKey}
          sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.8rem", color: entry.color }}
        >
          {entry.name}: {entry.value?.toFixed(4) ?? "—"}
        </Typography>
      ))}
    </Box>
  );
}

function CompareDrawdownTooltip({ active, payload, label }: CompareTooltipProps) {
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
      {payload.map((entry) => (
        <Typography
          key={entry.dataKey}
          sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "0.8rem", color: entry.color }}
        >
          {entry.name}: {entry.value != null ? `${(entry.value * 100).toFixed(2)}%` : "—"}
        </Typography>
      ))}
    </Box>
  );
}

// ── overlaid equity curve chart ──

function OverlaidEquityChart({
  presets,
  results,
}: {
  presets: PresetConfig[];
  results: PresetResult[];
}) {
  const loaded = results.filter((r) => r.data && r.data.equity_curve.length > 0);
  if (loaded.length === 0) return null;

  const allDates = new Set<string>();
  for (const r of loaded) {
    for (const pt of r.data!.equity_curve) {
      allDates.add(pt.date);
    }
  }
  const sortedDates = Array.from(allDates).sort();

  const chartData = sortedDates.map((date) => {
    const row: Record<string, string | number | null> = { date };
    for (const r of loaded) {
      const pt = r.data!.equity_curve.find((p) => p.date === date);
      row[`nav_${r.id}`] = pt?.nav ?? null;
    }
    if (loaded[0]?.data?.equity_curve.some((p) => p.benchmark_nav != null)) {
      const bp = loaded[0].data!.equity_curve.find((p) => p.date === date);
      row["benchmark"] = bp?.benchmark_nav ?? null;
    }
    return row;
  });

  const allNavs: number[] = [];
  for (const r of loaded) {
    for (const pt of r.data!.equity_curve) {
      allNavs.push(pt.nav);
      if (pt.benchmark_nav != null) allNavs.push(pt.benchmark_nav);
    }
  }
  const minVal = allNavs.length > 0 ? Math.min(...allNavs) : 0;
  const maxVal = allNavs.length > 0 ? Math.max(...allNavs) : 2;
  const padding = (maxVal - minVal) * 0.05;
  const domainMin = Math.floor((minVal - padding) * 1000) / 1000;
  const domainMax = Math.ceil((maxVal + padding) * 1000) / 1000;
  const hasBenchmark = chartData.some((d) => d["benchmark"] != null);

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="📈" title="净值曲线对比" />
        <Box sx={{ height: 360 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <defs>
                {loaded.map((r) => {
                  const preset = presets.find((p) => p.id === r.id);
                  const clr = preset?.color ?? "#888";
                  return (
                    <linearGradient key={`grad-${r.id}`} id={`grad-${r.id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={clr} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={clr} stopOpacity={0.02} />
                    </linearGradient>
                  );
                })}
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
              <Tooltip content={<CompareEquityTooltip />} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              {loaded.map((r) => {
                const preset = presets.find((p) => p.id === r.id);
                const clr = preset?.color ?? "#888";
                return (
                  <Area
                    key={r.id}
                    type="monotone"
                    dataKey={`nav_${r.id}`}
                    name={preset?.label ?? r.id}
                    stroke={clr}
                    strokeWidth={2}
                    fill={`url(#grad-${r.id})`}
                    dot={false}
                    activeDot={{ r: 4, fill: clr, strokeWidth: 0 }}
                    connectNulls
                  />
                );
              })}
              {hasBenchmark && (
                <Area
                  type="monotone"
                  dataKey="benchmark"
                  name="SPY"
                  stroke="#888"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  fill="none"
                  dot={false}
                  activeDot={{ r: 3, fill: "#888", strokeWidth: 0 }}
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

// ── overlaid drawdown chart ──

function OverlaidDrawdownChart({
  presets,
  results,
}: {
  presets: PresetConfig[];
  results: PresetResult[];
}) {
  const loaded = results.filter((r) => r.data && r.data.equity_curve.length > 0);
  if (loaded.length === 0) return null;

  const allDates = new Set<string>();
  for (const r of loaded) {
    for (const pt of r.data!.equity_curve) {
      allDates.add(pt.date);
    }
  }
  const sortedDates = Array.from(allDates).sort();

  const chartData = sortedDates.map((date) => {
    const row: Record<string, string | number | null> = { date };
    for (const r of loaded) {
      const pt = r.data!.equity_curve.find((p) => p.date === date);
      row[`dd_${r.id}`] = pt?.drawdown ?? null;
    }
    return row;
  });

  const allDD: number[] = [];
  for (const r of loaded) {
    for (const pt of r.data!.equity_curve) {
      allDD.push(pt.drawdown);
    }
  }
  const minDD = allDD.length > 0 ? Math.min(...allDD) : -1;
  const domainMin = Math.floor((minDD - 0.01) * 100) / 100;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="📉" title="回撤对比" />
        <Box sx={{ height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
              <defs>
                {loaded.map((r) => {
                  const preset = presets.find((p) => p.id === r.id);
                  const clr = preset?.color ?? "#888";
                  return (
                    <linearGradient key={`ddgrad-${r.id}`} id={`ddgrad-${r.id}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={clr} stopOpacity={0.25} />
                      <stop offset="95%" stopColor={clr} stopOpacity={0.05} />
                    </linearGradient>
                  );
                })}
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
              <Tooltip content={<CompareDrawdownTooltip />} />
              <Legend wrapperStyle={{ fontSize: "0.75rem" }} />
              {loaded.map((r) => {
                const preset = presets.find((p) => p.id === r.id);
                const clr = preset?.color ?? "#888";
                return (
                  <Area
                    key={r.id}
                    type="monotone"
                    dataKey={`dd_${r.id}`}
                    name={preset?.label ?? r.id}
                    stroke={clr}
                    strokeWidth={1.5}
                    fill={`url(#ddgrad-${r.id})`}
                    dot={false}
                    activeDot={{ r: 3, fill: clr, strokeWidth: 0 }}
                    connectNulls
                  />
                );
              })}
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
}

// ── metrics comparison table ──

const COMPARE_METRICS: {
  key: string;
  label: string;
  getValue: (d: BacktestData) => number | null;
  format: (v: number) => string;
  color?: (v: number) => string;
  higherIsBetter?: boolean;
}[] = [
  {
    key: "total_return",
    label: "总收益率",
    getValue: (d) => d.total_return_pct,
    format: (v) => `${(v * 100).toFixed(2)}%`,
    color: returnColor,
    higherIsBetter: true,
  },
  {
    key: "final_nav",
    label: "最终净值",
    getValue: (d) => d.final_nav,
    format: (v) => `$${v.toFixed(2)}`,
    higherIsBetter: true,
  },
  {
    key: "total_trades",
    label: "交易次数",
    getValue: (d) => d.total_trades,
    format: (v) => String(Math.round(v)),
  },
  {
    key: "sharpe",
    label: "夏普比率",
    getValue: (d) => d.extended_metrics?.["Sharpe"] ?? d.basic_stats?.["Sharpe"] ?? null,
    format: (v) => v.toFixed(2),
    color: returnColor,
    higherIsBetter: true,
  },
  {
    key: "sortino",
    label: "Sortino",
    getValue: (d) => d.extended_metrics?.["Sortino"] ?? null,
    format: (v) => v.toFixed(2),
    color: returnColor,
    higherIsBetter: true,
  },
  {
    key: "max_dd",
    label: "最大回撤",
    getValue: (d) => d.extended_metrics?.["Max Drawdown"] ?? d.basic_stats?.["Max Drawdown"] ?? null,
    format: (v) => `${(v * 100).toFixed(2)}%`,
    color: () => "#ff7134",
    higherIsBetter: false,
  },
  {
    key: "calmar",
    label: "Calmar",
    getValue: (d) => d.extended_metrics?.["Calmar"] ?? d.basic_stats?.["Calmar"] ?? null,
    format: (v) => v.toFixed(2),
    color: returnColor,
    higherIsBetter: true,
  },
  {
    key: "win_rate",
    label: "胜率",
    getValue: (d) => d.extended_metrics?.["Win Rate"] ?? null,
    format: (v) => `${(v * 100).toFixed(1)}%`,
    color: (v) => returnColor(v - 0.5),
    higherIsBetter: true,
  },
  {
    key: "profit_factor",
    label: "盈亏比",
    getValue: (d) => d.extended_metrics?.["Profit Factor"] ?? null,
    format: (v) => v.toFixed(2),
    color: (v) => returnColor(v - 1),
    higherIsBetter: true,
  },
  {
    key: "ann_return",
    label: "年化收益",
    getValue: (d) => d.extended_metrics?.["Ann Return"] ?? null,
    format: (v) => `${(v * 100).toFixed(2)}%`,
    color: returnColor,
    higherIsBetter: true,
  },
  {
    key: "ann_vol",
    label: "年化波动",
    getValue: (d) => d.extended_metrics?.["Ann Vol"] ?? null,
    format: (v) => `${(v * 100).toFixed(2)}%`,
    higherIsBetter: false,
  },
  {
    key: "dd_duration",
    label: "最大回撤天数",
    getValue: (d) => d.extended_metrics?.["Max DD Duration (days)"] ?? null,
    format: (v) => String(Math.round(v)),
    higherIsBetter: false,
  },
];

function MetricsCompareTable({
  presets,
  results,
}: {
  presets: PresetConfig[];
  results: PresetResult[];
}) {
  const loaded = results.filter((r) => r.data != null);
  if (loaded.length === 0) return null;

  function bestIdx(values: (number | null)[], higherIsBetter?: boolean): number {
    let bestI = -1;
    let bestV: number | null = null;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (v == null) continue;
      if (bestV == null) {
        bestV = v;
        bestI = i;
      } else if (higherIsBetter && v > bestV) {
        bestV = v;
        bestI = i;
      } else if (!higherIsBetter && v < bestV) {
        bestV = v;
        bestI = i;
      }
    }
    return bestI;
  }

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <SectionHeader icon="🔬" title="指标对比" />
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell
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
                  指标
                </TableCell>
                {loaded.map((r) => {
                  const preset = presets.find((p) => p.id === r.id);
                  return (
                    <TableCell
                      key={r.id}
                      align="right"
                      sx={{
                        fontWeight: 600,
                        fontSize: "0.7rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        borderColor: "divider",
                        whiteSpace: "nowrap",
                        color: preset?.color ?? "text.disabled",
                      }}
                    >
                      {preset?.label ?? r.id}
                    </TableCell>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {COMPARE_METRICS.map((metric) => {
                const values = loaded.map((r) => metric.getValue(r.data!));
                const best = metric.higherIsBetter != null ? bestIdx(values, metric.higherIsBetter) : -1;
                return (
                  <TableRow
                    key={metric.key}
                    sx={{ "&:hover": { bgcolor: "action.hover" }, "& td": { borderColor: "divider" } }}
                  >
                    <TableCell
                      sx={{
                        fontSize: "0.8rem",
                        fontWeight: 500,
                        color: "text.secondary",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {metric.label}
                    </TableCell>
                    {values.map((v, i) => {
                      const formatted = v != null ? metric.format(v) : "—";
                      const clr = v != null && metric.color ? metric.color(v) : undefined;
                      const isBest = i === best;
                      return (
                        <TableCell
                          key={loaded[i].id}
                          align="right"
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.8rem",
                            fontWeight: isBest ? 700 : 400,
                            color: clr ?? "text.primary",
                            position: "relative",
                          }}
                        >
                          {formatted}
                          {isBest && loaded.length > 1 && (
                            <Box
                              component="span"
                              sx={{
                                ml: 0.75,
                                fontSize: "0.6rem",
                                color: "#fdbc2a",
                                verticalAlign: "super",
                              }}
                            >
                              ★
                            </Box>
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
}

// ======= main page =======

export default function ComparePage() {
  const [presets, setPresets] = useState<PresetConfig[]>(makeDefaultPresets);
  const [results, setResults] = useState<PresetResult[]>([]);
  const [start, setStart] = useState("2024-06-01");
  const [end, setEnd] = useState("2026-03-01");
  const [running, setRunning] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const updatePreset = (id: string, field: keyof PresetConfig, value: string) => {
    setPresets((prev) => prev.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  const addPreset = () => {
    if (presets.length >= 6) return;
    const colorIdx = presets.length % PRESET_COLORS.length;
    setPresets((prev) => [
      ...prev,
      {
        id: nextPresetId(),
        label: `方案${prev.length + 1}`,
        capital: "100000",
        bps: "10",
        freq: "W-FRI",
        color: PRESET_COLORS[colorIdx],
      },
    ]);
  };

  const removePreset = (id: string) => {
    if (presets.length <= 1) return;
    setPresets((prev) => prev.filter((p) => p.id !== id));
    setResults((prev) => prev.filter((r) => r.id !== id));
  };

  const runComparison = useCallback(() => {
    setRunning(true);
    setGlobalError(null);

    const initial: PresetResult[] = presets.map((p) => ({
      id: p.id,
      data: null,
      loading: true,
      error: null,
    }));
    setResults(initial);

    const promises = presets.map((preset) => {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 300000);

      return fetch(
        `${API_BASE}/api/etf-trend/backtest?start=${start}&end=${end}&initial_capital=${preset.capital}&cost_bps=${preset.bps}&rebalance_freq=${encodeURIComponent(preset.freq)}`,
        { signal: controller.signal }
      )
        .then(async (res) => {
          if (!res.ok) {
            const body = (await res.json().catch(() => null)) as { detail?: string } | null;
            throw new Error(body?.detail || "回测请求失败");
          }
          return res.json() as Promise<BacktestData>;
        })
        .then((data) => {
          setResults((prev) =>
            prev.map((r) => (r.id === preset.id ? { ...r, data, loading: false } : r))
          );
        })
        .catch((e: unknown) => {
          const msg =
            e instanceof Error && e.name === "AbortError"
              ? "请求超时"
              : e instanceof Error
                ? e.message
                : "未知错误";
          setResults((prev) =>
            prev.map((r) => (r.id === preset.id ? { ...r, error: msg, loading: false } : r))
          );
        })
        .finally(() => {
          window.clearTimeout(timeoutId);
        });
    });

    Promise.allSettled(promises).then(() => setRunning(false));
  }, [presets, start, end]);

  const anyLoading = results.some((r) => r.loading);
  const hasResults = results.some((r) => r.data != null);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="策略对比"
          subtitle="Multi-Strategy Compare"
          description="ETF 趋势策略参数对比 · 净值叠加 · 回撤分析 · 指标横评"
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
          {/* ── header ── */}
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: "text.primary", mb: 0.5 }}>
              ETF 趋势策略对比
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              配置不同参数方案，同时回测并横向对比净值曲线与绩效指标
            </Typography>
          </Box>

          {/* ── shared date range ── */}
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: "text.secondary", mr: 1 }}>
                回测区间
              </Typography>
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
            </CardContent>
          </Card>

          {/* ── preset configs ── */}
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
                <SectionHeader icon="⚙️" title="参数方案" />
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={addPreset}
                  disabled={presets.length >= 6}
                  sx={{ fontSize: "0.75rem", textTransform: "none" }}
                >
                  添加方案
                </Button>
              </Box>

              <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {presets.map((preset) => {
                  const result = results.find((r) => r.id === preset.id);
                  return (
                    <Box
                      key={preset.id}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                        p: 1.5,
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                        bgcolor: "action.hover",
                        flexWrap: "wrap",
                      }}
                    >
                      <Chip
                        size="small"
                        sx={{
                          bgcolor: preset.color,
                          color: "#fff",
                          fontWeight: 700,
                          fontSize: "0.7rem",
                          minWidth: 12,
                          "& .MuiChip-label": { px: 0.75 },
                        }}
                        label="●"
                      />
                      <TextField
                        size="small"
                        value={preset.label}
                        onChange={(e) => updatePreset(preset.id, "label", e.target.value)}
                        sx={{ width: 100 }}
                        slotProps={{ input: { sx: { fontSize: "0.8rem" } } }}
                      />
                      <TextField
                        label="资金"
                        type="number"
                        size="small"
                        value={preset.capital}
                        onChange={(e) => updatePreset(preset.id, "capital", e.target.value)}
                        sx={{ width: 110 }}
                        slotProps={{ htmlInput: { min: 1000, step: 1000 }, input: { sx: { fontSize: "0.8rem" } } }}
                      />
                      <TextField
                        label="费用(bps)"
                        type="number"
                        size="small"
                        value={preset.bps}
                        onChange={(e) => updatePreset(preset.id, "bps", e.target.value)}
                        sx={{ width: 100 }}
                        slotProps={{ htmlInput: { min: 0, step: 1 }, input: { sx: { fontSize: "0.8rem" } } }}
                      />
                      <TextField
                        label="调仓频率"
                        size="small"
                        value={preset.freq}
                        onChange={(e) => updatePreset(preset.id, "freq", e.target.value)}
                        sx={{ width: 110 }}
                        slotProps={{ input: { sx: { fontSize: "0.8rem" } } }}
                      />
                      {result?.loading && <CircularProgress size={18} sx={{ color: preset.color }} />}
                      {result?.error && (
                        <Typography sx={{ fontSize: "0.7rem", color: "#ff7134" }}>
                          {result.error}
                        </Typography>
                      )}
                      {result?.data && (
                        <Typography sx={{ fontSize: "0.7rem", color: "#36bb80", fontFamily: "monospace" }}>
                          {fmtPct(result.data.total_return_pct)}
                        </Typography>
                      )}
                      <Box sx={{ flex: 1 }} />
                      <IconButton
                        size="small"
                        onClick={() => removePreset(preset.id)}
                        disabled={presets.length <= 1}
                        sx={{ color: "text.disabled" }}
                      >
                        <DeleteOutlineIcon sx={{ fontSize: "1rem" }} />
                      </IconButton>
                    </Box>
                  );
                })}
              </Box>

              <Box sx={{ mt: 2, display: "flex", justifyContent: "center" }}>
                <Button
                  variant="contained"
                  size="medium"
                  disabled={anyLoading || presets.length === 0}
                  onClick={runComparison}
                  sx={{
                    bgcolor: "#3b89ff",
                    "&:hover": { bgcolor: "#2a7af0" },
                    px: 4,
                    fontWeight: 700,
                    whiteSpace: "nowrap",
                  }}
                >
                  {anyLoading ? "运行中..." : "运行对比"}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {globalError && <Alert severity="error" sx={{ fontFamily: "monospace" }}>{globalError}</Alert>}

          {/* ── loading state ── */}
          {running && !hasResults && (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: "20vh",
                gap: 2,
              }}
            >
              <CircularProgress size={40} sx={{ color: "#3b89ff" }} />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                并行回测中，请稍候...
              </Typography>
            </Box>
          )}

          {/* ── summary cards ── */}
          {hasResults && (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: `repeat(${Math.min(results.filter((r) => r.data).length, 3)}, 1fr)` },
                gap: 2,
              }}
            >
              {results
                .filter((r) => r.data != null)
                .map((r) => {
                  const preset = presets.find((p) => p.id === r.id);
                  const d = r.data!;
                  const sharpe = d.extended_metrics?.["Sharpe"] ?? d.basic_stats?.["Sharpe"] ?? null;
                  const maxDD = d.extended_metrics?.["Max Drawdown"] ?? d.basic_stats?.["Max Drawdown"] ?? null;
                  return (
                    <Card
                      key={r.id}
                      variant="outlined"
                      sx={{
                        borderRadius: 2,
                        borderTop: `3px solid ${preset?.color ?? "#888"}`,
                      }}
                    >
                      <CardContent sx={{ p: 2.5 }}>
                        <Typography
                          sx={{
                            fontWeight: 700,
                            fontSize: "0.85rem",
                            color: preset?.color ?? "text.primary",
                            mb: 1.5,
                          }}
                        >
                          {preset?.label ?? r.id}
                        </Typography>
                        <Box
                          sx={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: 1,
                          }}
                        >
                          <StatBox
                            label="总收益"
                            value={`${d.total_return_pct >= 0 ? "+" : ""}${fmtPct(d.total_return_pct)}`}
                            valueColor={returnColor(d.total_return_pct)}
                          />
                          <StatBox
                            label="夏普"
                            value={fmtNum(sharpe)}
                            valueColor={sharpe != null ? returnColor(sharpe) : undefined}
                          />
                          <StatBox
                            label="最大回撤"
                            value={maxDD != null ? fmtPct(maxDD) : "—"}
                            valueColor="#ff7134"
                          />
                          <StatBox label="交易次数" value={String(d.total_trades)} />
                        </Box>
                      </CardContent>
                    </Card>
                  );
                })}
            </Box>
          )}

          {/* ── charts ── */}
          {hasResults && <OverlaidEquityChart presets={presets} results={results} />}
          {hasResults && <OverlaidDrawdownChart presets={presets} results={results} />}

          {/* ── metrics table ── */}
          {hasResults && <MetricsCompareTable presets={presets} results={results} />}

          {/* ── empty state ── */}
          {!running && !hasResults && (
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
              <Typography sx={{ fontSize: "3rem", opacity: 0.2, mb: 3 }}>⚖️</Typography>
              <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
                配置参数方案后点击「运行对比」
              </Typography>
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                系统将并行运行多组回测，生成叠加净值曲线与横向指标对比
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
