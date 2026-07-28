"""Why do indices/metals consistently outperform FX pairs across every
config in research_combined_strategy.py? Three checks, using the already
cached data:

1. Buy-and-hold drift: does the underlying asset itself trend up over the
   period (a beta effect any trend-follower would ride), independent of the
   EMA S/R signal's actual skill?
2. Trending-regime frequency: % of days with daily ADX >= 25, and mean ADX,
   per instrument - do indices/metals simply spend more time in a
   genuinely trending state?
3. Long vs. short trade split (baseline config): if the "edge" on trending
   instruments is really just "being long a rising asset", long trades
   should dominate both in count and in R-multiple quality there, while FX
   pairs (no secular drift) should show a more balanced long/short picture.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import INSTRUMENTS, load_all
from combined_strategy.pipeline import run_pipeline
from ema_strategy.indicators import adx

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

IN_SAMPLE_FRAC = 0.7


def split(h4: pd.DataFrame, frac: float):
    cut = int(len(h4) * frac)
    return h4.iloc[:cut], h4.iloc[cut:]


def buy_and_hold_return(daily: pd.DataFrame) -> float:
    return daily["Close"].iloc[-1] / daily["Close"].iloc[0] - 1


def main():
    print("Loading real Dukascopy H4/D1/W1 history for all 11 instruments (cached after first run)...")
    data = load_all("2016-07-28", "2026-07-28")

    rows = []
    for key in INSTRUMENTS:
        h4, daily, weekly = data[key]
        h4_is, h4_oos = split(h4, IN_SAMPLE_FRAC)
        daily_is, daily_oos = split(daily, IN_SAMPLE_FRAC)

        daily_adx = adx(daily, period=14)
        pct_trending_full = (daily_adx >= 25).mean()
        pct_trending_oos = (daily_adx.loc[daily_oos.index] >= 25).mean() if not daily_oos.empty else float("nan")

        signals, trades, equity, metrics = run_pipeline(h4_oos, daily, weekly)
        if not trades.empty:
            longs = trades[trades["direction"] == "LONG"]
            shorts = trades[trades["direction"] == "SHORT"]
            long_r = longs["r_multiple"].mean() if not longs.empty else float("nan")
            short_r = shorts["r_multiple"].mean() if not shorts.empty else float("nan")
            n_long, n_short = len(longs), len(shorts)
        else:
            long_r = short_r = float("nan")
            n_long = n_short = 0

        rows.append(
            {
                "instrument": key,
                "bh_return_full_10y_%": buy_and_hold_return(daily) * 100,
                "bh_return_oos_%": buy_and_hold_return(daily_oos) * 100,
                "mean_daily_adx": daily_adx.mean(),
                "pct_days_trending_full": pct_trending_full * 100,
                "pct_days_trending_oos": pct_trending_oos * 100,
                "oos_n_long": n_long,
                "oos_n_short": n_short,
                "oos_long_r_multiple": long_r,
                "oos_short_r_multiple": short_r,
            }
        )

    df = pd.DataFrame(rows).set_index("instrument")
    print("\n=== Buy-and-hold drift, trending frequency, and long/short split (baseline, OOS) ===")
    print(df.round(2))


if __name__ == "__main__":
    main()
