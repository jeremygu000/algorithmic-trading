"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import ToggleButton from "@mui/material/ToggleButton";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import CloseIcon from "@mui/icons-material/Close";
import { createChart, CandlestickSeries, HistogramSeries } from "lightweight-charts";
import { useThemeMode } from "@/components/ThemeProvider";

const API_BASE = "http://localhost:8300";

type Interval = "daily" | "weekly" | "monthly";

interface Candle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface OhlcvResponse {
  symbol: string;
  interval: string;
  count: number;
  candles: Candle[];
}

interface KlineModalProps {
  open: boolean;
  onClose: () => void;
  symbol: string;
  symbolName?: string;
}

export default function KlineModal({
  open,
  onClose,
  symbol,
  symbolName,
}: KlineModalProps) {
  const { mode } = useThemeMode();
  const [interval, setInterval] = useState<Interval>("daily");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || !symbol) return;

    const controller = new AbortController();

    Promise.resolve()
      .then(() => {
        setLoading(true);
        setError(null);
        setCandles([]);
        return fetch(`${API_BASE}/api/stock/${symbol}/ohlcv?interval=${interval}&days=365`, {
          signal: controller.signal,
        });
      })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || `获取K线数据失败 (${res.status})`);
        }
        return res.json() as Promise<OhlcvResponse>;
      })
      .then((data) => {
        setCandles(data.candles ?? []);
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [open, symbol, interval]);

  const createChartInstance = useCallback(() => {
    const container = containerRef.current;
    if (!container || candles.length === 0) return;

    container.innerHTML = "";

    const isLight = mode === "light";
    const bg = isLight ? "#ffffff" : "#111827";
    const textColor = isLight ? "#00162f" : "#e5e9ef";
    const gridColor = isLight ? "#e5e9ef" : "#1e2a3a";
    const upColor = "#36bb80";
    const downColor = "#ff7134";

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 420,
      layout: {
        background: { color: bg },
        textColor,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      rightPriceScale: {
        borderColor: gridColor,
      },
      timeScale: {
        borderColor: gridColor,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor,
      downColor,
      borderUpColor: upColor,
      borderDownColor: downColor,
      wickUpColor: upColor,
      wickDownColor: downColor,
      priceScaleId: "right",
    });

    candleSeries.setData(
      candles.map((c) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
    });

    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    candleSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.25 },
    });

    volumeSeries.setData(
      candles.map((c) => ({
        time: c.time,
        value: c.volume,
        color:
          c.close >= c.open
            ? "rgba(54,187,128,0.5)"
            : "rgba(255,113,52,0.5)",
      }))
    );

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [candles, mode]);

  useEffect(() => {
    const cleanup = createChartInstance();
    return cleanup;
  }, [createChartInstance]);

  const intervalLabel: Record<Interval, string> = {
    daily: "日K",
    weekly: "周K",
    monthly: "月K",
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          bgcolor: "background.paper",
          backgroundImage: "none",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          pb: 1,
          pr: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5 }}>
          <Typography
            component="span"
            sx={{
              fontFamily: "monospace",
              fontWeight: 700,
              fontSize: "1.1rem",
              color: "text.primary",
            }}
          >
            {symbol}
          </Typography>
          {symbolName && (
            <Typography
              component="span"
              variant="body2"
              sx={{ color: "text.secondary" }}
            >
              {symbolName}
            </Typography>
          )}
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <ToggleButtonGroup
            value={interval}
            exclusive
            size="small"
            onChange={(_e, val: Interval | null) => {
              if (val) setInterval(val);
            }}
          >
            {(["daily", "weekly", "monthly"] as Interval[]).map((iv) => (
              <ToggleButton
                key={iv}
                value={iv}
                sx={{
                  "&.Mui-selected": {
                    bgcolor: "#36bb80 !important",
                    color: "#ffffff !important",
                    "&:hover": {
                      bgcolor: "#2aa870 !important",
                    },
                  },
                }}
              >
                {intervalLabel[iv]}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <IconButton onClick={onClose} size="small" sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 2, pt: 1 }}>
        {loading && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 420,
              gap: 2,
            }}
          >
            <CircularProgress size={32} sx={{ color: "#36bb80" }} />
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              加载K线数据...
            </Typography>
          </Box>
        )}

        {!loading && error && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 420,
              flexDirection: "column",
              gap: 1,
            }}
          >
            <Typography variant="body1" sx={{ color: "error.main" }}>
              加载失败
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {error}
            </Typography>
          </Box>
        )}

        {!loading && !error && candles.length === 0 && (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: 420,
            }}
          >
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              暂无数据
            </Typography>
          </Box>
        )}

        <Box
          ref={containerRef}
          sx={{
            width: "100%",
            height: 420,
            display: loading || error || candles.length === 0 ? "none" : "block",
          }}
        />
      </DialogContent>
    </Dialog>
  );
}
