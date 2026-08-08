"""Research script: full multi-asset version of the Beluská & Vojtko (2026)
pullback system (200-day MA + N-day pullback + 1-day hold, dynamic
equal-weight across simultaneously active signals) - the version that
actually matches the paper's design, as opposed to the single-asset
Gold-only test run earlier in this project (which found no edge).

Scope: SP500, GOLD, OIL, EURUSD (4 of the paper's 6 assets - no EEM/IEF
equivalent in this repo's data stack, see pullback_multiasset/data.py).

Central question this answers: was the earlier "no edge" finding for Gold
alone specific to Gold, or does the SAME single-asset signal fail to add
value even inside the multi-asset design the paper actually tested?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pullback_multiasset.data import fetch_daily_ohlc
from pullback_multiasset.engine import simulate_multiasset_pullback

START, END = "2016-01-01", "2026-07-29"
SPLIT = pd.Timestamp("2021-01-01", tz="UTC")
MA_WINDOW = 200
COST_BPS = 5.0
N_CANDIDATES = [2, 3]


def perf_metrics(daily_returns: pd.Series) -> dict:
    r = daily_returns.dropna()
    active = r[r != 0]
    n_years = len(r) / 252
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    ann_vol = r.std() * np.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float("nan")
    equity = (1 + r).cumprod()
    max_dd = (equity / equity.cummax() - 1).min()
    calmar = ann_return / abs(max_dd) if max_dd < 0 else float("nan")
    hit_rate = (active > 0).mean() if len(active) else float("nan")
    return {
        "ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe, "max_dd": max_dd,
        "calmar": calmar, "hit_rate": hit_rate, "active_days": len(active), "active_pct": len(active) / len(r),
    }


def fmt(m: dict) -> str:
    return (
        f"Return={m['ann_return']:+.2%}  Vol={m['ann_vol']:.2%}  Sharpe={m['sharpe']:.2f}  "
        f"MaxDD={m['max_dd']:.2%}  Calmar={m['calmar']:.2f}  Hit={m['hit_rate']:.1%}  "
        f"active_days={m['active_days']} ({m['active_pct']:.1%})"
    )


def main():
    print(f"Fetching daily SP500/GOLD/OIL/EURUSD {START} -> {END} ...")
    data = fetch_daily_ohlc(START, END)
    for name, df in data.items():
        print(f"  {name}: {len(df)} bars")

    print("\n" + "=" * 78)
    print("1. 4-ASSET DYNAMIC EQUAL-WEIGHT PULLBACK SYSTEM")
    print("=" * 78)
    multi_results = {}
    for n in N_CANDIDATES:
        ret = simulate_multiasset_pullback(data, ma_window=MA_WINDOW, n_down_days=n, cost_bps=COST_BPS)
        multi_results[n] = ret
        print(f"  N={n}  {fmt(perf_metrics(ret))}")

    print("\n" + "=" * 78)
    print("2. GOLD-ONLY REFERENCE (same D1 source, same engine, single asset)")
    print("=" * 78)
    gold_only_results = {}
    for n in N_CANDIDATES:
        ret = simulate_multiasset_pullback({"GOLD": data["GOLD"]}, ma_window=MA_WINDOW, n_down_days=n, cost_bps=COST_BPS)
        gold_only_results[n] = ret
        print(f"  N={n}  {fmt(perf_metrics(ret))}")

    print("\n" + "=" * 78)
    print("3. EQUAL-WEIGHT BUY & HOLD BENCHMARK (4 assets, daily rebalanced)")
    print("=" * 78)
    daily_rets = pd.concat([df["close"].pct_change().rename(name) for name, df in data.items()], axis=1, sort=True)
    bh_ret = daily_rets.mean(axis=1).dropna()
    print(f"  {fmt(perf_metrics(bh_ret))}")

    best_n = max(N_CANDIDATES, key=lambda n: perf_metrics(multi_results[n])["sharpe"])
    print(f"\n" + "=" * 78)
    print(f"4. IS/OOS BREAKDOWN -- 4-asset system, N={best_n} (split={SPLIT.date()})")
    print("=" * 78)
    ret = multi_results[best_n]
    is_ret = ret[ret.index < SPLIT]
    oos_ret = ret[ret.index >= SPLIT]
    print(f"  Full: {fmt(perf_metrics(ret))}")
    print(f"  IS  : {fmt(perf_metrics(is_ret))}")
    print(f"  OOS : {fmt(perf_metrics(oos_ret))}")

    print("\n" + "=" * 78)
    print(f"5. OUTLIER-SENSITIVITY CHECK -- 4-asset system, N={best_n} (drop single best day)")
    print("=" * 78)
    active = ret[ret != 0]
    without_best = ret.drop(index=active.idxmax())
    s_full = perf_metrics(ret)
    s_wo = perf_metrics(without_best)
    print(f"  Full PF-equivalent (Sharpe): {s_full['sharpe']:.2f}")
    print(f"  Without best day Sharpe:     {s_wo['sharpe']:.2f}")

    print(
        "\nReading: compare section 1 (4 assets, dynamic weight) against section 2 (Gold alone, same\n"
        "engine/data/costs) to see whether the multi-asset diversification the paper relies on actually\n"
        "adds value over the single-asset signal, or whether the whole system's edge (if any) is still\n"
        "thin/outlier-driven even with more assets in the mix."
    )


if __name__ == "__main__":
    main()
