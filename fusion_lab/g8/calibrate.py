"""Kalibrierung des G8-Nachbaus gegen die veroeffentlichten SMH-Tabellen.

Vergleicht je Normierung (model.NORMS), Datenquelle (FRED/Dukascopy) und
Datums-Ausrichtung (Stand-Tag selbst / Vortag) die Horizont-Werte 1W/1M/3M
und den Score mit fusion_lab/data/g8/snapshots.csv. Das ist Anpassung an die
Definition des Originals, nicht an Renditen -- zaehlt nicht als Backtest-Versuch.

    python -m fusion_lab.g8.calibrate
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from fusion_lab.g8.data import log_values, usd_value_panel
from fusion_lab.g8.model import NORMS, horizon_scores

SNAPSHOTS = Path(__file__).resolve().parents[1] / "data" / "g8" / "snapshots.csv"


def compare(snap: pd.DataFrame, logv: pd.DataFrame, norm: str, lag_days: int) -> dict:
    hs = horizon_scores(logv, norm)
    rows = []
    for stand, g in snap.groupby("stand_date"):
        t = pd.Timestamp(stand) - pd.Timedelta(days=lag_days)
        idx = logv.index[logv.index <= t]
        if len(idx) == 0:
            continue
        d = idx[-1]
        if (t - d).days > 4:  # Datenquelle reicht nicht bis zum Stichtag
            continue
        for r in g.itertuples():
            ours = {k: float(hs[k].loc[d, r.currency]) for k in ("w1", "m1", "m3")}
            rows.append({"stand": stand, "ccy": r.currency, **{f"o_{k}": v for k, v in ours.items()},
                         "w1": r.w1, "m1": r.m1, "m3": r.m3, "score": r.score})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"n_days": 0}
    df["o_score"] = df[["o_w1", "o_m1", "o_m3"]].mean(axis=1)
    rank_corr = df.groupby("stand").apply(lambda g: g.score.corr(g.o_score, method="spearman"),
                                          include_groups=False)
    return {
        "n_days": int(df.stand.nunique()),
        "mae_w1": round(float((df.w1 - df.o_w1).abs().mean()), 3),
        "mae_m1": round(float((df.m1 - df.o_m1).abs().mean()), 3),
        "mae_m3": round(float((df.m3 - df.o_m3).abs().mean()), 3),
        "mae_score": round(float((df.score - df.o_score).abs().mean()), 3),
        "corr_score": round(float(df.score.corr(df.o_score)), 3),
        "rank_corr_mean": round(float(rank_corr.mean()), 3),
        "slope_score": round(float(np.polyfit(df.o_score, df.score, 1)[0]), 2),
    }


def main() -> int:
    snap = pd.read_csv(SNAPSHOTS)
    out = []
    for source in ("fred", "duka"):
        logv = log_values(usd_value_panel(source, start="1999-01-01" if source == "fred" else "2003-01-01"))
        for norm in NORMS:
            for lag in (0, 1):
                out.append({"source": source, "norm": norm, "lag": lag, **compare(snap, logv, norm, lag)})
    res = pd.DataFrame(out).sort_values("mae_score")
    print(res.to_string(index=False))
    res.to_csv(SNAPSHOTS.parent / "calibration.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
