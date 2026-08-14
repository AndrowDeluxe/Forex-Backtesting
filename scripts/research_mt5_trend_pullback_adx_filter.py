"""Follow-up to scripts/research_mt5_trend_pullback.py: the baseline
replication of the live bot's strategy showed edge concentrated in high-ADX
(>=25) bars in every market (regime decomposition), while the strategy was
flat-to-losing in EVERY market 2016-2022 (PF 0.48-0.97) and only profitable
2023-2026. This script tests whether an ADX floor - NOT part of the live
bot, which has no regime filter at all - would have helped, with the same
discipline as scripts/research_gold_trend_pullback_atr_regime_filter.py:

  - entry/exit params stay exactly the bot's own (EMA150/RSI14x35/ATR14x2.0/
    RR2.0) - not re-tuned here, only gated by adx_min
  - ONE adx_min is swept and chosen on the IS period (2016-2022), POOLED
    across all 5 markets (not tuned per-market - that would multiply the
    multiple-testing risk fivefold for a bot that treats all 5 markets
    identically anyway)
  - the chosen filter is then applied UNTOUCHED to OOS (2023-2026)
  - outlier-sensitivity check on the OOS result (single best trade dropped)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import ATR_STOP_MULT, RR_RATIO, run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")

MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]

ADX_MIN_CANDIDATES = [None, 15, 20, 25, 30, 35]
MIN_IS_TRADES = 20


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def load_markets() -> dict:
    data = {}
    for key, tf, label, spread_bps in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = (df, spread_bps)
    return data


def combined_summary(trades_by_market: dict, index_by_market: dict) -> dict:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    if not starts:
        return summarize(combined_trades, pd.DatetimeIndex([]))
    full_index = pd.date_range(min(starts), max(ends), freq="D")
    return summarize(combined_trades, full_index)


def main():
    print("Loading 5 markets (cached from the baseline run where available) ...")
    data = load_markets()
    for label, (df, _) in data.items():
        print(f"  {label}: {len(df)} bars")

    print("\n" + "=" * 78)
    print("0. BASELINE - no ADX filter (for reference)")
    print("=" * 78)
    base_full, base_is, base_oos = {}, {}, {}
    base_full_idx, base_is_idx, base_oos_idx = {}, {}, {}
    for label, (df, spread_bps) in data.items():
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        base_full[label], base_full_idx[label] = trades, signaled.index
        base_is[label] = trades[trades["entry_time"] < SPLIT]
        base_is_idx[label] = signaled[signaled.index < SPLIT].index
        base_oos[label] = trades[trades["entry_time"] >= SPLIT]
        base_oos_idx[label] = signaled[signaled.index >= SPLIT].index
    print(f"  Full: {fmt(combined_summary(base_full, base_full_idx))}")
    print(f"  IS  : {fmt(combined_summary(base_is, base_is_idx))}")
    print(f"  OOS : {fmt(combined_summary(base_oos, base_oos_idx))}")

    print("\n" + "=" * 78)
    print("1. ADX FILTER SWEEP - IS PERIOD ONLY (2016-2022), pooled across all 5 markets")
    print("=" * 78)
    rows = []
    for adx_min in ADX_MIN_CANDIDATES:
        is_trades, is_idx = {}, {}
        for label, (df, spread_bps) in data.items():
            signaled = run_pipeline(df, adx_min=adx_min)
            is_mask = signaled.index < SPLIT
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades = simulate_trades(signaled[is_mask], cfg)
            is_trades[label], is_idx[label] = trades, signaled[is_mask].index
        s = combined_summary(is_trades, is_idx)
        rows.append({"adx_min": adx_min, **s})
        print(f"  adx_min={str(adx_min):>4}  {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo adx_min reaches {MIN_IS_TRADES} pooled IS trades - stopping.")
        return
    best = eligible.loc[eligible["sharpe"].idxmax()]
    chosen_adx = None if pd.isna(best["adx_min"]) else float(best["adx_min"])
    print(f"\nChosen filter (best pooled-IS Sharpe, n>={MIN_IS_TRADES}): adx_min={chosen_adx}")
    print(f"  Pooled IS with chosen filter: {fmt(best.to_dict())}")

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - filter applied UNTOUCHED to 2023-2026")
    print("=" * 78)
    oos_trades, oos_idx = {}, {}
    per_market_oos = {}
    for label, (df, spread_bps) in data.items():
        signaled = run_pipeline(df, adx_min=chosen_adx)
        oos_mask = signaled.index >= SPLIT
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled[oos_mask], cfg)
        oos_trades[label], oos_idx[label] = trades, signaled[oos_mask].index
        per_market_oos[label] = summarize(trades, signaled[oos_mask].index)
    for label, s in per_market_oos.items():
        print(f"  {label:<7}: {fmt(s)}")
    oos_combined = combined_summary(oos_trades, oos_idx)
    print(f"\n  Pooled OOS with chosen filter: {fmt(oos_combined)}")
    print(f"  Pooled OOS baseline (no filter, from step 0): {fmt(combined_summary(base_oos, base_oos_idx))}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON POOLED OOS (drop single best trade)")
    print("=" * 78)
    all_oos = pd.concat(oos_trades.values(), ignore_index=True)
    if all_oos.empty:
        print("  No OOS trades with this filter - cannot check.")
    else:
        sorted_ret = all_oos["return_pct"].sort_values(ascending=False)
        without_best = all_oos.drop(index=sorted_ret.index[0])
        full_index = pd.date_range(min(idx.min() for idx in oos_idx.values()), max(idx.max() for idx in oos_idx.values()), freq="D")
        s_full = summarize(all_oos, full_index)
        s_wo = summarize(without_best, full_index)
        print(f"  Pooled OOS PF with best trade:    {s_full['profit_factor']:.3f}  (Sharpe {s_full['sharpe']:.2f})")
        print(f"  Pooled OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")
        if s_wo["profit_factor"] <= 1.0:
            print("  -> OOS edge collapses without the single best trade: not robust.")
        else:
            print("  -> OOS PF stays above 1.0 without the single best trade.")

    print("\n" + "=" * 78)
    print("4. FULL PERIOD WITH CHOSEN FILTER (for reference only, NOT a validation)")
    print("=" * 78)
    full_trades, full_idx = {}, {}
    for label, (df, spread_bps) in data.items():
        signaled = run_pipeline(df, adx_min=chosen_adx)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        full_trades[label], full_idx[label] = trades, signaled.index
    for label, trades in full_trades.items():
        print(f"  {label:<7}: {fmt(summarize(trades, full_idx[label]))}")
    print(f"\n  Pooled: {fmt(combined_summary(full_trades, full_idx))}")


if __name__ == "__main__":
    main()
