"""Nachrechnung der "Zeit-Heatmap FX" aus dem SMH-Elite-Call "Session Pips und
Wahrscheinlichkeiten" (2026-10-21) auf unseren Dukascopy-Daten (EUR/USD M5,
Berlin-Zeit, 2018-12 bis 2026-10). Rein beschreibend, keine Strategie und
kein Parameter -- beruehrt die Overfitting-Sperre nicht.
Abgleich: knowledge/resources/smh-session-pips-call.md.

Geprueft werden drei Aussagen des Mentors:
  1. Median-Stundenrange je Wochentag x Stunde, Muster "zu 97-99 % jedes Jahr
     gleich".
  2. "Ruck zu festen Terminen": Range der 5 Minuten NACH dem Termin gegen die
     5 Minuten DAVOR (Mentor: 07:00 1,4x, 08:00 1,9x, 09:00 1,5x, 11:00 1,1x,
     14:30 1,9x, 16:00 1,3x).
  3. "02-03 Uhr druckt besonders oft das Tageshoch/-tief" (Asia, LCH 02:30).

Aufruf:
    python scripts/research_session_pips_heatmap.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from cls_practical.data import fetch_eurusd_entry_tf_berlin
from research_cls_practical_smh_call_variants import load

pd.set_option("display.width", 220)
PIP = 0.0001
TERMINE = ["06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "14:30", "15:30", "16:00", "17:00"]


def main() -> None:
    e = load(fetch_eurusd_entry_tf_berlin, "M5")
    e = e[e.index.dayofweek < 5]
    rng = (e["high"] - e["low"]) / PIP
    print(f"EURUSD M5 {e.index[0]} .. {e.index[-1]}  ({len(e):,} Bars)\n")

    # ---- 1. Stundenrange
    h = e.groupby([e.index.date, e.index.hour]).agg(high=("high", "max"), low=("low", "min"))
    h["pips"] = (h["high"] - h["low"]) / PIP
    h.index.names = ["date", "hour"]
    h = h.reset_index()
    h["wd"] = pd.to_datetime(h["date"]).dt.dayofweek
    h["year"] = pd.to_datetime(h["date"]).dt.year
    heat = h.pivot_table(index="wd", columns="hour", values="pips", aggfunc="median")
    heat.index = ["Mo", "Di", "Mi", "Do", "Fr"]
    print("1) Median-Stundenrange in Pips (Berlin-Zeit)")
    print(heat.round(1).to_string())
    prof = h.pivot_table(index="year", columns="hour", values="pips", aggfunc="median")
    ref = prof.median()
    corr = prof.apply(lambda r: np.corrcoef(r, ref)[0, 1], axis=1)
    print("\n   Korrelation des Jahresprofils (24 Stunden) mit dem Gesamtprofil:")
    print("   " + "  ".join(f"{y}: {c:.3f}" for y, c in corr.items()))
    lvl = prof.median(axis=1)
    print("   Median-Stundenrange je Jahr (Niveau): " + "  ".join(f"{y}: {v:.1f}" for y, v in lvl.items()))

    # ---- 2. Ruck: Bar ab Termin gegen Bar davor (beide 5 Min.)
    print("\n2) Ruck zu festen Terminen: Median-Range 5 Min. nach / 5 Min. vor dem Termin")
    hm = e.index.strftime("%H:%M")
    rows = []
    for t in TERMINE:
        t0 = pd.Timestamp(f"2000-01-01 {t}")
        before = (t0 - pd.Timedelta(minutes=5)).strftime("%H:%M")
        a = rng[hm == t]
        b = rng[hm == before]
        a.index, b.index = a.index.date, b.index.date
        both = pd.concat([a.rename("nach"), b.rename("vor")], axis=1).dropna()
        rows.append({"Termin": t, "Tage": len(both),
                     "Median vor": both["vor"].median(), "Median nach": both["nach"].median(),
                     "Faktor (Mediane)": both["nach"].median() / both["vor"].median(),
                     "Faktor (Mittel)": both["nach"].mean() / both["vor"].mean(),
                     "Anteil nach>vor %": 100 * (both["nach"] > both["vor"]).mean()})
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    # ---- 3. Uhrzeit von Tageshoch / -tief (Berlin-Kalendertag)
    print("\n3) Stunde des Tageshochs bzw. -tiefs (Anteil der Tage in %, Berlin-Kalendertag)")
    d = e.copy()
    d["date"] = d.index.date
    hi_t = d.groupby("date")["high"].idxmax()
    lo_t = d.groupby("date")["low"].idxmin()
    dist = pd.DataFrame({
        "Hoch %": 100 * pd.Series([t.hour for t in hi_t]).value_counts(normalize=True).sort_index(),
        "Tief %": 100 * pd.Series([t.hour for t in lo_t]).value_counts(normalize=True).sort_index(),
    }).fillna(0.0)
    dist["Hoch oder Tief %"] = dist["Hoch %"] + dist["Tief %"]
    print(dist.round(1).T.to_string())
    print(f"\n   02-03 Uhr: Hoch {dist.loc[2, 'Hoch %']:.1f} %, Tief {dist.loc[2, 'Tief %']:.1f} % "
          f"(Gleichverteilung waere {100/24:.1f} %)")


if __name__ == "__main__":
    main()
