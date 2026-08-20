"""Fertige Strategien -- CTNL Edge Strategie (Gold XAUUSD), aus dem
mentor-eigenen SMC-Regelwerk (CTTNL/Inducement-/CHoCH-BOS-Material, chat
2026-08-14) rekonstruiert und über mehrere Sessions IS/OOS validiert
(2026-08-19).

Zwei unabhängige, beide Buy&Hold-im-Sharpe-schlagende Bausteine:
  1. Continuation ("mit dem Trend"): H4 (Invalidierung) -> H1 (trend-
     gefilterter BOS) -> M5 direct-Entry (Sweep-and-Reject des H1-
     Referenzlevels) -> TP am gegenüberliegenden H4-Liquiditätslevel.
     gold_smc_htf_ltf/continuation.py.
  2. Reversal-Kaskade ("gegen den Trend, an der Wende"): H4 Doppel-Sweep-
     Erschöpfung -> H1 Doppel-BOS -> M15 repeat_sweep-Entry (2. Sweep
     desselben H1-Referenzlevels, für besseres CRV) -> 5R-ATR-Ziel.
     gold_smc_htf_ltf/reversal_cascade.py.

Portfolio-Kombination beider Bausteine ist der nächste Schritt (noch nicht
Teil dieser Seite -- "Zwischenstand", chat 2026-08-19).

Dark/monospace-Styling matcht app_pages/mt5_trend_pullback.py /
cls_practical_strategy.py (gleiche Palette, "ctnl-"-Präfix). Chart & Entries
nutzt dieselbe TradingView-Lightweight-Charts-Einbettung wie mt5_trend_
pullback.py."""

import json

import pandas as pd

import streamlit as st
from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import annualized_sharpe, cagr, max_drawdown, summarize

st.set_page_config(page_title="CTNL Edge Strategie", page_icon=":material/military_tech:", layout="wide")

START, END = "2024-08-01", "2026-08-01"
SPLIT = pd.Timestamp("2025-08-01", tz="America/New_York")
SPREAD_BPS = 8.0

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
    cls = {"neutral": "ctnl-caveats", "good": "ctnl-good", "alert": "ctnl-alert"}[kind]
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
        _h4, _h1, _m5, trend_df=_m15, trend_indicator="adx_di",
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
    cfg = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96)
    trades = simulate_trades(signaled, cfg)
    return signaled, trades


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
    "Inducement, CHoCH/BOS), über mehrere Sessions rekonstruiert und mit strikter IS/OOS-Disziplin "
    "(IS 2024-08 bis 2025-08, OOS 2025-08 bis 2026-08, spread_bps=8) validiert. <b>Beide schlagen Gold "
    "Buy&amp;Hold im Sharpe, keine schlägt es im CAGR</b> -- Gold hatte im OOS-Fenster einen "
    "außergewöhnlich starken Lauf (Buy&amp;Hold Sharpe 0.73, CAGR +16.0%, MaxDD -28.6%).",
    kind="good",
)
caveat_box(
    "<b>Zwischenstand (2026-08-19):</b> Portfolio-Kombination beider Bausteine ist der nächste Schritt, "
    "noch nicht Teil dieser Seite. Continuation-Entry-Logik wird gerade weiter optimiert/validiert.",
    kind="alert",
)

h4, h1, m15, m5 = load_data()
cont_signaled, cont_trades = run_continuation_backtest(h4, h1, m5, m15)
rev_signaled, rev_trades = run_reversal_backtest(h4, h1, m15)

tab_cont, tab_rev, tab_history = st.tabs([
    ":material/trending_up: Continuation",
    ":material/sync_alt: Reversal-Kaskade",
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
            <b>1. Trendfilter:</b> ADX/DI auf M15 (adx_min entscheidet Richtung + Gültigkeit)<br>
            <b>2. H1-Struktur:</b> BOS (Bruch eines Swing High/Low) muss mit dem Trendfilter übereinstimmen<br>
            <b>3. M5-Entry ("direct"):</b> Sweep-and-Reject des H1-Referenzlevels (die Swing, die den BOS
            einleitete) -- Inducement-Konzept<br>
            <b>4. Stop:</b> Entry &minus; 0.5&times;ATR ab dem M5-Sweep-Level<br>
            <b>5. Target:</b> Literales gegenüberliegendes H4-Level (nicht ATR-basiert), min. 0.5&times;ATR
            Mindestabstand<br>
            <b>6. Invalidierung:</b> H4 bricht die Trendrichtung erneut
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
            5R-ATR-Ziel.
            </div>
            <div class="ctnl-caveats">
            <b>1. H4-Erschöpfung:</b> ZWEI Sweep-and-Reject-Events am selben erl_high/erl_low (die "doppelte
            Manipulation") + EMA-Reject-Bestätigung (geglättete EMA)<br>
            <b>2. H1-Bestätigung:</b> Doppel-BOS in Fade-Richtung, ausgerichtet auf die H4-These<br>
            <b>3. M15-Entry ("repeat_sweep"):</b> ZWEITER Sweep-and-Reject desselben H1-Referenzlevels
            (nicht der erste) -- für ein besseres Chance-Risiko-Verhältnis<br>
            <b>4. Stop:</b> 3.0&times;ATR (bewusst weit -- Fade-Trades brauchen Raum)<br>
            <b>5. Target:</b> 5R (ATR-Vielfaches vom initialen Risiko), kein Breakeven<br>
            <b>6. Max. Haltedauer:</b> 96 M15-Bars (24h)
            </div>
            """,
            unsafe_allow_html=True,
        )

    rev_is, rev_oos, rev_oos_trades, rev_oos_sig = is_oos_split(rev_signaled, rev_trades)
    bh_rev = buy_and_hold_stats(m15)

    section_title("Ergebnis (Out-of-Sample, 2025-08 bis 2026-08)")
    tile_row([
        ("N TRADES", str(rev_oos["n_trades"])),
        ("WIN-RATE", f"{rev_oos['win_rate']*100:.1f}%"),
        ("PROFIT-FAKTOR", fmt_num(rev_oos["profit_factor"])),
        ("SHARPE", fmt_num(rev_oos["sharpe"])),
        ("CAGR", fmt_pct(rev_oos["cagr"])),
        ("MAXDD", fmt_pct(rev_oos["max_drawdown"])),
    ])

    section_title("IS vs. OOS vs. Buy & Hold")
    comp_df = pd.DataFrame([
        {"Fenster": "In-Sample", "n": str(rev_is["n_trades"]), "Win-Rate": fmt_wr(rev_is["win_rate"]), "PF": fmt_num(rev_is["profit_factor"]), "Sharpe": fmt_num(rev_is["sharpe"]), "CAGR": fmt_pct(rev_is["cagr"]), "MaxDD": fmt_pct(rev_is["max_drawdown"])},
        {"Fenster": "Out-of-Sample", "n": str(rev_oos["n_trades"]), "Win-Rate": fmt_wr(rev_oos["win_rate"]), "PF": fmt_num(rev_oos["profit_factor"]), "Sharpe": fmt_num(rev_oos["sharpe"]), "CAGR": fmt_pct(rev_oos["cagr"]), "MaxDD": fmt_pct(rev_oos["max_drawdown"])},
        {"Fenster": "Buy & Hold (OOS)", "n": "--", "Win-Rate": "--", "PF": "--", "Sharpe": fmt_num(bh_rev["sharpe"]), "CAGR": fmt_pct(bh_rev["cagr"]), "MaxDD": fmt_pct(bh_rev["max_drawdown"])},
    ])
    st.dataframe(comp_df, hide_index=True)

    if not rev_oos_trades.empty:
        sorted_ret = rev_oos_trades["return_pct"].sort_values(ascending=False)
        without_best = rev_oos_trades.drop(index=sorted_ret.index[0])
        s_wo = summarize(without_best, rev_oos_sig.index)
        st.caption(f"Outlier-Check (OOS ohne besten Trade): PF {rev_oos['profit_factor']:.3f} -> {s_wo['profit_factor']:.3f}, Sharpe {rev_oos['sharpe']:.2f} -> {s_wo['sharpe']:.2f}")

    caveat_box(
        "<b>max_hold ist hier der profitabelste Exit-Grund</b> (hohe Win-Rate, Trades im Plus, erreichen "
        "aber das weite 5R-Ziel nicht immer innerhalb von 24h) -- kein Fehlverhalten, sondern mögliches "
        "Optimierungspotenzial (längeres Zeitfenster), noch nicht final getestet."
    )

    st.markdown("#### :material/candlestick_chart: Chart & Entries (M15, OOS-Trades)")
    render_chart(m15[m15.index >= SPLIT], rev_oos_trades, "rev")

    section_title("Exit-Grund-Aufschlüsselung (OOS)")
    render_exit_breakdown(rev_oos_trades, bar_minutes=15)

# -------------------------------------------------------------- Tab 3: Weg dorthin
def _render_tab_tab_history():
    section_title("Kritischer Fund: Stop-Loss-Bug (2026-08-19)")
    caveat_box(
        "Beim Bauen der Trade-Charts fiel auf: die Stop-Loss-Referenz landete in der Pipeline eine Bar "
        "zu frueh (Off-by-one), sodass 62-65% aller Trades faktisch OHNE Stop liefen. Behoben in beiden "
        "Pipelines (<code>.shift(1)</code>); alle Zahlen auf dieser Seite sind post-Fix. Der fruehere "
        "scheinbare Erfolg der Reversal-Kaskade (Sharpe 0.95) war zu grossen Teilen ein Artefakt dieses "
        "Bugs -- nach dem Fix war zunaechst KEIN Edge mehr vorhanden, bis die repeat_sweep-Entry-Logik "
        "(unten) den Durchbruch brachte.",
        kind="alert",
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
| **repeat_sweep (2. Sweep desselben Levels)** | **Durchbruch: OOS Sharpe 0.08 -> 1.61** |
"""
    )

    section_title("Verworfen (Continuation Entry-Logik)")
    st.markdown(
        """
| Ansatz | Befund |
|---|---|
| "zone" (Spike in die Zone statt Sweep-and-Reject) | OOS Sharpe 1.32 -- solide, aber schwaecher als "direct" |
| "repeat_sweep" (2. Sweep desselben Levels) | OOS Sharpe -0.65 -- deutlich schlechter |
| "trendline" (Bruch der internen Gegentrend-Linie) | OOS Sharpe -1.29 -- deutlich schlechter |
| **"direct" (Sweep-and-Reject, unveraendert)** | **Bleibt Sieger: OOS Sharpe 1.62** |
"""
    )
    st.caption(
        "Auffaellig: die Trendlinien-Bruch-Idee (aus echten TradingView-Chartbeispielen abgeleitet) "
        "funktioniert nur in der Reversal-Kaskade nicht -- fuer Continuation ist der reine Sweep-and-"
        "Reject bislang durch nichts geschlagen worden."
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
for _tab, _render in [(tab_cont, _render_tab_tab_cont), (tab_rev, _render_tab_tab_rev), (tab_history, _render_tab_tab_history)]:
    if _tab.open:
        with _tab:
            _render()
