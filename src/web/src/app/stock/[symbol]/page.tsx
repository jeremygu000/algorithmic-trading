"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";

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
  chart_base64: string;
}

export default function StockPage() {
  const params = useParams();
  const symbol = (params.symbol as string)?.toUpperCase();

  const [data, setData] = useState<StockData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;

    let cancelled = false;

    fetch(`${API_BASE}/api/stock/${symbol}`)
      .then((res) => {
        if (!res.ok) throw new Error(`股票 ${symbol} 未找到`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const recommendationChipSx: Record<string, object> = {
    强烈推荐: {
      bgcolor: "rgba(16,185,129,0.1)",
      color: "#34d399",
      border: "1px solid rgba(16,185,129,0.2)",
    },
    推荐: {
      bgcolor: "rgba(14,165,233,0.1)",
      color: "#38bdf8",
      border: "1px solid rgba(14,165,233,0.2)",
    },
    观望: {
      bgcolor: "rgba(100,116,139,0.15)",
      color: "#94a3b8",
      border: "1px solid rgba(100,116,139,0.3)",
    },
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box
          component="main"
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100vh",
          }}
        >
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
            <CircularProgress size={32} sx={{ color: "primary.main" }} />
            <Typography sx={{ color: "text.secondary" }}>
              正在分析 {symbol} 数据...
            </Typography>
          </Box>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Box sx={{ maxWidth: 800, mx: "auto", px: 4, py: 12 }}>
            <Box
              sx={{
                bgcolor: "rgba(159,18,57,0.15)",
                border: "1px solid rgba(159,18,57,0.3)",
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
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="股票分析"
          description={`${symbol} 深度技术面分析与交易计划`}
        />
        <Box sx={{ maxWidth: 1200, mx: "auto", px: 4, py: 5 }}>

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
                  {data?.symbol}
                </Typography>
                <Chip
                  label={data?.recommendation}
                  size="small"
                  sx={{
                    borderRadius: "999px",
                    fontWeight: 500,
                    fontSize: "0.8rem",
                    height: 28,
                    ...(recommendationChipSx[data?.recommendation ?? "观望"] ?? recommendationChipSx["观望"]),
                  }}
                />
              </Box>
              <Typography variant="body1" sx={{ color: "text.secondary" }}>
                {data?.name}
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
                ${data?.current_price.toFixed(2)}
              </Typography>
            </Box>
          </Box>

          <Box
            sx={{
              bgcolor: "action.hover",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              p: 2.5,
              mb: 4,
              display: "flex",
              gap: 1.5,
              alignItems: "flex-start",
            }}
          >
            <Typography component="span" sx={{ fontSize: "1.2rem", lineHeight: 1.6 }}>
              💡
            </Typography>
            <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.75 }}>
              <Typography
                component="span"
                variant="body2"
                sx={{ color: "text.disabled", fontWeight: 500 }}
              >
                分析结论：
              </Typography>{" "}
              {data?.reason}
            </Typography>
          </Box>

          {data?.fundamentals?.peRatio && (
            <Card
              variant="outlined"
              sx={{ mb: 4, borderRadius: 3 }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr 1fr" },
                    gap: 3,
                  }}
                >
                  <Box sx={{ gridColumn: { xs: "1 / -1" }, display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <Typography component="span" sx={{ fontSize: "1.2rem" }}>🏢</Typography>
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
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5 }}>
                      市盈率 (PE)
                    </Typography>
                    <Typography
                      variant="body1"
                      sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                    >
                      {data.fundamentals.peRatio?.toFixed(1) || "N/A"}
                      <Typography component="span" variant="caption" sx={{ color: "text.disabled", ml: 0.5 }}>
                        x
                      </Typography>
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5 }}>
                      PEG Ratio
                    </Typography>
                    <Typography
                      variant="body1"
                      sx={{
                        fontFamily: "var(--font-geist-mono, monospace)",
                        fontWeight: 600,
                        color:
                          (data.fundamentals.pegRatio || 0) < 1 &&
                          (data.fundamentals.pegRatio || 0) > 0
                            ? "success.main"
                            : "text.primary",
                      }}
                    >
                      {data.fundamentals.pegRatio?.toFixed(2) || "N/A"}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5 }}>
                      EPS (TTM)
                    </Typography>
                    <Typography
                      variant="body1"
                      sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                    >
                      ${data.fundamentals.trailingEPS?.toFixed(2) || "N/A"}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" sx={{ color: "text.disabled", display: "block", mb: 0.5 }}>
                      市值
                    </Typography>
                    <Typography
                      variant="body1"
                      sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                    >
                      {data.fundamentals.marketCap
                        ? `$${(data.fundamentals.marketCap / 1e9).toFixed(1)}B`
                        : "N/A"}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}

          {data?.ai_analysis && (
            <Box
              sx={{
                background: "linear-gradient(135deg, rgba(49,46,129,0.25) 0%, rgba(88,28,135,0.25) 100%)",
                border: "1px solid rgba(99,102,241,0.2)",
                borderRadius: 3,
                p: 3,
                mb: 4,
                position: "relative",
                overflow: "hidden",
                boxShadow: "0 4px 32px rgba(99,102,241,0.06)",
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  top: 0,
                  right: 0,
                  width: 128,
                  height: 128,
                  bgcolor: "rgba(99,102,241,0.1)",
                  borderRadius: "50%",
                  filter: "blur(48px)",
                  mr: -8,
                  mt: -8,
                  pointerEvents: "none",
                }}
              />

              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
                <Typography component="span" sx={{ fontSize: "1.2rem" }}>🤖</Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "#c7d2fe" }}>
                  AI 智能预测 (实验性)
                </Typography>
                <Chip
                  label="Alpha"
                  size="small"
                  sx={{
                    fontSize: "0.625rem",
                    height: 20,
                    bgcolor: "rgba(99,102,241,0.2)",
                    color: "#a5b4fc",
                    border: "1px solid rgba(99,102,241,0.3)",
                  }}
                />
              </Box>

              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
                <Box
                  sx={{
                    bgcolor: "rgba(15,23,42,0.6)",
                    borderRadius: 2,
                    p: 2.5,
                    border: "1px solid rgba(99,102,241,0.1)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                    <Box sx={{ width: 3, height: 16, bgcolor: "#818cf8", borderRadius: "2px" }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      历史形态匹配 (Pattern Matching)
                    </Typography>
                  </Box>

                  <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>相似历史片段</Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                      >
                        {data.ai_analysis.pattern_match.similar_patterns_count} 组
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>历史胜率</Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color:
                            data.ai_analysis.pattern_match.win_rate >= 0.6
                              ? "success.main"
                              : "text.primary",
                        }}
                      >
                        {(data.ai_analysis.pattern_match.win_rate * 100).toFixed(0)}%
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>平均期望收益 (20d)</Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color:
                            data.ai_analysis.pattern_match.avg_return > 0
                              ? "success.main"
                              : "error.main",
                        }}
                      >
                        {(data.ai_analysis.pattern_match.avg_return * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        pt: 1.5,
                        borderTop: "1px solid rgba(99,102,241,0.1)",
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "rgba(165,180,252,0.8)", fontStyle: "italic" }}
                      >
                        &ldquo;{data.ai_analysis.pattern_match.projection}&rdquo;
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                <Box
                  sx={{
                    bgcolor: "rgba(15,23,42,0.6)",
                    borderRadius: 2,
                    p: 2.5,
                    border: "1px solid rgba(99,102,241,0.1)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                    <Box sx={{ width: 3, height: 16, bgcolor: "#c084fc", borderRadius: "2px" }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      趋势线性回归 (Linear Trend)
                    </Typography>
                  </Box>

                  <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>当前价格</Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                      >
                        ${data.ai_analysis.trend_prediction.current_price.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>5日理论目标</Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color: "#d8b4fe",
                        }}
                      >
                        ${data.ai_analysis.trend_prediction.target_price_5d.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>拟合优度 (R²)</Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)" }}
                      >
                        {data.ai_analysis.trend_prediction.r_squared.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        pt: 1.5,
                        borderTop: "1px solid rgba(168,85,247,0.1)",
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "rgba(216,180,254,0.8)", fontStyle: "italic" }}
                      >
                        &ldquo;{data.ai_analysis.trend_prediction.description}&rdquo;
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </Box>
          )}

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" },
              gap: 4,
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data?.chart_base64 && (
                <Card variant="outlined" sx={{ borderRadius: 3 }}>
                  <CardContent sx={{ p: 3 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        mb: 3,
                      }}
                    >
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        📊 技术分析图表
                      </Typography>
                      <Box sx={{ display: "flex", gap: 3 }}>
                        {[
                          { color: "#22c55e", label: "入场" },
                          { color: "#ef4444", label: "止损" },
                          { color: "#3b82f6", label: "止盈" },
                        ].map(({ color, label }) => (
                          <Box
                            key={label}
                            sx={{ display: "flex", alignItems: "center", gap: 0.75 }}
                          >
                            <Box
                              sx={{
                                width: 12,
                                height: 2,
                                bgcolor: color,
                                borderRadius: "1px",
                              }}
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
                    {/* eslint-disable-next-line @next/next/no-img-element -- base64 data URL, next/image not applicable */}
                    <img
                      src={`data:image/png;base64,${data.chart_base64}`}
                      alt={`${data.symbol} 蜡烛图`}
                      style={{ width: "100%", borderRadius: "8px" }}
                    />
                  </CardContent>
                </Card>
              )}

              <Card variant="outlined" sx={{ borderRadius: 3 }}>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>
                    📉 技术指标详情
                  </Typography>
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: { xs: "1fr 1fr", md: "1fr 1fr 1fr" },
                      gap: 2,
                    }}
                  >
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        MA20 (短期趋势)
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                      >
                        ${data?.technicals.ma20.toFixed(2)}
                      </Typography>
                    </Box>
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        MA50 (中期趋势)
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                      >
                        ${data?.technicals.ma50.toFixed(2)}
                      </Typography>
                    </Box>
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        MA200 (长期趋势)
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                      >
                        ${data?.technicals.ma200.toFixed(2)}
                      </Typography>
                    </Box>
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        60日动量
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 600,
                          color:
                            data?.technicals.momentum_60d && data.technicals.momentum_60d > 0
                              ? "success.main"
                              : "error.main",
                        }}
                      >
                        {data?.technicals.momentum_60d.toFixed(1)}%
                      </Typography>
                    </Box>
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        年化波动率
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                      >
                        {data?.technicals.volatility.toFixed(1)}%
                      </Typography>
                    </Box>
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
                        sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                      >
                        ATR (波动幅度)
                      </Typography>
                      <Typography
                        variant="body1"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                      >
                        ${data?.technicals.atr.toFixed(2)}
                      </Typography>
                    </Box>

                    {data?.technicals.rsi !== undefined && (
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
                          sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                        >
                          RSI (14)
                        </Typography>
                        <Typography
                          variant="body1"
                          sx={{
                            fontFamily: "var(--font-geist-mono, monospace)",
                            fontWeight: 600,
                            color:
                              data.technicals.rsi > 70
                                ? "error.main"
                                : data.technicals.rsi < 30
                                ? "success.main"
                                : "text.primary",
                          }}
                        >
                          {data.technicals.rsi.toFixed(1)}
                        </Typography>
                      </Box>
                    )}

                    {data?.technicals.macd_hist !== undefined && (
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
                          sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                        >
                          MACD Hist
                        </Typography>
                        <Typography
                          variant="body1"
                          sx={{
                            fontFamily: "var(--font-geist-mono, monospace)",
                            fontWeight: 600,
                            color: data.technicals.macd_hist > 0 ? "success.main" : "error.main",
                          }}
                        >
                          {data.technicals.macd_hist.toFixed(2)}
                        </Typography>
                      </Box>
                    )}

                    {data?.technicals.bb_upper !== undefined &&
                      data?.technicals.bb_lower !== undefined && (
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
                            sx={{ color: "text.disabled", textTransform: "uppercase", display: "block", mb: 0.5 }}
                          >
                            Bollinger (Width)
                          </Typography>
                          <Typography
                            variant="body1"
                            sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 600 }}
                          >
                            {(
                              ((data.technicals.bb_upper - data.technicals.bb_lower) /
                                data.current_price) *
                              100
                            ).toFixed(1)}
                            %
                          </Typography>
                        </Box>
                      )}
                  </Box>
                </CardContent>
              </Card>
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <Card variant="outlined" sx={{ borderRadius: 3 }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
                    <Typography component="span" sx={{ fontSize: "1.2rem" }}>📈</Typography>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "success.main" }}>
                      入场计划 (Entry)
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.entry_levels.aggressive_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.entry_levels.aggressive.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "rgba(16,185,129,0.08)",
                        borderRadius: 1.5,
                        border: "1px solid rgba(16,185,129,0.2)",
                      }}
                    >
                      <Box>
                        <Typography variant="body2" sx={{ color: "#6ee7b7", fontWeight: 500 }}>
                          ✨ {data?.entry_levels.moderate_label}
                        </Typography>
                        <Typography variant="caption" sx={{ color: "rgba(110,231,183,0.6)" }}>
                          推荐挂单价位
                        </Typography>
                      </Box>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color: "success.main",
                        }}
                      >
                        ${data?.entry_levels.moderate.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.entry_levels.conservative_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.entry_levels.conservative.toFixed(2)}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              <Card variant="outlined" sx={{ borderRadius: 3 }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
                    <Typography component="span" sx={{ fontSize: "1.2rem" }}>🛑</Typography>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "error.main" }}>
                      风控止损 (Stop Loss)
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.stop_levels.tight_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.stop_levels.tight.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "rgba(239,68,68,0.06)",
                        borderRadius: 1.5,
                        border: "1px solid rgba(239,68,68,0.2)",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "#fca5a5" }}>
                        {data?.stop_levels.normal_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color: "error.main",
                        }}
                      >
                        ${data?.stop_levels.normal.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.stop_levels.loose_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.stop_levels.loose.toFixed(2)}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>

              <Card variant="outlined" sx={{ borderRadius: 3 }}>
                <CardContent sx={{ p: 3 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
                    <Typography component="span" sx={{ fontSize: "1.2rem" }}>🎯</Typography>
                    <Typography variant="subtitle1" sx={{ fontWeight: 700, color: "primary.main" }}>
                      获利目标 (Take Profit)
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "rgba(14,165,233,0.06)",
                        borderRadius: 1.5,
                        border: "1px solid rgba(14,165,233,0.2)",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "#7dd3fc" }}>
                        {data?.tp_levels.tp1_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{
                          fontFamily: "var(--font-geist-mono, monospace)",
                          fontWeight: 700,
                          color: "primary.main",
                        }}
                      >
                        ${data?.tp_levels.tp1.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.tp_levels.tp2_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.tp_levels.tp2.toFixed(2)}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        p: 1.5,
                        bgcolor: "action.hover",
                        borderRadius: 1.5,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.secondary" }}>
                        {data?.tp_levels.tp3_label}
                      </Typography>
                      <Typography
                        variant="body2"
                        sx={{ fontFamily: "var(--font-geist-mono, monospace)", fontWeight: 700 }}
                      >
                        ${data?.tp_levels.tp3.toFixed(2)}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
