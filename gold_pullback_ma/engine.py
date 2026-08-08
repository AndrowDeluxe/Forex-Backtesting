"""Long-only MA-pullback strategy on daily Gold bars, per Beluska & Vojtko
("Real Estate"-titled paper, actually a generic multi-asset pullback
template - tested on 6 ETFs incl. GLD): buy a pullback within an uptrend,
hold exactly 1 day.

Rules (single-asset adaptation - the paper's dynamic equal-weight-across-
simultaneous-signals sizing doesn't apply with only one instrument):
  1. Uptrend filter: day T's close is above its own `ma_window`-day SMA.
  2. Pullback trigger: exactly `n_down_days` consecutive lower closes
     ending at day T (close[T] < close[T-1] < ... for n_down_days steps).
  3. Entry: next trading day's (T+1) OPEN - not day T's close, which the
     paper's own close-to-close convention would use but which isn't
     actually tradable (the signal is only fully known once T's close
     prints). This is a deliberate, disclosed deviation for realism, same
     "no lookahead" discipline as asian_range_breakout/filters.py.
  4. Exit: day T+1's CLOSE (1-day hold).
  5. Position: always long (uptrend + pullback = buy-the-dip continuation).

`cost_bps`: flat round-trip cost in basis points, applied to return_pct -
a simplification vs. asian_range_breakout.engine's explicit spread/
slippage price model, appropriate for a daily EOD-style strategy where
intrabar fill mechanics aren't being modeled at all.
"""

import numpy as np
import pandas as pd


def _consecutive_down_days(close: pd.Series) -> pd.Series:
    """For each day, the number of consecutive lower closes ending at that
    day (0 if today's close isn't lower than yesterday's)."""
    down = (close < close.shift(1)).astype(int)
    reset_groups = (down == 0).cumsum()
    return down.groupby(reset_groups).cumsum()


def simulate_pullback(
    daily_ohlc: pd.DataFrame, ma_window: int = 200, n_down_days: int = 3, cost_bps: float = 5.0
) -> pd.DataFrame:
    close = daily_ohlc["close"]
    ma = close.rolling(ma_window).mean()
    uptrend = close > ma
    consec_down = _consecutive_down_days(close)

    signal = uptrend & (consec_down == n_down_days)
    signal_idx = daily_ohlc.index[signal]

    dates = daily_ohlc.index
    rows = []
    for t in signal_idx:
        pos = dates.get_loc(t)
        if pos + 1 >= len(dates):
            continue  # no next trading day in the data yet
        entry_date = dates[pos + 1]
        entry_price = daily_ohlc["open"].iloc[pos + 1]
        exit_price = daily_ohlc["close"].iloc[pos + 1]
        if pd.isna(entry_price) or pd.isna(exit_price) or entry_price <= 0:
            continue
        gross_return = (exit_price - entry_price) / entry_price
        return_pct = gross_return - cost_bps / 1e4
        rows.append(
            {
                "signal_date": t,
                "entry_time": entry_date,
                "exit_time": entry_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "direction": "long",
                "return_pct": return_pct,
                "n_down_days": n_down_days,
                "ma_window": ma_window,
                "hold_bars": 1,
                "exit_reason": "time_exit",
            }
        )

    return pd.DataFrame(rows)
