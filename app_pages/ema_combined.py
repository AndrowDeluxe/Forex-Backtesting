"""EMA Combined -- interactive dashboard for combined_strategy.

Same EMA S/R core (weekly/daily bias + H4 rejection) as app_pages/ema_sr.py,
plus three optional additions transferred from the ADX-VWAP paper's
theoretical framework: a VWAP-overextension entry filter (A), a
prior-session-extreme confluence entry filter (B), and an ADX-exhaustion
exit (C). Data is real Dukascopy H4/D1/W1 history (~10 years, cached to
disk), across the paper's 6 FX pairs plus Gold, Silver, S&P 500, Nasdaq-100
and Oil -- not yfinance's 730-day hourly cap.

See MEMORY (fx-vwap-adx-strategy-project) for the full honest research
history behind the numbers shown here.
"""

import altair as alt
import pandas as pd

import streamlit as st
from combined_strategy.data import INSTRUMENTS, fetch_multi_timeframe
from combined_strategy.pipeline import EMA_LENGTH, EMA_SMOOTH, run_pipeline
from ema_strategy.indicators import double_ema

st.set_page_config(
    page_title="EMA Combined Backtest",
    page_icon=":material/merge:",
    layout="wide",
)

START, END = "2016-07-28", "2026-07-28"
IN_SAMPLE_FRAC = 0.7

CONFIGS = {
    "Baseline (unveränderte EMA S/R)": dict(),
    "+A VWAP-Überdehnungsfilter": dict(use_vwap_filter=True, vwap_theta_window_bars=250, vwap_theta_multiplier=1.0),
    "+B Session-Extreme-Konfluenz": dict(use_session_confluence_filter=True, confluence_atr_mult=1.0),
    "+C ADX-Erschöpfungs-Exit": dict(
        exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0, adx_exhaustion_confirm_bars=2
    ),
    "+A+B+C kombiniert": dict(
        use_vwap_filter=True, vwap_theta_window_bars=250, vwap_theta_multiplier=1.0,
        use_session_confluence_filter=True, confluence_atr_mult=1.0,
        exit_on_adx_exhaustion=True, adx_exhaustion_entry_threshold=25.0, adx_exhaustion_confirm_bars=2,
    ),
}


@st.cache_data(ttl="1h", show_spinner="Lade Dukascopy-Historie...")
def load_instrument_data(key: str):
    return fetch_multi_timeframe(key, START, END)


def split_h4(h4: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "full":
        return h4
    cut = int(len(h4) * IN_SAMPLE_FRAC)
    return h4.iloc[:cut] if split == "is" else h4.iloc[cut:]


@st.cache_data(ttl="1h", show_spinner=False)
def run_cached(key: str, split: str, config_name: str):
    h4, daily, weekly = load_instrument_data(key)
    h4_split = split_h4(h4, split)
    signals, trades, equity, metrics = run_pipeline(h4_split, daily, weekly, **CONFIGS[config_name])
    return signals, trades, equity, metrics, daily, h4_split.index.min(), h4_split.index.max()


@st.cache_data(ttl="1h", show_spinner="Berechne Vergleichstabelle über alle Instrumente...")
def comparison_table(split: str) -> pd.DataFrame:
    rows = []
    for config_name in CONFIGS:
        for key in INSTRUMENTS:
            _, _, _, m, _, _, _ = run_cached(key, split, config_name)
            rows.append(
                {
                    "Konfiguration": config_name,
                    "Instrument": key,
                    "Trades": m.get("Anzahl Trades", 0),
                    "Profit Factor": m.get("Profit Factor"),
                    "Ø R-Multiple": m.get("Ø R-Multiple"),
                    "Buy & Hold %": m.get("Buy & Hold %"),
                    "Alpha %": m.get("Alpha vs. Buy & Hold %"),
                }
            )
    return pd.DataFrame(rows)


def metric_row(metrics: dict) -> None:
    if metrics.get("Anzahl Trades", 0) == 0:
        st.info("Keine Trades in diesem Zeitraum.", icon=":material/info:")
        return
    with st.container(horizontal=True):
        st.metric("Trades", f"{metrics['Anzahl Trades']:.0f}", border=True)
        st.metric("Trefferquote", f"{metrics['Trefferquote %']:.1f}%", border=True)
        st.metric("Profit factor", f"{metrics['Profit Factor']:.2f}", border=True)
        st.metric("Ø R-Multiple", f"{metrics['Ø R-Multiple']:.2f}", border=True)
        st.metric(
            "Gesamtrendite", f"{metrics['Gesamtrendite %']:.1f}%", border=True,
            delta=(
                f"{metrics['Alpha vs. Buy & Hold %']:+.1f}%pt vs. B&H"
                if "Alpha vs. Buy & Hold %" in metrics and not pd.isna(metrics["Alpha vs. Buy & Hold %"])
                else None
            ),
        )
        st.metric("Max drawdown", f"{metrics['Max Drawdown %']:.1f}%", border=True)
    if "Buy & Hold %" in metrics and not pd.isna(metrics["Buy & Hold %"]):
        st.caption(
            f"Buy & Hold über denselben Zeitraum: {metrics['Buy & Hold %']:+.1f}% — "
            "auf trendstarken Instrumenten (Gold, Indizes) ist das oft schwer zu schlagen."
        )


def price_entry_chart(daily: pd.DataFrame, trades: pd.DataFrame, window_start, height: int = 380) -> alt.LayerChart:
    ema_series = double_ema(daily["Close"], EMA_LENGTH, EMA_SMOOTH)
    mask = daily.index >= window_start
    price_df = pd.DataFrame(
        {"Date": daily.index[mask], "Close": daily["Close"][mask].to_numpy(), "EMA": ema_series[mask].to_numpy()}
    )

    price_line = alt.Chart(price_df).mark_line(color="#5c5c5c", strokeWidth=1).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Close:Q", title=None, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("Date:T"), alt.Tooltip("Close:Q", format=",.4f")],
    )
    ema_line = alt.Chart(price_df).mark_line(color="#e8590c", strokeWidth=2).encode(x="Date:T", y="EMA:Q")
    layers = [price_line, ema_line]

    if not trades.empty:
        window_trades = trades[trades["entry_time"] >= window_start]
        longs = window_trades[window_trades["direction"] == "LONG"]
        shorts = window_trades[window_trades["direction"] == "SHORT"]
        if not longs.empty:
            layers.append(
                alt.Chart(longs)
                .mark_point(shape="triangle-up", size=90, filled=True, color="#2f9e44")
                .encode(
                    x="entry_time:T", y="entry:Q",
                    tooltip=[
                        alt.Tooltip("entry_time:T", title="Einstieg"),
                        alt.Tooltip("entry:Q", format=",.4f"),
                        alt.Tooltip("pnl:Q", format=",.2f"),
                    ],
                )
            )
        if not shorts.empty:
            layers.append(
                alt.Chart(shorts)
                .mark_point(shape="triangle-down", size=90, filled=True, color="#e03131")
                .encode(
                    x="entry_time:T", y="entry:Q",
                    tooltip=[
                        alt.Tooltip("entry_time:T", title="Einstieg"),
                        alt.Tooltip("entry:Q", format=",.4f"),
                        alt.Tooltip("pnl:Q", format=",.2f"),
                    ],
                )
            )
    return alt.layer(*layers).properties(height=height).interactive()


def equity_chart(equity: pd.Series, height: int = 220) -> alt.Chart:
    eq_df = pd.DataFrame({"Date": equity.index, "Equity": equity.to_numpy()})
    return (
        alt.Chart(eq_df)
        .mark_line(color="#1f6feb")
        .encode(
            x=alt.X("Date:T", title=None),
            y=alt.Y("Equity:Q", title=None, scale=alt.Scale(zero=False)),
            tooltip=[alt.Tooltip("Date:T"), alt.Tooltip("Equity:Q", format=",.0f")],
        )
        .properties(height=height)
    )


def trades_table(trades: pd.DataFrame) -> None:
    if trades.empty:
        return
    with st.container(border=True):
        st.markdown("**Trades**")
        st.dataframe(
            trades.sort_values("entry_time", ascending=False),
            hide_index=True,
            column_config={
                "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                "direction": st.column_config.TextColumn("Richtung"),
                "entry": st.column_config.NumberColumn("Entry", format="%.4f"),
                "exit": st.column_config.NumberColumn("Exit", format="%.4f"),
                "sl": st.column_config.NumberColumn("SL", format="%.4f"),
                "tp": st.column_config.NumberColumn("TP", format="%.4f"),
                "pnl": st.column_config.NumberColumn("P&L", format="%.2f"),
                "r_multiple": st.column_config.NumberColumn("R", format="%.2f"),
                "reason": st.column_config.TextColumn("Exit-Grund"),
            },
        )


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("### Auswahl")
    instrument = st.selectbox("Instrument", list(INSTRUMENTS))
    config_name = st.segmented_control("Konfiguration", options=list(CONFIGS), default="Baseline (unveränderte EMA S/R)")
    if config_name is None:
        config_name = "Baseline (unveränderte EMA S/R)"
    split_label = st.radio("Zeitraum", options=["Gesamter Datensatz", "In-Sample (70%)", "Out-of-Sample (30%)"])
    st.caption(
        "Datenquelle: echte Dukascopy-Historie (H4/D1/W1), 2016-2026, "
        "auf Festplatte gecacht. 6 FX-Paare aus dem Paper plus Gold, "
        "Silber, S&P 500, Nasdaq-100, Öl."
    )

split_map = {"Gesamter Datensatz": "full", "In-Sample (70%)": "is", "Out-of-Sample (30%)": "oos"}
split = split_map[split_label]

if config_name != "Baseline (unveränderte EMA S/R)":
    st.warning(
        "**Keine der drei Erweiterungen zeigt einzeln einen überzeugenden Out-of-Sample-"
        "Vorteil** gegenüber der Baseline (siehe Tab **Vergleich**). Kombiniert wirken die "
        "Durchschnittswerte besser, aber bei deutlich weniger Trades und weniger profitablen "
        "Instrumenten — eher ein Zeichen kleinerer, konzentrierter Stichproben als ein echter "
        "Edge.",
        icon=":material/warning:",
    )

# =============================================================================
# Tabs
# =============================================================================

tab_backtest, tab_comparison = st.tabs(["Backtest", "Vergleich"])

with tab_backtest:
    st.markdown(f"## :material/merge: {instrument} — {config_name}, {split_label}")

    signals, trades, equity, metrics, daily, win_start, win_end = run_cached(instrument, split, config_name)
    metric_row(metrics)

    with st.container(border=True):
        st.markdown("**Equity-Kurve**")
        st.altair_chart(equity_chart(equity))

    with st.container(border=True):
        st.markdown("**Kurs, Daily-EMA (S/R) & Einstiege**")
        chart_window_start = win_start - pd.Timedelta(days=45)
        st.altair_chart(price_entry_chart(daily, trades, chart_window_start))

    trades_table(trades)

with tab_comparison:
    st.markdown("## :material/table_chart: Alle Konfigurationen × alle Instrumente")
    st.warning(
        "**Kernbefund:** Auf trendstarken Instrumenten (Gold, Silber, S&P 500, Nasdaq) "
        "unterliegt die Strategie in jeder Konfiguration deutlich einem simplen Buy & Hold "
        "(Alpha oft -40 bis -125 Prozentpunkte) — die hohe Rohrendite dort ist Beta "
        "(steigender Markt), nicht Strategie-Skill. Echte, wenn auch bescheidene, positive "
        "Alpha zeigt sich vor allem bei einzelnen FX-Paaren. Details siehe MEMORY / "
        "`scripts/research_alpha_check.py`.",
        icon=":material/warning:",
    )

    comp_split_label = st.radio(
        "Zeitraum für die Vergleichstabelle", options=["In-Sample (70%)", "Out-of-Sample (30%)"],
        horizontal=True, key="comp_split",
    )
    comp_split = "is" if comp_split_label == "In-Sample (70%)" else "oos"

    comp_df = comparison_table(comp_split)
    st.dataframe(
        comp_df,
        hide_index=True,
        column_config={
            "Profit Factor": st.column_config.NumberColumn(format="%.2f"),
            "Ø R-Multiple": st.column_config.NumberColumn(format="%.2f"),
            "Buy & Hold %": st.column_config.NumberColumn(format="%.1f%%"),
            "Alpha %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.markdown("### Aggregiert je Konfiguration")
    agg = comp_df.groupby("Konfiguration").agg(
        Trades_gesamt=("Trades", "sum"),
        Ø_Profit_Factor=("Profit Factor", "mean"),
        Ø_R_Multiple=("Ø R-Multiple", "mean"),
        Ø_Alpha=("Alpha %", "mean"),
        Instrumente_Alpha_positiv=("Alpha %", lambda s: (s > 0).sum()),
    )
    st.dataframe(agg.reindex(list(CONFIGS)), column_config={
        "Ø_Profit_Factor": st.column_config.NumberColumn(format="%.2f"),
        "Ø_R_Multiple": st.column_config.NumberColumn(format="%.2f"),
        "Ø_Alpha": st.column_config.NumberColumn(format="%.1f%%"),
    })
