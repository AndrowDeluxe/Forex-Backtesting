"""CLS Practical: ruhende Stop-Order am Trigger-Level statt Market nach dem Scan.

Nutzerfrage 2026-10-04: "Was wuerde uns der CLS-Umbau in Zahlen nuetzen und
wuerde sich damit die Nachhaltigkeit des Edges verbessern?"

Hintergrund: cls_practical/engine.py modelliert den Einstieg bereits als
ruhende Stop-Order ("Retest + entry: resting stop order breaking that
fractal") -- das Trigger-Level steht mit der Fraktal-Bestaetigung VOR dem
Ausbruch fest. Live (alle Bridges) wird dagegen erst nach dem Scan zum
Marktkurs eingestiegen, gemessen ~1 M5-Bar nach der Trigger-Bar (8 Min. nach
Label), mit Restlaufzeit-Gate und 0,50R-Detektor; TP liegt nicht beim Broker.

Varianten (Signale identisch: 5-Pip-Boden, Engine ohne Kosten):
  market_lag1   heute live: Close der Folgebar + halbe Kosten, absoluter SL,
                Gates, TP/Zeit-Exit einen Scan spaeter (= research_fk_gesamtportfolio_2026.cls_trades)
  stop_order    Fill am Trigger-Level (+ Stop-Slippage), SL/TP am Broker
                -> R direkt aus der Engine, nur Kosten abgezogen
Kosten je Broker (Round-Trip, gemessen): TTP 2,05 / IQ 1,30 / Tickmill 0,80 Pips
(Tickmill = Annahme). Stop-Slippage-Staffel 0 / 0,2 / 0,5 Pips.
Nachhaltigkeit: Ø R je Jahr, IS 2019-2022 vs. OOS 2023-2026, Bootstrap-
P(Ø R < 0) je Haelfte, Halbjahres-Trend.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

START, END = "2018-01-01", "2026-10-02"
H0, SPLIT = pd.Timestamp("2019-01-01"), pd.Timestamp("2023-01-01")
PIP = 0.0001
COSTS = {"TTP": 2.05, "IQ": 1.30, "Tickmill": 0.80}
OUT = REPO / "knowledge" / "_data" / "cls_stoporder.json"
rng = np.random.default_rng(20261004)


def load():
    from cls_practical.data import (fetch_2y_yield_daily, fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin,
                                    fetch_rate_instrument_m5_berlin)
    from cls_practical.engine import simulate_cls_practical
    from cls_practical.rates import compute_combined_rate_risk_multiplier
    from strategy.cls_advanced import PAIRS, compute_daily_features

    e = fetch_eurusd_entry_tf_berlin("M5", START, END)
    o = {p: fetch_major_m15_berlin(p, START, END) for p in PAIRS if p != "EURUSD"}
    b = fetch_rate_instrument_m5_berlin("BUND", START, END)
    u = fetch_rate_instrument_m5_berlin("USTBOND", START, END)
    daily = compute_daily_features(e)
    mult = compute_combined_rate_risk_multiplier(b, u, fetch_2y_yield_daily("DE02Y"), fetch_2y_yield_daily("US02Y"),
                                                 daily["direction"])
    tr = simulate_cls_practical(e, o, b, u, risk_multiplier=mult, min_sl_pips=5, spread_bps=0.0, slippage_bps=0.0)
    return e, tr


def market_lag1(tr, e, cost_pips, lag=1):
    half = cost_pips * PIP / 2
    idx = e.index
    pos = {t: i for i, t in enumerate(idx)}
    cl, hi, lo = e["close"].to_numpy(), e["high"].to_numpy(), e["low"].to_numpy()
    rows = []
    for _, t in tr.iterrows():
        i = pos.get(t["entry_time"])
        if i is None or i + lag >= len(cl):
            continue
        d = 1 if t["direction"] == "long" else -1
        sl, sd = float(t["sl"]), float(t["sl_distance"])
        seg = slice(i, i + lag + 1)
        if (lo[seg] <= sl).any() if d == 1 else (hi[seg] >= sl).any():
            continue
        P = cl[i + lag] + d * half
        eff = d * (P - sl)
        if eff <= 0 or (sd - eff) / sd > 0.5:
            continue
        X = float(t["exit_price"])
        if t["exit_reason"] not in ("stop", "breakeven"):
            j = pos.get(t["exit_time"])
            if j is not None and j + lag < len(cl):
                X = cl[j + lag]
        X -= d * half
        rows.append({"entry_time": t["entry_time"], "r": d * (X - P) / eff})
    return pd.DataFrame(rows)


def stop_order(tr, cost_pips, slip_pips=0.0):
    d = np.where(tr["direction"] == "long", 1, -1)
    P = tr["entry_price"].to_numpy(float) + d * (cost_pips / 2 + slip_pips) * PIP
    X = tr["exit_price"].to_numpy(float) - d * cost_pips / 2 * PIP
    sl = tr["sl"].to_numpy(float)
    eff = d * (P - sl)
    r = d * (X - P) / eff
    return pd.DataFrame({"entry_time": tr["entry_time"].to_numpy(), "r": r})[eff > 0]


def stats(df) -> dict:
    t = pd.to_datetime(df["entry_time"])
    t = t.dt.tz_convert(None) if t.dt.tz is not None else t
    df = df.assign(t=t)
    df = df[df["t"] >= H0]
    r = df["r"]
    w, lo = r[r > 0].sum(), -r[r < 0].sum()
    eq = r.cumsum()
    is_, oos = df[df["t"] < SPLIT]["r"].to_numpy(), df[df["t"] >= SPLIT]["r"].to_numpy()

    def p_neg(x):
        return float((rng.choice(x, size=(4000, len(x))).mean(axis=1) < 0).mean()) if len(x) else None
    years = df.groupby(df["t"].dt.year)["r"].mean()
    return {"n": int(len(r)), "avg_r": round(float(r.mean()), 3), "pf": round(float(w / lo), 2),
            "sum_r": round(float(r.sum()), 1), "maxdd_r": round(float((eq - eq.cummax()).min()), 1),
            "is": round(float(is_.mean()), 3), "oos": round(float(oos.mean()), 3),
            "p_neg_is": p_neg(is_), "p_neg_oos": p_neg(oos),
            "jahre_positiv": f"{int((years > 0).sum())}/{len(years)}",
            "je_jahr": years.round(3).to_dict()}


def main() -> None:
    e, tr = load()
    print(f"Signale (5-Pip-Boden): {len(tr)}")
    res = {}
    for broker, c in COSTS.items():
        res[broker] = {"market_lag1": stats(market_lag1(tr, e, c))}
        for slip in (0.0, 0.2, 0.5):
            res[broker][f"stop_order_slip{slip}"] = stats(stop_order(tr, c, slip))
        print(f"\n=== {broker} (RT {c} Pips)")
        for k, v in res[broker].items():
            print(f"  {k:22} n={v['n']} ØR={v['avg_r']:+.3f} PF={v['pf']} ΣR={v['sum_r']:+.1f} DD={v['maxdd_r']} "
                  f"IS={v['is']:+.3f} (P<0 {v['p_neg_is']:.1%}) OOS={v['oos']:+.3f} (P<0 {v['p_neg_oos']:.1%}) "
                  f"Jahre+ {v['jahre_positiv']}")
            print(f"      je Jahr {v['je_jahr']}")
    OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    print(f"\nGeschrieben: {OUT}")


if __name__ == "__main__":
    main()
