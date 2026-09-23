"""EU-Open-Fenster: Gegenchecks vor dem Abbruch.

research_eu_open_window.py + _decay.py zeigen: das Fenster traegt ab 2021
nichts mehr. Bevor das als "Edge zerfallen" protokolliert wird, zwei
Einwaende, die den Befund kippen koennten:

  A) VERSCHOBEN STATT TOT? Vielleicht liegt die Rendite inzwischen in einem
     ANDEREN Vier-Stunden-Fenster. Deshalb: alle 4h-Fenster im 30-Minuten-
     Raster ueber den ganzen Tag scannen (Paper Fig. 3 macht dasselbe fuer
     sein Sample). Wenn irgendwo eine Konzentration sitzt, findet dieser
     Scan sie.
  B) FALSCH VERANKERT? Ich habe in Berliner Zeit gerechnet (Paper-DST-Test:
     das Muster steht in europaeischer Zeit). Das Paper DEFINIERT das
     Fenster aber in ET. In den Wochen, in denen US- und EU-Umstellung
     auseinanderlaufen, sind das verschiedene Fenster. Also beide rechnen.

Wichtige Lesehilfe zum Scan: es werden ~45 ueberlappende Fenster getestet.
Ein t von 2 irgendwo darunter ist ERWARTBAR, nicht bemerkenswert -- genau
dagegen setzt das Paper seinen White-Reality-Check (99-%-Schwelle fuer
4h-Fenster: t=3,7). Diese Schwelle ist hier als Messlatte eingezeichnet.

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
    BERLIN, INSTRUMENTS, TRADING_DAYS, load_berlin, newey_west_t, price_at,
)

START, END = "2018-07-01", "2026-09-18"
NY = "America/New_York"
WHITE_4H_THRESHOLD = 3.7  # Paper: 99-%-Perzentil der Max-t-Verteilung, 4h-Fenster


def window_return(df: pd.DataFrame, t0: str, t1: str,
                  max_hold_h: float = 12.0) -> pd.Series:
    """Rendite von der Bar um t0 zur NAECHSTEN Bar um t1 danach.

    Bewusst ueber Bar-Zeitstempel gepaart und nicht ueber Kalendertage:
    ein Fenster wie 21:00-01:00 endet am FOLGETAG. Die Kalendertag-Variante
    (price_at + Index-Schnitt) paart dort 21:00 mit 01:00 DESSELBEN Tages,
    also minus 20 Stunden statt plus 4 -- ein stiller Vorzeichenfehler, der
    im ersten Lauf dieses Skripts ET-verankerte Fenster mit -13 bis -19 %
    p.a. ausgewiesen hat. max_hold_h verwirft Paare ueber Wochenend-/
    Feiertagsluecken hinweg.
    """
    a_sel = df.between_time(t0, t0)
    b_sel = df.between_time(t1, t1)
    if a_sel.empty or b_sel.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz=df.index.tz))

    a_idx, b_idx = a_sel.index, b_sel.index
    pos = b_idx.searchsorted(a_idx, side="right")  # erste b-Bar STRIKT nach jeder a-Bar
    ok = pos < len(b_idx)
    a_idx, pos = a_idx[ok], pos[ok]
    if len(a_idx) == 0:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz=df.index.tz))

    a_px = a_sel["Open"].to_numpy()[ok]
    b_px = b_sel["Open"].to_numpy()[pos]
    keep = (b_idx[pos] - a_idx) <= pd.Timedelta(hours=max_hold_h)
    r = pd.Series(np.log(b_px[keep] / a_px[keep]), index=a_idx[keep]).dropna()
    return r[np.isfinite(r) & (r.abs() <= 0.20)]


def scan(df: pd.DataFrame, label: str, years: tuple[int, ...] | None = None) -> list[dict]:
    rows = []
    for start_min in range(0, 24 * 60, 30):
        t0 = f"{start_min // 60:02d}:{start_min % 60:02d}"
        end_min = (start_min + 4 * 60) % (24 * 60)
        t1 = f"{end_min // 60:02d}:{end_min % 60:02d}"
        r = window_return(df, t0, t1)
        if len(r) == 0:
            continue
        if years is not None:
            r = r[r.index.year.isin(years)]
        if len(r) < 200:
            continue
        ann = float(r.mean() * TRADING_DAYS * 100)
        rows.append({"window": f"{t0}-{t1}", "n": int(len(r)),
                     "ann_pct": round(ann, 2), "t": round(newey_west_t(r.values), 2)})
    return rows


def main() -> None:
    out: dict = {"generated": pd.Timestamp.now(tz=BERLIN).isoformat(),
                 "white_4h_threshold": WHITE_4H_THRESHOLD, "instruments": {}}

    print("=" * 78)
    print("GEGENCHECK B: Berlin- vs. ET-Verankerung des EU-Open-Fensters")
    print("=" * 78)
    print(f"\n{'Inst':<8} {'Verankerung':<28} {'n':>5} {'p.a.%':>8} {'t':>6}   {'ohne 2020':>12}")
    print("-" * 78)
    for inst in INSTRUMENTS:
        df_b = load_berlin(inst, START, END)
        df_n = df_b.copy()
        df_n.index = df_b.index.tz_convert(NY)
        for label, df, t0, t1 in (("Berlin 05:30-09:30", df_b, "05:30", "09:30"),
                                  ("ET 23:30-03:30", df_n, "23:30", "03:30")):
            r = window_return(df, t0, t1)
            ex = r[r.index.year != 2020]
            ann = float(r.mean() * TRADING_DAYS * 100)
            ann_ex = float(ex.mean() * TRADING_DAYS * 100)
            print(f"{inst:<8} {label:<28} {len(r):>5} {ann:>8.2f} "
                  f"{newey_west_t(r.values):>6.2f}   {ann_ex:>7.2f}% (t={newey_west_t(ex.values):.2f})")
        print()

    print("=" * 78)
    print("GEGENCHECK A: Hat sich die Rendite in ein ANDERES 4h-Fenster verschoben?")
    print("=" * 78)
    print(f"Alle 4h-Fenster, 30-Min-Raster, Berliner Zeit. Messlatte fuer")
    print(f"Signifikanz bei ~45 ueberlappenden Tests: |t| >= {WHITE_4H_THRESHOLD} (Paper, White 2000).")

    for inst in INSTRUMENTS:
        df = load_berlin(inst, START, END)
        for years, ylabel in ((None, "2018-2026"), (tuple(range(2021, 2027)), "ab 2021")):
            rows = scan(df, inst, years)
            rows_sorted = sorted(rows, key=lambda d: -d["t"])
            top = rows_sorted[:4]
            bot = rows_sorted[-2:]
            hits = [r for r in rows if abs(r["t"]) >= WHITE_4H_THRESHOLD]
            print(f"\n  {inst} / {ylabel}  ({len(rows)} Fenster getestet)")
            print(f"    beste:  " + " | ".join(
                f"{r['window']} {r['ann_pct']:+.1f}% t={r['t']:+.2f}" for r in top))
            print(f"    worst:  " + " | ".join(
                f"{r['window']} {r['ann_pct']:+.1f}% t={r['t']:+.2f}" for r in bot))
            eu = next((r for r in rows if r["window"] == "05:30-09:30"), None)
            if eu:
                rank = 1 + sum(1 for r in rows if r["t"] > eu["t"])
                print(f"    EU-Open 05:30-09:30: {eu['ann_pct']:+.2f}% t={eu['t']:+.2f} "
                      f"-> Rang {rank}/{len(rows)}")
            print(f"    Fenster ueber der White-Schwelle |t|>={WHITE_4H_THRESHOLD}: "
                  f"{len(hits)}" + (f"  {[h['window'] for h in hits]}" if hits else "  (keins)"))
            out["instruments"].setdefault(inst, {})[ylabel] = rows

    p = REPO / "knowledge" / "_data" / "eu_open_windowscan.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nGeschrieben: {p}")


if __name__ == "__main__":
    main()
