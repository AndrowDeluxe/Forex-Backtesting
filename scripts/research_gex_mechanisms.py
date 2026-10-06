"""Welche Mechanismen lassen sich aus echtem Dealer-Gamma (SqueezeMetrics) ableiten?

Nutzerauftrag 2026-10-07. HYPOTHESEN-SUCHE auf bereits gesehenen Daten
(Phase 1-3) -- keine Auswahl, kein Edge-Beleg. Gesucht werden Zusammenhaenge
mit Mechanismus, die ueber ALLE Perioden das gleiche Vorzeichen haben.
Eine daraus abgeleitete Regel muss danach vorab registriert und nur auf
Forward-Daten bestaetigt werden (Overfitting-Sperre).

Gamma-Mass: SPX-GEX vom Vortag als Perzentil der letzten 252 Tage
(relativ, weil das Dollar-Gamma mit dem Indexniveau waechst), Quintile Q1-Q5.
Perioden: 2016-2022 | 2023-2024 | 2025-09/2026.

M1  Volatilitaet: Tagesrange und |Open->Close| je Gamma-Quintil
M2  Trend/Umkehr intraday: Corr(erste 30 Min., Rest des Tages) je Quintil
M3  ORB: erster Ausbruch vs. Fade (Stop 1,0 ATR, Exit 16:00, beide Richtungen)
    je Quintil -- und Ribbon neutral/mit Trend x Gamma
M4  DIX: SPX-Rendite der naechsten 20 Handelstage je DIX-Quintil (252-Tage-Perzentil)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from ny_open_orb.entries_nth import find_entries_nth  # noqa: E402
from research_orb_exit_grid_m1 import prepare, sim  # noqa: E402
from research_orb_is_only_reopt import load  # noqa: E402

RES = ROOT / "ny_open_orb" / "results"
GEX = ROOT / "scripts" / "frozen_data" / "sqzme_dix_gex_20261006.csv"
PER = [("2016-2022", "2016-07-28", "2023-01-01"), ("2023-2024", "2023-01-01", "2025-01-01"),
       ("2025-09/2026", "2025-01-01", "2026-10-01")]


def pctl(s: pd.Series, n=252) -> pd.Series:
    return s.rolling(n, min_periods=120).apply(lambda w: (w[:-1] < w[-1]).mean() if len(w) > 1 else np.nan, raw=True)


def period(ix):
    return pd.cut(pd.DatetimeIndex(ix).year + 0 * 0, bins=[2015, 2022, 2024, 2027], labels=[p[0] for p in PER])


def main() -> int:
    g = pd.read_csv(GEX, parse_dates=["date"]).set_index("date").sort_index()
    g["gex_p"] = pctl(g["gex"])
    g["dix_p"] = pctl(g["dix"])
    g["gex_q_prev"] = pd.cut(g["gex_p"].shift(1), [-0.01, .2, .4, .6, .8, 1.0], labels=["Q1 tief", "Q2", "Q3", "Q4", "Q5 hoch"])
    out = {}

    # M4 DIX -> 20-Tage-Rendite (SPX-Kurs aus der Datei)
    g["fwd20"] = g["price"].shift(-20) / g["price"] - 1
    g["dix_q"] = pd.cut(g["dix_p"], [-0.01, .2, .4, .6, .8, 1.0], labels=["Q1 tief", "Q2", "Q3", "Q4", "Q5 hoch"])
    d = g[g.index >= "2012-01-01"].dropna(subset=["fwd20", "dix_q"])
    d["per"] = np.select([d.index < "2016-07-28", d.index < "2023-01-01", d.index < "2025-01-01"],
                         ["2012-2016", "2016-2022", "2023-2024"], "2025-09/2026")
    out["M4 DIX -> 20T-Rendite %"] = (d.pivot_table(index="dix_q", columns="per", values="fwd20", aggfunc="mean") * 100).round(2)

    for inst in ("SP500", "NASDAQ"):
        frames, sessions, bias = load(inst, "2026-09-30")
        f = frames[1]
        f = f.assign(date=f.index.tz_localize(None).normalize())
        hm = f.index.hour * 60 + f.index.minute
        rth = f[(hm >= 570) & (hm < 960)]
        day = rth.groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
        p30 = rth[(rth.index.hour * 60 + rth.index.minute) < 600].groupby("date")["close"].last()
        day["r30"] = p30 / day["o"] - 1
        day["rest"] = day["c"] / p30 - 1
        day["range_pct"] = (day["h"] - day["l"]) / day["o"] * 100
        day["absoc_pct"] = (day["c"] / day["o"] - 1).abs() * 100
        day = day.join(g[["gex_q_prev"]], how="left")
        day["per"] = np.select([day.index < "2023-01-01", day.index < "2025-01-01"], ["2016-2022", "2023-2024"], "2025-09/2026")
        day = day.dropna(subset=["gex_q_prev"])
        out[f"M1 {inst} Tagesrange %"] = day.pivot_table(index="gex_q_prev", columns="per", values="range_pct", aggfunc="median", observed=False).round(2)
        out[f"M2 {inst} Corr(erste 30 Min, Rest)"] = day.groupby(["gex_q_prev", "per"], observed=False).apply(
            lambda x: x["r30"].corr(x["rest"]) if len(x) > 20 else np.nan).unstack().round(3)

        allowed = {s: [1, -1] for s in sessions}
        bias_d = {pd.Timestamp(k).tz_localize(None) if pd.Timestamp(k).tz else pd.Timestamp(k): v for k, v in bias.items()}
        for mode in ("first", "fade"):
            prep = prepare(f, find_entries_nth(f, allowed, mode))
            res = sim(prep, inst, 1.0, None, None)
            t = pd.DataFrame({"r": res["r"].to_numpy()}, index=pd.DatetimeIndex(res["entry_time"]).tz_localize(None).normalize())
            t["d"] = [p["d"] for p in prep if p["t"] in set(res["entry_time"])][:len(t)]
            t = t.join(g[["gex_q_prev"]], how="left").dropna(subset=["gex_q_prev"])
            t["per"] = np.select([t.index < "2023-01-01", t.index < "2025-01-01"], ["2016-2022", "2023-2024"], "2025-09/2026")
            out[f"M3 {inst} ORB {mode} Ø R"] = t.pivot_table(index="gex_q_prev", columns="per", values="r", aggfunc="mean", observed=False).round(3)
            out[f"M3 {inst} ORB {mode} n"] = t.pivot_table(index="gex_q_prev", columns="per", values="r", aggfunc="count", observed=False)
            if mode == "first":
                b = pd.Series({k: bias_d.get(k, np.nan) for k in t.index})
                t["ribbon"] = np.where(b.values == 0, "neutral", np.where(b.values * t["d"].values > 0, "mit Trend", "gegen"))
                t["gex_hl"] = np.where(t["gex_q_prev"].isin(["Q1 tief", "Q2"]), "Gamma tief (Q1-2)", np.where(
                    t["gex_q_prev"].isin(["Q4", "Q5 hoch"]), "Gamma hoch (Q4-5)", "Q3"))
                tt = t[t["ribbon"].isin(["neutral", "mit Trend"]) & (t["gex_hl"] != "Q3")]
                out[f"M3b {inst} Ribbon x Gamma Ø R"] = tt.pivot_table(index=["ribbon", "gex_hl"], columns="per", values="r", aggfunc="mean").round(3)
        print(f"{inst} fertig", flush=True)

    pd.set_option("display.width", 220)
    with open(RES / "gex_mechanisms.txt", "w", encoding="utf-8") as fh:
        for k, v in out.items():
            txt = f"\n### {k}\n{v.to_string()}\n"
            print(txt); fh.write(txt)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
