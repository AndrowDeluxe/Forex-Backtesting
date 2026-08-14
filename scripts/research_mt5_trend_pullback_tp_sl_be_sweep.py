"""Follow-up to scripts/research_mt5_trend_pullback_adx_filter.py: with the
ADX>=25 filter now established (chosen on IS, held fixed here), this sweeps
the bot's other two free parameters - the ATR stop multiple (SL) and the
R-multiple take-profit target (TP), currently 2.0/2.0 in the live bot's
config.py - plus tests adding a breakeven-stop trigger (BE, not in the live
bot at all) on top of the winning TP/SL combo.

Same discipline as every other pass in this series:
  - ONE (stop_atr_mult, take_profit_r) combo is chosen on the IS period
    (2016-2022), POOLED across all 5 markets (not tuned per-market)
  - applied UNTOUCHED to OOS (2023-2026)
  - a breakeven-trigger sub-sweep is then run ON TOP of that chosen combo,
    again selected on IS only and validated untouched on OOS
  - outlier-sensitivity check on the final OOS result

ADX>=25 filter is held fixed throughout (not re-swept jointly with TP/SL/BE
- three simultaneous free dimensions on ~180 pooled IS trades would spread
the sample too thin per cell and multiply the overfitting risk further).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
CHOSEN_ADX_MIN = 25.0

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]

STOP_ATR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_R_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
BE_TRIGGER_CANDIDATES = [None, 0.5, 1.0, 1.5]
MIN_IS_TRADES = 30


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def combined(trades_by_market: dict, index_by_market: dict) -> dict:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    if not starts:
        return summarize(combined_trades, pd.DatetimeIndex([]))
    full_index = pd.date_range(min(starts), max(ends), freq="D")
    return summarize(combined_trades, full_index)


def run_period(data: dict, cfg_kwargs: dict, start: pd.Timestamp | None, end: pd.Timestamp | None) -> dict:
    trades_by_market, idx_by_market = {}, {}
    for label, (signaled, spread_bps) in data.items():
        cfg = BacktestConfig(spread_bps=spread_bps, **cfg_kwargs)
        trades = simulate_trades(signaled, cfg)
        if start is not None:
            trades = trades[trades["entry_time"] >= start]
        if end is not None:
            trades = trades[trades["entry_time"] < end]
        sub_idx = signaled.index
        if start is not None:
            sub_idx = sub_idx[sub_idx >= start]
        if end is not None:
            sub_idx = sub_idx[sub_idx < end]
        trades_by_market[label], idx_by_market[label] = trades, sub_idx
    return combined(trades_by_market, idx_by_market), trades_by_market, idx_by_market


def main():
    print("Loading 5 markets (ADX>=25 filter, cached from prior runs where available) ...")
    data = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        signaled = run_pipeline(df, adx_min=CHOSEN_ADX_MIN)
        data[label] = (signaled, spread_bps)
        print(f"  {label}: {len(df)} bars")

    print("\n" + "=" * 78)
    print(f"0. BASELINE TP/SL (bot default: stop_atr=2.0, tp_r=2.0) -- for reference")
    print("=" * 78)
    base_kwargs = {"stop_atr_mult": 2.0, "use_vwap_target": False, "take_profit_r": 2.0}
    s_full, _, _ = run_period(data, base_kwargs, None, None)
    s_is, _, _ = run_period(data, base_kwargs, None, SPLIT)
    s_oos, _, _ = run_period(data, base_kwargs, SPLIT, None)
    print(f"  Full: {fmt(s_full)}")
    print(f"  IS  : {fmt(s_is)}")
    print(f"  OOS : {fmt(s_oos)}")

    print("\n" + "=" * 78)
    print("1. TP/SL SWEEP -- IS PERIOD ONLY (2016-2022), pooled across all 5 markets")
    print("=" * 78)
    rows = []
    for stop_atr in STOP_ATR_CANDIDATES:
        for tp_r in TP_R_CANDIDATES:
            kwargs = {"stop_atr_mult": stop_atr, "use_vwap_target": False, "take_profit_r": tp_r}
            s, _, _ = run_period(data, kwargs, None, SPLIT)
            rows.append({"stop_atr": stop_atr, "tp_r": tp_r, **s})
            print(f"  stop={stop_atr:.1f} tp={tp_r:.1f}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} pooled IS trades -- stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    chosen_stop, chosen_tp = float(best["stop_atr"]), float(best["tp_r"])
    print(f"\nChosen (best pooled-IS Sharpe, n>={MIN_IS_TRADES}): stop_atr={chosen_stop}, tp_r={chosen_tp}")
    print(f"  IS with chosen combo: {fmt(best.to_dict())}")

    print("\n" + "=" * 78)
    print("2. TP/SL VALIDATION -- unveraendert auf Out-of-Sample (2023-2026)")
    print("=" * 78)
    chosen_kwargs = {"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp}
    s_oos_chosen, oos_trades_by_market, oos_idx_by_market = run_period(data, chosen_kwargs, SPLIT, None)
    print(f"  OOS with chosen TP/SL: {fmt(s_oos_chosen)}")
    print(f"  OOS baseline (2.0/2.0, from step 0): {fmt(s_oos)}")
    for label, t in oos_trades_by_market.items():
        print(f"    {label:<8} {fmt(summarize(t, oos_idx_by_market[label]))}")

    print("\n" + "=" * 78)
    print(f"3. BREAKEVEN-TRIGGER SWEEP on top of stop={chosen_stop}/tp={chosen_tp} -- IS ONLY")
    print("=" * 78)
    be_rows = []
    for be in BE_TRIGGER_CANDIDATES:
        kwargs = {"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp, "breakeven_trigger_r": be}
        s, _, _ = run_period(data, kwargs, None, SPLIT)
        be_rows.append({"be_trigger_r": be, **s})
        print(f"  be_trigger={str(be):>4}  {fmt(s)}")

    be_sweep = pd.DataFrame(be_rows)
    be_eligible = be_sweep[be_sweep["n_trades"] >= MIN_IS_TRADES]
    be_best = be_eligible.loc[be_eligible["sharpe"].idxmax()]
    chosen_be = None if pd.isna(be_best["be_trigger_r"]) else float(be_best["be_trigger_r"])
    print(f"\nChosen BE trigger (best pooled-IS Sharpe): {chosen_be}")

    print("\n" + "=" * 78)
    print("4. BREAKEVEN VALIDATION -- unveraendert auf Out-of-Sample (2023-2026)")
    print("=" * 78)
    final_kwargs = {"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp, "breakeven_trigger_r": chosen_be}
    s_oos_final, final_trades_by_market, final_idx_by_market = run_period(data, final_kwargs, SPLIT, None)
    print(f"  OOS with stop={chosen_stop}/tp={chosen_tp}/be={chosen_be}: {fmt(s_oos_final)}")
    print(f"  OOS with stop={chosen_stop}/tp={chosen_tp}/no BE (from step 2): {fmt(s_oos_chosen)}")
    print(f"  OOS baseline (2.0/2.0, no BE, from step 0): {fmt(s_oos)}")

    print("\n" + "=" * 78)
    print("5. OUTLIER-SENSITIVITY CHECK ON FINAL POOLED OOS (drop single best trade)")
    print("=" * 78)
    all_final = pd.concat(final_trades_by_market.values(), ignore_index=True)
    if all_final.empty:
        print("  No OOS trades -- cannot check.")
    else:
        sorted_ret = all_final["return_pct"].sort_values(ascending=False)
        without_best = all_final.drop(index=sorted_ret.index[0])
        full_index = pd.date_range(min(idx.min() for idx in final_idx_by_market.values()), max(idx.max() for idx in final_idx_by_market.values()), freq="D")
        s_wo = summarize(without_best, full_index)
        print(f"  OOS PF with best trade:    {s_oos_final['profit_factor']:.3f}  (Sharpe {s_oos_final['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")

    print("\n" + "=" * 78)
    print("6. SUMMARY -- FULL PERIOD, all three configs (reference only, not a validation)")
    print("=" * 78)
    s_full_chosen, _, _ = run_period(data, chosen_kwargs, None, None)
    s_full_final, _, _ = run_period(data, final_kwargs, None, None)
    print(f"  Bot default (2.0/2.0, no BE):        {fmt(s_full)}")
    print(f"  Optimized TP/SL ({chosen_stop}/{chosen_tp}, no BE):  {fmt(s_full_chosen)}")
    print(f"  Optimized TP/SL + BE={chosen_be}:            {fmt(s_full_final)}")


if __name__ == "__main__":
    main()
