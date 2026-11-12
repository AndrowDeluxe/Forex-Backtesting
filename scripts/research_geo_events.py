"""Ereignisstudie Geopolitik (Makro-Agent v3, 12.11.2026): Was passiert nach einer Geopolitik-Spitze?

    python -m scripts.research_geo_events --stage is|oos

Spitze = Tageswert des Geopolitical Risk Index (Caldara/Iacoviello) ueber dem 95. Perzentil der IS-Jahre
2007-2016 und hoeher als an allen 10 Vortagen (erste Spitze einer Welle, keine Doppelzaehlung).
Reaktion = Log-Rendite vom Schluss des Vortags bis Tag 0, +1 und +5 (Handelstage), minus mittlere
Rendite aller Tage im selben Fenster. t ueber die Streuung der Ereignisse.

Overfitting-Sperre `geo_framework_v1`: Schwelle (95. Perzentil) und Fenster vorab fest, nur gezaehlt.
Ergebnis entscheidet, ob ein Geopolitik-Einfluss im Fact Sheet als "belegt" oder "Hypothese" steht.
"""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from fusion_lab.macro_agent import geo_framework as g
from research_lock import Lock

LOCK = Lock("geo_framework_v1")
SPLIT = ("2007-01-01", "2016-12-31", "2026-05-10", "2026-11-10")
PCT = 0.95
COOLDOWN = 10
HORIZONS = (0, 1, 5)
OUT = g.ROOT / "fusion_lab" / "data" / "macro_agent" / "geo_events.json"


def spikes(gpr: pd.Series, threshold: float) -> pd.DatetimeIndex:
    hi = gpr > threshold
    prior = gpr.shift(1).rolling(COOLDOWN, min_periods=1).max()
    return gpr.index[hi & (gpr > prior) & ~hi.shift(1, fill_value=False).rolling(COOLDOWN, min_periods=1).max().astype(bool)]


def reactions(prices: pd.DataFrame, events: pd.DatetimeIndex) -> pd.DataFrame:
    lr = np.log(prices).diff()
    rows = []
    for h in HORIZONS:
        fwd = lr.rolling(h + 1).sum().shift(-h)  # Tag 0 bis Tag h
        base = fwd.mean()
        idx = fwd.index.searchsorted(events)  # Ereignis am Wochenende -> naechster Handelstag
        idx = idx[idx < len(fwd)]
        ev = fwd.iloc[idx] - base
        for asset in prices.columns:
            x = ev[asset].dropna()
            if len(x) < 5:
                continue
            rows.append({"asset": asset, "tag": h, "n": len(x), "mittel_pct": round(100 * x.mean(), 3),
                         "t": round(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), 2),
                         "anteil_positiv": round(float((x > 0).mean()), 2)})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["is", "oos"], default="is")
    args = ap.parse_args()
    LOCK.register_split(*SPLIT)  # idempotent, verschieben ist gesperrt
    if args.stage == "is":  # eine Variante, der OOS-Blick zaehlt nicht neu
        LOCK.log_trials(1, f"GPR-Spitzen > {PCT:.0%} IS-Perzentil, Abklingzeit {COOLDOWN} Tage, Tag 0/+1/+5")
    d = g.history()
    gpr = d["gpr"].dropna()
    threshold = float(gpr.loc[SPLIT[0]:SPLIT[1]].quantile(PCT))
    prices = d[[a for a in g.ASSETS if a in d]].dropna(how="all")
    prices = prices[prices.index.dayofweek < 5]
    frame = LOCK.is_only(prices) if args.stage == "is" else LOCK.oos_only(prices)
    ev = spikes(gpr.loc[frame.index.min():frame.index.max()], threshold)
    res = reactions(frame.ffill(limit=3), ev)
    out = {"stufe": args.stage, "schwelle_gpr": round(threshold, 1), "ereignisse": len(ev),
           "daten": [str(x.date()) for x in ev], "ergebnis": res.to_dict("records")}
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev[args.stage] = out
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(f"Stufe {args.stage}: Schwelle {threshold:.0f}, {len(ev)} Ereignisse")
    print(res.pivot_table(index="asset", columns="tag", values=["mittel_pct", "t"]).round(2).to_string())


if __name__ == "__main__":
    main()
