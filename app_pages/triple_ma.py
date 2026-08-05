"""Triple Moving Average -- interactive dashboard for triple_ma_strategy/.

Reproduces "Evaluating Triple Moving Average Strategy Profitability Under
Different Market Regimes" (Walugembe & Stoica, SSRN 4185701): a long/flat
trend-follower on TEMA/TSMA (triple-nested EMA/SMA to cut lag) or a
"Three Triple" 20/30/50-day crossover of the same, plus a Gaussian-Mixture
market-regime overlay. See triple_ma_strategy/{indicators,signals,regime}.py
for the exact, explicitly-flagged places where the paper's own text is
ambiguous (single-MA window length, triple-crossover entry rule, GMM
feature set) and what was assumed to make it runnable.
"""

import altair as alt
import pandas as pd

import streamlit as st
from triple_ma_strategy.backtest import simulate_trend_trades
from triple_ma_strategy.data import ALL_INSTRUMENTS, fetch_daily
from triple_ma_strategy.metrics import compute_metrics
from triple_ma_strategy.regime import REGIME_LABELS, compute_regimes
from triple_ma_strategy.signals import generate_single_signal, generate_triple_crossover_signal

st.set_page_config(
    page_title="Triple Moving Average Backtest",
    page_icon=":material/stacked_line_chart:",
    layout="wide",
)

START, END = "2016-07-28", "2026-07-28"

VARIANT_SINGLE = "Single TEMA/TSMA (n=252, 1 Trend-Linie)"
VARIANT_TRIPLE = "Three Triple Crossover (20/30/50 Tage)"


@st.cache_data(ttl="1h", show_spinner="Lade Dukascopy-Tageshistorie...")
def load_daily(key: str) -> pd.DataFrame:
    return fetch_daily(key, START, END)


@st.cache_data(ttl="1h", show_spinner="Berechne Regime-Cluster...")
def load_regimes(key: str) -> pd.Series:
    df = load_daily(key)
    return compute_regimes(df["Close"])


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_backtest(key: str, variant: str, ma_type: str, cost_bps: float):
    df = load_daily(key)
    close = df["Close"]
    if variant == VARIANT_SINGLE:
        position = generate_single_signal(close, window=252, ma_type=ma_type)
    else:
        position = generate_triple_crossover_signal(close, 20, 30, 50, ma_type=ma_type)
    trades, equity = simulate_trend_trades(df, position, cost_bps=cost_bps)
    return trades, equity, close


with st.sidebar:
    st.markdown("### Konfiguration")
    key = st.selectbox("Instrument", ALL_INSTRUMENTS, index=ALL_INSTRUMENTS.index("SP500"))
    variant = st.radio("Variante", [VARIANT_SINGLE, VARIANT_TRIPLE], index=0)
    ma_type_label = st.radio("MA-Typ", ["Exponentiell (TEMA)", "Simple (TSMA)"], index=0)
    ma_type = "tema" if ma_type_label.startswith("Exponentiell") else "tsma"
    cost_bps = st.slider(
        "Kosten je Positionswechsel (bps)", 0.0, 10.0, 1.0, 0.5,
        help="Belastet auf jeden 0->1/1->0 Positionswechsel, nicht pro Kalendertag.",
    )
    show_regimes = st.toggle("Regime-Overlay anzeigen (GMM, 4 Cluster)", value=True)
    st.caption(
        "Datenquelle: echte Dukascopy-Tageshistorie (D1), ~2016-2026 (10 Jahre) -- "
        "nicht der Paper-Zeitraum 1997-2020 (Yahoo Finance), da Dukascopy nicht so "
        "weit zurückreicht."
    )

st.warning(
    "**Was das Paper nicht eindeutig spezifiziert, wurde hier explizit "
    "festgelegt statt stillschweigend geraten:** die Fensterlänge der "
    "einzelnen TEMA/TSMA (Paper nennt nur \"12 Monate\" -> hier n=252 "
    "Handelstage), die genaue Crossover-Regel für Three-Triple (hier: long "
    "wenn kurz > mittel > lang gestapelt sind) und die GMM-Feature-Basis "
    "(hier: Log-Return + 21-Tage-Rolling-Vola statt einer festen 12-Monats-"
    "Vola, sonst bewegt sich das Regime praktisch nie). Details in "
    "`triple_ma_strategy/{signals,regime}.py`.\n\n"
    "**Eigener Befund (S&P 500, 2016-2026, echte Dukascopy-Daten):** alle "
    "vier Varianten (Single TEMA/TSMA, Three-Triple TTEMA/TTSMA) sind vor "
    "Kosten profitabel (Profit Factor 1.6-2.7) und schlagen damit den "
    "Bereich, den auch das Paper selbst berichtet -- **aber alle vier "
    "liegen deutlich hinter Buy & Hold zurück** (Alpha -145 bis -209 "
    "Prozentpunkte über 10 Jahre), weil der S&P 500 in diesem Zeitraum "
    "fast ununterbrochen gestiegen ist und ein Long/Flat-Trendfolger jeden "
    "Ausstieg verpasste Aufwärtsbewegung kostet. Das deckt sich mit der "
    "eigenen Schlussfolgerung des Papers (Sec. 4/5): TEMA/TSMA schlagen "
    "Buy & Hold *nicht* zuverlässig, nur die Three-Triple-Variante kam im "
    "Paper (1998-2019) knapp darüber. Nicht als Edge präsentieren, wenn "
    "danach gefragt wird.",
    icon=":material/warning:",
)

if key == "BTC" and variant == VARIANT_SINGLE and ma_type == "tema":
    st.info(
        "**BTC-Befund, ehrlich eingeordnet:** die hohe Outperformance ggü. Buy & "
        "Hold hier hängt fast vollständig an einem einzigen Trade (10.10.2020 - "
        "25.03.2021, +354%, der 2020/21-Bullenlauf). Rechnet man diesen einen "
        "Trade heraus, sinkt die Gesamtrendite von ~6700% auf ~1400% - fast exakt "
        "auf Buy & Hold-Niveau. Real (kein Datenfehler), aber die Outperformance "
        "selbst ist nicht robust über viele Trades verteilt, sondern hängt an "
        "einem einzigen erwischten Trend.",
        icon=":material/info:",
    )

df = load_daily(key)
trades, equity, close = load_backtest(key, variant, ma_type, cost_bps)
metrics = compute_metrics(trades, equity, price_series=close)

st.markdown(f"## :material/stacked_line_chart: {key} — {variant}")

with st.container(horizontal=True):
    st.metric("Sharpe (approx.)", f"{metrics.get('Sharpe (approx.)', float('nan')):.2f}", border=True)
    st.metric("Profit Factor", f"{metrics.get('Profit Factor', float('nan')):.2f}", border=True)
    st.metric("Max Drawdown", f"{metrics.get('Max Drawdown %', float('nan')):.1f}%", border=True)
    st.metric("Trefferquote", f"{metrics.get('Trefferquote %', float('nan')):.1f}%", border=True)
    st.metric("Trades", metrics.get("Anzahl Trades", 0), border=True)
    alpha = metrics.get("Alpha vs. Buy & Hold %", float("nan"))
    st.metric("Alpha vs. Buy & Hold", f"{alpha:.1f} pp", border=True)

st.space("medium")

tab_equity, tab_regime, tab_trades = st.tabs(["Equity vs. Buy & Hold", "Regime-Cluster", "Trade-Log"])

with tab_equity:
    with st.container(border=True):
        bh = (close / close.iloc[0] * equity.iloc[0]).rename("Buy & Hold")
        curve = pd.DataFrame({"Strategie": equity, "Buy & Hold": bh}).reset_index(names="date")
        curve = curve.melt("date", var_name="Serie", value_name="Equity")
        chart = (
            alt.Chart(curve)
            .mark_line()
            .encode(
                x=alt.X("date:T", title="Datum"),
                y=alt.Y("Equity:Q", title="Portfoliowert", scale=alt.Scale(zero=False)),
                color=alt.Color("Serie:N", scale=alt.Scale(range=["#4c78a8", "#e45756"])),
                tooltip=["date:T", "Serie:N", alt.Tooltip("Equity:Q", format=".1f")],
            )
            .properties(height=420)
        )
        st.altair_chart(chart)

with tab_regime:
    with st.container(border=True):
        st.markdown(
            "Cluster nach Rolling-21-Tage-Volatilität sortiert (0 = ruhigste, "
            "3 = unruhigste Phase) -- siehe Sidebar-Warnhinweis zur Feature-Wahl."
        )
        if show_regimes:
            regimes = load_regimes(key)
            regime_df = pd.DataFrame({"close": close, "regime": regimes}).dropna().reset_index(names="date")
            regime_df["Regime"] = regime_df["regime"].map(REGIME_LABELS)
            chart = (
                alt.Chart(regime_df)
                .mark_circle(size=8)
                .encode(
                    x=alt.X("date:T", title="Datum"),
                    y=alt.Y("close:Q", title="Preis", scale=alt.Scale(zero=False)),
                    color=alt.Color("Regime:N", title="Regime", sort=list(REGIME_LABELS.values())),
                    tooltip=["date:T", "close:Q", "Regime:N"],
                )
                .properties(height=420)
            )
            st.altair_chart(chart)
        else:
            st.info("Regime-Overlay in der Sidebar aktivieren.", icon=":material/info:")

with tab_trades:
    with st.container(border=True):
        if not trades.empty:
            display_trades = trades.copy()
            display_trades["pnl_pct"] = display_trades["pnl_pct"] * 100
            st.dataframe(
                display_trades.sort_values("entry_time", ascending=False),
                hide_index=True,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD"),
                    "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD"),
                    "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.2f"),
                    "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.2f"),
                    "hold_days": st.column_config.NumberColumn("Haltedauer (Tage)"),
                    "pnl_pct": st.column_config.NumberColumn("Return (%)", format="%.2f"),
                },
            )
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")
