"""Live Log -- BTC EMA9/21 Paper-Forward-Test, 2026-08-16. Gleiches
"Collector laeuft lokal, Seite liest nur committete Daten"-Muster wie
app_pages/cls_practical_live_log.py/ou_scanner.py:
scripts/collect_btc_ema_cross_daily_log.py laeuft taeglich 02:10 (Europe/
Berlin) per Windows Task Scheduler ("BTC-EMA-Cross-Scan") und committet
btc_ema_cross_logs/. Diese Seite ruft nie Binance selbst auf.

PAPIER-Konto: $100k, 1% Risiko/Trade, exakt die im Dashboard
(app_pages/btc_ema_cross.py) validierte Konfiguration - siehe
btc_ema_cross/live_scan.py fuer die Logik, verifiziert gegen den Batch-
Backtest via scripts/verify_btc_ema_cross_live_scan.py (61/61 Trades ueber
8 Jahre exakt uebereinstimmend, siehe knowledge/resources/
trend-following-momentum.md)."""

import json
from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="BTC EMA9/21 -- Live Log", page_icon=":material/rss_feed:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_DIR / "btc_ema_cross_logs"
DAILY_LOG = LOG_DIR / "daily_log.csv"
STATE_PATH = LOG_DIR / "paper_state.json"
TRADES_CSV = LOG_DIR / "paper_trades.csv"

st.page_link("app_pages/btc_ema_cross.py", label="Zurueck zu BTC EMA9/21 Crossover", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/rss_feed: BTC EMA9/21 -- Paper-Forward-Test Live Log")
st.warning(
    "**Reines Papier-Konto -- keine echten Orders, kein Exchange-Konto verbunden.** "
    "Startkapital $100k, 1% Risiko/Trade, ATR(14)x2.0-Stop, kein TP/BE -- exakt die im "
    "Dashboard validierte Konfiguration. Ein taeglicher Scan (Windows Task Scheduler, "
    "~02:10 Europe/Berlin, kurz nach dem 00:00-UTC-Tagesschluss von Binance) prueft die "
    "Signale und aktualisiert diese Seite.",
    icon=":material/science:",
)

if not STATE_PATH.exists():
    st.info("Noch kein Scan gelaufen.", icon=":material/hourglass_empty:")
    st.stop()

state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

st.markdown("### Aktueller Status")
cols = st.columns(4)
cols[0].metric("Position", "LONG" if state["in_position"] else "FLAT")
cols[1].metric("Cash", f"${state['cash']:,.2f}")
if state["in_position"]:
    cols[2].metric("Entry", f"${state['raw_entry_price']:,.2f}")
    cols[3].metric("Stop", f"${state['stop_price']:,.2f}")
    st.caption(f"Entry-Datum: {state['entry_date']}  |  Groesse: {state['qty']:.6f} BTC")
else:
    cols[2].metric("Entry", "--")
    cols[3].metric("Stop", "--")

st.divider()
st.markdown("### Taegliches Log")
if DAILY_LOG.exists():
    daily = pd.read_csv(DAILY_LOG)
    st.dataframe(daily.sort_values("date", ascending=False), hide_index=True, width="stretch")
else:
    st.caption("Noch kein taegliches Log vorhanden.")

st.divider()
st.markdown("### Geschlossene Trades")
if TRADES_CSV.exists():
    trades = pd.read_csv(TRADES_CSV)
    st.dataframe(trades.sort_values("exit_date", ascending=False), hide_index=True, width="stretch")

    equity_points = [100_000.0] + trades["cash_after"].tolist()
    st.markdown("#### Equity-Kurve (nur geschlossene Trades, kein Mark-to-Market zwischendrin)")
    st.line_chart(pd.Series(equity_points, name="Equity"))

    n = len(trades)
    wins = (trades["pnl_dollar"] > 0).sum()
    total_pnl = trades["pnl_dollar"].sum()
    st.caption(
        f"{n} geschlossene Trades, {wins} Gewinner ({wins/n:.0%} Win-Rate), "
        f"Gesamt-PnL ${total_pnl:+,.2f} seit Start."
    )
else:
    st.caption("Noch keine geschlossenen Trades.")

st.caption(
    "Reproduzierbar/Logik: `btc_ema_cross/live_scan.py`. Verifiziert gegen den Batch-Backtest: "
    "`scripts/verify_btc_ema_cross_live_scan.py`."
)
