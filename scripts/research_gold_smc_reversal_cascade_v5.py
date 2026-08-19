"""Follow-up to research_gold_smc_reversal_cascade_v4.py (chat 2026-08-19,
"wir brauchen noch einen Filter fur Highs/Lows die ein Reversal einleiten
konnten wo wir danach mit der H1 Bos Inducement Logik einsteigen"). v4's
H1-inducement change (retest of the FIRST BOS-streak level) made things
WORSE across the board. This targets a different axis: whether the swept
H4 erl_high/erl_low was ever a plausible reversal candidate in the first
place, via three new independent pre-filters on compute_h4_exhaustion
(user approved testing all three plus EMA together, not picking one):
  - require_magnitude: current range (erl_high-erl_low) >= N ATRs
  - require_volume_exhaustion: reuse volume.py's pressure z-score -
    divergence (weak pressure into the extreme)
  - require_level_age: level stood unbroken >= N bars before being swept

h1_bos_min fixed at 2, require_h1_inducement fixed at False (v4's finding).
sweep_mode="double"/tol=0 fixed (v3's finding). Sweeps the 2^3=8 on/off
combos of the three new filters x require_ema_reject (on/off) x exit
params.
"""

import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
H4_CONFIRM_BARS, H1_VALID_BARS = 30, 24
MAX_HOLD_BARS = H1_VALID_BARS * 4

FILTER_AXES = ["magnitude", "volume", "age", "ema"]
STOP_ATR_CANDIDATES = [0.5, 1.0, 1.5]
BE_CANDIDATES = [None, 0.5, 1.0]
MTD = 1.0


def build_kwargs(combo: tuple[bool, ...]) -> dict:
    magnitude, volume, age, ema = combo
    kw = {}
    if magnitude:
        kw.update(require_magnitude=True, magnitude_atr_min=3.0)
    if volume:
        kw.update(require_volume_exhaustion=True, vol_exhaustion_zscore_max=0.0)
    if age:
        kw.update(require_level_age=True, min_level_age_bars=5)
    if ema:
        kw.update(require_ema_reject=True)
    return kw


def label_for(combo: tuple[bool, ...]) -> str:
    names = [name for name, on in zip(FILTER_AXES, combo) if on]
    return "+".join(names) if names else "none"


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def main():
    print(f"Fetching GOLD H4/H1/M15 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)}")

    combos = list(product([False, True], repeat=4))
    print(f"\nRunning pipeline once per filter combo ({len(combos)} combos) ...")
    signaled_by_combo = {}
    for combo in combos:
        kw = build_kwargs(combo)
        sig = run_pipeline(h4, h1, m15, h4_confirm_bars=H4_CONFIRM_BARS, h1_valid_bars=H1_VALID_BARS, min_target_distance_atr=MTD, **kw)
        signaled_by_combo[combo] = sig
        n = int((sig["signal"] != 0).sum())
        print(f"  {label_for(combo):<28}: {n} raw signals")

    print("\n" + "=" * 78)
    print(f"1. SWEEP - IS PERIOD ONLY, spread_bps={SPREAD_BPS}, max_hold_bars={MAX_HOLD_BARS}")
    print("=" * 78)
    rows = []
    for combo, sig in signaled_by_combo.items():
        sig_is = sig[sig.index < SPLIT]
        for stop_mult in STOP_ATR_CANDIDATES:
            for be in BE_CANDIDATES:
                cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
                trades = simulate_trades(sig_is, cfg)
                s = summarize(trades, sig_is.index)
                rows.append({"combo": combo, "label": label_for(combo), "stop_atr": stop_mult, "be": be, **s})

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    print(f"\n{len(sweep)} combos tested, {len(eligible)} reach n>={MIN_IS_TRADES} IS trades")
    if eligible.empty:
        print("Stopping.")
        return
    top15 = eligible.sort_values("sharpe", ascending=False).head(15)
    print("\nTop 15 combos by IS Sharpe:")
    print(top15[["label", "stop_atr", "be", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr"]].to_string(index=False))

    print("\nBest combo PER filter-label (by IS Sharpe, n>=15):")
    for combo in combos:
        lbl = label_for(combo)
        sub = eligible[eligible["label"] == lbl]
        if sub.empty:
            print(f"  {lbl:<28}: no combo reaches n>={MIN_IS_TRADES}")
            continue
        b = sub.loc[sub["sharpe"].idxmax()]
        print(f"  {lbl:<28} stop={b['stop_atr']} be={b['be']}  {fmt(b.to_dict())}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nStandout combo overall (highest IS Sharpe, n>={MIN_IS_TRADES}):")
    print(f"  filters={best['label']}  stop={best['stop_atr']}  be={best['be']}")
    print(f"  {fmt(best.to_dict())}")

    best_combo = best["combo"]
    stop_mult = float(best["stop_atr"])
    be = None if pd.isna(best["be"]) else float(best["be"])

    print("\n" + "=" * 78)
    print("2. OOS VALIDATION - chosen config applied UNTOUCHED to 2025-08 to 2026-08")
    print("=" * 78)
    sig_full = signaled_by_combo[best_combo]
    sig_oos = sig_full[sig_full.index >= SPLIT]
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=stop_mult, use_vwap_target=True, breakeven_trigger_r=be, max_hold_bars=MAX_HOLD_BARS)
    oos_trades = simulate_trades(sig_oos, cfg)
    oos_stats = summarize(oos_trades, sig_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    print("\n" + "=" * 78)
    print("3. OUTLIER-SENSITIVITY CHECK ON OOS (drop single best trade)")
    print("=" * 78)
    if oos_trades.empty:
        print("  No OOS trades - cannot check.")
    else:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, sig_oos.index)
        print(f"  OOS PF with best trade:    {oos_stats['profit_factor']:.3f}  (Sharpe {oos_stats['sharpe']:.2f})")
        print(f"  OOS PF without best trade: {s_wo['profit_factor']:.3f}  (Sharpe {s_wo['sharpe']:.2f})")
        print("  -> " + ("OOS PF stays above 1.0 without the single best trade." if s_wo["profit_factor"] > 1.0 else "OOS edge collapses without the single best trade: not robust."))

    print("\n" + "=" * 78)
    print("4. BUY & HOLD COMPARISON (same OOS window)")
    print("=" * 78)
    m15_oos = m15[m15.index >= SPLIT]
    daily_close = m15_oos["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"  Buy & hold Gold:  Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")
    print(f"  Strategy (OOS):   Sharpe={oos_stats['sharpe']:.2f}  CAGR={oos_stats['cagr']:+.1%}  MaxDD={oos_stats['max_drawdown']:.1%}  n_trades={oos_stats['n_trades']}")
    beats_sharpe = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe
    beats_both = beats_sharpe and oos_stats["cagr"] > bh_cagr
    print(f"\n  Beats buy-and-hold on Sharpe? {'YES' if beats_sharpe else 'no'}   On both Sharpe and CAGR? {'YES' if beats_both else 'no'}")

    print("\n" + "=" * 78)
    print("5. EXIT REASON + DIRECTION BREAKDOWN (OOS)")
    print("=" * 78)
    if not oos_trades.empty:
        print(oos_trades["exit_reason"].value_counts().to_string())
        print()
        print(oos_trades["direction"].value_counts().to_string())


if __name__ == "__main__":
    main()
