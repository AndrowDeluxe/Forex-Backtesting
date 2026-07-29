"""Live Logs -- OU-Modell: read-only view of the live (real-money) OU-Modell
signal-bot's daily performance, collected by
scripts/collect_ou_modell_daily_log.py and committed to
ou_modell_logs/daily_log.csv (the bot itself, its local logs, state DB and
the MT5 terminal live outside this repo on the user's machine and aren't
reachable from Streamlit Cloud - this page only ever reads the committed
CSV/raw logs, never connects to MT5 or touches an order).

First live trading day: 2026-07-29. Intentionally no performance verdict
here while the sample is this small - the point is to accumulate ~a month
of daily rows before drawing any conclusion, same discipline as every
backtest finding in this project.
"""

from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="OU-Modell -- Live Logs", page_icon=":material/monitoring:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_DIR / "ou_modell_logs" / "daily_log.csv"
RAW_DIR = REPO_DIR / "ou_modell_logs" / "raw"

st.markdown("## :material/monitoring: OU-Modell -- Live-Trading-Log")

st.info(
    "**Live-Konto, echtes Geld.** Ein gehosteter OU-Modell-Signal-Scanner sendet "
    "Long-Setups automatisch an ein MT5-Live-Konto (Windows Task Scheduler, drei "
    "Scans/Tag). Seit **29.07.2026** laufen echte Orders (davor nur Dry-Run-Tests). "
    "Diese Seite zeigt nur committete Tageswerte -- kein Live-Zugriff auf MT5 von "
    "hier aus. **Noch keine Auswertung/Verdict**: das kommt erst nach ~einem Monat "
    "gesammelter Tage, dieselbe Disziplin wie bei jedem Backtest in diesem Projekt.",
    icon=":material/warning:",
)

if not CSV_PATH.exists():
    st.warning(
        "Noch keine Tages-Logs vorhanden. Der erste Eintrag wird nach dem "
        "letzten täglichen Scan (21:30 Uhr) über "
        "`scripts/collect_ou_modell_daily_log.py` ergänzt.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

df = pd.read_csv(CSV_PATH, parse_dates=["date"])
df = df.sort_values("date")

n_days = len(df)
st.caption(f"{n_days} Tag{'e' if n_days != 1 else ''} erfasst seit {df['date'].min().date()}.")

latest = df.iloc[-1]
with st.container(horizontal=True):
    st.metric("Letzter Kontostand (Equity)", f"{latest['current_equity']:,.2f}" if pd.notna(latest["current_equity"]) else "n/a", border=True)
    pnl = latest["daily_pnl_pct"]
    st.metric("Tagesergebnis", f"{pnl:+.2%}" if pd.notna(pnl) else "n/a", border=True)
    st.metric("Signale heute gescannt", int(latest["signals_scanned"]) if pd.notna(latest["signals_scanned"]) else "n/a", border=True)
    st.metric("Orders gesendet", int(latest["orders_sent"]) if pd.notna(latest["orders_sent"]) else "n/a", border=True)
    st.metric("Übersprungen", int(latest["orders_skipped"]) if pd.notna(latest["orders_skipped"]) else "n/a", border=True)

if bool(latest.get("drawdown_halted")):
    st.error("Tages-Drawdown-Stopp hat am letzten erfassten Tag gegriffen -- keine neuen Orders mehr in diesem Lauf.", icon=":material/dangerous:")

if isinstance(latest.get("connection_error"), str) and latest["connection_error"]:
    st.warning(f"MT5-Verbindung beim Erfassen dieses Tages fehlgeschlagen: {latest['connection_error']} -- Equity-Werte ggf. unvollständig.", icon=":material/link_off:")

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
            "signals_scanned": st.column_config.NumberColumn("Gescannt"),
            "orders_sent": st.column_config.NumberColumn("Gesendet"),
            "orders_skipped": st.column_config.NumberColumn("Übersprungen"),
            "orders_error": st.column_config.NumberColumn("Fehler"),
            "symbols_sent": st.column_config.TextColumn("Symbole (gesendet)"),
            "baseline_equity": st.column_config.NumberColumn("Baseline-Equity", format="%.2f"),
            "current_equity": st.column_config.NumberColumn("Equity", format="%.2f"),
            "floating_pnl": st.column_config.NumberColumn("Floating P&L", format="%.2f"),
            "daily_pnl_pct": st.column_config.NumberColumn("Tagesergebnis", format="%.2%%"),
            "open_positions": st.column_config.TextColumn("Offene Positionen"),
            "drawdown_halted": st.column_config.CheckboxColumn("DD-Stopp"),
            "connection_error": st.column_config.TextColumn("MT5-Fehler"),
        },
    )

latest_raw = RAW_DIR / f"{latest['date'].date()}.log"
if latest_raw.exists():
    with st.expander(f"Rohes Bot-Log vom {latest['date'].date()}"):
        st.code(latest_raw.read_text(encoding="utf-8"), language="text")
