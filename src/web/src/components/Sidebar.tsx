"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import HomeIcon from "@mui/icons-material/Home";
import PublicIcon from "@mui/icons-material/Public";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import StarIcon from "@mui/icons-material/Star";
import CandlestickChartIcon from "@mui/icons-material/CandlestickChart";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import SearchIcon from "@mui/icons-material/Search";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useThemeMode } from "./ThemeProvider";

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { id: "/", label: "首页", Icon: HomeIcon },
  { id: "/market", label: "市场状态", Icon: PublicIcon },
  { id: "/trend-scan", label: "趋势扫描", Icon: TrendingUpIcon },
  { id: "/picks", label: "个股推荐", Icon: StarIcon },
  { id: "/beauty-shoulder", label: "美人肩", Icon: AutoGraphIcon },
  { id: "/stock/AAPL", label: "股票分析", Icon: CandlestickChartIcon },
] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [searchSymbol, setSearchSymbol] = useState("");
  const { mode, toggleMode } = useThemeMode();

  // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: hydration guard requires one-time sync setState
  useEffect(() => { setMounted(true); }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchSymbol.trim()) {
      router.push(`/stock/${searchSymbol.toUpperCase()}`);
      setSearchSymbol("");
    }
  };

  const isActive = (path: string) => {
    if (path === "/") return pathname === "/";
    if (path.startsWith("/stock/")) return pathname.startsWith("/stock/");
    return pathname === path;
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          bgcolor: "#0f2246",
        },
      }}
    >
      <Box sx={{ px: 2.5, py: 2.5, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: "8px",
              background: "linear-gradient(135deg, #3b89ff 0%, #1a6fe0 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Typography sx={{ color: "#fff", fontWeight: 800, fontSize: "0.875rem" }}>T</Typography>
          </Box>
          <Box>
            <Typography
              sx={{
                color: "#ffffff",
                fontWeight: 700,
                fontSize: "0.9rem",
                lineHeight: 1.2,
              }}
            >
              ETF Trend
            </Typography>
            <Typography
              sx={{
                color: "rgba(255,255,255,0.4)",
                fontSize: "0.65rem",
                fontFamily: "var(--font-geist-mono)",
              }}
            >
              量化分析系统
            </Typography>
          </Box>
        </Box>
      </Box>

      <List sx={{ flex: 1, px: 1.5, py: 2 }}>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.id);
          const { Icon } = item;
          return (
            <ListItemButton
              key={item.id}
              component={Link}
              href={item.id}
              selected={active}
              sx={{
                borderRadius: "8px",
                mb: 0.5,
                px: 1.5,
                py: 1,
                color: active ? "#3b89ff" : "rgba(255,255,255,0.55)",
                bgcolor: active ? "rgba(59,137,255,0.12) !important" : "transparent",
                "&:hover": {
                  bgcolor: "rgba(255,255,255,0.06) !important",
                  color: "rgba(255,255,255,0.85)",
                },
                "&.Mui-selected": {
                  bgcolor: "rgba(59,137,255,0.12)",
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 36,
                  color: active ? "#3b89ff" : "rgba(255,255,255,0.4)",
                }}
              >
                <Icon sx={{ fontSize: "1.1rem" }} />
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{
                  fontSize: "0.875rem",
                  fontWeight: active ? 600 : 400,
                  color: "inherit",
                }}
              />
              {active && (
                <Box
                  sx={{
                    width: 3,
                    height: 20,
                    borderRadius: "2px",
                    bgcolor: "#3b89ff",
                    ml: 1,
                  }}
                />
              )}
            </ListItemButton>
          );
        })}
      </List>

      <Box sx={{ px: 1.5, pb: 1.5 }}>
        <form onSubmit={handleSearch}>
          <TextField
            size="small"
            placeholder="搜索股票..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: "1rem", color: "rgba(255,255,255,0.3)" }} />
                  </InputAdornment>
                ),
                sx: {
                  fontSize: "0.8rem",
                  color: "rgba(255,255,255,0.8)",
                  bgcolor: "rgba(255,255,255,0.05)",
                  borderRadius: "8px",
                  "& .MuiOutlinedInput-notchedOutline": {
                    borderColor: "rgba(255,255,255,0.1)",
                  },
                  "&:hover .MuiOutlinedInput-notchedOutline": {
                    borderColor: "rgba(255,255,255,0.2)",
                  },
                  "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                    borderColor: "#3b89ff",
                  },
                },
              },
            }}
            fullWidth
          />
        </form>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />

      <Box sx={{ px: 2, py: 1.5, borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Typography
            sx={{
              fontSize: "0.65rem",
              color: "rgba(255,255,255,0.35)",
              fontFamily: "var(--font-geist-mono)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            {mounted ? (mode === "light" ? "Light" : "Dark") : "Theme"}
          </Typography>
          <IconButton
            onClick={toggleMode}
            size="small"
            sx={{
              color: mode === "light" ? "#fdbc2a" : "#6aaeff",
              "&:hover": {
                bgcolor: "rgba(255,255,255,0.08)",
              },
              p: 0.75,
            }}
            aria-label={mode === "light" ? "Switch to dark mode" : "Switch to light mode"}
          >
            {mounted ? (
              mode === "light" ? (
                <LightModeIcon sx={{ fontSize: "1rem" }} />
              ) : (
                <DarkModeIcon sx={{ fontSize: "1rem" }} />
              )
            ) : (
              <LightModeIcon sx={{ fontSize: "1rem" }} />
            )}
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ px: 2.5, py: 2 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.5 }}>
          <Typography
            sx={{
              fontSize: "0.65rem",
              color: "rgba(255,255,255,0.35)",
              fontFamily: "var(--font-geist-mono)",
              textTransform: "uppercase",
            }}
          >
            API
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "#36bb80" }} />
            <Typography sx={{ fontSize: "0.65rem", color: "#36bb80", fontFamily: "var(--font-geist-mono)" }}>
              Live
            </Typography>
          </Box>
        </Box>
        <Typography
          sx={{
            fontSize: "0.6rem",
            color: "rgba(255,255,255,0.25)",
            fontFamily: "var(--font-geist-mono)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          localhost:8300
        </Typography>
      </Box>
    </Drawer>
  );
}
