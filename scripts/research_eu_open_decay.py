"""EU-Open-Fenster: Zerfallsanalyse + konditionale Version.

Folgeschritt zu scripts/research_eu_open_window.py. Dort zeigte sich, dass
das Fenster ueber 2018-2026 zwar nominal positiv ist (SP500 +3,5 %,
NASDAQ +5,2 % p.a.), die Jahresreihe aber fast vollstaendig von EINEM Jahr
getragen wird: 2020 (+24,3 / +24,4 / +28,4 %). Unser 2020-Wert trifft die
vom Paper selbst berichteten 24,5 % fuer dessen 2020-Out-of-Sample fast
exakt -- ein starkes Indiz, dass die Messung stimmt und der Befund danach
echt ist, kein Pipeline-Fehler.

Drei Fragen hier:
  1. Was bleibt OHNE 2020, und was bleibt ab 2021?
  2. Ist das 2020er Ergebnis auf das COVID-Crashfenster konzentriert (wie im
     Paper: 14,3 der 24,5 Punkte zwischen 21.02. und 23.03.2020)?
  3. Rettet die KONDITIONALE Version etwas? Das Paper handelt nur die ~40 %
     Tage mit hoher erwarteter Rendite, Praediktoren Delta-VIX und
     Overnight-Realized-Vol. Delta-VIX geht bei uns erst ab 2022-10-04
     (Dukascopy-Historie), Overnight-Vol dagegen ueber die volle Historie
     aus den eigenen Index-Bars -- hier deshalb nur Overnight-Vol.

REIN LESEND.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.research_eu_open_window import (  # noqa: E402
    BERLIN, INSTRUMENTS, TRADING_DAYS, load_berlin, newey_west_t, price_at, max_drawdown,
)

START, END = "2018-07-01", "2026-09-18"
COVID = (pd.Timestamp("2020-02-21", tz=BERLIN), pd.Timestamp("2020-03-23", tz=BERLIN))


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {"n": int(len(r)), "error": "zu duenn"}
    ann = float(r.mean() * TRADING_DAYS * 100)
    sd = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100)
    return {"n": int(len(r)), "ann_pct": round(ann, 2), "t": round(newey_west_t(r.values), 2),
            "sharpe": round(ann / sd, 2) if sd else None,
            "bps_per_trade": round(float(r.mean() * 10_000), 2),
            "max_dd_pct": round(max_drawdown(r), 2)}


def main() -> None:
    out: dict = {"generated": pd.Timestamp.now(tz=BERLIN).isoformat(),
                 "sample": {"start": START, "end": END}, "instruments": {}}

    print("=" * 78)
    print("FRAGE 1+2: Was bleibt ohne 2020 / ab 2021, und wie konzentriert ist 2020?")
    print("=" * 78)
    print(f"\n{'Inst':<8} {'Zeitraum':<22} {'n':>5} {'p.a.%':>8} {'t':>6} {'Sharpe':>7} {'bps/Trade':>10}")
    print("-" * 78)

    series: dict[str, pd.Series] = {}
    for inst in INSTRUMENTS:
        df = load_berlin(inst, START, END)
        a, b = price_at(df, "05:30"), price_at(df, "09:30")
        common = a.index.intersection(b.index)
        r = np.log(b.loc[common] / a.loc[common]).dropna()
        r = r[np.isfinite(r) & (r.abs() <= 0.20)]
        series[inst] = r

        inst_out = {}
        for label, sub in (
            ("voll 2018-2026", r),
            ("OHNE 2020", r[r.index.year != 2020]),
            ("ab 2021", r[r.index.year >= 2021]),
            ("ab 2023", r[r.index.year >= 2023]),
            ("2020 COVID-Crash", r[(r.index >= COVID[0]) & (r.index <= COVID[1])]),
            ("2020 ohne Crash", r[(r.index.year == 2020) & ~((r.index >= COVID[0]) & (r.index <= COVID[1]))]),
        ):
            s = stats(sub)
            inst_out[label] = s
            if "error" in s:
                print(f"{inst:<8} {label:<22} {s['n']:>5}   (zu duenn)")
            else:
                print(f"{inst:<8} {label:<22} {s['n']:>5} {s['ann_pct']:>8.2f} {s['t']:>6.2f} "
                      f"{s['sharpe']:>7.2f} {s['bps_per_trade']:>10.2f}")
        print()
        out["instruments"][inst] = {"decay": inst_out}

    # --- Frage 3: konditionale Version ueber Overnight-Realized-Vol ---
    print("=" * 78)
    print("FRAGE 3: Konditionale Version -- nur die Tage mit hoher Overnight-Vol")
    print("=" * 78)
    print("Praediktor: realisierte Vol der M15-Bars 22:00(Vortag)-05:30 Berlin,")
    print("also VOR dem Fenster -- strikt ex ante, kein Look-ahead.")
    print(f"\n{'Inst':<8} {'Auswahl':<26} {'n':>5} {'p.a.%':>8} {'t':>6} {'bps/Trade':>10}")
    print("-" * 78)

    for inst in INSTRUMENTS:
        df = load_berlin(inst, START, END)
        r = series[inst]

        # Overnight-Realized-Vol: Summe quadrierter M15-Log-Returns 22:00->05:30,
        # dem FOLGENDEN Handelstag zugeordnet.
        bars = df.between_time("22:00", "05:30")
        lr = np.log(bars["Close"] / bars["Close"].shift(1))
        # Bars vor 12:00 gehoeren zum laufenden Kalendertag, Bars ab 12:00 zum naechsten
        sess = bars.index.normalize() + pd.to_timedelta((bars.index.hour >= 12).astype(int), unit="D")
        rv = (lr ** 2).groupby(sess).sum().pipe(np.sqrt)
        rv = rv[rv > 0]

        common = r.index.intersection(rv.index)
        r_c, rv_c = r.loc[common], rv.loc[common]
        # Schwelle aus der EXPANDIERENDEN Vergangenheit, nicht aus dem
        # Gesamtsample -- sonst waere die Auswahl look-ahead-behaftet.
        thresh = rv_c.shift(1).expanding(min_periods=120).quantile(0.60)
        valid = thresh.notna()
        hi = valid & (rv_c > thresh)
        lo = valid & (rv_c <= thresh)

        inst_res = {}
        for label, mask in (("alle Tage (ab min_periods)", valid),
                            ("hohe Overnight-Vol (Top 40 %)", hi),
                            ("niedrige Overnight-Vol", lo)):
            s = stats(r_c[mask])
            inst_res[label] = s
            if "error" in s:
                print(f"{inst:<8} {label:<26} {s['n']:>5}   (zu duenn)")
            else:
                print(f"{inst:<8} {label:<26} {s['n']:>5} {s['ann_pct']:>8.2f} {s['t']:>6.2f} "
                      f"{s['bps_per_trade']:>10.2f}")
        # dasselbe nochmal OHNE 2020, weil 2020 oben schon alles dominiert
        m = hi & (r_c.index.year != 2020)
        s = stats(r_c[m])
        inst_res["hohe Overnight-Vol OHNE 2020"] = s
        if "error" not in s:
            print(f"{inst:<8} {'  davon ohne 2020':<26} {s['n']:>5} {s['ann_pct']:>8.2f} "
                  f"{s['t']:>6.2f} {s['bps_per_trade']:>10.2f}")
        print()
        out["instruments"][inst]["conditional"] = inst_res

    p = REPO / "knowledge" / "_data" / "eu_open_decay.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Geschrieben: {p}")


if __name__ == "__main__":
    main()
