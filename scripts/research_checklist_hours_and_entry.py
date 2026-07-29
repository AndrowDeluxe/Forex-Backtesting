"""Three follow-up questions on the checklist strategy (EUR/USD M15):

1. Restrict entries to the London+NY combined window (07:00-22:00 UTC).
2. "Best hours" filter, tested honestly: hours are selected from an
   in-sample half (2016-07-28..2021-07-28) by total return only, then
   applied and evaluated ONLY on the untouched out-of-sample half
   (2021-07-28..2026-07-28) - avoids the circularity of picking hours from
   the same data used to judge them.
3. Alternative entry rule: RSI(14) crossing back through the 70/30 level
   itself, instead of crossing its own SMA(14).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from checklist_strategy.backtest import simulate_checklist_trades
from checklist_strategy.pipeline import run_checklist_pipeline
from strategy.metrics import summarize
from strategy.real_data import fetch_pair_history

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

SPLIT = pd.Timestamp("2021-07-28", tz="UTC")
YEARS = list(range(2017, 2026))


def yearly_table(signaled, trades):
    rows = []
    for year in YEARS:
        yr_df = signaled[signaled.index.year == year]
        if yr_df.empty:
            continue
        yr_trades = trades[trades["entry_time"].dt.year == year]
        if yr_trades.empty:
            rows.append({"year": year, "n_trades": 0})
            continue
        s = summarize(yr_trades, yr_df.index)
        rows.append(
            {
                "year": year, "n_trades": s["n_trades"], "win_rate": s["win_rate"],
                "avg_return_bps": s["avg_return_pct"] * 1e4, "sharpe": s["sharpe"],
            }
        )
    return pd.DataFrame(rows).set_index("year")


def report(signaled, trades, label):
    print(f"\n{'=' * 10} {label} {'=' * 10}")
    print(f"Total trades: {len(trades)}")
    if trades.empty:
        return
    full_summary = summarize(trades, signaled.index)
    print(f"  sharpe={full_summary['sharpe']:.3f}  win_rate={full_summary['win_rate']:.3f}  "
          f"profit_factor={full_summary['profit_factor']:.3f}  "
          f"avg_return_bps={full_summary['avg_return_pct']*1e4:.3f}")
    yearly = yearly_table(signaled, trades)
    active = yearly[yearly["n_trades"] > 0]
    if not active.empty:
        print(f"  mean yearly sharpe={active['sharpe'].mean():.3f}  "
              f"years positive={int((active['avg_return_bps'] > 0).sum())}/{len(active)}")


def main():
    print("Loading EUR/USD M15 history (cached after first run)...")
    df = fetch_pair_history("EURUSD", "2016-07-28", "2026-07-28")

    # --- Baseline, for reference ---
    signaled_base = run_checklist_pipeline(df)
    trades_base = simulate_checklist_trades(signaled_base)
    report(signaled_base, trades_base, "Baseline (no filter, full period)")

    # --- 1. London+NY session filter ---
    signaled_ln = run_checklist_pipeline(df, use_session_filter=True, session_start_hour=7.0, session_end_hour=22.0)
    trades_ln = simulate_checklist_trades(signaled_ln)
    report(signaled_ln, trades_ln, "London+NY only (07:00-22:00 UTC), full period")

    # --- 2. Best-hours filter, IS-selected / OOS-tested ---
    is_trades = trades_base[trades_base["entry_time"] < SPLIT]
    is_trades = is_trades.copy()
    is_trades["hour"] = is_trades["entry_time"].dt.hour
    hour_stats = is_trades.groupby("hour")["return_pct"].sum()
    good_hours = set(hour_stats[hour_stats > 0].index)
    print(f"\nIn-sample (2016-2021) hours with positive total return: {sorted(good_hours)}")

    signaled_hours = run_checklist_pipeline(df, use_session_filter=True, session_allowed_hours=good_hours)
    trades_hours = simulate_checklist_trades(signaled_hours)

    oos_signaled_base = signaled_base[signaled_base.index >= SPLIT]
    oos_trades_base = trades_base[trades_base["entry_time"] >= SPLIT]
    report(oos_signaled_base, oos_trades_base, "OOS (2021-2026) baseline, no hour filter")

    oos_signaled_hours = signaled_hours[signaled_hours.index >= SPLIT]
    oos_trades_hours = trades_hours[trades_hours["entry_time"] >= SPLIT]
    report(oos_signaled_hours, oos_trades_hours, "OOS (2021-2026) with IS-selected best-hours filter")

    # --- 3. Alternative entry rule: RSI level cross instead of RSI/MA cross ---
    signaled_level = run_checklist_pipeline(df, entry_rule="rsi_level_cross")
    trades_level = simulate_checklist_trades(signaled_level)
    report(signaled_level, trades_level, "entry_rule='rsi_level_cross', full period")


if __name__ == "__main__":
    main()
