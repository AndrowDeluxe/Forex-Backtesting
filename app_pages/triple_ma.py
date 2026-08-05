"""Triple Moving Average -- interactive dashboard for triple_ma_strategy/.

Reproduces "Evaluating Triple Moving Average Strategy Profitability Under
Different Market Regimes" (Walugembe & Stoica, SSRN 4185701): a long/flat
trend-follower on TEMA/TSMA (triple-nested EMA/SMA to cut lag) or a
"Three Triple" 20/30/50-day crossover of the same, plus a Gaussian-Mixture
market-regime overlay. See triple_ma_strategy/{indicators,signals,regime,
filters}.py for the exact, explicitly-flagged places where the paper's own
text is ambiguous and what was assumed to make it runnable, plus the
regime-filter experiment's honest (negative) result.

Two backtest engines, selectable in the sidebar:
- simulate_trend_trades: the paper's own approach - 100%-equity compounding
  while long, no stop-loss/take-profit.
- simulate_trades_with_risk: fixed-risk (risk_pct of equity) sizing with an
  ATR stop-loss and optional R-multiple take-profit, reusing
  ema_strategy.metrics.compute_metrics for its R-multiple-based stats.
"""

import altair as alt
import pandas as pd

import streamlit as st
from ema_strategy.metrics import compute_metrics as compute_metrics_risk
from triple_ma_strategy.backtest import simulate_trades_with_risk, simulate_trend_trades
from triple_ma_strategy.data import ALL_INSTRUMENTS, fetch_daily
from triple_ma_strategy.filters import apply_entry_regime_filter, apply_regime_filter
from triple_ma_strategy.metrics import compute_metrics as compute_metrics_trend
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

FILTER_OFF = "Aus"
FILTER_CONTINUOUS = "Kontinuierlich (kann laufende Trades beenden)"
FILTER_ENTRY_ONLY = "Nur bei Entry (laufende Trades bleiben unangetastet)"


@st.cache_data(ttl="1h", show_spinner="Lade Tageshistorie...")
def load_daily(key: str) -> pd.DataFrame:
    return fetch_daily(key, START, END)


@st.cache_data(ttl="1h", show_spinner="Berechne Regime-Cluster...")
def load_regimes(key: str) -> pd.Series:
    df = load_daily(key)
    return compute_regimes(df["Close"])


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_backtest(
    key: str, variant: str, ma_type: str, cost_bps: float,
    filter_mode: str, exclude_regimes: tuple, use_risk_mgmt: bool,
    risk_pct: float, atr_mult_sl: float, use_tp: bool, tp_rr: float,
):
    df = load_daily(key)
    close = df["Close"]
    if variant == VARIANT_SINGLE:
        position = generate_single_signal(close, window=252, ma_type=ma_type)
    else:
        position = generate_triple_crossover_signal(close, 20, 30, 50, ma_type=ma_type)

    if filter_mode != FILTER_OFF and exclude_regimes:
        regimes = load_regimes(key)
        fn = apply_regime_filter if filter_mode == FILTER_CONTINUOUS else apply_entry_regime_filter
        position = fn(position, regimes, set(exclude_regimes))

    if use_risk_mgmt:
        trades, equity = simulate_trades_with_risk(
            df, position, risk_pct=risk_pct, atr_mult_sl=atr_mult_sl,
            rr=(tp_rr if use_tp else None), cost_bps=cost_bps,
        )
        metrics = compute_metrics_risk(trades, equity, price_series=close)
    else:
        trades, equity = simulate_trend_trades(df, position, cost_bps=cost_bps)
        metrics = compute_metrics_trend(trades, equity, price_series=close)
    return trades, equity, close, metrics


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

    st.markdown("### Regime-Filter (Experiment)")
    st.caption(
        "Ehrlicher Befund: **keine der beiden Varianten unten verbessert das "
        "Ergebnis robust** (siehe Warnbox). Standardmäßig aus, hier nur zum "
        "Nachvollziehen."
    )
    filter_mode = st.selectbox("Filter-Modus", [FILTER_OFF, FILTER_CONTINUOUS, FILTER_ENTRY_ONLY], index=0)
    exclude_regimes = ()
    if filter_mode != FILTER_OFF:
        exclude_regimes = tuple(
            st.multiselect(
                "Ausgeschlossene Regimes", [0, 1, 2, 3],
                default=[1, 3], format_func=lambda r: REGIME_LABELS[r],
            )
        )

    st.markdown("### Risikomanagement")
    use_risk_mgmt = st.toggle(
        "SL/TP statt reiner Trend-Equity-Kurve", value=False,
        help="Aus = Paper-Original (100%-Equity-Kompoundierung, kein Stop). "
        "An = fixes Risiko/Trade + ATR-Stop (+ optionales Kursziel).",
    )
    risk_pct = atr_mult_sl = tp_rr = 0.0
    use_tp = False
    if use_risk_mgmt:
        risk_pct = st.slider("Risiko je Trade (%)", 0.25, 3.0, 1.0, 0.25) / 100
        atr_mult_sl = st.slider("Stop-Distanz (x ATR-14)", 0.5, 5.0, 2.5, 0.5)
        use_tp = st.toggle("Kursziel (Take-Profit) aktivieren", value=False)
        if use_tp:
            tp_rr = st.slider("Kursziel (x Anfangsrisiko, \"R\")", 0.5, 5.0, 2.0, 0.5)
        st.caption(
            "Ehrlicher Befund: Stop-Loss reduziert Max-Drawdown drastisch (fixe "
            "Risiko-Sizing statt 100%-Exposure), aber Sharpe/Profit-Factor sind "
            "gegenüber der Original-Trend-Kurve gemischt (mal minimal besser, "
            "mal schlechter) -- kein klarer Gewinn, kein klarer Verlust."
        )

    st.caption(
        "Datenquelle: echte Tageshistorie (D1, Dukascopy bzw. Binance für BTC), "
        "~2016-2026 (10 Jahre) -- nicht der Paper-Zeitraum 1997-2020 (Yahoo "
        "Finance), da die verfügbare Historie nicht so weit zurückreicht."
    )

st.warning(
    "**Was das Paper nicht eindeutig spezifiziert, wurde hier explizit "
    "festgelegt statt stillschweigend geraten:** die Fensterlänge der "
    "einzelnen TEMA/TSMA (Paper nennt nur \"12 Monate\" -> hier n=252 "
    "Handelstage), die genaue Crossover-Regel für Three-Triple (hier: long "
    "wenn kurz > mittel > lang gestapelt sind) und die GMM-Feature-Basis "
    "(hier: Log-Return + 21-Tage-Rolling-Vola statt einer festen 12-Monats-"
    "Vola, sonst bewegt sich das Regime praktisch nie).\n\n"
    "**Eigener Befund (S&P 500, 2016-2026, echte Dukascopy-Daten):** alle "
    "vier Grundvarianten sind vor Kosten profitabel (Profit Factor 1.6-2.7), "
    "**liegen aber deutlich hinter Buy & Hold zurück** (Alpha -145 bis -209 "
    "Prozentpunkte), weil ein Long/Flat-Trendfolger in einem fast "
    "durchgehenden Bullenmarkt jeden Ausstieg verpasste Aufwärtsbewegung "
    "kostet. Deckt sich mit der eigenen Schlussfolgerung des Papers.\n\n"
    "**Regime-Filter (neu getestet):** die naheliegende Idee, im "
    "volatilsten Cluster (\"Frenzy\") nicht zu handeln, wurde auf SP500/"
    "NASDAQ/GOLD geprüft -- **beide Umsetzungen verschlechtern das "
    "Ergebnis** (kontinuierlich: zerstückelt laufende Trades und drückt "
    "z.B. SP500s Profit Factor von 2.67 auf 0.98; nur-bei-Entry: vermeidet "
    "das Zerstückeln, aber die Konzentration auf das \"beste\" Cluster "
    "bringt trotzdem kein konsistent besseres Sharpe/Alpha). Details in "
    "`triple_ma_strategy/filters.py`.\n\n"
    "**SL/TP (neu getestet):** ein ATR-Stop mit fixem Risiko/Trade senkt "
    "den Max-Drawdown massiv (z.B. SP500 -16% -> -2 bis -6%), weil dabei "
    "nur ein kleiner Bruchteil des Kapitals exponiert ist statt 100% -- "
    "das ist aber überwiegend ein Sizing-Effekt, kein Beweis für eine "
    "bessere Kante. Risikobereinigt (Sharpe/Profit Factor) ist das Bild "
    "gemischt, kein durchgängiger Gewinn.",
    icon=":material/warning:",
)

if key == "BTC" and variant == VARIANT_SINGLE and ma_type == "tema" and not use_risk_mgmt and filter_mode == FILTER_OFF:
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

trades, equity, close, metrics = load_backtest(
    key, variant, ma_type, cost_bps, filter_mode, exclude_regimes,
    use_risk_mgmt, risk_pct, atr_mult_sl, use_tp, tp_rr,
)

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
        if trades.empty:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")
        elif "reason" in trades.columns:
            display_trades = trades.sort_values("entry_time", ascending=False)
            st.dataframe(
                display_trades,
                hide_index=True,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD"),
                    "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD"),
                    "direction": st.column_config.TextColumn("Richtung"),
                    "entry": st.column_config.NumberColumn("Entry-Preis", format="%.2f"),
                    "exit": st.column_config.NumberColumn("Exit-Preis", format="%.2f"),
                    "sl": st.column_config.NumberColumn("Stop-Loss", format="%.2f"),
                    "tp": st.column_config.NumberColumn("Kursziel", format="%.2f"),
                    "pnl": st.column_config.NumberColumn("P&L ($)", format="%.2f"),
                    "reason": st.column_config.TextColumn("Exit-Grund"),
                    "r_multiple": st.column_config.NumberColumn("R-Multiple", format="%.2f"),
                },
            )
        else:
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
