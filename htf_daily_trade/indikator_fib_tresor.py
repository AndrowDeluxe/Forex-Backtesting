"""Fib-Limit-Kandidat einfrieren + Tresor einmal oeffnen (Nutzerauftrag 27.11.2026, "interessehalber").

    python -m htf_daily_trade.indikator_fib_tresor

Eingefroren: A80 GX F0.5 V3 S2 T10 auf UTC-Tagen (= Backtest-Konfiguration). Tresor 26.05.-25.11.2026.
Auswertung auf H1 (indikator_fib_h1, Tageskerzen aus H1), weil die Dukascopy-D1-Dateien vor dem Tresorende enden.
Broker-Tag (SERVER) nur zur Info. Signale ohne 10 Tage Nachlauf fallen weg.
"""
from __future__ import annotations

import pandas as pd

from htf_daily_trade.backtest_r import stats
from htf_daily_trade.filter_matrix import MARKETS
from htf_daily_trade.indikator_fib_h1 import run
from research_lock import Lock

CONFIG = {"signal": "ML-Flaeche >= 80 % (3 T) + Stoch- oder RSI-MA-Cross", "limit": "0,5-Fib Signalkerze, 3 Tage",
          "stop": "Signal-Extrem +/- 0,25 ATR", "exit": "10 Tage Zeit", "tage": "UTC", "maerkte": list(MARKETS)}

if __name__ == "__main__":
    lock = Lock("indikator_fib_limit")
    h = lock.freeze(CONFIG)
    start, end = lock.unseal("tresor", h)
    print("Tresor", start, "bis", end)
    for mode in ("UTC", "SERVER"):
        t = pd.DataFrame([r for m in MARKETS for r in run(m, mode, start, end, [(3, 0.25)])])
        t.to_csv(f"htf_daily_trade/indikator_fib_tresor_{mode.lower()}.csv", index=False)
        if t.empty:
            print(mode, "keine Trades"); continue
        st = stats(t["r"])
        print(f"\n{mode}: n {st['n']}  R {st['mean_r']:.3f}  t {st['t']:.2f}  Summe {t['r'].sum():.2f}")
        print(t[["markt", "seite", "signal", "r"]].round(2).to_string(index=False))
