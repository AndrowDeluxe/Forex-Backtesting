"""Baut die Liste der auf TTP (TTPMarkets) tatsaechlich handelbaren Aktien --
fuer alle drei im Projekt genutzten Maerkte (S&P 500, Nasdaq-100, DAX).

Hintergrund: das OU-Modell wurde bisher auf ALLE Ticker jedes Universums
rueckgetestet, obwohl der Live-Bot (OU-Modell-MT5-Bridge) nur Signale fuer
Ticker ausfuehren kann, die auf dem tatsaechlichen Broker (TTPMarkets) als
Symbol existieren -- resolve_symbol() in executor.py ueberspringt jedes
Signal, dessen Symbol mt5.symbol_info() nicht liefert. Ein Backtest auf dem
vollen Universum ist damit ein Datenleck/Bias: er nimmt eine Handelbarkeit
an, die live nicht gegeben ist. Fuer S&P 500 zuerst gefunden (2026-08-11,
58/147 OU-selektierte Ticker tatsaechlich handelbar); dieses Skript prueft
dieselbe Frage jetzt auch fuer Nasdaq-100 und DAX.

Read-only, keine Order-Platzierung: fragt ausschliesslich mt5.symbols_get()
gegen das bereits laufende TTP-DEMO-Terminal (Konto 2, state_id="konto2_ttp",
KEIN Echtgeld) ab -- Zugangsdaten werden NUR zur Laufzeit aus dem separaten
OU-Modell-MT5-Bridge-Repo importiert, nie in dieses Repo geschrieben.

WICHTIG fuer DAX: die yfinance-Ticker in dax_wiki.csv tragen Boersen-Suffixe
(z.B. "SAP.DE", "AIR.PA" fuer Airbus/Euronext Paris) -- das ist NICHT
zwangslaeufig der MT5-Symbolname bei TTP. Dieses Skript prueft sowohl den
1:1-Namen (das, was resolve_symbol() ohne symbol_map tatsaechlich pruefen
wuerde) als auch den Namen OHNE Suffix (z.B. "SAP" statt "SAP.DE") als
Diagnose, meldet aber ttp_tradable=True nur fuer den 1:1-Fall, solange kein
symbol_map-Eintrag existiert.

Ergebnis je Markt: ou_paper_backtest/results/<market>_ttp_tradable.csv."""

import sys
from pathlib import Path

import pandas as pd

BRIDGE_DIR = Path(r"C:\Users\andre\OU-Modell-MT5-Bridge")
sys.path.insert(0, str(BRIDGE_DIR))

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"

MARKETS = {
    "sp500": {"wiki_csv": OU_DIR / "sp500_wiki.csv", "symbol_col": "Symbol", "name_col": "Security"},
    "nasdaq100": {"wiki_csv": OU_DIR / "nasdaq100_wiki.csv", "symbol_col": "Ticker", "name_col": "Company"},
    "dax": {"wiki_csv": OU_DIR / "dax_wiki.csv", "symbol_col": "Ticker", "name_col": "Company"},
}


def main() -> None:
    import MetaTrader5 as mt5

    import config as bridge_config  # from OU-Modell-MT5-Bridge, not this repo

    account = next(a for a in bridge_config.ACCOUNTS if a.state_id == "konto2_ttp")
    print(f"Verbinde read-only zu {account.name} ({account.mt5_server})...")

    ok = mt5.initialize(
        path=account.mt5_terminal_path,
        login=account.mt5_login,
        password=account.mt5_password,
        server=account.mt5_server,
    )
    if not ok:
        print(f"mt5.initialize() fehlgeschlagen: {mt5.last_error()}")
        sys.exit(1)

    try:
        info = mt5.account_info()
        print(f"Verbunden: login={info.login}, server={info.server}, "
              f"trade_mode={'DEMO' if info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO else 'LIVE/ANDERES'}")
        assert info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO, "Sicherheitscheck: das sollte das Demo-Konto sein!"

        all_symbols = mt5.symbols_get()
        symbol_names = {s.name for s in all_symbols}
        stock_symbols = sorted(s.name for s in all_symbols if s.path.startswith("Stocks"))
        print(f"{len(all_symbols)} Symbole insgesamt, davon {len(stock_symbols)} unter 'Stocks'.")
        print(f"Beispiele Stocks-Symbole: {stock_symbols[:15]}")
        # grobe Diagnose: gibt es ueberhaupt europaeische/deutsche Namen im Stocks-Zweig?
        de_like = [s for s in stock_symbols if any(k in s.upper() for k in
                   ("SAP", "SIE", "ALV", "BAS", "BAY", "BMW", "VOW", "DTE", "MBG", "ADS"))]
        print(f"Moegliche DAX-nahe Symbole (grobe Substring-Suche): {de_like}")

        for market_key, meta in MARKETS.items():
            wiki = pd.read_csv(meta["wiki_csv"])
            tickers = wiki[meta["symbol_col"]].tolist()
            rows = []
            n_tradable = 0
            for t in tickers:
                tradable = t in symbol_names
                base = t.split(".")[0] if "." in t else None
                base_tradable = base in symbol_names if base else None
                rows.append({
                    "Symbol": t,
                    "Name": wiki.loc[wiki[meta["symbol_col"]] == t, meta["name_col"]].iloc[0],
                    "ttp_tradable": tradable,
                    "base_symbol_tradable": base_tradable,  # nur Diagnose, s.o.
                })
                if tradable:
                    n_tradable += 1
            out = pd.DataFrame(rows)
            out_path = OU_DIR / "results" / f"{market_key}_ttp_tradable.csv"
            out.to_csv(out_path, index=False)
            print(f"\n[{market_key}] {n_tradable}/{len(tickers)} Ticker 1:1 auf TTP handelbar "
                  f"(wie resolve_symbol() es live prueft ohne symbol_map). Gespeichert: {out_path}")
            if out["base_symbol_tradable"].fillna(False).any():
                n_base = int(out["base_symbol_tradable"].fillna(False).sum())
                print(f"  Hinweis: {n_base} weitere Ticker waeren OHNE Boersen-Suffix handelbar "
                      f"(z.B. 'SAP' statt 'SAP.DE') -- aktuell NICHT aktiv, da kein "
                      f"symbol_map-Eintrag fuer diese Faelle existiert.")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
