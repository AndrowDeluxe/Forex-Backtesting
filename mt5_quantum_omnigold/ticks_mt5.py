"""Original-Ticks von MetaQuotes-Demo fuer den OmniGold-Nachbau exportieren.

Dukascopy weicht um 0,2-0,5 $ von den MT5-Testdaten ab; das ist so gross wie
die Ruecksetzer, an denen der EA aussteigt. Deshalb hier die echten Server-
Ticks aus dem freien Terminal `C:\\Program Files\\TTP MT5 Terminal` (Demo-Konto
5057577303, keine Bridge nutzt es). Nur lesen, nie handeln.

MetaQuotes-Demo hat Ticks fuer 2019-2020 und ab 27.05.2025; 2021 bis 04/2025
fehlen auch auf dem Server (Tester-"Qualitaet der Historie" 79 %).

Ausgabe je Monat in results/ticks/:
- `m1_YYYYMM.parquet`: M1-Kerzen aus Bid (OHLC) + letzter Ask, Brokerzeit
- `ticks_YYYYMM.parquet`: time_msc, bid, ask (vollstaendig)
"""

import datetime as dt
import sys
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

TERMINAL = r"C:\Program Files\TTP MT5 Terminal\terminal64.exe"
OUT = Path(__file__).parent / "results" / "ticks"
U = dt.timezone.utc


def export_month(year: int, month: int) -> int:
    start = dt.datetime(year, month, 1, tzinfo=U)
    end = dt.datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=U)
    tk = mt5.copy_ticks_range("XAUUSD", start, end, mt5.COPY_TICKS_ALL)
    if tk is None or len(tk) == 0:
        return 0
    d = pd.DataFrame(tk)[["time_msc", "bid", "ask"]]
    d = d[(d.bid > 0) & (d.ask > 0)]
    d["t"] = pd.to_datetime(d.time_msc, unit="ms")  # Server liefert Brokerzeit als "UTC"-Epoch
    d[["t", "bid", "ask"]].to_parquet(OUT / f"ticks_{year}{month:02d}.parquet", index=False)
    m1 = d.set_index("t").resample("1min").agg(
        open=("bid", "first"), high=("bid", "max"), low=("bid", "min"), close=("bid", "last"), ask=("ask", "last")
    ).dropna()
    m1.to_parquet(OUT / f"m1_{year}{month:02d}.parquet")
    return len(d)


def main(months: list[tuple[int, int]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=TERMINAL, timeout=30000):
        raise SystemExit(f"MT5 init fehlgeschlagen: {mt5.last_error()}")
    try:
        if mt5.account_info().server != "MetaQuotes-Demo":
            raise SystemExit("Terminal ist nicht auf MetaQuotes-Demo angemeldet")
        mt5.symbol_select("XAUUSD", True)
        for y, m in months:
            print(f"{y}-{m:02d}:", export_month(y, m), "Ticks", flush=True)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    a, b = sys.argv[1], sys.argv[2]  # z. B. 2025-05 2026-10
    rng = pd.period_range(a, b, freq="M")
    main([(p.year, p.month) for p in rng])
