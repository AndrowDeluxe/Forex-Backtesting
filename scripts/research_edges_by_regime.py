"""Live-Beine je Wachstums-Inflations-Regime (Regimekarte, First Prints).

    python scripts/research_edges_by_regime.py

Diagnose, keine Optimierung: es wird nichts gewaehlt, 0 optimierte Punkte.
Nach dem Vier-Fragen-Check (Fragen 2-3 nur auf IS) laeuft die Auswertung nur
auf dem IS-Fenster je Bein (gleiche Grenzen wie der Residual-Edge-Check
28.10.). Regime = Label am Entry-Tag (Print gilt ab der Folgesitzung).

Zufallstest je Bein und Linse: Regime-Reihe zirkulaer gegen die Trades
verschoben (Blockstruktur bleibt), 2000 Laeufe; p = Anteil Laeufe mit
mindestens so grosser Streuung der Regime-Mittel (gewichtete F-Statistik).
Ausgabe: knowledge/_data/edges_by_regime.json + Konsole.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "portfolio_construction" / "results"
OUT = ROOT / "knowledge" / "_data" / "edges_by_regime.json"
N_SHIFT = 2000
MIN_N = 15  # Zellen darunter werden gezeigt, aber nicht gedeutet

# Bein: (Quelle, IS-Ende exklusiv) -- Grenzen aus residual_edge/build_inputs.py
LEGS = {
    "orb_sp500": ("ttp", "2023-01-01"),
    "orb_nasdaq": ("ttp", "2023-01-01"),
    "orb_us30": ("ttp", "2023-01-01"),
    "gold_asb": ("ttp", "2023-01-01"),
    "gold_silver": ("ampel", "2023-01-01"),
    "ou_modell": ("ttp", "2023-01-01"),
    "cls_practical": ("ttp", "2022-06-01"),
    "trend_pullback": ("ttp", "2024-07-01"),
    "ctnl_reversal": ("ttp", "2026-10-01"),  # kein sauberes OOS, ganz IS
}
LENSES = ("change", "joint", "signs")


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    ttp = pd.read_csv(RES / "live_trades_ttp_2019_2026.csv").assign(quelle="ttp")
    amp = pd.read_csv(RES / "live_trades_tickmill_ampel.csv").assign(quelle="ampel")
    t = pd.concat([ttp, amp], ignore_index=True)
    t["day"] = pd.to_datetime(t["entry_time"]).dt.normalize()
    lab = pd.read_parquet(ROOT / "fusion_lab/data/macro_regime/labels.parquet")
    lab.index = pd.to_datetime(lab.index).normalize()
    return t, lab


def f_stat(r: np.ndarray, g: np.ndarray) -> float:
    """Gewichtete Streuung der Gruppenmittel (Zaehler der ANOVA-F)."""
    mu = r.mean()
    return sum((g == k).sum() * (r[g == k].mean() - mu) ** 2 for k in np.unique(g))


def cell_table(r: pd.Series, g: pd.Series) -> list[dict]:
    rows = []
    for k, x in r.groupby(g):
        sd = x.std(ddof=1) if len(x) > 1 else np.nan
        rows.append({"regime": k, "n": int(len(x)), "mean_r": round(x.mean(), 3),
                     "t": round(x.mean() / sd * np.sqrt(len(x)), 2) if sd and sd > 0 else None,
                     "sum_r": round(x.sum(), 1), "win": round((x > 0).mean(), 3)})
    return sorted(rows, key=lambda d: -d["n"])


def shift_test(days: pd.DatetimeIndex, r: np.ndarray, labels: pd.Series, rng) -> float:
    lab = labels.to_numpy()
    pos = labels.index.searchsorted(days)
    pos = np.clip(pos, 0, len(lab) - 1)
    obs = f_stat(r, lab[pos])
    hits = 0
    for _ in range(N_SHIFT):
        s = rng.integers(60, len(lab) - 60)  # mind. ~3 Monate Versatz
        hits += f_stat(r, np.roll(lab, s)[pos]) >= obs
    return (hits + 1) / (N_SHIFT + 1)


def main() -> None:
    trades, lab = load()
    lab = lab.loc["2017":]  # Verschiebe-Pool: reale Regimefolge um das Fenster herum
    rng = np.random.default_rng(20261028)
    out = {"stand": "2026-10-28", "scope": "IS je Bein", "n_shift": N_SHIFT, "legs": {}}
    port = []
    for leg, (quelle, is_end) in LEGS.items():
        t = trades[(trades.leg == leg) & (trades.quelle == quelle) & (trades.day < is_end)].copy()
        t = t[t.day >= lab.index[0]]
        for lens in LENSES:
            t[lens] = lab[lens].reindex(t.day, method="ffill").to_numpy()
        t = t.dropna(subset=list(LENSES))
        res = {"is_end": is_end, "n": int(len(t)), "mean_r": round(t.r.mean(), 3),
               "sum_r": round(t.r.sum(), 1), "lenses": {}}
        for lens in LENSES:
            p = shift_test(pd.DatetimeIndex(t.day), t.r.to_numpy(), lab[lens], rng)
            res["lenses"][lens] = {"p_shift": round(p, 3), "cells": cell_table(t.r, t[lens])}
        out["legs"][leg] = res
        port.append(t.assign(leg=leg)[["day", "leg", "r", *LENSES]])

    # Gemeinsamer Zeitraum aller Beine (2019 bis Ende 2022, ohne CLS-Ende): Gleichlauf je Regime
    p = pd.concat(port)
    p = p[p.day < "2022-06-01"]
    out["gleichlauf_2019_2022H1"] = {
        lens: p.pivot_table(index="leg", columns=lens, values="r", aggfunc="mean").round(3).to_dict()
        for lens in ("change", "joint")}

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for leg, res in out["legs"].items():
        print(f"\n=== {leg}  IS bis {res['is_end']}  n={res['n']}  Ø R {res['mean_r']}  ΣR {res['sum_r']}")
        for lens in ("change", "joint"):
            L = res["lenses"][lens]
            print(f"  [{lens}] p_shift={L['p_shift']}")
            for c in L["cells"]:
                flag = "" if c["n"] >= MIN_N else "  (dünn)"
                print(f"    {c['regime']:<22} n={c['n']:>4}  ØR {c['mean_r']:>7}  t {c['t']}  ΣR {c['sum_r']:>7}  WR {c['win']}{flag}")


if __name__ == "__main__":
    main()
