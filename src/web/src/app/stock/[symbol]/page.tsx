"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
  ColorType,
} from "lightweight-charts";
import { useTheme } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";

const GREEN = "#36bb80";
const RED = "#ff7134";
const BLUE = "#3b89ff";
const GOLD = "#fdbc2a";

const CHART_THEMES = {
  light: {
    background: { type: ColorType.Solid, color: "#ffffff" },
    textColor: "#627183",
    grid: { vertLines: { color: "#f0f2f5" }, horzLines: { color: "#f0f2f5" } },
    crosshair: { vertLine: { color: "#c5cdd8" }, horzLine: { color: "#c5cdd8" } },
    borderColor: "#e5e9ef",
    loadingBg: "rgba(255,255,255,0.7)",
  },
  dark: {
    background: { type: ColorType.Solid, color: "#111827" },
    textColor: "#8899aa",
    grid: { vertLines: { color: "#1e2a3a" }, horzLines: { color: "#1e2a3a" } },
    crosshair: { vertLine: { color: "#2d3748" }, horzLine: { color: "#2d3748" } },
    borderColor: "#1e2a3a",
    loadingBg: "rgba(17,24,39,0.7)",
  },
} as const;

const cardSx = {
  borderRadius: 3,
  boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  border: "none",
} as const;

function SectionHeader({
  label,
  accentColor = BLUE,
}: {
  label: string;
  accentColor?: string;
}) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
      <Box
        sx={{
          width: 3,
          height: 16,
          bgcolor: accentColor,
          borderRadius: "2px",
          flexShrink: 0,
        }}
      />
      <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
        {label}
      </Typography>
    </Box>
  );
}

function MetricTile({
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
        borderRadius: 2,
        p: 2,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "text.disabled",
          textTransform: "uppercase",
          display: "block",
          mb: 0.5,
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </Typography>
      <Typography
        variant="body1"
        sx={{
          fontFamily: "var(--font-geist-mono, monospace)",
          fontWeight: 600,
          color: valueColor ?? "text.primary",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function LevelRow({
  label,
  price,
  highlighted,
  highlightColor,
  sublabel,
}: {
  label: string;
  price: number;
  highlighted?: boolean;
  highlightColor?: string;
  sublabel?: string;
}) {
  const bg = highlighted ? `${highlightColor ?? GREEN}14` : "action.hover";
  const border = highlighted ? `1px solid ${highlightColor ?? GREEN}33` : "1px solid";

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        p: 1.5,
        bgcolor: bg,
        borderRadius: 1.5,
        border,
        borderColor: highlighted ? undefined : "divider",
      }}
    >
      <Box>
        <Typography
          variant="body2"
          sx={{
            color: highlighted ? `${highlightColor ?? GREEN}cc` : "text.secondary",
            fontWeight: highlighted ? 500 : 400,
          }}
        >
          {label}
        </Typography>
        {sublabel && (
          <Typography
            variant="caption"
            sx={{ color: highlighted ? `${highlightColor ?? GREEN}80` : "text.disabled" }}
          >
            {sublabel}
          </Typography>
        )}
      </Box>
      <Typography
        variant="body2"
        sx={{
          fontFamily: "var(--font-geist-mono, monospace)",
          fontWeight: 700,
          color: highlighted ? (highlightColor ?? GREEN) : "text.primary",
        }}
      >
        ${price.toFixed(2)}
      </Typography>
    </Box>
  );
}

interface OHLCVBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface StockData {
  symbol: string;
  name: string;
  date: string;
  current_price: number;
  recommendation: string;
  reason: string;
  technicals: {
    ma20: number;
    ma50: number;
    ma200: number;
    momentum_60d: number;
    volatility: number;
    atr: number;
    rsi?: number;
    macd?: number;
    macd_signal?: number;
    macd_hist?: number;
    bb_upper?: number;
    bb_lower?: number;
  };
  entry_levels: {
    aggressive: number;
    aggressive_label: string;
    moderate: number;
    moderate_label: string;
    conservative: number;
    conservative_label: string;
  };
  stop_levels: {
    tight: number;
    tight_label: string;
    normal: number;
    normal_label: string;
    loose: number;
    loose_label: string;
  };
  tp_levels: {
    tp1: number;
    tp1_label: string;
    tp2: number;
    tp2_label: string;
    tp3: number;
    tp3_label: string;
  };
  market_regime: string;
  fundamentals?: {
    peRatio: number | null;
    pegRatio: number | null;
    pbRatio: number | null;
    trailingEPS: number | null;
    marketCap: number | null;
    sector: string | null;
  };
  ai_analysis?: {
    pattern_match: {
      similar_patterns_count: number;
      avg_return: number;
      win_rate: number;
      confidence_score: number;
      projection: string;
    };
    trend_prediction: {
      current_price: number;
      target_price_5d: number;
      predicted_change_pct: number;
      slope: number;
      r_squared: number;
      description: string;
    };
  };
  ohlcv: OHLCVBar[];
}

function CandlestickChartInline({
  ohlcv,
  chartLoading,
}: {
  ohlcv: OHLCVBar[];
  chartLoading: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const volumeContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const volumeChartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const muiTheme = useTheme();
  const mode: "light" | "dark" = muiTheme.palette.mode === "dark" ? "dark" : "light";

  useEffect(() => {
    if (!containerRef.current || !volumeContainerRef.current) return;

    const theme = CHART_THEMES[mode];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 340,
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: false },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: GREEN,
      downColor: RED,
      borderUpColor: GREEN,
      borderDownColor: RED,
      wickUpColor: "#2a9264",
      wickDownColor: "#d95620",
    });
    candleRef.current = candleSeries;

    const volumeChart = createChart(volumeContainerRef.current, {
      width: volumeContainerRef.current.clientWidth,
      height: 80,
      layout: theme,
      grid: theme.grid,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor, timeVisible: false },
    });
    volumeChartRef.current = volumeChart;

    const volumeSeries = volumeChart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeRef.current = volumeSeries;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
      if (volumeContainerRef.current) {
        volumeChart.applyOptions({ width: volumeContainerRef.current.clientWidth });
      }
    });
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      volumeChart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const theme = CHART_THEMES[mode];
    chartRef.current?.applyOptions({
      layout: theme,
      grid: theme.grid,
      crosshair: theme.crosshair,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor },
    });
    volumeChartRef.current?.applyOptions({
      layout: theme,
      grid: theme.grid,
      rightPriceScale: { borderColor: theme.borderColor },
      timeScale: { borderColor: theme.borderColor },
    });
  }, [mode]);

  useEffect(() => {
    if (!candleRef.current || !volumeRef.current || ohlcv.length === 0) return;

    const seen = new Set<number>();
    const candles: { time: UTCTimestamp; open: number; high: number; low: number; close: number }[] =
      [];
    const volumes: { time: UTCTimestamp; value: number; color: string }[] = [];

    for (const b of ohlcv) {
      const t = (new Date(b.date).getTime() / 1000) as UTCTimestamp;
      if (!seen.has(t)) {
        seen.add(t);
        candles.push({ time: t, open: b.open, high: b.high, low: b.low, close: b.close });
        volumes.push({
          time: t,
          value: b.volume,
          color: b.close >= b.open ? "rgba(54,187,128,0.4)" : "rgba(255,113,52,0.4)",
        });
      }
    }

    candles.sort((a, b) => (a.time as number) - (b.time as number));
    volumes.sort((a, b) => (a.time as number) - (b.time as number));

    candleRef.current.setData(candles);
    volumeRef.current.setData(volumes);
    chartRef.current?.timeScale().fitContent();
    volumeChartRef.current?.timeScale().fitContent();
  }, [ohlcv]);

  const theme = CHART_THEMES[mode];

  return (
    <>
      <Box
        sx={{
          position: "relative",
          borderRadius: "8px",
          overflow: "hidden",
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        {chartLoading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: theme.loadingBg,
              zIndex: 10,
            }}
          >
            <CircularProgress size={28} />
          </Box>
        )}
        <div ref={containerRef} style={{ width: "100%" }} />
      </Box>

      <Box
        sx={{
          position: "relative",
          mt: 1,
          borderRadius: "8px",
          overflow: "hidden",
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="caption"
          sx={{
            position: "absolute",
            top: 6,
            left: 10,
            color: "text.disabled",
            fontSize: "0.65rem",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            zIndex: 5,
          }}
        >
          Volume
        </Typography>
        <div ref={volumeContainerRef} style={{ width: "100%" }} />
      </Box>
    </>
  );
}

function LoadingSkeleton({ symbol }: { symbol: string }) {
  return (
    <>
      <HeroBanner
        title="ETF Trend"
        subtitle="股票分析"
        description={`${symbol} 深度技术面分析与交易计划`}
      />
      <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5 }}>
        <Box sx={{ mb: 5, pb: 4, borderBottom: "1px solid", borderColor: "divider" }}>
          <Skeleton variant="rounded" height={48} width="40%" sx={{ borderRadius: 2, mb: 1 }} />
          <Skeleton variant="rounded" height={20} width="25%" sx={{ borderRadius: 2 }} />
        </Box>
        <Skeleton variant="rounded" height={64} sx={{ borderRadius: 3, mb: 4 }} />
        <Skeleton variant="rounded" height={420} sx={{ borderRadius: 3, mb: 4 }} />
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" }, gap: 4 }}>
          <Skeleton variant="rounded" height={240} sx={{ borderRadius: 3 }} />
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <Skeleton variant="rounded" height={140} sx={{ borderRadius: 3 }} />
            <Skeleton variant="rounded" height={140} sx={{ borderRadius: 3 }} />
            <Skeleton variant="rounded" height={140} sx={{ borderRadius: 3 }} />
          </Box>
        </Box>
      </Box>
    </>
  );
}

const recommendationChipSx: Record<string, object> = {
  强烈推荐: {
    bgcolor: "rgba(54,187,128,0.1)",
    color: GREEN,
    border: `1px solid rgba(54,187,128,0.25)`,
  },
  推荐: {
    bgcolor: "rgba(59,137,255,0.1)",
    color: BLUE,
    border: `1px solid rgba(59,137,255,0.25)`,
  },
  观望: {
    bgcolor: "rgba(100,116,139,0.15)",
    color: "#94a3b8",
    border: "1px solid rgba(100,116,139,0.3)",
  },
};

export default function StockPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase();

  const [data, setData] = useState<StockData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    const controller = new AbortController();

    fetch(`${API_BASE}/api/stock/${symbol}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`股票 ${symbol} 未找到`);
        return res.json();
      })
      .then((json: StockData) => {
        setData(json);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "请求失败");
      })
      .finally(() => {
        setLoading(false);
      });

    return () => controller.abort();
  }, [symbol]);

  if (loading) return <LoadingSkeleton symbol={symbol} />;

  if (error) {
    return (
      <Box sx={{ maxWidth: 800, mx: "auto", px: 4, py: 12 }}>
        <Box
          sx={{
            bgcolor: "rgba(159,18,57,0.12)",
            border: "1px solid rgba(159,18,57,0.25)",
            borderRadius: 3,
            p: 6,
            textAlign: "center",
          }}
        >
          <Typography variant="h6" sx={{ color: "error.light", mb: 1, fontWeight: 600 }}>
            查询失败
          </Typography>
          <Typography sx={{ color: "text.secondary", mb: 4 }}>{error}</Typography>
          <Button
            component={Link}
            href="/"
            variant="outlined"
            sx={{
              borderColor: "divider",
              color: "text.primary",
              "&:hover": { bgcolor: "action.hover" },
            }}
          >
            返回首页
          </Button>
        </Box>
      </Box>
    );
  }

  if (!data) return null;

  const chipSx = recommendationChipSx[data.recommendation] ?? recommendationChipSx["观望"];

  return (
    <>
      <HeroBanner
        title="ETF Trend"
        subtitle="股票分析"
        description={`${symbol} 深度技术面分析与交易计划`}
      />

      <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5 }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              alignItems: { md: "flex-end" },
              justifyContent: "space-between",
              mb: 5,
              gap: 3,
              borderBottom: "1px solid",
              borderColor: "divider",
              pb: 4,
            }}
          >
            <Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 0.5 }}>
                <Typography
                  variant="h2"
                  sx={{ fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1 }}
                >
                  {data.symbol}
                </Typography>
                <Chip
                  label={data.recommendation}
                  size="small"
                  sx={{
                    borderRadius: "999px",
                    fontWeight: 500,
                    fontSize: "0.8rem",
                    height: 28,
                    ...chipSx,
                  }}
                />
              </Box>
              <Typography variant="body1" sx={{ color: "text.secondary" }}>
                {data.name}
              </Typography>
            </Box>

            <Box sx={{ textAlign: { md: "right" } }}>
              <Typography
                variant="caption"
                sx={{
                  color: "text.disabled",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  display: "block",
                  mb: 0.5,
                }}
              >
                当前价格
              </Typography>
              <Typography
                variant="h3"
                sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
              >
                ${data.current_price.toFixed(2)}
              </Typography>
            </Box>
          </Box>

          <Card sx={{ ...cardSx, mb: 4 }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                <Box
                  sx={{
                    width: 3,
                    minHeight: 16,
                    bgcolor: GOLD,
                    borderRadius: "2px",
                    flexShrink: 0,
                    alignSelf: "stretch",
                  }}
                />
                <Box>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.disabled",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      display: "block",
                      mb: 0.75,
                    }}
                  >
                    分析结论
                  </Typography>
                  <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.8 }}>
                    {data.reason}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {data.fundamentals?.peRatio && (
            <Card sx={{ ...cardSx, mb: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr 1fr" },
                    gap: 3,
                  }}
                >
                  <Box
                    sx={{
                      gridColumn: "1 / -1",
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      mb: 1,
                    }}
                  >
                    <Box sx={{ width: 3, height: 16, bgcolor: BLUE, borderRadius: "2px" }} />
                    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                      基本面概览
                    </Typography>
                    {data.fundamentals.sector && (
                      <Chip
                        label={data.fundamentals.sector}
                        size="small"
                        sx={{ fontSize: "0.7rem", height: 22 }}
                      />
                    )}
                  </Box>

                  <MetricTile
                    label="市盈率 (PE)"
                    value={
                      data.fundamentals.peRatio
                        ? `${data.fundamentals.peRatio.toFixed(1)}x`
                        : "N/A"
                    }
                  />
                  <MetricTile
                    label="PEG Ratio"
                    value={data.fundamentals.pegRatio?.toFixed(2) ?? "N/A"}
                    valueColor={
                      data.fundamentals.pegRatio !== null &&
                      data.fundamentals.pegRatio !== undefined &&
                      data.fundamentals.pegRatio > 0 &&
                      data.fundamentals.pegRatio < 1
                        ? GREEN
                        : undefined
                    }
                  />
                  <MetricTile
                    label="EPS (TTM)"
                    value={
                      data.fundamentals.trailingEPS !== null &&
                      data.fundamentals.trailingEPS !== undefined
                        ? `$${data.fundamentals.trailingEPS.toFixed(2)}`
                        : "N/A"
                    }
                  />
                  <MetricTile
                    label="市值"
                    value={
                      data.fundamentals.marketCap
                        ? `$${(data.fundamentals.marketCap / 1e9).toFixed(1)}B`
                        : "N/A"
                    }
                  />
                </Box>
              </CardContent>
            </Card>
          )}

          {data.ai_analysis && (
            <Card sx={{ ...cardSx, mb: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 3 }}>
                  <SectionHeader label="AI 智能预测" accentColor={GOLD} />
                  <Chip
                    label="实验性"
                    size="small"
                    sx={{
                      fontSize: "0.625rem",
                      height: 20,
                      bgcolor: `${GOLD}18`,
                      color: GOLD,
                      border: `1px solid ${GOLD}40`,
                      mt: -0.5,
                    }}
                  />
                </Box>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                    gap: 3,
                  }}
                >
                  <Box
                    sx={{
                      bgcolor: "action.hover",
                      borderRadius: 2,
                      p: 2.5,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                      <Box
                        sx={{ width: 3, height: 16, bgcolor: BLUE, borderRadius: "2px" }}
                      />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        历史形态匹配 (Pattern Matching)
                      </Typography>
                    </Box>

                    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          相似历史片段
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                        >
                          {data.ai_analysis.pattern_match.similar_patterns_count} 组
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          历史胜率
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "var(--font-geist-mono, monospace)",
                            fontWeight: 700,
                            color:
                              data.ai_analysis.pattern_match.win_rate >= 0.6
                                ? GREEN
                                : "text.primary",
                          }}
                        >
                          {(data.ai_analysis.pattern_match.win_rate * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          平均期望收益 (20d)
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "var(--font-geist-mono, monospace)",
                            fontWeight: 700,
                            color: data.ai_analysis.pattern_match.avg_return > 0 ? GREEN : RED,
                          }}
                        >
                          {(data.ai_analysis.pattern_match.avg_return * 100).toFixed(1)}%
                        </Typography>
                      </Box>
                      <Box sx={{ pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                        <Typography
                          variant="caption"
                          sx={{ color: "text.disabled", fontStyle: "italic" }}
                        >
                          &ldquo;{data.ai_analysis.pattern_match.projection}&rdquo;
                        </Typography>
                      </Box>
                    </Box>
                  </Box>

                  <Box
                    sx={{
                      bgcolor: "action.hover",
                      borderRadius: 2,
                      p: 2.5,
                      border: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                      <Box
                        sx={{ width: 3, height: 16, bgcolor: GOLD, borderRadius: "2px" }}
                      />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        趋势线性回归 (Linear Trend)
                      </Typography>
                    </Box>

                    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          当前价格
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                        >
                          ${data.ai_analysis.trend_prediction.current_price.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          5日理论目标
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "var(--font-geist-mono, monospace)",
                            fontWeight: 700,
                            color: GOLD,
                          }}
                        >
                          ${data.ai_analysis.trend_prediction.target_price_5d.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          拟合优度 (R²)
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                        >
                          {data.ai_analysis.trend_prediction.r_squared.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box sx={{ pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
                        <Typography
                          variant="caption"
                          sx={{ color: "text.disabled", fontStyle: "italic" }}
                        >
                          &ldquo;{data.ai_analysis.trend_prediction.description}&rdquo;
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}

          <Card sx={{ ...cardSx, mb: 4 }}>
            <CardContent sx={{ p: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 3,
                }}
              >
                <SectionHeader label="K 线走势" accentColor={BLUE} />
                <Box sx={{ display: "flex", gap: 3 }}>
                  {[
                    { color: GREEN, label: "入场" },
                    { color: RED, label: "止损" },
                    { color: BLUE, label: "止盈" },
                  ].map(({ color, label }) => (
                    <Box
                      key={label}
                      sx={{ display: "flex", alignItems: "center", gap: 0.75 }}
                    >
                      <Box
                        sx={{ width: 12, height: 2, bgcolor: color, borderRadius: "1px" }}
                      />
                      <Typography
                        variant="caption"
                        sx={{
                          color: "text.secondary",
                          fontFamily: "var(--font-geist-mono, monospace)",
                        }}
                      >
                        {label}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
              <CandlestickChartInline ohlcv={data.ohlcv ?? []} chartLoading={false} />
            </CardContent>
          </Card>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" },
              gap: 4,
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <Card sx={cardSx}>
                <CardContent sx={{ p: 3 }}>
                  <SectionHeader label="技术指标详情" accentColor={BLUE} />
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr" },
                      gap: 2,
                    }}
                  >
                    <MetricTile
                      label="MA20 (短期趋势)"
                      value={`$${data.technicals.ma20.toFixed(2)}`}
                    />
                    <MetricTile
                      label="MA50 (中期趋势)"
                      value={`$${data.technicals.ma50.toFixed(2)}`}
                    />
                    <MetricTile
                      label="MA200 (长期趋势)"
                      value={`$${data.technicals.ma200.toFixed(2)}`}
                    />
                    <MetricTile
                      label="60日动量"
                      value={`${data.technicals.momentum_60d.toFixed(1)}%`}
                      valueColor={data.technicals.momentum_60d > 0 ? GREEN : RED}
                    />
                    <MetricTile
                      label="年化波动率"
                      value={`${data.technicals.volatility.toFixed(1)}%`}
                    />
                    <MetricTile
                      label="ATR (波动幅度)"
                      value={`$${data.technicals.atr.toFixed(2)}`}
                    />

                    {data.technicals.rsi !== undefined && (
                      <MetricTile
                        label="RSI (14)"
                        value={data.technicals.rsi.toFixed(1)}
                        valueColor={
                          data.technicals.rsi > 70
                            ? RED
                            : data.technicals.rsi < 30
                            ? GREEN
                            : undefined
                        }
                      />
                    )}

                    {data.technicals.macd_hist !== undefined && (
                      <MetricTile
                        label="MACD Hist"
                        value={data.technicals.macd_hist.toFixed(2)}
                        valueColor={data.technicals.macd_hist > 0 ? GREEN : RED}
                      />
                    )}

                    {data.technicals.bb_upper !== undefined &&
                      data.technicals.bb_lower !== undefined && (
                        <MetricTile
                          label="Bollinger (Width)"
                          value={`${(
                            ((data.technicals.bb_upper - data.technicals.bb_lower) /
                              data.current_price) *
                            100
                          ).toFixed(1)}%`}
                        />
                      )}
                  </Box>
                </CardContent>
              </Card>
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <Card sx={cardSx}>
                <CardContent sx={{ p: 3 }}>
                  <SectionHeader label="入场计划 (Entry)" accentColor={GREEN} />
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <LevelRow
                      label={data.entry_levels.aggressive_label}
                      price={data.entry_levels.aggressive}
                    />
                    <LevelRow
                      label={data.entry_levels.moderate_label}
                      price={data.entry_levels.moderate}
                      highlighted
                      highlightColor={GREEN}
                      sublabel="推荐挂单价位"
                    />
                    <LevelRow
                      label={data.entry_levels.conservative_label}
                      price={data.entry_levels.conservative}
                    />
                  </Box>
                </CardContent>
              </Card>

              <Card sx={cardSx}>
                <CardContent sx={{ p: 3 }}>
                  <SectionHeader label="风控止损 (Stop Loss)" accentColor={RED} />
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <LevelRow
                      label={data.stop_levels.tight_label}
                      price={data.stop_levels.tight}
                    />
                    <LevelRow
                      label={data.stop_levels.normal_label}
                      price={data.stop_levels.normal}
                      highlighted
                      highlightColor={RED}
                    />
                    <LevelRow
                      label={data.stop_levels.loose_label}
                      price={data.stop_levels.loose}
                    />
                  </Box>
                </CardContent>
              </Card>

              <Card sx={cardSx}>
                <CardContent sx={{ p: 3 }}>
                  <SectionHeader label="获利目标 (Take Profit)" accentColor={BLUE} />
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <LevelRow
                      label={data.tp_levels.tp1_label}
                      price={data.tp_levels.tp1}
                      highlighted
                      highlightColor={BLUE}
                    />
                    <LevelRow
                      label={data.tp_levels.tp2_label}
                      price={data.tp_levels.tp2}
                    />
                    <LevelRow
                      label={data.tp_levels.tp3_label}
                      price={data.tp_levels.tp3}
                    />
                  </Box>
                </CardContent>
              </Card>
          </Box>
        </Box>
      </Box>
    </>
  );
}
