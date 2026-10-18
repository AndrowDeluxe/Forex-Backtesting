"""Noise-Area-Momentum: Oel-Faktoren an 2026 angepasst (EXPLORATIV, KEIN BELEG) + Forward.

Nutzerauftrag 2026-10-14: "Gehe eine Oel-Optimierung an und schaue, welche Faktoren den Edge
profitabel halten koennten." Muster: research_orb_oel_filter.py Option 2 (12.10.).
Vorgeschichte: knowledge/projects/zarattini-noise-area-momentum.md (Abschnitt Oel-Zusammenhaenge):
2026 kippt die Oel-Index-Korrelation ins Negative, Gewinne nur an Oel-Schock-Tagen.

LOCK noise_area_oel_fit2026_20261014
  Fit ("IS")  2025-10-01 .. 2026-09-30   -- ganzes Jahr, kein OOS-Fenster aus 2026 (Lehre aus dem
              Regime-2026-Raster: ein halbes Jahr IS fiel sofort durch)
  "OOS"       2026-10-01 .. 2026-10-14   -- formal, leer, nur damit der Forward nach Lock-Regel oeffnen darf
  Forward     ab 2026-10-15, Stichtag 2027-03-31
  Rueckblick  dieselbe Regel auf 2016-07 .. 2025-09 (schadet sie frueher?)

Oel-Faktoren (alle vor dem Einstieg bekannt; Oel auf Index-Uhr 09:30-16:00):
  K_w     Korrelation Tagesrenditen Oel <-> Index, w = 20/40/60 Tage bis Vortag
  move    Oel 09:30 -> Entscheidungszeit, relativ zur Trade-Richtung (gleich/gegen), Mindestgroesse
          mult x Median |move| der letzten 60 Tage zur selben Uhrzeit
  gap     Oel-Gap Vortag 16:00 -> 09:30 relativ zur Trade-Richtung
  ovol    Oel-Vola 20 Tage (bis Vortag) ueber/unter ihrem 252-Tage-Median
  trend5  Oel-Rendite der letzten 5 Tage (bis Vortag) relativ zur Trade-Richtung
Basis: Paper-Config (WINNERS 11.10.: mom, VWAP-Stop) oder K2 (mom, nur 1. Trade, halten bis 16:00).

RASTER je Index: 2 Basen x 13 K x 3 move-Relationen x 4 mult x 3 gap x 3 ovol x 3 trend5 = 8.424
AUSWAHL: >= 50 Trades im Fit-Jahr, hoechster t (Netto-Tagesrenditen, 1x). DSR ueber alle Trials.

  python scripts/research_noise_area_oel_fit2026.py screen     # Einzelfaktoren, beschreibend
  python scripts/research_noise_area_oel_fit2026.py fit        # Raster + Einfrieren + Forward
  python scripts/research_noise_area_oel_fit2026.py evaluate   # ab 2027-03-31
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import DECISIONS, build_grid, run_general, slice_grid  # noqa: E402
from ny_open_orb.data import fetch_m1  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402
from research_noise_area_momentum import COST_RT, INSTRUMENTS, IS_START, WINNERS, grid  # noqa: E402
from research_noise_area_oel import oil_grid  # noqa: E402

STRATEGY = "noise_area_oel_fit2026_20261014"
FIT_START, FIT_END, OOS_END = "2025-10-01", "2026-09-30", "2026-10-14"
FORWARD_START, EVAL_DATE = "2026-10-15", "2027-03-31"
WARMUP = "2024-06-01"
OUT = ROOT / "noise_area_momentum" / "results"
MIN_TRADES = 50
PERIODS = [("2016-22", IS_START, "2023-01-01"), ("2023-09/25", "2023-01-01", "2025-10-01"),
           ("Fit 10/25-09/26", FIT_START, "2026-10-01")]

K_OPTS = [None] + [(w, t) for w in (20, 40, 60) for t in (-0.3, -0.2, -0.1, 0.0)]
REL = ["any", "gleich", "gegen"]
MULT = [0.0, 0.5, 1.0, 1.5]
TRI = {"gap": REL, "ovol": ["any", "hoch", "niedrig"], "trend5": REL}


def bases(inst: str) -> dict:
    w = WINNERS[inst]
    c = dict(vm=w["vm"], lookback=w["lookback"], direction="mom", sides="both")
    return {"paper": dict(c, exit="vwap", window="all"), "k2": dict(c, exit="none", window="first")}


def features(g: dict, oil: dict) -> dict:
    dates = g["dates"]
    oc = pd.Series(oil["close"][:, -1], index=oil["dates"])
    ic = pd.Series(g["close"][:, -1], index=dates)
    r = pd.DataFrame({"oil": oc.pct_change(), "idx": ic.pct_change()}).dropna()
    f = {f"k{w}": r["oil"].rolling(w).corr(r["idx"]).shift(1).reindex(dates).to_numpy() for w in (20, 40, 60)}
    ro = oc.pct_change()
    rv = ro.rolling(20).std().shift(1)
    f["ovol_hoch"] = (rv > rv.rolling(252, min_periods=120).median()).reindex(dates).to_numpy(dtype=float)
    f["trend5"] = np.sign((oc / oc.shift(5) - 1).shift(1)).reindex(dates).to_numpy()
    pos = pd.Index(oil["dates"]).get_indexer(dates)
    have = pos >= 0
    m = DECISIONS - 1
    move = np.full((len(dates), len(m)), np.nan)
    move[have] = oil["close"][pos[have]][:, m] / oil["open"][pos[have], 0][:, None] - 1
    f["move"] = move
    f["move_med"] = pd.DataFrame(np.abs(move), index=dates).rolling(60, min_periods=40).median().shift(1).to_numpy()
    prev_close = np.r_[np.nan, oil["close"][:-1, -1]]
    gap = np.full(len(dates), np.nan)
    gap[have] = oil["open"][pos[have], 0] / prev_close[pos[have]] - 1
    f["gap"] = np.sign(gap)
    return f


def masks(f: dict, k=None, rel="any", mult=0.0, gap="any", ovol="any", trend5="any"):
    """long_ok/short_ok (Tage x Entscheidungen)."""
    n, nd = f["move"].shape
    day = np.ones(n, dtype=bool)
    if k is not None:
        day &= np.nan_to_num(f[f"k{k[0]}"], nan=9) < k[1]
    if ovol != "any":
        day &= (f["ovol_hoch"] == 1) if ovol == "hoch" else (f["ovol_hoch"] == 0)
    lo = np.repeat(day[:, None], nd, axis=1)
    so = lo.copy()
    for name, val in (("gap", gap), ("trend5", trend5)):
        if val != "any":
            s = np.nan_to_num(f[name], nan=0)[:, None]
            want = 1 if val == "gleich" else -1
            lo &= s * want > 0
            so &= -s * want > 0
    mv = f["move"]
    ok = ~np.isnan(mv)
    if mult > 0:
        ok &= np.abs(mv) >= mult * np.nan_to_num(f["move_med"], nan=np.inf)
    if rel != "any":
        want = 1 if rel == "gleich" else -1
        lo &= ok & (np.nan_to_num(mv) * want > 0)
        so &= ok & (-np.nan_to_num(mv) * want > 0)
    elif mult > 0:
        lo &= ok
        so &= ok
    return lo, so


def stats(df: pd.DataFrame, a: str, b: str) -> dict:
    sl = df[(df.index >= a) & (df.index < b) & df["valid"]]
    r, tr = sl["ret_net"], sl["trades"].sum()
    sd = r.std(ddof=1)
    return {"trades": int(tr), "netto_bps_trade": r.sum() / max(tr, 1) * 1e4,
            "brutto_bps_trade": sl["gross_1x"].sum() / max(tr, 1) * 1e4,
            "t": r.mean() / sd * np.sqrt(len(r)) if sd > 0 else 0.0,
            "sharpe": r.mean() / sd * np.sqrt(252) if sd > 0 else 0.0}


SCREEN = {
    "keiner": {}, "K20 < -0,2": {"k": (20, -0.2)}, "K20 < 0": {"k": (20, 0.0)}, "K60 < 0": {"k": (60, 0.0)},
    "Oel gleich": {"rel": "gleich"}, "Oel gegen": {"rel": "gegen"},
    "Oel bewegt >= 1x Median": {"mult": 1.0}, "Oel bewegt >= 1,5x Median": {"mult": 1.5},
    "Gap gleich": {"gap": "gleich"}, "Gap gegen": {"gap": "gegen"},
    "Oel-Vola hoch": {"ovol": "hoch"}, "Oel-Vola niedrig": {"ovol": "niedrig"},
    "Oel-Trend5 gleich": {"trend5": "gleich"}, "Oel-Trend5 gegen": {"trend5": "gegen"},
}


def stage_screen() -> None:
    oil = oil_grid("index")
    rows = []
    for inst in INSTRUMENTS:
        g = grid(inst)
        f = features(g, oil)
        for bname, bc in bases(inst).items():
            for sname, sc in SCREEN.items():
                lo, so = masks(f, **sc)
                df = run_general(g, cost_rt_bps=COST_RT[inst], long_ok=lo, short_ok=so, **bc)
                for per, a, b in PERIODS:
                    rows.append({"inst": inst, "basis": bname, "faktor": sname, "periode": per, **stats(df, a, b)})
    rep = pd.DataFrame(rows)
    rep.to_csv(OUT / "oel_fit2026_screen.csv", index=False)
    pd.set_option("display.width", 250)
    for inst in INSTRUMENTS:
        for bname in ("paper", "k2"):
            s = rep[(rep.inst == inst) & (rep.basis == bname)]
            p = s.pivot(index="faktor", columns="periode", values="netto_bps_trade")[[x[0] for x in PERIODS]]
            n = s.pivot(index="faktor", columns="periode", values="trades")[[x[0] for x in PERIODS]]
            print(f"\n=== {inst} / Basis {bname}: netto bps je Trade (Trades) ===")
            print(p.round(2).astype(str).add(" (").add(n.astype(str)).add(")").reindex(list(SCREEN)).to_string())


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(FIT_START, FIT_END, OOS_END)
    return lk


def stage_fit() -> None:
    lk = lock()
    n_var = 2 * len(K_OPTS) * len(REL) * len(MULT) * 27
    if lk.trials == 0:
        lk.log_trials(n_var * len(INSTRUMENTS), note="Oel-Faktor-Raster je Index, angepasst an 10/25-09/26 (explorativ)")
    oil = oil_grid("index")
    winners, pd_opts = {}, pd.set_option("display.width", 250)
    for inst in INSTRUMENTS:
        gfull = grid(inst)
        g = slice_grid(gfull, WARMUP)
        f = features(g, oil)
        rows = []
        for bname, bc in bases(inst).items():
            for k, rel, mult, gp, ov, t5 in itertools.product(K_OPTS, REL, MULT, *TRI.values()):
                lo, so = masks(f, k=k, rel=rel, mult=mult, gap=gp, ovol=ov, trend5=t5)
                df = run_general(g, cost_rt_bps=COST_RT[inst], long_ok=lo, short_ok=so, **bc)
                rows.append({"basis": bname, "k": str(k), "rel": rel, "mult": mult, "gap": gp, "ovol": ov,
                             "trend5": t5, **stats(df, FIT_START, "2026-10-01")})
        rep = pd.DataFrame(rows)
        rep.to_csv(OUT / f"oel_fit2026_grid_{inst}.csv", index=False)
        ok = rep[rep.trades >= MIN_TRADES].sort_values("t", ascending=False)
        top = ok.head(50)
        print(f"\n===== {inst}: {len(ok)} von {len(rep)} mit >= {MIN_TRADES} Trades =====")
        print(top.head(15).round(2).to_string(index=False))
        print("Top 50 nach Faktor:")
        for c in ("basis", "k", "rel", "mult", "gap", "ovol", "trend5"):
            print(f"  {c}: {top[c].value_counts().to_dict()}")
        w = ok.iloc[0].to_dict()
        winners[inst] = {c: w[c] for c in ("basis", "k", "rel", "mult", "gap", "ovol", "trend5")}
        # DSR (Tagesrenditen im Fit-Jahr)
        kk = None if w["k"] == "None" else eval(w["k"])  # noqa: S307 -- eigener str(tuple)
        lo, so = masks(f, k=kk, rel=w["rel"], mult=w["mult"], gap=w["gap"], ovol=w["ovol"], trend5=w["trend5"])
        df = run_general(g, cost_rt_bps=COST_RT[inst], long_ok=lo, short_ok=so, **bases(inst)[w["basis"]])
        r = df[(df.index >= FIT_START) & (df.index < "2026-10-01") & df.valid]["ret_net"]
        sr = r.mean() / r.std(ddof=1)
        print(f"Gewinner {inst}: {winners[inst]} | DSR {deflated_sharpe(sr, len(r), lk.trials, float(r.skew()), float(r.kurt() + 3)):.3f}")
        # Rueckblick auf der vollen Historie
        ff = features(gfull, oil)
        lo, so = masks(ff, k=kk, rel=w["rel"], mult=w["mult"], gap=w["gap"], ovol=w["ovol"], trend5=w["trend5"])
        bc = bases(inst)[w["basis"]]
        dw = run_general(gfull, cost_rt_bps=COST_RT[inst], long_ok=lo, short_ok=so, **bc)
        db = run_general(gfull, cost_rt_bps=COST_RT[inst], **bc)
        for per, a, b in PERIODS:
            print(f"  {per}: Regel {stats(dw, a, b)['netto_bps_trade']:.2f} bps ({stats(dw, a, b)['trades']}), "
                  f"Basis {stats(db, a, b)['netto_bps_trade']:.2f} bps ({stats(db, a, b)['trades']})")
    h = lk.freeze({"gewinner": winners, "auswahl": f">= {MIN_TRADES} Trades, hoechster t", "kosten": COST_RT})
    if "oos" not in lk._load()["unsealed"]:
        lk.unseal("oos", h)        # formal (leeres Fenster), damit der Forward oeffnen darf
    if lk._load().get("forward") is None:
        lk.register_forward(FORWARD_START, EVAL_DATE, 10**6)
    print("Eingefroren", h[:12], "| Forward ab", FORWARD_START, "Stichtag", EVAL_DATE)


def stage_evaluate() -> None:
    lk = lock()
    st = lk._load()
    lk.unseal("forward", st["frozen"]["hash"])
    oil = oil_grid("index", end=EVAL_DATE, refresh=True)
    for inst, w in st["frozen"]["config"]["gewinner"].items():
        g = build_grid(fetch_m1(inst, IS_START, EVAL_DATE, force_refresh=True))
        f = features(g, oil)
        kk = None if w["k"] == "None" else eval(w["k"])  # noqa: S307
        lo, so = masks(f, k=kk, rel=w["rel"], mult=w["mult"], gap=w["gap"], ovol=w["ovol"], trend5=w["trend5"])
        bc = bases(inst)[w["basis"]]
        for name, df in (("Regel", run_general(g, cost_rt_bps=COST_RT[inst], long_ok=lo, short_ok=so, **bc)),
                         ("Basis", run_general(g, cost_rt_bps=COST_RT[inst], **bc))):
            print(inst, name, stats(df, FORWARD_START, "2027-04-01"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    {"screen": stage_screen, "fit": stage_fit, "evaluate": stage_evaluate}[sys.argv[1]]()
