"""Weekly CFTC Commitments-of-Traders (COT) positioning for Gold (COMEX) -
free, no API key, via the CFTC's public Socrata endpoint (Legacy Futures
Only report, dataset 6dca-aqww). Used to test the Zhang & Laws (2013)
COT-sentiment idea (paper151-style distillation, 2026-08-08 - see
app_pages/goldi_papers_202608.py) against the Gold Asian-Range Breakout.

Publication-lag handling: a report dated Tuesday (report_date_as_yyyy_mm_dd)
is only PUBLISHED the following Friday. Using the Tuesday date directly to
align with a trade's entry_time would be lookahead (that Tuesday's positions
aren't public yet on Wednesday/Thursday). This module shifts every report's
effective date forward by 3 calendar days (Tue->Fri) before returning it, so
downstream no-lookahead joins (asian_range_breakout.filters's prior-day
alignment helpers) are safe to use directly."""

from pathlib import Path

import pandas as pd
import requests

CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "asian_range_breakout"
SOCRATA_URL = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
GOLD_MARKET_NAME = "GOLD - COMMODITY EXCHANGE INC."
PUBLICATION_LAG_DAYS = 3  # Tuesday report date -> Friday publication


def fetch_cot_gold(start: str, end: str, force_refresh: bool = False) -> pd.DataFrame:
    """Returns a DataFrame indexed by publication date (tz-naive, Tue+3d),
    columns: open_interest, comm_net, noncomm_net, nonrept_net (net = long -
    short open interest for that trader group)."""
    path = CACHE_DIR / f"COT_GOLD_{start}_{end}.parquet"
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    params = {
        "$where": (
            f"market_and_exchange_names = '{GOLD_MARKET_NAME}' AND "
            f"report_date_as_yyyy_mm_dd >= '{start}T00:00:00.000' AND "
            f"report_date_as_yyyy_mm_dd <= '{end}T00:00:00.000'"
        ),
        "$select": (
            "report_date_as_yyyy_mm_dd, open_interest_all, "
            "noncomm_positions_long_all, noncomm_positions_short_all, "
            "comm_positions_long_all, comm_positions_short_all, "
            "nonrept_positions_long_all, nonrept_positions_short_all"
        ),
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": 5000,
    }
    resp = requests.get(SOCRATA_URL, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise ValueError(f"No CFTC COT data returned for GOLD in {start}..{end}")

    df = pd.DataFrame(rows)
    numeric_cols = [c for c in df.columns if c != "report_date_as_yyyy_mm_dd"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

    report_date = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    out = pd.DataFrame(index=report_date + pd.Timedelta(days=PUBLICATION_LAG_DAYS))
    out.index.name = "publication_date"
    out["open_interest"] = df["open_interest_all"].to_numpy()
    out["comm_net"] = (df["comm_positions_long_all"] - df["comm_positions_short_all"]).to_numpy()
    out["noncomm_net"] = (df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]).to_numpy()
    out["nonrept_net"] = (df["nonrept_positions_long_all"] - df["nonrept_positions_short_all"]).to_numpy()
    out = out.sort_index()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(path)
    return out


def wang_sentiment_index(net_position: pd.Series, window_weeks: int = 156) -> pd.Series:
    """Wang (2001) trader-position-based sentiment index: (S_t - rolling_min)
    / (rolling_max - rolling_min) over a trailing window_weeks (default 156
    = 3 years of weekly COT reports) - an oscillator in [0, 1], 0 = 3-year
    low, 1 = 3-year high. NaN until window_weeks of history has accumulated."""
    roll_min = net_position.rolling(window_weeks, min_periods=window_weeks).min()
    roll_max = net_position.rolling(window_weeks, min_periods=window_weeks).max()
    return (net_position - roll_min) / (roll_max - roll_min)
