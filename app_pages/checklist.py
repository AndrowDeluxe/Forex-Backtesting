"""Checklist Strategy -- interactive dashboard for checklist_strategy/.

The user's own manually-backtested 4-indicator setup: Nadaraya-Watson
Envelope breakout -> RSI Multi-Length [LuxAlgo] confirmation -> RSI(14)+
SMA(14) crossover entry -> ATR(3)x2.5 stop, fixed 1:2 R:R, breakeven at 1:1.
Unlike the other strategies here, overlapping positions are allowed by
design (see checklist_strategy/backtest.py).

See MEMORY (fx-vwap-adx-strategy-project) for the full honest finding.
"""

import altair as alt
import dukascopy_python
import pandas as pd

import streamlit as st
from checklist_strategy.backtest import simulate_checklist_trades
from checklist_strategy.pipeline import run_checklist_pipeline
from strategy.data import PAIRS
from strategy.metrics import equity_curve, summarize
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="Checklist Strategy Backtest",
    page_icon=":material/checklist:",
    layout="wide",
)

START, END = "2016-07-28", "2026-07-28"
TIMEFRAMES = {
    "M15": dukascopy_python.INTERVAL_MIN_15,
    "H1": dukascopy_python.INTERVAL_HOUR_1,
    "H4": dukascopy_python.INTERVAL_HOUR_4,
}

REGIME_NONE = "Kein Regime-Filter (Baseline)"
REGIME_ADX = "Nur ADX<25 (nicht stark trendend)"
REGIME_VOL = "Nur Volatilität über eigenem Median"
REGIME_BOTH = "Beide kombiniert"


@st.cache_data(ttl="1h", show_spinner="Lade Dukascopy-Historie...")
def load_raw(pair: str, timeframe: str) -> pd.DataFrame:
    return fetch_pair_history(pair, START, END, interval=TIMEFRAMES[timeframe])


@st.cache_data(ttl="1h", show_spinner="Berechne Indikatoren & Checkliste...")
def load_signaled(pair: str, timeframe: str, regime_choice: str) -> pd.DataFrame:
    df = load_raw(pair, timeframe)
    use_filter = regime_choice != REGIME_NONE
    require_trend = regime_choice in (REGIME_ADX, REGIME_BOTH)
    require_vol = regime_choice in (REGIME_VOL, REGIME_BOTH)
    return run_checklist_pipeline(
        df,
        use_regime_filter=use_filter,
        regime_require_not_trending=require_trend,
        regime_require_volatile=require_vol,
    )


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(pair: str, timeframe: str, regime_choice: str, spread_bps: float, stop_atr_mult: float) -> pd.DataFrame:
    signaled = load_signaled(pair, timeframe, regime_choice)
    return simulate_checklist_trades(signaled, spread_bps=spread_bps, stop_atr_mult=stop_atr_mult)


with st.sidebar:
    st.markdown("### Konfiguration")
    pair = st.selectbox("Pair", PAIRS)
    timeframe = st.selectbox("Zeitrahmen", list(TIMEFRAMES), index=0)
    regime_choice = st.radio("Regime-Filter", [REGIME_NONE, REGIME_ADX, REGIME_VOL, REGIME_BOTH])
    spread_bps = st.slider("Round-trip Spread (bps)", 0.0, 3.0, 0.3, 0.1)
    stop_atr_mult = st.slider("Stop-Distanz (x ATR(3))", 0.5, 5.0, 2.5, 0.25)
    st.caption(
        "Datenquelle: echte Dukascopy-Historie, 2016-2026, auf Festplatte "
        "gecacht. Envelope-Fenster (500 Bars) ist eine Annahme, nicht aus "
        "TradingView bestätigt - siehe Warnhinweis oben."
    )

st.warning(
    "**Erster systematischer Test dieser manuell gebackteten Strategie.** "
    "Baseline (EUR/USD, M15, kein Filter): 1265 Trades über 10 Jahre, "
    "**Sharpe -0.14**, Win-Rate 24% (bräuchte ~33% für Break-even bei 1:2 R:R). "
    "**Regime-Filter \"ADX<25\"** reduziert auf nur 30 Trades — sieht gepoolt "
    "gut aus (Sharpe +0.33), aber der Mittelwert der Jahres-Sharpes ist "
    "**-0.09** mit 4 von 9 Jahren bei 0% Trefferquote — zu dünn, um zu vertrauen. "
    "Strukturgrund: die Checkliste feuert überproportional bei bereits "
    "erhöhtem ADX, daher schließen sich \"Checkliste feuert\" und \"ADX niedrig\" "
    "gegenseitig weitgehend aus. Details: MEMORY / `scripts/research_checklist_strategy.py`.",
    icon=":material/warning:",
)

signaled = load_signaled(pair, timeframe, regime_choice)
trades = load_trades(pair, timeframe, regime_choice, spread_bps, stop_atr_mult)
summary = summarize(trades, signaled.index)

st.markdown(f"## :material/checklist: {pair} — {timeframe}, {regime_choice}")

with st.container(horizontal=True):
    st.metric("Sharpe (ann.)", f"{summary['sharpe']:.2f}", border=True)
    st.metric("Calmar", f"{summary['calmar']:.2f}", border=True)
    st.metric("Max drawdown", f"{summary['max_drawdown']:.2%}", border=True)
    st.metric("Win rate", f"{summary['win_rate']:.1%}", border=True)
    st.metric("Trades", summary["n_trades"], border=True)
    avg_bps = summary["avg_return_pct"] * 1e4 if pd.notna(summary["avg_return_pct"]) else float("nan")
    st.metric("Ø Return/Trade", f"{avg_bps:.2f} bps", border=True)

if summary["n_trades"] > 0 and summary["n_trades"] < 100:
    st.info(
        f"Nur {summary['n_trades']} Trades bei dieser Konfiguration — Kennzahlen "
        "sind bei so kleiner Stichprobe kaum von Zufall zu unterscheiden.",
        icon=":material/info:",
    )

st.space("medium")

col1, col2 = st.columns([2, 1])
with col1:
    with st.container(border=True):
        st.markdown("**Equity-Kurve (verkettete Tagesrenditen)**")
        if summary["n_trades"] > 0:
            daily = trades.groupby(trades["exit_time"].dt.floor("D"))["return_pct"].apply(
                lambda r: (1 + r).prod() - 1
            )
            days = pd.date_range(signaled.index.min().normalize(), signaled.index.max().normalize(), freq="D")
            daily = daily.reindex(days, fill_value=0.0)
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
    st.markdown("**Preis, Envelope & Einstiege (letzte Tage)**")
    n_days = st.slider("Anzahl Tage", 1, 30, 5, key=f"days_{pair}_{timeframe}")
    last_days = pd.Series(signaled.index.date).drop_duplicates().tail(n_days)
    window = signaled[pd.Series(signaled.index.date, index=signaled.index).isin(last_days)].reset_index(names="time")

    base = alt.Chart(window)
    price_lines = (
        base.transform_fold(["close", "env_mid", "env_upper", "env_lower"], as_=["series", "value"])
        .mark_line()
        .encode(
            x=alt.X("time:T", title="Zeit"),
            y=alt.Y("value:Q", title="Preis", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N", title="Serie",
                scale=alt.Scale(
                    domain=["close", "env_mid", "env_upper", "env_lower"],
                    range=["#333333", "#4c78a8", "#e45756", "#54a24b"],
                ),
            ),
            strokeDash=alt.condition(
                alt.FieldOneOfPredicate(field="series", oneOf=["env_upper", "env_lower"]),
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
                "moved_to_be": st.column_config.CheckboxColumn("Auf BE verschoben"),
            },
        )
    else:
        st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")
