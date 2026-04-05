"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import SearchIcon from "@mui/icons-material/Search";
import CandlestickChartIcon from "@mui/icons-material/CandlestickChart";
import HeroBanner from "@/components/HeroBanner";

const API_BASE = "http://localhost:8300";

export default function StockLandingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [symbolOptions, setSymbolOptions] = useState<string[]>([]);

  const qsSymbol = searchParams.get("symbol");
  useEffect(() => {
    if (qsSymbol) {
      router.replace(`/stock/${qsSymbol.toUpperCase()}`);
    }
  }, [qsSymbol, router]);

  const loadSymbols = useCallback(() => {
    fetch(`${API_BASE}/api/symbols`)
      .then(async (res) => {
        if (!res.ok) return;
        const json = (await res.json()) as { symbols: string[] };
        setSymbolOptions(json.symbols || []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadSymbols();
  }, [loadSymbols]);

  if (qsSymbol) return null;

  return (
    <>
      <HeroBanner
        title="ETF Trend"
        subtitle="股票分析"
        description="搜索并选择股票，查看深度技术面分析与交易计划"
      />

      <Box sx={{ maxWidth: 700, mx: "auto", px: 4, py: 8 }}>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
          }}
        >
          <Box
            sx={{
              width: 64,
              height: 64,
              borderRadius: "16px",
              background: "linear-gradient(135deg, #3b89ff 0%, #1a6fe0 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CandlestickChartIcon sx={{ fontSize: 32, color: "#fff" }} />
          </Box>

          <Box sx={{ textAlign: "center" }}>
            <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
              选择股票
            </Typography>
            <Typography sx={{ color: "text.secondary", fontSize: "0.95rem" }}>
              从股票池中搜索代码，进入深度技术分析页面
            </Typography>
          </Box>

          <Autocomplete
            freeSolo
            options={symbolOptions}
            filterOptions={(options, { inputValue }) => {
              const upper = inputValue.toUpperCase();
              if (!upper) return options.slice(0, 20);
              return options.filter((o) => o.startsWith(upper)).slice(0, 20);
            }}
            onChange={(_e, value) => {
              if (value && typeof value === "string") {
                router.push(`/stock/${value.toUpperCase()}`);
              }
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="输入股票代码 (如 NVDA, MSFT, TSLA ...)"
                variant="outlined"
                autoFocus
                InputProps={{
                  ...params.InputProps,
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon sx={{ color: "text.disabled", fontSize: 20 }} />
                    </InputAdornment>
                  ),
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const input = (e.target as HTMLInputElement).value.trim().toUpperCase();
                    if (input) {
                      router.push(`/stock/${input}`);
                    }
                  }
                }}
              />
            )}
            sx={{
              width: "100%",
              maxWidth: 480,
              "& .MuiOutlinedInput-root": {
                borderRadius: 2,
                fontSize: "1rem",
              },
            }}
          />

          <Typography
            variant="caption"
            sx={{ color: "text.disabled", mt: -1 }}
          >
            共 {symbolOptions.length > 0 ? symbolOptions.length.toLocaleString() : "—"} 只股票可供分析
          </Typography>
        </Box>
      </Box>
    </>
  );
}
