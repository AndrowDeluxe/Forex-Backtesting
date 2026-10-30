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


# --- Stufe B: Doppel-BOS-Einstieg (Plan 18.10.2026) -------------------------

BOS_TYPES = ["round", "half", "grid_placebo", "session", "week", "pivot_D"]
N_BASELINE = 3000   # Zufalls-Startzeitpunkte je Paar fuer "Doppel-BOS ohne Level"


def _touches(sym: str, s: "E.Series", m1: pd.DataFrame) -> pd.DataFrame:
    """Frische M1-Beruehrungen (Anlauf >= 20 Pips) aller Level-Typen inkl. Schein-Level,
    dazu Zufallszeitpunkte ohne Level."""
    ev = pd.read_parquet(OUT / f"events_is_{sym}.parquet",
                         columns=["type", "sub", "placebo", "tf", "G", "kind", "approach", "level", "t"])
    t = ev[(ev["tf"] == "M1") & (ev["G"] == 20) & (ev["kind"] == "touch") & ev["type"].isin(BOS_TYPES)]
    t = t[["type", "sub", "placebo", "approach", "level", "t"]]
    # Engulfing-Open (in Stufe 1 nur auf M15/H1/H4 gemessen) hier mit M1-Beruehrung
    lv = all_instance_levels(m1)
    eng = lv[lv["type"].isin(["engulf_D1", "engulf_H4"])].copy()
    eng["placebo"] = 0
    eng = pd.concat([eng, E.placebo_shift(eng.drop(columns="placebo"), 20, sym)], ignore_index=True)
    e2 = pd.DataFrame(E.instance_events(s, eng, "M1", 20, 1, sym))
    e2["t"] = pd.to_datetime(e2["t"], utc=True, unit="ns")
    t = pd.concat([t, e2[["type", "sub", "placebo", "approach", "level", "t"]]], ignore_index=True)
    rng = np.random.default_rng(11)
    pick = np.sort(rng.choice(len(s.t), N_BASELINE, replace=False))
    base = pd.DataFrame({"type": "no_level", "sub": "random", "placebo": 0, "approach": 0,
                         "level": np.nan, "t": pd.to_datetime(s.t[pick], utc=True, unit="ns")})
    return pd.concat([t, base], ignore_index=True)


def run_bos_events(sym: str) -> pd.DataFrame:
    from keylevels import bos as B
    from keylevels.volume import VolumeContext
    from smh_microstructure.costs import PIP
    m1 = LOCK.is_only(load(sym))
    s = E.Series(m1)
    pip = PIP[sym]
    touches = _touches(sym, s, m1)
    st = {"M5": B.Structure(s, "M5"), "M15": B.Structure(s, "M15")}
    vc = VolumeContext(s, pip)
    rows = []
    t_ns = pd.DatetimeIndex(touches["t"]).as_unit("ns").asi8
    for r, tt in zip(touches.itertuples(index=False), t_ns):
        hvn = vc.hvn(r.level, tt) if r.type != "no_level" else False
        for var, b1 in (("A_2xM5", "M5"), ("B_M15_M5", "M15")):
            trig = B.find_trigger(s, st["M5"], st[b1], int(tt))
            if trig is None:
                continue
            d = trig["dir"]
            rel = "Umkehr" if r.approach and d == -r.approach else ("Durchlauf" if r.approach else "ohne")
            z = vc.pressure_z(trig["i_fill"])
            rows.append({"sym": sym, "type": r.type, "sub": r.sub, "placebo": int(r.placebo), "variant": var,
                         "rel": rel, "dir": d, "level": r.level, "t_touch": tt, "t": trig["t_fill"],
                         "t_bos1": trig["t_bos1"], "price": trig["price"], "hvn": hvn, "pressure_z": z,
                         "pressure_ok": bool((d < 0 and z <= -1) or (d > 0 and z >= 1)),
                         **B.measure(s, trig, pip)})
    ev = pd.DataFrame(rows)
    ev["t"] = pd.to_datetime(ev["t"], utc=True, unit="ns")
    ev["tf"] = "M5"
    ev = flag_events(ev, sym, m1)
    for g in B.G_LIST:
        ev[f"cost_{g}"] = E.cost_in_g(sym, g)
    ev.to_parquet(OUT / f"bos_events_is_{sym}.parquet")
    print(f"  {sym}: {len(touches):,} Beruehrungen -> {len(ev):,} Doppel-BOS-Einstiege", flush=True)
    return ev


def bos_report() -> pd.DataFrame:
    from keylevels.bos import G_LIST
    ev = pd.concat([pd.read_parquet(p) for p in sorted(OUT.glob("bos_events_is_*.parquet"))], ignore_index=True)
    ev = ev[~ev["rollover"] & ~ev["excluded"]]
    vol_sets = {"ohne": lambda d: d, "HVN": lambda d: d[d["hvn"]], "Druck": lambda d: d[d["pressure_ok"]]}

    def stats(d, g):
        res, pnl, amb = d[f"res_{g}"], d[f"pnl_{g}"], d[f"amb_{g}"]
        h, f = int((res == "hit").sum()), int((res == "fail").sum())
        net = pnl - d[f"cost_{g}"]
        n = len(d)
        return {"n": n, "h": h, "hf": h + f, "hitrate": h / (h + f) if h + f else np.nan,
                "net": float(net.mean()) if n else np.nan,
                "net_t": float(net.mean() / net.std(ddof=1) * math.sqrt(n)) if n > 2 and net.std(ddof=1) > 0 else np.nan}

    base_all = ev[ev["type"] == "no_level"]
    rows = []
    for (t, var, rel), d in ev[(ev["placebo"] == 0) & ~ev["type"].isin(["no_level", "grid_placebo"])].groupby(
            ["type", "variant", "rel"]):
        pl_all = ev[(ev["type"] == placebo_type(t)) & (ev["placebo"] > 0) & (ev["variant"] == var) & (ev["rel"] == rel)]
        bl = base_all[base_all["variant"] == var]
        for vname, vf in vol_sets.items():
            dd, pp, bb = vf(d), vf(pl_all), vf(bl)
            for g in G_LIST:
                a, p, b = stats(dd, g), stats(pp, g), stats(bb, g)
                rows.append({"type": t, "variant": var, "rel": rel, "volume": vname, "G": g, "n": a["n"],
                             "hitrate": a["hitrate"], "placebo_hitrate": p["hitrate"], "baseline_hitrate": b["hitrate"],
                             "z_placebo": _z(a["h"], a["hf"], p["h"], p["hf"]),
                             "z_baseline": _z(a["h"], a["hf"], b["h"], b["hf"]),
                             "net_g": a["net"], "net_t": a["net_t"],
                             "mfe_med": float(dd["mfe_pips"].median()) if len(dd) else np.nan,
                             "mae_med": float(dd["mae_pips"].median()) if len(dd) else np.nan})
    rep = pd.DataFrame(rows)
    # Nachbargroesse: alle G derselben Zelle mit gleichem Vorzeichen (gegen Schein-Level)
    sgn = rep.groupby(["type", "variant", "rel", "volume"])["z_placebo"].transform(
        lambda z: np.sign(z).nunique() == 1)
    rep["neighbour_same_sign"] = sgn.astype(bool)
    rep["pass"] = ((rep["n"] >= 100) & (rep["z_placebo"] > 3) & (rep["z_baseline"] > 3) &
                   rep["neighbour_same_sign"] & (rep["net_g"] > 0))
    rep.to_csv(OUT / "bos_is_report.csv", index=False)
    return rep


# --- Magnet-Trade (Plan 19.10.2026) -------------------------------------------

MAGNET_TYPES = ["week", "session", "round", "half"]   # Kandidaten; pivot_D + Schein-Level = Kontrollen


def run_magnet_events(sym: str) -> pd.DataFrame:
    from keylevels import magnet as M
    m1 = LOCK.is_only(load(sym))
    s = E.Series(m1)
    lv = all_instance_levels(m1)
    lv = lv[lv["type"].isin(["week", "session", "pivot_D"])].copy()
    lv["placebo"] = 0
    rows = []
    for D in M.D_LIST:
        sub = pd.concat([lv, E.placebo_shift(lv.drop(columns="placebo"), 2 * D, sym)], ignore_index=True)
        rows += M.instance_triggers(s, sub, D, sym)
        rows += M.grid_triggers(s, D, sym, 0, "round", 0)
        rows += M.grid_triggers(s, D, sym, 50, "half", 0)
        for off in E.PLACEBO_GRID:
            rows += M.grid_triggers(s, D, sym, off, "grid_placebo", 1)
    ev = pd.DataFrame(rows)
    ev["t"] = pd.to_datetime(ev["t"], utc=True, unit="ns")
    ev["tf"] = "M1"
    ev = flag_events(ev, sym, m1)
    ev["cost_d"] = [M.cost_in_d(sym, d) for d in ev["D"]]
    ev.to_parquet(OUT / f"magnet_events_is_{sym}.parquet")
    print(f"  {sym}: {len(ev):,} Magnet-Einstiege", flush=True)
    return ev


def magnet_report() -> pd.DataFrame:
    ev = pd.concat([pd.read_parquet(p) for p in sorted(OUT.glob("magnet_events_is_*.parquet"))], ignore_index=True)
    ev = ev[~ev["rollover"] & ~ev["excluded"]]

    def stats(d, tg):
        res, pnl = d[f"res_{tg}"], d[f"pnl_{tg}"]
        h, f = int((res == "hit").sum()), int((res == "fail").sum())
        net = pnl - d["cost_d"]
        n = len(d)
        return {"n": n, "h": h, "hf": h + f, "hit": h / (h + f) if h + f else np.nan,
                "net": float(net.mean()) if n else np.nan,
                "net_t": float(net.mean() / net.std(ddof=1) * math.sqrt(n)) if n > 2 and net.std(ddof=1) > 0 else np.nan}

    rows = []
    for t in MAGNET_TYPES + ["pivot_D"]:
        for D in sorted(ev["D"].unique()):
            real = ev[(ev["type"] == t) & (ev["placebo"] == 0) & (ev["D"] == D)]
            pl = ev[(ev["type"] == placebo_type(t)) & (ev["placebo"] > 0) & (ev["D"] == D)]
            for tg, rand in (("lvl", 0.5), ("thru", 1 / 3)):
                a, p = stats(real, tg), stats(pl, tg)
                rows.append({"type": t, "D": D, "ziel": "Level (1:1)" if tg == "lvl" else "Level+D (2:1)",
                             "n": a["n"], "hitrate": a["hit"], "placebo_hitrate": p["hit"], "zufall": rand,
                             "z_placebo": _z(a["h"], a["hf"], p["h"], p["hf"]),
                             "net_d": a["net"], "net_t": a["net_t"], "placebo_net_d": p["net"],
                             "kontrolle": t == "pivot_D"})
    rep = pd.DataFrame(rows)
    rep["neighbour_same_sign"] = rep.groupby(["type", "ziel"])["z_placebo"].transform(
        lambda z: np.sign(z).nunique() == 1).astype(bool)
    rep["pass"] = (~rep["kontrolle"] & (rep["n"] >= 100) & (rep["z_placebo"] > 3) &
                   rep["neighbour_same_sign"] & (rep["net_d"] > 0))
    rep.to_csv(OUT / "magnet_is_report.csv", index=False)
    return rep


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "magnet-events":
        for sym in sys.argv[2:]:
            run_magnet_events(sym)
        sys.exit(0)
    if cmd == "magnet-report":
        pd.set_option("display.width", 250)
        print(magnet_report().to_string())
        sys.exit(0)
    if cmd == "events":
        for sym in sys.argv[2:]:
            run_events(sym)
    elif cmd == "report":
        pd.set_option("display.width", 220)
        print(report().to_string())
    elif cmd == "bos-events":
        for sym in sys.argv[2:]:
            run_bos_events(sym)
    elif cmd == "bos-report":
        pd.set_option("display.width", 250)
        print(bos_report().to_string())
