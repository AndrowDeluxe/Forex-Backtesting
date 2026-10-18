"""Gold ASB: Neuoptimierung NUR auf In-Sample, danach einmal OOS, einmal Tresor.

Nutzerauftrag 2026-10-15 (Gruppenarbeit, Standardprozess wie ORB 05.10.): Die
Live-Konfiguration (Stop 1,5x Range, Storno 03:00 NY, ADX>=15, SMA200, Silber 5T,
Liquiditaet 2/3-Quantil, Exit 11:00 NY) wurde am 01.10. auf allen Daten gewaehlt.
Dieser Lauf baut die Strategie so nach, als waere sie nur auf IS optimiert worden --
unter der Overfitting-Sperre (research_lock.py, knowledge/areas/overfitting-sperre.md).

SPLIT (registriert, unveraenderlich, Nutzerentscheid: wie ORB):
  IS     2016-01-01 .. 2022-12-31   optimieren
  OOS    2023-01-01 .. 2025-09-30   einmal testen
  Tresor 2025-10-01 .. 2026-09-30   einmal oeffnen
  Vorbehalt: der Tresor wurde im Live-Tresor-Check (live-strategien-tresor-check.md)
  schon einmal angesehen -- Rekonstruktion "als ob nur IS", kein jungfraeulicher Holdout.

SUCHRAUM (9 Punkte = alle Live-Stellschrauben, Nutzerentscheid):
  Stop 1,0/1,5/2,0 x Range x Storno 02:00/02:30/03:00/04:00 x Exit 10:00/11:00/12:00
  x ADX aus/15/20/25 x Trend-SMA aus/100/200 x Silber aus/3/5/10 Tage
  x Liquiditaet aus/Quantil 0,5/2/3/0,8 x Richtung beide/long/short.
  Fest: Range 21:00-01:00 NY, ruhende OCO-Stop-Order ab 01:00, kein TP/BE.

AUSWAHLREGEL (vor dem Lauf festgelegt, nur IS, wie ORB):
  1. Mindestbedingungen: >= 100 IS-Trades, PF > 1,3, beide IS-Haelften > 0
     (Haelften nach Trade-Anzahl).
  2. Score = t-Wert (Ø R / Std R x sqrt(n)), geglaettet: Median aus Zelle und
     direkten Stop-/Storno-Nachbarn derselben Konfiguration (Plateau statt Spitze).
  3. Gewinner = hoechster geglaetteter Score unter den Zellen mit (1).
  4. Deflated Sharpe gegen die gezaehlten Versuche.

Ausfuehrung: M5-Simulation aus research_gold_asb_optimization.py, TTP-Kosten
2,08 bps Round-Trip (teuerster Broker, Nutzerentscheid).

  python scripts/research_gold_asb_is_only_reopt.py --stage grid      # nur IS
  python scripts/research_gold_asb_is_only_reopt.py --stage evaluate  # freeze -> OOS -> Tresor
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from asian_range_breakout.filters import attach_series_change, attach_series_level, rolling_liquidity_threshold  # noqa: E402
from research_gold_asb_execution_costs import load_all  # noqa: E402
from research_gold_asb_optimization import TTP_BPS, day_table, simulate  # noqa: E402
from research_lock import Lock, deflated_sharpe  # noqa: E402

STRATEGY = "gold_asb_is_reopt_20261015"
IS_START, IS_END, OOS_END, TRESOR_END = "2016-01-01", "2022-12-31", "2025-09-30", "2026-09-30"
RES = ROOT / "asian_range_breakout" / "results"

STOPS = (1.0, 1.5, 2.0)
CANCELS = ("02:00", "02:30", "03:00", "04:00")
EXITS = {"10:00": "10:15", "11:00": "11:15", "12:00": "12:15"}  # Label -> Close der M15-Bar (Engine-Konvention)
ADX = (None, 15.0, 20.0, 25.0)
SMA = (None, 100, 200)
SILVER = (None, 3, 5, 10)
LIQ = (None, 0.5, 2 / 3, 0.8)
DIRS = ("beide", "long", "short")

LIVE = {"stop": 1.5, "cancel": "03:00", "exit": "11:00", "adx": 15.0, "sma": 200, "silver": 5,
        "liq": 2 / 3, "dirs": "beide"}


def lock() -> Lock:
    lk = Lock(STRATEGY)
    lk.register_split(IS_START, IS_END, OOS_END, TRESOR_END)
    return lk


def load_days():
    """Tagestabelle mit allen Filtermerkmalen (kausal: Wert des letzten Tages strikt
    vor dem Entry, gleiche Ausrichtung wie filters.py)."""
    m15, m5, dc, dcs, fr = load_all()
    days = day_table(m15, m5, dc, dcs, fr)
    tmp = days[["window_end"]].assign(entry_time=days["window_end"])
    for w in (100, 200):
        tmp = attach_series_level(tmp, dc.rolling(w).mean(), f"sma{w}")
    for w in (3, 5, 10):
        tmp = attach_series_change(tmp, dcs, f"silver{w}", window=w)
    for q in LIQ[1:]:
        tmp = attach_series_level(tmp, rolling_liquidity_threshold(fr, q, 250), f"thr{q:.3f}")
    feats = tmp.drop(columns="entry_time")
    days = days.merge(feats, on="window_end", how="left")
    days = days.dropna(subset=["sma100", "sma200", "silver3", "silver10"]).reset_index(drop=True)
    return days.set_index("window_end", drop=False), m5


def run_sim(days, m5, stop, cancel, exit_label) -> pd.DataFrame:
    t = simulate(days.reset_index(drop=True), m5, cancel=cancel, stop_frac=stop, exit_time=EXITS[exit_label],
                 bps=TTP_BPS)
    if t.empty:
        return t
    f = days.set_index("window_end")
    for c in ("gold_close_prior", "sma100", "sma200", "silver3", "silver5", "silver10", "friction_prior",
              *[f"thr{q:.3f}" for q in LIQ[1:]]):
        t[c] = f[c].reindex(t["window_end"]).to_numpy()
    return t.sort_values("window_end").reset_index(drop=True)


def mask(t: pd.DataFrame, cfg: dict) -> np.ndarray:
    m = np.ones(len(t), dtype=bool)
    d = t["dir"].to_numpy()
    if cfg["adx"] is not None:
        m &= t["adx"].to_numpy() >= cfg["adx"]
    if cfg["sma"] is not None:
        up = t["gold_close_prior"].to_numpy() > t[f"sma{cfg['sma']}"].to_numpy()
        m &= np.where(d == 1, up, ~up)
    if cfg["silver"] is not None:
        s = t[f"silver{cfg['silver']}"].to_numpy()
        m &= np.where(d == 1, s > 0, s < 0)
    if cfg["liq"] is not None:
        m &= t["friction_prior"].to_numpy() <= t[f"thr{cfg['liq']:.3f}"].to_numpy()
    if cfg["dirs"] == "long":
        m &= d == 1
    elif cfg["dirs"] == "short":
        m &= d == -1
    return m


def metrics(r: pd.Series) -> dict:
    if len(r) < 2:
        return {"n": len(r)}
    std = r.std(ddof=1)
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    half = len(r) // 2
    years = (r.index.max() - r.index.min()).days / 365.25
    return {"n": len(r), "per_year": len(r) / years if years > 0 else np.nan, "avg": r.mean(), "std": std,
            "t": r.mean() / std * np.sqrt(len(r)) if std > 0 else np.nan,
            "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
            "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
            "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "win": (r > 0).mean(),
            "yrs_pos": int((r.groupby(r.index.year).sum() > 0).sum()), "yrs": r.index.year.nunique(),
            "skew": float(r.skew()), "kurt": float(r.kurt() + 3)}


def series(t: pd.DataFrame, cfg: dict) -> pd.Series:
    s = t[mask(t, cfg)]
    return pd.Series(s["R"].to_numpy(), index=pd.DatetimeIndex(s["window_end"]))


FILTER_KEYS = ("adx", "sma", "silver", "liq", "dirs")


# ---------------------------------------------------------------------------
def stage_grid() -> int:
    lk = lock()
    days, m5 = load_days()
    days = lk.is_only(days)   # Sperre: nur IS-Tage werden simuliert
    print(f"IS-Tage: {len(days)}  {days.index.min()} .. {days.index.max()}", flush=True)

    rows, count = [], 0
    for stop, cancel, ex in itertools.product(STOPS, CANCELS, EXITS):
        t = run_sim(days, m5, stop, cancel, ex)
        for adx, sma, silver, liq, dirs in itertools.product(ADX, SMA, SILVER, LIQ, DIRS):
            count += 1
            cfg = {"stop": stop, "cancel": cancel, "exit": ex, "adx": adx, "sma": sma, "silver": silver,
                   "liq": liq, "dirs": dirs}
            m = metrics(series(t, cfg))
            rows.append({**cfg, **{k: m.get(k) for k in ("n", "avg", "std", "t", "pf", "sum", "dd", "h1", "h2", "win")}})
        print(f"  stop={stop} storno={cancel} exit={ex}: fertig", flush=True)
    lk.log_trials(count, note="IS-Gitter (9 Punkte)")
    grid = pd.DataFrame(rows)
    RES.mkdir(parents=True, exist_ok=True)
    grid.to_csv(RES / "is_reopt_grid.csv", index=False)

    # --- Auswahl --------------------------------------------------------------
    grid["eligible"] = (grid.n >= 100) & (grid.pf > 1.3) & (grid.h1 > 0) & (grid.h2 > 0)
    for k in ("adx", "sma", "silver", "liq"):
        grid[f"{k}_k"] = grid[k].fillna(-1)
    keys = ["exit", "adx_k", "sma_k", "silver_k", "liq_k", "dirs", "stop", "cancel"]
    t_lookup = grid.set_index(keys)["t"].to_dict()

    def smooth(row):
        si, ci = STOPS.index(row.stop), CANCELS.index(row.cancel)
        vals = []
        for ds, dc in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            a, b = si + ds, ci + dc
            if 0 <= a < len(STOPS) and 0 <= b < len(CANCELS):
                v = t_lookup.get((row.exit, row.adx_k, row.sma_k, row.silver_k, row.liq_k, row.dirs,
                                  STOPS[a], CANCELS[b]))
                if v is not None and not pd.isna(v):
                    vals.append(v)
        return float(np.median(vals)) if vals else np.nan

    el = grid[grid.eligible].copy()
    el["t_smooth"] = el.apply(smooth, axis=1)
    el = el.sort_values("t_smooth", ascending=False)
    allg = grid[grid.n >= 30]
    sr_var = float((allg["avg"] / allg["std"]).var())
    print(f"\n{len(el)} von {len(grid)} Zellen erfuellen die Mindestbedingungen")
    cols = ["stop", "cancel", "exit", "adx", "sma", "silver", "liq", "dirs", "n", "avg", "pf", "t", "t_smooth"]
    pd.set_option("display.width", 250)
    print(el.head(12)[cols].round(3).to_string(index=False))
    live = grid[(grid.stop == LIVE["stop"]) & (grid.cancel == LIVE["cancel"]) & (grid.exit == LIVE["exit"])
                & (grid.adx_k == LIVE["adx"]) & (grid.sma_k == LIVE["sma"]) & (grid.silver_k == LIVE["silver"])
                & np.isclose(grid.liq_k, LIVE["liq"]) & (grid.dirs == LIVE["dirs"])]
    print("\nLive-Config auf IS (Plausibilitaet):")
    print(live[cols[:-1]].round(3).to_string(index=False))
    winner = None
    if not el.empty:
        w = el.iloc[0]
        winner = {"stop": float(w.stop), "cancel": w.cancel, "exit": w.exit,
                  "adx": None if w.adx_k == -1 else float(w.adx), "sma": None if w.sma_k == -1 else int(w.sma),
                  "silver": None if w.silver_k == -1 else int(w.silver),
                  "liq": None if w.liq_k == -1 else float(w.liq), "dirs": w.dirs}
    out = {"winner": winner, "n_trials": count, "sr_var_trials": sr_var, "n_eligible": int(len(el))}
    (RES / "is_reopt_selection.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    el.head(50)[cols + ["h1", "h2", "dd", "win"]].to_csv(RES / "is_reopt_top50.csv", index=False)
    print("\nGewinner:", winner)
    print("Auswahl gespeichert -> is_reopt_selection.json (noch NICHT eingefroren)")
    return 0


def stage_evaluate() -> int:
    lk = lock()
    sel = json.loads((RES / "is_reopt_selection.json").read_text(encoding="utf-8"))
    winner = sel["winner"]
    if winner is None:
        print("Kein IS-Kandidat -- Strategie laut IS nicht handelbar, nichts zu oeffnen.")
        return 0
    h = lk.freeze(winner)
    print("eingefroren:", h)
    st = json.loads(lk.path.read_text(encoding="utf-8"))
    oos = lk.unseal("oos", h) if "oos" not in st["unsealed"] else None
    tre = lk.unseal("tresor", h) if "tresor" not in st["unsealed"] else None
    print("OOS geoeffnet:", oos, "| Tresor geoeffnet:", tre)

    days, m5 = load_days()
    days = days[days.index < pd.Timestamp(TRESOR_END, tz=days.index.tz) + pd.Timedelta(days=1)]
    rows, trades = [], []
    for label, cfg in (("IS-only", winner), ("Live", LIVE)):
        t = run_sim(days, m5, cfg["stop"], cfg["cancel"], cfg["exit"])
        sub = t[mask(t, cfg)]
        r = pd.Series(sub["R"].to_numpy(), index=pd.DatetimeIndex(sub["window_end"]))
        d = pd.Series(sub["dir"].to_numpy(), index=r.index)
        parts = {"IS": lk.is_only(r), "OOS": lk.stage_slice(r, "oos"), "Tresor": lk.stage_slice(r, "tresor"),
                 "Gesamt": r}
        part_of = pd.Series("IS", index=r.index)
        part_of[lk.stage_slice(r, "oos").index] = "OOS"
        part_of[lk.stage_slice(r, "tresor").index] = "Tresor"
        trades.append(pd.DataFrame({"variant": label, "time": r.index, "dir": d.values, "r": r.values,
                                    "part": part_of.values, "why": sub["why"].to_numpy()}))
        for part, rr in parts.items():
            rows.append({"variant": label, "part": part, **metrics(rr)})
            for side, sv in (("long", 1), ("short", -1)):
                rs = rr[d.reindex(rr.index).to_numpy() == sv]
                rows.append({"variant": label, "part": f"{part} {side}", **metrics(rs)})
        m_is = metrics(lk.is_only(r))
        if label == "IS-only" and m_is.get("n", 0) > 2:
            dsr = deflated_sharpe(m_is["avg"] / m_is["std"], m_is["n"], sel["n_trials"],
                                  m_is["skew"], m_is["kurt"], sel["sr_var_trials"])
            rows.append({"variant": label, "part": "DSR", "n": m_is["n"], "avg": dsr})
    rep = pd.DataFrame(rows)
    rep.to_csv(RES / "is_reopt_report.csv", index=False)
    tr = pd.concat(trades)
    tr.to_csv(RES / "is_reopt_trades.csv", index=False)
    yrs = tr.assign(year=pd.DatetimeIndex(tr["time"]).year).pivot_table(index="year", columns="variant", values="r",
                                                                         aggfunc=["count", "sum"])
    yrs.to_csv(RES / "is_reopt_years.csv")
    pd.set_option("display.width", 250)
    print(rep[["variant", "part", "n", "per_year", "avg", "pf", "sum", "dd", "win", "yrs_pos", "yrs"]]
          .round(3).to_string(index=False))
    print("\nJahre (Summe R):")
    print(yrs.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    stage = sys.argv[sys.argv.index("--stage") + 1] if "--stage" in sys.argv else "grid"
    sys.exit(stage_grid() if stage == "grid" else stage_evaluate())
