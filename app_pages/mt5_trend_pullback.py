"""Backtests -- MT5 Trend+Pullback Bot: replication of the user's own live
community MT5 bot (`.../Bots/Ideen1/MT5-TrendPullback-Bot/strategy.py`,
demo-account only, EMA150 trend filter + RSI14 pullback-resumption cross,
ATR14x2.0 stop, RR 2.0, long-only, on XAUUSD/XAGUSD/XPTUSD H1 +
CHFJPY/USDJPY H4) against this repo's real 10-year Dukascopy history
(mt5_trend_pullback/pipeline.py reproduces the bot's own indicator formulas
verbatim, not this repo's differently-seeded Wilder smoothing, so signals
line up with what the live bot would actually have fired).

Four research passes, run in order at the user's request:
  1. Baseline replication + regime decomposition (scripts/research_mt5_trend_pullback.py)
  2. ADX>=25 regime filter, chosen on IS only, validated untouched on OOS
     (scripts/research_mt5_trend_pullback_adx_filter.py)
  3. Spread-cost sensitivity / breakeven analysis, OOS only
     (scripts/research_mt5_trend_pullback_spread_sensitivity.py)
  4. $100k / 1%-risk dollar account simulation, honouring the live bot's real
     3-concurrent-position cap (mt5_trend_pullback/account_simulation.py,
     scripts/research_mt5_trend_pullback_account_sim.py)

Honest headline finding surfaced up front (not buried): the strategy lost
money or barely broke even in EVERY one of the 5 markets 2016-2022, and was
only profitable 2023-2026 -- the live bot's own config.py comments quote
full-history-sounding PF numbers that actually look like they came from a
short/recent test window, not a 10-year backtest.

Dark/monospace styling matches app_pages/gold_bitcoin_dual_momentum.py (same
palette, prefixed mtp- instead of gb- per that page's established
per-page-CSS convention)."""

import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

import streamlit as st
from combined_strategy.data import fetch_timeframe
from mt5_trend_pullback.pipeline import (
    ATR_LEN, ATR_STOP_MULT, RR_RATIO, RSI_LEN, RSI_OVERSOLD, TREND_LEN, run_pipeline,
)
from mt5_trend_pullback.account_simulation import account_stats, simulate_account
from mt5_trend_pullback.daily_risk_engine import simulate_open_risk_daily, sweep_risk_pct
from mt5_trend_pullback.execution_overlay import simulate_trades_overlay
from mt5_trend_pullback.filters import alignment_filter
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import breakeven_spread_bps, regime_decomposition, summarize

st.set_page_config(page_title="Trend Pullback", page_icon=":material/smart_toy:", layout="wide")

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
CHOSEN_ADX_MIN = 25.0  # picked on IS only by the ADX sweep below -- not re-tuned per market
STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01
MAX_CONCURRENT = 3

# (Dukascopy key, timeframe, MT5 symbol label, round-trip spread assumption in bps)
MARKETS = [
    ("GOLD", "H1", "XAUUSD", 10.0),
    ("SILVER", "H1", "XAGUSD", 10.0),
    ("PLATINUM", "H1", "XPTUSD", 10.0),
    ("CHFJPY", "H4", "CHFJPY", 3.0),
    ("USDJPY", "H4", "USDJPY", 1.5),
]
ADX_MIN_CANDIDATES = [None, 15, 20, 25, 30, 35]
SPREAD_SWEEP_BPS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]
STOP_ATR_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0]
TP_R_CANDIDATES = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
BE_TRIGGER_CANDIDATES = [None, 0.5, 1.0, 1.5]
MIN_IS_TRADES_TPSL = 30

# --- current standard recommendation (2026-08-14): Platinum dropped, Gold
# confirms Silver via alignment filter (see scripts/research_mt5_trend_
# pullback_market_dropout.py) -- regime-shifted window, not the full 2016
# history, since that's what motivated dropping Platinum in the first place.
# USDCAD added 2026-08-14 as a trial addition (scripts/research_mt5_trend_
# pullback_fx_majors.py: only 7 OOS trades, thin sample, but improved the
# pooled OOS Sharpe 0.87->0.90 when added) - NOT part of the original 5-
# market MARKETS list above (that list stays the historical-record set used
# by the other tabs), only added here for the standard-recommendation tab.
STANDARD_MARKET_LABELS = ["XAUUSD", "XAGUSD", "CHFJPY", "USDJPY", "USDCAD"]
STANDARD_EXTRA_MARKETS = [("USDCAD", "H4", "USDCAD", 1.5)]
NEW_IS_START = pd.Timestamp("2023-01-01", tz="UTC")
NEW_SPLIT = pd.Timestamp("2024-07-01", tz="UTC")
NEW_OOS_END = pd.Timestamp("2026-08-01", tz="UTC")
OVERLAY_WAIT_BARS = 5

# --- risk management: FK (funded/prop) and EK (personal) profiles (2026-08-15) ---
RISK_PROFILES = {
    "FK1 (TTP-Stil: 3% daily / 7% total)": {"daily": 0.03, "total": 0.07, "per_position_cap": None},
    "FK2 (IQ Markets: max 1% pro Position, 6% Trailing-Total, kein Daily)": {"daily": None, "total": 0.06, "per_position_cap": 0.01},
    "EK (Eigenkapital: kein daily / 20% total)": {"daily": None, "total": 0.20, "per_position_cap": None},
}
FK2_PROFIT_TARGET = 0.08  # context only, not a hard constraint on risk_pct
RISK_PCT_CANDIDATES = [0.001, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02, 0.025, 0.03]
OU_RISK_PCT = 0.005
OU_MAX_TOTAL_RISK_PCT = 0.02

# --- same palette as gold_bitcoin_dual_momentum.py / fertige_strategien.py ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
C_GRID = "#1c2128"
C_TEXT = "#f0f6fc"
C_MUTED = "#8b949e"
C_BODY = "#c9d1d9"
C_ORANGE = "#ff8c42"
C_ORANGE_SOFT = "#ffb37a"
C_BLUE = "#5ec8f8"
C_BLUE_SOFT = "#9db4e8"
C_GREEN = "#5ecb8c"
C_RED = "#ff5555"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .mtp-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .mtp-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .mtp-caveats b {{ color: {C_TEXT}; }}
    .mtp-alert {{ background: rgba(255,140,66,0.08); border: 1px solid {C_ORANGE};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .mtp-good {{ background: rgba(94,203,140,0.08); border: 1px solid {C_GREEN};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .mtp-good b {{ color: {C_TEXT}; }}
    .mtp-alert b {{ color: {C_TEXT}; }}
    .mtp-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .mtp-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px;
               transition: border-color 0.15s ease; }}
    .mtp-tile:hover {{ border-color: {C_ORANGE}; }}
    .mtp-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .mtp-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .mtp-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .mtp-legend {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.78rem; margin-top: 0.4rem; }}
    .mtp-legend span {{ margin-right: 1.4rem; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.82rem;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px 6px 0 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------ render helpers
def section_title(text: str, color: str = C_ORANGE) -> None:
    st.markdown(f"<div class='mtp-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, kind: str = "neutral") -> None:
    cls = {"neutral": "mtp-caveats", "alert": "mtp-alert", "good": "mtp-good"}[kind]
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='mtp-tile-row'>" + "".join(
        f"<div class='mtp-tile'><div class='mtp-tile-value'>{v}</div><div class='mtp-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def legend(items: list[tuple[str, str]]) -> None:
    spans = "".join(f"<span style='color:{color};'>&#9644;&#9644; {label}</span>" for label, color in items)
    st.markdown(f"<div class='mtp-legend'>{spans}</div>", unsafe_allow_html=True)


def line_chart(df_long: pd.DataFrame, series_colors: dict[str, tuple[str, tuple[int, int] | None]], height: int = 380):
    base = alt.Chart(df_long).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        y=alt.Y("value:Q", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        tooltip=["date:T", "Serie:N", alt.Tooltip("value:Q", format=".2f")],
    )
    layers = []
    for serie, (color, dash) in series_colors.items():
        mark_kwargs = {"color": color, "size": 2 if dash is None else 1.5}
        if dash:
            mark_kwargs["strokeDash"] = list(dash)
        layers.append(base.transform_filter(alt.datum.Serie == serie).mark_line(**mark_kwargs))
    chart = layers[0]
    for l in layers[1:]:
        chart = chart + l
    return chart.properties(height=height, background=C_BG).configure_view(strokeWidth=0)


def normalize(series: pd.Series, name: str) -> pd.DataFrame:
    df = (series / series.iloc[0]).reset_index()
    df.columns = ["date", "value"]
    df["Serie"] = name
    return df


def fmt_pct(x: float) -> str:
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt_num(x: float) -> str:
    return f"{x:.2f}" if pd.notna(x) else "n/a"


def fmt_row(s: dict) -> dict:
    return {
        "n": s["n_trades"], "Trefferquote": s["win_rate"], "Profit-Faktor": s["profit_factor"],
        "Sharpe": s["sharpe"], "CAGR": s["cagr"], "MaxDD": s["max_drawdown"],
    }


# ------------------------------------------------------------------ cached data / simulation
@st.cache_data(ttl="6h", show_spinner="Lade 10 Jahre Marktdaten (Dukascopy, 5 Maerkte)...")
def load_markets() -> dict[str, pd.DataFrame]:
    data = {}
    for key, tf, label, _spread in MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = df
    return data


@st.cache_data(ttl="6h", show_spinner="Lade USDCAD (Testkandidat fuer die Standard-Konfiguration)...")
def load_extra_markets() -> dict[str, pd.DataFrame]:
    data = {}
    for key, tf, label, _spread in STANDARD_EXTRA_MARKETS:
        df = fetch_timeframe(key, tf, START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = df
    return data


def _combined(trades_by_market: dict[str, pd.DataFrame], index_by_market: dict[str, pd.DatetimeIndex]) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    combined_trades = pd.concat(trades_by_market.values(), ignore_index=True) if trades_by_market else pd.DataFrame()
    starts = [idx.min() for idx in index_by_market.values() if len(idx)]
    ends = [idx.max() for idx in index_by_market.values() if len(idx)]
    full_index = pd.date_range(min(starts), max(ends), freq="D") if starts else pd.DatetimeIndex([])
    return combined_trades, full_index


@st.cache_data(ttl="6h", show_spinner="Simuliere Baseline (Bot wie er ist, ohne Filter)...")
def run_baseline(_data: dict[str, pd.DataFrame]) -> dict:
    per_market = {}
    trades_full, idx_full = {}, {}
    trades_is, idx_is = {}, {}
    trades_oos, idx_oos = {}, {}
    for label, df in _data.items():
        spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        trades_full[label], idx_full[label] = trades, signaled.index
        trades_is[label] = trades[trades["entry_time"] < SPLIT]
        idx_is[label] = signaled[signaled.index < SPLIT].index
        trades_oos[label] = trades[trades["entry_time"] >= SPLIT]
        idx_oos[label] = signaled[signaled.index >= SPLIT].index
        per_market[label] = {
            "full": summarize(trades_full[label], idx_full[label]),
            "is": summarize(trades_is[label], idx_is[label]),
            "oos": summarize(trades_oos[label], idx_oos[label]),
        }

    comb_full, fi_full = _combined(trades_full, idx_full)
    comb_is, fi_is = _combined(trades_is, idx_is)
    comb_oos, fi_oos = _combined(trades_oos, idx_oos)

    return {
        "per_market": per_market,
        "combined_full": summarize(comb_full, fi_full),
        "combined_is": summarize(comb_is, fi_is),
        "combined_oos": summarize(comb_oos, fi_oos),
        "trades_full": comb_full, "index_full": fi_full,
        "trades_oos": comb_oos, "index_oos": fi_oos,
        "regime": regime_decomposition(comb_full),
    }


@st.cache_data(ttl="6h", show_spinner="Sweepe ADX-Filter (nur In-Sample) und validiere Out-of-Sample...")
def run_adx_sweep(_data: dict[str, pd.DataFrame]) -> dict:
    sweep_rows = []
    for adx_min in ADX_MIN_CANDIDATES:
        is_trades, is_idx = {}, {}
        for label, df in _data.items():
            spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
            signaled = run_pipeline(df, adx_min=adx_min)
            is_mask = signaled.index < SPLIT
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            is_trades[label] = simulate_trades(signaled[is_mask], cfg)
            is_idx[label] = signaled[is_mask].index
        comb, fi = _combined(is_trades, is_idx)
        s = summarize(comb, fi)
        sweep_rows.append({"adx_min": adx_min, **s})

    per_market_oos, trades_oos, idx_oos = {}, {}, {}
    for label, df in _data.items():
        spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
        signaled = run_pipeline(df, adx_min=CHOSEN_ADX_MIN)
        oos_mask = signaled.index >= SPLIT
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades_oos[label] = simulate_trades(signaled[oos_mask], cfg)
        idx_oos[label] = signaled[oos_mask].index
        per_market_oos[label] = summarize(trades_oos[label], idx_oos[label])

    comb_oos, fi_oos = _combined(trades_oos, idx_oos)
    all_oos = comb_oos
    outlier = None
    if not all_oos.empty:
        sorted_ret = all_oos["return_pct"].sort_values(ascending=False)
        without_best = all_oos.drop(index=sorted_ret.index[0])
        outlier = {"with_best": summarize(all_oos, fi_oos), "without_best": summarize(without_best, fi_oos)}

    return {
        "sweep": pd.DataFrame(sweep_rows),
        "per_market_oos": per_market_oos,
        "combined_oos": summarize(comb_oos, fi_oos),
        "trades_oos": comb_oos, "index_oos": fi_oos,
        "outlier": outlier,
    }


@st.cache_data(ttl="6h", show_spinner="Berechne Break-even-Spread je Markt (Out-of-Sample)...")
def run_spread_sensitivity(_data: dict[str, pd.DataFrame]) -> dict:
    rows = []
    oos_filtered_by_market = {}
    for label, df in _data.items():
        spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
        base_cfg = BacktestConfig(stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)

        sig_nf = run_pipeline(df)
        oos_nf = sig_nf[sig_nf.index >= SPLIT]
        be_nf = breakeven_spread_bps(oos_nf, base_cfg, lo=0.0, hi=100.0)

        sig_f = run_pipeline(df, adx_min=CHOSEN_ADX_MIN)
        oos_f = sig_f[sig_f.index >= SPLIT]
        be_f = breakeven_spread_bps(oos_f, base_cfg, lo=0.0, hi=100.0)
        oos_filtered_by_market[label] = oos_f

        rows.append({
            "Markt": label, "Angenommener Spread (bp)": spread_bps,
            "Break-even ohne Filter (bp)": be_nf, "Break-even mit ADX-Filter (bp)": be_f,
            "Puffer (bp)": be_f - spread_bps,
        })

    sweep_rows = []
    for test_bps in SPREAD_SWEEP_BPS:
        trades_by_market, idx_by_market = {}, {}
        for label, oos_f in oos_filtered_by_market.items():
            cfg = BacktestConfig(spread_bps=test_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            trades_by_market[label] = simulate_trades(oos_f, cfg)
            idx_by_market[label] = oos_f.index
        comb, fi = _combined(trades_by_market, idx_by_market)
        s = summarize(comb, fi)
        sweep_rows.append({"Spread (bp)": test_bps, **s})

    return {"breakeven": pd.DataFrame(rows), "sweep": pd.DataFrame(sweep_rows)}


@st.cache_data(ttl="6h", show_spinner="Simuliere $100k-Konto (1% Risiko, max. 3 gleichzeitige Positionen)...")
def run_account_sim(_data: dict[str, pd.DataFrame]) -> dict:
    def trades_for(adx_min: float | None) -> dict[str, pd.DataFrame]:
        out = {}
        for label, df in _data.items():
            spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
            signaled = run_pipeline(df, adx_min=adx_min)
            cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
            out[label] = simulate_trades(signaled, cfg)
        return out

    def slice_period(trades_by_market: dict[str, pd.DataFrame], start, end) -> dict[str, pd.DataFrame]:
        out = {}
        for label, df in trades_by_market.items():
            d = df
            if start is not None:
                d = d[d["entry_time"] >= start]
            if end is not None:
                d = d[d["entry_time"] < end]
            out[label] = d
        return out

    result = {}
    for variant, adx_min in [("baseline", None), ("filtered", CHOSEN_ADX_MIN)]:
        trades_by_market = trades_for(adx_min)
        periods = {"full": trades_by_market, "is": slice_period(trades_by_market, None, SPLIT), "oos": slice_period(trades_by_market, SPLIT, None)}
        result[variant] = {}
        for period_name, period_trades in periods.items():
            sim = simulate_account(period_trades, starting_equity=STARTING_EQUITY, risk_pct=RISK_PCT, max_concurrent=MAX_CONCURRENT)
            result[variant][period_name] = {"sim": sim, "stats": account_stats(sim, starting_equity=STARTING_EQUITY)}
    return result


@st.cache_data(ttl="6h", show_spinner="Sweepe TP/SL (nur In-Sample, ADX>=25 Filter fest) und validiere Out-of-Sample...")
def run_tp_sl_be_sweep(_data: dict[str, pd.DataFrame]) -> dict:
    signaled_by_market = {}
    for label, df in _data.items():
        spread_bps = next(s for k, tf, lab, s in MARKETS if lab == label)
        signaled_by_market[label] = (run_pipeline(df, adx_min=CHOSEN_ADX_MIN), spread_bps)

    def run_period(cfg_kwargs: dict, start, end):
        trades_by_market, idx_by_market = {}, {}
        for label, (signaled, spread_bps) in signaled_by_market.items():
            cfg = BacktestConfig(spread_bps=spread_bps, **cfg_kwargs)
            trades = simulate_trades(signaled, cfg)
            if start is not None:
                trades = trades[trades["entry_time"] >= start]
            if end is not None:
                trades = trades[trades["entry_time"] < end]
            sub_idx = signaled.index
            if start is not None:
                sub_idx = sub_idx[sub_idx >= start]
            if end is not None:
                sub_idx = sub_idx[sub_idx < end]
            trades_by_market[label], idx_by_market[label] = trades, sub_idx
        comb, fi = _combined(trades_by_market, idx_by_market)
        return summarize(comb, fi), trades_by_market, idx_by_market

    base_kwargs = {"stop_atr_mult": ATR_STOP_MULT, "use_vwap_target": False, "take_profit_r": RR_RATIO}
    s_base_full, _, _ = run_period(base_kwargs, None, None)
    s_base_is, _, _ = run_period(base_kwargs, None, SPLIT)
    s_base_oos, _, _ = run_period(base_kwargs, SPLIT, None)

    sweep_rows = []
    for stop_atr in STOP_ATR_CANDIDATES:
        for tp_r in TP_R_CANDIDATES:
            kwargs = {"stop_atr_mult": stop_atr, "use_vwap_target": False, "take_profit_r": tp_r}
            s, _, _ = run_period(kwargs, None, SPLIT)
            sweep_rows.append({"stop_atr": stop_atr, "tp_r": tp_r, **s})
    sweep = pd.DataFrame(sweep_rows)
    eligible = sweep[sweep["n_trades"] >= MIN_IS_TRADES_TPSL]
    best = eligible.loc[eligible["sharpe"].idxmax()]
    chosen_stop, chosen_tp = float(best["stop_atr"]), float(best["tp_r"])

    chosen_kwargs = {"stop_atr_mult": chosen_stop, "use_vwap_target": False, "take_profit_r": chosen_tp}
    s_chosen_full, _, _ = run_period(chosen_kwargs, None, None)
    s_chosen_oos, chosen_oos_tbm, chosen_oos_idx = run_period(chosen_kwargs, SPLIT, None)

    be_rows = []
    for be in BE_TRIGGER_CANDIDATES:
        kwargs = {**chosen_kwargs, "breakeven_trigger_r": be}
        s, _, _ = run_period(kwargs, None, SPLIT)
        be_rows.append({"be_trigger_r": be, **s})
    be_sweep = pd.DataFrame(be_rows)
    be_eligible = be_sweep[be_sweep["n_trades"] >= MIN_IS_TRADES_TPSL]
    be_best = be_eligible.loc[be_eligible["sharpe"].idxmax()]
    chosen_be = None if pd.isna(be_best["be_trigger_r"]) else float(be_best["be_trigger_r"])

    final_kwargs = {**chosen_kwargs, "breakeven_trigger_r": chosen_be}
    s_final_full, _, _ = run_period(final_kwargs, None, None)
    s_final_oos, final_oos_tbm, final_oos_idx = run_period(final_kwargs, SPLIT, None)

    all_final_oos = pd.concat(final_oos_tbm.values(), ignore_index=True)
    outlier = None
    if not all_final_oos.empty:
        sorted_ret = all_final_oos["return_pct"].sort_values(ascending=False)
        without_best = all_final_oos.drop(index=sorted_ret.index[0])
        full_idx = pd.date_range(min(idx.min() for idx in final_oos_idx.values()), max(idx.max() for idx in final_oos_idx.values()), freq="D")
        outlier = {"with_best": summarize(all_final_oos, full_idx), "without_best": summarize(without_best, full_idx)}

    return {
        "base_full": s_base_full, "base_is": s_base_is, "base_oos": s_base_oos,
        "sweep": sweep, "chosen_stop": chosen_stop, "chosen_tp": chosen_tp,
        "chosen_full": s_chosen_full, "chosen_oos": s_chosen_oos,
        "be_sweep": be_sweep, "chosen_be": chosen_be,
        "final_full": s_final_full, "final_oos": s_final_oos,
        "outlier": outlier,
    }


@st.cache_data(ttl="6h", show_spinner="Lade Gold-Tagesschlusskurse (fuer den Silber-Alignment-Filter)...")
def load_gold_daily_close() -> pd.Series:
    d1 = fetch_timeframe("GOLD", "D1", START, END)
    close = d1["Close"]
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    return close


@st.cache_data(ttl="6h", show_spinner="Berechne die empfohlene Standard-Konfiguration (ohne Platin, Silber-aligned, +USDCAD)...")
def run_standard_recommendation(_data: dict[str, pd.DataFrame], _extra_data: dict[str, pd.DataFrame], _gold_daily_close: pd.Series) -> dict:
    all_data = {**_data, **_extra_data}
    all_market_info = MARKETS + STANDARD_EXTRA_MARKETS

    def build(label: str, use_overlay: bool) -> pd.DataFrame:
        df = all_data[label]
        spread_bps = next(s for k, tf, lab, s in all_market_info if lab == label)
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades_overlay(signaled, cfg, max_wait_bars=OVERLAY_WAIT_BARS) if use_overlay else simulate_trades(signaled, cfg)
        if label == "XAGUSD":
            trades = alignment_filter(trades, _gold_daily_close)
        return trades, signaled.index

    def period_trades(trades: pd.DataFrame, idx: pd.DatetimeIndex, start, end):
        t = trades[(trades["entry_time"] >= start) & (trades["entry_time"] < end)] if end is not None else trades[trades["entry_time"] >= start]
        i = idx[(idx >= start) & (idx < end)] if end is not None else idx[idx >= start]
        return t, i

    base_full, overlay_full = {}, {}
    base_idx = {}
    for label in STANDARD_MARKET_LABELS:
        t_base, idx = build(label, use_overlay=False)
        t_overlay, _ = build(label, use_overlay=True)
        base_full[label], overlay_full[label] = t_base, t_overlay
        base_idx[label] = idx

    per_market_oos = {}
    base_oos_tbm, base_oos_idx = {}, {}
    for label in STANDARD_MARKET_LABELS:
        t_oos, i_oos = period_trades(base_full[label], base_idx[label], NEW_SPLIT, NEW_OOS_END)
        base_oos_tbm[label], base_oos_idx[label] = t_oos, i_oos
        per_market_oos[label] = summarize(t_oos, i_oos)

    comb_oos, fi_oos = _combined(base_oos_tbm, base_oos_idx)

    overlay_oos_tbm, overlay_oos_idx = {}, {}
    for label in STANDARD_MARKET_LABELS:
        t_oos, i_oos = period_trades(overlay_full[label], base_idx[label], NEW_SPLIT, NEW_OOS_END)
        overlay_oos_tbm[label], overlay_oos_idx[label] = t_oos, i_oos
    comb_overlay_oos, fi_overlay_oos = _combined(overlay_oos_tbm, overlay_oos_idx)

    account_by_risk = {}
    for risk_pct in [0.005, 0.01, 0.015, 0.02]:
        sim = simulate_account(base_oos_tbm, starting_equity=STARTING_EQUITY, risk_pct=risk_pct, max_concurrent=3)
        account_by_risk[risk_pct] = account_stats(sim, starting_equity=STARTING_EQUITY)

    return {
        "per_market_oos": per_market_oos,
        "combined_oos": summarize(comb_oos, fi_oos),
        "combined_overlay_oos": summarize(comb_overlay_oos, fi_overlay_oos),
        "trades_oos": comb_oos, "index_oos": fi_oos,
        "account_by_risk": account_by_risk,
        # full-history, per-market trades (incl. the XAGUSD alignment filter)
        # for the "Chart & Entries" tab -- not sliced to OOS, since the chart
        # lets the user pick their own date window.
        "trades_by_market_full": base_full,
    }


@st.cache_data(ttl="6h", show_spinner="Kalibriere Risiko-Parameter (FK1/FK2/EK, volle Historie + 2023-2026)...")
def run_risk_management(_data: dict[str, pd.DataFrame], _extra_data: dict[str, pd.DataFrame], _gold_daily_close: pd.Series) -> dict:
    all_data = {**_data, **_extra_data}
    all_market_info = MARKETS + STANDARD_EXTRA_MARKETS

    trades_by_market, daily_low_by_market = {}, {}
    for label in STANDARD_MARKET_LABELS:
        df = all_data[label]
        spread_bps = next(s for k, tf, lab, s in all_market_info if lab == label)
        signaled = run_pipeline(df)
        cfg = BacktestConfig(spread_bps=spread_bps, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        trades = simulate_trades(signaled, cfg)
        if label == "XAGUSD":
            trades = alignment_filter(trades, _gold_daily_close)
        trades_by_market[label] = trades
        daily_low_by_market[label] = df["low"].resample("1D").min().dropna()

    trades_2023 = {m: t[t["entry_time"] >= NEW_IS_START] for m, t in trades_by_market.items()}

    sweeps, chosen = {}, {}
    for period_name, tbm in [("Volle Historie (2016-2026)", trades_by_market), ("Nur 2023-2026", trades_2023)]:
        sweeps[period_name], chosen[period_name] = {}, {}
        for profile_name, limits in RISK_PROFILES.items():
            cap = limits.get("per_position_cap")
            candidates = [r for r in RISK_PCT_CANDIDATES if cap is None or r <= cap]
            sweep = sweep_risk_pct(
                tbm, daily_low_by_market, candidates,
                max_daily_dd_limit=limits["daily"], max_total_dd_limit=limits["total"],
                starting_equity=STARTING_EQUITY, max_concurrent=3,
            )
            sweeps[period_name][profile_name] = sweep
            compliant = sweep[sweep["compliant"]]
            chosen[period_name][profile_name] = compliant.loc[compliant["risk_pct"].idxmax()] if not compliant.empty else None

    ou_results = {}
    for period_name, tbm in [("Volle Historie (2016-2026)", trades_by_market), ("Nur 2023-2026", trades_2023)]:
        res = simulate_open_risk_daily(tbm, daily_low_by_market, risk_pct=OU_RISK_PCT, max_total_risk_pct=OU_MAX_TOTAL_RISK_PCT, starting_equity=STARTING_EQUITY)
        compliance = {}
        for profile_name, limits in RISK_PROFILES.items():
            daily_ok = limits["daily"] is None or abs(res.max_daily_dd_pct) <= limits["daily"]
            total_ok = abs(res.max_total_dd_pct) <= limits["total"]
            compliance[profile_name] = daily_ok and total_ok
        ou_results[period_name] = {"result": res, "compliance": compliance}

    return {"sweeps": sweeps, "chosen": chosen, "ou_results": ou_results}


# ------------------------------------------------------------------ header
st.markdown("## :material/smart_toy: Trend Pullback")
st.caption(
    "Backtest-Replikation des eigenen, bereits laufenden Demo-Bots (MT5, Python/MetaTrader5-API) -- "
    "long-only Trend+Pullback auf Gold/Silber/Platin (H1) und CHFJPY/USDJPY (H4). Die Signal-Formeln "
    "hier sind 1:1 aus der Bot-Quelle uebernommen (strategy.py), nicht neu erfunden."
)

caveat_box(
    "<b>&#9888; Ehrlicher Hauptbefund:</b> Ueber die volle 10-Jahres-Historie war die Strategie in "
    "<b>jedem einzelnen der 5 Maerkte</b> 2016-2022 unprofitabel oder bestenfalls neutral (PF 0.48-0.97) "
    "und ist ausschliesslich seit 2023 profitabel geworden. Die Kommentare in der Bot-config.py "
    "(\"PF 1.92 im 1h-Fixed-Test\" fuer Gold usw.) sehen nach einem kurzen/aktuellen Testfenster aus, "
    "nicht nach einem vollen 10-Jahres-Backtest -- kein Beweis fuer einen strukturellen, "
    "regimeunabhaengigen Edge. <b>Kein Live-Handel hier</b> -- diese Seite zeigt Backtest-Ergebnisse, "
    "keine automatisierte Ausfuehrung (die laeuft ausschliesslich im separaten Bot-Ordner, auf einem "
    "Demo-Konto).",
    kind="alert",
)

caveat_box(
    "<b>&#11088; Aktuelle Standard-Empfehlung (Stand 2026-08-14):</b> <b>Platin raus, Silber gefiltert "
    "durch Gold-Alignment, USDCAD testweise dazu</b> (Gold/Silber/CHFJPY/USDJPY/USDCAD, getestet auf dem "
    "regime-verengten Fenster 2023-2024 IS / 2024-2026 OOS) -- siehe Tab <b>\"Empfehlung (Standard)\"</b>. "
    "USDCAD hat nur 7 OOS-Trades (duenne Stichprobe) -- als Testkandidat markiert, nicht als endgueltig "
    "validiert. Die uebrigen Tabs zeigen weiterhin den vollen Forschungsweg dorthin (5 Maerkte inkl. "
    "Platin, alte 2016-2022/2023-2026-Aufteilung) und bleiben als Dokumentation stehen.",
    kind="good",
)

with st.expander(":material/menu_book: Strategie-Regeln (1:1 aus dem Live-Bot)", expanded=False):
    st.markdown(
        f"""
        <div class="mtp-writeup">
        Long-only, eine Position pro Markt, feste ATR-Stop/R-Multiple-Exits -- keine Trailing-Stops,
        keine Zeit-Exits, kein Grid, kein Martingale.
        </div>
        <div class="mtp-caveats">
        <b>1. Trend-Filter:</b> Schlusskurs &gt; EMA({TREND_LEN})<br>
        <b>2. Pullback-Trigger:</b> RSI({RSI_LEN}) kreuzt auf derselben Kerze von unten ueber {RSI_OVERSOLD:.0f}
        (Pullback endet, Trend nimmt wieder auf)<br>
        <b>3. Stop:</b> Entry &minus; ATR({ATR_LEN}) &times; {ATR_STOP_MULT:.1f}<br>
        <b>4. Take-Profit:</b> {RR_RATIO:.1f}R (Chance-Risiko-Verhaeltnis {RR_RATIO:.1f})<br><br>
        Alle Formeln (EMA/RSI/ATR) sind hier wortgleich aus der Bot-Quelle uebernommen (nicht die
        anders geseedete Wilder-Variante, die sonst in diesem Repo ueblich ist), damit die Signale hier
        mit dem uebereinstimmen, was der Live-Bot auf denselben Kerzen tatsaechlich ausgeloest haette.
        </div>
        """,
        unsafe_allow_html=True,
    )

data = load_markets()
extra_data = load_extra_markets()
gold_daily_close = load_gold_daily_close()
standard_result = run_standard_recommendation(data, extra_data, gold_daily_close)
baseline = run_baseline(data)
adx_result = run_adx_sweep(data)
spread_result = run_spread_sensitivity(data)
account_result = run_account_sim(data)
tpsl_result = run_tp_sl_be_sweep(data)
risk_result = run_risk_management(data, extra_data, gold_daily_close)

tab_standard, tab_chart, tab_overview, tab_adx, tab_spread, tab_account, tab_tpsl, tab_risk, tab_mc = st.tabs([
    ":material/star: Empfehlung (Standard)",
    ":material/candlestick_chart: Chart & Entries",
    ":material/show_chart: Baseline (Bot wie er ist)",
    ":material/tune: ADX-Filter",
    ":material/payments: Spread-Sensitivitaet",
    ":material/account_balance: Konto-Simulation ($100k)",
    ":material/target: TP/SL & Breakeven",
    ":material/shield: Risk Management (FK & EK)",
    ":material/casino: Monte Carlo",
], on_change="rerun")

# ------------------------------------------------------------------ Tab: Standard recommendation
def _render_tab_tab_standard():
    caveat_box(
        "<b>Standard-Konfiguration:</b> Gold, Silber (gefiltert -- nur Trades, bei denen Golds eigener "
        "5-Tage-Trend positiv war), CHFJPY, USDJPY, <b>USDCAD (testweise, 2026-08-14 hinzugefuegt)</b>. "
        "Platin komplett entfernt. Bot-Default-Parameter unveraendert (EMA150/RSI14&gt;35/ATR14&times;2.0/"
        "RR2.0, kein ADX-Filter). Getestet auf dem regime-verengten Fenster: IS 2023-01 bis 2024-07, "
        "OOS 2024-07 bis 2026-08 -- nicht die volle 10-Jahres-Historie, siehe Baseline-Tab fuer den Grund. "
        "USDCAD hat in dieser Periode nur 7 OOS-Trades -- deutlich duenner besetzt als die anderen 4 "
        "Maerkte, Ergebnis entsprechend vorsichtig zu interpretieren."
    )

    r = standard_result
    c_oos = r["combined_oos"]
    tile_row([
        ("PF (OOS)", fmt_num(c_oos["profit_factor"])),
        ("SHARPE (OOS)", fmt_num(c_oos["sharpe"])),
        ("CAGR (OOS)", fmt_pct(c_oos["cagr"])),
        ("MAXDD (OOS)", fmt_pct(c_oos["max_drawdown"])),
        ("TRADES (OOS)", str(c_oos["n_trades"])),
        ("MAERKTE", "5 (ohne Platin, +USDCAD testweise)"),
    ])

    section_title("Pro Markt (Out-of-Sample, Standard-Konfiguration)")
    rows = [{"Markt": label, **fmt_row(s)} for label, s in r["per_market_oos"].items()]
    st.dataframe(
        pd.DataFrame(rows), hide_index=True,
        column_config={
            "Trefferquote": st.column_config.NumberColumn(format=".1%"),
            "Profit-Faktor": st.column_config.NumberColumn(format="%.3f"),
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "CAGR": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD": st.column_config.NumberColumn(format="+.1%"),
        },
    )

    section_title(f"$100k-Konto bei verschiedenen Risikostufen (OOS, max. 3 gleichzeitige Positionen)")
    acc_rows = []
    for risk_pct, s in r["account_by_risk"].items():
        acc_rows.append({
            "Risiko/Trade": risk_pct, "n genommen": s["n_trades"], "uebersprungen": s["n_skipped"],
            "Endkapital": s["final_equity"], "Gesamt-Return": s["total_return"],
            "MaxDD": s["max_drawdown_pct"], "MaxDD ($)": s["max_drawdown_usd"],
        })
    st.dataframe(
        pd.DataFrame(acc_rows), hide_index=True,
        column_config={
            "Risiko/Trade": st.column_config.NumberColumn(format=".2%"),
            "Endkapital": st.column_config.NumberColumn(format="$%.0f"),
            "Gesamt-Return": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD ($)": st.column_config.NumberColumn(format="$%.0f"),
        },
    )

    section_title("Execution-Overlay-Test (Entry verzoegert bis zur ersten Gegenbewegung)", color=C_ORANGE)
    ov = r["combined_overlay_oos"]
    tile_row([
        ("PF OHNE OVERLAY", fmt_num(c_oos["profit_factor"])),
        ("PF MIT OVERLAY", fmt_num(ov["profit_factor"])),
        ("SHARPE OHNE OVERLAY", fmt_num(c_oos["sharpe"])),
        ("SHARPE MIT OVERLAY", fmt_num(ov["sharpe"])),
        ("MAXDD OHNE OVERLAY", fmt_pct(c_oos["max_drawdown"])),
        ("MAXDD MIT OVERLAY", fmt_pct(ov["max_drawdown"])),
    ])
    caveat_box(
        "<b>Ergebnis: neutral, keine Empfehlung.</b> Der Execution-Overlay (Entry erst bei der ersten "
        "Gegen-Kerze nach dem Signal, sonst nach 5 Baren verworfen -- Idee aus Zarattini &amp; Pagani "
        "2026, bereits erfolgreich bei Gold Asian-Range-Breakout eingesetzt) verschiebt hier nur das "
        "Profil (Sharpe/PF praktisch gleich, CAGR etwas niedriger, MaxDD etwas besser) -- pro Markt "
        "gemischt (hilft Gold/USDJPY, schadet dem bereits gefilterten Silber). Eine 3-Werte-"
        "Sensitivitaetspruefung (3/5/10 Baren Wartezeit) zeigte grosse Ausschlaege in beide Richtungen "
        "-- ohne vorherige IS-Auswahl waere jede Wahl reines Data-Snooping. <b>Nicht Teil der "
        "Standard-Empfehlung.</b>"
    )

    section_title("Portfolio-Equity, Standard-Konfiguration (OOS)")
    daily_std = trades_to_daily_returns(r["trades_oos"], r["index_oos"])
    equity_std = (1 + daily_std).cumprod()
    st.altair_chart(line_chart(normalize(equity_std, "Standard (4 Maerkte)"), {"Standard (4 Maerkte)": (C_GREEN, None)}))

# ------------------------------------------------------------------ Tab: Chart & Entries
def _render_tab_tab_chart():
    caveat_box(
        "Interaktiver Kerzenchart (TradingView Lightweight Charts) mit den tatsaechlichen Backtest-"
        "Entries/Exits der Standard-Konfiguration ueberlagert -- blaue Pfeile nach oben = Long-Entry, "
        "Pfeile nach unten am Exit farbcodiert nach Ausstiegsgrund (gruen = Take-Profit, rot = Stop-Loss, "
        "orange = Breakeven). Reine Backtest-Simulation -- keine Live-Trades des laufenden Demo-Bots."
    )

    trades_by_market_full = standard_result["trades_by_market_full"]
    all_chart_data = {**data, **extra_data}

    c1, c2 = st.columns([1, 3])
    with c1:
        chart_market = st.selectbox("Markt", STANDARD_MARKET_LABELS, index=0, key="chart_market")

    chart_df_full = all_chart_data[chart_market]
    idx = chart_df_full.index
    tz = idx.tz
    idx_naive = idx.tz_localize(None) if tz is not None else idx
    min_dt, max_dt = idx_naive.min().to_pydatetime(), idx_naive.max().to_pydatetime()
    default_start = max(min_dt, max_dt - pd.Timedelta(days=120))

    with c2:
        date_range = st.slider(
            "Zeitraum", min_value=min_dt, max_value=max_dt,
            value=(default_start, max_dt), key="chart_range",
        )

    win_start, win_end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    if tz is not None:
        win_start, win_end = win_start.tz_localize(tz), win_end.tz_localize(tz)

    windowed = chart_df_full[(chart_df_full.index >= win_start) & (chart_df_full.index <= win_end)]
    MAX_BARS = 3000
    if len(windowed) > MAX_BARS:
        st.warning(f"Zeitraum zu lang fuer eine fluessige Darstellung ({len(windowed)} Kerzen) -- zeige die letzten {MAX_BARS}.")
        windowed = windowed.iloc[-MAX_BARS:]

    trades_market = trades_by_market_full.get(chart_market, pd.DataFrame())
    if not trades_market.empty and len(windowed):
        trades_window = trades_market[
            (trades_market["entry_time"] >= windowed.index.min()) & (trades_market["entry_time"] <= windowed.index.max())
        ]
    else:
        trades_window = trades_market

    if windowed.empty:
        st.info("Keine Kerzen im gewaehlten Zeitraum.")
    else:
        candles = [
            {"time": int(ts.timestamp()), "open": float(o), "high": float(h), "low": float(lo), "close": float(cl)}
            for ts, o, h, lo, cl in zip(windowed.index, windowed["open"], windowed["high"], windowed["low"], windowed["close"])
        ]

        EXIT_COLORS = {"target": C_GREEN, "stop": C_RED, "breakeven": C_ORANGE, "data_end": C_MUTED, "max_hold": C_MUTED}
        EXIT_LABELS = {"target": "TP", "stop": "SL", "breakeven": "BE", "data_end": "ENDE", "max_hold": "ZEIT"}
        markers = []
        for _, t in trades_window.iterrows():
            markers.append({
                "time": int(t["entry_time"].timestamp()), "position": "belowBar",
                "color": C_BLUE, "shape": "arrowUp", "text": "BUY",
            })
            reason = t["exit_reason"]
            markers.append({
                "time": int(t["exit_time"].timestamp()), "position": "aboveBar",
                "color": EXIT_COLORS.get(reason, C_MUTED), "shape": "arrowDown",
                "text": EXIT_LABELS.get(reason, reason),
            })
        markers.sort(key=lambda m: m["time"])

        n_wins = int((trades_window["exit_reason"] == "target").sum()) if not trades_window.empty else 0
        n_losses = int((trades_window["exit_reason"] == "stop").sum()) if not trades_window.empty else 0
        n_other = len(trades_window) - n_wins - n_losses
        st.caption(
            f"{len(windowed)} Kerzen | {len(trades_window)} Trades im Fenster "
            f"({n_wins} Take-Profit, {n_losses} Stop-Loss, {n_other} sonstige)"
        )

        chart_html = f"""
        <div id="tpchart" style="width:100%;height:560px;"></div>
        <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
        <script>
          const el = document.getElementById('tpchart');
          const chart = LightweightCharts.createChart(el, {{
            width: el.clientWidth,
            height: 560,
            layout: {{ background: {{ color: '{C_BG}' }}, textColor: '{C_BODY}' }},
            grid: {{ vertLines: {{ color: '{C_GRID}' }}, horzLines: {{ color: '{C_GRID}' }} }},
            timeScale: {{ timeVisible: true, secondsVisible: false, borderColor: '{C_BORDER}' }},
            rightPriceScale: {{ borderColor: '{C_BORDER}' }},
          }});
          const series = chart.addCandlestickSeries({{
            upColor: '{C_GREEN}', downColor: '{C_RED}',
            borderUpColor: '{C_GREEN}', borderDownColor: '{C_RED}',
            wickUpColor: '{C_GREEN}', wickDownColor: '{C_RED}',
          }});
          series.setData({json.dumps(candles)});
          series.setMarkers({json.dumps(markers)});
          chart.timeScale().fitContent();
          new ResizeObserver(() => {{
            chart.applyOptions({{ width: el.clientWidth }});
          }}).observe(el);
        </script>
        """
        st.iframe(chart_html, height=580)

# ------------------------------------------------------------------ Tab: Baseline
def _render_tab_tab_overview():
    cf, cis, coos = baseline["combined_full"], baseline["combined_is"], baseline["combined_oos"]
    tile_row([
        ("N TRADES (FULL)", str(cf["n_trades"])),
        ("PF FULL", fmt_num(cf["profit_factor"])),
        ("PF IS (2016-22)", fmt_num(cis["profit_factor"])),
        ("PF OOS (2023-26)", fmt_num(coos["profit_factor"])),
        ("SHARPE FULL", fmt_num(cf["sharpe"])),
        ("MAXDD FULL", fmt_pct(cf["max_drawdown"])),
    ])

    section_title("Portfolio-Equity (alle 5 Maerkte, gleichgewichtet kombiniert -- ohne die 3-Positionen-Kappe des Bots)")
    daily = trades_to_daily_returns(baseline["trades_full"], baseline["index_full"])
    equity = (1 + daily).cumprod()
    st.altair_chart(line_chart(normalize(equity, "Portfolio (Baseline)"), {"Portfolio (Baseline)": (C_ORANGE, None)}))
    st.caption(
        "Vereinfachung: die 5 Maerkte werden hier so kombiniert, als waere in jedem offenen Trade "
        "gleichzeitig voll investiert -- der Bot begrenzt real auf max. 3 gleichzeitige Positionen "
        "(Metalle korreliert). Reales Portfolio-Risiko duerfte dadurch etwas geglaettet sein."
    )

    section_title("Pro Markt: Full / In-Sample (2016-22) / Out-of-Sample (2023-26)")
    rows = []
    for label, stats in baseline["per_market"].items():
        rows.append({
            "Markt": label,
            "n (Full)": stats["full"]["n_trades"],
            "PF (Full)": stats["full"]["profit_factor"], "Sharpe (Full)": stats["full"]["sharpe"],
            "Calmar (Full)": stats["full"]["calmar"], "CAGR (Full)": stats["full"]["cagr"], "MaxDD (Full)": stats["full"]["max_drawdown"],
            "PF (IS)": stats["is"]["profit_factor"], "Sharpe (IS)": stats["is"]["sharpe"],
            "PF (OOS)": stats["oos"]["profit_factor"], "Sharpe (OOS)": stats["oos"]["sharpe"],
        })
    st.dataframe(
        pd.DataFrame(rows), hide_index=True,
        column_config={
            "PF (Full)": st.column_config.NumberColumn(format="%.3f"),
            "Sharpe (Full)": st.column_config.NumberColumn(format="%.2f"),
            "Calmar (Full)": st.column_config.NumberColumn(format="%.2f"),
            "CAGR (Full)": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD (Full)": st.column_config.NumberColumn(format="+.1%"),
            "PF (IS)": st.column_config.NumberColumn(format="%.3f"),
            "Sharpe (IS)": st.column_config.NumberColumn(format="%.2f"),
            "PF (OOS)": st.column_config.NumberColumn(format="%.3f"),
            "Sharpe (OOS)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(
        "USDJPY faellt konsistent ab (Full- und IS-Sharpe negativ, sowohl mit als auch ohne ADX-Filter -- "
        "siehe ADX-Filter-Tab) -- der schwaechste der 5 Maerkte in dieser Strategie. CHFJPY und XPTUSD "
        "zeigen die staerksten OOS-Sharpes."
    )

    section_title("Regime-Zerlegung (Trendstaerke x Volatilitaets-Tertile bei Entry) -- Motivation fuer den ADX-Filter", color=C_GREEN)
    regime = baseline["regime"]
    st.dataframe(
        regime, hide_index=True,
        column_config={
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "avg_return_pct": st.column_config.NumberColumn("Oe. Return/Trade", format=".3%"),
            "n_trades": st.column_config.NumberColumn("n"),
        },
    )
    st.caption(
        "Trades bei ADX &ge; 25 (starker Trend) schneiden in jeder Volatilitaets-Tertile besser ab als "
        "bei ADX < 25 -- der Bot selbst hat KEINEN ADX-Filter, das ist reine Diagnose."
    )

# ------------------------------------------------------------------ Tab: ADX filter
def _render_tab_tab_adx():
    caveat_box(
        f"Disziplin wie bei den anderen Research-Skripten in diesem Repo: EIN adx_min wird "
        f"<b>ausschliesslich auf der In-Sample-Periode (2016-2022)</b> gewaehlt (gepoolt ueber alle "
        f"5 Maerkte, nicht pro Markt einzeln optimiert -- der Bot behandelt alle Maerkte gleich), "
        f"dann <b>unveraendert</b> auf Out-of-Sample (2023-2026) angewendet. Gewaehlt: "
        f"<b>adx_min = {CHOSEN_ADX_MIN:.0f}</b> (beste IS-Sharpe, n&ge;20)."
    )

    section_title("1. Sweep -- nur In-Sample (2016-2022), gepoolt")
    sweep = adx_result["sweep"].copy()
    sweep["adx_min"] = sweep["adx_min"].apply(lambda x: "kein Filter" if pd.isna(x) else f"{x:.0f}")
    st.dataframe(
        sweep[["adx_min", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]],
        hide_index=True,
        column_config={
            "adx_min": "ADX-Minimum", "n_trades": "n",
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            "cagr": st.column_config.NumberColumn("CAGR", format="+.1%"),
            "max_drawdown": st.column_config.NumberColumn("MaxDD", format="+.1%"),
        },
    )

    section_title("2. Validierung -- unveraendert auf Out-of-Sample (2023-2026)", color=C_GREEN)
    base_oos, filt_oos = baseline["combined_oos"], adx_result["combined_oos"]
    tile_row([
        ("PF OOS (ohne Filter)", fmt_num(base_oos["profit_factor"])),
        ("PF OOS (ADX>=25)", fmt_num(filt_oos["profit_factor"])),
        ("SHARPE OOS (ohne Filter)", fmt_num(base_oos["sharpe"])),
        ("SHARPE OOS (ADX>=25)", fmt_num(filt_oos["sharpe"])),
        ("MAXDD OOS (ohne Filter)", fmt_pct(base_oos["max_drawdown"])),
        ("MAXDD OOS (ADX>=25)", fmt_pct(filt_oos["max_drawdown"])),
    ])

    daily_base = trades_to_daily_returns(baseline["trades_oos"], baseline["index_oos"])
    daily_filt = trades_to_daily_returns(adx_result["trades_oos"], adx_result["index_oos"])
    eq_base, eq_filt = (1 + daily_base).cumprod(), (1 + daily_filt).cumprod()
    oos_long = pd.concat([normalize(eq_base, "Ohne Filter"), normalize(eq_filt, "ADX >= 25")])
    st.altair_chart(line_chart(oos_long, {"Ohne Filter": (C_MUTED, (5, 4)), "ADX >= 25": (C_GREEN, None)}))
    legend([("Ohne Filter (Bot wie er ist)", C_MUTED), ("Mit ADX>=25-Filter", C_GREEN)])

    caveat_box(
        f"<b>Der Filter haelt, was die IS-Diagnose versprach:</b> Profit-Faktor {fmt_num(base_oos['profit_factor'])} "
        f"&rarr; {fmt_num(filt_oos['profit_factor'])}, Sharpe {fmt_num(base_oos['sharpe'])} &rarr; {fmt_num(filt_oos['sharpe'])}, "
        f"MaxDD {fmt_pct(base_oos['max_drawdown'])} &rarr; {fmt_pct(filt_oos['max_drawdown'])} -- deutliche Verbesserung, "
        f"und zwar auf einer Periode, auf der der Filter NICHT gewaehlt wurde.",
        kind="good",
    )

    section_title("Pro Markt (Out-of-Sample, mit ADX>=25-Filter)")
    rows = [{"Markt": label, **fmt_row(s)} for label, s in adx_result["per_market_oos"].items()]
    st.dataframe(
        pd.DataFrame(rows), hide_index=True,
        column_config={
            "Trefferquote": st.column_config.NumberColumn(format=".1%"),
            "Profit-Faktor": st.column_config.NumberColumn(format="%.3f"),
            "Sharpe": st.column_config.NumberColumn(format="%.2f"),
            "CAGR": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD": st.column_config.NumberColumn(format="+.1%"),
        },
    )

    section_title("3. Outlier-Sensitivitaet (bester Einzeltrade aus dem gepoolten OOS entfernt)")
    outlier = adx_result["outlier"]
    if outlier is None:
        st.caption("Keine OOS-Trades mit diesem Filter.")
    else:
        wb, wob = outlier["with_best"], outlier["without_best"]
        c1, c2 = st.columns(2)
        with c1:
            st.metric("PF mit bestem Trade", fmt_num(wb["profit_factor"]))
        with c2:
            st.metric("PF ohne bestem Trade", fmt_num(wob["profit_factor"]))
        if wob["profit_factor"] > 1.0:
            st.caption(":material/check_circle: PF bleibt ueber 1.0 auch ohne den besten Einzeltrade -- kein reiner Ausreisser-Effekt.")
        else:
            st.caption(":material/warning: PF faellt ohne den besten Trade unter 1.0 -- Ergebnis haengt stark an einem Einzeltrade.")

# ------------------------------------------------------------------ Tab: Spread sensitivity
def _render_tab_tab_spread():
    caveat_box(
        "Dieses Repo hat keine echte historische Geld-/Brief-Spread-Historie -- alle bisherigen "
        "Ergebnisse nutzen eine <b>angenommene</b> Round-Trip-Spanne (10bp Metalle / 3bp CHFJPY / 1.5bp "
        "USDJPY). Diese Seite zeigt, wie weit der reale Broker-Spread von dieser Annahme abweichen "
        "koennte, bevor der Edge kippt -- ausschliesslich auf der Out-of-Sample-Periode (2023-2026), "
        "da die In-Sample-Periode schon <b>ohne</b> jegliche Kosten unprofitabel war."
    )

    section_title("Break-even-Spread je Markt (Out-of-Sample, Round-Trip in Basispunkten)")
    be = spread_result["breakeven"].copy()
    st.dataframe(
        be, hide_index=True,
        column_config={
            "Angenommener Spread (bp)": st.column_config.NumberColumn(format="%.1f"),
            "Break-even ohne Filter (bp)": st.column_config.NumberColumn(format="%.1f"),
            "Break-even mit ADX-Filter (bp)": st.column_config.NumberColumn(format="%.1f"),
            "Puffer (bp)": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.caption(
        "\"Break-even\" = Spread, bei dem der mittlere Trade-Return auf null faellt (bisektionsbasiert, "
        "Obergrenze 100bp -- ein Wert von 100.0 heisst \"noch nicht erreicht, sehr robust\", keine exakte "
        "Zahl). \"Puffer\" = Break-even minus angenommener Spread, mit ADX-Filter."
    )

    section_title("Portfolio (ADX>=25-Filter, Out-of-Sample): PF/Sharpe bei steigendem Spread")
    sw = spread_result["sweep"]
    chart_df = sw[["Spread (bp)", "profit_factor"]].rename(columns={"profit_factor": "Profit-Faktor"})
    bar = alt.Chart(chart_df).mark_bar(color=C_ORANGE).encode(
        x=alt.X("Spread (bp):O", title="Spread (bp)", axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        y=alt.Y("Profit-Faktor:Q", axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        tooltip=["Spread (bp)", alt.Tooltip("Profit-Faktor:Q", format=".3f")],
    ).properties(height=280, background=C_BG).configure_view(strokeWidth=0)
    st.altair_chart(bar)

    st.dataframe(
        sw[["Spread (bp)", "n_trades", "win_rate", "profit_factor", "sharpe"]], hide_index=True,
        column_config={
            "n_trades": "n",
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
        },
    )
    st.caption(
        "Ergebnis: der OOS-Edge ist robust gegen deutlich hoehere Spreads als angenommen -- aber das "
        "gilt nur fuer 2023-2026. Die IS-Periode (2016-2022) war schon bei Spread=0 unprofitabel, "
        "keine Spread-Annahme haette das gerettet."
    )

# ------------------------------------------------------------------ Tab: Account simulation
def _render_tab_tab_account():
    caveat_box(
        f"<b>Backtest-Parameter dieser Simulation:</b> Startkapital {STARTING_EQUITY:,.0f} USD &middot; "
        f"Risiko/Trade {RISK_PCT:.1%} des aktuellen Kontostands (fixed-fractional, compounding, auf realisiertem "
        f"Saldo -- nicht laufend mark-to-market waehrend offene Positionen laufen) &middot; "
        f"max. {MAX_CONCURRENT} gleichzeitige Positionen ueber alle 5 Maerkte &middot; max. 1 Position/Markt &middot; "
        f"Strategie EMA{TREND_LEN}/RSI{RSI_LEN}&gt;{RSI_OVERSOLD:.0f}/ATR{ATR_LEN}&times;{ATR_STOP_MULT:.1f}/RR{RR_RATIO:.1f}, "
        f"long-only &middot; Zeitraum {START} bis {END} &middot; Spread-Annahme wie in den anderen Tabs "
        f"(10bp Metalle / 3bp CHFJPY / 1.5bp USDJPY, Round-Trip) &middot; <b>nicht modelliert:</b> Swap-/"
        f"Overnight-Gebuehren, Slippage, Broker-Lot-Rundung (Bot rundet ab &rarr; reales Risiko tendenziell "
        f"&le;1%, nie mehr)."
    )

    variant_label = st.radio(
        "Variante", ["Baseline (Bot wie er ist)", f"Mit ADX>={CHOSEN_ADX_MIN:.0f}-Filter"],
        horizontal=True, label_visibility="collapsed",
    )
    variant_key = "baseline" if variant_label.startswith("Baseline") else "filtered"
    res = account_result[variant_key]

    full_s, is_s, oos_s = res["full"]["stats"], res["is"]["stats"], res["oos"]["stats"]
    tile_row([
        ("ENDKAPITAL (FULL)", f"${full_s['final_equity']:,.0f}"),
        ("GESAMT-RETURN (FULL)", fmt_pct(full_s["total_return"])),
        ("ENDKAPITAL (OOS)", f"${oos_s['final_equity']:,.0f}"),
        ("PF (OOS)", fmt_num(oos_s["profit_factor"])),
        ("MAXDD (FULL)", fmt_pct(full_s["max_drawdown_pct"])),
        ("TRADES GENOMMEN / UEBERSPRUNGEN", f"{full_s['n_trades']} / {full_s['n_skipped']}"),
    ])

    section_title(f"Equity-Kurve ({variant_label}, {STARTING_EQUITY:,.0f} USD Start, log-Skala)")
    curve = res["full"]["sim"]["equity_curve"].copy()
    if not curve.empty:
        chart = alt.Chart(curve.rename(columns={"time": "date", "equity": "value"})).mark_line(color=C_ORANGE, size=2).encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
            y=alt.Y("value:Q", title=None, scale=alt.Scale(type="log"), axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
            tooltip=["date:T", alt.Tooltip("value:Q", format="$,.0f")],
        ).properties(height=380, background=C_BG).configure_view(strokeWidth=0)
        st.altair_chart(chart)
        st.caption(f"IS-Ende (2022-12-31): ~${is_s['final_equity']:,.0f} ({fmt_pct(is_s['total_return'])} seit Start). Danach OOS bis {END}.")
    else:
        st.caption("Keine Trades in diesem Zeitraum.")

    section_title("Baseline vs. ADX-Filter, Full / IS / OOS")
    rows = []
    for label, adx_key in [("Baseline", "baseline"), (f"ADX>={CHOSEN_ADX_MIN:.0f}", "filtered")]:
        for period_label, period_key in [("Full", "full"), ("IS 2016-22", "is"), ("OOS 2023-26", "oos")]:
            s = account_result[adx_key][period_key]["stats"]
            rows.append({
                "Variante": label, "Periode": period_label, "n": s["n_trades"], "uebersprungen": s["n_skipped"],
                "Trefferquote": s["win_rate"], "Profit-Faktor": s["profit_factor"],
                "Endkapital": s["final_equity"], "Gesamt-Return": s["total_return"],
                "MaxDD": s["max_drawdown_pct"], "MaxDD ($)": s["max_drawdown_usd"],
            })
    st.dataframe(
        pd.DataFrame(rows), hide_index=True,
        column_config={
            "Trefferquote": st.column_config.NumberColumn(format=".1%"),
            "Profit-Faktor": st.column_config.NumberColumn(format="%.3f"),
            "Endkapital": st.column_config.NumberColumn(format="$%.0f"),
            "Gesamt-Return": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD": st.column_config.NumberColumn(format="+.1%"),
            "MaxDD ($)": st.column_config.NumberColumn(format="$%.0f"),
        },
    )
    st.caption(
        "Ueber die volle 10-Jahres-Historie waere das Konto in der IS-Periode (2016-2022) trotz 1%-Risiko-"
        "Sizing GESCHRUMPFT (negativer Gesamt-Return) -- das compoundende Fixed-Fractional-Sizing macht aus "
        "einem schwachen Edge kein starkes Ergebnis. Der komplette Nettogewinn ueber 10 Jahre stammt aus der "
        "OOS-Periode 2023-2026. Wer heute live startet, startet in eine unbekannte Zukunft, nicht in die "
        "bereits bekannte guenstige OOS-Periode."
    )

# ------------------------------------------------------------------ Tab: TP/SL & breakeven
def _render_tab_tab_tpsl():
    caveat_box(
        f"Disziplin wie ueberall in dieser Serie: ADX&gt;={CHOSEN_ADX_MIN:.0f}-Filter bleibt FEST (nicht neu "
        f"gesweept -- 3 gleichzeitige freie Parameter auf ~180 gepoolten IS-Trades wuerden die Stichprobe je "
        f"Zelle zu duenn machen). Stop({', '.join(f'{x:.1f}' for x in STOP_ATR_CANDIDATES)}) x "
        f"TP({', '.join(f'{x:.1f}' for x in TP_R_CANDIDATES)}) wird <b>nur auf IS (2016-2022)</b> gewaehlt, "
        f"dann <b>unveraendert</b> auf OOS (2023-2026) angewendet. Danach ein Breakeven-Trigger-Sweep OBEN "
        f"DRAUF, gleiche Disziplin."
    )

    r = tpsl_result
    section_title("1. TP/SL-Sweep -- nur In-Sample (2016-2022), gepoolt")
    sw = r["sweep"].copy()
    pivot_pf = sw.pivot(index="stop_atr", columns="tp_r", values="sharpe")
    st.caption("Sharpe je (Stop-ATR-Multiple x Take-Profit-R), In-Sample -- hoehere Werte = besser (alle hier trotzdem <1.0, IS bleibt schwach)")
    st.dataframe(
        pivot_pf.style.format("{:.2f}").background_gradient(cmap="RdYlGn", vmin=-0.9, vmax=0.3, axis=None),
    )
    st.caption(
        f"Gewaehlt (beste IS-Sharpe, n&ge;{MIN_IS_TRADES_TPSL}): Stop-ATR={r['chosen_stop']:.1f}, TP-R={r['chosen_tp']:.1f} "
        f"(Bot-Default: 2.0/2.0)."
    )

    section_title("2. Validierung -- unveraendert auf Out-of-Sample (2023-2026)", color=C_GREEN)
    tile_row([
        ("SHARPE OOS (Bot-Default 2.0/2.0)", fmt_num(r["base_oos"]["sharpe"])),
        (f"SHARPE OOS (optimiert {r['chosen_stop']:.1f}/{r['chosen_tp']:.1f})", fmt_num(r["chosen_oos"]["sharpe"])),
        ("PF OOS (Default)", fmt_num(r["base_oos"]["profit_factor"])),
        ("PF OOS (optimiert)", fmt_num(r["chosen_oos"]["profit_factor"])),
        ("MAXDD OOS (Default)", fmt_pct(r["base_oos"]["max_drawdown"])),
        ("MAXDD OOS (optimiert)", fmt_pct(r["chosen_oos"]["max_drawdown"])),
    ])

    if r["chosen_oos"]["sharpe"] <= r["base_oos"]["sharpe"]:
        caveat_box(
            f"<b>Ehrlicher Befund -- gegen die Erwartung:</b> Die auf IS \"optimierten\" Parameter "
            f"(Stop={r['chosen_stop']:.1f}, TP={r['chosen_tp']:.1f}) verbessern die risikoadjustierte OOS-"
            f"Performance NICHT gegenueber dem Bot-Default (Sharpe {fmt_num(r['base_oos']['sharpe'])} vs. "
            f"{fmt_num(r['chosen_oos']['sharpe'])}) -- trotz hoeherem PF/CAGR kommt das mit spuerbar "
            f"schlechterem MaxDD und deutlich niedrigerer Trefferquote (weniger, aber groessere Trades = "
            f"fragiler). Der Bot-Default (2.0/2.0) haelt sich in dieser Validierung besser als die "
            f"IS-optimierte Alternative -- keine Empfehlung, das Live-Setup zu aendern.",
            kind="alert",
        )
    else:
        caveat_box(
            f"Die optimierten Parameter verbessern die OOS-Sharpe gegenueber dem Bot-Default "
            f"({fmt_num(r['base_oos']['sharpe'])} &rarr; {fmt_num(r['chosen_oos']['sharpe'])}).",
            kind="good",
        )

    section_title("3. Breakeven-Trigger-Sweep (oben drauf, nur In-Sample)")
    be_df = r["be_sweep"].copy()
    be_df["be_trigger_r"] = be_df["be_trigger_r"].apply(lambda x: "kein BE" if pd.isna(x) else f"{x:.1f}R")
    st.dataframe(
        be_df[["be_trigger_r", "n_trades", "win_rate", "profit_factor", "sharpe", "max_drawdown"]],
        hide_index=True,
        column_config={
            "be_trigger_r": "BE-Trigger", "n_trades": "n",
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            "max_drawdown": st.column_config.NumberColumn("MaxDD", format="+.1%"),
        },
    )
    be_label = "kein BE" if r["chosen_be"] is None else f"{r['chosen_be']:.1f}R"
    section_title(f"4. Finale Validierung -- Stop={r['chosen_stop']:.1f}/TP={r['chosen_tp']:.1f}/BE={be_label}, Out-of-Sample", color=C_GREEN)
    tile_row([
        ("SHARPE OOS (+BE)", fmt_num(r["final_oos"]["sharpe"])),
        ("PF OOS (+BE)", fmt_num(r["final_oos"]["profit_factor"])),
        ("CAGR OOS (+BE)", fmt_pct(r["final_oos"]["cagr"])),
        ("MAXDD OOS (+BE)", fmt_pct(r["final_oos"]["max_drawdown"])),
        ("PF OOS (ohne BE)", fmt_num(r["chosen_oos"]["profit_factor"])),
        ("PF OOS (Bot-Default)", fmt_num(r["base_oos"]["profit_factor"])),
    ])

    if r["outlier"] is not None:
        wb, wob = r["outlier"]["with_best"], r["outlier"]["without_best"]
        c1, c2 = st.columns(2)
        with c1:
            st.metric("PF (finale Config) mit bestem Trade", fmt_num(wb["profit_factor"]))
        with c2:
            st.metric("PF (finale Config) ohne bestem Trade", fmt_num(wob["profit_factor"]))

    section_title("Zusammenfassung (Full-Period, nur Referenz -- keine Validierung)")
    summary_rows = [
        {"Konfiguration": "Bot-Default (2.0/2.0, kein BE)", **r["base_full"]},
        {"Konfiguration": f"Optimiert ({r['chosen_stop']:.1f}/{r['chosen_tp']:.1f}, kein BE)", **r["chosen_full"]},
        {"Konfiguration": f"Optimiert + BE={be_label}", **r["final_full"]},
    ]
    st.dataframe(
        pd.DataFrame(summary_rows)[["Konfiguration", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]],
        hide_index=True,
        column_config={
            "n_trades": "n",
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            "cagr": st.column_config.NumberColumn("CAGR", format="+.1%"),
            "max_drawdown": st.column_config.NumberColumn("MaxDD", format="+.1%"),
        },
    )
    st.caption(
        "Gesamtfazit dieses Sweeps: der ADX-Filter (vorheriger Tab) bleibt der einzige Baustein in dieser "
        "Serie, der die OOS-Sharpe robust verbessert. TP/SL-Optimierung und Breakeven verschieben nur das "
        "Profil (weniger, groessere Trades; glatteres oder raueres Drawdown), ohne einen zusaetzlichen "
        "echten Edge zu liefern -- der Bot-Default ist keine schlechte Wahl."
    )

# ------------------------------------------------------------------ Tab: Risk management
def _render_tab_tab_risk():
    caveat_box(
        "<b>Zwei Fremdkapital-Profile + Eigenkapital, kalibriert per taeglichem Mark-to-Market</b> "
        "(Standard-Portfolio: Gold/Silber-aligned/CHFJPY/USDJPY/USDCAD, Bot-Default-Parameter, kein "
        "ADX-Filter). Offene Positionen werden jeden Tag am Tages-<b>Tief</b> bewertet (konservativ, "
        "nicht am Schlusskurs) -- \"Daily-DD\" = Verlust vom Vortages-Endstand zum heutigen Tief, "
        "\"Total-DD\" = Peak-to-Trough der gesamten Kurve. <b>Kalibrierung nutzt bewusst die volle "
        "10-Jahres-Historie</b>, nicht nur die guenstige 2023-2026-Phase -- die 2023-2026-Zahlen stehen "
        "unten nur als Vergleichspunkt, nicht als Empfehlung.",
        kind="alert",
    )

    period_choice = st.radio(
        "Zeitraum", ["Volle Historie (2016-2026) -- empfohlene Basis", "Nur 2023-2026 -- nur zum Vergleich"],
        horizontal=True, label_visibility="collapsed",
    )
    period_key = "Volle Historie (2016-2026)" if period_choice.startswith("Volle") else "Nur 2023-2026"

    section_title("Optimales Risiko/Trade je Profil (groesster konformer Wert, max. 3 gleichzeitige Positionen)")
    rows = []
    for profile_name in RISK_PROFILES:
        best = risk_result["chosen"][period_key][profile_name]
        if best is None:
            rows.append({"Profil": profile_name, "Risiko/Trade": None, "Endkapital": None, "Return": None, "Max Daily-DD": None, "Max Total-DD": None})
        else:
            rows.append({
                "Profil": profile_name, "Risiko/Trade": best["risk_pct"], "Endkapital": best["final_equity"],
                "Return": best["total_return"], "Max Daily-DD": best["max_daily_dd"], "Max Total-DD": best["max_total_dd"],
            })
    st.dataframe(
        pd.DataFrame(rows), hide_index=True,
        column_config={
            "Risiko/Trade": st.column_config.NumberColumn(format=".2%"),
            "Endkapital": st.column_config.NumberColumn(format="$%.0f"),
            "Return": st.column_config.NumberColumn(format="+.1%"),
            "Max Daily-DD": st.column_config.NumberColumn(format="+.2%"),
            "Max Total-DD": st.column_config.NumberColumn(format="+.2%"),
        },
    )

    with st.expander(":material/table_chart: Voller Sweep (alle getesteten Risiko/Trade-Werte)", expanded=False):
        for profile_name in RISK_PROFILES:
            st.caption(profile_name)
            sweep = risk_result["sweeps"][period_key][profile_name].copy()
            st.dataframe(
                sweep[["risk_pct", "max_daily_dd", "max_total_dd", "final_equity", "total_return", "n_trades", "compliant"]],
                hide_index=True,
                column_config={
                    "risk_pct": st.column_config.NumberColumn("Risiko/Trade", format=".2%"),
                    "max_daily_dd": st.column_config.NumberColumn("Max Daily-DD", format="+.2%"),
                    "max_total_dd": st.column_config.NumberColumn("Max Total-DD", format="+.2%"),
                    "final_equity": st.column_config.NumberColumn("Endkapital", format="$%.0f"),
                    "total_return": st.column_config.NumberColumn("Return", format="+.1%"),
                    "n_trades": "n",
                    "compliant": "Konform",
                },
            )

    section_title(f"OU-Modell-Stil Open-Risk-Engine: {OU_RISK_PCT:.1%} Risiko/Trade, {OU_MAX_TOTAL_RISK_PCT:.0%} max. offenes Risiko, kein Breakeven", color=C_GREEN)
    caveat_box(
        "<b>Breakeven-Trigger getestet und bewusst NICHT eingebaut:</b> ein Sweep (0.25R/0.5R/0.75R/1.0R/1.5R) "
        "auf reiner Trade-Ebene zeigte keinen klaren Vorteil (Sharpe 0.38 ohne BE vs. 0.25-0.40 mit BE, je "
        "nach Trigger). Im Portfolio-Kontext macht ein BE-Trigger es sogar SCHLECHTER: freigewordenes "
        "Risiko-Budget fliesst sofort in neue Trades, was die Gesamt-Exposure erhoeht statt senkt "
        "(Volle Historie: Total-DD -18.3% ohne BE vs. -23.1% mit BE=0.75 bei sonst gleichen Parametern).",
    )
    ou = risk_result["ou_results"][period_key]
    res = ou["result"]
    tile_row([
        ("ENDKAPITAL", f"${res.final_equity:,.0f}"),
        ("RETURN", fmt_pct(res.total_return)),
        ("MAX DAILY-DD", fmt_pct(res.max_daily_dd_pct)),
        ("MAX TOTAL-DD", fmt_pct(res.max_total_dd_pct)),
        ("TRADES GENOMMEN", str(res.n_trades_taken)),
        ("UEBERSPRUNGEN", str(res.n_trades_skipped)),
    ])
    compliance_rows = [{"Profil": name, "Konform": "Ja" if ok else "Nein"} for name, ok in ou["compliance"].items()]
    st.dataframe(pd.DataFrame(compliance_rows), hide_index=True)
    st.caption(
        f"{OU_RISK_PCT:.1%}/{OU_MAX_TOTAL_RISK_PCT:.0%} ist auf der vollen Historie nur fuer EK tragbar "
        "(knapp unter 20% Total-DD) -- fuer FK1/FK2 muesste es kleiner skaliert werden, aehnlich der "
        "Sweep-Tabelle oben."
    )

    section_title("Sharpe-gewichteter Risiko-Split (statt gleichverteilt ueber alle 5 Maerkte)")
    st.caption(
        "Mehr Risiko auf staerkere Maerkte (CHFJPY, Silber), weniger auf schwaechere (Gold, USDJPY) -- "
        "bringt bei EK auf voller Historie einen echten Mehrertrag (+41.6%->+49.4% bei gleichem "
        "Risikobudget, Gewichtung auf ca. 70% skaliert, um konform zu bleiben). Fuer FK2 mit der "
        "korrigierten Regel (1%-Positions-Deckel, 6% Trailing-Total) noch nicht neu durchgerechnet -- "
        "Zahlen aus scripts/research_mt5_trend_pullback_risk_management_v2.py stammen von der frueheren "
        "FK2-Definition (1% daily/8% total) und sind hier nicht mehr direkt uebertragbar."
    )

# ------------------------------------------------------------------ Tab: Monte Carlo
def _render_tab_tab_mc():
    mc_path = Path(__file__).resolve().parents[1] / "mt5_trend_pullback" / "results" / "monte_carlo.json"
    if not mc_path.exists():
        st.info("Monte-Carlo-Daten noch nicht committed.", icon=":material/info:")
        return
    data = json.loads(mc_path.read_text(encoding="utf-8"))
    mc, real, cfg = data["monte_carlo"], data["realized_oos"], data["config"]

    caveat_box(
        "<b>Phase-6-Audit-Nachtrag (2026-08-22):</b> Monte-Carlo-Bootstrap fehlte bislang komplett. "
        "Nachgeholt mit dem im Repo etablierten Muster (<code>ou_paper_backtest/monte_carlo.py</code>, "
        f"zirkulaerer Block-Bootstrap, Blockgroesse 20 Tage, {mc['n_sims']} Simulationen) auf der "
        f"Standard-Empfehlung ({', '.join(cfg['markets'])}, {cfg['risk_pct']*100:.0f}% Risiko/Trade, "
        f"max. {cfg['max_concurrent']} gleichzeitige Positionen), OOS-Fenster {cfg['oos_start']} bis "
        f"{cfg['oos_end']} -- also innerhalb des seit 2023 profitablen Regimes, NICHT rueckwirkend auf "
        "die verlustreiche 2016-2022-Phase (die bleibt der bekannte, unveraenderte Vorbehalt)."
    )

    tile_row([
        ("P(Verlust)", f"{mc['p_loss']*100:.1f}%"),
        ("Sharpe P50", f"{mc['sharpe_p50']:.2f}"),
        ("MaxDD P5 (worst)", f"{mc['max_dd_p5']:.1f}%"),
        ("Realisiertes MaxDD", f"{real['max_dd_pct']:.1f}%"),
    ])
    st.markdown(
        f"Sharpe-Spanne (P5-P95): **{mc['sharpe_p5']:.2f}** bis **{mc['sharpe_p95']:.2f}** &middot; "
        f"MaxDD-Spanne: **{mc['max_dd_p95']:.1f}%** (best) bis **{mc['max_dd_p5']:.1f}%** (worst) &middot; "
        f"Gesamtrendite-Spanne: **{mc['total_return_p5']:+.1f}%** bis **{mc['total_return_p95']:+.1f}%**"
    )
    caveat_box(
        f"<b>Solide innerhalb des bekannten guten Regimes:</b> P(Verlust)={mc['p_loss']*100:.1f}% ueber "
        f"2000 zirkulaere Bootstrap-Pfade, Sharpe bleibt auch im 5. Perzentil mit {mc['sharpe_p5']:.2f} "
        "positiv. Wichtig: dieser Test bootstrapt NUR aus der bereits profitablen 2024-2026-Historie -- "
        "er kann die bekannte Schwaeche vor 2023 nicht heilen oder widerlegen, sondern zeigt nur, wie "
        "stabil das Ergebnis INNERHALB des aktuell guten Fensters gegen Sequenz-Risiko ist.",
        kind="good",
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
for _tab, _render in [(tab_standard, _render_tab_tab_standard), (tab_chart, _render_tab_tab_chart), (tab_overview, _render_tab_tab_overview), (tab_adx, _render_tab_tab_adx), (tab_spread, _render_tab_tab_spread), (tab_account, _render_tab_tab_account), (tab_tpsl, _render_tab_tab_tpsl), (tab_risk, _render_tab_tab_risk), (tab_mc, _render_tab_tab_mc)]:
    if _tab.open:
        with _tab:
            _render()
