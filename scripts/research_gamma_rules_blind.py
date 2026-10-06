"""Blinder Test zweier Gamma-Regeln auf 06/2012-07/2016 (nie zuvor genutzt).

Nutzerauftrag 2026-10-07 ("Ja, mache das so"). Die Regeln wurden aus den
Daten 2016-2026 abgeleitet (knowledge/projects/gamma-mechanismen-gex.md) und
VOR dem Laden der Daten 2012-2016 hier festgeschrieben, eingefroren und
committet. Die M1-Daten der Index-CFDs beginnen bei Dukascopy im Mai 2012;
keine unserer ORB-Studien hat Daten vor dem 28.07.2016 benutzt.
Nicht blind testbar (deshalb nicht enthalten): DIX-Regel -- 2012-2016 wurde
in research_gex_mechanisms.py (Spalte "2012-2016") schon angesehen.

GAMMA: SqueezeMetrics-SPX-GEX vom VORTAG als Perzentil der letzten 252
Handelstage, Quintile Q1 (wenig) .. Q5 (viel). Fuer NASDAQ ist SPX-GEX die
Naeherung.

REGEL R1 Volatilitaet: Median der Tagesrange (09:30-16:00, high-low / open)
  je Gamma-Quintil.
  BESTANDEN, wenn fuer BEIDE Indizes (a) Median(Q1) >= 1,5 x Median(Q5) und
  (b) Spearman(Quintil-Rang, Median) <= -0,9.

REGEL R2 Kein Ausbruch bei viel Gamma: ORB erster Ausbruch, beide
  Richtungen, Range 15 Min., Stop 1,0 x M15-ATR, Ausstieg 16:00, Kosten wie
  bisher (gemessene Spreads + Slippage).
  BESTANDEN, wenn fuer BEIDE Indizes Ø R(Q5) < Ø R(Q1-Q4).
  STARK BESTANDEN, wenn zusaetzlich Ø R(Q5) < 0 fuer beide.
  Ausgewiesen: Welch-t der Differenz, Trades je Gruppe.

ABLAUF: Lock gamma_rules_blind_20261007 (IS = Aufwaermfenster ohne Trades
2012-01-01..2012-05-31, OOS = 2012-06-01..2016-07-27 = der blinde Zeitraum);
freeze(Regeln) -> unseal("oos") -> erst DANN Daten laden -> einmal auswerten.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

import challenge_portfolio.paper_bot as pb  # noqa: E402
from ny_open_orb.data import fetch_m1, fetch_m15  # noqa: E402
from ny_open_orb.engine import build_frame  # noqa: E402
from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_lock import Lock  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402

STRATEGY = "gamma_rules_blind_20261007"
WARM_START, WARM_END, BLIND_END = "2012-01-01", "2012-05-31", "2016-07-27"
LOAD_START = "2012-05-01"   # Daten beginnen im Mai 2012; Mai nur fuer ATR-Aufwaermung
RES = ROOT / "ny_open_orb" / "results"
GEX = ROOT / "scripts" / "frozen_data" / "sqzme_dix_gex_20261006.csv"
RULES = {
    "R1": "Median-Tagesrange Q1 >= 1,5 x Q5 und Spearman(Rang, Median) <= -0,9, beide Indizes",
    "R2": "ORB 1. Ausbruch (beide Richtungen, 15 Min., Stop 1,0 ATR, Exit 16:00): Ø R(Q5) < Ø R(Q1-Q4), beide Indizes; stark: Ø R(Q5) < 0",
    "gamma": "SPX-GEX Vortag, Perzentil 252 Tage, Quintile",
    "abgeleitet_aus": "2016-2026 (knowledge/projects/gamma-mechanismen-gex.md)",
}


def gex_quintile() -> pd.Series:
    g = pd.read_csv(GEX, parse_dates=["date"]).set_index("date")["gex"].sort_index()
    p = g.rolling(252, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    return pd.cut(p.shift(1), [-0.01, .2, .4, .6, .8, 1.0], labels=["Q1", "Q2", "Q3", "Q4", "Q5"])


def main() -> int:
    lk = Lock(STRATEGY)
    lk.register_split(WARM_START, WARM_END, BLIND_END)
    h = lk.freeze(RULES)
    st = lk._load()
    if "oos" not in st["unsealed"]:
        print("blinder Zeitraum geoeffnet:", lk.unseal("oos", h), flush=True)
    else:
        print("bereits geoeffnet am", st["unsealed"]["oos"], flush=True)
    q = gex_quintile()
    out, summary = [], {}
    for inst in ("SP500", "NASDAQ"):
        m15 = pb._retry(lambda: fetch_m15(inst, LOAD_START, BLIND_END), attempts=3, delay_seconds=5, timeout_seconds=900)
        m1 = pb._retry(lambda: fetch_m1(inst, LOAD_START, BLIND_END), attempts=3, delay_seconds=5, timeout_seconds=1800)
        frame = build_frame(m15, m1, range_bars=1)
        frame = frame[frame.index >= pd.Timestamp("2012-06-01", tz=frame.index.tz)]
        # R1
        f = frame.assign(date=frame.index.tz_localize(None).normalize())
        hm = f.index.hour * 60 + f.index.minute
        rth = f[(hm >= 570) & (hm < 960)]
        day = rth.groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"))
        day["range_pct"] = (day["h"] - day["l"]) / day["o"] * 100
        day["q"] = q.reindex(day.index)
        day = day.dropna(subset=["q"])
        med = day.groupby("q", observed=False)["range_pct"].median()
        rank_corr = pd.Series(range(5)).corr(pd.Series(med.to_numpy()), method="spearman")
        r1 = bool(med["Q1"] >= 1.5 * med["Q5"] and rank_corr <= -0.9)
        # R2
        sessions = pd.DatetimeIndex(frame["session"].dropna().unique())
        prep = prepare(frame, find_entries_nth(frame, {s: [1, -1] for s in sessions}, "first"))
        res = sim(prep, inst, 1.0, None, None)
        t = pd.DataFrame({"r": res["r"].to_numpy()}, index=pd.DatetimeIndex(res["entry_time"]).tz_localize(None).normalize())
        t["q"] = q.reindex(t.index)
        t = t.dropna(subset=["q"])
        q5, rest = t[t.q == "Q5"].r, t[t.q != "Q5"].r
        welch = (q5.mean() - rest.mean()) / np.sqrt(q5.var(ddof=1) / len(q5) + rest.var(ddof=1) / len(rest))
        by_q = t.groupby("q", observed=False)["r"].agg(["count", "mean"])
        summary[inst] = {"R1_bestanden": r1, "Q1/Q5": med["Q1"] / med["Q5"], "spearman": rank_corr,
                         "R2_bestanden": bool(q5.mean() < rest.mean()), "R2_stark": bool(q5.mean() < 0),
                         "R_Q5": q5.mean(), "R_Q1-4": rest.mean(), "welch_t": welch, "n_Q5": len(q5), "n_Q1-4": len(rest),
                         "tage": len(day)}
        for qq in med.index:
            out.append({"inst": inst, "quintil": qq, "median_range_pct": med[qq],
                        "orb_n": by_q.loc[qq, "count"], "orb_avg_r": by_q.loc[qq, "mean"]})
        print(f"{inst} fertig", flush=True)
    det = pd.DataFrame(out)
    det.to_csv(RES / "gamma_rules_blind_detail.csv", index=False)
    summ = pd.DataFrame(summary).T
    summ.to_csv(RES / "gamma_rules_blind_summary.csv")
    pd.set_option("display.width", 220)
    print(det.round(3).to_string(index=False))
    print(summ.to_string())
    r1_all = all(summary[i]["R1_bestanden"] for i in summary)
    r2_all = all(summary[i]["R2_bestanden"] for i in summary)
    r2_strong = r2_all and all(summary[i]["R2_stark"] for i in summary)
    print(f"\nURTEIL R1: {'BESTANDEN' if r1_all else 'NICHT bestanden'} | R2: "
          f"{'STARK BESTANDEN' if r2_strong else ('BESTANDEN' if r2_all else 'NICHT bestanden')}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
