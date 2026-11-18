"""Kontrolle (Nutzerauftrag 2026-11-18): live-Regel NASDAQ-ORB (0,6 ATR, Storno, Ausstieg 16:00)
mit Market-Einstieg, wenn der Ausbruch der ersten Minute vor der Platzierung kam.

Nur Ueberpruefung, keine Auswahl: die Varianten sind bereits im Lock nasdaq_orb_kerzen_sl_20261118
gezaehlt, dessen Tresor ist offen. Die live-Regel selbst wurde am 04.10. mit Blick auf 2026 gewaehlt,
Tresor und 05.10.-17.11. sind fuer sie also nicht unberuehrt.

  python scripts/research_orb_nasdaq_market_einstieg_check.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_orb_nasdaq_kerzen_sl_market import (IS_START, OUT, build_frame, days, fetch_m1, fetch_m15,  # noqa: E402
                                                  stats, trade_day)

PERIODS = [("IS 2016-22", "2016-07-28", "2022-12-31"), ("OOS 2023-05/26", "2023-01-01", "2026-05-17"),
           ("Tresor 05-11/26", "2026-05-18", "2026-11-17"), ("05.10.-17.11.26", "2026-10-05", "2026-11-17")]
ENTRIES = {"ideal (bisheriger Backtest)": "ideal", "live (1. Minute verpasst)": "live", "Market <= 0,05 ATR": "m0.05",
           "Market <= 0,1 ATR": "m0.1", "Market <= 0,2 ATR": "m0.2", "Market ohne Grenze": "m_inf"}


def main() -> int:
    m15, m1 = fetch_m15("NASDAQ", IS_START, "2026-11-18"), fetch_m1("NASDAQ", IS_START, "2026-11-18")
    fr = build_frame(m15, m1, range_bars=1)
    all_days = [(pd.Timestamp(s).tz_localize(None), d) for s, d in days(fr)]
    rows, yearly = [], {}
    for name, em in ENTRIES.items():
        recs = []
        for s, d in all_days:
            res, _ = trade_day(d, "atr", True, em, None)
            if res:
                res["session"] = s
                recs.append(res)
        df = pd.DataFrame(recs).set_index("session").sort_index()
        yearly[name] = df["r"].groupby(df.index.year).sum()
        for per, a, b in PERIODS:
            sub = df[(df.index >= a) & (df.index <= b)]
            rows.append({"einstieg": name, "periode": per, **stats(sub)})
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "market_einstieg_check.csv", index=False)
    pd.DataFrame(yearly).to_csv(OUT / "market_einstieg_check_jahre.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    cols = ["einstieg", "periode", "n", "avg", "t", "sum", "pf", "maxdd", "avg_pess", "avg_kosten_x2", "anteil_market"]
    print(tab[cols].round(3).to_string(index=False))
    print("\nSumme R je Jahr:\n" + pd.DataFrame(yearly).round(1).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
