"""Auction Market Playbook -- interactive dashboard for auction_playbook/.

Reconstructs Fabio Valentini's "Auction Market Playbook" (ChartFanatics /
Tradezella, Apr 2025, Futures/Scalping): one unified value-area-breakout
state machine that forks into Trend Continuation (a held breakout) or Mean
Reversion (a failed/reclaimed breakout), run on two data universes -
crypto (Binance, real per-bar taker buy/sell aggression) and the paper's
actual named assets (SP500/NASDAQ via Dukascopy E-mini CFD proxies, an
OHLC-shape aggression proxy since Dukascopy has no taker-side split).

See MEMORY (fabio-trading-bot-project) for the full history: two discarded
crypto-only drafts, the Step-5 target contradiction found and resolved with
the user, and the parallel futures run.
"""

import altair as alt
import pandas as pd

import streamlit as st
from auction_playbook.data import fetch_klines
from auction_playbook.dukascopy_data import fetch_index_bars
from auction_playbook.metrics import equity_curve_from_trades, trade_stats
from auction_playbook.signals import PlaybookConfig, generate_playbook_trades

st.set_page_config(page_title="Auction Market Playbook", page_icon=":material/gavel:", layout="wide")

LONG_START, LONG_END = "2025-08-01", "2026-07-29"
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
FUTURES_SYMBOLS = ["SP500", "NASDAQ"]
ALL_SYMBOLS = CRYPTO_SYMBOLS + FUTURES_SYMBOLS
TIMEFRAME_LABELS = ["5 Minuten", "15 Minuten"]
SETUP_LABELS = {"trend_continuation": "Trend Continuation", "mean_reversion": "Mean Reversion"}


def _is_crypto(symbol: str) -> bool:
    return symbol in CRYPTO_SYMBOLS


def _interval_for(symbol: str, label: str) -> str:
    if _is_crypto(symbol):
        return {"5 Minuten": "5m", "15 Minuten": "15m"}[label]
    return {"5 Minuten": "M5", "15 Minuten": "M15"}[label]


@st.cache_data(ttl="1h", show_spinner="Lade Marktdaten...")
def load_raw(symbol: str, timeframe_label: str) -> pd.DataFrame:
    interval = _interval_for(symbol, timeframe_label)
    if _is_crypto(symbol):
        return fetch_klines(symbol, interval, LONG_START, LONG_END)
    return fetch_index_bars(symbol, interval, LONG_START, LONG_END)


@st.cache_data(ttl="1h", show_spinner="Simuliere Trades...")
def load_trades(symbol: str, timeframe_label: str, cfg_kwargs: dict) -> pd.DataFrame:
    df = load_raw(symbol, timeframe_label)
    return generate_playbook_trades(df, PlaybookConfig(**cfg_kwargs))


with st.sidebar:
    st.markdown("### Konfiguration (Tab \"Backtest\")")
    symbol = st.selectbox("Instrument", ALL_SYMBOLS, help="BTCUSDT/ETHUSDT = Binance, echte Aggression. SP500/NASDAQ = Dukascopy E-mini-Proxy (Paper-Assets), Aggression aus Kerzenform genaehert.")
    timeframe_label = st.radio("Zeitrahmen", TIMEFRAME_LABELS)
    setup_filter = st.multiselect("Setup(s)", list(SETUP_LABELS), default=list(SETUP_LABELS), format_func=lambda k: SETUP_LABELS[k])
    aggression_z = st.slider("Aggressions-Schwelle (Std.-Abw. Delta)", 0.5, 3.0, 1.5, 0.1)
    reclaim_window = st.slider("Reclaim-Fenster (Bars)", 6, 48, 24, help="Wie lange ein Ausbruch Zeit hat zurueckzukommen, bevor er als 'haeltend' (Trend) statt 'gescheitert' (Reversion) gilt.")
    st.caption(
        "Datenquelle: Binance (Krypto, gecacht) bzw. Dukascopy (SP500/NASDAQ E-mini-Proxy, gecacht). "
        "Zeitraum: 12 Monate (2025-08-01 bis 2026-07-29)."
    )

cfg_kwargs = {"aggression_z": aggression_z, "reclaim_window": reclaim_window}

tab_components, tab_backtest = st.tabs(["Strategiebestandteile", "Backtest"], on_change="rerun")

# =============================================================================
# Tab: Strategiebestandteile
# =============================================================================
def _render_tab_components():
    st.markdown("## :material/gavel: Auction Market Playbook -- Strategiebestandteile")
    st.caption("Quelle: Fabio Valentini's Playbook, ChartFanatics / Tradezella, April 2025 (Futures, Scalping)")

    st.markdown(
        "Kernidee: der Markt pendelt zwischen **Balance** (Preis rotiert um Fair Value, Volume "
        "Profile bildet einen Point of Control/POC) und **Imbalance** (eine Seite ist aggressiv, "
        "Preis sucht neuen Fair Value). Drei Bedingungen muessen zusammenkommen, sonst bleibt man "
        "flat: **Market State** (Balance/Imbalance) → **Location** (Volume Profile: LVN/POC) → "
        "**Aggression** (Order Flow: grosse Prints, CVD-Druck)."
    )

    st.markdown("### Die zwei Hauptstrategieansaetze")
    col_trend, col_rev = st.columns(2)
    with col_trend:
        with st.container(border=True):
            st.markdown("#### :material/trending_up: 1. Trend Continuation")
            st.caption("\"Out-of-Balance → Seek New Balance\"")
            st.markdown(
                "- **Wann**: Preis bricht aus der Value Area des Vortages aus **und haelt** "
                "(kein schneller Reclaim)\n"
                "- **Location**: Volume Profile ueber die Impulse-Leg → LVNs darin\n"
                "- **Trigger**: Preis laeuft zurueck in eine LVN, **Aggression in Trendrichtung** "
                "(grosse Buy/Sell-Prints)\n"
                "- **Stop**: knapp hinter der LVN (ATR-skalierter Puffer statt woertlicher "
                "\"1-2 Ticks\" -- siehe Hinweis unten)\n"
                "- **Break-even**: bei starkem CVD-Druck in Trade-Richtung\n"
                "- **Exit**: bei **Gegen-Aggression** (nicht am Vortages-POC -- siehe "
                "Widerspruch unten)\n"
                "- **Session**: New York (13:00-21:00 UTC)"
            )
    with col_rev:
        with st.container(border=True):
            st.markdown("#### :material/trending_down: 2. Mean Reversion")
            st.caption("\"Out-of-Balance → Back Into Balance\"")
            st.markdown(
                "- **Wann**: Preis bricht aus der Value Area aus **und scheitert** (reklamiert "
                "schnell zurueck)\n"
                "- **Location**: Volume Profile ueber die Reclaim-Leg → LVNs darin\n"
                "- **Trigger**: Pullback in die LVN, **Aggression gegen die gescheiterte "
                "Ausbruchsrichtung**\n"
                "- **Stop**: knapp hinter dem gescheiterten Extrem -- **nie nachziehen**\n"
                "- **Exit**: am POC der Balance (Center of Value)\n"
                "- **Session**: London (07:00-12:00 UTC)"
            )

    st.markdown("### Eine State-Machine fuer beide")
    st.markdown(
        "Beide Ansaetze starten vom selben Ereignis -- Ausbruch aus der Value Area des Vortages "
        "(explizit die \"Balance-Referenz\" des Papers). **Haelt** der Ausbruch (keine Rueckkehr "
        "innerhalb des Reclaim-Fensters) → Trend-Kandidat. **Scheitert** er (schneller Reclaim) → "
        "Reversion-Kandidat. Das entspricht der eigenen Rahmung des Papers als zwei Seiten "
        "derselben Medaille, nicht zwei unabhaengige Systeme."
    )

    st.warning(
        "**Gefundener Widerspruch im Paper, mit dir geklaert:** Setup 1 heisst \"Seek **New** "
        "Balance\", Step 5 sagt aber Ziel = \"**previous** balance POC\" -- sobald ein Move "
        "wirklich als Trend gilt, liegt dieser POC fast immer hinter dem Trade. Empirisch "
        "bestaetigt: 41 von 46 sauber qualifizierten Setups scheiterten **nur** daran. Geloest "
        "nach Ruecksprache: Exit bei Gegen-Aggression (wie im Trade-Breakdown-Beispiel des "
        "Papers), kein festes POC-Ziel mehr fuer Trend Continuation.",
        icon=":material/warning:",
    )

    st.markdown("### Was genau gemessen wird -- und was genaehert ist")
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("**BTCUSDT / ETHUSDT (Binance)**")
            st.caption(
                "Echtes Taker-Buy/Sell-Volumen pro Kerze (Binance liefert das direkt) → "
                "echtes Delta/CVD, keine Schaetzung. Aber: falsche Asset-Klasse (Paper meint "
                "Futures, nicht Krypto)."
            )
    with col_b:
        with st.container(border=True):
            st.markdown("**SP500 / NASDAQ (Dukascopy E-mini-Proxy)**")
            st.caption(
                "Trifft die im Paper genannten Assets (Futures ES/NASDAQ). Aber: Dukascopy hat "
                "keinen Taker-Split -- Delta ist ein Kerzenform-Proxy "
                "((Close-Open)/(High-Low) x Volumen), kein echter Order Flow. Auch Dukascopys "
                "eigenes \"Volumen\" ist bei Index-CFDs selbst schon ein Broker-Proxy, kein "
                "echtes CME-Boersenvolumen."
            )
    st.caption(
        "\"1-2 Tick Puffer\" aus dem Paper ist woertlich auf Futures kalibriert (z.B. ES-Tick "
        "$0.25) -- bei BTCUSDT (Tick $0.01 auf ~$60-100k) waere das wirkungslos. Stattdessen "
        "wird ueberall ein ATR-skalierter Puffer verwendet."
    )

    st.markdown("### Ehrlicher Befund -- drei unabhaengige Durchlaeufe, gleiches Ergebnis")
    st.info(
        "**Kein robuster Edge, in keiner der drei Versionen** (verworfene Krypto-Erstversion, "
        "ueberarbeitete Krypto-Version, Futures-Proxy-Version): Median-R-Multiple ist in fast "
        "jeder Variante genau **-1.00** -- der typische Trade verliert den vollen Stop, mehr als "
        "die Haelfte aller Trades. Der Profit Factor sieht in mehreren Varianten ueber 1.0 aus, "
        "faellt aber fast ueberall unter 1.0 sobald man nur den **einen besten Trade** entfernt "
        "-- ein Ausreisser-Effekt, keine wiederholbare Kante. Bei den Futures-Assets (naeher am "
        "Paper) ist das Bild tendenziell **noch fragiler** als bei Krypto. NASDAQ und SP500 auf "
        "identischen Parametern zeigen gegensaetzliche Ergebnisse (0.57 vs. 1.30 Profit Factor) "
        "-- ein klassisches Rauschmuster, kein echter Instrumenten-Unterschied.",
        icon=":material/insights:",
    )

# =============================================================================
# Tab: Backtest
# =============================================================================
def _render_tab_backtest():
    st.markdown(f"## :material/gavel: {symbol} — {timeframe_label}")
    if not _is_crypto(symbol):
        st.caption("Dukascopy E-mini-Proxy, Aggression aus Kerzenform genaehert (kein echter Taker-Split verfuegbar).")

    trades_all = load_trades(symbol, timeframe_label, cfg_kwargs)
    trades = trades_all[trades_all["setup"].isin(setup_filter)] if not trades_all.empty else trades_all
    stats = trade_stats(trades)

    with st.container(horizontal=True):
        st.metric("Trades", stats["n_trades"], border=True)
        st.metric("Win-Rate", f"{stats['win_rate']:.1%}" if stats["n_trades"] else "–", border=True)
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}" if stats["n_trades"] else "–", border=True)
        st.metric("PF ohne besten Trade", f"{stats['profit_factor_excl_best_trade']:.2f}" if stats["n_trades"] > 1 else "–", border=True)
        st.metric("Median R-Multiple", f"{stats['median_r_multiple']:.2f}" if stats["n_trades"] else "–", border=True)
        st.metric("Ø Haltedauer", f"{stats['avg_hold_bars']:.1f} Bars" if stats["n_trades"] else "–", border=True)

    st.space("medium")

    col1, col2 = st.columns([2, 1])
    with col1:
        with st.container(border=True):
            st.markdown("**Equity-Kurve (verkettet je Trade, nach Exit-Zeitpunkt)**")
            if stats["n_trades"] > 0:
                curve = equity_curve_from_trades(trades)
                chart = (
                    alt.Chart(curve)
                    .mark_line(color="#4c78a8")
                    .encode(
                        x=alt.X("exit_time:T", title="Exit-Zeitpunkt"),
                        y=alt.Y("equity:Q", title="Equity (Start = 1.0)", scale=alt.Scale(zero=False)),
                        tooltip=[alt.Tooltip("exit_time:T"), alt.Tooltip("equity:Q", format=".4f")],
                    )
                    .properties(height=340)
                )
                st.altair_chart(chart)
            else:
                st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

    with col2:
        with st.container(border=True):
            st.markdown("**Exit-Gruende**")
            if stats["n_trades"] > 0 and stats.get("exit_reason_counts"):
                reason_df = pd.Series(stats["exit_reason_counts"]).rename("count")
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
        st.markdown("**Setup-Aufschluesselung**")
        if stats["n_trades"] > 0:
            rows = []
            for key, label in SETUP_LABELS.items():
                sub = trades[trades["setup"] == key]
                s = trade_stats(sub)
                rows.append({"Setup": label, **s})
            breakdown = pd.DataFrame(rows).set_index("Setup").drop(columns=["exit_reason_counts"], errors="ignore")
            st.dataframe(
                breakdown,
                column_config={
                    "win_rate": st.column_config.NumberColumn("Win-Rate", format="percent"),
                    "profit_factor": st.column_config.NumberColumn("Profit Factor", format="%.2f"),
                    "profit_factor_excl_best_trade": st.column_config.NumberColumn("PF ohne Besten", format="%.2f"),
                    "avg_r_multiple": st.column_config.NumberColumn("Ø R", format="%.2f"),
                    "median_r_multiple": st.column_config.NumberColumn("Median R", format="%.2f"),
                    "avg_hold_bars": st.column_config.NumberColumn("Ø Haltedauer (Bars)", format="%.1f"),
                },
            )
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")

    st.space("medium")

    with st.container(border=True):
        st.markdown("**Trade-Log**")
        if not trades.empty:
            display_trades = trades.copy()
            display_trades["setup"] = display_trades["setup"].map(SETUP_LABELS)
            display_trades["direction"] = display_trades["direction"].map({1: "Long", -1: "Short"})
            display_trades["return_bps"] = display_trades["return_pct"] * 1e4
            st.dataframe(
                display_trades.sort_values("entry_time", ascending=False).drop(columns=["return_pct"]),
                hide_index=True,
                column_config={
                    "setup": st.column_config.TextColumn("Setup"),
                    "entry_time": st.column_config.DatetimeColumn("Einstieg", format="YYYY-MM-DD HH:mm"),
                    "exit_time": st.column_config.DatetimeColumn("Ausstieg", format="YYYY-MM-DD HH:mm"),
                    "direction": st.column_config.TextColumn("Richtung"),
                    "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.4f"),
                    "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.4f"),
                    "stop": st.column_config.NumberColumn("Stop", format="%.4f"),
                    "target": st.column_config.NumberColumn("Ziel (POC)", format="%.4f"),
                    "return_bps": st.column_config.NumberColumn("Return (bps)", format="%.2f"),
                    "r_multiple": st.column_config.NumberColumn("R-Multiple", format="%.2f"),
                    "exit_reason": st.column_config.TextColumn("Exit-Grund"),
                    "hold_bars": st.column_config.NumberColumn("Haltedauer (Bars)"),
                },
            )
        else:
            st.info("Keine Trades bei dieser Konfiguration.", icon=":material/info:")


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
# Sidebar widgets (symbol, timeframe_label, setup_filter, cfg_kwargs) execute
# unconditionally above, outside any tab, so tab_backtest can read them
# regardless of which tab is open.
for _tab, _render in [(tab_components, _render_tab_components), (tab_backtest, _render_tab_backtest)]:
    if _tab.open:
        with _tab:
            _render()
