"""Remy-King A2: Carry-Korb der G8-Waehrungen.

    python -m scripts.research_remy_a2_carry

Monatsende: Waehrungen nach Leitzins sortieren, long die k hoechsten, short die k
niedrigsten (gleichgewichtet, je Seite Summe 1), gilt ab dem naechsten Handelstag.
Ertrag = Kurs + Zinsdifferenz - Swap-Aufschlag (1 % p.a. je offenem Paar) - halber
Spread je Umschichtung. Risk-off: halbe Groesse, wenn der VIX am Vortag ueber dem
IS-75.-Perzentil liegt. Abstand Long- zu Short-Seite < 0,25 Pp -> flat (Nullzins-Gleichstand).

Overfitting-Sperre `remy_a2_carry`: nur IS-Zahlen, 6 gezaehlte Varianten.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from research_lock import Lock, config_hash, deflated_sharpe
from scripts.remy_common import CCY, CURRENCIES, HALF_SPREAD, SWAP_MARKUP, ccy_returns, fx_closes, rates, stats, vix

LOCK = Lock("remy_a2_carry")
MIN_GAP = 0.25
VARIANTS = list(itertools.product((1, 2, 3), (False, True)))
PAIR_OF = {c: p for p, c in CCY.items()}


def month_end_weights(pr: pd.DataFrame, k: int) -> pd.DataFrame:
    ends = pr.groupby(pr.index.to_period("M")).tail(1)
    rows = {}
    for d, row in ends.iterrows():
        row = row.dropna()
        w = pd.Series(0.0, index=CURRENCIES)
        if len(row) >= 2 * k:
            order = row.sort_values(kind="stable")
            low, high = order.index[:k], order.index[-k:]
            if order[high].mean() - order[low].mean() >= MIN_GAP:
                w[high], w[low] = 1.0 / k, -1.0 / k
        rows[d] = w
    return pd.DataFrame(rows).T


def daily_weights(ret: pd.DataFrame, pr: pd.DataFrame, vx: pd.Series, k: int, riskoff: bool,
                  vix_cut: float) -> pd.DataFrame:
    """Gewichte je Handelstag, schon um einen Tag verschoben (Position fuer den Ertrag von Tag t)."""
    w = month_end_weights(pr, k).reindex(ret.index).ffill().fillna(0.0).shift(1).fillna(0.0)
    if riskoff:
        w = w.mul(np.where(vx.shift(1) > vix_cut, 0.5, 1.0), axis=0)
    return w


def pnl(w: pd.DataFrame, ret: pd.DataFrame, pr: pd.DataFrame) -> pd.Series:
    carry = pr.sub(pr["US"], axis=0) / 100 / 252
    gross = (w * (ret + carry)).sum(axis=1)
    fx = [c for c in CURRENCIES if c != "US"]
    swap = w[fx].abs().sum(axis=1) * SWAP_MARKUP / 252
    turn = sum(w[c].diff().abs().fillna(0.0) * HALF_SPREAD[PAIR_OF[c]] for c in fx)
    return gross - swap - turn


def run(ret: pd.DataFrame, pr: pd.DataFrame, vx: pd.Series, k: int, riskoff: bool, vix_cut: float) -> pd.Series:
    return pnl(daily_weights(ret, pr, vx, k, riskoff, vix_cut), ret, pr)


def main() -> None:
    closes = fx_closes()
    ret = ccy_returns(closes)
    pr = rates(ret.index, "policy_rate")
    vx = vix(ret.index)
    vix_cut = float(LOCK.is_only(vx).quantile(0.75))
    rows = {}
    series = {}
    for k, ro in VARIANTS:
        s = LOCK.is_only(run(ret, pr, vx, k, ro, vix_cut)).iloc[1:]
        series[(k, ro)] = s
        rows[f"k={k} riskoff={'an' if ro else 'aus'}"] = stats(s)
    LOCK.log_trials(len(VARIANTS), "A2 IS-Sweep k x riskoff")
    tab = pd.DataFrame(rows).T
    print(f"IS {LOCK.split['is_start']} .. {LOCK.split['is_end']}, VIX-Schwelle (IS-p75) {vix_cut:.1f}")
    print(tab[["n", "ret_pa", "vol_pa", "sharpe", "t", "maxdd", "skew"]].round(3).to_string())

    best = max(series, key=lambda v: rows[f"k={v[0]} riskoff={'an' if v[1] else 'aus'}"]["sharpe"])
    b = stats(series[best])
    dsr = deflated_sharpe(b["sr_d"], b["n"], LOCK.trials, b["skew"], b["kurt"],
                          sr_var_trials=float(tab["sr_d"].astype(float).var()))
    print(f"\nBeste: k={best[0]} riskoff={best[1]}  Sharpe {b['sharpe']:.2f}  t {b['t']:.2f}  "
          f"DSR {dsr:.2f} (Versuche {LOCK.trials})")

    s = series[best]
    print("\nJahre (IS, Summe log-Rendite):")
    print(s.groupby(s.index.year).sum().round(3).to_string())
    bucket = pd.cut(vx.reindex(s.index).shift(1), [0, 15, 20, 30, 200])
    print("\nVIX-Vortag (IS): Ø Tagesrendite in bp, Tage")
    print(s.groupby(bucket, observed=True).agg(["mean", "size"]).assign(mean=lambda d: d["mean"] * 1e4).round(2))
    w = month_end_weights(pr, best[0])
    w = LOCK.is_only(w)
    print("\nHaeufigkeit long/short je Waehrung (IS-Monate):")
    print(pd.DataFrame({"long": (w > 0).sum(), "short": (w < 0).sum()}).T.to_string())
    print("\nKonfig-Hash (noch nicht eingefroren):", config_hash({"k": best[0], "riskoff": best[1],
                                                                  "vix_cut": round(vix_cut, 2)}))


if __name__ == "__main__":
    main()
