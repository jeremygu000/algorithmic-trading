"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import SearchIcon from "@mui/icons-material/Search";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";

const quickLinks = [
  {
    href: "/market",
    icon: "🌍",
    title: "市场状态",
    desc: "实时监控市场情绪 (Risk On/Off)，查看风险预算分配与关键市场信号。",
    hoverBorder: "success.main",
    hoverText: "success.main",
  },
  {
    href: "/trend-scan",
    icon: "📡",
    title: "趋势扫描",
    desc: "按连续上涨/下跌形态自动扫描股票池，快速定位近 K 日强势或弱势标的。",
    hoverBorder: "primary.main",
    hoverText: "primary.main",
  },
  {
    href: "/picks",
    icon: "🎯",
    title: "今日推荐",
    desc: "AI 筛选的高动量个股列表，包含激进/稳健/保守三级买入方案与动态止损位。",
    hoverBorder: "warning.main",
    hoverText: "warning.main",
  },
  {
    href: "/stock/AAPL",
    icon: "📊",
    title: "深度分析",
    desc: "交互式 K 线图表，集成均线系统与关键支撑阻力位，提供完整的技术面诊断。",
    hoverBorder: "error.main",
    hoverText: "error.main",
  },
];

const popularStocks = [
  "AAPL",
  "NVDA",
  "TSLA",
  "MSFT",
  "GOOGL",
  "AMZN",
  "META",
  "AMD",
  "PLTR",
  "COIN",
];

export default function Home() {
  const [symbol, setSymbol] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (symbol.trim()) {
      router.push(`/stock/${symbol.toUpperCase()}`);
    }
  };

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner />
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
          <Box sx={{ textAlign: "center" }}>
            <Chip
              label="✨ 量化交易系统 v2.0"
              size="small"
              sx={{
                mb: 3,
                bgcolor: "background.paper",
                color: "primary.main",
                border: "1px solid",
                borderColor: "divider",
                fontWeight: 500,
                fontSize: "0.8rem",
              }}
            />

            <Typography
              variant="h2"
              sx={{
                fontWeight: 700,
                mb: 2,
                letterSpacing: "-0.02em",
                fontSize: { xs: "2.5rem", md: "3.5rem" },
              }}
            >
              <Box component="span" sx={{ color: "text.primary" }}>
                发现下一个
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
                {" "}
                交易机会
              </Box>
            </Typography>

            <Typography
              variant="body1"
              sx={{
                color: "text.secondary",
                mb: 4,
                maxWidth: 560,
                mx: "auto",
                lineHeight: 1.8,
                fontSize: "1.1rem",
              }}
            >
              基于动量和趋势的专业量化分析平台。提供多级买卖点位、ATR 动态止损与交互式蜡烛图分析。
            </Typography>

            <Box
              component="form"
              onSubmit={handleSearch}
              sx={{
                maxWidth: 520,
                mx: "auto",
                display: "flex",
                gap: 1.5,
                p: 1,
                bgcolor: "background.paper",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 3,
                transition: "border-color 0.2s",
                "&:focus-within": {
                  borderColor: "primary.main",
                },
              }}
            >
              <TextField
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="输入股票代码 (如 AAPL, MSFT)"
                variant="standard"
                fullWidth
                InputProps={{
                  disableUnderline: true,
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: "text.disabled", fontSize: 20 }} />
                    </InputAdornment>
                  ),
                  sx: {
                    px: 1,
                    fontSize: "1rem",
                    color: "text.primary",
                    "& input::placeholder": { color: "text.disabled" },
                  },
                }}
              />
              <Button
                type="submit"
                variant="contained"
                disableElevation
                sx={{
                  px: 4,
                  py: 1.25,
                  borderRadius: 2,
                  fontWeight: 600,
                  fontSize: "0.95rem",
                  bgcolor: "primary.main",
                  color: "#fff",
                  whiteSpace: "nowrap",
                  "&:hover": { bgcolor: "primary.dark" },
                }}
              >
                分析
              </Button>
            </Box>
          </Box>

          <Grid container spacing={3}>
            {quickLinks.map((item) => (
              <Grid size={{ xs: 12, sm: 6, xl: 3 }} key={item.href}>
                <Card
                  component={Link}
                  href={item.href}
                  sx={{
                    display: "block",
                    textDecoration: "none",
                    height: "100%",
                    position: "relative",
                    bgcolor: "background.paper",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 3,
                    overflow: "hidden",
                    transition: "border-color 0.2s, box-shadow 0.2s, transform 0.2s",
                    cursor: "pointer",
                    "&:hover": {
                      borderColor: item.hoverBorder,
                      transform: "translateY(-2px)",
                      boxShadow: 4,
                      "& .card-icon-bg": { opacity: 0.2 },
                      "& .card-icon": { transform: "scale(1.1)" },
                      "& .card-title": { color: item.hoverText },
                    },
                  }}
                >
                  <Box
                    className="card-icon-bg"
                    sx={{
                      position: "absolute",
                      top: 8,
                      right: 12,
                      fontSize: "6rem",
                      lineHeight: 1,
                      opacity: 0.07,
                      transition: "opacity 0.2s",
                      pointerEvents: "none",
                    }}
                  >
                    {item.icon}
                  </Box>

                  <CardContent sx={{ p: 4, position: "relative", zIndex: 1 }}>
                    <Box
                      className="card-icon"
                      sx={{
                        width: 48,
                        height: 48,
                        bgcolor: "action.hover",
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "1.5rem",
                        mb: 3,
                        transition: "transform 0.3s",
                      }}
                    >
                      {item.icon}
                    </Box>

                    <Typography
                      className="card-title"
                      variant="h6"
                      sx={{
                        fontWeight: 700,
                        mb: 1.5,
                        color: "text.primary",
                        transition: "color 0.2s",
                      }}
                    >
                      {item.title}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        lineHeight: 1.7,
                      }}
                    >
                      {item.desc}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ textAlign: "center" }}>
            <Typography
              variant="overline"
              sx={{
                color: "text.disabled",
                letterSpacing: "0.12em",
                fontWeight: 600,
                display: "block",
                mb: 2.5,
              }}
            >
              热门关注
            </Typography>

            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "center",
                gap: 1.5,
              }}
            >
              {popularStocks.map((s) => (
                <Chip
                  key={s}
                  label={s}
                  component={Link}
                  href={`/stock/${s}`}
                  clickable
                  sx={{
                    bgcolor: "background.paper",
                    border: "1px solid",
                    borderColor: "divider",
                    color: "text.secondary",
                    fontWeight: 600,
                    fontSize: "0.85rem",
                    px: 0.5,
                    transition: "border-color 0.15s, color 0.15s, background-color 0.15s",
                    "&:hover": {
                      bgcolor: "action.hover",
                      borderColor: "primary.main",
                      color: "primary.main",
                    },
                  }}
                />
              ))}
            </Box>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
