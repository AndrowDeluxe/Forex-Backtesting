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

import altair as alt
import pandas as pd

import streamlit as st
from combined_strategy.data import fetch_timeframe

st.set_page_config(page_title="ORB Forward-Test -- Live Logs", page_icon=":material/bolt:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = REPO_DIR / "orb_forward_test_logs" / "daily_log.csv"
TRADES_CSV_PATH = REPO_DIR / "orb_forward_test_logs" / "trades.csv"
RAW_DIR = REPO_DIR / "orb_forward_test_logs" / "raw"

# MT5-Symbol (Demokonto) -> Dukascopy-Instrument-Key (combined_strategy.data),
# fuer den Preis-Hintergrund des Kerzencharts - der Chart selbst kann nicht
# live gegen MT5 gehen (siehe Modul-Docstring), nutzt also dieselbe
# Dukascopy-Quelle wie der Rest des Dashboards.
SYMBOL_TO_DUKASCOPY = {"USTEC": "NASDAQ", "US500": "SP500"}


@st.cache_data(ttl="15m", show_spinner="Lade Kerzen-Daten...")
def load_candles(mt5_symbol: str, start: str, end: str) -> pd.DataFrame:
    duka_key = SYMBOL_TO_DUKASCOPY[mt5_symbol]
    df = fetch_timeframe(duka_key, "M15", start, end)
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})

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

with st.container(border=True):
    st.markdown("**Kerzenchart mit Einstiegen**")
    symbol = st.selectbox("Symbol", list(SYMBOL_TO_DUKASCOPY), key="candle_symbol")

    trades_df = pd.DataFrame()
    if TRADES_CSV_PATH.exists():
        all_trades = pd.read_csv(TRADES_CSV_PATH, parse_dates=["executed_at"])
        trades_df = all_trades[all_trades["symbol"] == symbol]

    today = pd.Timestamp.now("UTC").normalize()
    if not trades_df.empty:
        start = (trades_df["executed_at"].min().normalize() - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        end = (max(trades_df["executed_at"].max().normalize(), today) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start = (today - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        candles = load_candles(symbol, start, end)
    except Exception as e:  # Dukascopy kann fuer die juengsten Stunden noch keine Daten haben
        candles = pd.DataFrame()
        st.info(f"Kerzen-Daten (noch) nicht verfuegbar: {e}", icon=":material/info:")

    if candles.empty:
        st.info("Keine Kerzen-Daten fuer diesen Zeitraum.", icon=":material/info:")
    else:
        window = candles.reset_index(names="time")
        base = alt.Chart(window).encode(x=alt.X("time:T", title="Zeit"))
        bullish = alt.condition("datum.close >= datum.open", alt.value("#26a69a"), alt.value("#ef5350"))
        wick = base.mark_rule().encode(y=alt.Y("low:Q", title="Preis", scale=alt.Scale(zero=False)), y2="high:Q", color=bullish)
        body = base.mark_bar(size=3).encode(y="open:Q", y2="close:Q", color=bullish)
        layers = [wick, body]

        if not trades_df.empty:
            marker_df = trades_df.copy()
            marker_df["label"] = marker_df["direction"].map({"Long": "Long-Einstieg"}).fillna(marker_df["direction"])
            layers.append(
                alt.Chart(marker_df)
                .mark_point(shape="triangle-up", size=220, filled=True, color="#2ca02c")
                .encode(
                    x="executed_at:T", y="entry_price:Q",
                    tooltip=["executed_at:T", "symbol", alt.Tooltip("entry_price:Q", format=".2f"), alt.Tooltip("stop_price:Q", format=".2f"), "dry_run"],
                )
            )
        st.altair_chart(alt.layer(*layers).properties(height=420).interactive())
        if trades_df.empty:
            st.caption("Noch keine Trades fuer dieses Symbol - Chart zeigt nur den Preisverlauf.")

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
