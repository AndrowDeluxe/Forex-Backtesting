"""Cost-sensitivity follow-up to the Gold-Bitcoin dual-momentum backtest
(scripts/research_gold_bitcoin_dual_momentum.py), which so far only used
raw price returns with no trading costs at all. This applies per-asset
round-trip transaction costs, charged only when the held asset actually
switches (cash<->gold<->btc), across three cost tiers to see how much of
the edge survives realistic execution costs.

Cost tiers (round-trip, basis points):
  - Tight (institutional-ish spot access): Gold 5bp, Bitcoin 15bp
  - Realistic retail (typical spot/CFD broker + retail crypto exchange
    taker fees ~0.075-0.1% per leg): Gold 10bp, Bitcoin 30bp
  - Expensive retail (wider spreads, app-based broker, lower liquidity
    hours): Gold 20bp, Bitcoin 60bp

These are estimates, not quotes from a specific broker - the point is the
sensitivity curve, not a precise cost figure. Whichever venue is picked for
live execution, its actual quoted spread/fee should replace these.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from gold_bitcoin_dual_momentum.data import fetch_weekly_gold_btc
from gold_bitcoin_dual_momentum.engine import simulate_dual_momentum

START, END = "2017-08-20", "2026-07-29"
COMPOSITE_SET = [4, 8, 12]
WARMUP_WEEKS = 40
VOL_CAP = 0.20
SPLIT = None  # set after data is loaded (needs tz)

COST_TIERS = {
    "Tight":      {"gold": 5.0,  "btc": 15.0},
    "Realistic":  {"gold": 10.0, "btc": 30.0},
    "Expensive":  {"gold": 20.0, "btc": 60.0},
}


def perf_metrics(weekly_returns: pd.Series) -> dict:
    r = weekly_returns.dropna()
    if len(r) == 0:
        return {"ann_return": float("nan"), "ann_vol": float("nan"), "sharpe": float("nan"), "max_dd": float("nan"), "calmar": float("nan"), "hit_rate": float("nan"), "n_weeks": 0}
    n_years = len(r) / 52
    growth = (1 + r).prod()
    ann_return = growth ** (1 / n_years) - 1
    ann_vol = r.std() * np.sqrt(52)
    sharpe = ann_return / ann_vol if ann_vol > 0 else float("nan")
    equity = (1 + r).cumprod()
    max_dd = (equity / equity.cummax() - 1).min()
    calmar = ann_return / abs(max_dd) if max_dd < 0 else float("nan")
    hit_rate = (r > 0).mean()
    return {"ann_return": ann_return, "ann_vol": ann_vol, "sharpe": sharpe, "max_dd": max_dd, "calmar": calmar, "hit_rate": hit_rate, "n_weeks": len(r)}


def fmt(m: dict) -> str:
    return (
        f"Return={m['ann_return']:+.2%}  Vol={m['ann_vol']:.2%}  Sharpe={m['sharpe']:.2f}  "
        f"MaxDD={m['max_dd']:.2%}  Calmar={m['calmar']:.2f}  Hit={m['hit_rate']:.1%}  n={m['n_weeks']}"
    )


def count_switches(held_position: pd.Series) -> int:
    hp = held_position.dropna()
    return int((hp != hp.shift(1)).iloc[1:].sum())


def composite_series(weekly, vol_cap, cost_bps, warmup):
    parts = []
    n_switches = 0
    for lb in COMPOSITE_SET:
        sim = simulate_dual_momentum(weekly, lookback_weeks=lb, vol_cap=vol_cap, switch_cost_bps=cost_bps)
        parts.append(sim["strategy_return"].iloc[warmup:])
        n_switches += count_switches(sim["held_position"].iloc[warmup:])
    combined = pd.concat(parts, axis=1).mean(axis=1)
    return combined, n_switches


def main():
    global SPLIT
    print(f"Fetching weekly GOLD/BTC {START} -> {END} ...")
    weekly = fetch_weekly_gold_btc(START, END)
    SPLIT = pd.Timestamp("2024-02-01", tz=weekly.index.tz)
    print(f"{len(weekly)} weekly bars")

    print("\n" + "=" * 90)
    print("COST SENSITIVITY -- vol-capped composite (X=4/8/12w avg), no cost vs 3 cost tiers")
    print("=" * 90)
    no_cost, n_switch_free = composite_series(weekly, VOL_CAP, None, WARMUP_WEEKS)
    print(f"  No cost (baseline)   {fmt(perf_metrics(no_cost))}   switches(sum of 3 sub-books)={n_switch_free}")
    for tier_name, costs in COST_TIERS.items():
        ret, n_switch = composite_series(weekly, VOL_CAP, costs, WARMUP_WEEKS)
        print(f"  {tier_name:<10}Gold={costs['gold']}bp/Btc={costs['btc']}bp  {fmt(perf_metrics(ret))}   switches={n_switch}")

    print("\n" + "=" * 90)
    print("COST SENSITIVITY -- single best lookback (X=8w, pure) for comparison")
    print("=" * 90)
    for tier_name, costs in [("No cost", None)] + list(COST_TIERS.items()):
        sim = simulate_dual_momentum(weekly, lookback_weeks=8, vol_cap=VOL_CAP, switch_cost_bps=costs)
        ret = sim["strategy_return"].iloc[WARMUP_WEEKS:]
        n_switch = count_switches(sim["held_position"].iloc[WARMUP_WEEKS:])
        label = "No cost" if costs is None else f"{tier_name} Gold={costs['gold']}bp/Btc={costs['btc']}bp"
        print(f"  {label:<32}{fmt(perf_metrics(ret))}   switches={n_switch}")

    print("\n" + "=" * 90)
    print("IS/OOS UNDER REALISTIC COSTS -- vol-capped composite")
    print("=" * 90)
    ret, _ = composite_series(weekly, VOL_CAP, COST_TIERS["Realistic"], WARMUP_WEEKS)
    is_ret = ret[ret.index < SPLIT]
    oos_ret = ret[ret.index >= SPLIT]
    print(f"  Full: {fmt(perf_metrics(ret))}")
    print(f"  IS  : {fmt(perf_metrics(is_ret))}")
    print(f"  OOS : {fmt(perf_metrics(oos_ret))}")


if __name__ == "__main__":
    main()
