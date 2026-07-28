"""Results dashboard for the ADX-conditioned VWAP mean-reversion strategy.

Runs the full pipeline (synthetic data -> indicators -> signal -> backtest ->
metrics) per pair, cached, and presents it as a portfolio overview plus a
per-pair drill-down.
"""

from dataclasses import replace

import altair as alt
import dukascopy_python
import pandas as pd

import streamlit as st
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.data import PAIRS, generate_synthetic_ohlcv
from strategy.metrics import (
    breakeven_spread_bps,
    equity_curve,
    regime_decomposition,
    summarize,
)
from strategy.real_data import fetch_pair_history
from strategy.signals import run_indicator_pipeline
from strategy.walkforward import fold_performance, stability_summary

SYNTHETIC_START, SYNTHETIC_END, FREQ_MINUTES, SEED_BASE = "2023-01-01", "2026-01-01", 15, 42
REAL_DATA_START, REAL_DATA_END = "2016-07-28", "2026-07-28"
REAL_DATA_INTERVAL = dukascopy_python.INTERVAL_HOUR_1

SOURCE_SYNTHETIC = "Synthetic (validates pipeline mechanics only)"
SOURCE_REAL = "Real (Dukascopy, 2016-2026, H1)"

# Refined configuration on top of the paper's literal Eq. 14, found via a
# yearly walk-forward screen (scripts/research_adx_params.py) across all 6
# pairs, 2017-2025: shorter ADX lookback (n=10 vs. the paper's standard 14),
# an absolute ADX ceiling (paper Foundation 3's "don't fade a live trend"
# taken to its logical conclusion), and a wider VWAP-deviation threshold.
# This is the best of several candidates tried, not a confirmed edge - see
# the warning banner below and MEMORY notes for the full honest history.
REFINED_PARAMS = dict(adx_n=10, adx_window=20, adx_ceiling=25.0, theta_multiplier=1.5)

st.set_page_config(
    page_title="ADX-VWAP FX strategy backtest",
    page_icon=":material/candlestick_chart:",
    layout="wide",
)


@st.cache_data(ttl="1h", show_spinner="Loading data and running indicator pipeline...")
def load_signaled(pair: str, source: str) -> pd.DataFrame:
    if source == SOURCE_REAL:
        df = fetch_pair_history(pair, REAL_DATA_START, REAL_DATA_END, interval=REAL_DATA_INTERVAL)
        return run_indicator_pipeline(df, **REFINED_PARAMS)
    df = generate_synthetic_ohlcv(
        pair, start=SYNTHETIC_START, end=SYNTHETIC_END, freq_minutes=FREQ_MINUTES,
        seed=SEED_BASE + PAIRS.index(pair),
    )
    return run_indicator_pipeline(df)  # literal Eq. 14 defaults - pipeline sanity check only


@st.cache_data(ttl="1h", show_spinner="Simulating trades...")
def load_trades(pair: str, source: str, spread_bps: float, stop_atr_mult: float) -> pd.DataFrame:
    signaled = load_signaled(pair, source)
    cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=stop_atr_mult)
    return simulate_trades(signaled, cfg)


@st.cache_data(ttl="1h", show_spinner="Searching breakeven spread...")
def load_breakeven(pair: str, source: str, stop_atr_mult: float) -> float:
    signaled = load_signaled(pair, source)
    base_cfg = BacktestConfig(spread_bps=0.3, stop_atr_mult=stop_atr_mult)
    trades = load_trades(pair, source, base_cfg.spread_bps, stop_atr_mult)
    if trades.empty:
        return 0.0
    return breakeven_spread_bps(signaled, base_cfg)


@st.cache_data(ttl="1h")
def load_pair_report(pair: str, source: str, spread_bps: float, stop_atr_mult: float) -> dict:
    signaled = load_signaled(pair, source)
    trades = load_trades(pair, source, spread_bps, stop_atr_mult)
    summary = summarize(trades, signaled.index)
    folds = fold_performance(trades, signaled.index, fold="MS")
    stability = stability_summary(folds)
    regimes = regime_decomposition(trades)
    breakeven = load_breakeven(pair, source, stop_atr_mult)
    return {
        "summary": summary, "folds": folds, "stability": stability,
        "regimes": regimes, "breakeven": breakeven,
    }


with st.sidebar:
    st.markdown("### Configuration")
    source = st.radio("Data source", [SOURCE_REAL, SOURCE_SYNTHETIC], index=0)
    view = st.selectbox("View", ["Portfolio overview", *PAIRS], index=0)
    spread_bps = st.slider(
        "Round-trip spread (bps)", 0.0, 3.0, 0.3, 0.1,
        help="Sec. 6.3: institutional major-pair spreads run ~0.1-0.5bps.",
    )
    stop_atr_mult = st.slider(
        "Stop distance (x ATR beyond trigger level)", 0.1, 2.0, 0.5, 0.1,
        help="Sec. 5.3: stop = prior extreme +/- this many ATRs.",
    )
    if source == SOURCE_REAL:
        st.caption(
            "Real H1 bid-side bars from Dukascopy, 2016-2026, all 6 pairs. "
            "Cached to disk after first fetch."
        )
    else:
        st.caption(
            "Data is synthetic (regime-switching + mean-reverting FX simulation), "
            "seeded and cached. This validates the pipeline's mechanics, not a "
            "real-world edge — see `strategy/data.py`."
        )

config = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=stop_atr_mult)

"""
# :material/candlestick_chart: Momentum exhaustion & fair value reversion

ADX-conditioned VWAP mean-reversion strategy — backtest results across all
six major pairs from the paper's planned empirical programme.
"""

if source == SOURCE_REAL:
    st.warning(
        "**Refined configuration, not the paper's literal Eq. 14.** H1 bars, "
        "ADX lookback n=10 (paper standard: 14), an absolute ADX ceiling of 25 "
        "(not in the paper — added because trades during genuinely strong "
        "trends were the main loss source), and a wider VWAP-deviation "
        "threshold (θ×1.5). This is the best of several candidates found via "
        "a yearly walk-forward screen (2017-2025, all 6 pairs) — **not a "
        "confirmed edge**: sample sizes are thin (~2-7 trades/pair/year), and "
        "each refinement step was chosen by picking the best of several tried "
        "on the same historical data. Switch **Data source** to *Synthetic* "
        "to see the literal, unmodified Eq. 14 signal instead.",
        icon=":material/warning:",
    )

if view == "Portfolio overview":
    reports = {pair: load_pair_report(pair, source, spread_bps, stop_atr_mult) for pair in PAIRS}

    summary_df = pd.DataFrame({pair: r["summary"] for pair, r in reports.items()}).T
    summary_df.index.name = "pair"
    summary_df["avg_return_bps"] = summary_df["avg_return_pct"] * 10_000

    with st.container(horizontal=True):
        st.metric("Pairs tested", len(PAIRS), border=True)
        st.metric("Avg. Sharpe", f"{summary_df['sharpe'].mean():.2f}", border=True)
        st.metric("Avg. Calmar", f"{summary_df['calmar'].mean():.2f}", border=True)
        st.metric("Total trades", int(summary_df["n_trades"].sum()), border=True)
        st.metric(
            "Pairs Sharpe > 1",
            f"{(summary_df['sharpe'] > 1).sum()} / {len(PAIRS)}",
            border=True,
        )

    st.space("medium")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Risk-adjusted return by pair**")
            chart_df = summary_df.reset_index().melt(
                id_vars="pair", value_vars=["sharpe", "calmar"], var_name="metric", value_name="value"
            )
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("pair:N", title="Pair"),
                    y=alt.Y("value:Q", title="Ratio"),
                    color=alt.Color("metric:N", title="Metric"),
                    xOffset="metric:N",
                    tooltip=["pair", "metric", alt.Tooltip("value:Q", format=".2f")],
                )
                .properties(height=320)
            )
            st.altair_chart(chart)

    with col2:
        with st.container(border=True):
            st.markdown("**Breakeven spread vs. assumed cost**")
            be_df = pd.DataFrame(
                {"pair": PAIRS, "breakeven_bps": [reports[p]["breakeven"] for p in PAIRS]}
            )
            be_df["assumed_bps"] = spread_bps
            chart = (
                alt.Chart(be_df)
                .mark_bar(color="#4c78a8")
                .encode(
                    x=alt.X("pair:N", title="Pair"),
                    y=alt.Y("breakeven_bps:Q", title="Breakeven round-trip spread (bps)"),
                    tooltip=["pair", alt.Tooltip("breakeven_bps:Q", format=".2f")],
                )
                .properties(height=320)
            )
            rule = (
                alt.Chart(be_df)
                .mark_rule(color="red", strokeDash=[4, 4])
                .encode(y="assumed_bps:Q")
            )
            st.altair_chart(chart + rule)
            st.caption("Dashed red line = spread currently assumed in the sidebar.")

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Summary by pair**")
        st.dataframe(
            summary_df[
                ["n_trades", "win_rate", "avg_return_bps", "sharpe", "calmar", "max_drawdown", "cagr"]
            ],
            column_config={
                "n_trades": st.column_config.NumberColumn("Trades"),
                "win_rate": st.column_config.NumberColumn("Win rate", format="percent"),
                "avg_return_bps": st.column_config.NumberColumn("Avg. return/trade (bps)", format="%.2f"),
                "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
                "calmar": st.column_config.NumberColumn("Calmar", format="%.2f"),
                "max_drawdown": st.column_config.NumberColumn("Max drawdown", format="percent"),
                "cagr": st.column_config.NumberColumn("CAGR", format="percent"),
            },
        )

else:
    pair = view
    signaled = load_signaled(pair, source)
    trades = load_trades(pair, source, spread_bps, stop_atr_mult)
    report = load_pair_report(pair, source, spread_bps, stop_atr_mult)
    summary, stability, regimes = report["summary"], report["stability"], report["regimes"]

    st.markdown(f"## {pair}")

    with st.container(horizontal=True):
        st.metric("Sharpe (ann.)", f"{summary['sharpe']:.2f}", border=True)
        st.metric("Calmar", f"{summary['calmar']:.2f}", border=True)
        st.metric("Max drawdown", f"{summary['max_drawdown']:.2%}", border=True)
        st.metric("Win rate", f"{summary['win_rate']:.1%}", border=True)
        st.metric("Trades", summary["n_trades"], border=True)
        st.metric("Breakeven spread", f"{report['breakeven']:.2f} bps", border=True)

    st.space("medium")

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown("**Equity curve (compounded daily trade returns)**")
            daily = trades_to_daily_returns(trades, signaled.index)
            curve = equity_curve(daily).rename("equity")
            curve.index.name = "date"
            curve = curve.reset_index()
            chart = (
                alt.Chart(curve)
                .mark_line(color="#4c78a8")
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("equity:Q", title="Equity (start = 1.0)", scale=alt.Scale(zero=False)),
                    tooltip=["date:T", alt.Tooltip("equity:Q", format=".4f")],
                )
                .properties(height=340)
            )
            st.altair_chart(chart)

    with col2:
        with st.container(border=True):
            st.markdown("**Exit reasons**")
            reason_df = pd.Series(summary["exit_reason_counts"]).rename("count")
            reason_df.index.name = "reason"
            reason_df = reason_df.reset_index()
            if not reason_df.empty:
                st.altair_chart(
                    alt.Chart(reason_df)
                    .mark_arc()
                    .encode(theta="count:Q", color=alt.Color("reason:N", title="Exit reason"), tooltip=["reason", "count"])
                    .properties(height=340)
                )
            else:
                st.info("No trades at this configuration.", icon=":material/info:")

    st.space("medium")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**Monthly stability (walk-forward folds)**")
            st.caption(
                f"{stability.get('n_active_folds', 0)}/{stability.get('n_folds', 0)} months with trades, "
                f"{stability.get('pct_folds_positive', float('nan')):.0%} of those net positive."
            )
            folds = report["folds"].reset_index()
            if not folds.empty:
                folds["positive"] = folds["avg_return_pct"] > 0
                chart = (
                    alt.Chart(folds)
                    .mark_bar()
                    .encode(
                        x=alt.X("period:T", title="Month"),
                        y=alt.Y("avg_return_pct:Q", title="Avg. return per trade"),
                        color=alt.Color(
                            "positive:N",
                            scale=alt.Scale(domain=[True, False], range=["#54a24b", "#e45756"]),
                            legend=None,
                        ),
                        tooltip=["period:T", alt.Tooltip("avg_return_pct:Q", format=".4%"), "n_trades"],
                    )
                    .properties(height=300)
                )
                st.altair_chart(chart)
            else:
                st.info("No monthly folds to show.", icon=":material/info:")

    with col2:
        with st.container(border=True):
            st.markdown("**Regime decomposition** (ADX level x volatility tercile)")
            if not regimes.empty:
                regimes = regimes.copy()
                regimes["avg_return_bps"] = regimes["avg_return_pct"] * 10_000
                st.dataframe(
                    regimes.drop(columns=["avg_return_pct"]),
                    hide_index=True,
                    column_config={
                        "adx_bucket": st.column_config.TextColumn("ADX regime"),
                        "vol_tercile": st.column_config.TextColumn("Vol tercile"),
                        "n_trades": st.column_config.NumberColumn("Trades"),
                        "win_rate": st.column_config.NumberColumn("Win rate", format="percent"),
                        "profit_factor": st.column_config.NumberColumn("Profit factor", format="%.2f"),
                        "avg_return_bps": st.column_config.NumberColumn("Avg. return (bps)", format="%.2f"),
                        "avg_hold_bars": st.column_config.NumberColumn("Avg. hold (bars)", format="%.1f"),
                    },
                )
            else:
                st.info("No trades to decompose.", icon=":material/info:")

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Price, VWAP & signals (last few sessions)**")
        n_days = st.slider("Sessions to show", 1, 15, 5, key=f"days_{pair}")
        last_sessions = signaled["session"].drop_duplicates().tail(n_days)
        window = signaled[signaled["session"].isin(last_sessions)].reset_index(names="time")

        base = alt.Chart(window)
        price_lines = base.transform_fold(
            ["close", "vwap", "prev_high", "prev_low"], as_=["series", "value"]
        ).mark_line().encode(
            x=alt.X("time:T", title="Time"),
            y=alt.Y("value:Q", title="Price", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title="Series",
                scale=alt.Scale(
                    domain=["close", "vwap", "prev_high", "prev_low"],
                    range=["#333333", "#4c78a8", "#e45756", "#54a24b"],
                ),
            ),
            strokeDash=alt.condition(
                alt.FieldOneOfPredicate(field="series", oneOf=["prev_high", "prev_low"]),
                alt.value([4, 3]),
                alt.value([1, 0]),
            ),
        )

        window_trades = trades[
            (trades["entry_time"] >= window["time"].min()) & (trades["entry_time"] <= window["time"].max())
        ] if not trades.empty else trades
        layers = [price_lines]
        if not window_trades.empty:
            marker_df = window_trades.copy()
            marker_df["label"] = marker_df["direction"].map({1: "Long entry", -1: "Short entry"})
            markers = (
                alt.Chart(marker_df)
                .mark_point(size=120, filled=True)
                .encode(
                    x=alt.X("entry_time:T"),
                    y=alt.Y("entry_price:Q"),
                    shape=alt.Shape(
                        "label:N",
                        scale=alt.Scale(domain=["Long entry", "Short entry"], range=["triangle-up", "triangle-down"]),
                    ),
                    color=alt.Color(
                        "label:N",
                        scale=alt.Scale(domain=["Long entry", "Short entry"], range=["#54a24b", "#e45756"]),
                        legend=alt.Legend(title="Trades"),
                    ),
                    tooltip=["entry_time:T", "label", alt.Tooltip("entry_price:Q", format=".5f"), "exit_reason"],
                )
            )
            layers.append(markers)

        st.altair_chart(alt.layer(*layers).properties(height=380).resolve_scale(color="independent"))

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Trade log**")
        if not trades.empty:
            display_trades = trades.copy()
            display_trades["direction"] = display_trades["direction"].map({1: "Long", -1: "Short"})
            display_trades["return_bps"] = display_trades["return_pct"] * 10_000
            st.dataframe(
                display_trades.sort_values("entry_time", ascending=False).drop(columns=["return_pct"]),
                hide_index=True,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Entry", format="YYYY-MM-DD HH:mm"),
                    "exit_time": st.column_config.DatetimeColumn("Exit", format="YYYY-MM-DD HH:mm"),
                    "direction": st.column_config.TextColumn("Direction"),
                    "entry_price": st.column_config.NumberColumn("Entry price", format="%.5f"),
                    "exit_price": st.column_config.NumberColumn("Exit price", format="%.5f"),
                    "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                    "exit_reason": st.column_config.TextColumn("Exit reason"),
                    "hold_bars": st.column_config.NumberColumn("Hold (bars)"),
                    "adx_at_entry": st.column_config.NumberColumn("ADX @ entry", format="%.1f"),
                    "atr_at_entry": st.column_config.NumberColumn("ATR @ entry", format="%.5f"),
                },
            )
        else:
            st.info("No trades triggered at this configuration.", icon=":material/info:")
