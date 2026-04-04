"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useThemeMode } from "./ThemeProvider";

interface HeroBannerProps {
  title?: string;
  subtitle?: string;
  description?: string;
}

export default function HeroBanner({
  title = "ETF Trend",
  subtitle = "量化分析系统",
  description = "基于动量和趋势的专业量化分析平台 — 提供多级买卖点位、ATR 动态止损与交互式蜡烛图分析",
}: HeroBannerProps) {
  const { mode } = useThemeMode();

  const gradient =
    mode === "dark"
      ? "linear-gradient(135deg, #060a12 0%, #0a1628 50%, #1a3a6e 100%)"
      : "linear-gradient(135deg, #0f2246 0%, #1a3a6e 50%, #3b89ff 100%)";

  return (
    <Box
      sx={{
        background: gradient,
        px: 5,
        py: 5,
        mb: 0,
        width: "100%",
        transition: "background 0.3s ease",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "rgba(255,255,255,0.6)",
          fontSize: "0.7rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          display: "block",
          mb: 0.5,
        }}
      >
        {title}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          color: "#ffffff",
          fontWeight: 700,
          fontSize: "1.75rem",
          mb: 0.5,
        }}
      >
        {subtitle}
      </Typography>
      <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.65)", fontSize: "0.875rem" }}>
        {description}
      </Typography>
    </Box>
  );
}
