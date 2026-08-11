"""Pre-Settle Range Breakout -- interactive dashboard for presettle_breakout/.

User's own manual observation (2026-08-10), tested here for the first time -
not from a paper. EUR/USD M5: range = high/low from 06:00 Europe/Berlin (the
"pre-settle" window already documented in strategy/cls_advanced.py's CLS
Advanced framework) through the first confirmed local M5 swing high/low
("fractal") at or after 07:00 - matches the user's own chart illustration
(2026-08-10) of a Pre-Settle-range break followed by a Settle-window swing
point. The moment that pivot is confirmed, a resting Buy-Stop/Sell-Stop OCO
pair is armed at the range high/low. Stop-loss = 2x ATR(14) on M5 (measured
at the range close, no lookahead), take-profit = fixed 1:2 risk/reward. An
order unfilled by 12:00 Berlin is invalidated - no trade that day. A
fixed-clock-window mode is also available for comparison. See
presettle_breakout/engine.py for the exact fidelity choices.

Default view is the CURRENT month only, per the user's own request to test
this "quick and dirty" before running the full history - toggle to full
history in the sidebar.
"""

from datetime import date, timedelta

import pandas as pd

import streamlit as st
from presettle_breakout.chart import build_entry_chart
from presettle_breakout.data import fetch_m5_berlin
from presettle_breakout.engine import simulate_presettle_breakout
from strategy.metrics import trade_stats

st.set_page_config(page_title="Pre-Settle Range Breakout", page_icon=":material/wb_twilight:", layout="wide")

FULL_START, FULL_END = "2016-07-28", "2026-08-11"


@st.cache_data(ttl="1h", show_spinner="Lade EUR/USD M5-Daten (Dukascopy, Berlin-Zeit)...")
def load_data(start: str, end: str) -> pd.DataFrame:
    return fetch_m5_berlin("EURUSD", start, end)


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(
    start: str, end: str, rr: float, atr_period: int, atr_mult: float, cutoff: str, spread_bps: float,
    range_end_mode: str, range_end: str, pivot_after: str,
) -> pd.DataFrame:
    df = load_data(start, end)
    return simulate_presettle_breakout(
        df, entry_cutoff=cutoff, atr_period=atr_period, atr_mult=atr_mult, rr=rr, spread_bps=spread_bps,
        range_end_mode=range_end_mode, range_end=range_end, pivot_after=pivot_after,
    )


MODE_PIVOT = "Erstes lokales Hoch/Tief (M5) nach 07:00"
MODE_FIXED = "Feste Uhrzeit"

with st.sidebar:
    st.markdown("### Konfiguration")
    scope = st.radio("Zeitraum", ["Nur aktueller Monat", "Volle Historie"], index=0)
    mode_label = st.radio("Range-Ende", [MODE_PIVOT, MODE_FIXED], index=0)
    range_end_mode = "first_pivot" if mode_label == MODE_PIVOT else "fixed"
    if range_end_mode == "first_pivot":
        pivot_after = st.text_input("Frühester Pivot-Zeitpunkt (Berlin-Zeit, HH:MM)", "07:00")
        range_end = "08:30"  # unused in this mode
    else:
        range_end = st.text_input("Range-Ende (Berlin-Zeit, HH:MM)", "08:30")
        pivot_after = "07:00"  # unused in this mode
    rr = st.slider("Take-Profit (Risk/Reward)", 1.0, 4.0, 2.0, 0.5)
    atr_period = st.slider("ATR-Periode (M5)", 5, 30, 14, 1)
    atr_mult = st.slider("Stop-Distanz (x ATR)", 0.5, 4.0, 2.0, 0.5)
    cutoff = st.text_input("Entry-Cutoff (Berlin-Zeit, HH:MM)", "12:00")
    spread_bps = st.slider("Round-trip Spread (bps)", 0.0, 3.0, 0.3, 0.1)
    st.caption("Datenquelle: Dukascopy EUR/USD M5, Europe/Berlin lokal, gecacht.")

if scope == "Nur aktueller Monat":
    today = date.today()
    month_start = today.replace(day=1)
    fetch_start = (month_start - timedelta(days=5)).isoformat()  # ATR(14) warmup buffer
    fetch_end = (today + timedelta(days=1)).isoformat()
    display_start = pd.Timestamp(month_start, tz="Europe/Berlin")
else:
    fetch_start, fetch_end = FULL_START, FULL_END
    display_start = pd.Timestamp(FULL_START, tz="Europe/Berlin")

df = load_data(fetch_start, fetch_end)
trades = load_trades(
    fetch_start, fetch_end, rr, atr_period, atr_mult, cutoff, spread_bps,
    range_end_mode, range_end, pivot_after,
)
trades = trades[trades["entry_time"] >= display_start] if not trades.empty else trades

st.markdown("## :material/wb_twilight: Pre-Settle Range Breakout (EUR/USD, M5)")
range_desc = (
    f"Range 06:00 bis zum ersten lokalen M5-Hoch/Tief ab {pivot_after} (Berlin)"
    if range_end_mode == "first_pivot"
    else f"Range 06:00-{range_end} (Berlin)"
)
st.info(
    f"**Eigene Beobachtung, kein etabliertes Setup** - erste Auswertung. {range_desc}, "
    "Ausbruch danach gehandelt, SL = 2x ATR(14) M5, TP = fix 1:2 RR, Entries nach "
    "12:00 verfallen ungenutzt.",
    icon=":material/info:",
)

stats = trade_stats(trades)
with st.container(horizontal=True):
    st.metric("Trades", stats["n_trades"], border=True)
    st.metric("Win-Rate", f"{stats['win_rate']:.1%}" if pd.notna(stats["win_rate"]) else "n/a", border=True)
    pf = stats["profit_factor"]
    st.metric("Profit Factor", f"{pf:.2f}" if pd.notna(pf) and pf not in (0, float("inf")) else "n/a", border=True)
    avg_bps = stats["avg_return_pct"] * 1e4 if pd.notna(stats["avg_return_pct"]) else float("nan")
    st.metric("Ø Return/Trade", f"{avg_bps:.1f} bps" if pd.notna(avg_bps) else "n/a", border=True)

st.space("medium")

if trades.empty:
    st.warning("Keine Trades in diesem Zeitraum.", icon=":material/warning:")
else:
    with st.container(border=True):
        st.markdown("**Chart: Range, Entry/Exit-Level, Trades**")
        chart_days = pd.Series(df.index.date).drop_duplicates()
        chart_days = chart_days[chart_days >= display_start.date()]
        n_days = st.slider("Anzahl Tage im Chart", 1, max(int(len(chart_days)), 1), min(10, max(int(len(chart_days)), 1)))
        shown_days = chart_days.tail(n_days)
        window_df = df[pd.Series(df.index.date, index=df.index).isin(shown_days)]
        window_trades = trades[trades["window_start"].dt.date.isin(shown_days)]
        st.altair_chart(build_entry_chart(window_df, window_trades))

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Trade-Log**")
        display_trades = trades.copy()
        display_trades["return_bps"] = display_trades["return_pct"] * 1e4
        st.dataframe(
            display_trades.sort_values("entry_time", ascending=False).drop(columns=["return_pct"]),
            hide_index=True,
            column_config={
                "window_start": st.column_config.DatetimeColumn("Range-Start", format="YYYY-MM-DD HH:mm"),
                "window_end": st.column_config.DatetimeColumn("Range-Ende", format="YYYY-MM-DD HH:mm"),
                "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                "direction": st.column_config.TextColumn("Richtung"),
                "entry_price": st.column_config.NumberColumn("Entry", format="%.5f"),
                "sl": st.column_config.NumberColumn("Stop", format="%.5f"),
                "tp": st.column_config.NumberColumn("Ziel", format="%.5f"),
                "exit_price": st.column_config.NumberColumn("Exit", format="%.5f"),
                "range_high": st.column_config.NumberColumn("Range-Hoch", format="%.5f"),
                "range_low": st.column_config.NumberColumn("Range-Tief", format="%.5f"),
                "range_width": st.column_config.NumberColumn("Range-Breite", format="%.5f"),
                "atr_m5_at_entry": st.column_config.NumberColumn("ATR(M5) @ Entry", format="%.5f"),
                "exit_reason": st.column_config.TextColumn("Exit-Grund"),
                "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                "hold_bars": st.column_config.NumberColumn("Haltedauer (Bars)"),
            },
        )
