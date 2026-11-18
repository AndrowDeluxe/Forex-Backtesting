"""Tresor-Lauf (einmalig) fuer den eingefrorenen Kandidaten aus
research_orb_nasdaq_kerzen_sl_market.py (Nutzerfreigabe 2026-11-18):
SL = Hoch/Tief der 15:30-Kerze, Market-Einstieg ohne Grenze, Storno an, Ziel 3R.
Tresor 18.05.-17.11.2026. Zum Vergleich (nicht eingefroren, nur Kontext) die live-Regel.

  python scripts/research_orb_nasdaq_kerzen_sl_tresor.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from research_orb_nasdaq_kerzen_sl_market import (IS_START, OUT, STRATEGY, TRESOR_END, build_frame, days,  # noqa: E402
                                                  fetch_m1, fetch_m15, stats, trade_day, Lock)

FROZEN = {"instrument": "NASDAQ", "sl": "kerze", "storno": True, "einstieg": "m_inf", "ziel_r": 3.0,
          "range": "M15 09:30-09:45 NY", "exit": "16:00 NY", "ohne": "Mittwoch"}
VARIANTS = {"Kandidat (eingefroren)": ("kerze", True, "m_inf", 3.0),
            "Kontext: Kandidat mit Ausstieg 16:00": ("kerze", True, "m_inf", None),
            "Kontext: live-Regel, Backtest ideal": ("atr", True, "ideal", None),
            "Kontext: live-Regel, 1. Minute verpasst": ("atr", True, "live", None)}


def main() -> int:
    lk = Lock(STRATEGY)
    h = lk.freeze(FROZEN)
    state = lk._load()
    if "tresor" in state["unsealed"]:
        # Erster Lauf 18.11. brach nach unseal() vor jeder Ausgabe ab (leere Kontext-Variante);
        # gleiche eingefrorene Konfiguration, keine neue Sicht -> Daten der geoeffneten Stufe nutzen.
        sp = state["split"]
        start = (pd.Timestamp(sp["oos_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        end = sp["tresor_end"]
    else:
        start, end = lk.unseal("tresor", h)
    print(f"Tresor geoeffnet: {start} bis {end} (Hash {h})")
    m15 = fetch_m15("NASDAQ", "2026-01-01", "2026-11-18")
    m1 = fetch_m1("NASDAQ", "2026-01-01", "2026-11-18")
    fr = build_frame(m15, m1, range_bars=1)
    tdays = [(s, d) for s, d in days(fr)
             if pd.Timestamp(start) <= pd.Timestamp(s).tz_localize(None) <= pd.Timestamp(end)]
    print(f"{len(tdays)} Handelstage im Tresor (ohne Mittwoch)")
    rows, per_trade = [], {}
    for name, (sl, st, em, tg) in VARIANTS.items():
        recs = []
        for s, d in tdays:
            res, status = trade_day(d, sl, st, em, tg)
            if res:
                res["session"] = pd.Timestamp(s).tz_localize(None)
                recs.append(res)
        df = (pd.DataFrame(recs).set_index("session").sort_index() if recs
              else pd.DataFrame(columns=["r", "r_pess", "typ", "dir", "risk_pts", "cost_r"]))
        per_trade[name] = df
        rows.append({"variante": name, **stats(df)})
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "tresor.csv", index=False)
    per_trade["Kandidat (eingefroren)"].to_csv(OUT / "tresor_trades_kandidat.csv")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(tab.round(3).to_string(index=False))
    k = per_trade["Kandidat (eingefroren)"]
    print("\nMonate (Summe R, Kandidat):\n" + k["r"].groupby(k.index.to_period("M")).sum().round(2).to_string())
    print("\nStichprobe 13./16./17.11.:")
    print(k.loc[k.index.normalize().isin(pd.to_datetime(["2026-11-13", "2026-11-16", "2026-11-17"]))].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
