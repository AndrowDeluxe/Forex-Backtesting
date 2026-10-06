"""Gamma als Regler fuer den ORB ab 2025 -- wie haette er performt?

Nutzerauftrag 2026-10-07: "Danach schauen wir uns die Gamma-Werte als Regler
im neuen ORB-IS-Zeitraum ab 2025 an und wie es aktuell performt."

BESCHREIBEND, keine Auswahl: 2025-2026 ist bereits gesehen (Tresor-/Regime-
Studien). Die Regler sind vorab aus dem Befund 2016-2026 + dem blinden Test
2012-2016 festgelegt (research_gamma_rules_blind.py), nicht auf 2025-26 gefittet.

ORB-Versionen: "live" (Stand 04.10.2026, run_config) und "basis" (1. Ausbruch,
beide Richtungen, Stop 1,0 ATR, Exit 16:00).
Regler (Gamma = SPX-GEX Vortag, Perzentil 252 Tage, Quintile):
  ohne | kein Q5 | Q1+Q5 halbes Risiko | nur Q2-Q4
Konto: 100k ab 01.01.2025, 1 % vom Kontostand je Trade x Regler-Gewicht.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_gamma_rules_blind import gex_quintile  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import LIVE, load, run_config  # noqa: E402

RES = ROOT / "ny_open_orb" / "results"
START, END = "2025-01-01", "2026-09-30"
REGLER = {
    "ohne": {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 1},
    "kein Q5": {"Q1": 1, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 0},
    "Q1+Q5 halbes Risiko": {"Q1": .5, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": .5},
    "nur Q2-Q4": {"Q1": 0, "Q2": 1, "Q3": 1, "Q4": 1, "Q5": 0},
}


def account(df: pd.DataFrame, start=100_000.0, risk=0.01):
    eq, path = start, [start]
    for _, g in df.groupby(df.index.normalize()):
        eq += float((g["r"] * g["w"]).sum()) * risk * eq
        path.append(eq)
    p = np.array(path)
    return eq, (p / np.maximum.accumulate(p) - 1).min()


def main() -> int:
    q = gex_quintile()
    rows, quarters = [], []
    for inst in ("SP500", "NASDAQ"):
        frames, sessions, bias = load(inst, END)
        series = {"live": run_config(frames, sessions, bias, inst, LIVE[inst])[0]}
        f = frames[1]
        prep = prepare(f, find_entries_nth(f, {s: [1, -1] for s in sessions}, "first"))
        res = sim(prep, inst, 1.0, None, None)
        series["basis"] = pd.Series(res["r"].to_numpy(), index=pd.DatetimeIndex(res["entry_time"]))
        for ver, r in series.items():
            r = r.copy()
            r.index = pd.DatetimeIndex(r.index).tz_localize(None)
            r = r[(r.index >= START) & (r.index < pd.Timestamp(END) + pd.Timedelta(days=1))]
            df = pd.DataFrame({"r": r.values, "q": q.reindex(r.index.normalize()).astype(str).values}, index=r.index)
            for name, wmap in REGLER.items():
                df["w"] = df["q"].map(wmap).fillna(1.0)
                eff = df["r"] * df["w"]
                traded = df[df["w"] > 0]
                loss = -eff[eff < 0].sum()
                end_eq, dd = account(df)
                rows.append({"inst": inst, "version": ver, "regler": name, "trades": len(traded),
                             "sum_r": eff.sum(), "pf": eff[eff > 0].sum() / loss if loss > 0 else np.inf,
                             "konto_end": end_eq, "maxdd_pct": dd * 100})
                qs = eff.groupby(df.index.to_period("Q")).sum()
                for per, v in qs.items():
                    quarters.append({"inst": inst, "version": ver, "regler": name, "quartal": str(per), "sum_r": v})
        print(f"{inst} fertig", flush=True)
    rep = pd.DataFrame(rows)
    qt = pd.DataFrame(quarters)
    rep.to_csv(RES / "orb_gamma_regler_2025.csv", index=False)
    qt.to_csv(RES / "orb_gamma_regler_2025_quartale.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(2).to_string(index=False))
    for inst in ("SP500", "NASDAQ"):
        for ver in ("live", "basis"):
            print(f"\n{inst} {ver} – Σ R je Quartal")
            print(qt[(qt.inst == inst) & (qt.version == ver)].pivot(index="regler", columns="quartal", values="sum_r").round(1).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
