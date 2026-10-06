"""ORB: Untersuchung "N-ter Ausbruch" -- altes Regime gegen neues Regime (IS).

Nutzerauftrag 2026-10-06: "Evtl. macht es jetzt Sinn, nicht mehr den ersten
Breakout zu traden, sondern den zweiten oder dritten in die jeweilige Richtung.
Untersuche das bitte ausfuehrlich." Dazu die Paper-Ideen: Fade des ersten
Ausbruchs (Ladia 2026, 1:1-Payoff, Edge in den fruehen Minuten), Retest,
Bruch nach Fehlausbruch der Gegenseite.

Beschreibend, KEINE Auswahl. Feste Exit-Config, damit die Einstiegsarten
vergleichbar sind: Stop 1,0 x M15-ATR, Ausstieg 16:00 (Variante B: Ziel 1R).
Beide Richtungen, kein Filter, Range 15 Min.

Zeitraeume (Overfitting-Sperre, Lock ny_open_orb_regime2026_20261006):
  altes Regime  2016-07-28 .. 2025-09-30   (vor dem IS = Geschichte)
  neues Regime  2025-10-01 .. 2026-03-31   (= IS)
  OOS/Tresor bleiben versiegelt: Daten werden nur bis 31.03.2026 geladen.
Ausgabe: ny_open_orb/results/nth_breakout_study{,_yearly}.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_orb_cancel_at_sl_and_hold import (  # noqa: E402
    ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS, SPREAD_BPS, find_live_entries,
)
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import load  # noqa: E402

STRATEGY = "ny_open_orb_regime2026_20261006"
IS_START, IS_END, OOS_END, TRESOR_END = "2025-10-01", "2026-03-31", "2026-06-30", "2026-09-30"
RES = Path(__file__).resolve().parents[1] / "ny_open_orb" / "results"
MODES = [("first", 1), ("nth_same", 2), ("nth_same", 3), ("after_fail", 1), ("fade", 1), ("retest", 1)]
EXITS = {"Exit 16:00": None, "Ziel 1R": 1.0}
STOP = 1.0


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    lk.register_forward("2026-10-05", "2027-03-31", 100)
    return lk


def metrics(r: pd.Series, c: pd.Series, sessions: int) -> dict:
    if len(r) < 2:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    t_min = r.index.hour * 60 + r.index.minute
    return {"n": len(r), "per_day": len(r) / sessions, "win": (r > 0).mean(), "avg": r.mean(),
            "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)),
            "sum": r.sum(), "cost_r": c.mean(), "median_entry": f"{int(np.median(t_min)) // 60:02d}:{int(np.median(t_min)) % 60:02d}",
            "share_before_1030": float((t_min < 10 * 60 + 30).mean())}


def main() -> int:
    lk = lock()
    rows, yearly = [], []
    for inst in ("SP500", "NASDAQ"):
        frames, sessions, bias = load(inst, IS_END)          # Sperre: nichts nach dem IS laden
        frame = frames[1]
        allowed = {s: [1, -1] for s in sessions}
        # Paritaet: Modus first == find_live_entries(rule="none")
        a = find_entries_nth(frame, allowed, "first")
        b = find_live_entries(frame, allowed, STOP, "none")
        same = len(a) == len(b) and (a.entry_time.values == b.entry_time.values).all() and \
            (a.direction.values == b.direction.values).all()
        print(f"{inst}: Paritaet first vs find_live_entries: {len(a)} vs {len(b)} -> {'OK' if same else 'ABWEICHUNG'}", flush=True)
        if not same:
            return 1
        sess = pd.DatetimeIndex(sessions)
        n_old = int(((sess >= "2016-07-28") & (sess < IS_START)).sum())
        n_new = int(((sess >= IS_START) & (sess <= IS_END)).sum())
        cost_bps = (SPREAD_BPS[inst] + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) / 10_000
        for mode, n in MODES:
            ent = find_entries_nth(frame, allowed, mode, n=n)
            prep = prepare(frame, ent)
            by_t = {p["t"]: p for p in prep}
            for ex_name, target in EXITS.items():
                res = sim(prep, inst, STOP, target, None)
                if res.empty:
                    continue
                idx = pd.DatetimeIndex(res["entry_time"]).tz_localize(None)
                r = pd.Series(res["r"].to_numpy(), index=idx).sort_index()
                c = pd.Series([by_t[t]["level"] * cost_bps / (STOP * by_t[t]["atr"]) for t in res["entry_time"]],
                              index=idx).sort_index()
                label = mode if mode != "nth_same" else f"nth_same_{n}"
                for per, sl, ns in (("alt 2016-09/2025", r.index < IS_START, n_old),
                                    ("neu IS 10/2025-03/2026", (r.index >= IS_START) & (r.index <= pd.Timestamp(IS_END) + pd.Timedelta(days=1)), n_new)):
                    rows.append({"inst": inst, "modus": label, "exit": ex_name, "periode": per,
                                 **metrics(r[sl], c[sl], ns)})
                if ex_name == "Exit 16:00":
                    y = r[r.index < IS_START].groupby(r[r.index < IS_START].index.year).mean()
                    for yr, v in y.items():
                        yearly.append({"inst": inst, "modus": label, "jahr": yr, "avg": v})
                    yearly.append({"inst": inst, "modus": label, "jahr": "IS neu", "avg": r[r.index >= IS_START].mean()})
            print(f"  {inst} {mode} {n}: fertig", flush=True)
    rep = pd.DataFrame(rows)
    rep.to_csv(RES / "nth_breakout_study.csv", index=False)
    yr = pd.DataFrame(yearly)
    yr.to_csv(RES / "nth_breakout_study_yearly.csv", index=False)
    pd.set_option("display.width", 250)
    for inst in ("SP500", "NASDAQ"):
        g = rep[rep.inst == inst]
        print(f"\n===== {inst} =====")
        print(g[["modus", "exit", "periode", "n", "per_day", "win", "avg", "pf", "t", "cost_r", "median_entry",
                 "share_before_1030"]].round(3).to_string(index=False))
        print(yr[yr.inst == inst].pivot(index="modus", columns="jahr", values="avg").round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
