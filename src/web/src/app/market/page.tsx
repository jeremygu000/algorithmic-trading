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
import Sidebar from "@/components/Sidebar";
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

export default function MarketPage() {
  const [data, setData] = useState<MarketStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/market`)
      .then((res) => res.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const regimeConfig: Record<
    string,
    { color: string; icon: string; label: string; borderColor: string; bgColor: string }
  > = {
    RISK_ON: {
      color: "success.main",
      icon: "🟢",
      label: "风险偏好 (Risk On)",
      borderColor: "success.main",
      bgColor: "rgba(46, 125, 50, 0.08)",
    },
    NEUTRAL: {
      color: "primary.main",
      icon: "🔵",
      label: "中性观望 (Neutral)",
      borderColor: "primary.main",
      bgColor: "rgba(25, 118, 210, 0.08)",
    },
    RISK_OFF: {
      color: "error.main",
      icon: "🔴",
      label: "风险厌恶 (Risk Off)",
      borderColor: "error.main",
      bgColor: "rgba(211, 47, 47, 0.08)",
    },
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
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
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Box sx={{ maxWidth: 900, mx: "auto", px: 4, py: 5 }}>
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
        </Box>
      </Box>
    );
  }

  const regime = regimeConfig[data?.regime || "NEUTRAL"];

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="市场状态"
          description="实时监控市场情绪 (Risk On/Off)，查看风险预算分配与关键市场信号"
        />
        <Box
          sx={{
            maxWidth: 900,
            mx: "auto",
            px: 4,
            py: 5,
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 2 }}>
            <Typography variant="h4" fontWeight={700}>
              🌍 市场状态
            </Typography>
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
              borderColor: regime.borderColor,
              bgcolor: regime.bgColor,
              backdropFilter: "blur(8px)",
            }}
          >
            <CardContent sx={{ p: 4 }}>
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
                    letterSpacing={2}
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
                    letterSpacing={2}
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
                    bgcolor: "rgba(0,0,0,0.12)",
                    "& .MuiLinearProgress-bar": {
                      borderRadius: 5,
                      background: "linear-gradient(90deg, #0288d1, #1565c0)",
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
              <Typography
                variant="h6"
                fontWeight={700}
                color="text.primary"
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}
              >
                ⚙️ 核心指标详情
              </Typography>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                  gap: 2,
                }}
              >
                {Object.entries(data.signals).map(([key, value]) => (
                  <Card
                    key={key}
                    sx={{
                      borderRadius: 2,
                      border: "1px solid",
                      borderColor: "divider",
                      bgcolor: "background.paper",
                      transition: "border-color 0.2s",
                      "&:hover": { borderColor: "primary.light" },
                    }}
                  >
                    <CardContent
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        py: 2,
                        "&:last-child": { pb: 2 },
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
                ))}
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
