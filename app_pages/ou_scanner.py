"""Live-Signale (Scanner) -- reads the committed snapshot from
ou_paper_backtest/scanner.py (run locally, NOT from Streamlit Cloud -- same
"collector runs locally, page only reads committed data" pattern as the OU-Modell
Live-Logs page). Shows which OU-selected tickers, across all three validated
markets (S&P 500, Nasdaq-100, DAX), currently sit below their lower Bollinger band
with the market-wide EMA200 regime filter open -- i.e. would trigger an entry under
the final locked strategy (see "Fertige Strategien" page) as of the last scan.

Point-in-time snapshot only: does not track positions a user might already be
holding from an earlier scan, and position sizing here assumes each signal is the
ONLY open position (the 15%-total-portfolio-risk cap from the backtest isn't
applied, since that requires knowing all other concurrently open positions)."""

from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Live-Signale", page_icon=":material/radar:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
SIGNALS_PATH = REPO_DIR / "ou_paper_backtest" / "results" / "scanner_signals.csv"

st.markdown("## :material/radar: Live-Signale (Scanner)")
st.info(
    "Zeigt, welche OU-selektierten Ticker (S&P 500, Nasdaq-100, DAX) beim letzten "
    "lokalen Scan unter ihrem unteren Bollinger-Band lagen UND der marktweite "
    "EMA200-Regimefilter offen war -- also unter der finalen, validierten "
    "Konfiguration (siehe *Fertige Strategien*) einen Long-Einstieg ausgeloest "
    "haetten. **Kein Live-Datenabruf aus Streamlit Cloud** -- dieser Scan laeuft "
    "lokal (`python ou_paper_backtest/scanner.py`) und wird committed, exakt wie "
    "die OU-Modell Live-Logs-Seite. Momentaufnahme: verfolgt keine bereits offenen "
    "Positionen aus fruehreren Scans, und die Positionsgroesse geht davon aus, dass "
    "jedes Signal die EINZIGE offene Position ist (das 15%-Gesamtrisiko-Cap aus dem "
    "Backtest kann hier nicht angewendet werden).",
    icon=":material/info:",
)

if not SIGNALS_PATH.exists():
    st.error(
        "Noch kein Scan committed. Lokal `python ou_paper_backtest/scanner.py` "
        "ausfuehren und `ou_paper_backtest/results/scanner_signals.csv` committen.",
        icon=":material/error:",
    )
    st.stop()

signals = pd.read_csv(SIGNALS_PATH)

if signals.empty:
    st.success(
        "Keine aktiven Setups beim letzten Scan -- entweder kein Ticker unter dem "
        "unteren Band, oder der Regimefilter war auf mindestens einem Markt geschlossen.",
        icon=":material/check_circle:",
    )
    st.stop()

scan_date = signals["scan_date"].iloc[0]
st.caption(f"Letzter Scan: {scan_date} -- {len(signals)} Setup(s) ueber {signals['market'].nunique()} Markt/Maerkte.")

with st.container(horizontal=True):
    st.metric("Setups gesamt", len(signals), border=True)
    for market in signals["market"].unique():
        st.metric(market, int((signals["market"] == market).sum()), border=True)

display_cols = [
    "market", "ticker", "close", "entry", "sl", "tp", "risk_pct_price",
    "position_size_pct", "position_size_concentrated_pct", "regime_ok",
]
st.dataframe(
    signals[[c for c in display_cols if c in signals.columns]].sort_values(["market", "ticker"]),
    hide_index=True,
    column_config={
        "market": st.column_config.TextColumn("Markt"),
        "ticker": st.column_config.TextColumn("Ticker"),
        "close": st.column_config.NumberColumn("Kurs", format="%.2f"),
        "entry": st.column_config.NumberColumn("Entry", format="%.2f"),
        "sl": st.column_config.NumberColumn("Stop", format="%.2f"),
        "tp": st.column_config.TextColumn("Ziel"),
        "risk_pct_price": st.column_config.NumberColumn("SL-Abstand (%)", format="%.2f%%"),
        "position_size_pct": st.column_config.NumberColumn("Groesse Risk-based (%)", format="%.2f%%"),
        "position_size_concentrated_pct": st.column_config.NumberColumn("Groesse Konzentriert (%)", format="%.2f%%"),
        "regime_ok": st.column_config.CheckboxColumn("Regime offen"),
    },
)
st.caption(
    "Groesse Risk-based (%) = 1% Equity-Risiko / SL-Abstand, gedeckelt auf 20% "
    "Notional. Groesse Konzentriert (%) = 1/(Anzahl heutiger Setups in diesem "
    "Markt), gedeckelt auf 1/8 -- beide exakt wie im Backtest "
    "(`portfolio.simulate_bracket_portfolio` bzw. `simulate_concentrated_book`). "
    "**Wichtig:** im echten Out-of-Sample-Test (2025-heute, siehe *Fertige "
    "Strategien*) lagen BEIDE Methoden weit unter Buy&Hold -- vor blindem Vertrauen "
    "in diese Zahlen erst den OOS-Abschnitt dort lesen."
)
