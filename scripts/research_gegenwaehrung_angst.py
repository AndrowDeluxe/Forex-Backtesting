"""Gegenwährung bei Dollar-Stärke: Hafen oder Rohstoffwährung? Hängt es an der Angst?

These (Makro-Agent-Leitlinie, Einschränkung vom 15.11.2026):
  Steigt der Dollar wegen der Zinsen UND es herrscht Angst -> Rohstoffwährungen (AUD/NZD/CAD)
  verlieren am meisten. Steigen die Zinsen OHNE Angst -> die zinslosen Häfen (CHF/JPY) verlieren am
  meisten.

Vorab festgelegt (vor dem ersten Lauf):
  - Wochenschlüsse Freitag (yfinance FX + VIX + S&P, FRED DGS2).
  - Spread S = mean(log-Rendite USD gegen CHF, JPY) - mean(USD gegen AUD, NZD, CAD), in %.
    S > 0: Dollar gewinnt mehr gegen die Häfen.
  - Zinswoche: DGS2-Wochenänderung >= +10 bp.
  - Angst Haupt: VIX-Wochenänderung > 0. Varianten (gezählt): VIX-Schluss > 20; S&P-Woche < 0.
  - Test A (gleichzeitig, erklärt die Woche): S in Zinswochen, ohne Angst vs. mit Angst.
  - Test B (handelbar, Sonntag-Entscheid): Regime der Vorwoche -> S der Folgewoche.
  - Split: IS 2004-2017, OOS 2018 - 15.05.2026, Tresor letzte 6 Monate (bleibt zu).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_lock import Lock  # noqa: E402
from fusion_lab.g8.data import fetch_fred  # noqa: E402

lock = Lock("gegenwaehrung_angst")
lock.register_split("2004-01-01", "2017-12-31", "2026-05-15", "2026-11-13")

TICK = {"AUD": "AUDUSD=X", "NZD": "NZDUSD=X", "CAD": "USDCAD=X", "CHF": "USDCHF=X", "JPY": "USDJPY=X",
        "VIX": "^VIX", "SPX": "^GSPC"}
raw = {}
for k, t in TICK.items():
    d = yf.download(t, start="2003-06-01", end="2026-11-15", progress=False, auto_adjust=False)
    raw[k] = d["Close"].squeeze()
px = pd.DataFrame(raw)
px["US2Y"] = fetch_fred("DGS2", False)
wk = px.resample("W-FRI").last().dropna()

ret = np.log(wk).diff() * 100
usd_vs = pd.DataFrame({
    "AUD": -ret["AUD"], "NZD": -ret["NZD"], "CAD": ret["CAD"], "CHF": ret["CHF"], "JPY": ret["JPY"]})
df = pd.DataFrame({
    "S": usd_vs[["CHF", "JPY"]].mean(axis=1) - usd_vs[["AUD", "NZD", "CAD"]].mean(axis=1),
    "dollar": usd_vs.mean(axis=1),
    "d2y": wk["US2Y"].diff() * 100,
    "vix_chg": wk["VIX"].diff(),
    "vix": wk["VIX"],
    "spx": ret["SPX"],
}).dropna()
df["zins"] = df["d2y"] >= 10
FEAR = {"vix_steigt (Haupt)": df["vix_chg"] > 0, "vix_ueber_20": df["vix"] > 20, "spx_faellt": df["spx"] < 0}
lock.log_trials(len(FEAR) * 2, "3 Angst-Definitionen x Test A/B, Schwelle 10 bp fest")


def compare(sub, name):
    a = sub.loc[sub.ohne, "y"]
    b = sub.loc[~sub.ohne, "y"]
    t, p = stats.ttest_ind(a, b, equal_var=False) if len(a) > 2 and len(b) > 2 else (np.nan, np.nan)
    hit = (a > 0).mean() if len(a) else np.nan
    print(f"  {name:6s} ohne Angst n={len(a):3d} S={a.mean():+.2f}% (S>0 {hit:.0%}) | mit Angst n={len(b):3d} "
          f"S={b.mean():+.2f}% | Diff {a.mean() - b.mean():+.2f} t={t:.2f} p={p:.3f}")


for fname, fear in FEAR.items():
    print(f"\n=== Angst = {fname} ===")
    # Test A: gleichzeitig
    A = pd.DataFrame({"y": df["S"], "ohne": ~fear})[df["zins"]]
    # Test B: Vorwoche -> Folgewoche
    B = pd.DataFrame({"y": df["S"].shift(-1), "ohne": ~fear})[df["zins"]].dropna()
    for tname, T in [("A gleichzeitig", A), ("B Folgewoche", B)]:
        print(f" {tname}")
        compare(lock.is_only(T), "IS")
        compare(lock.oos_only(T), "OOS")

print("\nKontrolle: alle Wochen (ohne Zinsfilter), Angst Haupt, Test A")
C = pd.DataFrame({"y": df["S"], "ohne": ~FEAR["vix_steigt (Haupt)"]})
compare(lock.is_only(C), "IS")
compare(lock.oos_only(C), "OOS")
print("\nKW46/2026:", df.loc["2026-11-13", ["S", "d2y", "vix_chg", "spx"]].round(2).to_dict())
