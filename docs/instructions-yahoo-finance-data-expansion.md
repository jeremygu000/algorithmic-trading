# Instruction: Expand yahoo-finance-data Download Pool to Russell 3000

## Background

The algorithmic-trading project needs OHLCV data for ~2500 stocks to run a "Beauty Shoulder" (美人肩) pattern detection and backtest. Currently yahoo-finance-data only downloads 33 tickers (hardcoded in `DEFAULT_TICKERS`). The Russell 3000 constituent list is already available at `~/Desktop/projects/algorithmic-trading/cache/index/russell3000.txt` (2481 symbols, maintained by `daily_refresh.py`).

## Objective

Enable yahoo-finance-data to download daily OHLCV data for all Russell 3000 constituents (~2500 tickers) into `~/.market_data/parquet/`.

## Requirements

### 1. Support External Symbol List File

**File:** `src/market_data/config.py`

Add a config option to load tickers from an external file, falling back to `DEFAULT_TICKERS` if the file doesn't exist:

```python
# New env var: path to a text file with one ticker per line
TICKER_LIST_FILE = os.environ.get("MARKET_DATA_TICKER_LIST_FILE", "")
```

Add a helper function:

```python
def get_tickers() -> list[str]:
    """Load tickers from TICKER_LIST_FILE if set, otherwise use DEFAULT_TICKERS."""
    if TICKER_LIST_FILE and Path(TICKER_LIST_FILE).exists():
        tickers = [
            line.strip().upper()
            for line in Path(TICKER_LIST_FILE).read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if tickers:
            return list(dict.fromkeys(tickers))  # dedupe, preserve order
    return DEFAULT_TICKERS
```

### 2. Update CLI to Use `get_tickers()`

**File:** `src/market_data/cli.py`

Change the fetch command's default ticker source:

```python
# Before
tickers = args.tickers.split(",") if args.tickers else DEFAULT_TICKERS

# After
from market_data.config import get_tickers
tickers = args.tickers.split(",") if args.tickers else get_tickers()
```

Same for the `backfill` command.

### 3. Add Batch-Friendly Fetching (Important for 2500 Tickers)

**File:** `src/market_data/fetcher.py`

The current `fetch_batch()` sends all tickers at once. For 2500 tickers, yfinance may struggle. Add chunked fetching:

```python
BATCH_SIZE = int(os.environ.get("MARKET_DATA_BATCH_SIZE", "50"))
```

Split the ticker list into chunks of `BATCH_SIZE` and fetch sequentially with a small delay between chunks. This avoids Yahoo Finance rate limiting and memory pressure.

### 4. Add Incremental Update Support

When re-running fetch for 2500 tickers, skip tickers whose local parquet file is already up-to-date (last_date == yesterday or today). Only fetch tickers with stale or missing data.

The `store.last_date()` function already exists. Use it:

```python
from market_data.store import last_date

def filter_stale_tickers(tickers: list[str], data_dir: Path) -> list[str]:
    """Return only tickers that need updating."""
    today = date.today()
    stale = []
    for t in tickers:
        ld = last_date(t, data_dir=data_dir)
        if ld is None or (today - ld).days > 1:
            stale.append(t)
    return stale
```

### 5. Keep Existing DEFAULT_TICKERS Intact

Do NOT remove or modify `DEFAULT_TICKERS`. It serves as the fallback when no external file is configured.

## Usage

```bash
# Set the ticker list file to Russell 3000
export MARKET_DATA_TICKER_LIST_FILE=~/Desktop/projects/algorithmic-trading/cache/index/russell3000.txt

# First-time full download (~2500 tickers, may take 30-60 min)
market-data fetch

# Subsequent runs: only fetches stale/missing tickers (fast)
market-data fetch

# Override with specific tickers (existing behavior preserved)
market-data fetch --tickers AAPL,MSFT,GOOGL
```

## Expected Outcome

- `~/.market_data/parquet/` contains `{TICKER}_1d.parquet` for ~2500 stocks
- Each parquet file has columns: `Open, High, Low, Close, Volume`
- Date range: at least 2025-04-01 to present (1 year lookback)
- Total disk usage: ~750 MB
- Existing 33 ticker data is preserved and updated

## Constraints

- Do NOT break existing functionality — `DEFAULT_TICKERS`, CLI commands, API endpoints, watchlist all work as before
- Do NOT add new dependencies
- Yahoo Finance is free but rate-limited — respect delays between batches
- Handle failures gracefully: if a ticker fails, log warning and continue to next
