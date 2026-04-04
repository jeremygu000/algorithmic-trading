"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import CircularProgress from "@mui/material/CircularProgress";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";

interface MarketStatus {
  date: string;
  regime: string;
  risk_budget: number;
  signals: {
    [key: string]: number | boolean | string;
  };
}

const signalIcons: Record<string, string> = {
  vix: "📉",
  momentum: "🚀",
  trend: "📈",
  volume: "📊",
  breadth: "🌐",
  yield: "💹",
  default: "⚙️",
};

function getSignalIcon(key: string): string {
  const lower = key.toLowerCase();
  for (const k of Object.keys(signalIcons)) {
    if (lower.includes(k)) return signalIcons[k];
  }
  return signalIcons.default;
}

export default function MarketPage() {
  const [data, setData] = useState<MarketStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/market`, { signal: controller.signal })
      .then((res) => res.json())
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  const regimeConfig: Record<
    string,
    { color: string; label: string; accentColor: string }
  > = {
    RISK_ON: {
      color: "#36bb80",
      label: "风险偏好 (Risk On)",
      accentColor: "#36bb80",
    },
    NEUTRAL: {
      color: "#3b89ff",
      label: "中性观望 (Neutral)",
      accentColor: "#3b89ff",
    },
    RISK_OFF: {
      color: "#ff7134",
      label: "风险厌恶 (Risk Off)",
      accentColor: "#ff7134",
    },
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
          <CircularProgress size={40} />
          <Typography color="text.secondary">加载市场数据...</Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5 }}>
        <Card
          sx={{
            border: "1px solid",
            borderColor: "error.dark",
            bgcolor: "rgba(211, 47, 47, 0.08)",
            borderRadius: 3,
            textAlign: "center",
          }}
        >
          <CardContent sx={{ py: 6 }}>
            <Typography variant="h6" color="error.main" fontWeight={600} mb={1}>
              连接失败
            </Typography>
            <Typography color="text.secondary" mb={3}>
              {error}
            </Typography>
            <Button
              variant="contained"
              color="error"
              onClick={() => window.location.reload()}
              sx={{ textTransform: "none" }}
            >
              重试
            </Button>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const regime = regimeConfig[data?.regime || "NEUTRAL"];

  return (
    <>
      <HeroBanner
        title="ETF Trend"
        subtitle="市场状态"
        description="实时监控市场情绪 (Risk On/Off)，查看风险预算分配与关键市场信号"
      />
      <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            px: 4,
            py: 5,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
            <Box>
              <Chip
                label="📡 实时监控"
                size="small"
                sx={{
                  mb: 2,
                  bgcolor: "background.paper",
                  color: "primary.main",
                  border: "1px solid",
                  borderColor: "divider",
                  fontWeight: 500,
                  fontSize: "0.8rem",
                }}
              />
              <Typography variant="h4" fontWeight={700} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Box component="span" sx={{ color: "text.primary" }}>
                  市场
                </Box>
                <Box
                  component="span"
                  sx={{
                    background: "linear-gradient(90deg, #3b89ff 0%, #36bb80 100%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                  }}
                >
                  状态
                </Box>
              </Typography>
            </Box>
            <Button
              component={Link}
              href="/trend-scan"
              variant="outlined"
              color="success"
              size="small"
              sx={{ textTransform: "none", fontWeight: 500 }}
            >
              趋势扫描
            </Button>
          </Box>

          <Card
            sx={{
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              borderLeft: `4px solid ${regime.accentColor}`,
              bgcolor: "background.paper",
              position: "relative",
              overflow: "hidden",
              transition: "border-color 0.2s, box-shadow 0.2s, transform 0.2s",
              "&:hover": {
                transform: "translateY(-2px)",
                boxShadow: 4,
              },
            }}
          >
            <CardContent sx={{ p: 4, position: "relative", zIndex: 1 }}>
              <Box
                sx={{
                  display: "flex",
                  flexDirection: { xs: "column", md: "row" },
                  alignItems: { md: "center" },
                  justifyContent: "space-between",
                  gap: 3,
                  mb: 4,
                }}
              >
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    fontWeight={600}
                    letterSpacing="0.12em"
                    display="block"
                    mb={0.5}
                  >
                    当前趋势
                  </Typography>
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    sx={{ color: regime.color, display: "flex", alignItems: "center", gap: 1.5 }}
                  >
                    {regime.label}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: { md: "right" } }}>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    fontWeight={600}
                    letterSpacing="0.12em"
                    display="block"
                    mb={0.5}
                  >
                    数据更新于
                  </Typography>
                  <Typography variant="h5" fontFamily="monospace" color="text.primary">
                    {data?.date}
                  </Typography>
                </Box>
              </Box>

              <Box mb={4}>
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    仓位建议 (Risk Budget)
                  </Typography>
                  <Typography variant="body2" color="text.secondary" fontFamily="monospace" fontWeight={600}>
                    {((data?.risk_budget || 0) * 100).toFixed(0)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={(data?.risk_budget || 0) * 100}
                  sx={{
                    height: 10,
                    borderRadius: 5,
                    bgcolor: "action.hover",
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 5,
                      bgcolor: regime.accentColor,
                    },
                  }}
                />
              </Box>

              <Box
                sx={{
                  bgcolor: "background.paper",
                  borderRadius: 2,
                  p: 3,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography
                  variant="subtitle1"
                  fontWeight={600}
                  color="primary.main"
                  sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}
                >
                  <Box
                    component="svg"
                    sx={{ width: 20, height: 20 }}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </Box>
                  策略解读
                </Typography>
                <Typography variant="body2" color="text.secondary" lineHeight={1.8}>
                  {data?.regime === "RISK_ON" &&
                    "市场动量强劲，处于上升趋势。系统建议增加权益类资产配置，积极参与市场机会。"}
                  {data?.regime === "NEUTRAL" &&
                    "市场趋势不明确或处于震荡整理。建议保持中性仓位，耐心等待趋势确认。"}
                  {data?.regime === "RISK_OFF" &&
                    "市场波动率上升或动量转负。系统建议大幅降低风险敞口，优先保本，增配现金或债券。"}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {data?.signals && (
            <Box>
              <Box sx={{ mb: 3 }}>
                <Typography
                  variant="overline"
                  sx={{
                    color: "text.disabled",
                    letterSpacing: "0.12em",
                    fontWeight: 600,
                    display: "block",
                    mb: 0.5,
                  }}
                >
                  核心指标
                </Typography>
                <Typography variant="h5" fontWeight={700} color="text.primary">
                  详细信号
                </Typography>
              </Box>
              <Grid container spacing={3}>
                {Object.entries(data.signals).map(([key, value]) => {
                  const icon = getSignalIcon(key);
                  return (
                    <Grid size={{ xs: 12, sm: 6 }} key={key}>
                      <Card
                        sx={{
                          borderRadius: 3,
                          border: "1px solid",
                          borderColor: "divider",
                          bgcolor: "background.paper",
                          position: "relative",
                          overflow: "hidden",
                          transition: "border-color 0.2s, box-shadow 0.2s, transform 0.2s",
                          "&:hover": {
                            borderColor: "primary.main",
                            transform: "translateY(-2px)",
                            boxShadow: 4,
                          },
                        }}
                      >
                        <Box
                          sx={{
                            position: "absolute",
                            top: 8,
                            right: 12,
                            fontSize: "6rem",
                            lineHeight: 1,
                            opacity: 0.07,
                            pointerEvents: "none",
                          }}
                        >
                          {icon}
                        </Box>
                        <CardContent
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            py: 2.5,
                            px: 3,
                            position: "relative",
                            zIndex: 1,
                            "&:last-child": { pb: 2.5 },
                          }}
                        >
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            fontWeight={500}
                            sx={{ textTransform: "uppercase", letterSpacing: 1 }}
                          >
                            {key}
                          </Typography>
                          <Typography
                            variant="body1"
                            fontFamily="monospace"
                            fontWeight={600}
                            sx={{
                              color:
                                typeof value === "boolean"
                                  ? value
                                    ? "success.main"
                                    : "error.main"
                                  : "text.primary",
                            }}
                          >
                            {typeof value === "boolean"
                              ? value
                                ? "TRUE"
                                : "FALSE"
                              : typeof value === "number"
                              ? value.toFixed(2)
                              : value}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </Box>
          )}
        </Box>
    </>
  );
}
