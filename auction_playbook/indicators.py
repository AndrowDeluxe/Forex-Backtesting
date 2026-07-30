"""Volume Profile, Auction-Market-Theory value area, and session tagging
for the Auction Market Playbook reconstruction (see auction_playbook/signals.py
for how these compose into the two setups via one unified state machine).

Operational choices, made explicit since the source PDF describes these
concepts qualitatively rather than as precise formulas:

- **Balance reference**: the source states this directly for the Mean
  Reversion setup - "use the previous day's profile as the balance
  reference" - and both setups target "the balance POC", so this module
  reuses the *same* previous-calendar-day value area as the shared
  reference for both setups (see signals.py's docstring for why treating
  a held vs. a failed breakout as the fork between Trend/Reversion removes
  the need for a second, separately-invented "balance" definition).
- **Sessions**: "New York session" -> 13:00-21:00 UTC (regular NYSE/CME
  hours), "London session" -> 07:00-12:00 UTC (pre-NY-overlap), both
  operational UTC windows since crypto trades 24/7 and the source's session
  references come from a futures-market context (NASDAQ, ES).
- **Value area** (POC +/- the range holding ~70% of volume) is the standard
  Auction Market Theory construct implied by "balance ... where most
  trading activity happens" - the 70% figure is the conventional AMT
  default (also matching the source's own "70% of the time, the market
  stays stuck" framing elsewhere), not a number given explicitly for the
  value-area calculation itself.
"""

import numpy as np
import pandas as pd

NY_SESSION = (13.0, 21.0)      # UTC hours
LONDON_SESSION = (7.0, 12.0)   # UTC hours


def tag_sessions(index: pd.DatetimeIndex) -> pd.DataFrame:
    hour = index.hour + index.minute / 60.0
    return pd.DataFrame(
        {
            "in_ny_session": (hour >= NY_SESSION[0]) & (hour < NY_SESSION[1]),
            "in_london_session": (hour >= LONDON_SESSION[0]) & (hour < LONDON_SESSION[1]),
        },
        index=index,
    )


def volume_profile(df_leg: pd.DataFrame, num_bins: int = 24) -> pd.DataFrame:
    """Volume-by-price histogram over a bar slice (a "leg"), distributing
    each bar's volume across price bins by its high/low overlap - the same
    method the bot's own `aiService.calculateVolumeProfile` (JS) uses.

    Returns one row per bin: price (bin midpoint), volume, and `level`
    ("POC"/"HVN"/"LVN"/"Normal") - POC/HVN >150% of the bin-average volume,
    LVN <50%, mirroring the source's own thresholds.
    """
    if df_leg.empty:
        return pd.DataFrame(columns=["price", "volume", "level"])

    lo, hi = df_leg["low"].min(), df_leg["high"].max()
    if hi <= lo:
        return pd.DataFrame(columns=["price", "volume", "level"])

    edges = np.linspace(lo, hi, num_bins + 1)
    bin_lo, bin_hi = edges[:-1], edges[1:]
    bin_mid = (bin_lo + bin_hi) / 2
    bin_volume = np.zeros(num_bins)

    highs = df_leg["high"].to_numpy()
    lows = df_leg["low"].to_numpy()
    vols = df_leg["volume"].to_numpy()
    ranges = np.maximum(highs - lows, 1e-12)
    vol_per_price = vols / ranges

    for b in range(num_bins):
        overlap = np.maximum(0.0, np.minimum(bin_hi[b], highs) - np.maximum(bin_lo[b], lows))
        bin_volume[b] += (vol_per_price * overlap).sum()

    avg_vol = bin_volume.mean() if bin_volume.mean() > 0 else 1e-12
    max_vol = bin_volume.max()
    level = np.where(
        bin_volume == max_vol, "POC",
        np.where(bin_volume > avg_vol * 1.5, "HVN", np.where(bin_volume < avg_vol * 0.5, "LVN", "Normal")),
    )
    return pd.DataFrame({"price": bin_mid, "volume": bin_volume, "level": level})


def poc_price(profile: pd.DataFrame) -> float | None:
    poc = profile.loc[profile["level"] == "POC", "price"]
    return float(poc.iloc[0]) if not poc.empty else None


def lvn_prices(profile: pd.DataFrame) -> list[float]:
    return profile.loc[profile["level"] == "LVN", "price"].tolist()


def value_area(profile: pd.DataFrame, pct: float = 0.70) -> tuple[float, float, float]:
    """Classic AMT value area: expand out from the POC bin, adding whichever
    neighbouring bin (above/below) has more volume, until `pct` of total
    volume is enclosed. Returns (value_area_low, poc, value_area_high).
    """
    if profile.empty or profile["volume"].sum() == 0:
        return (np.nan, np.nan, np.nan)

    profile = profile.reset_index(drop=True).sort_values("price").reset_index(drop=True)
    total = profile["volume"].sum()
    poc_idx = profile["volume"].idxmax()

    lo_i, hi_i = poc_idx, poc_idx
    included = profile.loc[poc_idx, "volume"]
    while included < total * pct and (lo_i > 0 or hi_i < len(profile) - 1):
        vol_below = profile.loc[lo_i - 1, "volume"] if lo_i > 0 else -1
        vol_above = profile.loc[hi_i + 1, "volume"] if hi_i < len(profile) - 1 else -1
        if vol_above >= vol_below:
            hi_i += 1
            included += profile.loc[hi_i, "volume"]
        else:
            lo_i -= 1
            included += profile.loc[lo_i, "volume"]

    return (float(profile.loc[lo_i, "price"]), float(profile.loc[poc_idx, "price"]), float(profile.loc[hi_i, "price"]))


def build_daily_reference_cache(df: pd.DataFrame) -> dict:
    """Precompute the previous-calendar-day value area/POC once per day
    present in `df`, keyed by `date` (a `datetime.date`) - the shared
    "balance reference" both setups in signals.py read from. Precomputing
    matters: recomputing a full day's profile on every intraday bar (rather
    than once per calendar day) was the dominant cost in the first draft of
    this backtest.
    """
    cache = {}
    for day, day_df in df.groupby(df.index.date):
        profile = volume_profile(day_df, num_bins=30)
        va_low, poc, va_high = value_area(profile)
        if np.isnan(poc):
            continue
        cache[day] = {"poc": poc, "va_low": va_low, "va_high": va_high, "day_high": day_df["high"].max(), "day_low": day_df["low"].min()}
    return cache
