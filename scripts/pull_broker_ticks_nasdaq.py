"""Zieht NASDAQ-Ticks (Bid/Ask) aus den Broker-Terminals fuer die ORB-Fill-Messung (15.11.2026).

REIN LESEND (copy_ticks_range), keine Order. Nutzt Verbindung, State-Lock und Terminal-Handhabung aus
scripts/measure_broker_spreads.py. Startet fehlende Terminals und schliesst genau die wieder.

Fenster je Handelstag: Serverzeit 14:50 bis 00:05 (deckt 08:50-16:05 NY fuer Server = NY+6..+8 ab;
der genaue Versatz wird spaeter je Tag gegen Dukascopy bestimmt).
Ausgabe: data_cache/broker_ticks/<broker>_<symbol>.parquet  (time_msc [Serverzeit], bid, ask)

  python scripts/pull_broker_ticks_nasdaq.py --start 2026-05-15 --end 2026-11-13
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import measure_broker_spreads as M  # noqa: E402

OUT = ROOT / "data_cache" / "broker_ticks"
SHORT = {"TTPMarkets-Server": "TTP", "BeyondIQCapital-Server": "IQ", "TickmillEU-Live": "Tickmill"}


def main() -> int:
    import MetaTrader5 as mt5
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    days = pd.bdate_range(a.start, a.end)
    seen, started = set(), []
    for t in M._load_targets(("NASDAQ",)):
        if t.terminal_path in seen:
            continue
        seen.add(t.terminal_path)
        was = M._terminal_running(t.terminal_path)
        name = SHORT.get(t.server, t.server)
        parts = []
        try:
            with M.account_state_lock(t):
                M._connect(mt5, t)
                if not was:
                    started.append(t.terminal_path)
                M._ensure_symbol(mt5, t.symbol)
                for d in days:
                    f = datetime(d.year, d.month, d.day, 14, 50)
                    tk = mt5.copy_ticks_range(t.symbol, f, f + timedelta(hours=9, minutes=15), mt5.COPY_TICKS_ALL)
                    if tk is None or len(tk) == 0:
                        continue
                    df = pd.DataFrame(tk)[["time_msc", "bid", "ask"]]
                    df = df[(df.bid > 0) & (df.ask > 0)]
                    parts.append(df)
                info = mt5.symbol_info(t.symbol)
                print(f"{name} {t.symbol}: {len(parts)} Tage, digits {info.digits}, contract {info.trade_contract_size}",
                      flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"{name}: FEHLER {exc}", flush=True)
            continue
        if parts:
            out = pd.concat(parts, ignore_index=True).drop_duplicates()
            out["bid"] = out.bid.astype(np.float64)
            out["ask"] = out.ask.astype(np.float64)
            out.to_parquet(OUT / f"{name}_{t.symbol}.parquet", index=False)
            print(f"  {len(out):,} Ticks gespeichert", flush=True)
    mt5.shutdown()
    for p in started:
        M._stop_terminal(p)
        print("geschlossen:", p)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
