"use client";

import { useEffect, useRef, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import IconButton from "@mui/material/IconButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import ToggleButton from "@mui/material/ToggleButton";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import CloseIcon from "@mui/icons-material/Close";

const API_BASE = "http://localhost:8300";

type OrderType = "market" | "limit" | "bracket";
type Phase = "confirm" | "executing" | "results";

interface BatchOrderResult {
  order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  qty: number;
  status: string;
  filled_qty: number | null;
  filled_avg_price: number | null;
  error: string | null;
}

interface BatchResultItem {
  symbol: string;
  plan: object | null;
  order: BatchOrderResult | null;
  error: string | null;
}

interface BatchExecuteResponse {
  total: number;
  success_count: number;
  failure_count: number;
  results: BatchResultItem[];
}

interface WsTradeUpdate {
  type: "trade_update" | "ping";
  event?: string;
  timestamp?: string;
  order?: {
    id: string;
    symbol: string;
    side: string;
    type: string;
    qty: number;
    status: string;
    filled_qty: number;
    filled_avg_price: number | null;
  };
}

interface BatchExecuteModalProps {
  open: boolean;
  onClose: () => void;
  symbols: string[];
}

function statusBadgeStyle(status: string): { bgcolor: string; color: string } {
  switch (status) {
    case "new":
    case "accepted":
    case "pending_new":
      return { bgcolor: "rgba(59,137,255,0.12)", color: "#3b89ff" };
    case "partially_filled":
      return { bgcolor: "rgba(253,188,42,0.15)", color: "#fdbc2a" };
    case "filled":
      return { bgcolor: "rgba(54,187,128,0.12)", color: "#36bb80" };
    case "canceled":
    case "expired":
    case "done_for_day":
      return { bgcolor: "rgba(0,0,0,0.06)", color: "text.secondary" as unknown as string };
    case "rejected":
      return { bgcolor: "rgba(255,113,52,0.12)", color: "#ff7134" };
    default:
      return { bgcolor: "rgba(0,0,0,0.06)", color: "text.secondary" as unknown as string };
  }
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    new: "新建",
    accepted: "已接受",
    pending_new: "待提交",
    partially_filled: "部分成交",
    filled: "已成交",
    canceled: "已取消",
    expired: "已过期",
    done_for_day: "当日结束",
    rejected: "已拒绝",
  };
  return map[status] ?? status;
}

export default function BatchExecuteModal({ open, onClose, symbols }: BatchExecuteModalProps) {
  const [orderType, setOrderType] = useState<OrderType>("bracket");
  const [phase, setPhase] = useState<Phase>("confirm");
  const [batchResult, setBatchResult] = useState<BatchExecuteResponse | null>(null);
  const [execError, setExecError] = useState<string | null>(null);
  const [liveStatuses, setLiveStatuses] = useState<Record<string, string>>({});

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  const connectWs = (trackedIds: Set<string>) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    const ws = new WebSocket(`${API_BASE.replace("http://", "ws://")}/ws/trades`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsTradeUpdate;
        if (msg.type === "ping") {
          ws.send("pong");
          return;
        }
        if (msg.type === "trade_update" && msg.order) {
          const { id, symbol, status } = msg.order;
          if (trackedIds.has(id)) {
            setLiveStatuses((prev) => ({ ...prev, [symbol]: status }));
          }
        }
      } catch { }
    };
    ws.onerror = () => ws.close();
  };

  const handleExecute = () => {
    setPhase("executing");
    setExecError(null);

    fetch(`${API_BASE}/api/trade/batch-execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols, order_type: orderType }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || `批量执行失败 (${res.status})`);
        }
        return res.json() as Promise<BatchExecuteResponse>;
      })
      .then((data) => {
        setBatchResult(data);
        setPhase("results");

        const trackedIds = new Set<string>();
        for (const item of data.results) {
          if (item.order?.order_id) {
            trackedIds.add(item.order.order_id);
          }
        }
        if (trackedIds.size > 0) {
          connectWs(trackedIds);
        }
      })
      .catch((e: unknown) => {
        setExecError(e instanceof Error ? e.message : "未知错误");
        setPhase("confirm");
      });
  };

  const handleClose = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setPhase("confirm");
    setBatchResult(null);
    setExecError(null);
    setLiveStatuses({});
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
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
        <Typography
          component="span"
          sx={{ fontWeight: 700, fontSize: "1.05rem", color: "text.primary" }}
        >
          批量交易
        </Typography>
        <IconButton onClick={handleClose} size="small" sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 2, pt: 1 }}>
        {phase === "confirm" && (
          <Box>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 1.5 }}>
              将对以下 <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 700, color: "text.primary" }}>{symbols.length}</Box> 只股票执行批量建仓：
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 2.5 }}>
              {symbols.map((sym) => (
                <Chip
                  key={sym}
                  label={sym}
                  size="small"
                  sx={{
                    fontFamily: "monospace",
                    fontWeight: 700,
                    bgcolor: "rgba(59,137,255,0.1)",
                    color: "#3b89ff",
                    border: "1px solid rgba(59,137,255,0.3)",
                  }}
                />
              ))}
            </Box>

            <Divider sx={{ mb: 2 }} />

            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                订单类型
              </Typography>
              <ToggleButtonGroup
                value={orderType}
                exclusive
                size="small"
                onChange={(_e, val: OrderType | null) => {
                  if (val) setOrderType(val);
                }}
              >
                {(["market", "limit", "bracket"] as OrderType[]).map((ot) => (
                  <ToggleButton
                    key={ot}
                    value={ot}
                    sx={{
                      px: 1.5,
                      "&.Mui-selected": {
                        bgcolor: "rgba(54,187,128,0.15) !important",
                        borderColor: "rgba(54,187,128,0.4) !important",
                        color: "#36bb80 !important",
                        "&:hover": { bgcolor: "rgba(54,187,128,0.2) !important" },
                      },
                    }}
                  >
                    {ot === "market" ? "市价" : ot === "limit" ? "限价" : "组合"}
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            </Box>

            {execError && (
              <Box
                sx={{
                  mt: 2,
                  p: 1.5,
                  bgcolor: "rgba(255,113,52,0.08)",
                  border: "1px solid rgba(255,113,52,0.3)",
                  borderRadius: 2,
                }}
              >
                <Typography variant="caption" sx={{ color: "#ff7134", fontWeight: 600, display: "block", mb: 0.25 }}>
                  执行失败
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
                  {execError}
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {phase === "executing" && (
          <Box sx={{ py: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
              <CircularProgress size={20} sx={{ color: "#3b89ff" }} />
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                正在批量执行，共 {symbols.length} 只...
              </Typography>
            </Box>
            <LinearProgress
              variant="indeterminate"
              sx={{
                borderRadius: 1,
                bgcolor: "rgba(59,137,255,0.1)",
                "& .MuiLinearProgress-bar": { bgcolor: "#3b89ff" },
              }}
            />
          </Box>
        )}

        {phase === "results" && batchResult && (
          <Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
              <Chip
                label={`成功 ${batchResult.success_count}`}
                size="small"
                sx={{
                  fontFamily: "monospace",
                  fontWeight: 700,
                  bgcolor: "rgba(54,187,128,0.12)",
                  color: "#36bb80",
                  border: "1px solid rgba(54,187,128,0.3)",
                }}
              />
              {batchResult.failure_count > 0 && (
                <Chip
                  label={`失败 ${batchResult.failure_count}`}
                  size="small"
                  sx={{
                    fontFamily: "monospace",
                    fontWeight: 700,
                    bgcolor: "rgba(255,113,52,0.12)",
                    color: "#ff7134",
                    border: "1px solid rgba(255,113,52,0.3)",
                  }}
                />
              )}
              <Chip
                label={`总计 ${batchResult.total}`}
                size="small"
                sx={{
                  fontFamily: "monospace",
                  bgcolor: "action.hover",
                  color: "text.secondary",
                  border: "1px solid",
                  borderColor: "divider",
                }}
              />
            </Box>

            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {batchResult.results.map((item) => {
                const liveStatus = item.order ? (liveStatuses[item.symbol] ?? item.order.status) : null;
                const hasError = item.error || item.order?.error;

                return (
                  <Box
                    key={item.symbol}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1.5,
                      px: 1.5,
                      py: 1,
                      bgcolor: "action.hover",
                      border: "1px solid",
                      borderColor: hasError ? "rgba(255,113,52,0.3)" : "divider",
                      borderRadius: 1.5,
                      flexWrap: "wrap",
                    }}
                  >
                    <Typography
                      sx={{ fontFamily: "monospace", fontWeight: 700, fontSize: "0.85rem", color: "text.primary", minWidth: 60 }}
                    >
                      {item.symbol}
                    </Typography>

                    {item.order && (
                      <>
                        <Typography
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            color: item.order.side === "buy" ? "#36bb80" : "#ff7134",
                          }}
                        >
                          {item.order.side === "buy" ? "买入" : "卖出"}
                        </Typography>
                        <Typography
                          sx={{ fontFamily: "monospace", fontSize: "0.75rem", color: "text.secondary" }}
                        >
                          {item.order.qty} 股
                        </Typography>
                        {liveStatus && (
                          <Chip
                            label={statusLabel(liveStatus)}
                            size="small"
                            sx={{
                              fontFamily: "monospace",
                              fontSize: "0.65rem",
                              height: 20,
                              ...statusBadgeStyle(liveStatus),
                            }}
                          />
                        )}
                      </>
                    )}

                    {hasError && (
                      <Typography
                        variant="caption"
                        sx={{ color: "#ff7134", ml: "auto", maxWidth: 200, textAlign: "right" }}
                      >
                        {item.error ?? item.order?.error}
                      </Typography>
                    )}
                  </Box>
                );
              })}
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 2, pb: 2, pt: 0, gap: 1 }}>
        <Button
          variant="outlined"
          size="small"
          onClick={handleClose}
          sx={{ color: "text.secondary", borderColor: "divider" }}
        >
          {phase === "results" ? "关闭" : "取消"}
        </Button>
        {phase === "confirm" && (
          <Button
            variant="contained"
            size="small"
            onClick={handleExecute}
            sx={{
              bgcolor: "#3b89ff",
              color: "#ffffff",
              "&:hover": { bgcolor: "#2a78ee" },
              fontWeight: 600,
            }}
          >
            确认执行
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
