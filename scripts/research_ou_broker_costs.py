"""OU-Modell: Handelskosten EK (Tickmill) vs. FK (TTP) je Aktie (Research, 2026-09-19).

Nutzerfrage: "wie unterschiedlich sind die Kosten auf EK und FK und wie
unterschiedlich entwickelt sich dadurch das Bein?"

Die Kostenzahlen der bisherigen Auswertung (Spread 12 bps / 27,9 bps zur
Eroeffnung, Swap 1,78 bps/Tag) stammen AUSSCHLIESSLICH von TTP -- die
Tickfenster am 17.09. liefen ueber das Funded-Terminal. Fuer das EK-Bein
(Tickmill, echtes Geld, eigenes Kapital) war nie etwas gemessen; es wurde
bisher stillschweigend mit denselben Zahlen gerechnet. Genau das pruefen wir
hier nach.

Gemessen je Broker ueber das OU-Universum (~59 Aktien):
  1. SPREAD aus dem `spread`-Feld der H1-Kerzen (Punkte -> bps ueber den
     Kerzenschluss), getrennt nach NY-Stunde. Broker-eigene Kurse, mehrere
     Jahre Historie, kein Tickabzug noetig.
  2. SWAP aus symbol_info: swap_long in Prozent p.a. (beide Broker rechnen
     Aktien-CFD-Swaps prozentual) -> bps je Kalendertag.
  3. Handelbarkeit: trade_mode je Symbol (ein Titel, den ein Broker nicht
     stellt, ist kein Nullbeitrag -- siehe Memory iq_no_stocks_leg_weight_coupling).

REIN LESEND: copy_rates_range / symbol_info / symbol_select. Keine Order,
keine Config-Aenderung. Startet fehlende Terminals mit /portable und schliesst
GENAU die wieder, die vorher nicht liefen (Vorfall 2026-09-01).

Aufruf: python research_ou_broker_costs.py [--days 120]
"""
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import measure_broker_spreads as mbs  # noqa: E402  (Terminal-Handling, Lock, Connect)
import research_ou_execution_costs as rx  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = REPO / "ou_paper_backtest" / "results" / "broker_costs_ou_20260919.json"
NY = ZoneInfo("America/New_York")
SERVER = ZoneInfo("Europe/Helsinki")  # MT5-Zeitstempel sind Serverzeit (UTC+3), nicht UTC
TERMINAL_BOOT_S = 60  # Tickmill braucht laenger als die 20 s in measure_broker_spreads._connect
FUNDED = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
EK = Path(r"C:\Users\andre\EK-Portfolio-Bridge")


def _targets():
    """Ein Konto je BROKER (nicht je Konto): die zwei TTP-Konten haengen am
    selben Server und sehen denselben Spread. Fuer TTP das DEMO-Konto 2 --
    gleicher Server wie Konto 1, aber kein Echtgeld-Terminal angefasst."""
    out = []
    sys.path.insert(0, str(FUNDED))
    import config as funded_config  # noqa: E402
    acc = next(a for a in funded_config.ACCOUNTS if a.state_id == "ttp")
    out.append(mbs.Target(portfolio="FK", account=acc.name, broker=acc.mt5_server, state_id=acc.state_id,
                          terminal_path=acc.mt5_terminal_path, login=acc.mt5_login,
                          password=acc.mt5_password, server=acc.mt5_server, symbol=""))
    sys.path.remove(str(FUNDED))
    del sys.modules["config"]

    sys.path.insert(0, str(EK))
    import config as ek_config  # noqa: E402
    out.append(mbs.Target(portfolio="EK", account="EK-Portfolio (Tickmill, echtes Geld)",
                          broker=ek_config.MT5_SERVER, state_id=None,
                          terminal_path=ek_config.TERMINAL_PATH, login=ek_config.MT5_LOGIN,
                          password=ek_config.MT5_PASSWORD, server=ek_config.MT5_SERVER, symbol=""))
    sys.path.remove(str(EK))
    del sys.modules["config"]
    return out


def _connect_direct(target) -> None:
    """Verbindet wie die Bridges selbst: Zugangsdaten DIREKT an initialize(),
    nicht als separates mt5.login() (so macht es measure_broker_spreads._connect,
    und genau daran scheitert ein frisch gestartetes Tickmill-Terminal mit
    'Authorization failed' -- es ist noch in keinem Konto eingeloggt).
    Ein Versuch, kein Retry: wiederholte Fehlanmeldungen sperren Live-Konten."""
    mt5.shutdown()
    if not mt5.initialize(path=target.terminal_path, login=target.login,
                          password=target.password, server=target.server, timeout=60000):
        raise RuntimeError(f"initialize() fehlgeschlagen fuer {target.account}: {mt5.last_error()}")
    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"account_info() fehlgeschlagen fuer {target.account}: {mt5.last_error()}")
    if info.login != target.login:
        raise RuntimeError(f"Terminal ist in Konto {info.login} eingeloggt, erwartet {target.login}.")
    print(f"    verbunden: {info.login} @ {info.server}, Equity {info.equity:.2f} {info.currency}", flush=True)


def measure(target, tickers, days) -> dict:
    res = {"portfolio": target.portfolio, "account": target.account, "broker": target.broker,
           "symbols": {}, "not_tradable": []}
    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=days)
    for t in tickers:
        info = mt5.symbol_info(t)
        if info is None:
            res["not_tradable"].append(t)
            continue
        if not info.visible and not mt5.symbol_select(t, True):
            res["not_tradable"].append(t)
            continue
        info = mt5.symbol_info(t)
        rates = mt5.copy_rates_range(t, mt5.TIMEFRAME_H1, frm, now)
        row = {"swap_long_pct_pa": float(info.swap_long), "swap_mode": int(info.swap_mode),
               "trade_mode": int(info.trade_mode), "point": float(info.point)}
        if rates is not None and len(rates) > 20:
            d = pd.DataFrame(rates)
            d["ny_hour"] = (pd.to_datetime(d["time"], unit="s").dt.tz_localize(SERVER, ambiguous="NaT",
                        nonexistent="shift_forward").dt.tz_convert(NY).dt.hour)
            d = d[(d["ny_hour"] >= 9) & (d["ny_hour"] <= 16) & (d["close"] > 0)]
            if len(d) > 20:
                d["bps"] = d["spread"] * info.point / d["close"] * 1e4
                row["n_bars"] = int(len(d))
                row["spread_bps_median"] = round(float(d["bps"].median()), 2)
                row["spread_bps_p75"] = round(float(d["bps"].quantile(0.75)), 2)
                first = d[d["ny_hour"] == 9]["bps"]
                row["spread_bps_open"] = round(float(first.median()), 2) if len(first) > 5 else None
                late = d[d["ny_hour"] >= 12]["bps"]
                row["spread_bps_late"] = round(float(late.median()), 2) if len(late) > 5 else None
        res["symbols"][t] = row
    return res


def summarise(res) -> dict:
    rows = [r for r in res["symbols"].values() if "spread_bps_median" in r]
    med = lambda key: round(float(np.median([r[key] for r in rows if r.get(key) is not None])), 2) if rows else None
    swaps = [r["swap_long_pct_pa"] for r in res["symbols"].values()]
    s = {"n_symbols": len(res["symbols"]), "n_with_bars": len(rows), "not_tradable": len(res["not_tradable"]),
         "spread_bps_median": med("spread_bps_median"), "spread_bps_open": med("spread_bps_open"),
         "spread_bps_late": med("spread_bps_late"),
         "swap_long_pct_pa_median": round(float(np.median(swaps)), 3) if swaps else None,
         "swap_modes": sorted({int(r["swap_mode"]) for r in res["symbols"].values()})}
    if s["swap_long_pct_pa_median"] is not None:
        s["swap_bps_day"] = round(abs(s["swap_long_pct_pa_median"]) / 365 * 100, 3)
    return s


def main():
    days = 120
    for i, a in enumerate(sys.argv):
        if a == "--days":
            days = int(sys.argv[i + 1])
    _, _, uni = rx.load_universe()
    tickers = sorted({t for v in uni.values() for t in v})
    print(f"OU-Universum: {len(tickers)} Titel, Fenster {days} Tage H1\n", flush=True)

    out = {"measured_at": datetime.now().isoformat(timespec="seconds"), "lookback_days": days,
           "n_tickers": len(tickers), "brokers": {}}
    for target in _targets():
        print(f"=== {target.portfolio}: {target.account} ({target.broker}) ===", flush=True)
        was_running = mbs._terminal_running(target.terminal_path)
        if not was_running:
            import subprocess
            subprocess.Popen([target.terminal_path, "/portable"])
            print(f"    Terminal gestartet, warte {TERMINAL_BOOT_S}s ...", flush=True)
            time.sleep(TERMINAL_BOOT_S)
        try:
            if target.state_id:
                with mbs.account_state_lock(target):
                    _connect_direct(target)
                    res = measure(target, tickers, days)
            else:
                _connect_direct(target)
                res = measure(target, tickers, days)
        finally:
            mt5.shutdown()
            if not was_running:
                time.sleep(2)
                mbs._stop_terminal(target.terminal_path)
                print("    Terminal wieder geschlossen (lief vorher nicht).", flush=True)
        res["summary"] = summarise(res)
        out["brokers"][target.portfolio] = res
        print("   ", json.dumps(res["summary"], ensure_ascii=False), flush=True)

    OUT.write_text(json.dumps(out, indent=1, default=str))
    print("\ngeschrieben:", OUT)


if __name__ == "__main__":
    main()
