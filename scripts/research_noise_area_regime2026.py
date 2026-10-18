"""Noise-Area-Momentum im Regime 2026: breites Raster auf dem Bruch-Halbjahr + Forward-Test.

Nutzerentscheid 2026-10-14 (Plan wild-discovering-wave): "wie bei ORB einen Edge bauen, der auf
Basis von 2026 laeuft, und diesen forward testen" -- breites Raster, SP500 + NASDAQ, nur Skript
(kein Bot), Forward-Stichtag 31.03.2027. Vorgeschichte: knowledge/projects/zarattini-noise-area-momentum.md
(Paper im Tresor durchgefallen, Diagnose 12.10.). Bekanntes Risiko: derselbe Weg ist beim ORB
gescheitert (knowledge/projects/orb-neues-regime-2026.md).

LOCK noise_area_regime2026_20261014
  IS      2025-10-01 .. 2026-03-31   (hier wird optimiert)
  OOS     2026-04-01 .. 2026-06-30   (einmal; vorbelastet, Diagnose kennt 2026)
  Tresor  2026-07-01 .. 2026-09-30   (einmal; vorbelastet)
  Forward ab 2026-10-15, oeffnet nur am Stichtag 2027-03-31

SUCHRAUM je Index (6*4*2*4*3*4*4 = 18.432, alle als Trials gezaehlt):
  vm 0.5/0.75/1.0/1.25/1.5/2.0 | lookback 14/30/60/90 | direction mom/fade
  exit vwap/band/opp/none | sides both/long/short | window all/first/am/pm
  gate none/gex_low/gex_high/rv_high  (GEX = SPX-GEX Vortag gg. 252-Tage-Median; RV14 Vortag gg. 252-Tage-Median)

AUSWAHLREGEL (vor dem ersten Lauf fixiert):
  1. zulaessig: >= 60 Trades im IS und Netto-Rendite > 0 (gemessene Kosten COST_RT, 1x)
  2. Rang nach Nachbarschafts-Score = Median des Netto-Sharpe ueber vm +-1 Stufe x lookback +-1 Stufe
     (uebrige Dimensionen gleich, Nachbarn mit < 60 Trades zaehlen als Sharpe 0)
  3. Gewinner je Index = hoechster Score; DSR gegen alle Trials
KONTROLLEN (mit eingefroren, laufen im Forward mit):
  K1 Paper-Original (eingefrorene Config 11.10., run() mit WINNERS)
  K2 Paper-Einstieg, nur erster Trade, Exit 16:00 (Diagnose-Hypothese: Stop kostet)
  K3 Gewinner ohne Gate (nur wenn der Gewinner ein Gate hat)
ERFOLG IM FORWARD (vorab): Netto-bps je Trade > 0 UND besser als K1, je Index.

  python scripts/research_noise_area_regime2026.py is
  python scripts/research_noise_area_regime2026.py unseal
  python scripts/research_noise_area_regime2026.py register
  python scripts/research_noise_area_regime2026.py evaluate      # ab 2027-03-31
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import build_grid, metrics, run, run_general, slice_grid  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_noise_area_momentum import COST_RT, GEX_FILE, INSTRUMENTS, WINNERS, grid  # noqa: E402

STRATEGY = "noise_area_regime2026_20261014"
IS_START, IS_END, OOS_END, TRESOR_END = "2025-10-01", "2026-03-31", "2026-06-30", "2026-09-30"
FORWARD_START, EVAL_DATE = "2026-10-15", "2027-03-31"
WARMUP_START = "2024-09-01"          # Vorlauf fuer Lookback 90 und die 252-Tage-Gates
OUT = ROOT / "noise_area_momentum" / "results"
MIN_TRADES = 60

VMS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
LBS = [14, 30, 60, 90]
DIMS = {"direction": ["mom", "fade"], "exit": ["vwap", "band", "opp", "none"], "sides": ["both", "long", "short"],
        "window": ["all", "first", "am", "pm"], "gate": ["none", "gex_low", "gex_high", "rv_high"]}
N_VARIANTS = len(VMS) * len(LBS) * int(np.prod([len(v) for v in DIMS.values()]))


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def gates(g: dict) -> dict:
    d = g["dates"]
    gex = pd.read_csv(GEX_FILE, parse_dates=["date"]).set_index("date")["gex"].sort_index().shift(1)
    med = gex.rolling(252, min_periods=120).median()
    low = (gex < med).reindex(d, method="ffill").fillna(False).to_numpy(bool)
    high = (gex >= med).reindex(d, method="ffill").fillna(False).to_numpy(bool)
    rv = pd.Series(g["close"][:, -1], index=d).pct_change().rolling(14).std().shift(1)
    rvh = (rv > rv.rolling(252, min_periods=120).median()).fillna(False).to_numpy(bool)
    return {"none": None, "gex_low": low, "gex_high": high, "rv_high": rvh}


def run_variant(g: dict, gt: dict, cfg: dict, **kw) -> pd.DataFrame:
    c = dict(cfg)
    return run_general(g, gate=gt[c.pop("gate")], **c, **kw)


def grid_short(inst: str) -> dict:
    return slice_grid(grid(inst), WARMUP_START)


def stage_is() -> None:
    lk = lock()
    if lk.trials == 0:
        lk.log_trials(N_VARIANTS * len(INSTRUMENTS), note="breites Raster je Index (Nutzerentscheid 14.10.)")
    OUT.mkdir(parents=True, exist_ok=True)
    for inst in INSTRUMENTS:
        g = grid_short(inst)
        gt = gates(g)
        rows = []
        for vm, lbk, *rest in itertools.product(VMS, LBS, *DIMS.values()):
            cfg = {"vm": vm, "lookback": lbk, **dict(zip(DIMS, rest))}
            df = lk.is_only(run_variant(g, gt, cfg, cost_rt_bps=COST_RT[inst]))
            d = df[df["valid"]]
            r = d["ret_net"]
            sd = r.std(ddof=1)
            rows.append({**cfg, "trades": int(d["trades"].sum()), "tage": len(r),
                         "sharpe": r.mean() / sd * np.sqrt(252) if sd > 0 else 0.0,
                         "netto_bps_trade": r.sum() / max(d["trades"].sum(), 1) * 1e4,
                         "summe_%": r.sum() * 100})
        rep = pd.DataFrame(rows)
        rep["sharpe_z"] = np.where(rep["trades"] >= MIN_TRADES, rep["sharpe"], 0.0)
        key = list(DIMS)
        rep["vm_i"] = rep["vm"].map({v: i for i, v in enumerate(VMS)})
        rep["lb_i"] = rep["lookback"].map({v: i for i, v in enumerate(LBS)})
        piv = {k: grp.set_index(["vm_i", "lb_i"])["sharpe_z"] for k, grp in rep.groupby(key)}
        score = []
        for _, row in rep.iterrows():
            s = piv[tuple(row[k] for k in key)]
            nb = [s.get((a, b)) for a in range(row.vm_i - 1, row.vm_i + 2) for b in range(row.lb_i - 1, row.lb_i + 2)]
            score.append(float(np.median([x for x in nb if x is not None])))
        rep["score"] = score
        rep["zulaessig"] = (rep["trades"] >= MIN_TRADES) & (rep["summe_%"] > 0)
        rep = rep.drop(columns=["vm_i", "lb_i", "sharpe_z"]).sort_values("score", ascending=False)
        rep.to_csv(OUT / f"regime2026_is_{inst}.csv", index=False)
        top = rep[rep["zulaessig"]].head(50)
        pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
        print(f"\n===== {inst}: {rep['zulaessig'].sum()} von {len(rep)} zulaessig =====")
        print(top.head(20).round(3).to_string(index=False))
        print("\nTop 50 nach Dimension:")
        for k in key:
            print(f"  {k}: {top[k].value_counts().to_dict()}")
        print("Gewinner:", top.iloc[0][["vm", "lookback", *key]].to_dict() if len(top) else "keiner")


def winners_from_is() -> dict:
    out = {}
    for inst in INSTRUMENTS:
        rep = pd.read_csv(OUT / f"regime2026_is_{inst}.csv")
        w = rep[rep["zulaessig"]].sort_values("score", ascending=False).iloc[0]
        out[inst] = {"vm": float(w.vm), "lookback": int(w.lookback), **{k: str(w[k]) for k in DIMS}}
    return out


def frozen_set(win: dict) -> dict:
    """Je Index: Gewinner + Kontrollen als (name -> cfg); K1 laeuft ueber run() (Paper-Engine)."""
    s = {}
    for inst in INSTRUMENTS:
        w = win[inst]
        p = WINNERS[inst]
        v = {"G Gewinner": w,
             "K1 Paper-Original": {"paper": True, **p},
             "K2 Paper, nur 1. Trade, Exit 16:00": {"vm": p["vm"], "lookback": p["lookback"], "direction": "mom",
                                                    "exit": "none", "sides": "both", "window": "first", "gate": "none"}}
        if w["gate"] != "none":
            v["K3 Gewinner ohne Gate"] = {**w, "gate": "none"}
        s[inst] = v
    return s


def run_named(g: dict, gt: dict, inst: str, cfg: dict, **kw) -> pd.DataFrame:
    if cfg.get("paper"):
        return run(g, vm=cfg["vm"], lookback=cfg["lookback"], stop="vwap", **kw)
    return run_variant(g, gt, cfg, **kw)


def stage_unseal() -> None:
    lk = lock()
    win = winners_from_is()
    fs = frozen_set(win)
    h = lk.freeze({"varianten": fs, "kosten_rt_bps": COST_RT, "auswahl": "Nachbarschafts-Score, >= 60 Trades"})
    n_trials = lk.trials
    print(f"Eingefroren {h[:12]}, Trials {n_trials}")
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)
    if "tresor" not in lk._load()["unsealed"]:
        lk.unseal("tresor", h)
    rows = []
    for inst in INSTRUMENTS:
        g = grid_short(inst)
        gt = gates(g)
        for name, cfg in fs[inst].items():
            for lag in (0, 5):
                df = run_named(g, gt, inst, cfg, cost_rt_bps=COST_RT[inst], lag_bars=lag)
                for per, sl in (("IS", lk.is_only(df)), ("OOS", lk.stage_slice(df, "oos")),
                                ("Tresor", lk.stage_slice(df, "tresor"))):
                    if lag == 5 and per == "IS":
                        continue
                    m = metrics(sl)
                    d = sl[sl["valid"]]
                    rows.append({"inst": inst, "variante": name, "lag": lag, "periode": per,
                                 "trades": int(d["trades"].sum()),
                                 "netto_bps_trade": d["ret_net"].sum() / max(d["trades"].sum(), 1) * 1e4,
                                 **{k: m.get(k) for k in ("sharpe", "t", "cagr_%", "mdd_%")}})
        d = lk.is_only(run_variant(g, gt, win[inst], cost_rt_bps=COST_RT[inst])).query("valid")["ret_net"]
        sr = d.mean() / d.std(ddof=1)
        print(f"{inst} Gewinner {win[inst]}: DSR {deflated_sharpe(sr, len(d), n_trials, float(d.skew()), float(d.kurt() + 3)):.3f}"
              f" (Sharpe ann. {sr * np.sqrt(252):.2f})")
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "regime2026_unseal.csv", index=False)
    pd.set_option("display.width", 250)
    print(rep.round(3).to_string(index=False))


def stage_register() -> None:
    lk = lock()
    lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
    print("Forward registriert ab", FORWARD_START, "| oeffnet am", EVAL_DATE)


def stage_evaluate() -> None:
    lk = lock()
    st = lk._load()
    h = st["frozen"]["hash"]
    fs = st["frozen"]["config"]["varianten"]
    lk.unseal("forward", h)                     # bricht vor dem Stichtag ab
    rows = []
    for inst in INSTRUMENTS:
        g = build_grid(fetch_m1(inst, WARMUP_START, EVAL_DATE, force_refresh=True))
        gt = gates(g)
        for name, cfg in fs[inst].items():
            df = run_named(g, gt, inst, cfg, cost_rt_bps=COST_RT[inst])
            sl = df[(df.index >= FORWARD_START) & (df.index <= EVAL_DATE)]
            d = sl[sl["valid"]]
            rows.append({"inst": inst, "variante": name, "trades": int(d["trades"].sum()),
                         "netto_bps_trade": d["ret_net"].sum() / max(d["trades"].sum(), 1) * 1e4,
                         **{k: metrics(sl).get(k) for k in ("sharpe", "t", "cagr_%", "mdd_%")}})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "regime2026_forward.csv", index=False)
    print(rep.round(3).to_string(index=False))
    for inst in INSTRUMENTS:
        r = rep[rep.inst == inst].set_index("variante")["netto_bps_trade"]
        ok = r["G Gewinner"] > 0 and r["G Gewinner"] > r["K1 Paper-Original"]
        print(f"{inst}: Erfolgskriterium {'ERFUELLT' if ok else 'NICHT erfuellt'}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"is": stage_is, "unseal": stage_unseal, "register": stage_register, "evaluate": stage_evaluate}[sys.argv[1]]()
