"""CLS-Squeeze -- interactive dashboard for strategy/cls_squeeze.py.

Tests a market-microstructure hypothesis distinct from the ADX-VWAP paper's
own thesis: banks squaring CLS settlement funding in a daily cutoff window
(default 06:00-07:00 UTC) mechanically displace price, which should then
either revert toward VWAP (Reversion) or continue (Momentum) as London
liquidity comes online. Explicitly practitioner folklore, not an
academically-established result - tested empirically, not assumed.

See MEMORY (fx-vwap-adx-strategy-project) for the full honest finding.
"""

import altair as alt
import dukascopy_python
import pandas as pd

import streamlit as st
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.cls_squeeze import run_cls_squeeze_pipeline
from strategy.data import PAIRS
from strategy.metrics import equity_curve, summarize
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="CLS-Squeeze Backtest",
    page_icon=":material/schedule:",
    layout="wide",
)

START, END = "2016-07-28", "2026-07-28"
CUTOFF_START_HOUR, CUTOFF_END_HOUR, ENTRY_START_HOUR = 6.0, 7.0, 7.0

TIMEFRAMES = {
    "M5": dukascopy_python.INTERVAL_MIN_5,
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "M30": dukascopy_python.INTERVAL_MIN_30,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
}
# ~2.5h hold cap in bars, per timeframe.
MAX_HOLD_BARS = {"M5": 30, "M15": 10, "M30": 5, "H1": 3}

MODE_REVERSION = "Reversion (gegen die Verdrängung)"
MODE_MOMENTUM = "Momentum (mit der Verdrängung)"


@st.cache_data(ttl="1h", show_spinner="Lade Dukascopy-Historie...")
def load_raw(pair: str, timeframe: str) -> pd.DataFrame:
    return fetch_pair_history(pair, START, END, interval=TIMEFRAMES[timeframe])


@st.cache_data(ttl="1h", show_spinner="Berechne Indikatoren & Signal...")
def load_signaled(pair: str, timeframe: str, entry_end_hour: float, direction_mode: str) -> pd.DataFrame:
    df = load_raw(pair, timeframe)
    mode = "momentum" if direction_mode == MODE_MOMENTUM else "reversion"
    return run_cls_squeeze_pipeline(
        df,
        cutoff_start_hour=CUTOFF_START_HOUR, cutoff_end_hour=CUTOFF_END_HOUR,
        entry_start_hour=ENTRY_START_HOUR, entry_end_hour=entry_end_hour,
        direction_mode=mode,
    )


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(
    pair: str, timeframe: str, entry_end_hour: float, direction_mode: str,
    spread_bps: float, stop_atr_mult: float,
) -> pd.DataFrame:
    signaled = load_signaled(pair, timeframe, entry_end_hour, direction_mode)
    cfg = BacktestConfig(
        spread_bps=spread_bps, stop_atr_mult=stop_atr_mult,
        max_hold_bars=MAX_HOLD_BARS[timeframe],
        use_vwap_target=(direction_mode == MODE_REVERSION),
    )
    return simulate_trades(signaled, cfg)


with st.sidebar:
    st.markdown("### Konfiguration")
    pair = st.selectbox("Pair", PAIRS)
    timeframe = st.selectbox("Zeitrahmen", list(TIMEFRAMES), index=1)
    direction_mode = st.radio("Richtung", [MODE_REVERSION, MODE_MOMENTUM], index=1)
    entry_end_hour = st.slider(
        "Entry-Fenster-Ende (UTC)", 7.5, 10.0, 9.0, 0.5,
        help="Entry-Fenster beginnt 07:00 UTC (direkt nach dem CLS-Cutoff 06:00-07:00). "
        "Ein zu enges Fenster liefert zu wenige Trades für eine belastbare Aussage.",
    )
    spread_bps = st.slider("Round-trip Spread (bps)", 0.0, 3.0, 0.3, 0.1)
    stop_atr_mult = st.slider("Stop-Distanz (x ATR)", 0.1, 2.0, 0.5, 0.1)
    st.caption(
        "Datenquelle: echte Dukascopy-Historie, 2016-2026, auf Festplatte gecacht. "
        "VWAP läuft ab Tagesbeginn (00:00 UTC), Cutoff-Fenster 06:00-07:00 UTC."
    )

st.warning(
    "**Praktiker-Hypothese, kein etabliertes akademisches Ergebnis** (anders als "
    "die VWAP-Fair-Value-These des ADX-VWAP-Papers): Banken sollen vor dem täglichen "
    "CLS-Settlement-Cutoff (06:00-07:00 UTC) mechanischen Orderflow erzeugen, der Preise "
    "von VWAP wegdrückt. **Ehrlicher Befund** (EUR/USD, 9 Jahre Walk-Forward): bei engem "
    "Entry-Fenster zu wenige Trades für eine Aussage; bei breiterem Fenster (07:00-09:00) "
    "ist **Reversion klar negativ** (Sharpe -0.84, 863 Trades), **Momentum** deutlich "
    "weniger schlecht (Sharpe +0.21), aber immer noch **kein robuster Edge** — und das "
    "einzige auffällig gute Pair wechselt zwischen Testläufen (Zufalls-Muster, kein "
    "echter instrumentenspezifischer Effekt). Details: MEMORY / "
    "`scripts/research_cls_squeeze.py`.",
    icon=":material/warning:",
)

signaled = load_signaled(pair, timeframe, entry_end_hour, direction_mode)
trades = load_trades(pair, timeframe, entry_end_hour, direction_mode, spread_bps, stop_atr_mult)
summary = summarize(trades, signaled.index)

st.markdown(f"## :material/schedule: {pair} — {timeframe}, {direction_mode}")

with st.container(horizontal=True):
    st.metric("Sharpe (ann.)", f"{summary['sharpe']:.2f}", border=True)
    st.metric("Calmar", f"{summary['calmar']:.2f}", border=True)
    st.metric("Max drawdown", f"{summary['max_drawdown']:.2%}", border=True)
    st.metric("Win rate", f"{summary['win_rate']:.1%}", border=True)
    st.metric("Trades", summary["n_trades"], border=True)
    avg_bps = summary["avg_return_pct"] * 1e4 if pd.notna(summary["avg_return_pct"]) else float("nan")
    st.metric("Ø Return/Trade", f"{avg_bps:.2f} bps", border=True)

st.space("medium")

col1, col2 = st.columns([2, 1])
with col1:
    with st.container(border=True):
        st.markdown("**Equity-Kurve (verkettete Tagesrenditen)**")
        if summary["n_trades"] > 0:
            daily = trades_to_daily_returns(trades, signaled.index)
            curve = equity_curve(daily).rename("equity")
            curve.index.name = "date"
            curve = curve.reset_index()
            chart = (
                alt.Chart(curve)
                .mark_line(color="#4c78a8")
                .encode(
                    x=alt.X("date:T", title="Datum"),
                    y=alt.Y("equity:Q", title="Equity (Start = 1.0)", scale=alt.Scale(zero=False)),
                    tooltip=["date:T", alt.Tooltip("equity:Q", format=".4f")],
                )
                .properties(height=340)
            )
            st.altair_chart(chart)
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

with col2:
    with st.container(border=True):
        st.markdown("**Exit-Gründe**")
        if summary["n_trades"] > 0 and summary.get("exit_reason_counts"):
            reason_df = pd.Series(summary["exit_reason_counts"]).rename("count")
            reason_df.index.name = "reason"
            reason_df = reason_df.reset_index()
            st.altair_chart(
                alt.Chart(reason_df)
                .mark_arc()
                .encode(theta="count:Q", color=alt.Color("reason:N", title="Exit-Grund"), tooltip=["reason", "count"])
                .properties(height=340)
            )
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

st.space("medium")

with st.container(border=True):
    st.markdown("**Preis, VWAP, Cutoff-Fenster-Extremum & Einstiege (letzte Tage)**")
    n_days = st.slider("Anzahl Tage", 1, 20, 5, key=f"days_{pair}_{timeframe}")
    last_days = pd.Series(signaled.index.date).drop_duplicates().tail(n_days)
    window = signaled[pd.Series(signaled.index.date, index=signaled.index).isin(last_days)].reset_index(names="time")

    base = alt.Chart(window)
    price_lines = (
        base.transform_fold(["close", "vwap", "window_high", "window_low"], as_=["series", "value"])
        .mark_line()
        .encode(
            x=alt.X("time:T", title="Zeit"),
            y=alt.Y("value:Q", title="Preis", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N", title="Serie",
                scale=alt.Scale(
                    domain=["close", "vwap", "window_high", "window_low"],
                    range=["#333333", "#4c78a8", "#e45756", "#54a24b"],
                ),
            ),
            strokeDash=alt.condition(
                alt.FieldOneOfPredicate(field="series", oneOf=["window_high", "window_low"]),
                alt.value([4, 3]), alt.value([1, 0]),
            ),
        )
    )

    window_trades = (
        trades[(trades["entry_time"] >= window["time"].min()) & (trades["entry_time"] <= window["time"].max())]
        if not trades.empty else trades
    )
    layers = [price_lines]
    if not window_trades.empty:
        marker_df = window_trades.copy()
        marker_df["label"] = marker_df["direction"].map({1: "Long-Einstieg", -1: "Short-Einstieg"})
        layers.append(
            alt.Chart(marker_df)
            .mark_point(size=120, filled=True)
            .encode(
                x=alt.X("entry_time:T"),
                y=alt.Y("entry_price:Q"),
                shape=alt.Shape(
                    "label:N",
                    scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["triangle-up", "triangle-down"]),
                ),
                color=alt.Color(
                    "label:N",
                    scale=alt.Scale(domain=["Long-Einstieg", "Short-Einstieg"], range=["#54a24b", "#e45756"]),
                    legend=alt.Legend(title="Trades"),
                ),
                tooltip=["entry_time:T", "label", alt.Tooltip("entry_price:Q", format=".5f"), "exit_reason"],
            )
        )
    st.altair_chart(alt.layer(*layers).properties(height=380).resolve_scale(color="independent"))

st.space("medium")

with st.container(border=True):
    st.markdown("**Trade-Log**")
    if not trades.empty:
        display_trades = trades.copy()
        display_trades["direction"] = display_trades["direction"].map({1: "Long", -1: "Short"})
        display_trades["return_bps"] = display_trades["return_pct"] * 1e4
        st.dataframe(
            display_trades.sort_values("entry_time", ascending=False).drop(columns=["return_pct"]),
            hide_index=True,
            column_config={
                "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                "direction": st.column_config.TextColumn("Richtung"),
                "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.5f"),
                "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.5f"),
                "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                "exit_reason": st.column_config.TextColumn("Exit-Grund"),
                "hold_bars": st.column_config.NumberColumn("Haltedauer (Bars)"),
                "adx_at_entry": st.column_config.NumberColumn("ADX @ Entry", format="%.1f"),
                "atr_at_entry": st.column_config.NumberColumn("ATR @ Entry", format="%.5f"),
            },
        )
    else:
        st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")
