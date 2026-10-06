"""NUR LESEN: Kontraktdaten + Swap-Saetze fuer den Faber-Trend-Test aus den
bereits laufenden MT5-Terminals (TTP, Tickmill/EK). Keine Order, kein Login
(haengt sich an die laufende Terminal-Sitzung), kein neues Terminal-Fenster:
bricht ab, wenn das Terminal nicht laeuft. Ergebnis eingefroren nach
scripts/frozen_data/faber_symbol_specs_<datum>.json.
"""
import json
import os
import subprocess
from datetime import date

import MetaTrader5 as mt5

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERMINALS = {
    "TTP": (r"C:\Users\andre\MT5-Terminals\TTP MT5 Terminal Konto2neu\terminal64.exe", 504072729),
    "EK": (r"C:\Users\andre\MT5-Terminals\Tickmill MT5 Terminal - EKPortfolio\terminal64.exe", 55918977),
}
# interner Name -> Kandidaten-Symbolnamen (erster Treffer zaehlt)
CANDIDATES = {
    "SP500": ["US500", "SPX500", "US500.cash"], "NASDAQ": ["USTEC", "US100", "NAS100"],
    "US30": ["US30", "DJ30"], "DAX": ["DE40", "GER40", "DE30", "GER30"],
    "GOLD": ["XAUUSD"], "SILVER": ["XAGUSD"], "OIL": ["USOIL", "XTIUSD", "WTI", "CL-OIL", "USOUSD"],
    "COPPER": ["COPPER", "XCUUSD", "HG"], "TNOTE10": ["UST10Y", "TNOTE", "US10Y"],
    "TBOND30": ["USTBOND", "TBOND", "US30Y"], "EURUSD": ["EURUSD"], "USDJPY": ["USDJPY"],
    "BTC": ["BTCUSD"],
}
FIELDS = ["trade_contract_size", "volume_min", "volume_step", "swap_long", "swap_short", "swap_mode",
          "swap_rollover3days", "currency_profit", "currency_margin", "point", "trade_tick_size",
          "trade_tick_value", "spread", "bid", "ask", "description"]


def running_paths():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | ForEach-Object { $_.ExecutablePath }"],
                         capture_output=True, text=True).stdout
    return {l.strip().lower() for l in out.splitlines() if l.strip().lower().endswith("terminal64.exe")}


def main():
    run = running_paths()
    res = {"stand": str(date.today()), "konten": {}}
    for acc, (path, login) in TERMINALS.items():
        if path.lower() not in run:
            res["konten"][acc] = {"fehler": "Terminal laeuft nicht -- nicht gestartet"}
            continue
        if not mt5.initialize(path=path):
            res["konten"][acc] = {"fehler": str(mt5.last_error())}
            continue
        try:
            ai = mt5.account_info()
            if ai is None or ai.login != login:
                res["konten"][acc] = {"fehler": f"falsches Konto: {getattr(ai, 'login', None)}"}
                continue
            all_names = {s.name for s in (mt5.symbols_get() or [])}
            specs = {"login": ai.login, "waehrung": ai.currency, "equity": ai.equity, "symbole": {}}
            for k, cands in CANDIDATES.items():
                hit = next((c for c in cands if c in all_names), None)
                if hit is None:
                    hit = next((n for n in sorted(all_names) for c in cands if n.upper().startswith(c.upper())), None)
                if hit is None:
                    specs["symbole"][k] = None
                    continue
                si = mt5.symbol_info(hit)
                specs["symbole"][k] = {"symbol": hit, **{f: getattr(si, f, None) for f in FIELDS}}
            res["konten"][acc] = specs
        finally:
            mt5.shutdown()
    path = os.path.join(ROOT, "scripts", "frozen_data", f"faber_symbol_specs_{date.today():%Y%m%d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=str)
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
