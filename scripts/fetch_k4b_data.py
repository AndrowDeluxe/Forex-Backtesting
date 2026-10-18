"""K4-Nachtest (18.10.2026): M1-Bid 2016-heute fuer USDNOK/USDSEK und M1-Ask
fuer zwei IS-Jahre (2019, 2021) zur Spread-Messung -- auch EURUSD als Referenz.
Reiner Datenabruf, keine Auswertung."""
import sys
from pathlib import Path

import dukascopy_python
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smh_microstructure.data import CACHE, INSTRUMENTS, load  # noqa: E402

ASK = CACHE / "ask"
for sym in ("USDNOK", "USDSEK"):
    load(sym)
    print(sym, "bid ok", flush=True)
ASK.mkdir(parents=True, exist_ok=True)
for sym in ("EURUSD", "USDNOK", "USDSEK"):
    for y in (2019, 2021):
        path = ASK / f"{sym}_M1_ASK_{y}.parquet"
        if path.exists():
            continue
        df = dukascopy_python.fetch(INSTRUMENTS[sym], dukascopy_python.INTERVAL_MIN_1, dukascopy_python.OFFER_SIDE_ASK,
                                    pd.Timestamp(f"{y}-01-01").to_pydatetime(), pd.Timestamp(f"{y + 1}-01-01").to_pydatetime())
        df = df.sort_index()
        df = df[~df.index.duplicated()]
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df[["open", "close"]].astype("float64").to_parquet(path)
        print(sym, y, "ask ok", flush=True)
