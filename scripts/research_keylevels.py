"""Key-Level-Edge-Card, Stufe 1 (beschreibend, nur IS).

Edge Card: knowledge/projects/keylevel-edge-card-final.md
Lock:      knowledge/_research_lock/keylevels_v1.json (IS 2016-01-01..2023-03-31)

    python scripts/research_keylevels.py events EURUSD     # Ereignisse eines Paars (IS)
    python scripts/research_keylevels.py report            # Stufe-1-Auswertung aller Paare

Kein Zugriff auf OOS/Tresor in diesem Skript.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from keylevels import events as E  # noqa: E402
from keylevels.filters import flag_events  # noqa: E402
from keylevels.levels import all_instance_levels, engulf_variants  # noqa: E402
from research_lock import Lock  # noqa: E402
from smh_microstructure.data import load  # noqa: E402

LOCK = Lock("keylevels_v1")
OUT = ROOT / "keylevels" / "results"
KNOWN = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
FRESH = ["USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP"]
PAIRS = KNOWN + FRESH

# Welche zeitbegrenzten Level auf welchen Timeframes gemessen werden (Regel 13)
ENGULF_TF = {"D1": ("H1", "H4"), "H4": ("M15", "H1")}


def _types_for(levels: pd.DataFrame, tf: str) -> pd.DataFrame:
    t = levels["type"]
    keep = t.str.startswith(("week", "session", "pivot"))
    for src, tfs in ENGULF_TF.items():
        if tf in tfs:
            keep |= t.isin([f"engulf_{src}", f"plainopen_{src}", f"engulfmid_{src}", f"engulfclose_{src}"])
    return levels[keep]


def run_events(sym: str) -> pd.DataFrame:
    m1 = LOCK.is_only(load(sym))
    s = E.Series(m1)
    lv = all_instance_levels(m1)
    eng = lv[lv["type"].str.startswith("engulf_")]
    lv = pd.concat([lv, engulf_variants(eng)], ignore_index=True)
    lv["placebo"] = 0
    rows = []
    for tf, g, win in E.COMBOS:
        rows += E.grid_events(s, tf, g, win, sym, 0, "round", 0)
        rows += E.grid_events(s, tf, g, win, sym, 50, "half", 0)
        for off in E.PLACEBO_GRID:
            rows += E.grid_events(s, tf, g, win, sym, off, "grid_placebo", 1)
        sub = _types_for(lv, tf)
        # Schein-Level nur fuer die Haupt-Level-Typen (Kontrollvarianten haben ihre eigene Rolle)
        main = sub[sub["type"].str.startswith(("engulf_", "week", "session", "pivot_"))]
        sub = pd.concat([sub, E.placebo_shift(main.drop(columns="placebo"), g, sym)], ignore_index=True)
        rows += E.instance_events(s, sub, tf, g, win, sym)
        print(f"  {sym} {tf} G={g}: {len(rows):,} Ereignisse bisher", flush=True)
    ev = pd.DataFrame(rows)
    ev["t"] = pd.to_datetime(ev["t"], utc=True, unit="ns")
    ev["t_exit"] = pd.to_datetime(ev["t_exit"], utc=True, unit="ns")
    ev = flag_events(ev, sym, m1)
    ev["cost_g"] = [E.cost_in_g(sym, g) for g in ev["G"]]
    OUT.mkdir(parents=True, exist_ok=True)
    ev.to_parquet(OUT / f"events_is_{sym}.parquet")
    return ev


# --- Auswertung -------------------------------------------------------------

def _cell_stats(d: pd.DataFrame) -> dict:
    hit, fail = (d["res"] == "hit").sum(), (d["res"] == "fail").sum()
    n = len(d)
    net = d["pnl_g"] - d["cost_g"]
    # Gegenrichtung (nur touch: Durchlauf statt Umkehr); unklare Kerzen auch dort Verlust
    inv = np.where(d["ambig"].fillna(False).to_numpy(bool), -1.0, -d["pnl_g"].to_numpy()) - d["cost_g"].to_numpy()
    return {"inv_net": float(inv.mean()) if n else np.nan,
            "inv_t": float(inv.mean() / inv.std(ddof=1) * math.sqrt(n)) if n > 2 and inv.std(ddof=1) > 0 else np.nan,
            "ambig_share": float(d["ambig"].fillna(False).mean()) if n else np.nan,
            "n": n, "hits": int(hit), "fails": int(fail), "open": int(n - hit - fail),
            "hitrate": hit / (hit + fail) if hit + fail else np.nan,
            "gross": float(d["pnl_g"].mean()) if n else np.nan,
            "net": float(net.mean()) if n else np.nan,
            "net_t": float(net.mean() / net.std(ddof=1) * math.sqrt(n)) if n > 2 and net.std(ddof=1) > 0 else np.nan}


def _z(h1, n1, h2, n2) -> float:
    if n1 == 0 or n2 == 0:
        return np.nan
    p = (h1 + h2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (h1 / n1 - h2 / n2) / se if se > 0 else np.nan


def placebo_type(t: str) -> str:
    return "grid_placebo" if t in ("round", "half") else t


def report() -> pd.DataFrame:
    ev = pd.concat([pd.read_parquet(p) for p in sorted(OUT.glob("events_is_*.parquet"))], ignore_index=True)
    ev = ev[~ev["rollover"]]                       # Regel 21: hart ausgeschlossen
    clean = ev[~ev["excluded"]]                    # Regel 22/23: Hauptauswertung ohne News/Hochvola
    rows = []
    keys = ["type", "tf", "G", "kind"]
    real = clean[clean["placebo"] == 0]
    for key, d in real.groupby(keys):
        t, tf, g, kind = key
        if t == "grid_placebo":
            continue
        pl = clean[(clean["type"] == placebo_type(t)) & (clean["placebo"] > 0) &
                   (clean["tf"] == tf) & (clean["G"] == g) & (clean["kind"] == kind)]
        a, b = _cell_stats(d), _cell_stats(pl)
        z = _z(a["hits"], a["hits"] + a["fails"], b["hits"], b["hits"] + b["fails"])
        ex = ev[(ev["placebo"] == 0) & (ev["type"] == t) & (ev["tf"] == tf) & (ev["G"] == g) &
                (ev["kind"] == kind) & ev["excluded"]]
        c = _cell_stats(ex)
        rows.append({"type": t, "tf": tf, "G": g, "kind": kind, "n": a["n"], "hitrate": a["hitrate"],
                     "placebo_hitrate": b["hitrate"], "placebo_n": b["n"], "diff_pp": (a["hitrate"] - b["hitrate"]) * 100,
                     "z": z, "net_g": a["net"], "net_t": a["net_t"], "inv_net_g": a["inv_net"], "inv_t": a["inv_t"],
                     "ambig_share": a["ambig_share"], "open_share": a["open"] / max(a["n"], 1),
                     "excl_n": c["n"], "excl_hitrate": c["hitrate"]})
    rep = pd.DataFrame(rows)
    # Nachbargroesse: anderes G im selben Timeframe, gleicher Typ/Ereignistyp
    sign = np.sign(rep["diff_pp"])
    nb = {}
    for key, d in rep.groupby(["type", "tf", "kind"]):
        if len(d) == 2:
            same = np.sign(d["diff_pp"]).nunique() == 1
            for i in d.index:
                nb[i] = same
    rep["neighbour_same_sign"] = rep.index.map(nb).astype("boolean")
    # Weitergabe (Feld 05): n>=100, |z|>3 in Signalrichtung, Nachbar gleiches Vorzeichen, netto positiv.
    # touch: beide Richtungen zulaessig (Umkehr oder Durchlauf); Durchlauf-Netto = -gross - Kosten.
    rep["direction"] = np.where((rep["kind"] == "touch") & (rep["z"] < 0), "Durchlauf", "Signal")
    rep["net_trade_g"] = np.where(rep["direction"] == "Durchlauf", rep["inv_net_g"], rep["net_g"])
    rep["pass"] = ((rep["n"] >= 100) & (rep["z"].abs() > 3) &
                   ((rep["kind"] == "touch") | (rep["z"] > 0)) &
                   rep["neighbour_same_sign"].fillna(False) & (rep["net_trade_g"] > 0))
    rep = rep.sort_values(["type", "tf", "G", "kind"]).reset_index(drop=True)
    rep.to_csv(OUT / "stage1_is_report.csv", index=False)
    return rep


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "events":
        for sym in sys.argv[2:]:
            run_events(sym)
    elif cmd == "report":
        pd.set_option("display.width", 220)
        print(report().to_string())
