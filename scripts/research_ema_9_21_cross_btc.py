"""Research script: reproduce "The Backtest Machine" cheat sheet's (Miles
Deutscher Finance) headline example - EMA 9/21 crossover, long-only, on
BTCUSDT daily - using this repo's own real Binance data instead of trusting
the sheet's claimed TradingView numbers.

Sheet's claim (Part 2): win rate ~35%, profit factor ~3, "half the drawdown"
of buy-and-hold, tester range July 2023 -> today, 0.1% commission per side,
fills on next bar open, no leverage, long-only, 100% of equity per trade.

Also runs the sheet's own overfitting check (Part 3, caveat 4): neighbouring
parameters (8/20, 10/22) should form a plateau around 9/21, not a spike.

Extension (long/short + full history + IS/OOS): the sheet's system is
long-flat (short-side days sit in cash). This adds a long-short variant
(short instead of flat below the crossover) and re-runs on the full
available Binance history (2017-08-17 onward, ~9y) split IS/OOS 70/30,
instead of only the sheet's cherry-picked-by-nature 2023-2026 window (which
is mostly a BTC bull market). Funding-rate cost for the short side is NOT
modeled (no funding-rate data source in this repo yet) - flagged explicitly
in the results rather than silently ignored, since perpetual shorts
typically pay funding in trending-up regimes, which would erode the short
leg's real-world P&L below what's shown here.

Simulation engine lives in btc_ema_cross/engine.py (factored out 2026-08-15
so the Streamlit dashboard, app_pages/btc_ema_cross.py, shares the exact
same tested logic instead of a second copy)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import (
    ATR_PERIOD,
    ATR_STOP_MULT,
    COMMISSION,
    simulate_ema_cross,
    simulate_ema_cross_ls,
    simulate_risk_sized,
)

START, END = "2023-07-01", "2026-08-13"
FULL_START = "2017-08-17"  # BTCUSDT listing date on Binance
PARAM_GRID = [(8, 20), (9, 21), (10, 22)]
IS_FRACTION = 0.7

STARTING_CAPITAL = 100_000.0
RISK_PCT = 0.01


def fmt(m: dict) -> str:
    return (
        f"EMA {m['fast']}/{m['slow']}: n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  "
        f"PF={m['profit_factor']:.2f}  TotalReturn={m['total_return']:+.1%}  "
        f"CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}"
    )


def main():
    print(f"Fetching BTCUSDT daily {FULL_START} -> {END} ...")
    full = fetch_klines("BTCUSDT", "1d", FULL_START, END)
    print(f"{len(full)} daily bars ({full.index[0].date()} -> {full.index[-1].date()})")

    split_i = int(len(full) * IS_FRACTION)
    is_df, oos_split_date = full.iloc[:split_i], full.index[split_i]
    oos_df = full.loc[full.index >= oos_split_date]  # kept for its date range/len only; simulations use `full` + sim_from
    # (label, df, sim_from): Full/IS start at the true beginning of their own series (no warmup
    # issue), OOS runs on the FULL series from oos_split_date so EMA/ATR keep proper warmup from
    # all prior history instead of restarting cold at the split date (see note printed below).
    windows = [("Full", full, None), ("IS", is_df, None), ("OOS", full, oos_split_date)]
    print(f"IS : {is_df.index[0].date()} -> {is_df.index[-1].date()}  ({len(is_df)} bars)")
    print(f"OOS: {oos_df.index[0].date()} -> {oos_df.index[-1].date()}  ({len(oos_df)} bars)")
    print(
        "Note: OOS simulations below run on the FULL series with sim_from=OOS-start, so EMA/ATR carry\n"
        "proper warmup from all prior history instead of restarting cold at the split date (a bug found\n"
        "and fixed while building this section - a naively re-sliced OOS df gave measurably different\n"
        "results, e.g. a different worst-single-day reading, because the EMA/ATR seed differed)."
    )

    sheet_start = pd.Timestamp(START, tz="UTC")
    bh_window = full.loc[full.index >= sheet_start, "close"]
    bh_ret = bh_window.iloc[-1] / bh_window.iloc[0] - 1
    bh_equity = bh_window / bh_window.iloc[0]
    bh_dd = (bh_equity / bh_equity.cummax() - 1).min()
    print(f"\nBuy & hold BTC ({START} -> {END}): TotalReturn={bh_ret:+.1%}  MaxDD={bh_dd:.1%}")

    print("\n" + "=" * 78)
    print("OVERFITTING CHECK (sheet's own caveat 4: plateau, not spike)")
    print("=" * 78)
    for fast, slow in PARAM_GRID:
        m = simulate_ema_cross(full, fast, slow, sim_from=sheet_start)
        print("  " + fmt(m))

    print("\n" + "=" * 78)
    print("LONG/SHORT EXTENSION on FULL HISTORY, IS/OOS split (fast=9, slow=21)")
    print("=" * 78)
    bh_full = full["close"].iloc[-1] / full["close"].iloc[0] - 1
    bh_full_dd = (full["close"] / full["close"].cummax() - 1).min()
    print(f"\nBuy & Hold BTC (full history): TotalReturn={bh_full:+.1%}  MaxDD={bh_full_dd:.1%}")

    for label, part, sim_from in windows:
        w_start = sim_from.date() if sim_from is not None else part.index[0].date()
        m_lf = simulate_ema_cross_ls(part, 9, 21, allow_short=False, sim_from=sim_from)
        m_ls = simulate_ema_cross_ls(part, 9, 21, allow_short=True, sim_from=sim_from)
        print(f"\n  {label} ({w_start} -> {part.index[-1].date()}):")
        print(f"    Long/Flat : n={m_lf['n_trades']:>3}  WinRate={m_lf['win_rate']:.1%}  PF={m_lf['profit_factor']:.2f}  "
              f"TotalReturn={m_lf['total_return']:+.1%}  CAGR={m_lf['cagr']:+.1%}  MaxDD={m_lf['max_dd']:.1%}")
        print(f"    Long/Short: n={m_ls['n_trades']:>3}  WinRate={m_ls['win_rate']:.1%}  PF={m_ls['profit_factor']:.2f}  "
              f"TotalReturn={m_ls['total_return']:+.1%}  CAGR={m_ls['cagr']:+.1%}  MaxDD={m_ls['max_dd']:.1%}")

    print(
        "\nNote: the short leg does NOT model perpetual funding-rate cost (no funding-rate\n"
        "data source in this repo yet) - real short P&L would be lower whenever funding is\n"
        "positive (shorts pay longs), which is common during BTC uptrends/chop."
    )

    print("\n" + "=" * 78)
    print("RISK-SIZED ACCOUNT SIMULATION ($100k, 1% risk/trade, long/flat only)")
    print("=" * 78)
    print("All backtest parameters:")
    print(f"  Asset / timeframe     : BTCUSDT, 1D (Binance spot klines)")
    print(f"  Signal                : EMA{9} close-cross EMA{21} (long above, flat below)")
    print(f"  Direction             : long/flat only (long/short tested worse, see note above)")
    print(f"  Fill timing           : signal on bar close, filled at NEXT bar's open")
    print(f"  Commission            : {COMMISSION:.2%} per side (entry and exit)")
    print(f"  Slippage              : not modeled")
    print(f"  Starting capital      : ${STARTING_CAPITAL:,.0f}")
    print(f"  Risk per trade        : {RISK_PCT:.1%} of CURRENT equity (compounding)")
    print(f"  Stop-loss             : entry - {ATR_STOP_MULT} x ATR({ATR_PERIOD}), NOT part of the original")
    print(f"                          sheet strategy - added here to make risk sizing meaningful")
    print(f"  Stop fill assumption  : exact stop price if that day's low touches it (no gap-through)")
    print(f"  Leverage              : none - position notional capped at available equity;")
    print(f"                          if the risk-based size would need >1x, size is capped and")
    print(f"                          actual $ risk on that trade is below the {RISK_PCT:.0%} target")
    print(f"  IS/OOS split          : {IS_FRACTION:.0%}/{1-IS_FRACTION:.0%}, split at {is_df.index[-1].date()}")
    print(f"  IS window             : {is_df.index[0].date()} -> {is_df.index[-1].date()} ({len(is_df)} bars)")
    print(f"  OOS window            : {oos_df.index[0].date()} -> {oos_df.index[-1].date()} ({len(oos_df)} bars)")

    for label, part, sim_from in windows:
        m = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, RISK_PCT, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
        w_start = sim_from.date() if sim_from is not None else part.index[0].date()
        print(f"\n  {label} ({w_start} -> {part.index[-1].date()}):")
        print(f"    n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  "
              f"AvgR={m['avg_r']:+.2f}  StoppedOut={m['n_stopped']}/{m['n_trades']}  "
              f"SizeCapped={m['n_capped']}/{m['n_trades']}")
        print(f"    EndEquity=${m['end_equity']:,.0f}  TotalReturn={m['total_return']:+.1%}  "
              f"CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")

    print("\n" + "=" * 78)
    print("FUNDED-CHALLENGE COMPLIANCE CHECK (100k, max 3%/day loss, 10% profit target -")
    print("same rules/methodology as ou_paper_backtest/oos_holdout_challenge_profiles.py)")
    print("=" * 78)
    print("Evaluated on OOS only (the genuine holdout, per this repo's own convention).")
    challenge_profiles = [
        ("baseline_1pct_noBE", 0.01, None),
        ("conservative_0.25pct_noBE", 0.0025, None),
        ("baseline_1pct_BE1R", 0.01, 1.0),
        ("conservative_0.25pct_BE1R", 0.0025, 1.0),
    ]
    for label, risk_pct, be_r in challenge_profiles:
        m = simulate_risk_sized(full, 9, 21, STARTING_CAPITAL, risk_pct, ATR_PERIOD, ATR_STOP_MULT,
                                 be_trigger_r=be_r, sim_from=oos_split_date)
        breach = "BREACHED" if m["breached_3pct_daily_rule"] else "ok"
        days = m["days_to_10pct_target"] if m["days_to_10pct_target"] is not None else "not reached"
        print(f"\n  {label}:")
        print(f"    n={m['n_trades']:>3}  WinRate={m['win_rate']:.1%}  PF={m['profit_factor']:.2f}  "
              f"CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}")
        print(f"    WorstDay={m['worst_day_pct']:+.2f}% ({m['worst_day_date'].date()})  "
              f"3%-Regel={breach}  10%-Ziel erreicht nach={days} Tagen")

    print("\n" + "=" * 78)
    print("OWN-CAPITAL ACCOUNT, NO EXTERNAL LIMITS (no daily-loss rule, no profit-target")
    print("deadline - risk_pct sweep, judged on CAGR/MaxDD/Calmar for long-horizon growth)")
    print("=" * 78)
    risk_sweep = [0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08, 0.12]
    for label, part, sim_from in windows:
        w_start = sim_from.date() if sim_from is not None else part.index[0].date()
        print(f"\n  {label} ({w_start} -> {part.index[-1].date()}):")
        for risk_pct in risk_sweep:
            m = simulate_risk_sized(part, 9, 21, STARTING_CAPITAL, risk_pct, ATR_PERIOD, ATR_STOP_MULT, sim_from=sim_from)
            calmar = m["cagr"] / abs(m["max_dd"]) if m["max_dd"] < 0 else float("nan")
            print(f"    risk={risk_pct:.1%}: n={m['n_trades']:>3}  PF={m['profit_factor']:.2f}  "
                  f"CAGR={m['cagr']:+.1%}  MaxDD={m['max_dd']:.1%}  Calmar={calmar:.2f}  "
                  f"WorstDay={m['worst_day_pct']:+.2f}%  SizeCapped={m['n_capped']}/{m['n_trades']}  "
                  f"EndEquity=${m['end_equity']:,.0f}")
    print(
        "\nNote: 'no limits' still keeps the no-leverage cap (spot BTC, position notional <= equity) -\n"
        "leverage was never needed at 1% risk (see SizeCapped counts above); at higher risk_pct it may\n"
        "start binding, which the SizeCapped column would show. Same OOS caveat as everywhere else in\n"
        "this script: OOS is the only fenster that hasn't been looked at during tuning - IS numbers are\n"
        "more optimistic by construction and shouldn't be used alone to pick a risk_pct."
    )


if __name__ == "__main__":
    main()
