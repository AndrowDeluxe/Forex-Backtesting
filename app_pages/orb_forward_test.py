"""Live Logs -- ORB Forward-Test: read-only view of the ORB long-only +
ADX>=25 + weekday-filter strategy running on a MetaQuotes-Demo account
(110209087 - demo, no real money), collected by
scripts/collect_orb_forward_test_log.py and committed to
orb_forward_test_logs/daily_log.csv (the forward-test project's local
logs/state DB/MT5 terminal live outside this repo, unreachable from
Streamlit Cloud - this page only ever reads the committed CSV/raw logs,
never connects to MT5 or touches an order).

First live day: 2026-08-03. Intentionally no performance verdict here -
the backtest (see the "ORB Strategie" page) is the actual evidence base;
this page is a forward-test sanity check accumulating over time, same
thin-sample discipline as everywhere else in this project.
"""

from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="ORB Forward-Test -- Live Logs", page_icon=":material/bolt:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_DIR / "orb_forward_test_logs" / "daily_log.csv"
RAW_DIR = REPO_DIR / "orb_forward_test_logs" / "raw"

st.markdown("## :material/bolt: ORB Forward-Test -- Live-Log")

st.info(
    "**Demokonto, kein echtes Geld.** Long-only + ADX>=25 + Wochentag-Filter "
    "(USTEC ohne Donnerstag, US500 ohne Montag) laeuft alle 15 Minuten auf "
    "einem MetaQuotes-Demokonto (110209087) - dieselbe Konfiguration wie im "
    "Backtest (siehe \"ORB Strategie\"-Seite). Seit **03.08.2026** live "
    "(nicht nur Dry-Run). Diese Seite zeigt nur committete Tageswerte -- "
    "kein Live-Zugriff auf MT5 von hier aus. **Der Backtest ist die "
    "eigentliche Evidenzbasis** - das hier ist ein zusaetzlicher, langsam "
    "wachsender Realitaets-Check, keine neue Beweisquelle nach ein paar Tagen.",
    icon=":material/warning:",
)

if not CSV_PATH.exists():
    st.warning(
        "Noch keine Tages-Logs vorhanden. Der erste Eintrag wird ueber "
        "`scripts/collect_orb_forward_test_log.py` ergaenzt.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

df = pd.read_csv(CSV_PATH, parse_dates=["date"])
df = df.sort_values("date")

n_days = len(df)
st.caption(f"{n_days} Tag{'e' if n_days != 1 else ''} erfasst seit {df['date'].min().date()}.")

latest = df.iloc[-1]
with st.container(horizontal=True):
    st.metric("Equity", f"{latest['current_equity']:,.2f}" if pd.notna(latest["current_equity"]) else "n/a", border=True)
    st.metric("Floating P&L", f"{latest['floating_pnl']:+,.2f}" if pd.notna(latest["floating_pnl"]) else "n/a", border=True)
    st.metric("Scans heute", int(latest["runs"]) if pd.notna(latest["runs"]) else "n/a", border=True)
    st.metric("Orders gesendet", int(latest["orders_sent"]) if pd.notna(latest["orders_sent"]) else "n/a", border=True)
    st.metric("Session-Ende-Exits", int(latest["session_end_closes"]) if pd.notna(latest["session_end_closes"]) else "n/a", border=True)

if isinstance(latest.get("connection_error"), str) and latest["connection_error"]:
    st.warning(f"MT5-Verbindung beim Erfassen dieses Tages fehlgeschlagen: {latest['connection_error']}", icon=":material/link_off:")

st.space("medium")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("**Equity über die Zeit**")
        if df["current_equity"].notna().sum() >= 2:
            st.line_chart(df.set_index("date")["current_equity"])
        else:
            st.info("Braucht mindestens 2 Tage mit gültiger Equity für einen Verlauf.", icon=":material/info:")

with col2:
    with st.container(border=True):
        st.markdown("**Orders pro Tag**")
        if not df.empty:
            st.bar_chart(df.set_index("date")[["orders_sent", "orders_skipped", "orders_error"]])

st.space("medium")

with st.container(border=True):
    st.markdown("**Tages-Log**")
    display = df.copy()
    display["date"] = display["date"].dt.date
    st.dataframe(
        display.sort_values("date", ascending=False),
        hide_index=True,
        column_config={
            "date": st.column_config.DateColumn("Datum"),
            "runs": st.column_config.NumberColumn("Scans"),
            "orders_sent": st.column_config.NumberColumn("Gesendet"),
            "orders_skipped": st.column_config.NumberColumn("Übersprungen"),
            "orders_error": st.column_config.NumberColumn("Fehler"),
            "session_end_closes": st.column_config.NumberColumn("Session-Ende-Exits"),
            "symbols_traded": st.column_config.TextColumn("Symbole"),
            "current_equity": st.column_config.NumberColumn("Equity", format="%.2f"),
            "floating_pnl": st.column_config.NumberColumn("Floating P&L", format="%.2f"),
            "open_positions": st.column_config.TextColumn("Offene Positionen"),
            "connection_error": st.column_config.TextColumn("MT5-Fehler"),
        },
    )

latest_raw = RAW_DIR / f"{latest['date'].date()}.log"
if latest_raw.exists():
    with st.expander(f"Rohes Log vom {latest['date'].date()}"):
        st.code(latest_raw.read_text(encoding="utf-8"), language="text")
