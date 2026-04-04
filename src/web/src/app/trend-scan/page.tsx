"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";
import TradePlanModal from "@/components/TradePlanModal";

const API_BASE = "http://localhost:8300";

type TrendDirection = "up" | "down";

interface ScannedStock {
  symbol: string;
  name: string;
  latest_price: number;
  daily_changes_pct: number[];
}

interface TrendScanData {
  date: string;
  k: number;
  trend: TrendDirection;
  trend_label: string;
  total_scanned: number;
  matched_count: number;
  stocks: ScannedStock[];
}

function calcCumulativeChange(changes: number[]): number {
  return changes.reduce((acc, pct) => acc * (1 + pct / 100), 1) - 1;
}

export default function TrendScanPage() {
  const [k, setK] = useState<number>(5);
  const [trend, setTrend] = useState<TrendDirection>("up");
  const [data, setData] = useState<TrendScanData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [planSymbol, setPlanSymbol] = useState<string | null>(null);
  const [planStockName, setPlanStockName] = useState("");
  const [planPrice, setPlanPrice] = useState(0);

  const handleTrendChange = (nextTrend: TrendDirection) => {
    if (nextTrend === trend) return;
    setLoading(true);
    setError(null);
    setTrend(nextTrend);
  };

  const handleKChange = (nextK: number) => {
    if (nextK === k) return;
    setLoading(true);
    setError(null);
    setK(nextK);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/stocks/trend-scan?k=${k}&t=${trend}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "趋势扫描请求失败");
        }
        return res.json() as Promise<TrendScanData>;
      })
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") {
          return;
        }
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [k, trend]);

  const trendColor = useMemo(
    () => (trend === "up" ? "success.main" : "error.main"),
    [trend]
  );

  const trendColorHex = useMemo(
    () => (trend === "up" ? "#36bb80" : "#ff7134"),
    [trend]
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="趋势扫描"
          description="按最近 K 日连续上涨/下跌形态筛选股票池，点击股票名称可进入深度分析页面"
        />
        <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5, display: "flex", flexDirection: "column", gap: 4 }}>

          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: { md: "center" }, gap: 4 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  趋势方向
                </Typography>
                <ToggleButtonGroup
                  exclusive
                  value={trend}
                  onChange={(_e, val: TrendDirection | null) => {
                    if (val) handleTrendChange(val);
                  }}
                  size="small"
                >
                  <ToggleButton
                    value="up"
                    sx={{
                      px: 2,
                      "&.Mui-selected": {
                        bgcolor: "rgba(54,187,128,0.15)",
                        borderColor: "rgba(54,187,128,0.4)",
                        color: "#36bb80",
                        "&:hover": { bgcolor: "rgba(54,187,128,0.2)" },
                      },
                    }}
                  >
                    上涨
                  </ToggleButton>
                  <ToggleButton
                    value="down"
                    sx={{
                      px: 2,
                      "&.Mui-selected": {
                        bgcolor: "rgba(255,113,52,0.15)",
                        borderColor: "rgba(255,113,52,0.4)",
                        color: "#ff7134",
                        "&:hover": { bgcolor: "rgba(255,113,52,0.2)" },
                      },
                    }}
                  >
                    下跌
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>

              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  连续天数 K
                </Typography>
                <Select
                  value={k}
                  onChange={(e) => handleKChange(Number(e.target.value))}
                  size="small"
                  sx={{ minWidth: 80 }}
                >
                  {[3, 5, 7, 10].map((val) => (
                    <MenuItem key={val} value={val}>
                      {val}
                    </MenuItem>
                  ))}
                </Select>
              </Box>

              {data?.date && (
                <Box sx={{ ml: { md: "auto" } }}>
                  <Chip
                    label={`📅 ${data.date}`}
                    size="small"
                    variant="outlined"
                    sx={{ fontFamily: "monospace", color: "text.secondary" }}
                  />
                </Box>
              )}
            </CardContent>
          </Card>

          {loading && (
            <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "32vh", gap: 2 }}>
              <CircularProgress size={36} />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                扫描中...
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
                扫描失败
              </Typography>
              <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
                {error}
              </Typography>
              <Button
                variant="outlined"
                color="error"
                size="small"
                onClick={() => window.location.reload()}
              >
                重试
              </Button>
            </Box>
          )}

          {!loading && !error && data && (
            <>
              <Box
                sx={{
                  bgcolor: trend === "up" ? "rgba(54,187,128,0.08)" : "rgba(255,113,52,0.08)",
                  border: `1px solid ${trend === "up" ? "rgba(54,187,128,0.25)" : "rgba(255,113,52,0.25)"}`,
                  borderRadius: 2,
                  px: 3,
                  py: 2,
                }}
              >
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                  {[
                    { label: "方向", value: data.trend_label },
                    { label: "K", value: String(data.k) },
                    { label: "扫描总数", value: String(data.total_scanned) },
                    { label: "命中", value: String(data.matched_count) },
                  ].map(({ label, value }) => (
                    <Typography key={label} variant="body2" sx={{ color: trendColorHex }}>
                      {label}: <Box component="b" sx={{ color: trendColorHex }}>{value}</Box>
                    </Typography>
                  ))}
                </Box>
              </Box>

              {data.stocks.length > 0 ? (
                <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
                  {data.stocks.map((stock, idx) => {
                    const cumulative = calcCumulativeChange(stock.daily_changes_pct);
                    const cumulativeColor = cumulative >= 0 ? "#36bb80" : "#ff7134";

                    return (
                      <Card
                        key={stock.symbol}
                        variant="outlined"
                        sx={{
                          borderRadius: 3,
                          transition: "border-color 0.2s, box-shadow 0.2s",
                          "&:hover": {
                            borderColor: trendColorHex,
                            boxShadow: `0 4px 24px rgba(0,0,0,0.18)`,
                          },
                        }}
                      >
                         <CardContent sx={{ p: 3 }}>
                          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
                             <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                               <Box
                                sx={{
                                  width: 40,
                                  height: 40,
                                  borderRadius: 1.5,
                                  bgcolor: "action.hover",
                                  border: "1px solid",
                                  borderColor: "divider",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  color: "primary.main",
                                  fontWeight: 700,
                                  fontSize: "0.95rem",
                                  flexShrink: 0,
                                }}
                              >
                                {idx + 1}
                              </Box>
                              <Box>
                                <Link
                                  href={`/stock/${stock.symbol}`}
                                  style={{ textDecoration: "none" }}
                                >
                                  <Typography
                                    variant="h6"
                                    sx={{
                                      fontWeight: 700,
                                      color: "text.primary",
                                      lineHeight: 1.2,
                                      "&:hover": { color: trendColor },
                                      transition: "color 0.15s",
                                    }}
                                  >
                                    {stock.symbol}
                                  </Typography>
                                </Link>
                                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                                  {stock.name}
                                </Typography>
                              </Box>
                             </Box>
                             <Box sx={{ textAlign: "right" }}>
                              <Typography variant="caption" sx={{ color: "text.disabled", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", mb: 0.25 }}>
                                最新价
                              </Typography>
                              <Typography variant="h6" sx={{ fontFamily: "monospace", fontWeight: 600, color: "text.primary" }}>
                                ${stock.latest_price.toFixed(2)}
                              </Typography>
                            </Box>
                           </Box>

                          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
                            <Typography variant="body2" sx={{ color: "text.secondary" }}>
                              近 {stock.daily_changes_pct.length} 日累计变化
                            </Typography>
                            <Typography variant="body1" sx={{ fontFamily: "monospace", fontWeight: 600, color: cumulativeColor }}>
                              {(cumulative * 100).toFixed(2)}%
                            </Typography>
                          </Box>

                          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 1 }}>
                             {stock.daily_changes_pct.map((dayPct, i) => (
                               <Box
                                 key={`${stock.symbol}-${i}`}
                                 sx={{
                                   bgcolor: "action.hover",
                                   border: "1px solid",
                                   borderColor: "divider",
                                   borderRadius: 1.5,
                                   p: 1,
                                   textAlign: "center",
                                 }}
                               >
                                 <Typography variant="caption" sx={{ color: "text.disabled", display: "block", fontSize: "0.65rem", mb: 0.25 }}>
                                   D-{stock.daily_changes_pct.length - i}
                                 </Typography>
                                 <Typography
                                   variant="caption"
                                   sx={{
                                     fontFamily: "monospace",
                                     fontSize: "0.7rem",
                                     fontWeight: 600,
                                     color: dayPct >= 0 ? "#36bb80" : "#ff7134",
                                   }}
                                 >
                                   {dayPct > 0 ? "+" : ""}
                                   {dayPct.toFixed(2)}%
                                 </Typography>
                               </Box>
                             ))}
                           </Box>

                           <Box sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
                             <Button
                               variant="outlined"
                               size="small"
                               onClick={() => {
                                 setPlanSymbol(stock.symbol);
                                 setPlanStockName(stock.name);
                                 setPlanPrice(stock.latest_price);
                               }}
                               sx={{
                                 borderColor: trendColorHex,
                                 color: trendColorHex,
                                 "&:hover": {
                                   borderColor: trendColorHex,
                                   bgcolor: trend === "up" ? "rgba(54,187,128,0.08)" : "rgba(255,113,52,0.08)",
                                 },
                               }}
                             >
                               一键交易
                             </Button>
                           </Box>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Box>
              ) : (
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
                  <Typography sx={{ fontSize: "3.5rem", opacity: 0.2, mb: 3 }}>🧭</Typography>
                  <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
                    暂无符合条件的股票
                  </Typography>
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    可尝试切换趋势方向或调整 K 值后再次扫描。
                  </Typography>
                </Box>
              )}
            </>
          )}
        </Box>
      </Box>
      <TradePlanModal
        open={planSymbol !== null}
        onClose={() => setPlanSymbol(null)}
        symbol={planSymbol ?? ""}
        stockName={planStockName}
        latestPrice={planPrice}
      />
    </Box>
  );
}
