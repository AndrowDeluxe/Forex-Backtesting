"""Tests inducement as a STANDALONE entry (chat 2026-08-14), not as a
filter bolted onto the momentum-thrust+pullback signal (that was
require_inducement on gold_trend_pullback_atr... no, gold_m1_momentum_
thrust.pipeline.generate_signal_pullback - the user clarified that's not
what they meant).

Two variants, tested separately as the user asked:
  1. inducement_only: enter immediately on the liquidity-sweep-and-reject
     bar itself, no further confirmation.
  2. inducement_structure: enter only after a subsequent break of
     structure (close back above the swing high that existed at the sweep)
     confirms the reversal - the user's own stated design ("Inducement +
     Struktur-Bestätigung").

Both long-only, both use the lessons already learned this session: no
breakeven (be=0.5/1.0 consistently hurt in the prior sweep), wider TP
tends to help, so TP is swept up to 5x. Same window/discipline as every
other M1 script: 2024-08-01 to 2026-08-01, IS/OOS split 2025-08-01,
spread_bps=8.0, sweep IS -> pick best IS Sharpe -> OOS validate untouched
-> outlier check -> buy-and-hold.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_m1_momentum_thrust.data import fetch_gold_m1
from gold_m1_momentum_thrust.pipeline import run_pipeline_inducement_only, run_pipeline_inducement_structure
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

pd.set_option("display.width", 160)

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
MIN_IS_TRADES = 15

TP_CANDIDATES = [2.0, 3.0, 4.0, 5.0]
SWING_WINDOW_CANDIDATES = [10, 15, 20, 30]
CONFIRM_BARS_CANDIDATES = [10, 20, 40]
STOP_ATR = 2.5


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return (
        f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  "
        f"Sharpe={s['sharpe']:.2f}  CAGR={s['cagr']:+.1%}  MaxDD={s['max_drawdown']:.1%}"
    )


def run_variant(name, df, is_df, oos_df, bh_sharpe, bh_cagr, param_grid_fn, pipeline_fn):
    print("\n" + "=" * 78)
    print(f"VARIANT: {name} - IS sweep")
    print("=" * 78)
    rows = []
    for params, cfg_kwargs, label in param_grid_fn():
        signaled = pipeline_fn(is_df, **params)
        cfg = BacktestConfig(spread_bps=SPREAD_BPS, use_vwap_target=False, **cfg_kwargs)
        trades = simulate_trades(signaled, cfg)
        s = summarize(trades, signaled.index)
        rows.append({"label": label, "params": params, "cfg_kwargs": cfg_kwargs, **s})
        print(f"  {label:<45} {fmt(s)}")

    sweep = pd.DataFrame(rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES]
    if eligible.empty:
        print(f"  No combo reaches {MIN_IS_TRADES} IS trades - skipping OOS.")
        return None

    best = eligible.loc[eligible["sharpe"].idxmax()]
    print(f"\n  Chosen (best IS Sharpe): {best['label']}  {fmt(best.to_dict())}")

    signaled_oos = pipeline_fn(oos_df, **best["params"])
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, use_vwap_target=False, **best["cfg_kwargs"])
    oos_trades = simulate_trades(signaled_oos, cfg)
    oos_stats = summarize(oos_trades, signaled_oos.index)
    print(f"  OOS: {fmt(oos_stats)}")

    robust = False
    if not oos_trades.empty:
        sorted_ret = oos_trades["return_pct"].sort_values(ascending=False)
        without_best = oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, signaled_oos.index)
        robust = s_wo["profit_factor"] > 1.0
        print(f"  Outlier check: PF {oos_stats['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f} without best trade")

    beats_bh = oos_stats["n_trades"] > 0 and oos_stats["sharpe"] > bh_sharpe and oos_stats["cagr"] > bh_cagr
    print(f"  Beats buy-and-hold? {'YES' if beats_bh else 'no'}   Outlier-robust? {'yes' if robust else 'no/n-a'}")
    return {
        "variant": name, "label": best["label"], "oos_n": oos_stats["n_trades"],
        "oos_sharpe": oos_stats["sharpe"], "oos_pf": oos_stats["profit_factor"],
        "oos_cagr": oos_stats["cagr"], "beats_buyhold": beats_bh, "outlier_robust": robust,
    }


def main():
    print(f"Fetching GOLD M1 {START} -> {END} ...")
    df = fetch_gold_m1(START, END)
    print(f"{len(df)} M1 bars")
    is_df = df[df.index < SPLIT]
    oos_df = df[df.index >= SPLIT]

    daily_close = oos_df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    bh_sharpe, bh_cagr, bh_mdd = annualized_sharpe(daily_ret), cagr(daily_ret), max_drawdown(daily_ret)
    print(f"\nBuy & hold Gold (OOS window): Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}  MaxDD={bh_mdd:.1%}")

    leaderboard = []

    def grid_inducement_only():
        for sw in SWING_WINDOW_CANDIDATES:
            for tp in TP_CANDIDATES:
                yield {"swing_window": sw}, {"stop_atr_mult": STOP_ATR, "take_profit_r": tp}, f"swing_window={sw} tp={tp}"

    result = run_variant("inducement_only", df, is_df, oos_df, bh_sharpe, bh_cagr, grid_inducement_only, run_pipeline_inducement_only)
    if result:
        leaderboard.append(result)

    def grid_inducement_structure():
        for sw in SWING_WINDOW_CANDIDATES[:3]:  # [10, 15, 20] - drop 30 here to control combinatorics, already covered by inducement_only
            for cb in CONFIRM_BARS_CANDIDATES:
                for tp in TP_CANDIDATES:
                    yield (
                        {"swing_window": sw, "confirm_bars": cb},
                        {"stop_atr_mult": STOP_ATR, "take_profit_r": tp},
                        f"swing_window={sw} confirm_bars={cb} tp={tp}",
                    )

    result = run_variant("inducement_structure", df, is_df, oos_df, bh_sharpe, bh_cagr, grid_inducement_structure, run_pipeline_inducement_structure)
    if result:
        leaderboard.append(result)

    print("\n" + "=" * 78)
    print("LEADERBOARD")
    print("=" * 78)
    print(f"Buy & hold reference: Sharpe={bh_sharpe:.2f}  CAGR={bh_cagr:+.1%}")
    lb = pd.DataFrame(leaderboard)
    print(lb.to_string(index=False))


if __name__ == "__main__":
    main()
