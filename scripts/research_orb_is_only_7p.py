"""ORB IS-only, Runde 2: max. 7 optimierte Punkte je Index, nur SP500 + NASDAQ.

Nutzerentscheid 2026-10-06 nach der ersten IS-Runde
(research_orb_is_only_reopt.py, 8 Dimensionen inkl. Wochentag, 22.680
Varianten je Index):
  - je Index hoechstens 9 optimierte Punkte (Richtwert aus dem Kurs, siehe
    knowledge/areas/overfitting-sperre.md, Hinweis, keine harte Sperre)
  - genutzt werden 7: Range-Laenge, Richtung, Trendfilter, Order-Storno,
    Stop, Ziel, Teilziel. Der Wochentag faellt weg (frueher OOS gescheitert,
    in Runde 1 ein Warnsignal).
  - nur SP500 + NASDAQ
  - Tresor auf einem 100k-Konto mit 1 % Risiko vom aktuellen Kontostand

Die 7-Punkte-Varianten sind eine Teilmenge des Runde-1-Gitters (weekday leer),
deshalb kommt die Auswahl ohne Neurechnung aus is_only_grid.csv. Das ist
reine IS-Information. Die Auswahlregel ist unveraendert (siehe
research_orb_is_only_reopt.py).

Der erste evaluate-Lauf (Runde 1) wurde nach dem Unseal und vor jeder
Berechnung abgebrochen. Es gibt keine OOS-/Tresor-Zahlen aus Runde 1
(Protokoll: knowledge/_research_lock/ny_open_orb_is_reopt_20261005.jsonl).

  python scripts/research_orb_is_only_7p.py --stage select
  python scripts/research_orb_is_only_7p.py --stage oos      # laedt Daten nur bis 30.09.2025
  python scripts/research_orb_is_only_7p.py --stage tresor   # einmal, inkl. 100k-Konto
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_orb_is_only_reopt import (  # noqa: E402
    IS_END, IS_START, LIVE, OOS_END, RES, STOPS, TARGETS, TRESOR_END, load, metrics, run_config,
)

STRATEGY = "ny_open_orb_is_reopt_7p_20261006"
INSTRUMENTS = ("SP500", "NASDAQ")
N_TRIALS_ROUND1 = 22680
START_CAPITAL, RISK = 100_000.0, 0.01


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def stage_select() -> int:
    lk = lock()
    grid = pd.read_csv(RES / "is_only_grid.csv")
    grid = grid[grid.instrument.isin(INSTRUMENTS) & grid.weekday.isna()].copy()
    grid["eligible"] = (grid.n >= 100) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    grid["partial_k"] = grid.partial.fillna(-1)
    grid["target_k"] = grid.target.fillna(-1)
    keys = ["instrument", "range_bars", "dirs", "ribbon", "rule", "partial_k", "stop", "target_k"]
    t_lookup = grid.set_index(keys)["t"].to_dict()
    tk = [-1] + [t for t in TARGETS if t is not None]

    def smooth(row):
        si, ti = STOPS.index(row.stop), tk.index(row.target_k)
        vals = []
        for ds, dt in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            a, b = si + ds, ti + dt
            if 0 <= a < len(STOPS) and 0 <= b < len(tk):
                v = t_lookup.get((row.instrument, row.range_bars, row.dirs, row.ribbon, row.rule, row.partial_k,
                                  STOPS[a], tk[b]))
                if v is not None and not pd.isna(v):
                    vals.append(v)
        return float(np.median(vals)) if vals else np.nan

    st = json.loads(lk.path.read_text(encoding="utf-8"))
    winners, n_trials, sr_var = {}, {}, {}
    for inst in INSTRUMENTS:
        g = grid[grid.instrument == inst]
        n_trials[inst] = len(g)
        if st["trials"] == 0:
            lk.log_trials(len(g), note=f"{inst}: 7-Punkte-Teilgitter (aus Runde 1, ohne Wochentag)")
        sr_var[inst] = float((g[g.n >= 30]["avg"] / g[g.n >= 30]["std"]).var())
        el = g[g.eligible].copy()
        el["t_smooth"] = el.apply(smooth, axis=1)
        el = el.sort_values("t_smooth", ascending=False)
        print(f"\n{inst}: {len(el)} von {len(g)} Zellen erfuellen die Mindestbedingungen")
        print(el.head(8)[["range_bars", "dirs", "ribbon", "rule", "stop", "target", "partial", "n", "avg", "pf",
                          "t", "t_smooth"]].to_string(index=False))
        w = el.iloc[0]
        winners[inst] = {"dirs": w.dirs, "ribbon": w.ribbon, "weekday": None, "rule": w.rule, "stop": float(w.stop),
                         "target": None if w.target_k == -1 else float(w.target),
                         "partial": None if w.partial_k == -1 else float(w.partial), "range_bars": int(w.range_bars)}
    out = {"winners": winners, "n_trials": n_trials, "n_trials_round1": N_TRIALS_ROUND1, "sr_var_trials": sr_var,
           "optimized_points": ["range_bars", "dirs", "ribbon", "rule", "stop", "target", "partial"]}
    (RES / "is_only_7p_selection.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n", json.dumps(winners, indent=2))
    return 0


def account(trades: pd.DataFrame, start: float = START_CAPITAL, risk: float = RISK) -> pd.DataFrame:
    """1 % vom Kontostand zu Tagesbeginn je Trade. Alle ORB-Trades eines Tages
    laufen parallel und schliessen bis 16:00, deshalb wird je Tag mit dem
    Stand vom Vortag gesized und abends gebucht."""
    day = trades.groupby(trades.index.normalize())["r"].apply(list)
    eq, rows = start, []
    for d, rs in day.items():
        pnl = sum(r * risk * eq for r in rs)
        eq += pnl
        rows.append({"date": d, "pnl": pnl, "equity": eq, "trades": len(rs)})
    return pd.DataFrame(rows).set_index("date")


def acc_stats(a: pd.DataFrame, start: float = START_CAPITAL) -> dict:
    eq = pd.concat([pd.Series([start]), a["equity"].reset_index(drop=True)])
    dd = (eq / eq.cummax() - 1).min()
    yrs = max((a.index.max() - a.index.min()).days / 365.25, 1 / 12)
    end = a["equity"].iloc[-1]
    return {"end": end, "ret": end / start - 1, "cagr": (end / start) ** (1 / yrs) - 1, "maxdd": dd,
            "trades": int(a.trades.sum()), "best_day": a.pnl.max(), "worst_day": a.pnl.min()}


def evaluate(stage: str) -> int:
    lk = lock()
    sel = json.loads((RES / "is_only_7p_selection.json").read_text(encoding="utf-8"))
    winners = sel["winners"]
    h = lk.freeze(winners)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    if stage not in st["unsealed"]:
        print(f"{stage} geoeffnet:", lk.unseal(stage, h))
    end = OOS_END if stage == "oos" else TRESOR_END
    parts = ["IS", "OOS"] + (["Tresor"] if stage == "tresor" else [])

    rows, trades = [], []
    for inst in INSTRUMENTS:
        frames, sessions, bias = load(inst, end)
        for label, cfg in (("IS-only", winners[inst]), ("frueher", LIVE[inst])):
            r, cost = run_config(frames, sessions, bias, inst, cfg)
            r = r[r.index <= pd.Timestamp(end, tz=r.index.tz) + pd.Timedelta(days=1)]
            cost = cost.reindex(r.index)
            trades.append(pd.DataFrame({"instrument": inst, "variant": label, "time": r.index, "r": r.values,
                                        "cost_r": cost.values}))
            sl = {"IS": lk.is_only, "OOS": lambda x: lk.stage_slice(x, "oos"),
                  "Tresor": lambda x: lk.stage_slice(x, "tresor")}
            for p in parts:
                m = metrics(sl[p](r), sl[p](cost))
                rows.append({"instrument": inst, "variant": label, "part": p, **m})
            if label == "IS-only":
                m_is = metrics(lk.is_only(r))
                for nt, tag in ((sel["n_trials"][inst], "DSR"), (sel["n_trials_round1"], "DSR_runde1")):
                    dsr = deflated_sharpe(m_is["avg"] / m_is["std"], m_is["n"], nt, m_is["skew"], m_is["kurt"],
                                          sel["sr_var_trials"][inst])
                    rows.append({"instrument": inst, "variant": label, "part": tag, "n": nt, "avg": dsr})
    rep = pd.DataFrame(rows)
    tr = pd.concat(trades)
    rep.to_csv(RES / f"is_only_7p_report_{stage}.csv", index=False)
    tr.to_csv(RES / f"is_only_7p_trades_{stage}.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))

    if stage == "tresor":
        t = tr[tr.variant == "IS-only"].copy()
        t["time"] = pd.to_datetime(t["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        t = t.set_index("time").sort_index()
        acc_rows = []
        for name, sub in (("Tresor 10/2025-09/2026", t[t.index > pd.Timestamp(OOS_END) + pd.Timedelta(days=1)]),
                          ("OOS 01/2023-09/2025", t[(t.index > pd.Timestamp(IS_END) + pd.Timedelta(days=1)) &
                                                    (t.index <= pd.Timestamp(OOS_END) + pd.Timedelta(days=1))]),
                          ("Gesamt 2016-2026", t)):
            a = account(sub)
            a.to_csv(RES / f"is_only_7p_account_{name.split()[0].lower()}.csv")
            acc_rows.append({"zeitraum": name, **acc_stats(a)})
        acc = pd.DataFrame(acc_rows)
        acc.to_csv(RES / "is_only_7p_account_summary.csv", index=False)
        print("\n100k-Konto, 1 % vom Kontostand je Trade:\n", acc.round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1]
    sys.exit(stage_select() if stage == "select" else evaluate(stage))
