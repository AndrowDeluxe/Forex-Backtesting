"""Config for the OU-Modell paper replication (Jashnani, 'Bollinger Bands + OU Mean
Reversion in S&P 500 Equities'). See ../OU Modell.pdf for the source paper."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_CACHE = ROOT / "data_cache"
RESULTS_DIR = ROOT / "results"
SP500_WIKI_CSV = ROOT / "sp500_wiki.csv"
NASDAQ100_WIKI_CSV = ROOT / "nasdaq100_wiki.csv"
DAX_WIKI_CSV = ROOT / "dax_wiki.csv"

# --- Universe ---
N_SAMPLE_TICKERS = 90          # reduced sample (paper used 424 of 503)
RANDOM_SEED = 42

UNIVERSES = {
    "sp500": {"label": "S&P 500 (Sample, 90 Ticker)", "benchmark": "^GSPC", "benchmark_label": "S&P 500"},
    "nasdaq100": {"label": "Nasdaq-100 (alle ~103 Ticker)", "benchmark": "^NDX", "benchmark_label": "Nasdaq-100"},
    "dax": {"label": "DAX (alle 40 Ticker)", "benchmark": "^GDAXI", "benchmark_label": "DAX"},
}

# --- Portfolio / equity curve (100k account) ---
INITIAL_EQUITY = 100_000.0
RISK_PCT_PER_TRADE = 0.01      # % of current equity risked per trade (stop-distance based)
MAX_TOTAL_RISK_PCT = 0.15      # cap on aggregate open risk across all concurrent positions
MAX_POSITION_PCT = 0.20        # cap on notional size of any single position (vs. equity)

# --- Sample split (matches paper section 4.3) ---
IN_SAMPLE_START = "2010-01-01"
IN_SAMPLE_END = "2017-12-31"
OUT_SAMPLE_START = "2018-01-01"
OUT_SAMPLE_END = "2024-12-31"

DOWNLOAD_START = "2009-06-01"  # a bit before in-sample so the first 252d window is full
DOWNLOAD_END = "2024-12-31"

# --- OU estimation (section 4.2 / 4.4) ---
ROLLING_WINDOWS = [60, 120, 252]

# --- OU-universe selection criteria (section 4) ---
THETA_MIN = 0.03
PVALUE_MAX = 0.2
HALFLIFE_MIN = 5
HALFLIFE_MAX = 200

# --- Bollinger Band strategy (section 4.1) ---
BB_LOOKBACK = 20
BB_K = 2.0
MAX_HOLDING_DAYS = 10
STOP_LOSS_SIGMA = 2.0

TRADING_DAYS_PER_YEAR = 252
