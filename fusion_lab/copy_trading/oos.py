"""Gewinner aus dem IS-Raster einfrieren und das OOS genau einmal oeffnen (Nutzerentscheid
26.10.2026: A2 = BOS-Einstieg, SL 1x ATR, Dennis' TP-Label, Gueltigkeit bis naechstes Update).

    python -m fusion_lab.copy_trading.oos --dry   # nur IS-Kennzahlen + DSR, Lock unberuehrt
    python -m fusion_lab.copy_trading.oos         # einfrieren + OOS oeffnen (einmalig!)
"""

import copy
import json
import sys

import numpy as np
import pandas as pd

from fusion_lab.copy_trading import grid, sim
from fusion_lab.copy_trading.extract import CALLS
from research_lock import deflated_sharpe

FROZEN = {"etype": "A2", "validity": "update", "sl": "atr1", "tp": "struct", "be": None, "trail": None}


def calls_between(lo: str, hi: str) -> list:
    a, b = pd.Timestamp(lo, tz="UTC"), pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
    calls, _ = sim.load_calls(CALLS)
    cs = [copy.copy(c) for c in calls if a <= c.t_post < b]
    sim.assign_validity(cs, b)
    return cs


def run(cs: list) -> pd.DataFrame:
    markets: dict = {}
    ents = grid.entries(cs, FROZEN["etype"], markets)
    cfg = {k: v for k, v in FROZEN.items() if k != "etype"}
    return grid.evaluate(ents, cfg, markets)


def report(name: str, tr: pd.DataFrame) -> dict:
    st = grid.stats(tr)
    r = tr["r"]
    out = {**st, "sharpe_je_trade": float(r.mean() / r.std(ddof=1)) if len(r) > 1 else np.nan,
           "long": grid.stats(tr[tr["dir"] > 0]), "short": grid.stats(tr[tr["dir"] < 0]),
           "offen": int((tr["exit"] == "offen").sum()),
           "sum_r_ohne_offen": float(tr.loc[tr["exit"] != "offen", "r"].sum()),
           "top5_anteil": float(r.nlargest(5).sum()), "median_r": float(r.median())}
    print(f"\n== {name} ==")
    print(json.dumps(out, indent=1, default=lambda v: round(float(v), 3)))
    return out


def main(argv=None) -> int:
    dry = "--dry" in (argv if argv is not None else sys.argv[1:])
    lock = grid.LOCK
    s = lock.split
    tr_is = run(calls_between(s["is_start"], s["is_end"]))
    rep_is = report("IS (zur Kontrolle, entspricht dem Raster)", tr_is)
    log = pd.read_csv(grid.RES / "stufe3_is_suche.csv")
    sr_trials = (log["t"] / np.sqrt(log["n"])).replace([np.inf, -np.inf], np.nan).dropna()
    r = tr_is["r"]
    dsr = deflated_sharpe(rep_is["sharpe_je_trade"], len(r), lock.trials, float(r.skew()),
                          float(r.kurt() + 3), float(sr_trials.var()))
    print(f"\nDeflated Sharpe (IS, {lock.trials} Versuche): {dsr:.3f}")
    if dry:
        print("\n--dry: nichts eingefroren, OOS bleibt versiegelt.")
        return 0
    h = lock.freeze(FROZEN)
    lo, hi = lock.unseal("oos", h)
    tr_oos = run(calls_between(lo, hi))
    rep_oos = report(f"OOS {lo} bis {hi} (einmalig geoeffnet)", tr_oos)
    tr_oos.to_csv(grid.RES / "oos_A2_trades.csv", index=False)
    (grid.RES / "oos_A2.json").write_text(json.dumps({"frozen": FROZEN, "hash": h, "dsr_is": dsr,
                                                      "is": rep_is, "oos": rep_oos}, indent=2,
                                                     default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
