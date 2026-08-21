"""EMA S/R Backtest -- interactive dashboard.

Multi-timeframe EMA support/resistance strategy (EUR/USD, Gold, S&P 500):
Weekly+Daily EMA bias, H4 (or H12 for the V2 variants) rejection trigger.
Market data is fetched live from Yahoo Finance (`yfinance`) and cached for
1h -- no local data snapshot is shipped, so results stay current.

See the original project's README_Ergebnisse.md for the full strategy
derivation, including the honest overfitting finding behind the "Optimiert
(In-Sample)" preset and the V2-Trail recalibration.
"""
import json
import os

import altair as alt
import pandas as pd

import streamlit as st
import ema_strategy
from ema_strategy.data import ASSETS, fetch_h4_and_daily, resample_ohlc
from ema_strategy.indicators import double_ema
from ema_strategy.pipeline import (
    EMA_LENGTH, EMA_SMOOTH, V2_PARAMS, V2_TRAIL_PARAMS, V2_TRIGGER_RULE, run_pipeline,
)

st.set_page_config(
    page_title="EMA S/R Backtest",
    page_icon=":material/candlestick_chart:",
    layout="wide",
)

OPTDIR = os.path.join(os.path.dirname(ema_strategy.__file__), "optimization")
IN_SAMPLE_FRAC = 0.7

# Defaults for all engine parameters -- each preset below overrides only the
# fields it actually changes (see full_params()).
PARAM_DEFAULTS = dict(
    trigger_rule="4h", ema_length=EMA_LENGTH, ema_smooth=EMA_SMOOTH, rr=2.0,
    sl_buffer_atr=0.1, min_rejection_atr=0.0, require_htf_slope=False,
    invalidation_confirm_bars=1, sl_mode="signal_extreme", atr_multiplier=1.5,
    exit_on_htf_bias_flip=False, htf_bias_col="daily_bias",
    use_trailing_stop=False, breakeven_trigger_r=1.0, trail_atr_mult=2.5,
    adx_col="daily_adx", adx_threshold=25.0,
)
BASELINE_PARAMS = dict(PARAM_DEFAULTS)
V2_FULL_PARAMS = dict(PARAM_DEFAULTS, trigger_rule=V2_TRIGGER_RULE, **V2_PARAMS)
V2_TRAIL_FULL_PARAMS = dict(PARAM_DEFAULTS, trigger_rule=V2_TRIGGER_RULE, **V2_TRAIL_PARAMS)


def full_params(overrides: dict) -> dict:
    return dict(PARAM_DEFAULTS, **overrides)


@st.cache_data(ttl="1h", show_spinner=False)
def load_optimized_params() -> dict:
    path = os.path.join(OPTDIR, "best_params.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return BASELINE_PARAMS


@st.cache_data(ttl="1h", show_spinner="Lade Kursdaten von Yahoo Finance...")
def load_asset_data(name: str):
    h4, d1 = fetch_h4_and_daily(ASSETS[name])
    w1 = resample_ohlc(d1, "W")
    return h4, d1, w1


def split_h4(h4: pd.DataFrame, split: str) -> pd.DataFrame:
    if split == "full":
        return h4
    cut = int(len(h4) * IN_SAMPLE_FRAC)
    return h4.iloc[:cut] if split == "is" else h4.iloc[cut:]


@st.cache_data(ttl="1h", show_spinner=False)
def run_cached(name: str, split: str, trigger_rule: str, ema_length: int, ema_smooth: int,
               rr: float, sl_buffer_atr: float, min_rejection_atr: float,
               require_htf_slope: bool, invalidation_confirm_bars: int, sl_mode: str,
               atr_multiplier: float, exit_on_htf_bias_flip: bool, htf_bias_col: str,
               use_trailing_stop: bool, breakeven_trigger_r: float, trail_atr_mult: float,
               adx_col: str, adx_threshold: float):
    h4, d1, w1 = load_asset_data(name)
    trigger_df = h4 if trigger_rule == "4h" else resample_ohlc(h4, trigger_rule)
    trigger_df = split_h4(trigger_df, split)
    signals, trades, equity, metrics, daily, weekly = run_pipeline(
        trigger_df, daily=d1, weekly=w1, ema_length=ema_length, ema_smooth=ema_smooth, rr=rr,
        sl_buffer_atr=sl_buffer_atr, min_rejection_atr=min_rejection_atr,
        require_htf_slope=require_htf_slope, invalidation_confirm_bars=invalidation_confirm_bars,
        sl_mode=sl_mode, atr_multiplier=atr_multiplier,
        exit_on_htf_bias_flip=exit_on_htf_bias_flip, htf_bias_col=htf_bias_col,
        use_trailing_stop=use_trailing_stop, breakeven_trigger_r=breakeven_trigger_r,
        trail_atr_mult=trail_atr_mult, adx_col=adx_col, adx_threshold=adx_threshold,
    )
    return signals, trades, equity, metrics, daily, trigger_df.index.min(), trigger_df.index.max()


def run_for(name: str, split: str, params: dict):
    p = full_params(params)
    return run_cached(
        name, split, p["trigger_rule"], p["ema_length"], p["ema_smooth"], p["rr"],
        p["sl_buffer_atr"], p["min_rejection_atr"], p["require_htf_slope"],
        p["invalidation_confirm_bars"], p["sl_mode"], p["atr_multiplier"],
        p["exit_on_htf_bias_flip"], p["htf_bias_col"],
        p["use_trailing_stop"], p["breakeven_trigger_r"], p["trail_atr_mult"],
        p["adx_col"], p["adx_threshold"],
    )


def metric_row(metrics: dict) -> None:
    if metrics.get("Anzahl Trades", 0) == 0:
        st.info("Keine Trades in diesem Zeitraum.")
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
        st.metric("Sharpe (approx.)", f"{metrics['Sharpe (approx.)']:.2f}", border=True)
    if "Buy & Hold %" in metrics and not pd.isna(metrics["Buy & Hold %"]):
        st.caption(
            f"Buy & hold over the same window: {metrics['Buy & Hold %']:+.1f}% — "
            "a trend-following strategy's return should be judged against this, "
            "not in isolation (see the ADX-VWAP research on beta vs. skill)."
        )


def price_entry_chart(daily: pd.DataFrame, trades: pd.DataFrame, window_start,
                       ema_length: int, ema_smooth: int, height: int = 380) -> alt.LayerChart:
    ema_series = double_ema(daily["Close"], ema_length, ema_smooth)
    mask = daily.index >= window_start
    price_df = pd.DataFrame({
        "Date": daily.index[mask],
        "Close": daily["Close"][mask].to_numpy(),
        "EMA": ema_series[mask].to_numpy(),
    })

    price_line = alt.Chart(price_df).mark_line(color="#5c5c5c", strokeWidth=1).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Close:Q", title=None, scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("Date:T"), alt.Tooltip("Close:Q", format=",.4f")],
    )
    ema_line = alt.Chart(price_df).mark_line(color="#e8590c", strokeWidth=2).encode(
        x="Date:T", y="EMA:Q",
    )
    layers = [price_line, ema_line]

    if not trades.empty:
        window_trades = trades[trades["entry_time"] >= window_start]
        longs = window_trades[window_trades["direction"] == "LONG"]
        shorts = window_trades[window_trades["direction"] == "SHORT"]
        if not longs.empty:
            layers.append(
                alt.Chart(longs).mark_point(
                    shape="triangle-up", size=90, filled=True, color="#2f9e44",
                ).encode(
                    x="entry_time:T", y="entry:Q",
                    tooltip=[alt.Tooltip("entry_time:T", title="Einstieg"),
                             alt.Tooltip("entry:Q", format=",.4f"),
                             alt.Tooltip("pnl:Q", format=",.2f")],
                )
            )
        if not shorts.empty:
            layers.append(
                alt.Chart(shorts).mark_point(
                    shape="triangle-down", size=90, filled=True, color="#e03131",
                ).encode(
                    x="entry_time:T", y="entry:Q",
                    tooltip=[alt.Tooltip("entry_time:T", title="Einstieg"),
                             alt.Tooltip("entry:Q", format=",.4f"),
                             alt.Tooltip("pnl:Q", format=",.2f")],
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


def trades_table(trades: pd.DataFrame, name: str) -> None:
    if trades.empty:
        return
    decimals = 4 if name == "EURUSD" else 2
    fmt = f"%.{decimals}f"
    with st.container(border=True):
        st.markdown("**Trades**")
        st.dataframe(
            trades.sort_values("entry_time", ascending=False),
            hide_index=True,
            column_config={
                "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                "direction": st.column_config.TextColumn("Richtung"),
                "entry": st.column_config.NumberColumn("Entry", format=fmt),
                "exit": st.column_config.NumberColumn("Exit", format=fmt),
                "sl": st.column_config.NumberColumn("SL", format=fmt),
                "tp": st.column_config.NumberColumn("TP", format=fmt),
                "pnl": st.column_config.NumberColumn("P&L", format="%.2f"),
                "r_multiple": st.column_config.NumberColumn("R", format="%.2f"),
                "reason": st.column_config.TextColumn("Exit-Grund"),
            },
        )


# =============================================================================
# Sidebar
# =============================================================================

PARAM_CHOICES = ["Baseline", "Optimiert (In-Sample)", "V2: H12-Rejection", "V2-Trail"]

with st.sidebar:
    st.markdown("### Auswahl")
    asset = st.selectbox("Asset", list(ASSETS))
    param_choice = st.segmented_control("Parameter", options=PARAM_CHOICES, default="Baseline")
    if param_choice is None:
        param_choice = "Baseline"
    split_label = st.radio(
        "Zeitraum", options=["Gesamter Datensatz", "In-Sample (70%)", "Out-of-Sample (30%)"],
    )
    st.caption(
        "Datenquelle: Yahoo Finance (`yfinance`), live geladen und 1h gecacht. "
        "H4-Fenster je nach Asset ~1,6–2,8 Jahre (Yahoo-Limit für Stundendaten)."
    )

split_map = {"Gesamter Datensatz": "full", "In-Sample (70%)": "is", "Out-of-Sample (30%)": "oos"}
split = split_map[split_label]
optimized_params = load_optimized_params()
params = {
    "Baseline": BASELINE_PARAMS,
    "Optimiert (In-Sample)": optimized_params,
    "V2: H12-Rejection": V2_FULL_PARAMS,
    "V2-Trail": V2_TRAIL_FULL_PARAMS,
}[param_choice]

if param_choice == "Optimiert (In-Sample)":
    st.warning(
        ":material/warning: Diese Parameter wurden auf dem In-Sample-Zeitraum ausgewählt und "
        "brechen Out-of-Sample bei EUR/USD und S&P 500 deutlich ein (klassisches "
        "Overfitting-Signal bei der begrenzten Datenmenge). Nicht ungeprüft übernehmen — "
        "Details im Tab **Optimierung**.",
        icon=":material/warning:",
    )
elif param_choice == "V2: H12-Rejection":
    st.info(
        "Trend = Daily-Close vs. einfache EMA(60) (kein Doppel-Glätten), Weekly-Bias als "
        "Zusatzfilter, Entry = Rejection an der EMA(60) auf H12-Kerzen, SL = ATR(14)×1.5, "
        "sofortiger Ausstieg bei Daily-Bias-Flip, TP = festes RR. Deutlich weniger Trades als "
        "Baseline (gröberer Trigger-Timeframe + weniger Signale) — Kennzahlen entsprechend "
        "mit Vorsicht interpretieren (kleinere Stichprobe).",
        icon=":material/info:",
    )
elif param_choice == "V2-Trail":
    st.warning(
        "Wie V2, zusätzlich: SL auf Breakeven nach 1.5R, danach Chandelier-Trail "
        "(3.0×ATR hinter Hoch/Tief seit Entry). War der ADX(14) auf Daily bei Entry ≥25, "
        "entfällt das feste TP komplett. Diese Werte sind bereits das Ergebnis einer "
        "In-Sample-Grid-Suche — die erste Schätzung (2.5×/25/1.0R) war noch schlechter. "
        "**Befund:** Auch rekalibriert bleibt das Setup In-Sample hinter V2 ohne Trail "
        "zurück (Ø R über 3 Assets: 0.13 vs. 0.29). Out-of-Sample sieht es besser aus, das "
        "wird aber fast komplett von einem einzelnen Gold-Ausreißer (8.67R bei nur 8 "
        "OOS-Trades) getragen, nicht von einem robusten Effekt. Fazit: auf diesem Datensatz "
        "kein verlässlicher Vorteil gegenüber dem festen TP.",
        icon=":material/warning:",
    )

# =============================================================================
# Tabs
# =============================================================================

tab_backtest, tab_optimization = st.tabs(["Backtest", "Optimierung"], on_change="rerun")

def _render_tab_backtest():
    st.markdown(f"## :material/candlestick_chart: {asset} — {param_choice}, {split_label}")

    signals, trades, equity, metrics, daily, win_start, win_end = run_for(asset, split, params)
    metric_row(metrics)

    with st.container(border=True):
        st.markdown("**Equity-Kurve**")
        st.altair_chart(equity_chart(equity))

    with st.container(border=True):
        st.markdown("**Kurs, Daily-EMA (S/R) & Einstiege**")
        chart_window_start = win_start - pd.Timedelta(days=45)
        st.altair_chart(
            price_entry_chart(daily, trades, chart_window_start,
                               params["ema_length"], params["ema_smooth"])
        )

    trades_table(trades, asset)

def _render_tab_optimization():
    st.markdown("## :material/tune: Parameteroptimierung")
    st.warning(
        "**Kernbefund:** Die In-Sample-Grid-Suche fand ein Setup (EMA 40/20, RR 2.5, "
        "HTF-Slope-Filter), das In-Sample auf allen drei Assets deutlich besser aussieht "
        "als die Baseline — Out-of-Sample bricht es aber bei EUR/USD und S&P 500 massiv "
        "ein (Profit Factor 0.22 bzw. 0.54). Bei nur 1,6–2,8 Jahren echter H4-Historie "
        "folgt die Grid-Suche im Wesentlichen Rauschen, nicht einem stabilen Edge. "
        "Empfehlung: mehr Historie, Walk-Forward mit mehreren Fenstern und Paper-Trading "
        "vor produktivem Einsatz.",
        icon=":material/warning:",
    )

    st.markdown("### In-Sample vs. Out-of-Sample, Baseline vs. optimiert")
    rows = []
    for a in ASSETS:
        for label, p in (("Baseline", BASELINE_PARAMS), ("Optimiert (IS)", optimized_params)):
            for split_key, split_lbl in (("is", "In-Sample"), ("oos", "Out-of-Sample")):
                _, _, _, m, _, _, _ = run_for(a, split_key, p)
                rows.append({
                    "Asset": a, "Parameter": label, "Zeitraum": split_lbl,
                    "Trades": m.get("Anzahl Trades"), "Trefferquote %": m.get("Trefferquote %"),
                    "Profit Factor": m.get("Profit Factor"), "Ø R-Multiple": m.get("Ø R-Multiple"),
                })
    comparison_df = pd.DataFrame(rows)
    st.dataframe(
        comparison_df,
        hide_index=True,
        column_config={
            "Trefferquote %": st.column_config.NumberColumn(format="%.1f%%"),
            "Profit Factor": st.column_config.NumberColumn(format="%.2f"),
            "Ø R-Multiple": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    st.markdown("### Ausgewählte optimierte Parameter")
    st.json(optimized_params)

    col1, col2 = st.columns(2)
    stage_a_path = os.path.join(OPTDIR, "stageA_core_grid.csv")
    stage_b_path = os.path.join(OPTDIR, "stageB_filter_ablation.csv")
    with col1:
        with st.container(border=True):
            st.markdown("**Stage A — Kern-Parameter-Grid (In-Sample)**")
            if os.path.exists(stage_a_path):
                st.dataframe(pd.read_csv(stage_a_path).sort_values("score_R", ascending=False),
                             hide_index=True, height=300)
    with col2:
        with st.container(border=True):
            st.markdown("**Stage B — Filter-Ablation (In-Sample)**")
            if os.path.exists(stage_b_path):
                st.dataframe(pd.read_csv(stage_b_path).sort_values("score_R", ascending=False),
                             hide_index=True, height=300)


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
# tab_optimization alone runs run_for() 12x (3 assets x 2 param sets x 2 splits).
for _tab, _render in [(tab_backtest, _render_tab_backtest), (tab_optimization, _render_tab_optimization)]:
    if _tab.open:
        with _tab:
            _render()
