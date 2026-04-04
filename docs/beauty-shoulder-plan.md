# 美人肩图形检测 — 需求分析与执行计划

## 需求来源

客户需求文档：`docs/美人肩图形.docx`

---

## 需求分析

客户提出 **两个独立需求**：

### 需求 A：美人肩图形检测 + 历史回测

**图形定义：** 主升浪中的脉冲式上涨形态，形状类似美女的肩部。

**三阶段构造：**

```
        ● 加速阶段1高点
       /|
      / |  回调整理阶段 (4-6天)
     /  |  回调10%-25%
    /   |      ___
   /    |     /   \    ● 中阳线入场信号
  /     |    /     \  /
 /      |   /       \/  ← 最低点（不破EMA20）
/       |  /
        | /
        |/

|--3~4天--|--4~6天--|--2天--|
  +20~40%  -10~25%   +3~10%
```

| 阶段 | 条件 | 参数 |
|------|------|------|
| **加速阶段1** | 近 3-4 个交易日合计涨幅 20%-40% | 可选条件：连续3根阳线（收盘价 > 开盘价） |
| **回调整理阶段** | 从加速阶段1高点回调 10%-25%，持续 4-6 天 | **硬约束：** 整理期间任何一天的收盘价都不能跌穿 EMA20 |
| **加速阶段2（入场信号）** | 整理阶段收盘价最低点之后 2 天内，出现一根中阳线（涨幅 3%-10%） | 此时价格接近加速阶段1高点，等额平铺买入 |

**交易策略：**
- 入场：出现加速阶段2信号时买入
- 仓位：等额平铺（每只符合条件的股票分配相同金额）
- 持有：2-3 天
- 退出：固定持有期卖出（无额外止损止盈）

**回测要求：**
- 时间范围：2025年10月、11月、12月、2026年1月
- 统计指标：符合图形的股票平均收益率
- 建议额外输出：胜率、中位收益、最大亏损、按月分组统计

---

### 需求 B：早期启动股票筛选

**定义：** 在任意 20 天窗口内，第 20 天的收盘价比第 1 天的收盘价高出 20%-30%。

**用途：** 独立筛选器，也可作为美人肩检测的预筛选条件（先找到近期有强势启动的股票，再在其中找美人肩形态）。

---

## 待确认事项

| # | 疑点 | 当前理解 | 建议处理 |
|---|------|----------|----------|
| 1 | "等额平铺"具体含义 | 每只信号股分配相同金额 | 回测用等权重组合 |
| 2 | "持有2-3天" | 固定持有期 | 分别统计 2 天和 3 天收益 |
| 3 | 需求 B 和需求 A 的关系 | B 可作为 A 的预筛选 | 设计为独立模块，可串联 |
| 4 | 股票池范围 | 现有 stock_symbols (~300 只) | 需确认是否扩大池子 |
| 5 | "平均收益率"指标 | 入场后 N 天的涨跌幅 | 同时输出胜率、最大亏损、中位数 |
| 6 | EMA20 vs SMA20 | 文档明确写 EMA20 | 使用指数移动平均线 |

---

## 现有架构分析

### 可复用的基础设施

| 模块 | 文件 | 复用点 |
|------|------|--------|
| 价格数据加载 | `data/providers/unified.py` | `load_prices_with_fallback()` 统一数据源 |
| 技术指标计算 | `features/indicators.py` | RSI、MACD、Bollinger Bands |
| 趋势扫描服务 | `api/services/trend_scanner.py` | `TrendScannerService` 模式（加载→扫描→返回） |
| 股票池构建 | `api/services/stock_universe.py` | `StockUniverseBuilder` |
| DTW 形态匹配 | `features/pattern_match.py` | `PatternMatchResult` 接口 |
| 回测引擎 | `backtest/engine.py` + `metrics.py` | 月度收益计算框架 |
| API 框架 | `api/main.py` | FastAPI 端点模式 |
| 前端扫描页 | `web/src/app/trend-scan/page.tsx` | UI 结构、数据获取模式 |

### 关键接口

```python
# 检测结果 dataclass 模板（参考 TrendScanMatch）
@dataclass
class BeautyShoulderPattern:
    symbol: str
    name: str
    phase1_start: str          # 加速阶段1起始日期
    phase1_end: str            # 加速阶段1结束日期（高点）
    phase1_gain: float         # 加速阶段1涨幅 %
    pullback_low_date: str     # 回调最低点日期
    pullback_depth: float      # 回调深度 %
    signal_date: str           # 入场信号日期
    signal_candle_gain: float  # 中阳线涨幅 %
    entry_price: float         # 建议入场价
    confidence: float          # 形态置信度 0-1
    has_3_bullish: bool        # 是否满足可选条件（3根阳线）

# 扫描结果（参考 TrendScanResult）
@dataclass
class BeautyShoulderScanResult:
    date: str
    total_scanned: int
    matches: list[BeautyShoulderPattern]
```

---

## 执行计划

### Phase 1：核心检测引擎

**新建文件：** `src/etf_trend/features/beauty_shoulder.py`

**实现内容：**
1. `detect_beauty_shoulder(prices: pd.Series, opens: pd.Series, ema20: pd.Series) -> list[BeautyShoulderPattern]`
2. 加速阶段1检测：滑动窗口（3-4天），合计涨幅 20%-40%
3. 可选阳线验证：检查是否连续3根阳线（close > open）
4. 回调阶段检测：从高点开始，4-6天回调 10%-25%，每天 close > EMA20
5. 入场信号检测：回调最低点后 2 天内出现中阳线（3%-10%）
6. 返回 `BeautyShoulderPattern` dataclass 列表

**技术要点：**
- EMA20 使用 `pandas.Series.ewm(span=20).mean()`
- 滑动窗口用 numpy/pandas rolling 实现
- 需要 OHLC 数据（开盘价用于阳线判断）

**预计工时：** 4-6 小时

---

### Phase 2：早期启动筛选器

**新建文件：** `src/etf_trend/features/early_mover.py`

**实现内容：**
1. `detect_early_mover(prices: pd.Series, window=20, min_gain=0.20, max_gain=0.30) -> list[EarlyMoverSignal]`
2. 滑动窗口（20天），检测 close[day20] / close[day1] - 1 在 20%-30% 范围内
3. 返回所有符合条件的窗口起止日期和涨幅

**预计工时：** 1-2 小时

---

### Phase 3：历史回测模块

**新建文件：** `src/etf_trend/backtest/beauty_shoulder_backtest.py`

**实现内容：**
1. 加载 2025年10月 - 2026年1月的历史数据
2. 对股票池逐一运行美人肩检测
3. 每个信号等权买入，分别统计持有 2 天和 3 天的收益
4. 输出指标：
   - 平均收益率（按月分组）
   - 胜率（正收益占比）
   - 中位收益率
   - 最大单笔亏损
   - 最大单笔盈利
   - 信号总数
5. 生成 CSV 明细 + 汇总报告

**输出格式：**
```
reports/
├── beauty_shoulder_trades.csv     # 每笔交易明细
├── beauty_shoulder_summary.txt    # 汇总统计
└── beauty_shoulder_monthly.csv    # 按月分组统计
```

**预计工时：** 3-4 小时

---

### Phase 4：API 端点

**修改文件：** `src/etf_trend/api/main.py`
**新建文件：** `src/etf_trend/api/services/beauty_shoulder_scanner.py`

**新增端点：**

| 端点 | 方法 | 功能 | 参数 |
|------|------|------|------|
| `GET /api/stocks/beauty-shoulder` | GET | 扫描当前符合美人肩形态的股票 | `lookback` (默认30天) |
| `GET /api/stocks/early-movers` | GET | 早期启动股票列表 | `window` (默认20), `min_gain`, `max_gain` |

**实现模式：** 复用 `TrendScannerService` 的模式
- 构造函数接收 config + API key
- scan() 方法加载价格 → 逐股检测 → 返回 dataclass
- to_dict() 序列化为 JSON

**预计工时：** 2-3 小时

---

### Phase 5：前端页面

**新建文件：** `src/web/src/app/beauty-shoulder/page.tsx`

**UI 设计（参考 trend-scan 页面）：**
- 扫描参数控制卡片（lookback天数选择）
- 统计摘要（扫描总数、命中数）
- 结果网格：
  - 股票代码 + 名称
  - 形态各阶段标注（加速1涨幅、回调深度、信号阳线涨幅）
  - 入场价位 + 置信度
  - 点击跳转个股详情
- Sidebar 导航添加新页面入口

**预计工时：** 3-4 小时

---

### Phase 6：测试 + 验证

**测试文件：**
- `src/etf_trend/tests/test_beauty_shoulder.py` — 单元测试（已知形态的合成数据）
- `src/etf_trend/tests/test_early_mover.py` — 早期启动检测测试
- API 集成测试

**验证清单：**
- [ ] `ruff check` 通过
- [ ] `black --check` 通过
- [ ] `tsc --noEmit` 通过（前端）
- [ ] `npm run lint` 通过（前端）
- [ ] `pytest` 全部通过
- [ ] `next build` 成功

**预计工时：** 2-3 小时

---

## 总工时估算

| Phase | 内容 | 预计工时 |
|-------|------|----------|
| Phase 1 | 核心检测引擎 | 4-6h |
| Phase 2 | 早期启动筛选器 | 1-2h |
| Phase 3 | 历史回测 | 3-4h |
| Phase 4 | API 端点 | 2-3h |
| Phase 5 | 前端页面 | 3-4h |
| Phase 6 | 测试验证 | 2-3h |
| **合计** | | **15-22h** |

---

## 依赖关系

```
Phase 2 (早期启动) ──────────────────────────┐
                                              ├──→ Phase 4 (API)  ──→ Phase 5 (前端)
Phase 1 (美人肩检测) ──→ Phase 3 (回测) ──────┘                        ↓
                                                                  Phase 6 (测试)
```

Phase 1 和 Phase 2 可并行开发。Phase 3 依赖 Phase 1。Phase 4-5 依赖 Phase 1-2。

---

*Created: April 2026*
*Status: Pending approval*
