"""Briefing-Kennzahlen (Folie 11) und Pruefliste (Folie 8) aus einer Trade-Liste.

Trades: DataFrame mit Spalten entry_time (UTC), pnl_r (Netto-Ergebnis in R)
und optional pnl_bps. R = Ergebnis / Risiko je Trade; bei Zeit-Exit ohne
Stop ist R auf eine feste Risikoeinheit normiert (siehe Kandidat).
"""

import math

import numpy as np
import pandas as pd


def metrics(tr: pd.DataFrame, col: str = "pnl_r") -> dict:
    x = tr[col].dropna().to_numpy()
    n = len(x)
    if n == 0:
        return {"n": 0}
    wins, losses = x[x > 0].sum(), -x[x < 0].sum()
    eq = np.cumsum(x)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    years = max((tr["entry_time"].max() - tr["entry_time"].min()).days / 365.25, 1e-9)
    sd = x.std(ddof=1) if n > 1 else float("nan")
    return {
        "n": n,
        "pf": float(wins / losses) if losses > 0 else float("inf"),
        "avg": float(x.mean()),
        "sum": float(x.sum()),
        "maxdd": dd,
        "per_year": n / years,
        "t": float(x.mean() / sd * math.sqrt(n)) if n > 1 and sd > 0 else float("nan"),
        "winrate": float((x > 0).mean()),
    }


def halves(tr: pd.DataFrame, col: str = "pnl_r") -> tuple[dict, dict]:
    tr = tr.sort_values("entry_time")
    mid = len(tr) // 2
    return metrics(tr.iloc[:mid], col), metrics(tr.iloc[mid:], col)


def without_best(tr: pd.DataFrame, k: int = 5, col: str = "pnl_r") -> dict:
    return metrics(tr.drop(tr[col].nlargest(k).index), col)


def by_year(tr: pd.DataFrame, col: str = "pnl_r") -> pd.DataFrame:
    g = tr.groupby(tr["entry_time"].dt.year)[col]
    return pd.DataFrame({"n": g.size(), "sum": g.sum().round(2), "avg": g.mean().round(3)})


def fmt(m: dict) -> str:
    if not m.get("n"):
        return "keine Trades"
    return (f"n={m['n']}  PF={m['pf']:.2f}  Ø={m['avg']:+.3f}R  Σ={m['sum']:+.1f}R  "
            f"MaxDD={m['maxdd']:.1f}R  /Jahr={m['per_year']:.0f}  t={m['t']:.2f}  WR={m['winrate']:.0%}")
