"""OU-Optimierung Block 0/2: Intraday-Daten von TTP ziehen (read-only, 2026-09-17).

1. Stundenkerzen (OHLC + Broker-Spread-Feld) je Universum-Aktie, so weit TTP
   zurueckliefert (~3,5 Jahre) -> Block 2 (Einstiegszeit).
2. Spread-Stichproben: fuer die letzten N Handelstage je halbe Stunde (09:30 ...
   15:30 NY) ein 3-Minuten-Tickfenster ab Bucket+2 Min -> Block 0 (Kostenkurve).

Nur copy_rates_from / copy_ticks_range / symbol_select -- keine Order.
Laeuft unter Funded-Portfolio-Bridge::account_state_lock("ttp"), aber je Ticker
nur kurz gehalten, damit kein Bridge-Lauf auf das Terminal wartet.
"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
FUNDED = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
OUT = REPO / "ou_paper_backtest" / "data_cache" / "intraday_ttp"
OUT.mkdir(parents=True, exist_ok=True)
N_DAYS = 20
NY = ZoneInfo("America/New_York")
SERVER = ZoneInfo("Europe/Helsinki")  # = orb_mt5_source.SERVER_TZ, verifiziert UTC+3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import research_ou_execution_costs as rx  # noqa: E402

sys.path.insert(0, str(FUNDED))
import run_once as funded  # noqa: E402


def srv(dt_ny: datetime) -> datetime:
    """NY-Zeitpunkt -> MT5-Konvention: Server-Wanduhr, als waere sie UTC."""
    return dt_ny.astimezone(SERVER).replace(tzinfo=None).replace(tzinfo=timezone.utc)


def is_quiet_minute() -> bool:
    """Bridge-Laeufe meiden: Funded :13/:28/:43/:58 (+~1 Min), Fast alle 5 Min :x3/:x8."""
    m = datetime.now().minute
    return m % 5 in (0, 1)  # startet >= 60 s vor dem naechsten :x3-Lauf; Bridge wartet max. 45 s auf den Lock


def main():
    _, _, uni = rx.load_universe()
    tickers = sorted({t for v in uni.values() for t in v})
    acc = [a for a in funded.ACCOUNTS if a.state_id == "ttp"][0]

    # letzte N NYSE-Handelstage (Mo-Fr, Feiertage fallen unten als "keine Ticks" heraus)
    days, d = [], datetime.now(NY).date() - timedelta(days=1)
    while len(days) < N_DAYS:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    # TTP quotiert Aktien-CFDs erst ab 09:35 NY (Tickabzug 2026-09-17: erster Tick
    # 09:35:00) und bis ~15:55 -- deshalb 09:35 statt 09:30, dazu 09:45 fuer die
    # teure Eroeffnungsphase und 15:45 fuer "Einstieg kurz vor Schluss".
    buckets = [(9, 35), (9, 45)] + [(h, m) for h in range(10, 16) for m in (0, 30)] + [(15, 45)]

    rows, bars_ok = [], 0
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if only:
        tickers = [t for t in tickers if t in only]
    for i, t in enumerate(tickers):
        for _ in range(10):
            while not is_quiet_minute():
                time.sleep(10)
            try:
                lock = funded.account_state_lock(acc)
                lock.__enter__()
                break
            except TimeoutError:
                time.sleep(30)
        else:
            print(f"{t}: Lock nie frei -- uebersprungen")
            continue
        t_start = time.monotonic()
        try:
            mt5.shutdown()
            if not (mt5.initialize(path=acc.mt5_terminal_path, timeout=30000)
                    and mt5.login(acc.mt5_login, password=acc.mt5_password, server=acc.mt5_server, timeout=30000)):
                print("Verbindung fehlgeschlagen", t, mt5.last_error())
                continue
            if mt5.symbol_info(t) is None:
                print(f"{t}: kein Symbol auf TTP")
                mt5.shutdown()
                continue
            mt5.symbol_select(t, True)
            h1 = mt5.copy_rates_from(t, mt5.TIMEFRAME_H1, datetime.now(timezone.utc) + timedelta(days=1), 99999)
            if h1 is not None and len(h1):
                pd.DataFrame(h1).to_parquet(OUT / f"{t}_H1.parquet")
                bars_ok += 1
            for day in days:
                for hh, mm in buckets:
                    offset = 0 if (hh, mm) == (9, 35) else 2  # erster Quote kommt exakt 09:35
                    start_ny = datetime(day.year, day.month, day.day, hh, mm, tzinfo=NY) + timedelta(minutes=offset)
                    ticks = mt5.copy_ticks_range(t, srv(start_ny), srv(start_ny + timedelta(minutes=3)), mt5.COPY_TICKS_INFO)
                    if ticks is None or len(ticks) == 0:
                        continue
                    tk = pd.DataFrame(ticks)
                    tk = tk[(tk["bid"] > 0) & (tk["ask"] > tk["bid"])]
                    if tk.empty:
                        continue
                    mid = (tk["bid"] + tk["ask"]) / 2
                    rows.append({"ticker": t, "day": day.isoformat(), "bucket": f"{hh:02d}:{mm:02d}",
                                 "spread_bps": float(np.median((tk["ask"] - tk["bid"]) / mid * 1e4)),
                                 "n_ticks": int(len(tk)), "mid": float(mid.median())})
            mt5.shutdown()
        finally:
            lock.__exit__(None, None, None)
        print(f"[{i + 1}/{len(tickers)}] {t} ({time.monotonic() - t_start:.0f}s Lock): H1 {'ok' if h1 is not None and len(h1) else 'leer'}, "
              f"Spread-Stichproben bisher {len(rows)}", flush=True)

    name = "spread_samples.parquet" if not only else f"spread_samples_{'_'.join(only)}.parquet"
    pd.DataFrame(rows).to_parquet(OUT / name)
    print(f"fertig: {bars_ok} Stundenkerzen-Dateien, {len(rows)} Spread-Stichproben -> {OUT}")


if __name__ == "__main__":
    main()
