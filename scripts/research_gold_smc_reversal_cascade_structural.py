"""Follow-up to research_gold_smc_reversal_cascade.py (chat 2026-08-19): the
first pass only swept EXIT params (stop/be/tp) against 4 fixed on/off
confirmation-layer variants, leaving every STRUCTURAL param at its
smoke-test default. This sweeps h4_confirm_bars, h1_valid_bars,
ema_length/ema_smooth (ema_reject variant), and ribbon_extension_atr_min
(both variant) - identified as the two biggest untapped levers: (1) 24%
of OOS trades still exit via max_hold (residual indecisive-entry
symptom from the old single-confirmation mean_reversion.py), (2)
structural params were never tuned, only left at defaults.

Exit params are FIXED at the already-validated winner from the first
script: stop_atr_mult=0.5, breakeven_trigger_r=0.5, tp_mode=h4_level -
this isolates entry-side gains from re-fitting exits, which would just
add spurious degrees of freedom.

Same IS/OOS discipline: sweep on IS only, pick best IS Sharpe (n>=15),
validate untouched on OOS.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h1, fetch_gold_h4, fetch_gold_m15, fetch_gold_w1
from gold_smc_htf_ltf.reversal_cascade import run_pipeline
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15
FIXED_STOP, FIXED_BE = 0.5, 0.5


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"


def eval_config(signaled: pd.DataFrame, max_hold_bars: int):
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=FIXED_STOP, use_vwap_target=True, breakeven_trigger_r=FIXED_BE, max_hold_bars=max_hold_bars)
    is_sig = signaled[signaled.index < SPLIT]
    oos_sig = signaled[signaled.index >= SPLIT]
    is_trades = simulate_trades(is_sig, cfg)
    is_stats = summarize(is_trades, is_sig.index)
    return is_stats, signaled, cfg, oos_sig


def main():
    print(f"Fetching GOLD H4/H1/M15/D1/W1 {START} -> {END} ...")
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    d1 = fetch_gold_d1(START, END)
    w1 = fetch_gold_w1(START, END)
    print(f"H4={len(h4)} H1={len(h1)} M15={len(m15)} D1={len(d1)} W1={len(w1)}")

    rows = []

    print("\n=== 1. h4_confirm_bars x h1_valid_bars (ema_reject, defaults elsewhere) ===")
    for h4_confirm in [30, 50, 80]:
        for h1_valid in [12, 24, 36]:
            signaled = run_pipeline(h4, h1, m15, require_ema_reject=True, h4_confirm_bars=h4_confirm, h1_valid_bars=h1_valid)
            max_hold = h1_valid * 4
            is_stats, signaled, cfg, oos_sig = eval_config(signaled, max_hold)
            rows.append({"axis": "h4_confirm/h1_valid", "h4_confirm_bars": h4_confirm, "h1_valid_bars": h1_valid, "ema_length": 50, "ema_smooth": 15, "ribbon_ext": None, "signaled": signaled, "oos_sig": oos_sig, "cfg": cfg, **is_stats})
            print(f"  h4_confirm={h4_confirm:>3} h1_valid={h1_valid:>3}: {fmt(is_stats)}")

    print("\n=== 2. ema_length x ema_smooth (h4_confirm=50, h1_valid=24 default) ===")
    for ema_length in [30, 50, 80]:
        for ema_smooth in [10, 15, 20]:
            if ema_length == 50 and ema_smooth == 15:
                continue  # already covered by axis 1's default row
            signaled = run_pipeline(h4, h1, m15, require_ema_reject=True, ema_length=ema_length, ema_smooth=ema_smooth)
            is_stats, signaled, cfg, oos_sig = eval_config(signaled, 24 * 4)
            rows.append({"axis": "ema_length/smooth", "h4_confirm_bars": 50, "h1_valid_bars": 24, "ema_length": ema_length, "ema_smooth": ema_smooth, "ribbon_ext": None, "signaled": signaled, "oos_sig": oos_sig, "cfg": cfg, **is_stats})
            print(f"  ema_length={ema_length:>3} ema_smooth={ema_smooth:>3}: {fmt(is_stats)}")

    print("\n=== 3. ribbon_extension_atr_min (both: ema_reject + ribbon_stretch) ===")
    for ext_min in [1.5, 2.0, 2.5, 3.0, 4.0]:
        signaled = run_pipeline(h4, h1, m15, require_ema_reject=True, require_ribbon_stretch=True, d1_df=d1, w1_df=w1, ribbon_extension_atr_min=ext_min)
        is_stats, signaled, cfg, oos_sig = eval_config(signaled, 24 * 4)
        rows.append({"axis": "ribbon_ext (both)", "h4_confirm_bars": 50, "h1_valid_bars": 24, "ema_length": 50, "ema_smooth": 15, "ribbon_ext": ext_min, "signaled": signaled, "oos_sig": oos_sig, "cfg": cfg, **is_stats})
        print(f"  ribbon_ext={ext_min}: {fmt(is_stats)}")

    df = pd.DataFrame(rows)
    eligible = df[df["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"\nNo combo reaches {MIN_IS_TRADES} IS trades.")
        return

    print("\n=== Top 8 structural combos by IS Sharpe ===")
    top8 = eligible.sort_values("sharpe", ascending=False).head(8)
    print(top8[["axis", "h4_confirm_bars", "h1_valid_bars", "ema_length", "ema_smooth", "ribbon_ext", "n_trades", "win_rate", "profit_factor", "sharpe"]].to_string(index=False))

    baseline_row = eligible[(eligible["h4_confirm_bars"] == 50) & (eligible["h1_valid_bars"] == 24) & (eligible["ema_length"] == 50) & (eligible["ema_smooth"] == 15) & (eligible["ribbon_ext"].isna())]
    if not baseline_row.empty:
        print(f"\nBaseline (defaults, ema_reject only) IS: {fmt(baseline_row.iloc[0].to_dict())}")

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\nBest structural combo: h4_confirm={best['h4_confirm_bars']} h1_valid={best['h1_valid_bars']} ema_length={best['ema_length']} ema_smooth={best['ema_smooth']} ribbon_ext={best['ribbon_ext']}")
    print(f"  IS:  {fmt(best.to_dict())}")

    oos_trades = simulate_trades(best["oos_sig"], best["cfg"])
    oos_stats = summarize(oos_trades, best["oos_sig"].index)
    print(f"  OOS: {fmt(oos_stats)}")
    if not oos_trades.empty:
        print("  exit reasons:", oos_trades["exit_reason"].value_counts().to_dict())

    if best["sharpe"] > baseline_row.iloc[0]["sharpe"] + 0.05 if not baseline_row.empty else True:
        print("\n  -> Structural tuning materially improves on the smoke-test defaults." if not baseline_row.empty else "")
    else:
        print("\n  -> Defaults were already close to optimal; no major structural lever found.")


if __name__ == "__main__":
    main()
