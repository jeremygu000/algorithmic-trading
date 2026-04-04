"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import CircularProgress from "@mui/material/CircularProgress";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Chip from "@mui/material/Chip";
import MenuItem from "@mui/material/MenuItem";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import Sidebar from "@/components/Sidebar";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";

interface Account {
  account_id: string;
  status: string;
  currency: string;
  cash: string;
  portfolio_value: string;
  equity: string;
  buying_power: string;
  pattern_day_trader: boolean;
  trading_blocked: boolean;
}

interface Position {
  symbol: string;
  qty: string;
  avg_entry_price: string;
  market_value: string;
  cost_basis: string;
  unrealized_pl: string;
  unrealized_plpc: string;
  current_price: string;
}

interface Order {
  order_id: string;
  client_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  qty: string;
  status: string;
  filled_qty: string;
  filled_avg_price: string | null;
  limit_price: string | null;
  stop_price: string | null;
  error?: string;
}

type OrderTab = "open" | "closed" | "all";
type OrderType = "market" | "limit" | "bracket";
type Side = "buy" | "sell";

const WS_URL = "ws://localhost:8300/ws/trades";
const WS_RECONNECT_BASE = 1000;
const WS_RECONNECT_MAX = 30000;

interface TradeEvent {
  type: "trade_update" | "ping";
  event?: string;
  order?: {
    order_id: string | null;
    symbol: string | null;
    side: string | null;
    status: string | null;
    filled_qty: string | null;
    filled_avg_price: string | null;
  };
  fill_price?: string;
  fill_qty?: string;
  position_qty?: string;
  ts?: number;
}

const EVENT_LABELS: Record<string, string> = {
  new: "新订单已提交",
  accepted: "订单已接受",
  fill: "订单已成交",
  partial_fill: "部分成交",
  canceled: "订单已取消",
  expired: "订单已过期",
  rejected: "订单被拒绝",
  replaced: "订单已替换",
  done_for_day: "今日完成",
};

interface TradeForm {
  symbol: string;
  qty: string;
  side: Side;
  order_type: OrderType;
  limit_price: string;
  stop_loss_price: string;
  take_profit_price: string;
}

interface ConfirmDialogState {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
}

function fmtMoney(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

function fmtNum(value: string | number, decimals = 2): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "—";
  return n.toFixed(decimals);
}

function plColor(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "text.primary";
  return n >= 0 ? "#36bb80" : "#ff7134";
}

function plSign(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(n)) return "";
  return n >= 0 ? "+" : "";
}

function StatBox({
  label,
  value,
  valueColor,
  large,
}: {
  label: string;
  value: string;
  valueColor?: string;
  large?: boolean;
}) {
  return (
    <Box
      sx={{
        bgcolor: "action.hover",
        borderRadius: 1.5,
        p: large ? 2 : 1.5,
        border: "1px solid",
        borderColor: "divider",
        textAlign: "center",
      }}
    >
      <Typography
        sx={{
          color: "text.disabled",
          fontSize: "0.65rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          mb: 0.5,
        }}
      >
        {label}
      </Typography>
      <Typography
        sx={{
          fontFamily: "monospace",
          fontWeight: 600,
          fontSize: large ? "1.1rem" : "0.9rem",
          color: valueColor ?? "text.primary",
        }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function LoadingState({ message }: { message: string }) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "20vh",
        gap: 2,
      }}
    >
      <CircularProgress size={36} />
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {message}
      </Typography>
    </Box>
  );
}

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
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
        加载失败
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 3 }}>
        {message}
      </Typography>
      <Button variant="outlined" color="error" size="small" onClick={onRetry}>
        重试
      </Button>
    </Box>
  );
}

function SectionHeader({ icon, title }: { icon: string; title: string }) {
  return (
    <Typography
      variant="body2"
      sx={{
        fontWeight: 700,
        color: "text.primary",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontSize: "0.75rem",
        display: "flex",
        alignItems: "center",
        gap: 0.75,
      }}
    >
      {icon} {title}
    </Typography>
  );
}

function AccountOverview({
  account,
  loading,
  error,
  onRetry,
}: {
  account: Account | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) return <LoadingState message="加载账户信息..." />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (!account) return null;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2.5,
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          <SectionHeader icon="💼" title="账户总览" />
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Chip
              label="📝 Paper Trading"
              size="small"
              sx={{
                fontFamily: "monospace",
                fontSize: "0.7rem",
                bgcolor: "rgba(59,137,255,0.12)",
                color: "#3b89ff",
                border: "1px solid rgba(59,137,255,0.3)",
                fontWeight: 600,
              }}
            />
            <Chip
              label={account.status.toUpperCase()}
              size="small"
              sx={{
                fontFamily: "monospace",
                fontSize: "0.7rem",
                bgcolor:
                  account.status === "ACTIVE"
                    ? "rgba(54,187,128,0.12)"
                    : "rgba(255,113,52,0.12)",
                color: account.status === "ACTIVE" ? "#36bb80" : "#ff7134",
                border: `1px solid ${account.status === "ACTIVE" ? "rgba(54,187,128,0.3)" : "rgba(255,113,52,0.3)"}`,
                fontWeight: 600,
              }}
            />
            {account.trading_blocked && (
              <Chip
                label="交易已冻结"
                size="small"
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.7rem",
                  bgcolor: "rgba(211,47,47,0.12)",
                  color: "error.main",
                  border: "1px solid rgba(211,47,47,0.3)",
                  fontWeight: 600,
                }}
              />
            )}
          </Box>
        </Box>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr 1fr",
              sm: "1fr 1fr 1fr 1fr",
            },
            gap: 1.5,
          }}
        >
          <StatBox label="资产总值" value={fmtMoney(account.equity)} large />
          <StatBox
            label="购买力"
            value={fmtMoney(account.buying_power)}
            large
            valueColor="#3b89ff"
          />
          <StatBox label="现金" value={fmtMoney(account.cash)} large />
          <StatBox
            label="持仓市值"
            value={fmtMoney(account.portfolio_value)}
            large
          />
        </Box>
        {account.pattern_day_trader && (
          <Box
            sx={{
              mt: 2,
              px: 2,
              py: 1,
              bgcolor: "rgba(255,188,50,0.08)",
              border: "1px solid rgba(255,188,50,0.25)",
              borderRadius: 1.5,
            }}
          >
            <Typography
              variant="caption"
              sx={{ color: "#fdbc2a", fontFamily: "monospace" }}
            >
              ⚠ PDT（Pattern Day Trader）账户 — 每5个交易日最多3次日内交易
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function PositionsTable({
  positions,
  loading,
  error,
  onRetry,
  onClosePosition,
}: {
  positions: Position[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onClosePosition: (symbol: string) => void;
}) {
  if (loading) return <LoadingState message="加载持仓中..." />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2.5,
          }}
        >
          <SectionHeader icon="📊" title={`持仓明细（${positions.length}）`} />
        </Box>

        {positions.length === 0 ? (
          <Box
            sx={{
              bgcolor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
            }}
          >
            <Typography sx={{ fontSize: "2.5rem", opacity: 0.2, mb: 2 }}>
              📭
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              暂无持仓
            </Typography>
          </Box>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Box
              component="table"
              sx={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.8rem",
              }}
            >
              <Box component="thead">
                <Box component="tr">
                  {[
                    "代码",
                    "数量",
                    "均价",
                    "现价",
                    "市值",
                    "未实现盈亏",
                    "盈亏%",
                    "操作",
                  ].map((h) => (
                    <Box
                      key={h}
                      component="th"
                      sx={{
                        textAlign: "left",
                        px: 1.5,
                        py: 1,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        color: "text.disabled",
                        fontWeight: 600,
                        fontSize: "0.7rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </Box>
                  ))}
                </Box>
              </Box>
              <Box component="tbody">
                {positions.map((p) => {
                  const pl = parseFloat(p.unrealized_pl);
                  const plpc = parseFloat(p.unrealized_plpc);
                  return (
                    <Box
                      key={p.symbol}
                      component="tr"
                      sx={{
                        "&:hover": { bgcolor: "action.hover" },
                        borderBottom: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Box
                        component="td"
                        sx={{ px: 1.5, py: 1.5, whiteSpace: "nowrap" }}
                      >
                        <Typography
                          sx={{
                            fontWeight: 700,
                            fontSize: "0.85rem",
                            color: "text.primary",
                            fontFamily: "monospace",
                          }}
                        >
                          {p.symbol}
                        </Typography>
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          color: "text.secondary",
                        }}
                      >
                        {fmtNum(p.qty, 0)}
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          color: "text.secondary",
                        }}
                      >
                        {fmtMoney(p.avg_entry_price)}
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          color: "text.primary",
                          fontWeight: 600,
                        }}
                      >
                        {fmtMoney(p.current_price)}
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          color: "text.primary",
                        }}
                      >
                        {fmtMoney(p.market_value)}
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          fontWeight: 600,
                          color: plColor(pl),
                        }}
                      >
                        {plSign(pl)}
                        {fmtMoney(p.unrealized_pl)}
                      </Box>
                      <Box
                        component="td"
                        sx={{
                          px: 1.5,
                          py: 1.5,
                          fontFamily: "monospace",
                          fontWeight: 600,
                          color: plColor(plpc),
                        }}
                      >
                        {plSign(plpc)}
                        {(plpc * 100).toFixed(2)}%
                      </Box>
                      <Box component="td" sx={{ px: 1.5, py: 1 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => onClosePosition(p.symbol)}
                          sx={{
                            fontSize: "0.7rem",
                            py: 0.25,
                            px: 1.25,
                            borderColor: "#ff7134",
                            color: "#ff7134",
                            "&:hover": {
                              borderColor: "#ff7134",
                              bgcolor: "rgba(255,113,52,0.08)",
                            },
                          }}
                        >
                          平仓
                        </Button>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function OrdersSection({
  orders,
  loading,
  error,
  orderTab,
  onTabChange,
  onRetry,
  onCancelOrder,
}: {
  orders: Order[];
  loading: boolean;
  error: string | null;
  orderTab: OrderTab;
  onTabChange: (tab: OrderTab) => void;
  onRetry: () => void;
  onCancelOrder: (orderId: string) => void;
}) {
  const statusLabel: Record<string, string> = {
    new: "新建",
    partially_filled: "部分成交",
    filled: "已成交",
    done_for_day: "当日结束",
    canceled: "已取消",
    expired: "已过期",
    replaced: "已替换",
    pending_cancel: "取消中",
    pending_replace: "替换中",
    held: "暂挂",
    accepted: "已接受",
    pending_new: "待提交",
    accepted_for_bidding: "竞价中",
    stopped: "已停止",
    rejected: "已拒绝",
    suspended: "已暂停",
    calculated: "结算中",
  };

  const sideColor = (side: string) =>
    side === "buy" ? "#36bb80" : "#ff7134";
  const sideLabel = (side: string) => (side === "buy" ? "买入" : "卖出");
  const orderTypeLabel: Record<string, string> = {
    market: "市价",
    limit: "限价",
    stop: "止损",
    stop_limit: "止损限价",
    trailing_stop: "追踪止损",
    bracket: "括号单",
  };

  const isOpenStatus = (s: string) =>
    [
      "new",
      "partially_filled",
      "accepted",
      "pending_new",
      "held",
      "accepted_for_bidding",
    ].includes(s);

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 3,
          pt: 3,
          pb: 1,
        }}
      >
        <SectionHeader icon="📋" title="订单记录" />
      </Box>

      <Tabs
        value={orderTab}
        onChange={(_e, v: OrderTab) => onTabChange(v)}
        sx={{
          px: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          "& .MuiTab-root": {
            fontSize: "0.8rem",
            fontWeight: 500,
            minHeight: 44,
            textTransform: "none",
          },
          "& .Mui-selected": {
            color: "#36bb80 !important",
            fontWeight: 700,
          },
          "& .MuiTabs-indicator": {
            bgcolor: "#36bb80",
          },
        }}
      >
        <Tab label="进行中" value="open" />
        <Tab label="已完成" value="closed" />
        <Tab label="全部" value="all" />
      </Tabs>

      <CardContent sx={{ p: 3 }}>
        {loading ? (
          <LoadingState message="加载订单中..." />
        ) : error ? (
          <ErrorState message={error} onRetry={onRetry} />
        ) : orders.length === 0 ? (
          <Box
            sx={{
              bgcolor: "background.paper",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
              p: 5,
              textAlign: "center",
            }}
          >
            <Typography sx={{ fontSize: "2.5rem", opacity: 0.2, mb: 2 }}>
              📂
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              暂无订单记录
            </Typography>
          </Box>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Box
              component="table"
              sx={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.8rem",
              }}
            >
              <Box component="thead">
                <Box component="tr">
                  {[
                    "代码",
                    "方向",
                    "类型",
                    "数量",
                    "已成交",
                    "均价",
                    "限价",
                    "状态",
                    "操作",
                  ].map((h) => (
                    <Box
                      key={h}
                      component="th"
                      sx={{
                        textAlign: "left",
                        px: 1.5,
                        py: 1,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        color: "text.disabled",
                        fontWeight: 600,
                        fontSize: "0.7rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </Box>
                  ))}
                </Box>
              </Box>
              <Box component="tbody">
                {orders.map((o) => (
                  <Box
                    key={o.order_id}
                    component="tr"
                    sx={{
                      "&:hover": { bgcolor: "action.hover" },
                      borderBottom: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    <Box
                      component="td"
                      sx={{ px: 1.5, py: 1.5, whiteSpace: "nowrap" }}
                    >
                      <Typography
                        sx={{
                          fontWeight: 700,
                          fontSize: "0.85rem",
                          color: "text.primary",
                          fontFamily: "monospace",
                        }}
                      >
                        {o.symbol}
                      </Typography>
                    </Box>
                    <Box component="td" sx={{ px: 1.5, py: 1.5 }}>
                      <Typography
                        sx={{
                          fontFamily: "monospace",
                          fontWeight: 600,
                          fontSize: "0.8rem",
                          color: sideColor(o.side),
                        }}
                      >
                        {sideLabel(o.side)}
                      </Typography>
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        px: 1.5,
                        py: 1.5,
                        fontFamily: "monospace",
                        color: "text.secondary",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {orderTypeLabel[o.order_type] ?? o.order_type}
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        px: 1.5,
                        py: 1.5,
                        fontFamily: "monospace",
                        color: "text.primary",
                      }}
                    >
                      {fmtNum(o.qty, 0)}
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        px: 1.5,
                        py: 1.5,
                        fontFamily: "monospace",
                        color: "text.secondary",
                      }}
                    >
                      {fmtNum(o.filled_qty, 0)}
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        px: 1.5,
                        py: 1.5,
                        fontFamily: "monospace",
                        color: "text.secondary",
                      }}
                    >
                      {o.filled_avg_price ? fmtMoney(o.filled_avg_price) : "—"}
                    </Box>
                    <Box
                      component="td"
                      sx={{
                        px: 1.5,
                        py: 1.5,
                        fontFamily: "monospace",
                        color: "text.secondary",
                      }}
                    >
                      {o.limit_price ? fmtMoney(o.limit_price) : "—"}
                    </Box>
                    <Box component="td" sx={{ px: 1.5, py: 1.5 }}>
                      <Chip
                        label={statusLabel[o.status] ?? o.status}
                        size="small"
                        sx={{
                          fontFamily: "monospace",
                          fontSize: "0.65rem",
                          height: 20,
                          bgcolor: isOpenStatus(o.status)
                            ? "rgba(59,137,255,0.1)"
                            : o.status === "filled"
                              ? "rgba(54,187,128,0.1)"
                              : "rgba(0,0,0,0.05)",
                          color: isOpenStatus(o.status)
                            ? "#3b89ff"
                            : o.status === "filled"
                              ? "#36bb80"
                              : "text.secondary",
                        }}
                      />
                    </Box>
                    <Box component="td" sx={{ px: 1.5, py: 1 }}>
                      {isOpenStatus(o.status) ? (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => onCancelOrder(o.order_id)}
                          sx={{
                            fontSize: "0.7rem",
                            py: 0.25,
                            px: 1.25,
                            borderColor: "#ff7134",
                            color: "#ff7134",
                            "&:hover": {
                              borderColor: "#ff7134",
                              bgcolor: "rgba(255,113,52,0.08)",
                            },
                          }}
                        >
                          取消订单
                        </Button>
                      ) : (
                        <Typography
                          variant="caption"
                          sx={{ color: "text.disabled" }}
                        >
                          —
                        </Typography>
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function QuickTradeForm({
  onOrderSubmitted,
}: {
  onOrderSubmitted: () => void;
}) {
  const defaultForm: TradeForm = {
    symbol: "",
    qty: "",
    side: "buy",
    order_type: "market",
    limit_price: "",
    stop_loss_price: "",
    take_profit_price: "",
  };

  const [form, setForm] = useState<TradeForm>(defaultForm);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  function setField<K extends keyof TradeForm>(key: K, value: TradeForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit() {
    setSubmitError(null);

    const symbol = form.symbol.trim().toUpperCase();
    if (!symbol) {
      setSubmitError("请输入股票代码");
      return;
    }
    const qty = parseFloat(form.qty);
    if (isNaN(qty) || qty <= 0) {
      setSubmitError("请输入有效数量");
      return;
    }
    if (form.order_type === "limit" || form.order_type === "bracket") {
      if (!form.limit_price || isNaN(parseFloat(form.limit_price))) {
        setSubmitError("请输入限价");
        return;
      }
    }
    if (form.order_type === "bracket") {
      if (!form.stop_loss_price || isNaN(parseFloat(form.stop_loss_price))) {
        setSubmitError("请输入止损价");
        return;
      }
      if (
        !form.take_profit_price ||
        isNaN(parseFloat(form.take_profit_price))
      ) {
        setSubmitError("请输入止盈价");
        return;
      }
    }

    const body: Record<string, string | number> = {
      symbol,
      side: form.side,
      qty,
      order_type: form.order_type,
    };
    if (form.order_type === "limit" || form.order_type === "bracket") {
      body.limit_price = parseFloat(form.limit_price);
    }
    if (form.order_type === "bracket") {
      body.stop_loss_price = parseFloat(form.stop_loss_price);
      body.take_profit_price = parseFloat(form.take_profit_price);
    }

    setSubmitting(true);
    fetch(`${API_BASE}/api/trade/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) {
          const errBody = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(errBody?.detail || "下单失败");
        }
        return res.json();
      })
      .then(() => {
        setSuccessMsg(
          `${form.side === "buy" ? "买入" : "卖出"} ${symbol} × ${qty} 下单成功`
        );
        setForm(defaultForm);
        onOrderSubmitted();
      })
      .catch((e: unknown) => {
        setSubmitError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setSubmitting(false));
  }

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ mb: 2.5 }}>
          <SectionHeader icon="⚡" title="快速下单" />
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "1fr 1fr",
              md: "1fr 1fr 1fr 1fr",
            },
            gap: 2,
            alignItems: "flex-start",
          }}
        >
          <TextField
            label="股票代码"
            placeholder="例：AAPL"
            size="small"
            value={form.symbol}
            onChange={(e) => setField("symbol", e.target.value.toUpperCase())}
            slotProps={{
              input: { style: { fontFamily: "monospace", fontWeight: 700 } },
            }}
          />

          <TextField
            label="数量（股）"
            placeholder="例：10"
            size="small"
            type="number"
            value={form.qty}
            onChange={(e) => setField("qty", e.target.value)}
            slotProps={{
              input: { style: { fontFamily: "monospace" } },
            }}
          />

          <TextField
            select
            label="方向"
            size="small"
            value={form.side}
            onChange={(e) => setField("side", e.target.value as Side)}
          >
            <MenuItem value="buy">
              <Typography sx={{ color: "#36bb80", fontWeight: 600 }}>
                买入
              </Typography>
            </MenuItem>
            <MenuItem value="sell">
              <Typography sx={{ color: "#ff7134", fontWeight: 600 }}>
                卖出
              </Typography>
            </MenuItem>
          </TextField>

          <TextField
            select
            label="订单类型"
            size="small"
            value={form.order_type}
            onChange={(e) =>
              setField("order_type", e.target.value as OrderType)
            }
          >
            <MenuItem value="market">市价单</MenuItem>
            <MenuItem value="limit">限价单</MenuItem>
            <MenuItem value="bracket">括号单（含止损/止盈）</MenuItem>
          </TextField>
        </Box>

        {(form.order_type === "limit" || form.order_type === "bracket") && (
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: form.order_type === "bracket" ? "1fr 1fr 1fr" : "1fr",
              },
              gap: 2,
              mt: 2,
            }}
          >
            <TextField
              label="限价（USD）"
              placeholder="例：150.00"
              size="small"
              type="number"
              value={form.limit_price}
              onChange={(e) => setField("limit_price", e.target.value)}
              slotProps={{
                input: { style: { fontFamily: "monospace" } },
              }}
            />
            {form.order_type === "bracket" && (
              <>
                <TextField
                  label="止损价（USD）"
                  placeholder="例：145.00"
                  size="small"
                  type="number"
                  value={form.stop_loss_price}
                  onChange={(e) => setField("stop_loss_price", e.target.value)}
                  slotProps={{
                    input: { style: { fontFamily: "monospace" } },
                  }}
                />
                <TextField
                  label="止盈价（USD）"
                  placeholder="例：160.00"
                  size="small"
                  type="number"
                  value={form.take_profit_price}
                  onChange={(e) =>
                    setField("take_profit_price", e.target.value)
                  }
                  slotProps={{
                    input: { style: { fontFamily: "monospace" } },
                  }}
                />
              </>
            )}
          </Box>
        )}

        {submitError && (
          <Box
            sx={{
              mt: 2,
              px: 2,
              py: 1.5,
              bgcolor: "rgba(211,47,47,0.08)",
              border: "1px solid rgba(211,47,47,0.25)",
              borderRadius: 1.5,
            }}
          >
            <Typography
              variant="caption"
              sx={{ color: "error.main", fontFamily: "monospace" }}
            >
              ✕ {submitError}
            </Typography>
          </Box>
        )}

        <Box sx={{ mt: 2.5, display: "flex", gap: 1.5, flexWrap: "wrap" }}>
          <Button
            variant="contained"
            disabled={submitting}
            onClick={handleSubmit}
            sx={{
              bgcolor: form.side === "buy" ? "#36bb80" : "#ff7134",
              "&:hover": {
                bgcolor: form.side === "buy" ? "#2daa73" : "#e85f25",
              },
              fontWeight: 700,
              px: 4,
              minWidth: 120,
            }}
          >
            {submitting ? (
              <CircularProgress size={16} sx={{ color: "#fff" }} />
            ) : form.side === "buy" ? (
              "买入下单"
            ) : (
              "卖出下单"
            )}
          </Button>
          <Button
            variant="outlined"
            disabled={submitting}
            onClick={() => {
              setForm(defaultForm);
              setSubmitError(null);
            }}
            sx={{ px: 2 }}
          >
            重置
          </Button>
        </Box>

        {successMsg && (
          <Snackbar
            open
            autoHideDuration={4000}
            onClose={() => setSuccessMsg(null)}
            anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          >
            <Alert
              onClose={() => setSuccessMsg(null)}
              severity="success"
              sx={{ fontFamily: "monospace" }}
            >
              ✓ {successMsg}
            </Alert>
          </Snackbar>
        )}
      </CardContent>
    </Card>
  );
}

export default function TradingPage() {
  const [account, setAccount] = useState<Account | null>(null);
  const [accountLoading, setAccountLoading] = useState(true);
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountTick, setAccountTick] = useState(0);

  const [positions, setPositions] = useState<Position[]>([]);
  const [positionsLoading, setPositionsLoading] = useState(true);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [positionsTick, setPositionsTick] = useState(0);

  const [orders, setOrders] = useState<Order[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(true);
  const [ordersError, setOrdersError] = useState<string | null>(null);
  const [orderTab, setOrderTab] = useState<OrderTab>("open");
  const [ordersTick, setOrdersTick] = useState(0);

  const [wsConnected, setWsConnected] = useState(false);
  const [tradeToast, setTradeToast] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(WS_RECONNECT_BASE);

  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
    title: "",
    message: "",
    onConfirm: () => {},
  });

  const handleTradeEvent = useCallback((evt: TradeEvent) => {
    if (evt.type === "ping") {
      wsRef.current?.send("pong");
      return;
    }
    if (evt.type === "trade_update" && evt.event) {
      const label = EVENT_LABELS[evt.event] ?? evt.event;
      const sym = evt.order?.symbol ?? "";
      setTradeToast(`${sym} ${label}`);
      setPositionsTick((n) => n + 1);
      setOrdersTick((n) => n + 1);
    }
  }, []);

  useEffect(() => {
    let unmounted = false;

    function connect() {
      if (unmounted) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        backoffRef.current = WS_RECONNECT_BASE;
      };
      ws.onclose = () => {
        setWsConnected(false);
        if (!unmounted) {
          reconnectTimer.current = setTimeout(() => {
            backoffRef.current = Math.min(backoffRef.current * 2, WS_RECONNECT_MAX);
            connect();
          }, backoffRef.current);
        }
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (e) => {
        try {
          handleTradeEvent(JSON.parse(e.data) as TradeEvent);
        } catch { /* ignore malformed messages */ }
      };
    }

    connect();
    return () => {
      unmounted = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [handleTradeEvent]);

  const reloadAccount = () => {
    setAccountLoading(true);
    setAccountError(null);
    setAccountTick((n) => n + 1);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/trade/account`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "账户信息请求失败");
        }
        return res.json() as Promise<Account>;
      })
      .then(setAccount)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setAccountError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setAccountLoading(false));

    return () => controller.abort();
  }, [accountTick]);

  const reloadPositions = () => {
    setPositionsLoading(true);
    setPositionsError(null);
    setPositionsTick((n) => n + 1);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/trade/positions`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "持仓信息请求失败");
        }
        return res.json() as Promise<Position[]>;
      })
      .then(setPositions)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setPositionsError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setPositionsLoading(false));

    return () => controller.abort();
  }, [positionsTick]);

  const reloadOrders = () => {
    setOrdersLoading(true);
    setOrdersError(null);
    setOrdersTick((n) => n + 1);
  };

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_BASE}/api/trade/orders?status=${orderTab}&limit=50`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = (await res.json().catch(() => null)) as {
            detail?: string;
          } | null;
          throw new Error(body?.detail || "订单信息请求失败");
        }
        return res.json() as Promise<Order[]>;
      })
      .then(setOrders)
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return;
        setOrdersError(e instanceof Error ? e.message : "未知错误");
      })
      .finally(() => setOrdersLoading(false));

    return () => controller.abort();
  }, [orderTab, ordersTick]);

  function handleClosePosition(symbol: string) {
    setConfirmDialog({
      open: true,
      title: "确认平仓",
      message: `确定要平仓 ${symbol} 的全部持仓吗？此操作将按市价卖出所有股份。`,
      onConfirm: () => {
        setConfirmDialog((prev) => ({ ...prev, open: false }));
        fetch(`${API_BASE}/api/trade/positions/${symbol}`, {
          method: "DELETE",
        })
          .then(async (res) => {
            if (!res.ok) {
              const body = (await res.json().catch(() => null)) as {
                detail?: string;
              } | null;
              throw new Error(body?.detail || "平仓请求失败");
            }
            return res.json();
          })
          .then(() => {
            reloadPositions();
          })
          .catch(() => {});
      },
    });
  }

  function handleCancelOrder(orderId: string) {
    setConfirmDialog({
      open: true,
      title: "确认取消订单",
      message: `确定要取消订单 ${orderId.slice(0, 8)}... 吗？`,
      onConfirm: () => {
        setConfirmDialog((prev) => ({ ...prev, open: false }));
        fetch(`${API_BASE}/api/trade/orders/${orderId}`, {
          method: "DELETE",
        })
          .then(async (res) => {
            if (!res.ok) {
              const body = (await res.json().catch(() => null)) as {
                detail?: string;
              } | null;
              throw new Error(body?.detail || "取消订单失败");
            }
            return res.json();
          })
          .then(() => {
            reloadOrders();
          })
          .catch(() => {});
      },
    });
  }

  return (
    <Box
      sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}
    >
      <Sidebar />
      <Box
        component="main"
        sx={{ flex: 1, overflowY: "auto", height: "100vh" }}
      >
        <HeroBanner
          title="ETF Trend"
          subtitle="交易中心"
          description="Alpaca Paper Trading · 账户管理 · 一键下单"
        />

        <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            px: 4,
            pt: 1,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Chip
            size="small"
            label={wsConnected ? "实时连接" : "离线"}
            sx={{
              fontSize: "0.7rem",
              height: 22,
              bgcolor: wsConnected
                ? "rgba(54,187,128,0.15)"
                : "rgba(255,113,52,0.15)",
              color: wsConnected ? "#36bb80" : "#ff7134",
              fontWeight: 600,
              "& .MuiChip-icon": { fontSize: "0.6rem" },
            }}
            icon={
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  bgcolor: wsConnected ? "#36bb80" : "#ff7134",
                  ml: 0.8,
                }}
              />
            }
          />
        </Box>

        <Box
          sx={{
            maxWidth: 1100,
            mx: "auto",
            px: 4,
            py: 5,
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <AccountOverview
            account={account}
            loading={accountLoading}
            error={accountError}
            onRetry={reloadAccount}
          />

          <QuickTradeForm
            onOrderSubmitted={reloadOrders}
          />

          <PositionsTable
            positions={positions}
            loading={positionsLoading}
            error={positionsError}
            onRetry={reloadPositions}
            onClosePosition={handleClosePosition}
          />

          <OrdersSection
            orders={orders}
            loading={ordersLoading}
            error={ordersError}
            orderTab={orderTab}
            onTabChange={(tab) => {
              setOrdersLoading(true);
              setOrdersError(null);
              setOrderTab(tab);
            }}
            onRetry={reloadOrders}
            onCancelOrder={handleCancelOrder}
          />
        </Box>
      </Box>

      <Dialog
        open={confirmDialog.open}
        onClose={() =>
          setConfirmDialog((prev) => ({ ...prev, open: false }))
        }
        PaperProps={{
          sx: {
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          },
        }}
      >
        <DialogTitle
          sx={{ fontWeight: 700, color: "text.primary", fontSize: "1rem" }}
        >
          {confirmDialog.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText
            sx={{ color: "text.secondary", fontSize: "0.875rem" }}
          >
            {confirmDialog.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() =>
              setConfirmDialog((prev) => ({ ...prev, open: false }))
            }
          >
            取消
          </Button>
          <Button
            size="small"
            variant="contained"
            onClick={confirmDialog.onConfirm}
            sx={{
              bgcolor: "#ff7134",
              "&:hover": { bgcolor: "#e85f25" },
              fontWeight: 700,
            }}
          >
            确认
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!tradeToast}
        autoHideDuration={4000}
        onClose={() => setTradeToast(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          severity="info"
          variant="filled"
          onClose={() => setTradeToast(null)}
          sx={{ fontWeight: 600, fontSize: "0.85rem" }}
        >
          {tradeToast}
        </Alert>
      </Snackbar>
    </Box>
  );
}
