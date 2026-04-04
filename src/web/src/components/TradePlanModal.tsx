"use client";

import { useEffect, useState } from "react";
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
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import CloseIcon from "@mui/icons-material/Close";

const API_BASE = "http://localhost:8300";

type OrderType = "market" | "limit" | "bracket";

interface EntryLevels {
  aggressive: number;
  moderate: number;
  conservative: number;
}

interface StopLevels {
  tight: number;
  normal: number;
  loose: number;
  current: number | null;
}

interface TakeProfitLevels {
  tp1: number;
  tp2: number;
  tp3: number;
}

interface TradePlan {
  symbol: string;
  action: string;
  target_weight: number;
  current_price: number;
  entry_levels: EntryLevels;
  stop_levels: StopLevels;
  take_profit_levels: TakeProfitLevels;
  atr: number;
  trailing_stop_pct: number;
  recommended_hold_days: number;
  reason: string;
}

interface OrderResult {
  order_id: string;
  client_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  qty: number;
  status: string;
  filled_qty: number | null;
  filled_avg_price: number | null;
  limit_price: number | null;
  stop_price: number | null;
  error: string | null;
}

interface ExecuteResult {
  plan: TradePlan;
  order: OrderResult;
}

interface TradePlanModalProps {
  open: boolean;
  onClose: () => void;
  symbol: string;
  stockName: string;
  latestPrice: number;
}

function PriceRow({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", py: 0.5 }}>
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        {label}
      </Typography>
      <Typography
        variant="caption"
        sx={{ fontFamily: "monospace", fontWeight: 600, color: color ?? "text.primary" }}
      >
        ${value.toFixed(2)}
      </Typography>
    </Box>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="caption"
      sx={{
        color: "text.disabled",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 600,
        display: "block",
        mb: 0.5,
        mt: 1.5,
      }}
    >
      {children}
    </Typography>
  );
}

export default function TradePlanModal({
  open,
  onClose,
  symbol,
  stockName,
  latestPrice,
}: TradePlanModalProps) {
  const [plan, setPlan] = useState<TradePlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orderType, setOrderType] = useState<OrderType>("bracket");
  const [executing, setExecuting] = useState(false);
  const [execResult, setExecResult] = useState<ExecuteResult | null>(null);
  const [execError, setExecError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !symbol) return;

    const controller = new AbortController();

    Promise.resolve()
      .then(() => {
        setPlan(null);
        setError(null);
        setExecResult(null);
        setExecError(null);
        setLoading(true);
        return fetch(`${API_BASE}/api/trade/plan/${symbol}`, { signal: controller.signal });
      })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || `获取交易计划失败 (${res.status})`);
        }
        return res.json() as Promise<TradePlan>;
      })
      .then((data) => setPlan(data))
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [open, symbol]);

  const handleExecute = () => {
    const controller = new AbortController();
    setExecuting(true);
    setExecResult(null);
    setExecError(null);

    fetch(`${API_BASE}/api/trade/execute-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, order_type: orderType }),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as { detail?: string } | null;
          throw new Error(body?.detail || `执行失败 (${res.status})`);
        }
        return res.json() as Promise<ExecuteResult>;
      })
      .then((data) => setExecResult(data))
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setExecError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setExecuting(false));
  };

  const actionColor = plan?.action === "BUY" ? "#36bb80" : plan?.action === "SELL" ? "#ff7134" : "text.secondary";

  return (
    <Dialog
      open={open}
      onClose={onClose}
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
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5 }}>
          <Typography
            component="span"
            sx={{ fontFamily: "monospace", fontWeight: 700, fontSize: "1.1rem", color: "text.primary" }}
          >
            {symbol}
          </Typography>
          {stockName && (
            <Typography component="span" variant="body2" sx={{ color: "text.secondary" }}>
              {stockName}
            </Typography>
          )}
          <Typography
            component="span"
            sx={{ fontFamily: "monospace", fontWeight: 600, fontSize: "1rem", color: "text.primary", ml: 1 }}
          >
            ${latestPrice.toFixed(2)}
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small" sx={{ color: "text.secondary" }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: 2, pt: 1 }}>
        {loading && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 220, gap: 2 }}>
            <CircularProgress size={28} sx={{ color: "#36bb80" }} />
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              加载交易计划...
            </Typography>
          </Box>
        )}

        {!loading && error && (
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 220, flexDirection: "column", gap: 1 }}>
            <Typography variant="body1" sx={{ color: "error.main" }}>
              加载失败
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {error}
            </Typography>
          </Box>
        )}

        {!loading && !error && plan && (
          <Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
              <Box
                sx={{
                  px: 1.5,
                  py: 0.4,
                  borderRadius: 1,
                  bgcolor:
                    plan.action === "BUY"
                      ? "rgba(54,187,128,0.15)"
                      : plan.action === "SELL"
                      ? "rgba(255,113,52,0.15)"
                      : "action.hover",
                  border: "1px solid",
                  borderColor:
                    plan.action === "BUY"
                      ? "rgba(54,187,128,0.4)"
                      : plan.action === "SELL"
                      ? "rgba(255,113,52,0.4)"
                      : "divider",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{ fontFamily: "monospace", fontWeight: 700, color: actionColor, fontSize: "0.8rem" }}
                >
                  {plan.action}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                目标仓位: <Box component="span" sx={{ fontFamily: "monospace", color: "text.primary" }}>{(plan.target_weight * 100).toFixed(1)}%</Box>
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                建议持有: <Box component="span" sx={{ fontFamily: "monospace", color: "text.primary" }}>{plan.recommended_hold_days} 天</Box>
              </Typography>
            </Box>

            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 2, mb: 2 }}>
              <Box
                sx={{
                  bgcolor: "action.hover",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                  p: 1.5,
                }}
              >
                <SectionLabel>入场价</SectionLabel>
                <PriceRow label="激进" value={plan.entry_levels.aggressive} color="#36bb80" />
                <PriceRow label="稳健" value={plan.entry_levels.moderate} />
                <PriceRow label="保守" value={plan.entry_levels.conservative} />
              </Box>

              <Box
                sx={{
                  bgcolor: "action.hover",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                  p: 1.5,
                }}
              >
                <SectionLabel>止损价</SectionLabel>
                <PriceRow label="紧" value={plan.stop_levels.tight} color="#ff7134" />
                <PriceRow label="标准" value={plan.stop_levels.normal} color="#ff7134" />
                <PriceRow label="宽" value={plan.stop_levels.loose} color="#ff7134" />
              </Box>

              <Box
                sx={{
                  bgcolor: "action.hover",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                  p: 1.5,
                }}
              >
                <SectionLabel>止盈价</SectionLabel>
                <PriceRow label="TP1" value={plan.take_profit_levels.tp1} color="#36bb80" />
                <PriceRow label="TP2" value={plan.take_profit_levels.tp2} color="#36bb80" />
                <PriceRow label="TP3" value={plan.take_profit_levels.tp3} color="#36bb80" />
              </Box>
            </Box>

            <Box sx={{ display: "flex", gap: 3, mb: 2 }}>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                ATR: <Box component="span" sx={{ fontFamily: "monospace", color: "text.primary" }}>{plan.atr.toFixed(2)}</Box>
              </Typography>
              {plan.trailing_stop_pct > 0 && (
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  移动止损: <Box component="span" sx={{ fontFamily: "monospace", color: "text.primary" }}>{(plan.trailing_stop_pct * 100).toFixed(1)}%</Box>
                </Typography>
              )}
            </Box>

            {plan.reason && (
              <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2, lineHeight: 1.6 }}>
                {plan.reason}
              </Typography>
            )}

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

            {execResult && (
              <Box
                sx={{
                  mt: 2,
                  p: 1.5,
                  bgcolor: "rgba(54,187,128,0.08)",
                  border: "1px solid rgba(54,187,128,0.3)",
                  borderRadius: 2,
                }}
              >
                <Typography variant="caption" sx={{ color: "#36bb80", fontWeight: 600, display: "block", mb: 0.5 }}>
                  下单成功
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace", display: "block" }}>
                  订单号: {execResult.order.order_id}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", fontFamily: "monospace", display: "block" }}>
                  数量: {execResult.order.qty} 股 · 状态: {execResult.order.status}
                </Typography>
              </Box>
            )}

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
                <Typography variant="caption" sx={{ color: "#ff7134", fontWeight: 600, display: "block", mb: 0.5 }}>
                  下单失败
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
                  {execError}
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      {!loading && !error && plan && (
        <DialogActions sx={{ px: 2, pb: 2, pt: 0, gap: 1 }}>
          <Button
            variant="outlined"
            size="small"
            onClick={onClose}
            sx={{ color: "text.secondary", borderColor: "divider" }}
          >
            取消
          </Button>
          <Button
            variant="contained"
            size="small"
            disabled={executing || execResult !== null}
            onClick={handleExecute}
            sx={{
              bgcolor: "#36bb80",
              color: "#ffffff",
              "&:hover": { bgcolor: "#2aa870" },
              "&.Mui-disabled": { bgcolor: "action.disabledBackground" },
            }}
          >
            {executing ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <CircularProgress size={14} sx={{ color: "inherit" }} />
                执行中...
              </Box>
            ) : execResult ? (
              "已执行"
            ) : (
              "确认下单"
            )}
          </Button>
        </DialogActions>
      )}
    </Dialog>
  );
}
