"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";
type PickSizeFilter = "all" | "large" | "small";

interface TradePlan {
  symbol: string;
  action: string;
  current_price: number;
  entry_levels: {
    aggressive: number;
    moderate: number;
    conservative: number;
  };
  stop_levels: {
    tight: number;
    normal: number;
    loose: number;
  };
  take_profit_levels: {
    tp1: number;
    tp2: number;
    tp3: number;
  };
  reason: string;
}

interface PicksMetadata {
  date: string;
  regime: string;
  risk_budget: number;
  size: PickSizeFilter;
  size_label: string;
  eligible_stock_count: number;
  is_active: boolean;
}

interface ProgressInfo {
  stage: string;
  message: string;
  current?: number;
  total?: number;
}

interface WatchlistData {
  count: number;
  symbols: string[];
}

/* stage -> 0-100 base progress (before AI granular updates) */
const STAGE_PROGRESS: Record<string, number> = {
  config: 5,
  prices: 20,
  regime: 35,
  fundamentals: 50,
  ai: 70,
  select: 90,
};

export default function PicksPage() {
  const [picks, setPicks] = useState<TradePlan[]>([]);
  const [metadata, setMetadata] = useState<PicksMetadata | null>(null);
  const [doneMessage, setDoneMessage] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(true);
  const [progress, setProgress] = useState<ProgressInfo | null>(null);
  const [progressPercent, setProgressPercent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [sizeFilter, setSizeFilter] = useState<PickSizeFilter>("all");
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [symbolOptions, setSymbolOptions] = useState<string[]>([]);
  const [watchLoading, setWatchLoading] = useState(false);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [reloadTick, setReloadTick] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleFilterChange = (nextFilter: PickSizeFilter) => {
    if (nextFilter === sizeFilter) return;
    setStreaming(true);
    setError(null);
    setPicks([]);
    setMetadata(null);
    setDoneMessage(null);
    setProgress(null);
    setProgressPercent(0);
    setSizeFilter(nextFilter);
  };

  /* ── watchlist + symbol suggestions ──────────────────────── */

  const loadWatchlist = useCallback(() => {
    fetch(`${API_BASE}/api/watchlist`)
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "加载 watch list 失败");
        }
        return res.json() as Promise<WatchlistData>;
      })
      .then((res) => setWatchlist(res.symbols || []))
      .catch((e: unknown) => {
        setWatchError(e instanceof Error ? e.message : "加载 watch list 失败");
      });
  }, []);

  const loadSymbols = useCallback(() => {
    fetch(`${API_BASE}/api/symbols`)
      .then(async (res) => {
        if (!res.ok) return;
        const data = (await res.json()) as { symbols: string[] };
        setSymbolOptions(data.symbols || []);
      })
      .catch(() => { /* non-critical — autocomplete just won't have suggestions */ });
  }, []);

  const syncWatchlist = useCallback((newSymbols: string[]) => {
    setWatchLoading(true);
    setWatchError(null);

    fetch(`${API_BASE}/api/watchlist`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols: newSymbols }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || "更新 watch list 失败");
        }
        return res.json() as Promise<WatchlistData>;
      })
      .then((res) => {
        setWatchlist(res.symbols || []);
        setReloadTick((n) => n + 1);
      })
      .catch((e: unknown) => {
        setWatchError(e instanceof Error ? e.message : "更新 watch list 失败");
      })
      .finally(() => setWatchLoading(false));
  }, []);

  /* ── SSE streaming ──────────────────────────────────────── */

  useEffect(() => {
    setPicks([]);
    setMetadata(null);
    setDoneMessage(null);
    setError(null);
    setProgress(null);
    setProgressPercent(0);
    setStreaming(true);

    const url = `${API_BASE}/api/picks/stream?size=${sizeFilter}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.addEventListener("progress", (ev) => {
      const info: ProgressInfo = JSON.parse(ev.data);
      setProgress(info);
      const base = STAGE_PROGRESS[info.stage] ?? 0;
      if (info.current != null && info.total != null && info.total > 0) {
        const stageRange = info.stage === "ai" ? 20 : 10;
        setProgressPercent(base + Math.round((info.current / info.total) * stageRange));
      } else {
        setProgressPercent(base);
      }
    });

    es.addEventListener("metadata", (ev) => {
      const meta: PicksMetadata = JSON.parse(ev.data);
      setMetadata(meta);
    });

    es.addEventListener("pick", (ev) => {
      const plan: TradePlan = JSON.parse(ev.data);
      setPicks((prev) => [...prev, plan]);
    });

    es.addEventListener("done", (ev) => {
      const info = JSON.parse(ev.data) as { total: number; message: string };
      setDoneMessage(info.message);
      setProgressPercent(100);
      setStreaming(false);
      es.close();
    });

    es.addEventListener("error", (ev) => {
      /* SSE spec fires a generic Event on connection errors,
         but our backend sends a named "error" event with JSON data. */
      const me = ev as MessageEvent;
      if (me.data) {
        try {
          const info = JSON.parse(me.data) as { detail: string };
          setError(info.detail);
        } catch {
          setError("连接异常，请稍后重试");
        }
      } else {
        setError("连接异常，请稍后重试");
      }
      setStreaming(false);
      es.close();
    });

    es.onerror = () => {
      /* Connection-level error (e.g. server down, CORS). */
      if (es.readyState === EventSource.CLOSED) return;
      setError("连接服务器失败，请检查后端是否运行");
      setStreaming(false);
      es.close();
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [sizeFilter, reloadTick]);

  useEffect(() => {
    loadWatchlist();
    loadSymbols();
  }, [loadWatchlist, loadSymbols]);

  /* ── full-page loading (streaming, no metadata yet) ───── */

  if (streaming && !metadata && picks.length === 0) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box
          component="main"
          sx={{ flex: 1, overflowY: "auto", height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}
        >
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2, width: 280 }}>
            <CircularProgress size={32} />
            <Typography sx={{ color: "text.secondary", textAlign: "center" }}>
              {progress?.message || "筛选优质标的中..."}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={progressPercent}
              sx={{ width: "100%", borderRadius: 1, height: 4 }}
            />
          </Box>
        </Box>
      </Box>
    );
  }

  /* ── hard error (no data at all) ────────────────────────── */

  if (error && !metadata && picks.length === 0) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Sidebar />
        <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
          <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 12 }}>
            <Box
              sx={{
                bgcolor: "rgba(244,63,94,0.08)",
                border: "1px solid rgba(244,63,94,0.25)",
                borderRadius: 3,
                p: 6,
                textAlign: "center",
              }}
            >
              <Typography sx={{ color: "error.main" }}>{error}</Typography>
            </Box>
          </Box>
        </Box>
      </Box>
    );
  }

  /* ── main UI (progressive) ──────────────────────────────── */

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflowY: "auto", height: "100vh" }}>
        <HeroBanner
          title="ETF Trend"
          subtitle="智能选股推荐"
          description="基于多因子模型的每日精选 (动量 + 波动率 + 趋势)"
        />
        <Box sx={{ maxWidth: 1100, mx: "auto", px: 4, py: 5, display: "flex", flexDirection: "column", gap: 4 }}>

          {/* streaming progress bar */}
          {streaming && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                <CircularProgress size={16} />
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  {progress?.message || "处理中..."}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={progressPercent}
                sx={{ borderRadius: 1, height: 4 }}
              />
            </Box>
          )}

          <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
            <Box
              sx={{
                px: 2,
                py: 0.75,
                bgcolor: "background.paper",
                borderRadius: 1.5,
                border: "1px solid",
                borderColor: "divider",
                fontSize: "0.8rem",
                fontFamily: "monospace",
                color: "text.secondary",
              }}
            >
              {metadata?.date || "..."}
            </Box>
          </Box>

          {/* watchlist card */}
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent sx={{ display: "flex", flexDirection: "column", gap: 2, p: 2.5, "&:last-child": { pb: 2.5 } }}>
              <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
                  Watch List (动态候选池)
                </Typography>
                <Typography variant="caption" sx={{ color: "text.disabled" }}>
                  当前 {watchlist.length} 只
                </Typography>
              </Box>

              <Autocomplete
                multiple
                freeSolo
                limitTags={8}
                options={symbolOptions.filter((s) => !watchlist.includes(s))}
                value={watchlist}
                disabled={watchLoading}
                onChange={(_e, newValue) => {
                  const normalized = newValue.map((v) => v.trim().toUpperCase()).filter(Boolean);
                  const unique = [...new Set(normalized)];
                  syncWatchlist(unique);
                }}
                getLimitTagsText={(more) => `+${more}`}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    size="small"
                    placeholder={watchlist.length === 0 ? "输入股票代码，例如 PLTR" : "继续输入添加..."}
                    slotProps={{ htmlInput: { ...params.inputProps, style: { fontSize: "0.875rem" } } }}
                  />
                )}
                filterOptions={(options, { inputValue }) => {
                  const upper = inputValue.toUpperCase();
                  if (!upper) return options.slice(0, 20);
                  return options.filter((o) => o.startsWith(upper)).slice(0, 20);
                }}
                ChipProps={{ size: "small", sx: { fontSize: "0.75rem" } }}
                sx={{
                  "& .MuiAutocomplete-inputRoot": {
                    maxHeight: 120,
                    overflowY: "auto",
                    flexWrap: "wrap",
                  },
                }}
              />

              {watchError && (
                <Typography variant="caption" sx={{ color: "error.main" }}>
                  {watchError}
                </Typography>
              )}
            </CardContent>
          </Card>

          {/* size filter toggle */}
          <Card variant="outlined" sx={{ borderRadius: 2 }}>
            <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
              <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 2 }}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  规模筛选 (Russell)
                </Typography>
                <ToggleButtonGroup
                  value={sizeFilter}
                  exclusive
                  onChange={(_e, val) => { if (val) handleFilterChange(val as PickSizeFilter); }}
                  size="small"
                >
                  <ToggleButton value="all" sx={{ px: 2, py: 0.75, fontSize: "0.8rem" }}>
                    全部
                  </ToggleButton>
                  <ToggleButton value="large" sx={{ px: 2, py: 0.75, fontSize: "0.8rem" }}>
                    大盘股
                  </ToggleButton>
                  <ToggleButton value="small" sx={{ px: 2, py: 0.75, fontSize: "0.8rem" }}>
                    小盘股
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>
            </CardContent>
          </Card>

          {/* regime status */}
          {metadata && (
            <Box
              sx={{
                borderRadius: 2,
                p: 2.5,
                border: "1px solid",
                borderColor: metadata.is_active ? "success.main" : "warning.main",
                bgcolor: metadata.is_active ? "rgba(46,160,67,0.08)" : "rgba(245,158,11,0.08)",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5, color: metadata.is_active ? "success.main" : "warning.main" }}>
                    系统状态: {metadata.regime}
                  </Typography>
                  <Typography variant="caption" sx={{ display: "block", mb: 0.5, color: metadata.is_active ? "success.main" : "warning.main", opacity: 0.8 }}>
                    当前范围: {metadata.size_label || "全部"} | 可参与筛选: {metadata.eligible_stock_count ?? 0} 只
                  </Typography>
                  {doneMessage && (
                    <Typography variant="body2" sx={{ color: metadata.is_active ? "success.main" : "warning.main", opacity: 0.9 }}>
                      {doneMessage}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
          )}

          {/* picks grid (progressive) */}
          {picks.length > 0 ? (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
              {picks.map((pick, idx) => (
                <Card
                  key={pick.symbol}
                  component={Link}
                  href={`/stock/${pick.symbol}`}
                  variant="outlined"
                  sx={{
                    borderRadius: 2,
                    textDecoration: "none",
                    display: "block",
                    transition: "border-color 0.2s, box-shadow 0.2s",
                    "&:hover": {
                      borderColor: "primary.main",
                      boxShadow: "0 8px 32px rgba(59,137,255,0.12)",
                    },
                  }}
                >
                  <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
                    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2.5 }}>
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
                            fontSize: "0.9rem",
                            flexShrink: 0,
                          }}
                        >
                          {idx + 1}
                        </Box>
                        <Typography
                          variant="h5"
                          sx={{
                            fontWeight: 700,
                            color: "text.primary",
                            ".MuiCard-root:hover &": { color: "primary.main" },
                            transition: "color 0.2s",
                          }}
                        >
                          {pick.symbol}
                        </Typography>
                      </Box>
                      <Box sx={{ textAlign: "right" }}>
                        <Typography variant="caption" sx={{ color: "text.disabled", textTransform: "uppercase", letterSpacing: "0.08em", display: "block", mb: 0.25 }}>
                          现价
                        </Typography>
                        <Typography
                          sx={{
                            fontSize: "1.4rem",
                            fontFamily: "monospace",
                            fontWeight: 600,
                            color: "text.primary",
                          }}
                        >
                          ${pick.current_price.toFixed(2)}
                        </Typography>
                      </Box>
                    </Box>

                    <Typography
                      variant="body2"
                      sx={{
                        color: "text.secondary",
                        mb: 3,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                        minHeight: "2.5em",
                      }}
                    >
                      {pick.reason}
                    </Typography>

                    <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1.5 }}>
                      <Box
                        sx={{
                          bgcolor: "action.hover",
                          borderRadius: 1.5,
                          p: 1.5,
                          border: "1px solid",
                          borderColor: "divider",
                        }}
                      >
                        <Typography sx={{ color: "text.disabled", fontSize: "0.65rem", textTransform: "uppercase", mb: 0.5 }}>
                          入场 (稳健)
                        </Typography>
                        <Typography sx={{ color: "success.main", fontFamily: "monospace", fontWeight: 500, fontSize: "0.875rem" }}>
                          ${pick.entry_levels.moderate.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          bgcolor: "action.hover",
                          borderRadius: 1.5,
                          p: 1.5,
                          border: "1px solid",
                          borderColor: "divider",
                        }}
                      >
                        <Typography sx={{ color: "text.disabled", fontSize: "0.65rem", textTransform: "uppercase", mb: 0.5 }}>
                          止损 (标准)
                        </Typography>
                        <Typography sx={{ color: "error.main", fontFamily: "monospace", fontWeight: 500, fontSize: "0.875rem" }}>
                          ${pick.stop_levels.normal.toFixed(2)}
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          bgcolor: "action.hover",
                          borderRadius: 1.5,
                          p: 1.5,
                          border: "1px solid",
                          borderColor: "divider",
                        }}
                      >
                        <Typography sx={{ color: "text.disabled", fontSize: "0.65rem", textTransform: "uppercase", mb: 0.5 }}>
                          目标 (TP1)
                        </Typography>
                        <Typography sx={{ color: "primary.main", fontFamily: "monospace", fontWeight: 500, fontSize: "0.875rem" }}>
                          ${pick.take_profit_levels.tp1.toFixed(2)}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          ) : !streaming ? (
            <Card variant="outlined" sx={{ borderRadius: 3 }}>
              <CardContent sx={{ p: 8, textAlign: "center", "&:last-child": { pb: 8 } }}>
                <Typography variant="h6" sx={{ color: "text.primary", mb: 1 }}>
                  暂无推荐
                </Typography>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  当前市场环境下，模型未筛选出符合高胜率条件的标的。
                </Typography>
              </CardContent>
            </Card>
          ) : null}

          {/* risk disclaimer */}
          <Card variant="outlined" sx={{ borderRadius: 2, bgcolor: "background.paper", opacity: 0.9 }}>
            <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
              <Typography
                variant="caption"
                sx={{
                  color: "primary.main",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  display: "block",
                  mb: 1.5,
                }}
              >
                风险提示
              </Typography>
              <Box component="ul" sx={{ m: 0, pl: 2.5, display: "flex", flexDirection: "column", gap: 0.75 }}>
                <Box component="li">
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    个股波动风险显著高于 ETF，建议严格控制单只股票仓位（推荐 ≤5%）。
                  </Typography>
                </Box>
                <Box component="li">
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    请务必严格执行止损策略。当价格达到止盈目标时，建议分批减仓锁定利润。
                  </Typography>
                </Box>
                <Box component="li">
                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    本系统生成的信号仅供量化研究参考，不构成具体投资建议。
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

        </Box>
      </Box>
    </Box>
  );
}
