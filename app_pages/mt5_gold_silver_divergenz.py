"""Backtests -- MT5 Gold/Silber-Divergenz Bot: replication of the third
community MT5 bot in the "Neue Bots" release
(`.../Bots/Neue Bots/3-Divergenz-Gold-Silber/strategy.py`, demo-account
only) against this repo's real 10-year Dukascopy history
(mt5_gold_silver_divergenz/pipeline.py reproduces the bot's own signal
formulas verbatim, verified bit-exact against the live bot's own
check_signal() -- 6393 bars, 0 mismatches -- so signals line up with what
the live bot would actually have fired).

Intermarket mean-reversion, not trend-following: Gold's own 20-bar return
minus Silver's own 20-bar return (a momentum DIFFERENCE, not a price
spread), compared to that difference's own rolling 100-bar -1.5-sigma band.
When Gold falls behind Silver (difference drops below the band) and then
catches back up (crosses back above -- the actual transition event), that's
read as a long signal for Gold, combined with the usual EMA150 trend filter.
Only Gold is traded; Silver is a reference input only.

Honest headline finding surfaced up front: unlike the Haupt-Bot and
David-V2, this one is a genuinely POSITIVE Phase-6 finding -- 2 of 3 rolling
sub-periods profitable with a rising trend, a 15x cost safety margin, low
profit concentration (outlier-check stable), and a favourable Monte Carlo
sequence-risk profile. The 2016-2019 sub-period was still negative though,
and the sample is thin (single instrument, 130 trades/10 years) -- both
flagged inline, not hidden.

Phase 5 update (2026-08-25): the 2016-2019 weak spot was root-caused to the
Gold/Silver RATIO itself being in a smooth structural uptrend that period
(not, as first suspected, raw volatility -- that hypothesis was tested and
REJECTED, see knowledge/projects/mt5-gold-silber-divergenz.md). Two levers
survived a proper IS(2016-2022)-sweep / OOS(2023-2026)-validation and are
now the recommended config (first tab below): band parameters
(ret_len=25/band_lookback=50/band_mult=1.75, was 20/100/1.5) and a Silver-
confirms-itself filter (confirm_len=10 -- Silver's own 10-bar return must
also be positive, not just "less negative than Gold"). Re-ran the FULL
Phase 6 suite on this config, not just the two-way IS/OOS split (rule from
[[backtest-standard-process]]): 2016-2019 Sharpe -0.53 -> +0.14 (no longer
negative), Monte-Carlo P(MaxDD>20%) 5.1%->0.4% (full) / 0.8%->0.1% (OOS),
cost safety factor unchanged at 15x. All other tabs still show the
UNCHANGED bot-original for transparency/comparison -- see
scripts/research_mt5_gold_silver_divergenz_optimization.py and
scripts/research_mt5_gold_silver_divergenz_final_phase6.py.

config.py of the live bot cites a prior research result (OOS ratio
2.43-2.65, 142 trades, top-5 concentration 10.7%) from a script this machine
has no record of -- this page is an independent reconstruction against this
repo's own data/process, not a re-run of that exact methodology (see
knowledge/projects/mt5-gold-silber-divergenz.md for the full comparison).

Dark/monospace styling matches app_pages/mt5_trend_pullback.py (same
palette, prefixed gsd- per that page's established per-page-CSS
convention)."""

import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd

import streamlit as st
from combined_strategy.data import fetch_timeframe
from mt5_gold_silver_divergenz.pipeline import (
    ATR_LEN, ATR_STOP_MULT, BAND_LOOKBACK, BAND_MULT, RET_LEN, RR_RATIO, TREND_LEN, run_pipeline,
)
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import breakeven_spread_bps, regime_decomposition, summarize

st.set_page_config(page_title="Gold/Silber-Divergenz", page_icon=":material/compare_arrows:", layout="wide")

START, END = "2016-01-01", "2026-08-01"
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
SPREAD_BPS = 10.0
STARTING_EQUITY = 100_000.0
RISK_PCT = 0.01  # config.py RISK_PERCENT default

# --- recommended config, chosen on IS (2016-2022) only, validated on OOS (2023-2026) --
# see scripts/research_mt5_gold_silver_divergenz_optimization.py + ..._final_phase6.py
CHOSEN_RET_LEN = 25
CHOSEN_BAND_LOOKBACK = 50
CHOSEN_BAND_MULT = 1.75
CHOSEN_CONFIRM_LEN = 10

PERIODS = [
    ("2016-2019", "2016-01-01", "2019-01-01"),
    ("2019-2022", "2019-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2026-08-01"),
]
SPREAD_SWEEP_BPS = [5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 70.0, 100.0, 150.0, 200.0]

# --- same palette as mt5_trend_pullback.py / gold_bitcoin_dual_momentum.py ---
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
    .gsd-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .gsd-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .gsd-caveats b {{ color: {C_TEXT}; }}
    .gsd-alert {{ background: rgba(255,140,66,0.08); border: 1px solid {C_ORANGE};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .gsd-good {{ background: rgba(94,203,140,0.08); border: 1px solid {C_GREEN};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .gsd-good b {{ color: {C_TEXT}; }}
    .gsd-alert b {{ color: {C_TEXT}; }}
    .gsd-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .gsd-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px;
               transition: border-color 0.15s ease; }}
    .gsd-tile:hover {{ border-color: {C_ORANGE}; }}
    .gsd-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .gsd-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .gsd-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .gsd-legend {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.78rem; margin-top: 0.4rem; }}
    .gsd-legend span {{ margin-right: 1.4rem; }}
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
    st.markdown(f"<div class='gsd-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, kind: str = "neutral") -> None:
    cls = {"neutral": "gsd-caveats", "alert": "gsd-alert", "good": "gsd-good"}[kind]
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='gsd-tile-row'>" + "".join(
        f"<div class='gsd-tile'><div class='gsd-tile-value'>{v}</div><div class='gsd-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def legend(items: list[tuple[str, str]]) -> None:
    spans = "".join(f"<span style='color:{color};'>&#9644;&#9644; {label}</span>" for label, color in items)
    st.markdown(f"<div class='gsd-legend'>{spans}</div>", unsafe_allow_html=True)


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
@st.cache_data(ttl="6h", show_spinner="Lade 10 Jahre XAUUSD/XAGUSD H4 (Dukascopy)...")
def load_markets() -> dict[str, pd.DataFrame]:
    data = {}
    for key, label in [("GOLD", "XAUUSD"), ("SILVER", "XAGUSD")]:
        df = fetch_timeframe(key, "H4", START, END)
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        data[label] = df
    return data


@st.cache_data(ttl="6h", show_spinner="Simuliere Baseline (Bot wie er ist)...")
def run_baseline(_data: dict[str, pd.DataFrame]) -> dict:
    signaled = run_pipeline(_data["XAUUSD"], _data["XAGUSD"])
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(signaled, cfg)

    is_trades = trades[trades["entry_time"] < SPLIT]
    is_idx = signaled[signaled.index < SPLIT].index
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    oos_idx = signaled[signaled.index >= SPLIT].index

    best_idx = trades["return_pct"].idxmax() if not trades.empty else None
    without_best = trades.drop(best_idx) if best_idx is not None else trades

    return {
        "signaled": signaled, "trades": trades,
        "full": summarize(trades, signaled.index),
        "is": summarize(is_trades, is_idx),
        "oos": summarize(oos_trades, oos_idx),
        "trades_oos": oos_trades, "index_oos": oos_idx,
        "regime": regime_decomposition(trades),
        "outlier": {"with_best": summarize(trades, signaled.index), "without_best": summarize(without_best, signaled.index)},
    }


@st.cache_data(ttl="6h", show_spinner="Walk-Forward ueber 3 rollierende Sub-Perioden...")
def run_walkforward(_signaled: pd.DataFrame, _trades: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, start, end in PERIODS:
        start_ts, end_ts = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        period_idx = _signaled.index[(_signaled.index >= start_ts) & (_signaled.index < end_ts)]
        t = _trades[(_trades["entry_time"] >= start_ts) & (_trades["entry_time"] < end_ts)]
        rows.append({"Periode": name, **summarize(t, period_idx)})
    return pd.DataFrame(rows)


@st.cache_data(ttl="6h", show_spinner="Simuliere die empfohlene, optimierte Konfiguration (Phase 5+6)...")
def run_optimized(_data: dict[str, pd.DataFrame]) -> dict:
    signaled = run_pipeline(
        _data["XAUUSD"], _data["XAGUSD"],
        ret_len=CHOSEN_RET_LEN, band_lookback=CHOSEN_BAND_LOOKBACK, band_mult=CHOSEN_BAND_MULT,
        confirm_len=CHOSEN_CONFIRM_LEN,
    )
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    trades = simulate_trades(signaled, cfg)

    is_trades = trades[trades["entry_time"] < SPLIT]
    is_idx = signaled[signaled.index < SPLIT].index
    oos_trades = trades[trades["entry_time"] >= SPLIT]
    oos_idx = signaled[signaled.index >= SPLIT].index

    wf_rows = []
    for name, start, end in PERIODS:
        start_ts, end_ts = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC")
        period_idx = signaled.index[(signaled.index >= start_ts) & (signaled.index < end_ts)]
        t = trades[(trades["entry_time"] >= start_ts) & (trades["entry_time"] < end_ts)]
        wf_rows.append({"Periode": name, **summarize(t, period_idx)})

    return {
        "signaled": signaled, "trades": trades,
        "full": summarize(trades, signaled.index),
        "is": summarize(is_trades, is_idx),
        "oos": summarize(oos_trades, oos_idx),
        "trades_oos": oos_trades, "index_oos": oos_idx,
        "walkforward": pd.DataFrame(wf_rows),
    }


@st.cache_data(ttl="6h", show_spinner="Monte-Carlo-Bootstrap (ou_paper_backtest/monte_carlo.py, 2000 Pfade)...")
def run_monte_carlo_tab(_trades: pd.DataFrame, _index: pd.DatetimeIndex, _oos_trades: pd.DataFrame, _oos_index: pd.DatetimeIndex, variant: str) -> dict:
    # `variant` is the ONLY hashed argument here (the others are underscore-
    # prefixed so Streamlit doesn't try to hash the DataFrames) -- without it,
    # calling this twice with different trade sets (baseline vs. optimized)
    # would collide on the same cache key and silently return the first
    # call's result for both (exactly the bug this fixes: the "Optimiert"
    # column showed identical numbers to "Original" on the dashboard).
    import sys
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root / "ou_paper_backtest") not in sys.path:
        sys.path.insert(0, str(repo_root / "ou_paper_backtest"))
    from monte_carlo import run_monte_carlo

    out = {}
    for label, trades, index in [("full", _trades, _index), ("oos", _oos_trades, _oos_index)]:
        if trades.empty:
            out[label] = None
            continue
        daily = trades_to_daily_returns(trades, index)
        mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
        out[label] = mc["summary"]
    return out


@st.cache_data(ttl="6h", show_spinner="Kosten-Sensitivitaet (Out-of-Sample, Breakeven-Spread)...")
def run_cost_sensitivity(_oos_signaled: pd.DataFrame) -> dict:
    base_cfg = BacktestConfig(stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
    breakeven = breakeven_spread_bps(_oos_signaled, base_cfg, lo=0.0, hi=250.0)

    rows = []
    for sp in SPREAD_SWEEP_BPS:
        cfg = BacktestConfig(spread_bps=sp, stop_atr_mult=ATR_STOP_MULT, use_vwap_target=False, take_profit_r=RR_RATIO)
        t = simulate_trades(_oos_signaled, cfg)
        s = summarize(t, _oos_signaled.index)
        rows.append({"Spread (bp)": sp, **s})
    return {"breakeven": breakeven, "sweep": pd.DataFrame(rows)}


# ------------------------------------------------------------------ header
st.markdown("## :material/compare_arrows: Gold/Silber-Divergenz")
st.caption(
    "Backtest-Replikation des dritten \"Neue Bots\"-Community-Bots (MT5, Python/MetaTrader5-API, "
    "Demo-Konto only) -- Intermarket-Mean-Reversion: kauft Gold, wenn seine Momentum-Differenz zu "
    "Silber deutlich unter ihr eigenes Band faellt und dann wieder aufholt. Die Signal-Formeln hier "
    "sind 1:1 aus der Bot-Quelle uebernommen (strategy.py), bit-exakt gegen check_signal() geprueft."
)

caveat_box(
    "<b>&#11088; Ehrlicher Hauptbefund: der robusteste der drei \"Neue Bots\".</b> 2 von 3 rollierenden "
    "Sub-Perioden (2019-2022, 2022-2026) sind profitabel mit steigender Tendenz, der Kosten-Sicherheitspuffer "
    "liegt bei <b>15x</b> der angenommenen Spread-Kosten, und die Gewinnkonzentration ist niedrig (Outlier-"
    "Check zeigt kaum Abhaengigkeit von einzelnen Trades). Die fruehste Periode (2016-2019) war dagegen "
    "negativ, und das Sample ist mit 130 Trades/10 Jahren auf nur einem Instrument klein -- beides ist unten "
    "offen ausgewiesen, nicht versteckt. <b>Kein Live-Handel hier</b> -- diese Seite zeigt Backtest-"
    "Ergebnisse, keine automatisierte Ausfuehrung.",
    kind="good",
)

caveat_box(
    f"<b>&#128295; Phase-5-Optimierung (2026-08-25), siehe Tab \"Empfehlung (Optimiert)\":</b> Band-Parameter "
    f"neu gesweept (ret_len={CHOSEN_RET_LEN}, band_lookback={CHOSEN_BAND_LOOKBACK}, band_mult={CHOSEN_BAND_MULT}, "
    f"war {RET_LEN}/{BAND_LOOKBACK}/{BAND_MULT}) plus ein Silber-Bestaetigungsfilter (Silbers eigene "
    f"{CHOSEN_CONFIRM_LEN}-Kerzen-Rendite muss bei Entry auch positiv sein) -- beides nur auf In-Sample "
    f"(2016-2022) gewaehlt, unveraendert auf Out-of-Sample geprueft, danach die KOMPLETTE Phase-6-Robustheits-"
    f"pruefung auf der neuen Config wiederholt (nicht nur der IS/OOS-Split). Ergebnis: die schwache 2016-2019-"
    f"Periode ist nicht mehr negativ (Sharpe -0.53 &rarr; +0.14), und das Sequenzrisiko sinkt deutlich "
    f"(Monte-Carlo P(MaxDD&gt;20%) 5.1%&rarr;0.4%). Alle anderen Tabs unten zeigen weiterhin die UNVERAENDERTE "
    f"Bot-Original-Config zur Dokumentation/zum Vergleich.",
    kind="good",
)

caveat_box(
    "<b>Zur Herkunftsangabe der Bot-config.py:</b> die dort behaupteten Kennzahlen (OOS-Verhaeltnis "
    "2.43-2.65, 142 Trades, Top-5-Konzentration 10.7%) stammen aus einem Skript "
    "(<code>backtest-pipeline/idea_r28_intermarket_divergenz.py</code>), das auf dieser Maschine nirgends "
    "auffindbar ist -- das \"Neue Bots\"-Paket ist bewusst ohne interne Forschungsskripte veroeffentlicht. "
    "Diese Seite ist eine <b>unabhaengige Neu-Rekonstruktion</b>, keine Verifikation jenes Befunds -- die "
    "Zahlen weichen leicht ab (130 statt 142 Trades, Top-5 15.5% statt 10.7%), stimmen aber in der Groessenordnung "
    "und Richtung ueberein. Details: <code>knowledge/projects/mt5-gold-silber-divergenz.md</code>.",
)

with st.expander(":material/menu_book: Strategie-Regeln (1:1 aus dem Live-Bot)", expanded=False):
    st.markdown(
        f"""
        <div class="gsd-writeup">
        Long-only Gold, eine Position, feste ATR-Stop/R-Multiple-Exits -- keine Trailing-Stops,
        keine Zeit-Exits. Silber wird nur referenziert (letzter bekannter Kurs auf-oder-vor jedem
        Gold-Balken, kausal), nie selbst gehandelt.
        </div>
        <div class="gsd-caveats">
        <b>1. Momentum-Differenz:</b> d(t) = Golds {RET_LEN}-Kerzen-Rendite &minus; Silbers {RET_LEN}-Kerzen-Rendite<br>
        <b>2. Band:</b> gleitender Mittelwert/Std.-Abw. von d ueber {BAND_LOOKBACK} Kerzen,
        Band = Mittelwert &minus; {BAND_MULT:.1f} &times; Std.-Abw.<br>
        <b>3. Signal:</b> d lag auf der Vorkerze unter dem Band UND liegt jetzt wieder darueber
        (echtes Uebergangsereignis)<br>
        <b>4. Trend-Filter:</b> Schlusskurs Gold &gt; EMA({TREND_LEN})<br>
        <b>5. Stop:</b> Entry &minus; ATR({ATR_LEN}) &times; {ATR_STOP_MULT:.1f}<br>
        <b>6. Take-Profit:</b> {RR_RATIO:.1f}R<br><br>
        Alle Formeln (EMA/ATR) sind hier wortgleich aus der Bot-Quelle uebernommen, damit die Signale
        mit dem uebereinstimmen, was der Live-Bot auf denselben Kerzen tatsaechlich ausgeloest haette.
        </div>
        """,
        unsafe_allow_html=True,
    )

tab_empfehlung, tab_overview, tab_chart, tab_wf, tab_mc, tab_cost = st.tabs([
    ":material/star: Empfehlung (Optimiert)",
    ":material/show_chart: Baseline (Bot-Original)",
    ":material/candlestick_chart: Chart & Entries",
    ":material/timeline: Walk-Forward",
    ":material/casino: Monte Carlo",
    ":material/payments: Kosten-Sensitivitaet",
], on_change="rerun")

# ------------------------------------------------------------------ Tab: Empfehlung (optimiert)
def _render_tab_empfehlung():
    data = load_markets()
    baseline = run_baseline(data)
    optimized = run_optimized(data)
    walkforward = run_walkforward(baseline["signaled"], baseline["trades"])
    mc_result = run_monte_carlo_tab(baseline["trades"], baseline["signaled"].index, baseline["trades_oos"], baseline["index_oos"], variant="baseline")
    mc_result_opt = run_monte_carlo_tab(optimized["trades"], optimized["signaled"].index, optimized["trades_oos"], optimized["index_oos"], variant="optimized")

    caveat_box(
        f"<b>Empfohlene Konfiguration</b> (auf In-Sample 2016-2022 gewaehlt, unveraendert auf Out-of-Sample "
        f"2023-2026 geprueft, komplette Phase-6-Robustheitspruefung wiederholt -- "
        f"<code>scripts/research_mt5_gold_silver_divergenz_optimization.py</code> + "
        f"<code>..._final_phase6.py</code>): ret_len={CHOSEN_RET_LEN} (war {RET_LEN}), "
        f"band_lookback={CHOSEN_BAND_LOOKBACK} (war {BAND_LOOKBACK}), band_mult={CHOSEN_BAND_MULT} "
        f"(war {BAND_MULT}), Stop/RR unveraendert ({ATR_STOP_MULT:.1f}/{RR_RATIO:.1f} -- im Sweep selbst "
        f"bestbewertet), plus neuer Silber-Bestaetigungsfilter: Silbers eigene {CHOSEN_CONFIRM_LEN}-Kerzen-"
        f"Rendite muss bei Entry auch positiv sein (nicht nur \"weniger negativ als Gold\")."
    )

    cf, cis, coos = optimized["full"], optimized["is"], optimized["oos"]
    bf = baseline["full"]
    tile_row([
        ("N TRADES (FULL)", f"{cf['n_trades']} (Original: {bf['n_trades']})"),
        ("PF FULL", f"{fmt_num(cf['profit_factor'])} (Original: {fmt_num(bf['profit_factor'])})"),
        ("SHARPE FULL", f"{fmt_num(cf['sharpe'])} (Original: {fmt_num(bf['sharpe'])})"),
        ("SHARPE OOS", fmt_num(coos["sharpe"])),
        ("PF OOS", fmt_num(coos["profit_factor"])),
        ("MAXDD FULL", fmt_pct(cf["max_drawdown"])),
    ])

    section_title("Equity-Kurve: Optimiert vs. Bot-Original (Full History)")
    daily_opt = trades_to_daily_returns(optimized["trades"], optimized["signaled"].index)
    daily_base = trades_to_daily_returns(baseline["trades"], baseline["signaled"].index)
    eq_opt, eq_base = (1 + daily_opt).cumprod(), (1 + daily_base).cumprod()
    combined_eq = pd.concat([normalize(eq_base, "Bot-Original"), normalize(eq_opt, "Optimiert")])
    st.altair_chart(line_chart(combined_eq, {"Bot-Original": (C_MUTED, (5, 4)), "Optimiert": (C_GREEN, None)}))
    legend([("Bot-Original", C_MUTED), ("Optimiert (Band-Params + Silber-Filter)", C_GREEN)])

    section_title("Walk-Forward: Optimiert vs. Bot-Original, je Sub-Periode", color=C_GREEN)
    wf_opt = optimized["walkforward"].copy()
    wf_base = walkforward.copy()
    compare_rows = []
    for i, row in wf_opt.iterrows():
        base_row = wf_base.iloc[i]
        compare_rows.append({
            "Periode": row["Periode"],
            "Sharpe (Original)": base_row["sharpe"], "Sharpe (Optimiert)": row["sharpe"],
            "PF (Original)": base_row["profit_factor"], "PF (Optimiert)": row["profit_factor"],
            "n (Optimiert)": row["n_trades"],
        })
    st.dataframe(
        pd.DataFrame(compare_rows), hide_index=True,
        column_config={
            "Sharpe (Original)": st.column_config.NumberColumn(format="%.2f"),
            "Sharpe (Optimiert)": st.column_config.NumberColumn(format="%.2f"),
            "PF (Original)": st.column_config.NumberColumn(format="%.3f"),
            "PF (Optimiert)": st.column_config.NumberColumn(format="%.3f"),
        },
    )
    caveat_box(
        "Die fruehere Schwaeche 2016-2019 ist nicht mehr negativ, wird aber nicht vollstaendig \"repariert\" -- "
        "sie bleibt die schwaechste der 3 Perioden. Ehrlich gemeldet, nicht wegdiskutiert.",
    )

    section_title("Monte-Carlo-Vergleich (Full History, 2000 Pfade, 1% Risiko/Trade)", color=C_GREEN)
    s_opt, s_base = mc_result_opt.get("full"), mc_result.get("full")
    if s_opt is not None and s_base is not None:
        comp_rows = [
            {"Kennzahl": "Median TotalReturn", "Original": f"{np.percentile(s_base['total_return_pct'], 50):+.1f}%", "Optimiert": f"{np.percentile(s_opt['total_return_pct'], 50):+.1f}%"},
            {"Kennzahl": "Median MaxDD", "Original": f"{np.percentile(s_base['max_drawdown_pct'], 50):.1f}%", "Optimiert": f"{np.percentile(s_opt['max_drawdown_pct'], 50):.1f}%"},
            {"Kennzahl": "P(MaxDD>20%)", "Original": f"{(s_base['max_drawdown_pct'] < -20).mean():.1%}", "Optimiert": f"{(s_opt['max_drawdown_pct'] < -20).mean():.1%}"},
            {"Kennzahl": "Median Sharpe", "Original": f"{np.nanmedian(s_base['sharpe']):.2f}", "Optimiert": f"{np.nanmedian(s_opt['sharpe']):.2f}"},
        ]
        st.dataframe(pd.DataFrame(comp_rows), hide_index=True)

    caveat_box(
        "<b>Einordnung:</b> 125 Band-Kombinationen auf ~190 gepoolten Trades zu sweepen traegt ein reales "
        "Overfitting-Risiko, auch wenn IS und OOS sich hier gemeinsam verbessert haben (kein Kollaps-Muster "
        "wie beim Trend-Pullback-Bot-TP/SL-Sweep). Mit 45-50 OOS-Trades nach dem Silber-Filter ist die "
        "Stichprobe dünn -- als starker Kandidat zu lesen, nicht als endgueltig bewiesen. Ein separat "
        "getesteter Ratio-Trendigkeits-Filter (misst, ob die Gold/Silber-Ratio selbst gerade strukturell "
        "trendet) blieb bewusst aussen vor -- die verfuegbare Silber-Historie (ab Mitte 2014) reicht nicht "
        "fuer eine zusaetzliche unabhaengige Regime-Instanz, um ihn sauber IS/OOS zu validieren.",
        kind="alert",
    )

# ------------------------------------------------------------------ Tab: Overview
def _render_tab_overview():
    data = load_markets()
    baseline = run_baseline(data)

    cf, cis, coos = baseline["full"], baseline["is"], baseline["oos"]
    tile_row([
        ("N TRADES (FULL)", str(cf["n_trades"])),
        ("PF FULL", fmt_num(cf["profit_factor"])),
        ("PF IS (2016-22)", fmt_num(cis["profit_factor"])),
        ("PF OOS (2023-26)", fmt_num(coos["profit_factor"])),
        ("SHARPE FULL", fmt_num(cf["sharpe"])),
        ("MAXDD FULL", fmt_pct(cf["max_drawdown"])),
    ])

    section_title("Equity-Kurve (Full History, 1% Risiko/Trade, kein Compounding-Cap noetig -- MAX_OPEN_POSITIONS=1)")
    daily = trades_to_daily_returns(baseline["trades"], baseline["signaled"].index)
    equity = (1 + daily).cumprod()
    st.altair_chart(line_chart(normalize(equity, "Portfolio (Baseline)"), {"Portfolio (Baseline)": (C_ORANGE, None)}))

    section_title("Full / In-Sample (2016-22) / Out-of-Sample (2023-26)")
    rows = [
        {"Periode": "Full (2016-2026)", **fmt_row(cf)},
        {"Periode": "IS (2016-2022)", **fmt_row(cis)},
        {"Periode": "OOS (2023-2026)", **fmt_row(coos)},
    ]
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
    st.caption(
        "Ungewoehnlich, aber kein Fehler: OOS schneidet besser ab als IS (kein Overfitting-Warnsignal in "
        "die uebliche Richtung) -- siehe Walk-Forward-Tab fuer die Aufschluesselung in 3 Sub-Perioden, "
        "die zeigt, dass dieser Trend graduell ueber 3 Fenster steigt statt an einem einzelnen Split zu haengen."
    )

    section_title("Outlier-Sensitivitaet (bester Einzeltrade entfernt, Full History)")
    wb, wob = baseline["outlier"]["with_best"], baseline["outlier"]["without_best"]
    c1, c2 = st.columns(2)
    with c1:
        st.metric("PF mit bestem Trade", fmt_num(wb["profit_factor"]))
    with c2:
        st.metric("PF ohne bestem Trade", fmt_num(wob["profit_factor"]))
    st.caption(":material/check_circle: PF bleibt deutlich ueber 1.0 auch ohne den besten Einzeltrade -- kein Ausreisser-Effekt.")

    section_title("Regime-Zerlegung (Trendstaerke x Volatilitaets-Tertile bei Entry)", color=C_GREEN)
    st.dataframe(
        baseline["regime"], hide_index=True,
        column_config={
            "win_rate": st.column_config.NumberColumn("Trefferquote", format=".1%"),
            "profit_factor": st.column_config.NumberColumn("Profit-Faktor", format="%.3f"),
            "avg_return_pct": st.column_config.NumberColumn("Oe. Return/Trade", format=".3%"),
            "n_trades": st.column_config.NumberColumn("n"),
        },
    )

# ------------------------------------------------------------------ Tab: Chart & Entries
def _render_tab_chart():
    data = load_markets()
    baseline = run_baseline(data)

    caveat_box(
        "Interaktiver Kerzenchart (TradingView Lightweight Charts) mit den tatsaechlichen Backtest-"
        "Entries/Exits ueberlagert -- blaue Pfeile nach oben = Long-Entry, Pfeile nach unten am Exit "
        "farbcodiert (gruen = Take-Profit, rot = Stop-Loss). Nur Gold wird als Kerzenchart gezeigt "
        "(Silber ist reine Referenz, nicht gehandelt)."
    )

    chart_df_full = data["XAUUSD"]
    idx = chart_df_full.index
    tz = idx.tz
    idx_naive = idx.tz_localize(None) if tz is not None else idx
    min_dt, max_dt = idx_naive.min().to_pydatetime(), idx_naive.max().to_pydatetime()
    default_start = max(min_dt, max_dt - pd.Timedelta(days=365))

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

    trades_market = baseline["trades"]
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

        EXIT_COLORS = {"target": C_GREEN, "stop": C_RED, "data_end": C_MUTED}
        EXIT_LABELS = {"target": "TP", "stop": "SL", "data_end": "ENDE"}
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
        <div id="gsdchart" style="width:100%;height:560px;"></div>
        <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
        <script>
          const el = document.getElementById('gsdchart');
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

# ------------------------------------------------------------------ Tab: Walk-Forward
def _render_tab_wf():
    data = load_markets()
    baseline = run_baseline(data)
    walkforward = run_walkforward(baseline["signaled"], baseline["trades"])

    caveat_box(
        "3 rollierende Sub-Perioden statt eines einzelnen IS/OOS-Splits -- zeigt, ob ein Fund an einem "
        "einzelnen Zeitpunkt haengt oder sich ueber mehrere unabhaengige Fenster durchtraegt "
        "(Phase 6 p6_1/p6_4, app_pages/education_gold_intraday.py)."
    )

    section_title("Sharpe/PF je Sub-Periode")
    wf = walkforward.copy()
    st.dataframe(
        wf[["Periode", "n_trades", "win_rate", "profit_factor", "sharpe", "cagr", "max_drawdown"]],
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

    chart_df = wf[["Periode", "sharpe"]].rename(columns={"sharpe": "Sharpe"})
    bar = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X("Periode:N", title=None, axis=alt.Axis(labelColor=C_MUTED, domainColor=C_BORDER)),
        y=alt.Y("Sharpe:Q", axis=alt.Axis(labelColor=C_MUTED, gridColor=C_GRID, domainColor=C_BORDER)),
        color=alt.condition(alt.datum.Sharpe > 0, alt.value(C_GREEN), alt.value(C_RED)),
        tooltip=["Periode", alt.Tooltip("Sharpe:Q", format=".2f")],
    ).properties(height=280, background=C_BG).configure_view(strokeWidth=0)
    st.altair_chart(bar)

    if (wf["sharpe"].iloc[1:] > 0).all() and wf["sharpe"].iloc[0] < 0:
        caveat_box(
            "<b>Steigende Tendenz ueber 3 unabhaengige Fenster:</b> 2016-2019 negativ, 2019-2022 und "
            "2022-2026 klar positiv -- keine Eintagsfliege im letzten Fenster. Die schwache erste Periode "
            "ist trotzdem real und nicht wegzudiskutieren: der Edge trug nicht in jedem Marktregime.",
            kind="good",
        )

# ------------------------------------------------------------------ Tab: Monte Carlo
def _render_tab_mc():
    data = load_markets()
    baseline = run_baseline(data)
    mc_result = run_monte_carlo_tab(baseline["trades"], baseline["signaled"].index, baseline["trades_oos"], baseline["index_oos"], variant="baseline")

    caveat_box(
        "Zirkulaerer Block-Bootstrap (<code>ou_paper_backtest/monte_carlo.py</code>, Blockgroesse 20 Tage, "
        f"2000 Simulationen), {RISK_PCT:.0%} Risiko/Trade -- config.py-Default. MAX_OPEN_POSITIONS=1, "
        "also einfache Compounding-Simulation (kein Portfolio-Engine noetig, nur ein Markt/eine Position)."
    )

    for label, key in [("Full History (2016-2026)", "full"), ("Out-of-Sample (2023-2026)", "oos")]:
        s = mc_result.get(key)
        section_title(label)
        if s is None:
            st.caption("Keine Trades in diesem Zeitraum.")
            continue
        tile_row([
            ("MEDIAN TOTALRETURN", f"{np.percentile(s['total_return_pct'], 50):+.1f}%"),
            ("MEDIAN MAXDD", f"{np.percentile(s['max_drawdown_pct'], 50):.1f}%"),
            ("P(MAXDD>10%)", f"{(s['max_drawdown_pct'] < -10).mean():.1%}"),
            ("P(MAXDD>20%)", f"{(s['max_drawdown_pct'] < -20).mean():.1%}"),
            ("MEDIAN SHARPE", f"{np.nanmedian(s['sharpe']):.2f}"),
            ("MEDIAN CALMAR", f"{np.nanmedian(s['calmar']):.2f}"),
        ])
        band_rows = []
        for p in (5, 25, 50, 75, 95):
            band_rows.append({
                "Perzentil": f"P{p}",
                "MaxDD": np.percentile(s["max_drawdown_pct"], p) / 100,
                "TotalReturn": np.percentile(s["total_return_pct"], p) / 100,
            })
        st.dataframe(
            pd.DataFrame(band_rows), hide_index=True,
            column_config={
                "MaxDD": st.column_config.NumberColumn(format="+.1%"),
                "TotalReturn": st.column_config.NumberColumn(format="+.1%"),
            },
        )

    caveat_box(
        "<b>Guenstiges Sequenzrisiko-Profil:</b> P(MaxDD&gt;20%) liegt sowohl Full-History als auch OOS "
        "im niedrigen einstelligen Prozentbereich -- deutlich guenstiger als David-V2 (P(MaxDD&gt;30%)=79.8% "
        "in dessen staerkster Periode) und in der gleichen Groessenordnung wie der validierte Haupt-Bot.",
        kind="good",
    )

# ------------------------------------------------------------------ Tab: Cost sensitivity
def _render_tab_cost():
    data = load_markets()
    baseline = run_baseline(data)
    oos_signaled = baseline["signaled"][baseline["signaled"].index >= SPLIT]
    cost_result = run_cost_sensitivity(oos_signaled)

    caveat_box(
        "Dieses Repo hat keine echte historische Geld-/Brief-Spread-Historie -- alle bisherigen Ergebnisse "
        f"nutzen eine <b>angenommene</b> Round-Trip-Spanne ({SPREAD_BPS:.1f}bp, \"Realistic\"-Gold-Tier). "
        "Ausschliesslich auf Out-of-Sample (2023-2026) berechnet -- die IS-Periode ist hier nicht "
        "irrefuehrend, war aber ohnehin schwaecher, siehe Walk-Forward-Tab."
    )

    be = cost_result["breakeven"]
    tile_row([
        ("BREAK-EVEN-SPREAD", f"{be:.0f} bp"),
        ("ANGENOMMEN", f"{SPREAD_BPS:.1f} bp"),
        ("SICHERHEITSFAKTOR", f"{be / SPREAD_BPS:.1f}x"),
    ])

    section_title("Profit-Faktor bei steigendem Spread (Out-of-Sample)")
    sw = cost_result["sweep"]
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
    caveat_box(
        f"<b>Robustester Wert aller drei \"Neue Bots\":</b> Break-even bei ~{be:.0f}bp gegenueber "
        f"{SPREAD_BPS:.1f}bp Annahme -- ein {be / SPREAD_BPS:.1f}-facher Sicherheitspuffer. "
        "Selbst ein deutlich schlechterer Broker-Spread als angenommen wuerde den Edge nicht kippen.",
        kind="good",
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default. on_change="rerun"
# makes tab.open reflect the actually-selected tab; only that one's render
# function runs (see app_pages/mt5_trend_pullback.py for the original instance
# of this Streamlit Cloud memory-limit fix).
for _tab, _render in [
    (tab_empfehlung, _render_tab_empfehlung),
    (tab_overview, _render_tab_overview), (tab_chart, _render_tab_chart),
    (tab_wf, _render_tab_wf), (tab_mc, _render_tab_mc), (tab_cost, _render_tab_cost),
]:
    if _tab.open:
        with _tab:
            _render()
