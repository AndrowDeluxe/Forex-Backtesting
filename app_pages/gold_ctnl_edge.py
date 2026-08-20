"""Fertige Strategien -- CTNL Edge Strategie (Gold XAUUSD), aus dem
mentor-eigenen SMC-Regelwerk (CTTNL/Inducement-/CHoCH-BOS-Material, chat
2026-08-14) rekonstruiert und über mehrere Sessions IS/OOS validiert +
Phase-6-robust getestet (2026-08-20, siehe app_pages/education_gold_
intraday.py "Robustheit" und knowledge/projects/gold-ctnl-edge-portfolio.md).

Zwei unabhängige, beide Buy&Hold-im-Sharpe-schlagende Bausteine, jetzt zu
einem 50/50-Portfolio kombiniert:
  1. Continuation ("mit dem Trend"): H4 (Invalidierung) -> H1 (trend-
     gefilterter BOS, ema_adx_combo) -> M5 direct-Entry (Sweep-and-Reject
     des H1-Referenzlevels) -> TP am gegenüberliegenden H4-Liquiditätslevel.
     gold_smc_htf_ltf/continuation.py.
  2. Reversal-Kaskade ("gegen den Trend, an der Wende"): H4 Doppel-Sweep-
     Erschöpfung -> H1 Doppel-BOS -> M15 repeat_sweep-Entry (2. Sweep
     desselben H1-Referenzlevels, für besseres CRV) -> 5R-ATR-Ziel, MIT
     Re-Entry (max_concurrent=3, $-Konto-Simulation).
     gold_smc_htf_ltf/reversal_cascade.py + concurrent_backtest.py.

WICHTIGER VORBEHALT (Phase 6, 2026-08-20): beide Bausteine wurden nur auf
2024-08/2026-08 optimiert/getestet. Ein Walk-Forward-Test auf 2016-2024
(nie gesehen) zeigt NEGATIVE Performance in allen vier Sub-Perioden --
siehe Tab "Weg dorthin". Zwei Runden Regime-Filter-Suche (ADX/ATH-Nähe/
VIX/DXY/Öl) fanden keinen vorhersagenden Filter. Statt eines Vorab-Filters:
ein Realized-Performance-Kill-Switch gegen die Monte-Carlo-Bänder unten.

Dark/monospace-Styling matcht app_pages/mt5_trend_pullback.py /
cls_practical_strategy.py (gleiche Palette, "ctnl-"-Präfix). Chart & Entries
nutzt dieselbe TradingView-Lightweight-Charts-Einbettung wie mt5_trend_
pullback.py."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import streamlit as st
from gold_smc_htf_ltf.concurrent_backtest import (
    equity_curve_to_daily_returns, simulate_account_reentry, simulate_combined_account, simulate_trades_concurrent,
)
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades, trades_to_daily_returns
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

st.set_page_config(page_title="CTNL Edge Strategie", page_icon=":material/military_tech:", layout="wide")

# ou_paper_backtest/ is a flat script module (siblings import each other as bare
# `import config`) -- same sys.path pattern as app_pages/ou_paper_backtest.py, so
# the Monte-Carlo tab reuses the ESTABLISHED bootstrap (block_size=20, n_sims=2000,
# circular) instead of a bespoke one (chat 2026-08-20 lesson: reuse, don't reinvent).
REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "ou_paper_backtest"))
from monte_carlo import run_monte_carlo  # noqa: E402

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0
STARTING_EQUITY = 100_000.0
MAX_DD_LIMIT = 0.06
MAX_CONCURRENT = {"continuation": None, "reversal": 3}

FK_RISK = {"continuation": 0.005, "reversal": 0.0015}
EK_RISK = {"continuation": 0.02, "reversal": 0.015}

# --- gleiche Palette wie mt5_trend_pullback.py / cls_practical_strategy.py ---
C_BG = "#0a0e14"
C_CARD = "#11151c"
C_BORDER = "#232936"
C_GRID = "#1c2128"
C_TEXT = "#f0f6fc"
C_MUTED = "#8b949e"
C_BODY = "#c9d1d9"
C_ORANGE = "#ff8c42"
C_BLUE = "#5ec8f8"
C_BLUE_SOFT = "#9db4e8"
C_GREEN = "#5ecb8c"
C_RED = "#ff5555"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {C_BG}; }}
    .block-container {{ padding-top: 2rem; max-width: 1200px; }}
    .ctnl-writeup {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.92rem;
                  line-height: 1.7; color: {C_BLUE_SOFT}; margin-bottom: 1rem; }}
    .ctnl-caveats {{ font-family: 'JetBrains Mono','Fira Code',Consolas,monospace; font-size: 0.85rem;
                  line-height: 1.7; color: {C_BODY}; margin-bottom: 1.2rem; }}
    .ctnl-caveats b {{ color: {C_TEXT}; }}
    .ctnl-good {{ background: rgba(94,203,140,0.08); border: 1px solid {C_GREEN};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .ctnl-good b {{ color: {C_TEXT}; }}
    .ctnl-alert {{ background: rgba(255,140,66,0.08); border: 1px solid {C_ORANGE};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .ctnl-alert b {{ color: {C_TEXT}; }}
    .ctnl-danger {{ background: rgba(255,85,85,0.08); border: 1px solid {C_RED};
                border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 1.2rem;
                font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.85rem;
                line-height: 1.6; color: {C_BODY}; }}
    .ctnl-danger b {{ color: {C_TEXT}; }}
    .ctnl-tile-row {{ display: flex; gap: 0.9rem; flex-wrap: wrap; margin: 1.2rem 0; }}
    .ctnl-tile {{ background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 8px;
               padding: 1rem 1.3rem; text-align: center; flex: 1; min-width: 148px; }}
    .ctnl-tile-value {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 1.75rem;
                     font-weight: 700; color: {C_TEXT}; }}
    .ctnl-tile-label {{ font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.66rem;
                     letter-spacing: 0.08em; color: {C_MUTED}; margin-top: 0.35rem; text-transform: uppercase; }}
    .ctnl-section-title {{ font-family: 'JetBrains Mono',Consolas,monospace; color: {C_ORANGE};
                      letter-spacing: 0.05em; font-size: 0.8rem; text-transform: uppercase;
                      margin: 0.2rem 0 0.7rem 0; font-weight: 600; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.4rem; }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'JetBrains Mono',Consolas,monospace; font-size: 0.82rem;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 6px 6px 0 0;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def section_title(text: str, color: str = C_ORANGE) -> None:
    st.markdown(f"<div class='ctnl-section-title' style='color:{color};'>{text}</div>", unsafe_allow_html=True)


def caveat_box(html: str, kind: str = "neutral") -> None:
    cls = {"neutral": "ctnl-caveats", "good": "ctnl-good", "alert": "ctnl-alert", "danger": "ctnl-danger"}[kind]
    st.markdown(f"<div class='{cls}'>{html}</div>", unsafe_allow_html=True)


def tile_row(tiles: list[tuple[str, str]]) -> None:
    html = "<div class='ctnl-tile-row'>" + "".join(
        f"<div class='ctnl-tile'><div class='ctnl-tile-value'>{v}</div><div class='ctnl-tile-label'>{l}</div></div>"
        for l, v in tiles
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def fmt_pct(x: float) -> str:
    return f"{x:+.1%}" if pd.notna(x) else "n/a"


def fmt_num(x: float) -> str:
    return f"{x:.2f}" if pd.notna(x) else "n/a"


def fmt_wr(x: float) -> str:
    return f"{x:.1%}" if pd.notna(x) else "n/a"


# ------------------------------------------------------------------ cached data / backtests
@st.cache_data(ttl="6h", show_spinner="Lade Gold H4/H1/M15/M5 (Dukascopy)...")
def load_data():
    h4 = fetch_gold_h4(START, END)
    h1 = fetch_gold_h1(START, END)
    m15 = fetch_gold_m15(START, END)
    m5 = fetch_gold_m5(START, END)
    return h4, h1, m15, m5


@st.cache_data(ttl="6h", show_spinner="Berechne Continuation-Trades...")
def run_continuation_backtest(_h4, _h1, _m5, _m15):
    signaled = run_continuation(
        _h4, _h1, _m5, trend_df=_m15, trend_indicator="ema_adx_combo",
        htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5,
    )
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)
    trades = simulate_trades(signaled, cfg)
    return signaled, trades


@st.cache_data(ttl="6h", show_spinner="Berechne Reversal-Kaskade-Trades...")
def run_reversal_backtest(_h4, _h1, _m15):
    signaled = run_reversal(
        _h4, _h1, _m15, h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0,
        require_ema_reject=True, m15_entry_mode="repeat_sweep",
    )
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)
    trades_single = simulate_trades(signaled, cfg)
    trades_concurrent = simulate_trades_concurrent(signaled, cfg)
    return signaled, trades_single, trades_concurrent


@st.cache_data(ttl="6h", show_spinner="Berechne Portfolio & Risk-Sizing...")
def run_portfolio(_cont_trades_oos, _rev_trades_concurrent_oos, _rev_sig_oos_index):
    daily_cont = trades_to_daily_returns(_cont_trades_oos, _rev_sig_oos_index)
    daily_cont.index = daily_cont.index.tz_localize(None)

    def combo_stats(risk: dict) -> dict:
        sim = simulate_combined_account(
            {"continuation": _cont_trades_oos, "reversal": _rev_trades_concurrent_oos},
            risk, MAX_CONCURRENT, starting_equity=STARTING_EQUITY,
        )
        daily = equity_curve_to_daily_returns(sim["equity_curve"], _rev_sig_oos_index)
        eq = sim["equity_curve"]["equity"].to_numpy()
        peak = np.maximum.accumulate(eq)
        realized_mdd = float(((eq - peak) / peak).min()) if len(eq) else 0.0
        mc = run_monte_carlo(daily, initial_equity=STARTING_EQUITY, block_size=20, n_sims=2000, seed=42)
        s = mc["summary"]
        breach_prob = float((s["max_drawdown_pct"] < -MAX_DD_LIMIT * 100).mean())
        return {
            "final_equity": sim["final_equity"], "total_return": sim["final_equity"] / STARTING_EQUITY - 1,
            "realized_mdd": realized_mdd, "sharpe": annualized_sharpe(daily), "n_taken": sim["n_taken"], "n_skipped": sim["n_skipped"],
            "mc_p5_mdd": np.percentile(s["max_drawdown_pct"], 5) / 100, "mc_p50_mdd": np.percentile(s["max_drawdown_pct"], 50) / 100,
            "mc_p5_ret": np.percentile(s["total_return_pct"], 5) / 100, "mc_p50_ret": np.percentile(s["total_return_pct"], 50) / 100,
            "mc_p95_ret": np.percentile(s["total_return_pct"], 95) / 100, "breach_prob": breach_prob,
            "median_sharpe": float(np.nanmedian(s["sharpe"])),
        }

    fk = combo_stats(FK_RISK)
    ek = combo_stats(EK_RISK)

    # 50/50-Blend (gleichgewichtete "Sleeves", je eigene Risikokonvention)
    rev_sim_default = simulate_account_reentry(_rev_trades_concurrent_oos, starting_equity=STARTING_EQUITY, risk_pct=0.01, max_concurrent=3)
    daily_rev_default = equity_curve_to_daily_returns(rev_sim_default["equity_curve"], _rev_sig_oos_index)
    daily_cont_a, daily_rev_a = daily_cont.align(daily_rev_default, join="outer", fill_value=0.0)
    blend = 0.5 * daily_cont_a + 0.5 * daily_rev_a
    blend_stats = {"sharpe": annualized_sharpe(blend), "cagr": cagr(blend), "max_drawdown": max_drawdown(blend), "total_return": (1 + blend).prod() - 1}

    return fk, ek, blend_stats


def is_oos_split(signaled: pd.DataFrame, trades: pd.DataFrame):
    sig_is, sig_oos = signaled[signaled.index < SPLIT], signaled[signaled.index >= SPLIT]
    t_is = trades[trades["entry_time"] < SPLIT]
    t_oos = trades[trades["entry_time"] >= SPLIT]
    return summarize(t_is, sig_is.index), summarize(t_oos, sig_oos.index), t_oos, sig_oos


def buy_and_hold_stats(price_df: pd.DataFrame) -> dict:
    oos_df = price_df[price_df.index >= SPLIT]
    daily_close = oos_df["close"].resample("1D").last().dropna()
    daily_ret = daily_close.pct_change().fillna(0.0)
    if len(daily_ret):
        daily_ret.iloc[0] -= SPREAD_BPS / 2 / 1e4
    return {"sharpe": annualized_sharpe(daily_ret), "cagr": cagr(daily_ret), "max_drawdown": max_drawdown(daily_ret)}


def render_chart(price_df: pd.DataFrame, trades: pd.DataFrame, key_prefix: str) -> None:
    idx = price_df.index
    idx_naive = idx.tz_localize(None) if idx.tz is not None else idx
    min_dt, max_dt = idx_naive.min().to_pydatetime(), idx_naive.max().to_pydatetime()
    default_start = max(min_dt, max_dt - pd.Timedelta(days=60))

    date_range = st.slider(
        "Zeitraum", min_value=min_dt, max_value=max_dt,
        value=(default_start, max_dt), key=f"{key_prefix}_range",
    )
    win_start, win_end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    if idx.tz is not None:
        win_start, win_end = win_start.tz_localize(idx.tz), win_end.tz_localize(idx.tz)

    windowed = price_df[(price_df.index >= win_start) & (price_df.index <= win_end)]
    MAX_BARS = 4000
    if len(windowed) > MAX_BARS:
        st.warning(f"Zeitraum zu lang fuer eine fluessige Darstellung ({len(windowed)} Kerzen) -- zeige die letzten {MAX_BARS}.")
        windowed = windowed.iloc[-MAX_BARS:]

    if windowed.empty:
        st.info("Keine Kerzen im gewaehlten Zeitraum.")
        return

    trades_window = trades[(trades["entry_time"] >= windowed.index.min()) & (trades["entry_time"] <= windowed.index.max())] if not trades.empty else trades

    candles = [
        {"time": int(ts.timestamp()), "open": float(o), "high": float(h), "low": float(lo), "close": float(cl)}
        for ts, o, h, lo, cl in zip(windowed.index, windowed["open"], windowed["high"], windowed["low"], windowed["close"])
    ]

    EXIT_COLORS = {"target": C_GREEN, "stop": C_RED, "breakeven": C_ORANGE, "data_end": C_MUTED, "max_hold": C_MUTED}
    EXIT_LABELS = {"target": "TP", "stop": "SL", "breakeven": "BE", "data_end": "ENDE", "max_hold": "ZEIT"}
    markers = []
    for _, t in trades_window.iterrows():
        markers.append({
            "time": int(t["entry_time"].timestamp()), "position": "belowBar" if t["direction"] == 1 else "aboveBar",
            "color": C_BLUE, "shape": "arrowUp" if t["direction"] == 1 else "arrowDown", "text": "LONG" if t["direction"] == 1 else "SHORT",
        })
        reason = t["exit_reason"]
        markers.append({
            "time": int(t["exit_time"].timestamp()), "position": "aboveBar" if t["direction"] == 1 else "belowBar",
            "color": EXIT_COLORS.get(reason, C_MUTED), "shape": "circle",
            "text": EXIT_LABELS.get(reason, reason),
        })
    markers.sort(key=lambda m: m["time"])

    n_target = int((trades_window["exit_reason"] == "target").sum()) if not trades_window.empty else 0
    n_stop = int((trades_window["exit_reason"] == "stop").sum()) if not trades_window.empty else 0
    n_other = len(trades_window) - n_target - n_stop
    st.caption(f"{len(windowed)} Kerzen | {len(trades_window)} Trades im Fenster ({n_target} Target, {n_stop} Stop, {n_other} sonstige)")

    chart_html = f"""
    <div id="{key_prefix}chart" style="width:100%;height:560px;"></div>
    <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
    <script>
      const el = document.getElementById('{key_prefix}chart');
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


def render_exit_breakdown(trades: pd.DataFrame, bar_minutes: int) -> None:
    if trades.empty:
        st.info("Keine Trades.")
        return
    rows = []
    for reason, grp in trades.groupby("exit_reason"):
        rows.append({
            "Exit-Grund": reason, "n": len(grp), "Win-Rate": fmt_wr((grp["return_pct"] > 0).mean()),
            "Ø Return": f"{grp['return_pct'].mean():+.3%}", "Summe Return": f"{grp['return_pct'].sum():+.2%}",
            "Ø Haltedauer (h)": f"{(grp['hold_bars'] * bar_minutes / 60).mean():.1f}",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)


# ==================================================================== Seite
st.markdown("## :material/military_tech: CTNL Edge Strategie -- Gold XAUUSD")
caveat_box(
    "Zwei unabhängige Bausteine aus dem mentor-eigenen SMC-Regelwerk (CTTNL: External Range Liquidity, "
    "Inducement, CHoCH/BOS), über mehrere Sessions rekonstruiert, mit strikter IS/OOS-Disziplin "
    "(IS 2024-08 bis 2025-08, OOS 2025-08 bis 2026-08, spread_bps=8) validiert und zu einem Portfolio "
    "kombiniert. <b>Beide schlagen Gold Buy&amp;Hold im Sharpe</b> -- Gold hatte im OOS-Fenster einen "
    "außergewöhnlich starken Lauf (Buy&amp;Hold Sharpe 0.73, CAGR +16.0%, MaxDD -28.6%).",
    kind="good",
)
caveat_box(
    "<b>Phase-6-Vorbehalt (2026-08-20):</b> Walk-Forward auf 2016-2024 (nie gesehen) zeigt NEGATIVE "
    "Performance in allen vier Sub-Perioden -- der Edge ist bisher nur fuer das 2024-08/2026-08-Fenster "
    "nachgewiesen. Zwei Runden Regime-Filter-Suche fanden keinen vorhersagenden Filter (siehe Tab "
    "\"Portfolio &amp; Risk\"). Details: <code>knowledge/projects/gold-ctnl-edge-portfolio.md</code>.",
    kind="danger",
)

h4, h1, m15, m5 = load_data()
cont_signaled, cont_trades = run_continuation_backtest(h4, h1, m5, m15)
rev_signaled, rev_trades_single, rev_trades_concurrent = run_reversal_backtest(h4, h1, m15)

tab_cont, tab_rev, tab_portfolio, tab_history = st.tabs([
    ":material/trending_up: Continuation",
    ":material/sync_alt: Reversal-Kaskade",
    ":material/pie_chart: Portfolio & Risk",
    ":material/history: Weg dorthin",
], on_change="rerun")

# -------------------------------------------------------------- Tab 1: Continuation
def _render_tab_tab_cont():
    with st.expander(":material/menu_book: Strategie-Regeln", expanded=False):
        st.markdown(
            """
            <div class="ctnl-writeup">
            H4 (Invalidierung) -> H1 (trend-gefilterter BOS) -> M5 (Entry) -> TP am gegenüberliegenden
            H4-Liquiditätslevel ("trade from liquidity to liquidity").
            </div>
            <div class="ctnl-caveats">
            <b>1. Trendfilter:</b> ema_adx_combo auf M15 (EMA20/50-Cross, ADX&ge;20 als Gate -- Selektivitaet
            schlaegt reine Richtungsbestimmung)<br>
            <b>2. H1-Struktur:</b> BOS (Bruch eines Swing High/Low) muss mit dem Trendfilter übereinstimmen<br>
            <b>3. M5-Entry ("direct"):</b> Sweep-and-Reject des H1-Referenzlevels (die Swing, die den BOS
            einleitete) -- Inducement-Konzept<br>
            <b>4. Stop:</b> Entry &minus; 0.5&times;ATR ab dem M5-Sweep-Level<br>
            <b>5. Target:</b> Literales gegenüberliegendes H4-Level (nicht ATR-basiert), min. 0.5&times;ATR
            Mindestabstand<br>
            <b>6. Invalidierung:</b> H4 bricht die Trendrichtung erneut<br>
            <b>7. Re-Entry:</b> getestet, hilft NICHT -- Einzelposition ist final
            </div>
            """,
            unsafe_allow_html=True,
        )

    cont_is, cont_oos, cont_oos_trades, cont_oos_sig = is_oos_split(cont_signaled, cont_trades)
    bh_cont = buy_and_hold_stats(m5)

    section_title("Ergebnis (Out-of-Sample, 2025-08 bis 2026-08)")
    tile_row([
        ("N TRADES", str(cont_oos["n_trades"])),
        ("WIN-RATE", f"{cont_oos['win_rate']*100:.1f}%"),
        ("PROFIT-FAKTOR", fmt_num(cont_oos["profit_factor"])),
        ("SHARPE", fmt_num(cont_oos["sharpe"])),
        ("CAGR", fmt_pct(cont_oos["cagr"])),
        ("MAXDD", fmt_pct(cont_oos["max_drawdown"])),
    ])

    section_title("IS vs. OOS vs. Buy & Hold")
    comp_df = pd.DataFrame([
        {"Fenster": "In-Sample", "n": str(cont_is["n_trades"]), "Win-Rate": fmt_wr(cont_is["win_rate"]), "PF": fmt_num(cont_is["profit_factor"]), "Sharpe": fmt_num(cont_is["sharpe"]), "CAGR": fmt_pct(cont_is["cagr"]), "MaxDD": fmt_pct(cont_is["max_drawdown"])},
        {"Fenster": "Out-of-Sample", "n": str(cont_oos["n_trades"]), "Win-Rate": fmt_wr(cont_oos["win_rate"]), "PF": fmt_num(cont_oos["profit_factor"]), "Sharpe": fmt_num(cont_oos["sharpe"]), "CAGR": fmt_pct(cont_oos["cagr"]), "MaxDD": fmt_pct(cont_oos["max_drawdown"])},
        {"Fenster": "Buy & Hold (OOS)", "n": "--", "Win-Rate": "--", "PF": "--", "Sharpe": fmt_num(bh_cont["sharpe"]), "CAGR": fmt_pct(bh_cont["cagr"]), "MaxDD": fmt_pct(bh_cont["max_drawdown"])},
    ])
    st.dataframe(comp_df, hide_index=True)

    if not cont_oos_trades.empty:
        sorted_ret = cont_oos_trades["return_pct"].sort_values(ascending=False)
        without_best = cont_oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, cont_oos_sig.index)
        st.caption(f"Outlier-Check (OOS ohne besten Trade): PF {cont_oos['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f}, Sharpe {cont_oos['sharpe']:.2f} -> {s_wo['sharpe']:.2f}")

    st.markdown("#### :material/candlestick_chart: Chart & Entries (M5, OOS-Trades)")
    render_chart(m5[m5.index >= SPLIT], cont_oos_trades, "cont")

    section_title("Exit-Grund-Aufschlüsselung (OOS)")
    render_exit_breakdown(cont_oos_trades, bar_minutes=5)

# -------------------------------------------------------------- Tab 2: Reversal-Kaskade
def _render_tab_tab_rev():
    with st.expander(":material/menu_book: Strategie-Regeln", expanded=False):
        st.markdown(
            """
            <div class="ctnl-writeup">
            H4 (Doppel-Sweep-Erschöpfung) -> H1 (Doppel-BOS-Bestätigung) -> M15 (repeat_sweep-Entry) ->
            5R-ATR-Ziel, MIT Re-Entry.
            </div>
            <div class="ctnl-caveats">
            <b>1. H4-Erschöpfung:</b> ZWEI Sweep-and-Reject-Events am selben erl_high/erl_low (die "doppelte
            Manipulation") + EMA-Reject-Bestätigung (geglättete EMA)<br>
            <b>2. H1-Bestätigung:</b> Doppel-BOS in Fade-Richtung, ausgerichtet auf die H4-These<br>
            <b>3. M15-Entry ("repeat_sweep"):</b> ZWEITER Sweep-and-Reject desselben H1-Referenzlevels
            (nicht der erste) -- für ein besseres Chance-Risiko-Verhältnis. M5-Entry explizit getestet und
            verworfen (repeat_sweep degeneriert auf M5 zu Mikro-Rauschen: 10.819 statt 3.258 Rohsignale)<br>
            <b>4. Stop:</b> 3.0&times;ATR (bewusst weit -- Fade-Trades brauchen Raum)<br>
            <b>5. Target:</b> 5R (ATR-Vielfaches vom initialen Risiko), kein Breakeven<br>
            <b>6. Max. Haltedauer:</b> 384 M15-Bars (96h)<br>
            <b>7. Re-Entry:</b> max_concurrent=3 -- hilft HIER deutlich (hump-shaped Optimum, zweimal
            unabhaengig bestaetigt), im Gegensatz zu Continuation
            </div>
            """,
            unsafe_allow_html=True,
        )

    rev_is, rev_oos, rev_oos_trades, rev_oos_sig = is_oos_split(rev_signaled, rev_trades_single)
    bh_rev = buy_and_hold_stats(m15)

    section_title("Einzelposition-Referenz (Out-of-Sample, kein Re-Entry)")
    tile_row([
        ("N TRADES", str(rev_oos["n_trades"])),
        ("WIN-RATE", f"{rev_oos['win_rate']*100:.1f}%"),
        ("PROFIT-FAKTOR", fmt_num(rev_oos["profit_factor"])),
        ("SHARPE", fmt_num(rev_oos["sharpe"])),
        ("CAGR", fmt_pct(rev_oos["cagr"])),
        ("MAXDD", fmt_pct(rev_oos["max_drawdown"])),
    ])

    rev_conc_oos = rev_trades_concurrent[rev_trades_concurrent["entry_time"] >= SPLIT]
    rev_sim = simulate_account_reentry(rev_conc_oos, starting_equity=STARTING_EQUITY, risk_pct=0.01, max_concurrent=3)
    daily_rev = equity_curve_to_daily_returns(rev_sim["equity_curve"], rev_oos_sig.index)

    section_title("Mit Re-Entry (finale Config: max_concurrent=3, $100k/1% Risiko)")
    tile_row([
        ("N TRADES", str(rev_sim["n_taken"])),
        ("GESKIPPT", str(rev_sim["n_skipped"])),
        ("SHARPE", fmt_num(annualized_sharpe(daily_rev))),
        ("TOTAL RETURN", fmt_pct(rev_sim["final_equity"] / STARTING_EQUITY - 1)),
        ("END-KAPITAL", f"${rev_sim['final_equity']:,.0f}"),
    ])

    section_title("IS vs. OOS (Einzelposition) vs. Buy & Hold")
    comp_df = pd.DataFrame([
        {"Fenster": "In-Sample", "n": str(rev_is["n_trades"]), "Win-Rate": fmt_wr(rev_is["win_rate"]), "PF": fmt_num(rev_is["profit_factor"]), "Sharpe": fmt_num(rev_is["sharpe"]), "CAGR": fmt_pct(rev_is["cagr"]), "MaxDD": fmt_pct(rev_is["max_drawdown"])},
        {"Fenster": "Out-of-Sample (Einzelpos.)", "n": str(rev_oos["n_trades"]), "Win-Rate": fmt_wr(rev_oos["win_rate"]), "PF": fmt_num(rev_oos["profit_factor"]), "Sharpe": fmt_num(rev_oos["sharpe"]), "CAGR": fmt_pct(rev_oos["cagr"]), "MaxDD": fmt_pct(rev_oos["max_drawdown"])},
        {"Fenster": "Out-of-Sample (Re-Entry)", "n": str(rev_sim["n_taken"]), "Win-Rate": "--", "PF": "--", "Sharpe": fmt_num(annualized_sharpe(daily_rev)), "CAGR": fmt_pct(cagr(daily_rev)), "MaxDD": fmt_pct(max_drawdown(daily_rev))},
        {"Fenster": "Buy & Hold (OOS)", "n": "--", "Win-Rate": "--", "PF": "--", "Sharpe": fmt_num(bh_rev["sharpe"]), "CAGR": fmt_pct(bh_rev["cagr"]), "MaxDD": fmt_pct(bh_rev["max_drawdown"])},
    ])
    st.dataframe(comp_df, hide_index=True)

    caveat_box(
        "<b>Re-Entry hilft hier substanziell</b> (Sharpe/Return deutlich höher als Einzelposition) -- "
        "der gegenteilige Befund zu Continuation, wo Re-Entry NICHT half. Grund: Reversal-Kaskades Sharpe "
        "zeigt ein echtes hump-shaped Optimum bei max_concurrent=3-4 (zweimal unabhängig via 432- und "
        "4725-Combo-Sweep bestätigt), waehrend Continuations Sharpe mit mehr Concurrency monoton faellt."
    )

    st.markdown("#### :material/candlestick_chart: Chart & Entries (M15, OOS-Trades, alle Kandidaten)")
    render_chart(m15[m15.index >= SPLIT], rev_conc_oos, "rev")

    section_title("Exit-Grund-Aufschlüsselung (OOS, Einzelposition)")
    render_exit_breakdown(rev_oos_trades, bar_minutes=15)

# -------------------------------------------------------------- Tab 3: Portfolio & Risk
def _render_tab_tab_portfolio():
    cont_oos_trades_only = cont_trades[cont_trades["entry_time"] >= SPLIT]
    rev_conc_oos_only = rev_trades_concurrent[rev_trades_concurrent["entry_time"] >= SPLIT]
    rev_oos_sig_index = rev_signaled[rev_signaled.index >= SPLIT].index

    fk, ek, blend = run_portfolio(cont_oos_trades_only, rev_conc_oos_only, rev_oos_sig_index)

    section_title("50/50-Portfolio (gleichgewichtet, Baseline 1% Risiko je Sleeve)")
    tile_row([
        ("SHARPE", fmt_num(blend["sharpe"])),
        ("CAGR", fmt_pct(blend["cagr"])),
        ("TOTAL RETURN", fmt_pct(blend["total_return"])),
        ("MAXDD", fmt_pct(blend["max_drawdown"])),
    ])
    st.caption("Korrelation der Tagesrenditen zwischen den Bausteinen: -0.033 -- praktisch unabhängig, nur 3 von ~66 aktiven Handelstagen überlappen beide.")

    section_title("FK Challenge (IQ Markets) -- max 6% Drawdown, max 1%/Position, Ziel +8%")
    tile_row([
        ("RISK CONT.", "0.50%"),
        ("RISK REV.", "0.15%"),
        ("REALISIERTE MAXDD", fmt_pct(fk["realized_mdd"])),
        ("TOTAL RETURN", fmt_pct(fk["total_return"])),
        ("P(MAXDD>6%)", f"{fk['breach_prob']:.1%}"),
    ])
    caveat_box(
        f"Monte-Carlo (2000 zirkuläre Bootstrap-Pfade, block_size=20): Median MaxDD "
        f"<b>{fk['mc_p50_mdd']:.1%}</b>, Median TotalReturn <b>{fk['mc_p50_ret']:+.1%}</b>, "
        f"P5-P95-Spanne TotalReturn <b>{fk['mc_p5_ret']:+.1%}</b> bis <b>{fk['mc_p95_ret']:+.1%}</b>. "
        f"Ursprünglich gewählter 1.00%/0.25%-Pick hatte P(Bruch)=49.7% -- verworfen, da eine reine "
        f"Punktschätzung aus EINEM historischen Pfad irreführend optimistisch war.",
        kind="good",
    )

    section_title("EK (Eigenkapital) -- renditeoptimiert, kein hartes DD-Limit")
    tile_row([
        ("RISK CONT.", "2.00%"),
        ("RISK REV.", "1.50%"),
        ("REALISIERTE MAXDD", fmt_pct(ek["realized_mdd"])),
        ("TOTAL RETURN", fmt_pct(ek["total_return"])),
        ("MEDIAN MC-SHARPE", fmt_num(ek["median_sharpe"])),
    ])
    st.caption(f"Monte-Carlo Median MaxDD {ek['mc_p50_mdd']:.1%}, Median TotalReturn {ek['mc_p50_ret']:+.1%}, P5-P95 {ek['mc_p5_ret']:+.1%} bis {ek['mc_p95_ret']:+.1%}.")

    section_title("Phase-6-Robustheit -- Walk-Forward, Regimefilter, Kill-Switch")
    caveat_box(
        "<b>Walk-Forward 2016-2024 (nie gesehen):</b> beide Bausteine NEGATIV in allen 4 Sub-Perioden "
        "(Continuation Sharpe -0.93 bis -2.00, Reversal-Kaskade -0.46 bis +0.13). Buy&amp;Hold schlägt "
        "beide in 3 von 4 Fenstern. Der Edge ist bislang nur für 2024-08/2026-08 belegt.",
        kind="danger",
    )
    caveat_box(
        "<b>Regime-Filter-Suche (2 Runden, 8 Variablen):</b> ADX(D1)-Trendstärke, Nähe zum rollierenden "
        "2J-Hoch, VIX, DXY-Niveau/-Momentum, Öl-Niveau/-Momentum, Gold-DXY-Korrelation -- KEINE trennt die "
        "verlierenden von der gewinnenden Periode sauber. Zentralbankkäufe (Rekord seit 2022) und "
        "De-Dollarisierung sind real, erklären die exakte Zeitgrenze aber nicht (2022-24 war bereits "
        "Rekordkäufe-Fenster, performte trotzdem negativ). Krieg/Trump-Regime/Gold-ETF-Inflows haben keine "
        "sauber quantifizierbare Datenquelle im Repo. Details: "
        "<code>knowledge/projects/gold-ctnl-edge-portfolio.md</code>.",
        kind="alert",
    )
    caveat_box(
        "<b>Kill-Switch (Design, noch nicht live):</b> statt eines Vorab-Filters ein Realized-Performance-"
        "Schwellenwert -- die Monte-Carlo-P5-Bänder oben sind die Referenz. Fällt die tatsächliche "
        "rollierende Live-Performance signifikant darunter, ist das ein objektives Pause-Signal, "
        "unabhängig davon ob der genaue Auslöser bekannt ist. Wird mit dem Live-Bot (stündlicher Log) "
        "operationalisiert.",
    )

# -------------------------------------------------------------- Tab 4: Weg dorthin
def _render_tab_tab_history():
    section_title("Kritischer Fund: Stop-Loss-Bug (2026-08-19)")
    caveat_box(
        "Beim Bauen der Trade-Charts fiel auf: die Stop-Loss-Referenz landete in der Pipeline eine Bar "
        "zu frueh (Off-by-one), sodass 62-65% aller Trades faktisch OHNE Stop liefen. Behoben in beiden "
        "Pipelines (<code>.shift(1)</code>); alle Zahlen auf dieser Seite sind post-Fix.",
        kind="alert",
    )

    section_title("Durchbrüche nach dem Bugfix")
    st.markdown(
        """
| Baustein | Durchbruch | Befund |
|---|---|---|
| Reversal-Kaskade Entry | repeat_sweep (2. Sweep desselben Levels) | OOS Sharpe 0.08 -> 1.61 |
| Reversal-Kaskade Sizing | Re-Entry (max_concurrent=3, statt Einzelposition) | Hump-shaped Optimum, zweimal bestätigt |
| Continuation Trendfilter | ema_adx_combo (EMA-Cross + ADX-Selektivität) | OOS Sharpe 1.62 -> 1.95, schlägt adx_di und ema_cross |
| Reversal-Kaskade M5-Entry | explizit getestet, verworfen | repeat_sweep degeneriert auf M5 zu Mikro-Rauschen (10.819 Rohsignale statt 3.258) |
"""
    )

    section_title("Verworfen (Reversal-Kaskade Entry-Logik)")
    st.markdown(
        """
| Ansatz | Befund |
|---|---|
| Zonen-Toleranz statt exaktem Level (H4-Sweep) | Mehr Trades, aber schlechterer IS-Sharpe |
| Single-Sweep statt Doppel-Sweep (H4) | Mehr Trades, aber schlechterer IS-Sharpe |
| H1-Inducement (erstes statt aktuelles Level) | Verschlechtert durchgehend (IS Sharpe -0.72 bis -1.11) |
| H4-Magnitude-Filter (Range-Groesse) | Bricht OOS ein, nicht outlier-robust |
| H4-Volumen-Erschoepfung (Signed-Pressure-Z-Score) | Verschlechtert eigenstaendig |
| H4-Level-Alter | Leicht positiv IS, bricht OOS ein |
| EMA-Ribbon-Stretch (MTF-Reversal-Zone) | Bei jeder Schwelle nicht hilfreich |
| EMA-Cross / EMA-Touch als LTF-Entry | Deutlich schlechter als Sweep-basiert |
| Trendlinien-Bruch als LTF-Entry (Reversal) | Nicht getestet vs. repeat_sweep -- repeat_sweep gewann direkt |
| H4-Trendbestätigung (ema_cross ODER ema_adx_combo) | Beide zu wenig IS-Trades, schlechter OOS |
| M5 statt M15 als LTF-Entry | repeat_sweep degeneriert zu Rauschen, IS-Standout schlägt nicht das M15-Original |
| **repeat_sweep (2. Sweep desselben Levels)** | **Durchbruch: OOS Sharpe 0.08 -> 1.61** |
"""
    )

    section_title("Verworfen (Continuation Entry-Logik / Trendfilter)")
    st.markdown(
        """
| Ansatz | Befund |
|---|---|
| "zone" (Spike in die Zone statt Sweep-and-Reject) | OOS Sharpe 1.49 -- solide, aber schwaecher als "direct" |
| "repeat_sweep" (2. Sweep desselben Levels) | OOS Sharpe 0.82 -- deutlich schlechter |
| "trendline" (Bruch der internen Gegentrend-Linie) | OOS Sharpe -0.74 -- deutlich schlechter |
| adx_di (reine Richtung, kein Selektivitäts-Gate) | Vorgänger-Champion, geschlagen von ema_adx_combo |
| H1/H4 als Trendfilter-Timeframe (statt M15) | Unabhängig SL/TP-optimiert, bleibt trotzdem hinter M15 zurück |
| H4-Manipulation-Bestätigung (Stop-Hunt vor Fortsetzung) | Redundant mit bestehender H1-BOS-Logik |
| **"direct" (Sweep-and-Reject) + ema_adx_combo-Filter** | **Bleibt Sieger: OOS Sharpe 1.95** |
"""
    )

    section_title("Phase 6 -- Robustheit (2026-08-20, siehe Tab \"Portfolio & Risk\")")
    st.markdown(
        """
| Test | Ergebnis |
|---|---|
| p6_1 Walk-Forward 2016-2024 | NEGATIV in allen 4 Sub-Perioden -- Edge bisher nur für 2024-26 belegt |
| p6_2 Monte-Carlo-Bootstrap (etabliertes Muster) | FK P(MaxDD>6%)=7.8%, EK Median-Sharpe 2.42 |
| p6_3 Kosten-Sensitivität | Breakeven bei ~32-40bps Spread (5x Puffer über den angenommenen 8bps) |
| p6_4 Regime-Filter (2 Runden, 8 Variablen) | Kein vorhersagender Filter gefunden -- Kill-Switch statt Vorab-Filter |
"""
    )
    st.caption(
        "Prozess-Lektion: Phase 6 wurde ursprünglich NICHT vor dem Portfolio-Bau abgeschlossen, sondern "
        "erst nachträglich auf Nachfrage nachgeholt -- siehe knowledge/projects/gold-ctnl-edge-portfolio.md."
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
for _tab, _render in [
    (tab_cont, _render_tab_tab_cont), (tab_rev, _render_tab_tab_rev),
    (tab_portfolio, _render_tab_tab_portfolio), (tab_history, _render_tab_tab_history),
]:
    if _tab.open:
        with _tab:
            _render()
