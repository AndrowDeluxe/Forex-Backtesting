"""ORB-Einstiegsvarianten auf dem urspruenglichen IS 2016-2022, OOS 2023-09/2026.

Nutzerauftrag 2026-10-06: "Backteste die Einstiegsvarianten und die beste
Entry-Methodik auf dem urspruenglichen IS von 2016 und werte OOS 2025-2026 aus."

SPLIT (Lock ny_open_orb_entries_is2016_20261006):
  IS   2016-07-28 .. 2022-12-31   Auswahl
  OOS  2023-01-01 .. 2026-09-30   einmal; Bericht getrennt fuer 2023-24 und
                                   2025-09/2026 (Nutzerfokus)
  NICHT blind: Die Untersuchung des N-ten Ausbruchs (06.10.) hat 2016-03/2026
  bereits beschreibend gesehen. Das ist ein Prozess-Test, kein jungfraeulicher
  Holdout.

SUCHRAUM je Index (4 Punkte): Einstiegsart (first / 2. / 3. Ausbruch /
nach Fehlausbruch / Fade / Retest) x Richtung (long/short/beide) x Stop
(0,6/0,8/1,0/1,5 ATR) x Ziel (2R/4R/8R/ohne). Fest: Range 15 Min., kein
Filter, Einstieg bis 16:00, Ausstieg spaetestens 16:00.

AUSWAHLREGEL (wie bisher): >= 100 IS-Trades, PF > 1,3, beide IS-Haelften > 0,
dann t geglaettet ueber Stop-/Ziel-Nachbarn. Zusaetzlich je Einstiegsart die
beste IS-Variante, damit sichtbar wird, welche Methodik im OOS haelt.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import load, metrics  # noqa: E402

STRATEGY = "ny_open_orb_entries_is2016_20261006"
IS_START, IS_END, OOS_END = "2016-07-28", "2022-12-31", "2026-09-30"
RES = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"
MODES = [("first", 1), ("nth_same", 2), ("nth_same", 3), ("after_fail", 1), ("fade", 1), ("retest", 1)]
DIRS = {"long": [1], "short": [-1], "beide": [1, -1]}
STOPS = [0.6, 0.8, 1.0, 1.5]
TARGETS = [2.0, 4.0, 8.0, None]


def label(mode, n):
    return mode if mode != "nth_same" else f"nth_same_{n}"


def run(frame, sessions, inst, mode, n, dirs):
    allowed = {s: DIRS[dirs] for s in sessions}
    return prepare(frame, find_entries_nth(frame, allowed, mode, n=n))


def to_series(res):
    return pd.Series(res["r"].to_numpy(), index=pd.DatetimeIndex(res["entry_time"])).sort_index()


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    rows, winners, per_mode = [], {}, {}
    for inst in ("SP500", "NASDAQ"):
        frames, sessions, _ = load(inst, IS_END)                 # Sperre: nur IS geladen
        frame = lk.is_only(frames[1])
        for (mode, n), dirs in itertools.product(MODES, DIRS):
            prep = run(frame, sessions, inst, mode, n, dirs)
            for stop, target in itertools.product(STOPS, TARGETS):
                res = sim(prep, inst, stop, target, None)
                if res.empty:
                    continue
                m = metrics(to_series(res))
                rows.append({"inst": inst, "modus": label(mode, n), "mode": mode, "n_brk": n, "dirs": dirs,
                             "stop": stop, "target": target,
                             **{k: m.get(k) for k in ("n", "avg", "std", "t", "pf", "sum", "h1", "h2", "win")}})
        print(f"{inst}: IS-Gitter fertig", flush=True)
    grid = pd.DataFrame(rows)
    n_trials = int(len(grid) / 2)
    if st["trials"] == 0:
        lk.log_trials(len(grid), note="beide Indizes, 6 Einstiegsarten x 3 Richtungen x 4 Stops x 4 Ziele")
    grid.to_csv(RES / "entries_is2016_grid.csv", index=False)

    grid["eligible"] = (grid.n >= 100) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    grid["tk"] = grid.target.fillna(-1)
    tks = [2.0, 4.0, 8.0, -1]
    look = grid.set_index(["inst", "modus", "dirs", "stop", "tk"])["t"].to_dict()

    def smooth(r):
        si, ti = STOPS.index(r.stop), tks.index(r.tk)
        v = [look.get((r.inst, r.modus, r.dirs, STOPS[a], tks[b])) for a, b in
             ((si, ti), (si - 1, ti), (si + 1, ti), (si, ti - 1), (si, ti + 1)) if 0 <= a < 4 and 0 <= b < 4]
        v = [x for x in v if x is not None and not pd.isna(x)]
        return float(np.median(v)) if v else np.nan

    grid["t_smooth"] = grid.apply(smooth, axis=1)
    for inst in ("SP500", "NASDAQ"):
        g = grid[grid.inst == inst]
        el = g[g.eligible].sort_values("t_smooth", ascending=False)
        print(f"\n{inst}: {len(el)} von {len(g)} erfuellen die Mindestbedingungen")
        print(el.head(10)[["modus", "dirs", "stop", "target", "n", "avg", "pf", "t", "t_smooth"]].round(3).to_string(index=False))
        winners[inst] = None if el.empty else el.iloc[0][["modus", "mode", "n_brk", "dirs", "stop", "target"]].to_dict()
        # je Einstiegsart die beste IS-Variante (geglaettet, ohne Mindestbedingung)
        best = g.sort_values("t_smooth", ascending=False).groupby("modus").head(1)
        per_mode[inst] = best[["modus", "mode", "n_brk", "dirs", "stop", "target"]].to_dict("records")

    cfg = {"winners": winners, "per_mode": per_mode}
    cfg = json.loads(json.dumps(cfg, default=lambda x: None if (isinstance(x, float) and np.isnan(x)) else str(x)))
    h = lk.freeze(cfg)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if "oos" not in st["unsealed"]:
        print("\nOOS geoeffnet:", lk.unseal("oos", h))

    out = []
    for inst in ("SP500", "NASDAQ"):
        frames, sessions, _ = load(inst, OOS_END)
        frame = frames[1]
        cands = [("Gewinner", winners[inst])] if winners[inst] else []
        cands += [(f"bester {c['modus']}", c) for c in per_mode[inst]]
        for tag, c in cands:
            tgt = None if c["target"] in (None, "None", "nan") or (isinstance(c["target"], float) and np.isnan(c["target"])) else float(c["target"])
            prep = run(frame, sessions, inst, c["mode"], int(c["n_brk"]), c["dirs"])
            res = sim(prep, inst, float(c["stop"]), tgt, None)
            r = to_series(res)
            r.index = r.index.tz_localize(None)
            for per, a, b in (("IS 2016-2022", IS_START, "2023-01-01"), ("OOS 2023-2024", "2023-01-01", "2025-01-01"),
                              ("OOS 2025-09/2026", "2025-01-01", "2026-10-01")):
                m = metrics(r[(r.index >= a) & (r.index < b)])
                out.append({"inst": inst, "variante": tag, "dirs": c["dirs"], "stop": c["stop"], "target": tgt,
                            "periode": per, **{k: m.get(k) for k in ("n", "avg", "pf", "t", "sum", "win")}})
    rep = pd.DataFrame(out)
    rep.to_csv(RES / "entries_is2016_report.csv", index=False)
    pd.set_option("display.width", 250)
    for inst in ("SP500", "NASDAQ"):
        print(f"\n===== {inst} =====")
        pv = rep[rep.inst == inst].pivot_table(index=["variante", "dirs", "stop", "target"], columns="periode",
                                               values=["avg", "pf", "n"], dropna=False)
        print(pv.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
