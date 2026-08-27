"""Gold (XAUUSD) Asian-Range Breakout -- interactive dashboard for
asian_range_breakout/.

Source: user-supplied TradeStation EasyLanguage strategy spec
(Gold_Asian_Breakout_Strategy.txt, 2026-08-04) -- NOT an academic paper like
most other strategies in this repo, but a fully-specified rule set, so no
extraction/interpretation ambiguity: build the Asian-session (21:00-01:00 NY)
high/low range, arm a resting Buy-Stop/Sell-Stop OCO pair the moment the
window closes, stop = stop_frac x range width, no take-profit, flat-by
exit_time (11:00 NY). One trade per window. See asian_range_breakout/engine.py
for the exact fidelity choices/simplifications versus the literal
EasyLanguage semantics.
"""

from datetime import timedelta

import altair as alt
import pandas as pd

import streamlit as st
from asian_range_breakout.chart import build_entry_chart
from asian_range_breakout.data import fetch_gold_m15, fetch_gold_m15_live
from asian_range_breakout.engine import get_latest_setup, simulate_asian_breakout
from asian_range_breakout.execution_overlay import simulate_asian_breakout_overlay
from asian_range_breakout.filters import (
    apply_adx_filter,
    apply_entry_delay_filter,
    apply_gold_liquidity_filter_causal,
    apply_silver_alignment_filter,
    apply_trend_bias_filter,
    attach_entry_delay,
    attach_gold_liquidity,
    attach_silver_alignment,
    attach_trend_bias,
    rolling_liquidity_threshold,
)
from asian_range_breakout.montecarlo import run_monte_carlo, simulate_time_to_target, summarize_monte_carlo
from asian_range_breakout.sizing import simulate_equity
from asian_range_breakout.walkforward import (
    run_delay_filter_walk_forward,
    run_execution_mode_walk_forward,
    run_liquidity_filter_walk_forward,
    run_trend_bias_walk_forward,
    run_walk_forward,
)
from bond_yield_indicator.friction import fetch_fx_friction
from combined_strategy.data import fetch_timeframe
from strategy.backtest import trades_to_daily_returns
from strategy.metrics import max_drawdown, summarize, trade_stats

st.set_page_config(page_title="Gold Asian-Range Breakout", page_icon=":material/wb_twilight:", layout="wide")

START, END = "2016-01-01", "2026-07-29"
SPLIT = "2021-01-01"
TREND_SMA_WINDOW = 200
SILVER_ALIGNMENT_WINDOW = 5
LIQUIDITY_QUANTILE = 2 / 3
LIQUIDITY_MIN_PERIODS = 250
TTP_MAX_DAILY_DD = 0.03
TTP_MAX_TOTAL_DD = 0.07
RECOMMENDED_RISK_PCT = 0.01


@st.cache_data(ttl="10m", show_spinner="Lade Gold M15-Daten (Dukascopy, ~10 Jahre)...")
def load_data() -> pd.DataFrame:
    # Short TTL on purpose (unlike the 6h caches below, which hold small
    # derived series): backed by a local disk cache underneath, so a cache
    # miss here is a fast re-read, not a slow re-fetch - see knowledge/ +
    # app_pages/ny_open_orb_portfolio.py for the analogous fix.
    return fetch_gold_m15(START, END)


@st.cache_data(ttl="6h", show_spinner="Berechne Gold-Tagesschlusskurse...")
def load_daily_close() -> pd.Series:
    """Fuer den Trend-Bias-Filter (siehe Strategiebestandteile) - abgeleitet
    aus derselben Dukascopy-M15-Reihe, keine zusaetzliche Datenquelle."""
    return load_data()["close"].tz_localize(None).resample("D").last().dropna()


@st.cache_data(ttl="6h", show_spinner="Lade Silber-Tagesschlusskurse (Dukascopy)...")
def load_daily_close_silver() -> pd.Series:
    """Fuer den Silber-Alignment-Filter (siehe Strategiebestandteile) -
    Dukascopy XAGUSD, dieselbe Quelle wie ueberall sonst in diesem Repo."""
    silver_m15 = fetch_timeframe("SILVER", "M15", START, END)
    return silver_m15["Close"].tz_localize(None).resample("D").last().dropna()


@st.cache_data(ttl="6h", show_spinner="Berechne Gold-Liquiditaetsproxy (Corwin-Schultz)...")
def load_gold_friction() -> pd.Series:
    """Fuer den Liquiditaetsfilter (siehe Strategiebestandteile) - Corwin-
    Schultz Bid-Ask-Spread-Schaetzer aus Golds eigenen Daily-OHLC, wieder-
    verwendet aus dem Bond-Yield-Spread-Indikator-Projekt
    (bond_yield_indicator/friction.py). Keine neue Datenquelle."""
    return fetch_fx_friction("GOLD", START, END)


@st.cache_data(ttl="15m", show_spinner="Lade aktuelle Gold-Futures-Daten (yfinance)...")
def load_live_data() -> pd.DataFrame:
    """Für den 'Live Entry-Signal'-Tab: NICHT Dukascopy (Bug behoben
    2026-08-05, erster Fix war nur "bis heute statt bis Backtest-Ende" -
    zeigte sich als unzureichend, Dukascopys eigene Daten liefen selbst
    frisch abgerufen >10h hinter der Realzeit her, ein Anbieter-seitiges
    Limit, kein Cache-Problem). Jetzt yfinance GC=F (Gold-Future, ~19 Min.
    Verzug beim Test) - andere Instrument-Definition als Spot-XAUUSD
    (Cost-of-Carry-Aufschlag/-Abschlag, gelegentliche Rollover-Lücken),
    für eine reine Anschauungsansicht aber deutlich aktueller als die
    Backtest-Datenquelle. TTL 15 Min entsprechend kurz gehalten."""
    return fetch_gold_m15_live(period="60d")


@st.cache_data(ttl="6h", show_spinner="Simuliere Trades...")
def load_trades(
    stop_frac: float,
    tp_r_mult: float | None,
    be_trigger_r: float | None,
    spread_price: float,
    slippage_price: float,
    use_overlay: bool = False,
) -> pd.DataFrame:
    """use_overlay=True: Execution-Overlay-Fuellung (siehe Strategiebestandteile,
    Abschnitt "Execution-Overlay") statt sofortiger Wick-Fuellung - Signal
    (welches Fenster ausbricht, welche Richtung) bleibt identisch, nur
    Fuellzeitpunkt/-preis aendert sich. Separat gecacht von der Wick-Variante
    (anderer Cache-Key durch den zusaetzlichen Parameter)."""
    df = load_data()
    if use_overlay:
        return simulate_asian_breakout_overlay(
            df,
            stop_frac=stop_frac,
            tp_r_mult=tp_r_mult,
            be_trigger_r=be_trigger_r,
            spread_price=spread_price,
            slippage_price=slippage_price,
        )
    return simulate_asian_breakout(
        df,
        stop_frac=stop_frac,
        tp_r_mult=tp_r_mult,
        be_trigger_r=be_trigger_r,
        spread_price=spread_price,
        slippage_price=slippage_price,
    )


with st.sidebar:
    st.markdown("### Konfiguration (Tab \"Backtest\")")
    stop_frac = st.slider("Stop-Faktor (x Range-Breite)", 0.5, 2.0, 1.0, 0.1)
    use_tp = st.toggle(
        "Take-Profit aktivieren", value=False,
        help="Original-Regel hat KEIN Kursziel (reitet bis Zeit-Exit). Eigener Test (2026-08-04): "
        "jedes getestete TP-Level macht das Ergebnis schlechter, siehe Strategiebestandteile.",
    )
    tp_r_mult = st.slider("Take-Profit (x Stop-Distanz)", 0.5, 3.0, 1.5, 0.1, disabled=not use_tp) if use_tp else None
    use_be = st.toggle(
        "Break-Even aktivieren", value=False,
        help="Original-Regel zieht den Stop NIE nach. Eigener Test (2026-08-04): jedes getestete "
        "BE-Level macht das Ergebnis DRASTISCH schlechter (Win-Rate faellt von 39% auf teils nur "
        "5%) - siehe Strategiebestandteile. Aus denselben Gruenden wie beim Take-Profit: die "
        "Strategie lebt davon, Gewinner ungebremst laufen zu lassen.",
    )
    be_trigger_r = st.slider("Break-Even ab (x Stop-Distanz)", 0.25, 1.5, 0.5, 0.25, disabled=not use_be) if use_be else None
    use_adx_filter = st.toggle(
        "ADX-Regimefilter aktivieren (ADX < 15 raus)", value=True,
        help="Eigener Test (2026-08-04): ADX<15-Trades enden zu 59% im Stop (vs. 47% sonst), "
        "in beiden Zeitraum-Haelften konsistent. Standardmaessig AN, da es die robusteste "
        "gefundene Verbesserung ist - siehe Strategiebestandteile.",
    )
    use_trend_filter = st.toggle(
        "Trend-Bias-Filter aktivieren (nur mit Gold-SMA200 handeln)", value=True,
        help="Aus dem 151-Trading-Strategies-Paper abgeleitet (Time-Series-Momentum, "
        "2026-08-08): nur Breakouts IN Richtung von Golds eigenem Tages-Trend (Long ueber "
        "SMA200, Short darunter). Robust ueber 4 SMA-Fenster, IS/OOS, Walk-Forward (8/8 Jahre "
        "bestaetigt, 7/8 mit PF>1.0) und nicht Ausreisser-getrieben - siehe Strategiebestandteile. "
        "Halbiert die Trade-Zahl (weniger absolute Rendite), verbessert aber Profit Factor und "
        "senkt den Max Drawdown spuerbar.",
    )
    use_delay_filter = st.toggle(
        "Fuellverzoegerungs-Filter aktivieren (max. 3 Bars Wartezeit)", value=True,
        help="Aus der Bottleneck-Diagnose (2026-08-08): schnelle Fuellungen (Breakout direkt "
        "nach Fenster-Schluss) sind durchweg besser als langsame - PF faellt monoton von 1.31 "
        "(sofort) auf 1.02 (8+ Bars Wartezeit). Kein Lookahead: entspricht einer Order, die nach "
        "3 Bars (45 Min.) automatisch verfaellt, statt bis 11:00 zu warten. Walk-Forward-"
        "bestaetigt (7/8 Jahre), 10/11 Kalenderjahre netto positiv - siehe Strategiebestandteile.",
    )
    use_silver_filter = st.toggle(
        "Silber-Alignment-Filter aktivieren (5-Tage-Richtung)", value=True,
        help="Aus einem User-Paper zu Gold-Silber-BTC-Lead-Lag (2026-08-08): nur Breakouts IN "
        "Richtung von Silbers eigener 5-Tage-Kursbewegung. Walk-Forward-bestaetigt (5/6 Jahre), "
        "rettet insbesondere das schwache Jahr 2023 (PF 0.89 -> 1.82). Verbessert Sharpe UND "
        "Win-Rate (nicht nur Profit Factor wie die anderen Filter) - siehe Strategiebestandteile.",
    )
    use_liquidity_filter = st.toggle(
        "Liquiditaets-Filter aktivieren (Corwin-Schultz, unteres Zweidrittel)", value=True,
        help="Aus dem Bond-Yield-Spread-Indikator-Projekt (2026-08-11): nur Breakouts an Tagen "
        "mit normaler/guter Gold-Liquiditaet (Corwin-Schultz Bid-Ask-Proxy). Staerkster bisher "
        "gefundener Filter - besteht Structure-Preserving-Randomisierung (p=0.000/0.001) UND "
        "Walk-Forward (6/6 Testjahre bestaetigt), kausale (Lookahead-freie) rollierende Schwelle "
        "- siehe Strategiebestandteile.",
    )
    use_overlay_entry = st.toggle(
        "Execution-Overlay-Fuellung aktivieren (statt sofortiger Wick-Fuellung)", value=True,
        help="Aus dem Zarattini-&-Pagani-Fast-Alpha-Konzept (2026-08-09): statt sofort bei "
        "Beruehrung des Range-Levels zu fuellen, wird auf die erste Gegenrichtungs-Kerze "
        "(M15-Schlusskurs) nach dem Ausbruch gewartet und DANN gefuellt - gleiches Signal, "
        "nur anderer Fuellzeitpunkt/-preis. Volle Kette (ADX+Trend+Delay+Silber): Profit "
        "Factor 1.43 -> 1.80, IS/OOS beide verbessert, Ausreisser-robust, Walk-Forward "
        "waehlt Overlay in 6 von 8 Testjahren (nur 2019/2020 zu wenig Daten) - siehe "
        "Strategiebestandteile. Trade-off: manche Fenster liefern KEINEN Trade mehr (kein "
        "Pullback vor Sessionende), also weniger absolute Trade-Zahl.",
    )
    spread_price = st.slider(
        "Spread (USD, Round-Trip)", 0.0, 1.50, 0.30, 0.05,
        help="Wird hälftig auf Entry und Exit angerechnet, gegen dich.",
    )
    slippage_price = st.slider(
        "Zusatz-Slippage auf Stop-/Zeit-Exits (USD)", 0.0, 0.50, 0.10, 0.05,
        help="Nur auf Stop- und Zeit-Exits, nicht auf den Range-Entry selbst (siehe Strategiebestandteile).",
    )
    st.caption(f"Datenquelle: Dukascopy XAUUSD M15, {START} bis {END} (gecacht).")

tab_components, tab_backtest, tab_live, tab_walkforward = st.tabs(
    [
        ":material/wb_twilight: Strategiebestandteile",
        ":material/query_stats: Backtest",
        ":material/candlestick_chart: Live Entry-Signal",
        ":material/timeline: Walk-Forward & Equity",
    ],
    on_change="rerun",
)

# =============================================================================
# Tab: Strategiebestandteile
# =============================================================================
def _render_tab_components():
    st.markdown("## :material/wb_twilight: Gold Asian-Range Breakout -- Strategiebestandteile")
    st.caption("Quelle: user-bereitgestellte TradeStation-EasyLanguage-Spezifikation, 2026-08-04")

    st.markdown(
        "**Idee**: Während der Asien-Session bildet Gold typischerweise eine ruhige Range. "
        "Kommt der London-/frühe-US-Flow, bricht der Kurs die Range oft klar in eine Richtung "
        "und läuft. Gehandelt wird der Bruch von Asien-Range-Hoch/-Tief, geritten bis zu einem "
        "festen Zeit-Exit (kein Kursziel)."
    )

    st.markdown("### Regeln (Long und Short, ein Trade pro Tag)")
    st.markdown(
        "1. Asien-Range = höchstes Hoch / tiefstes Tief im Fenster 21:00-01:00 NY-Zeit.\n"
        "2. In dem Moment, in dem das Fenster schließt: Buy-Stop am Range-Hoch, Sell-Stop am "
        "Range-Tief - wer zuerst füllt, gewinnt (OCO), der andere verfällt.\n"
        "3. Stop-Abstand = stop_frac x Range-Breite (Standard 1.0 = volle Range-Breite).\n"
        "4. **Kein Kursziel** - die Position läuft bis zum Zeit-Exit.\n"
        "5. Flat-by-Time-Exit um 11:00 NY-Zeit."
    )
    st.info(
        "**Warum es (laut Quelle) realistischen Tests standhält**: die Orders werden GENAU in "
        "dem Moment platziert, in dem die Range schließt - keine Lücke zwischen Level-Definition "
        "und scharfgeschalteter Order. Das unterscheidet es von naiven "
        "\"Vortages-Range\"-Breakouts, wo eine mehrstündige Lücke den Kurs durch das Level laufen "
        "lässt, bevor die Order existiert.",
        icon=":material/info:",
    )

    st.markdown("### Umsetzung in diesem Repo")
    st.markdown(
        "Eigene bar-für-bar State-Machine (`asian_range_breakout/engine.py`), **nicht** "
        "`strategy.backtest.simulate_trades` - dieses Setup braucht eine über Nacht ruhende "
        "OCO-Order über ein Sitzungsfenster hinweg, das ist strukturell etwas anderes als ein "
        "Einzelbar-Signal mit einmaligem SL/TP. Gleiche Denkweise wie bei `auction_playbook`/"
        "`checklist_strategy` in diesem Repo."
    )
    with st.expander("Offengelegte Vereinfachungen gegenüber dem Original-Code"):
        st.markdown(
            "- Ein Bar, der beide Levels gleichzeitig berührt (H-L-Range überstreicht beides), "
            "wird übersprungen, nicht aufgelöst - die Order bleibt für den nächsten Bar bestehen "
            "(gleiche Konvention wie `orb_strategy.py`).\n"
            "- Entries füllen exakt am berührten Stop-Level, nicht am Bar-Open.\n"
            "- Der Zeit-Exit füllt am Close des ersten Bars, dessen NY-Zeit >= Exit-Zeit ist - "
            "das Original würde einen Bar später am Open füllen (\"next bar at market\"), eine "
            "kleine, offengelegte Vereinfachung.\n"
            "- Kosten: der halbe Round-Trip-Spread wird gegen Entry UND Exit gerechnet, "
            "Slippage nur auf Stop-/Zeit-Exits (nicht auf den präzisen Range-Entry selbst)."
        )

    st.markdown("### Ehrlicher Befund (10,5 Jahre, 2016-01 bis 2026-07, Dukascopy XAUUSD M15)")
    trades_default = load_trades(1.0, None, None, 0.30, 0.10)
    full_stats = summarize(trades_default, load_data().index)
    is_stats = trade_stats(trades_default[trades_default["entry_time"] < SPLIT])
    oos_stats = trade_stats(trades_default[trades_default["entry_time"] >= SPLIT])

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("**Gesamtzeitraum**")
            st.markdown(
                f"- {full_stats['n_trades']} Trades\n"
                f"- Sharpe {full_stats['sharpe']:.2f}, PF {full_stats['profit_factor']:.2f}\n"
                f"- Win-Rate {full_stats['win_rate']:.1%}\n"
                f"- Max Drawdown {full_stats['max_drawdown']:.1%}"
            )
    with col2:
        with st.container(border=True):
            st.markdown(f"**{START} - {SPLIT}**")
            st.markdown(
                f"- {is_stats['n_trades']} Trades\n"
                f"- PF {is_stats['profit_factor']:.3f}\n"
                f"- Win-Rate {is_stats['win_rate']:.1%}"
            )
    with col3:
        with st.container(border=True):
            st.markdown(f"**{SPLIT} - {END}**")
            st.markdown(
                f"- {oos_stats['n_trades']} Trades\n"
                f"- PF {oos_stats['profit_factor']:.3f}\n"
                f"- Win-Rate {oos_stats['win_rate']:.1%}"
            )

    st.success(
        "Anders als die meisten anderen Strategien in diesem Repo zeigt diese ohne jedes "
        "Parameter-Fitting (Standardwerte 1:1 aus der Quelle übernommen) über die volle "
        "10,5-Jahres-Historie einen positiven Edge, der sich über beide Hälften des Zeitraums "
        "grob hält (PF 1.00 vs. 1.15) und in **9 von 11 Kalenderjahren** netto positiv war "
        "(Verlustjahre: 2017, 2019). Kein Ausreißer-Einzeljahr trägt das Ergebnis.",
        icon=":material/check_circle:",
    )
    st.warning(
        "**Aber der Profit Factor ist dünn (1.09 bei Spread=0.30/Slippage=0.10) und knickt unter "
        "realistischen Kosten schnell um** - eigene Sensitivitätsanalyse (Bisektion) findet den "
        "Break-even-Punkt bei ca. **0.54 USD Round-Trip-Spread** (bei proportional mitskalierter "
        "Slippage). Retail-Gold-Spreads liegen je nach Broker/Konto oft im Bereich 0.20-0.50+, "
        "und diese Strategie handelt gezielt um Sessionübergänge (Asien-Schluss/London-Open) - "
        "typischerweise eher die teurere, nicht die günstigere Tageszeit für den Spread. Ob das "
        "live tragfähig ist, hängt stark vom tatsächlich erreichbaren Spread ab, nicht nur vom "
        "Backtest-Ergebnis. Median-Trade-Return ist leicht negativ (Verlierer sind volle "
        "Stop-Outs, Gewinner reiten den Trend - laut Quelle normal, aber ein Warnsignal für "
        "Kosten-Sensitivität).",
        icon=":material/warning:",
    )

    st.markdown("### SL/TP-Optimierung und Bottleneck-Analyse (2026-08-04)")
    st.markdown(
        "**Aufschlüsselung nach Exit-Grund** zeigt die Mechanik klar: Stops (1331 von 2700 "
        "Trades) sind per Konstruktion **immer** 100% Verlierer (Ø -0.38%), lösen im Schnitt "
        "schon nach ~4.5h aus. Zeit-Exits (1369 Trades) gewinnen dagegen zu **77.8%** (Ø "
        "+0.40%), laufen fast bis zum vollen ~10h-Fenster. Gewinn/Verlust-Verhältnis insgesamt "
        "1.67 - klassisches \"Verlierer klein halten, Gewinner laufen lassen\"-Profil."
    )
    col_sl, col_tp = st.columns(2)
    with col_sl:
        with st.container(border=True):
            st.markdown("**Stop-Faktor-Sweep (kein TP)**")
            st.caption(
                "0.5/0.75/1.25/1.5/2.0x Range-Breite getestet, alle mit In-Sample-PF < 1.0 "
                "(0.92-0.97) - **nur der Original-Wert 1.0x liegt in beiden Zeitraum-Hälften "
                "über 1.0** (IS 1.003, OOS 1.150). Der Stop ist also schon gut kalibriert, aber "
                "das ist ein schmaler Grat, kein breites Plateau - eher ein Robustheits-"
                "Warnsignal als eine Bestätigung."
            )
    with col_tp:
        with st.container(border=True):
            st.markdown("**Take-Profit-Sweep (stop_frac=1.0)**")
            st.caption(
                "0.5/1.0/1.5/2.0/3.0x Stop-Distanz getestet - **jedes einzelne TP-Level "
                "verschlechtert den Profit Factor** gegenüber \"kein TP\" (1.087 → 0.97-1.08). "
                "Passt zur Diagnose oben: der Gewinn entsteht fast ausschließlich dadurch, dass "
                "Zeit-Exit-Gewinner ungebremst laufen dürfen - ein TP kappt genau das, ohne den "
                "Stops zu helfen (die erreichen ohnehin nie ein TP)."
            )

    with st.container(border=True):
        st.markdown("**Break-Even-Sweep (eigene Erweiterung, nicht im Original)**")
        st.caption(
            "0.25/0.5/0.75/1.0x Stop-Distanz als BE-Trigger getestet - **jedes Level "
            "verschlechtert das Ergebnis drastisch**, nicht nur leicht: PF fällt von 1.087 "
            "(kein BE) auf 0.40-1.02, die Win-Rate bricht von 39.4% auf teils nur 5.2% ein "
            "(bei be_trigger_r=0.25). Gleicher Mechanismus wie beim Take-Profit: viele Trades, "
            "die später zum profitablen Zeit-Exit gelaufen wären, werden durch einen "
            "vorgezogenen Stop bei Breakeven abgewürgt, sobald sie kurz zurücksetzen, bevor "
            "die eigentliche Bewegung kommt. Mit ADX-Filter kombiniert (adx_min=15) bleibt "
            "das Muster identisch (PF 1.122 ohne BE → 0.45-1.07 mit)."
        )

    st.markdown("**Range-Breite als Filter?** (eigene, nicht im Original enthaltene Idee)")
    st.caption(
        "Asien-Range-Breite relativ zum eigenen 60-Tage-Median gruppiert: enge Nächte (< 70% "
        "vom Median) zeigen klar schwächere Setups (PF 1.05, Win-Rate nur 30.9%) als normale "
        "oder weite Nächte (PF ~1.09, Win-Rate 39-46%) - aber die Gesamtkorrelation Range-Breite "
        "vs. Return ist mit -0.036 praktisch null, das ist ein schwaches Randmuster, keine "
        "starke Kante. Selbst enge Nächte bleiben (knapp) profitabel - ein reiner Ausschluss "
        "würde nur unnötig Trades kosten."
    )
    st.info(
        "**Fazit zum Bottleneck**: Weder ein engerer/weiterer Stop noch ein Take-Profit "
        "verbessern das Ergebnis spürbar - die Original-Parameter sind schon nahe am Optimum "
        "dessen, was diese einfache SL/TP-Struktur hergibt. Der eigentliche Flaschenhals ist "
        "**nicht** SL/TP, sondern die **Kosten-Sensitivität** (Break-even bei ~0.54 USD Spread, "
        "siehe oben). Der wirksamere Hebel ist ein **Eingangsfilter**, der schwache Setups vor "
        "dem Trade aussortiert - siehe ADX-Regimefilter unten, der genau das leistet.",
        icon=":material/insights:",
    )

    st.markdown("### Regimefilter: ADX (implementiert) und VIX (getestet, verworfen)")
    col_adx, col_vix = st.columns(2)
    with col_adx:
        with st.container(border=True):
            st.markdown("**ADX-Regimefilter -- robust, jetzt Standard im Dashboard**")
            st.caption(
                "ADX(14) auf der M15-Reihe selbst, gemessen im Moment des Range-Schlusses "
                "(vor der Order-Scharfschaltung, kein Lookahead). Bucket-Analyse zeigt einen "
                "klaren, in beiden Zeitraum-Hälften stabilen Effekt: **ADX<15-Trades enden zu "
                "59% im Stop, ADX>=15-Trades nur zu 47%** - direkt der vom User gesuchte "
                "Mechanismus. Filter `adx_min=15` raus:\n\n"
                "- Trades: 2700 → 2190 (-19%)\n"
                "- Sharpe: 0.40 → **0.50**\n"
                "- Profit Factor: 1.087 → **1.122**\n"
                "- Max Drawdown: -18.5% → **-14.9%**\n"
                "- Break-even-Spread: 0.54 → **0.64 USD** (mehr Kosten-Puffer!)\n\n"
                "Konsistent in IS und OOS, ökonomisch plausibel (ADX<15 = kein klarer Trend, "
                "Ausbrüche sind in einem trendlosen Markt eher Fehlausbrüche). **Jetzt "
                "standardmäßig aktiv** im Backtest-Tab, lässt sich dort deaktivieren."
            )
    with col_vix:
        with st.container(border=True):
            st.markdown("**VIX-Filter -- getestet, keine robuste Kante gefunden**")
            st.caption(
                "Vortages-VIX-Schlusskurs (yfinance ^VIX, ffill über Wochenenden/Feiertage, "
                "kein Lookahead) in vier Buckets getestet. Ergebnis uneinheitlich zwischen "
                "IS und OOS - z.B. VIX<13: PF 0.947 (IS) vs. 1.687 (OOS), VIX>25: PF 1.014 "
                "(IS) vs. 1.375 (OOS) - beide fast verdoppeln sich zwischen den Hälften, ein "
                "klassisches Rauschmuster bei relativ dünnen Bucket-Größen (n=74-442), kein "
                "stabiler Zusammenhang. Einzig VIX 13-18 ist in beiden Hälften eher schwach "
                "(0.878 / 1.030), aber nicht klar genug, um daraus einen Filter zu bauen. "
                "**Nicht implementiert** - Reproduzierbar über `asian_range_breakout/vix.py` "
                "+ `filters.py::attach_vix`, falls später mit mehr Daten erneut geprüft werden soll."
            )

    st.markdown("### Aus dem 151-Trading-Strategies-Paper abgeleitete Kontextfilter (getestet, 2026-08-07)")
    st.caption(
        "Zwei konkrete Hypothesen aus der Gold-Bausteine-Seite (`app_pages/paper151.py`) gegen "
        "die ADX-gefilterte Produktionskonfiguration getestet - Fensterlängen-Sweep (3/5/10/20 "
        "Tage) plus IS/OOS-Split, gleiche Disziplin wie beim VIX-Level-Test oben. Beide zeigen "
        "**keine robuste, umsetzbare Kante** - siehe `scripts/research_gold_dxy_vix_change_filters.py`."
    )
    col_dxy, col_vixchg = st.columns(2)
    with col_dxy:
        with st.container(border=True):
            st.markdown("**DXY-Alignment -- Hypothese nicht bestätigt**")
            st.caption(
                "These: Long-Trades bei fallendem Dollar (DXY) / Short-Trades bei steigendem "
                "Dollar sollten besser halten als Trades gegen diesen Rückenwind. Ergebnis: "
                "**genau umgekehrt** und über alle 4 getesteten Fenster (3/5/10/20 Tage) sowie "
                "IS und OOS konsistent - \"misaligned\" Trades haben durchweg den höheren Profit "
                "Factor (z.B. Fenster=5: PF 1.21 misaligned vs. 1.04 aligned, IS 1.14 vs. 0.95, "
                "OOS 1.25 vs. 1.11). Konsistent im Vorzeichen, aber **nicht implementiert** - der "
                "Mechanismus für ein *umgekehrtes* Signal ist nicht ökonomisch plausibel "
                "hergeleitet, und dieses Repo hat schon mehrfach gesehen, wie ein zunächst "
                "konsistent aussehendes Muster bei genauerer Prüfung Rauschen war. Als "
                "Beobachtung festgehalten, nicht als Filter eingebaut."
            )
    with col_vixchg:
        with st.container(border=True):
            st.markdown("**VIX-Änderungsrate ('Spike') -- keine robuste Kante**")
            st.caption(
                "These: ein frischer Vola-Schub (VIX-Änderungsrate statt Level) sollte stärkere "
                "Breakout-Fortsetzung anzeigen als ein einfacher Level-Filter (der schon oben als "
                "Rauschen verworfen wurde). Ergebnis: **uneinheitlich über die Fensterlängen** - "
                "bei 3/5/10 Tagen ist \"kein Spike\" durchweg leicht besser (Fenster=5: PF 1.15 "
                "kein Spike vs. 1.06 Spike, IS 1.08 vs. 1.01, OOS 1.21 vs. 1.10), bei 20 Tagen "
                "kippt es (PF 1.18 Spike vs. 1.09 kein Spike) - genau das Rauschmuster, das schon "
                "beim VIX-Level-Test auftrat. **Nicht implementiert.**"
            )

    st.markdown("### Trend-Bias-Filter (Time-Series Momentum, Kap. 10.4) -- getestet, jetzt Standard (2026-08-08)")
    st.success(
        "**Erster wirklich robuster Fund aus dem 151-Strategies-Paper für diese Strategie.** "
        "These: Breakouts IN Richtung von Golds eigenem Tages-Trend (Long über SMA200 des "
        "Vortages-Schlusskurses, Short darunter) sollten besser halten als Breakouts gegen den "
        "Trend - dieselbe \"trade with the trend\"-Logik, die dem Paper-Kapitel zur Futures-"
        "Trendfolge zugrunde liegt, hier als Zusatzfilter statt als eigene Strategie. "
        "**Bestätigt sich über jeden getesteten Blickwinkel:**",
        icon=":material/check_circle:",
    )

    daily_close_writeup = load_daily_close()
    trend_base_trades = apply_adx_filter(load_trades(1.0, None, None, 0.30, 0.10), adx_min=15)
    trend_tagged = attach_trend_bias(trend_base_trades, daily_close_writeup, sma_window=TREND_SMA_WINDOW)

    col_tsweep, col_tmetrics = st.columns(2)
    with col_tsweep:
        with st.container(border=True):
            st.markdown("**Fenster-Sweep (SMA 50/100/150/200), volle Historie**")
            st.caption(
                "Aligned schlägt Counter-Trend bei **jedem** getesteten Fenster - PF-Abstand wird "
                "mit längerem Fenster sogar größer (SMA50: 1.13 vs. 1.10 → SMA200: 1.18 vs. 1.06). "
                "SMA200 gewählt, weil hier IS UND OOS beide klar bestätigen (bei SMA100 kippt OOS "
                "knapp: 1.15 vs. 1.19 - SMA200 ist der robustere Schnitt)."
            )
            st.caption(
                f"IS ({START}-{SPLIT}): Aligned PF 1.093 / WR 42.4% vs. Counter PF **0.960** / WR 37.2% "
                f"-- Counter-Trend liegt sogar unter Break-even.  \n"
                f"OOS ({SPLIT}-{END}): Aligned PF 1.220 / WR 43.7% vs. Counter PF 1.123 / WR 38.2%."
            )
    with col_tmetrics:
        with st.container(border=True):
            st.markdown("**Volle Kennzahlen: ADX-only vs. ADX+Trend-Aligned**")
            st.caption(
                "Profit Factor 1.122 → **1.176**, Sharpe 0.498 → **0.513**, Max Drawdown **-14.9% → "
                "-9.4%** (deutliche Verbesserung), aber Trades 2190 → 1027 und CAGR 3.48% → 2.25% "
                "(weniger absolute Rendite bei weniger Gelegenheiten - der übliche Trade-off eines "
                "schärferen Filters, wie schon beim ADX-Filter selbst). **Nicht Ausreißer-getrieben**: "
                "PF ohne den einzigen besten Trade (+3.07%) fällt nur von 1.176 auf 1.160."
            )

    st.markdown("**Walk-Forward-Validierung (Expanding-Window, gleiche Methodik wie beim ADX-Filter)**")
    trend_wf_table = run_trend_bias_walk_forward(trend_tagged, start_test_year=2019, end_test_year=2026)
    st.dataframe(
        trend_wf_table,
        hide_index=True,
        column_config={
            "test_year": st.column_config.NumberColumn("Testjahr"),
            "train_n_trades": st.column_config.NumberColumn("Trainings-Trades"),
            "filter_confirmed_on_train": st.column_config.CheckboxColumn("Filter bestätigt (nur Training)"),
            "n_trades_unfiltered": st.column_config.NumberColumn("Trades ungefiltert"),
            "pf_unfiltered": st.column_config.NumberColumn("PF ungefiltert", format="%.3f"),
            "n_trades_walkforward": st.column_config.NumberColumn("Trades Walk-Forward"),
            "pf_walkforward": st.column_config.NumberColumn("PF Walk-Forward", format="%.3f"),
            "win_rate_walkforward": st.column_config.NumberColumn("Win-Rate WF", format="%.1f%%"),
        },
    )
    n_confirmed_trend = int(trend_wf_table["filter_confirmed_on_train"].sum())
    n_positive_trend = int((trend_wf_table["pf_walkforward"] > 1.0).sum())
    st.info(
        f"Filter in **{n_confirmed_trend}/{len(trend_wf_table)}** Testjahren bereits aus den "
        f"Trainingsdaten allein bestätigt (ab 2019, kein Blick auf die Zukunft), "
        f"**{n_positive_trend}/{len(trend_wf_table)}** Testjahre mit PF>1.0 unter der Walk-Forward-"
        "Regel. Einziger Ausreißer: 2023 (PF 0.71) - passt zur bereits beim ADX-Filter "
        "dokumentierten echten OOS-Delle in diesem Jahr, kein Artefakt dieses neuen Filters.",
        icon=":material/insights:",
    )
    st.warning(
        "**Kombiniert mit ADX halbiert sich die Trade-Zahl gegenüber der reinen ADX-Konfiguration** "
        "(2190 → 1027) - statistisch immer noch eine solide Stichprobe, aber der Rückgang bei CAGR "
        "ist real, nicht nur ein Nebeneffekt. Wer absolute Rendite über Drawdown-Kontrolle "
        "priorisiert, kann den Filter im Sidebar-Toggle deaktivieren. Standardmäßig **AN**, aus "
        "denselben Gründen wie der ADX-Filter: konsistent über Fenster, IS/OOS und Walk-Forward, "
        "nicht Ausreißer-getrieben.",
        icon=":material/warning:",
    )
    st.caption(
        "Reproduzierbar über `asian_range_breakout/filters.py::attach_trend_bias`/"
        "`apply_trend_bias_filter` + `asian_range_breakout/walkforward.py::run_trend_bias_walk_forward` "
        "+ `scripts/research_gold_trend_bias_seasonality.py`."
    )

    with st.expander("Nebenbei geprüft: Saisonalität (Wochentag/Monat) -- Rauschen, nicht implementiert"):
        st.markdown(
            "Aus demselben Skript (`research_gold_trend_bias_seasonality.py`), eher der "
            "Vollständigkeit halber (Rohstoff-Kapitel des Papers) als mit plausiblem Mechanismus "
            "für eine Session-Breakout-Strategie: Wochentag zeigt Freitag/Donnerstag stark (PF "
            "1.41/1.30), Mittwoch schwach (PF 0.87) - bei n=395-470/Tag nicht dünn genug, um es "
            "sofort zu verwerfen, aber ohne erkennbaren Mechanismus. Monat-Aufschlüsselung ist "
            "deutlich unruhiger (Februar PF 0.81, März/Mai/Oktober >1.4, bei nur n=159-203/Monat) "
            "- klassisches Muster für Rauschen bei 12 dünnen Buckets, kein Saisonmuster mit "
            "erkennbarer Erzählung wie bei Agrarrohstoffen. **Nicht implementiert.**"
        )

    st.markdown("### Bottleneck-Diagnose: wo genau geht die Win-Rate verloren? (2026-08-08)")
    st.caption(
        "User-Anfrage: Bottleneck aufdecken und pruefen, ob sich die Win-Rate sinnvoll erhoehen "
        "laesst - inkl. kurzer Internet-Recherche zu etablierten Breakout-Techniken. Siehe "
        "`scripts/research_gold_bottleneck_diagnosis.py`."
    )
    st.info(
        "**Kernbefund: die Win-Rate ist strukturell gedeckelt, nicht zufaellig niedrig.** "
        "Stop-Exits sind per Konstruktion **immer** 100% Verlierer (45.5% aller Trades), "
        "Zeit-Exits gewinnen zu 79.1%. Die Strategie lebt vom asymmetrischen Payoff (fixer "
        "-1R-Stop, unbegrenzter Gewinn bis Zeit-Exit) - genau das macht sie trotz <44% "
        "Win-Rate profitabel, und genau deshalb haben TP/BE (die diese Asymmetrie kappen) "
        "das Ergebnis in frueheren Tests bereits verschlechtert. Eine hoehere Win-Rate ist "
        "hier kein Selbstzweck - der Hebel ist, WELCHE Trades ueberhaupt genommen werden, "
        "nicht wie sie gemanagt werden.",
        icon=":material/insights:",
    )

    col_diag1, col_diag2 = st.columns(2)
    with col_diag1:
        with st.container(border=True):
            st.markdown("**MFE-Analyse der Stop-Trades**")
            st.caption(
                "Wie nah kamen Verlierer an einen Gewinn, bevor sie umkehrten? 96% aller "
                "Stop-Trades bewegten sich zwischenzeitlich ins Plus, aber nur 18.8% erreichten "
                "je +1R (Median 0.40R). Das ist die Signatur eines echten Fehlausbruchs "
                "(kurzer Vorstoss, dann volle Umkehr) - kein Fall von \"Stop zu eng\"."
            )
    with col_diag2:
        with st.container(border=True):
            st.markdown("**Long vs. Short**")
            st.caption(
                "Long WR 44.6% / PF 1.176, Short WR 39.2% / PF 1.174 - Shorts haben eine "
                "niedrigere Win-Rate, aber im Schnitt groessere Gewinner, PF praktisch "
                "identisch. Kein Hebel: ein reiner Long-only-Filter wuerde nur die Trade-Zahl "
                "kappen, ohne den Profit Factor zu verbessern."
            )

    st.markdown("**Getestete Idee 1 (extern recherchiert): Close-Bestaetigung statt Docht-Beruehrung**")
    st.error(
        "Etablierte Breakout-Literatur empfiehlt, einen Ausbruch erst zu werten, wenn eine Kerze "
        "GESCHLOSSEN jenseits des Levels liegt, nicht nur den Docht beruehrt - filtert klassische "
        "Fehlausbrueche. Ein naiver Test (pruefen, ob die Fuellungs-Kerze selbst auch geschlossen "
        "bestaetigt) sah zunaechst spektakulaer aus (PF 1.48 bestaetigt vs. 0.92 unbestaetigt) - "
        "**das war aber ein Lookahead-Fehler**: der Kerzen-Schluss ist im Moment einer Stop-Order-"
        "Fuellung intrabar noch gar nicht bekannt. Sauber nachgebaut (`engine.py`, neuer Parameter "
        "`entry_mode=\"close\"` - wartet echt auf eine bestaetigende Kerze, Entry zum Schlusskurs "
        "dieser Kerze statt am Level) bricht der Effekt komplett zusammen: PF faellt auf **~1.00** "
        "(IS 0.87, OOS 1.07) - schlechter als die aktuelle Konfiguration. Grund: genau die "
        "schnellen, sofortigen Fuellungen (siehe unten) sind die besten Trades - Bestaetigung "
        "abwarten bedeutet, diese exakt zu verpassen und stattdessen zu einem schlechteren Preis "
        "einzusteigen. **Nicht implementiert - eine wichtige Lektion, keinen Post-hoc-Filter mit "
        "gleichzeitigem Signal und Fuellung zu verwechseln.**",
        icon=":material/dangerous:",
    )

    st.markdown("**Getestete Idee 2 (eigene Diagnose): Fuellverzoegerungs-Filter -- funktioniert, jetzt Standard**")
    st.success(
        "Wie lange nach Fenster-Schluss braucht der Ausbruch, um zu fuellen? **Klar monotoner "
        "Zusammenhang mit der Trade-Qualitaet**: sofortige Fuellung (0 Bars Wartezeit) PF 1.31, "
        "8+ Bars Wartezeit nur noch PF 1.02 (praktisch Break-even). Kein Lookahead - entspricht "
        "einer Order, die nach N Bars automatisch verfaellt, vollstaendig in Echtzeit umsetzbar. "
        "Filter `max_delay_bars=3` (45 Minuten) auf der ADX+Trend-Konfiguration:",
        icon=":material/check_circle:",
    )
    col_delay1, col_delay2 = st.columns(2)
    with col_delay1:
        with st.container(border=True):
            st.markdown("**Kennzahlen: +Fuellverzoegerungs-Filter**")
            st.caption(
                "Profit Factor 1.176 → **1.242**, Max Drawdown -9.4% → **-5.0%** (nochmal "
                "fast halbiert), Calmar-Ratio 0.238 → 0.330. Trades 1027 → 540, CAGR sinkt "
                "entsprechend (2.25% → 1.65%) - derselbe Trade-off wie bei den anderen beiden "
                "Filtern. Win-Rate bleibt praktisch unveraendert (43.1% → 43.1%) - dieser Filter "
                "verbessert die Trade-QUALITAET, nicht die Trefferquote selbst, was zum "
                "Kernbefund oben passt. Nicht Ausreisser-getrieben (PF ohne besten Trade: 1.21)."
            )
    with col_delay2:
        with st.container(border=True):
            st.markdown("**Walk-Forward + Jahresbilanz**")
            st.caption(
                "Expanding-Window-Walk-Forward: in 7/8 Testjahren (2019-2026) bestaetigt, 7/8 "
                "mit PF>1.0 (2023 bleibt schwach, aber besser als ungefiltert). **10 von 11 "
                "Kalenderjahren netto positiv** - mehr als jeder andere hier getestete Filter "
                "einzeln. Reproduzierbar ueber `filters.py::attach_entry_delay`/"
                "`apply_entry_delay_filter` + `walkforward.py::run_delay_filter_walk_forward`."
            )
    st.warning(
        "**Kombiniert (ADX + Trend-Bias + Fuellverzoegerung) sinkt die Stichprobe auf 540 Trades** "
        "- immer noch solide fuer die Gesamtaussage, aber pro Jahr teils nur 15-70 Trades. Wer "
        "mehr Handelsgelegenheiten priorisiert, kann den Filter im Sidebar-Toggle deaktivieren. "
        "Standardmaessig **AN**, aus denselben Gruenden wie die anderen beiden Filter: "
        "monotoner Zusammenhang, IS/OOS konsistent, Walk-Forward bestaetigt, nicht "
        "Ausreisser-getrieben.",
        icon=":material/warning:",
    )

    with st.expander("Getestet, 2026-08-08: Momentum-Thrust-Filter -- kein robustes Signal, nicht implementiert"):
        st.markdown(
            "Idee: ATR-normalisierte Kursbewegung der letzten N Bars VOR Fenster-Schluss "
            "(\"war schon echter Schwung im Markt, bevor die Session ueberhaupt schloss\") - "
            "kein Lookahead, anders konstruiert als ADX, Korrelation dazu nur 0.075 (echte "
            "Zusatzinformation). Zwei Varianten getestet "
            "(`scripts/research_gold_momentum_thrust_filter.py`): **Richtungs-Alignment** "
            "(Long nach Aufwaerts-Schwung, Short nach Abwaerts-Schwung) und **reine Staerke** "
            "(groesster Schwung unabhaengig von Richtung). **Beide kippen das Vorzeichen je "
            "nach Lookback-Fenster** (4/8/16/24/48 Bars) - bei Alignment schlaegt "
            "Gegen-Trend ab Fenster=8 sogar den Trend, bei Staerke dreht es bei Fenster=16 "
            "komplett um. Dasselbe Rauschmuster wie beim DXY- und VIX-Aenderungsraten-Test. "
            "**Nicht implementiert.**"
        )

    with st.expander("Getestet, 2026-08-08: CFTC-COT-Sentiment-Filter (Zhang & Laws 2013) -- keine robuste Kante, nicht implementiert"):
        st.markdown(
            "Idee aus einem User-Upload (SSRN 2382299, siehe \"Neue Papers\"-Seite): "
            "woechentlicher CFTC-COT-Bericht (kostenlos, CFTC-Socrata-API, keine Bezahl-Quelle "
            "noetig) liefert eine \"Wang-Sentiment\"-Kennzahl je Trader-Gruppe (rollierendes "
            "3-Jahres-Perzentil der Netto-Position). Zwei Konventionen getestet "
            "(`scripts/research_gold_cot_sentiment_filter.py`): **Commercial-Konvention** "
            "(Paper-Original: Long ausgerichtet auf bullishes Commercial-Sentiment) sieht im "
            "Fenster-Sweep (2/3/4 Jahre) auf den ersten Blick konsistent aus (PF Aligned > "
            "Counter in allen drei Fenstern), **bricht aber Out-of-Sample komplett zusammen** "
            "(PF 1.24 Aligned vs. 1.25 Counter, praktisch ein Unentschieden -- der komplette "
            "\"Vorteil\" steckt nur in der In-Sample-Haelfte, PF 1.72 vs. 1.11). Die gespiegelte "
            "**Non-Commercial-Konvention** kippt das Vorzeichen schon im reinen Fenster-Sweep. "
            "Passt zum eigenen ehrlichen Befund des Original-Papers: die Granger-Kausalitaet "
            "zeigt dort *keine* Vorhersagekraft von Sentiment auf Rendite, nur eine gleichzeitige "
            "Korrelation -- der im Paper gezeigte Handelserfolg (1999-2012, andere Instrumente/"
            "Konstruktion) repliziert sich nicht als Filter auf unserem Asian-Range-Breakout. "
            "**Nicht implementiert.**"
        )

    st.markdown("### Silber-Alignment-Filter (Gold-Silber-BTC-Lead-Lag) -- getestet, jetzt Standard (2026-08-08)")
    st.success(
        "**Zweiter echter Treffer aus den User-Papers.** Idee aus einer Literatursynthese zu "
        "Gold-Silber-Bitcoin-Lead-Lag (SSRN 7200580, siehe \"Neue Papers\"-Seite): Silber gilt "
        "als \"High-Beta-Version von Gold\" mit spekulativerem Orderflow. Einfachste direkt "
        "testbare Uebersetzung: **nur Breakouts in Richtung von Silbers eigener juengster "
        "Kursbewegung handeln** (5-Tage-Rendite von Silber, Dukascopy XAGUSD, keine neue "
        "Datenquelle). **Haelt jedem Test stand:**",
        icon=":material/check_circle:",
    )

    daily_close_silver_writeup = load_daily_close_silver()
    trend_delay_trades = apply_entry_delay_filter(
        apply_trend_bias_filter(trend_base_trades, daily_close_writeup, sma_window=TREND_SMA_WINDOW),
        max_delay_bars=3,
    )
    silver_tagged = attach_silver_alignment(trend_delay_trades, daily_close_silver_writeup, window=SILVER_ALIGNMENT_WINDOW)

    col_ssweep, col_smetrics = st.columns(2)
    with col_ssweep:
        with st.container(border=True):
            st.markdown("**Fenster-Sweep (1/3/5/10/20 Tage), volle Historie**")
            st.caption(
                "Aligned schlaegt Counter-Trend in 4 von 5 Fenstern (nur bei 10 Tagen knapp "
                "umgekehrt) - bei 5 Tagen der groesste Abstand: PF 1.43 Aligned vs. 1.00 Counter. "
                "IS UND OOS bestaetigen dieselbe Richtung (nicht nur eine Seite wie beim COT-"
                "Test): IS PF 1.65 vs. 0.76, OOS PF 1.32 vs. 1.13 - der Vorteil schrumpft OOS, "
                "kippt aber nicht um."
            )
    with col_smetrics:
        with st.container(border=True):
            st.markdown("**Volle Kennzahlen: +Silber-Filter vs. ohne**")
            st.caption(
                "Profit Factor 1.242 → **1.426**, Sharpe 0.490 → **0.610** (deutliche "
                "Verbesserung), Max Drawdown -5.0% → **-4.0%**. Trades 540 → 310, aber CAGR "
                "bleibt fast unveraendert (1.65% → 1.68%) - anders als die anderen Filter "
                "verbessert dieser auch die **Win-Rate** (43.1% → 46.5%), nicht nur den Profit "
                "Factor. Nicht Ausreisser-getrieben (PF ohne besten Trade: 1.376)."
            )

    st.markdown("**Walk-Forward-Validierung (Expanding-Window, gleiche Methodik wie die anderen drei Filter)**")
    silver_wf_table = run_trend_bias_walk_forward(silver_tagged, start_test_year=2021, end_test_year=2026)
    st.dataframe(
        silver_wf_table,
        hide_index=True,
        column_config={
            "test_year": st.column_config.NumberColumn("Testjahr"),
            "train_n_trades": st.column_config.NumberColumn("Trainings-Trades"),
            "filter_confirmed_on_train": st.column_config.CheckboxColumn("Filter bestätigt (nur Training)"),
            "n_trades_unfiltered": st.column_config.NumberColumn("Trades ungefiltert"),
            "pf_unfiltered": st.column_config.NumberColumn("PF ungefiltert", format="%.3f"),
            "n_trades_walkforward": st.column_config.NumberColumn("Trades Walk-Forward"),
            "pf_walkforward": st.column_config.NumberColumn("PF Walk-Forward", format="%.3f"),
            "win_rate_walkforward": st.column_config.NumberColumn("Win-Rate WF", format="%.1f%%"),
        },
    )
    n_confirmed_silver = int(silver_wf_table["filter_confirmed_on_train"].sum())
    n_positive_silver = int((silver_wf_table["pf_walkforward"] > 1.0).sum())
    st.info(
        f"Filter in **{n_confirmed_silver}/{len(silver_wf_table)}** Testjahren bestaetigt, "
        f"**{n_positive_silver}/{len(silver_wf_table)}** Testjahre mit PF>1.0. Besonders "
        "bemerkenswert: **rettet das schwache 2023** (PF 0.89 ungefiltert -> 1.82 gefiltert) - "
        "genau das Jahr, das beim ADX- und Fuellverzoegerungs-Filter als einzige echte OOS-Delle "
        "uebrig blieb. Einziger Ausreisser: 2026 (nur 20 Trades, halbes Jahr, PF 0.68).",
        icon=":material/insights:",
    )
    st.warning(
        "**Kombiniert (ADX + Trend-Bias + Fuellverzoegerung + Silber-Alignment) sinkt die "
        "Stichprobe auf 310 Trades** - immer noch eine solide Gesamtaussage, aber der "
        "duennste Schnitt aller vier Filter zusammen. Standardmaessig **AN**, da Sharpe, "
        "Win-Rate UND Max Drawdown gleichzeitig besser werden und Walk-Forward + Ausreisser-"
        "Check beide bestehen - wer absolute Trade-Zahl priorisiert, kann ihn im "
        "Sidebar-Toggle deaktivieren.",
        icon=":material/warning:",
    )
    st.caption(
        "Reproduzierbar ueber `asian_range_breakout/filters.py::attach_silver_alignment`/"
        "`apply_silver_alignment_filter` + `scripts/research_gold_silver_leadlag_filter.py`. "
        "Datenquelle: Dukascopy XAGUSD ueber `combined_strategy.data.fetch_timeframe` (bereits "
        "in diesem Repo genutzt), keine neue Datenanbindung noetig."
    )

    st.markdown("### Liquiditaets-Filter (Corwin-Schultz) -- getestet, jetzt Standard (2026-08-11)")
    st.success(
        "**Staerkster bisher gefundener Filter fuer diese Strategie.** Aus dem Bond-Yield-"
        "Spread-Indikator-Projekt (siehe \"Strategie Bestandteile\" -> \"FX-Liquiditaetsfilter\"): "
        "Corwin & Schultz (2012) schaetzen den Bid-Ask-Spread allein aus taeglichem High/Low - "
        "hier auf Golds eigenen Kursen. Hypothese: Breakouts an Tagen mit ungewoehnlich schlechter "
        "Liquiditaet (weiter geschaetzter Spread) sind unzuverlaessiger. **Getestet gegen den "
        "vollen Stack (ADX+Trend+Delay+Silber) mit demselben zweistufigen Rigor wie die anderen "
        "vier Filter:**",
        icon=":material/check_circle:",
    )

    silver_filtered = apply_silver_alignment_filter(
        trend_delay_trades, daily_close_silver_writeup, window=SILVER_ALIGNMENT_WINDOW
    ).sort_values("entry_time").reset_index(drop=True)
    friction_writeup = load_gold_friction()
    liquidity_tagged = attach_gold_liquidity(silver_filtered, friction_writeup)

    col_lsweep, col_lmetrics = st.columns(2)
    with col_lsweep:
        with st.container(border=True):
            st.markdown("**Structure-Preserving-Randomisierung (Patel et al.)**")
            st.caption(
                "Gegen den vollen Produktions-Stack getestet (n=310): p=**0.000** unter Rotation "
                "UND p=**0.001** unter Run-Permutation (je 1000 Shuffles) - das tatsaechliche "
                "Behalten/Verwerfen-Muster schlaegt praktisch jede gleich-foermige Zufalls-"
                "Platzierung mit demselben Fussabdruck. Deutlich staerker als die p≈0.16-0.23 "
                "der schwaechsten beiden bestehenden Filter (Trend-Bias, Verzoegerung)."
            )
    with col_lmetrics:
        with st.container(border=True):
            st.markdown("**Kennzahlen: +Liquiditaetsfilter (kausale Schwelle)**")
            liq_final = apply_gold_liquidity_filter_causal(
                silver_filtered, friction_writeup, quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS
            )
            liq_final_stats = trade_stats(liq_final)
            silver_stats_ref = trade_stats(silver_filtered)
            st.caption(
                f"Profit Factor {silver_stats_ref['profit_factor']:.3f} -> "
                f"**{liq_final_stats['profit_factor']:.3f}**, Win-Rate "
                f"{silver_stats_ref['win_rate']:.1%} -> **{liq_final_stats['win_rate']:.1%}**. "
                f"Trades {silver_stats_ref['n_trades']} -> {liq_final_stats['n_trades']}. "
                "Kausale (Lookahead-freie) rollierende Zweidrittel-Schwelle - nicht die volle-"
                "Stichprobe-Schwelle des reinen Signifikanztests oben, sondern das, was live "
                "tatsaechlich handelbar gewesen waere."
            )

    st.markdown("**Walk-Forward-Validierung (Expanding-Window, gleiche Methodik wie die anderen vier Filter)**")
    liquidity_wf_table = run_liquidity_filter_walk_forward(
        liquidity_tagged, start_test_year=2019, end_test_year=2026, min_train_trades=100
    )
    st.dataframe(
        liquidity_wf_table,
        hide_index=True,
        column_config={
            "test_year": st.column_config.NumberColumn("Testjahr"),
            "train_n_trades": st.column_config.NumberColumn("Trainings-Trades"),
            "filter_confirmed_on_train": st.column_config.CheckboxColumn("Filter bestätigt (nur Training)"),
            "n_trades_unfiltered": st.column_config.NumberColumn("Trades ungefiltert"),
            "pf_unfiltered": st.column_config.NumberColumn("PF ungefiltert", format="%.3f"),
            "n_trades_walkforward": st.column_config.NumberColumn("Trades Walk-Forward"),
            "pf_walkforward": st.column_config.NumberColumn("PF Walk-Forward", format="%.3f"),
            "win_rate_walkforward": st.column_config.NumberColumn("Win-Rate WF", format="%.1f%%"),
        },
    )
    n_confirmed_liq = int(liquidity_wf_table["filter_confirmed_on_train"].sum())
    st.info(
        f"Filter in **{n_confirmed_liq}/{len(liquidity_wf_table)}** Testjahren (2021-2026, "
        "2019/2020 noch zu wenig Trainingsdaten) bereits aus den Trainingsdaten allein "
        "bestaetigt - jedes einzelne Jahr, in dem eine Entscheidung ueberhaupt moeglich war. "
        f"Mittlerer PF/Jahr: {liquidity_wf_table['pf_unfiltered'].mean():.3f} ungefiltert -> "
        f"{liquidity_wf_table['pf_walkforward'].mean():.3f} walk-forward.",
        icon=":material/insights:",
    )
    st.warning(
        "**Kombiniert (ADX+Trend+Delay+Silber+Liquiditaet) sinkt die Stichprobe weiter** - "
        "der duennste Schnitt aller fuenf Filter zusammen. Standardmaessig **AN**, da es der "
        "am staerksten validierte Filter dieser gesamten Strategie ist (staerker als 2 der "
        "4 vorherigen). FOMC-3-Tage-Fenster wurde im selben Projekt ebenfalls getestet und "
        "**verworfen** (p=0.42-0.62, kein Edge) - nicht implementiert.",
        icon=":material/warning:",
    )
    st.caption(
        "Reproduzierbar ueber `asian_range_breakout/filters.py::attach_gold_liquidity`/"
        "`apply_gold_liquidity_filter_causal` + `walkforward.py::run_liquidity_filter_walk_forward` + "
        "`scripts/research_gold_liquidity_event_filters.py`. Datenquelle: "
        "`bond_yield_indicator/friction.py` (Corwin-Schultz auf Golds Dukascopy-D1-Kursen, "
        "wiederverwendet aus dem Bond-Yield-Spread-Indikator-Projekt, keine neue Datenanbindung "
        "noetig)."
    )

    st.markdown("### Execution-Overlay (Fast-Alpha-Timing) -- getestet, jetzt Standard (2026-08-09)")
    st.success(
        "**Timing-Filter, kein Signal-Filter.** Konzept aus Zarattini & Pagani (2026), "
        "\"Improving Performance with Fast Alphas\" (siehe eigene Seite \"Execution-Overlay\" "
        "unter \"Strategie Bestandteile\"): ein Signal, das fuer sich allein nicht profitabel "
        "genug fuer die Kosten ist, kann trotzdem echte kurzfristige Richtungsinformation "
        "enthalten - nutzbar rein fuer den FUELLZEITPUNKT einer bereits entschiedenen Order, "
        "nicht fuer die Entscheidung selbst. Uebersetzt auf die ASB: **welches Fenster ausbricht "
        "und in welche Richtung bleibt exakt wie bisher** - nur WANN gefuellt wird, aendert sich. "
        "Statt die resting Buy-/Sell-Stop-Order sofort bei Beruehrung des Levels zu fuellen, "
        "wartet sie auf die erste M15-Kerze, die GEGEN die Ausbruchsrichtung schliesst (die "
        "grobkoernige Entsprechung des Papers eigenem 5-Minuten-\"Streak-Reversal\"-Signals - "
        "feinere Aufloesung als M15 steht hier nicht zur Verfuegung), und fuellt dort zum "
        "Schlusskurs. Kommt keine solche Kerze vor dem Sessionende, verfaellt der Trade "
        "komplett (kein Fallback auf die alte Wick-Fuellung).",
        icon=":material/check_circle:",
    )

    col_ov1, col_ov2 = st.columns(2)
    with col_ov1:
        with st.container(border=True):
            st.markdown("**Rohes Signal (ungefiltert) - reine Timing-Wirkung**")
            st.caption(
                "Wick PF 1.087 (n=2700) vs. Overlay PF 1.016 (n=2694, 99.8% Fuellrate, "
                "Median-Wartezeit 1 Bar/~15 Min.) - der Overlay allein hilft dem rohen Signal "
                "NICHT. Die Wirkung entsteht erst in Kombination mit dem Produktions-Filterstack."
            )
    with col_ov2:
        with st.container(border=True):
            st.markdown("**Voller Filterstack (ADX+Trend+Delay+Silber+Liquiditaet)**")
            st.caption(
                "Aktualisiert 2026-08-11 nach Aufnahme des Liquiditaetsfilters (vorher PF 1.426 "
                "auf n=310, s. Liquiditaets-Abschnitt oben). Wick (heutige Produktion) PF "
                "**1.999** (n=187) vs. Overlay+Stack PF **2.310** (n=110, WR=53.6%) - weiterhin "
                "deutliche Verbesserung, auf kleinerer Stichprobe (weniger Fuellungen, 5 statt 4 "
                "Filter). IS PF 1.734 (n=51) vs. OOS PF 2.820 (n=59) - OOS weiterhin staerker als "
                "IS. Ausreisser-Check: PF 2.310 -> 2.160 ohne besten Trade (robust)."
            )

    st.markdown("**Beispiel-Trade: derselbe Ausbruch, Wick- vs. Overlay-Fuellung**")
    st.caption(
        "Graue Box = Range, gestrichelte Linien = Buy-/Sell-Stop-Level, Dreieck = tatsaechlicher "
        "Entry (Farbe = Richtung), Raute = Exit (Farbe = Exit-Grund). Wick wuerde direkt an der "
        "gestrichelten Linie fuellen - hier fuellt der Overlay erst einige Kerzen spaeter, nach "
        "dem ersten Gegenschlag."
    )
    price_full_ov = load_data()
    example_overlay_trades = load_trades(1.0, None, None, 0.30, 0.10, use_overlay=True)
    if not example_overlay_trades.empty:
        has_multi_bar_wait = (example_overlay_trades["wait_bars"] >= 2).any()
        example_trade = (
            example_overlay_trades[example_overlay_trades["wait_bars"] >= 2].iloc[-1:]
            if has_multi_bar_wait
            else example_overlay_trades.iloc[-1:]
        )
        ex_start = example_trade["window_start"].iloc[0] - timedelta(hours=6)
        ex_end = example_trade["exit_time"].iloc[0] + timedelta(hours=6)
        price_window_ex = price_full_ov.loc[ex_start:ex_end]
        st.altair_chart(build_entry_chart(price_window_ex, example_trade), width="stretch")
        st.caption(
            f"Fenster {example_trade['window_start'].iloc[0]:%Y-%m-%d %H:%M} NY, Ausbruch-Trigger "
            f"{example_trade['trigger_time'].iloc[0]:%H:%M}, tatsaechlicher Entry "
            f"{example_trade['entry_time'].iloc[0]:%H:%M} ({int(example_trade['wait_bars'].iloc[0])} "
            f"Bar(s)/{int(example_trade['wait_bars'].iloc[0]) * 15} Min. spaeter) - "
            f"Exit-Grund: {example_trade['exit_reason'].iloc[0]}."
        )
    else:
        st.info("Keine Overlay-Trades fuer die Standardparameter gefunden.", icon=":material/info:")

    st.info(
        "Walk-Forward-Validierung (waehlt Wick oder Overlay pro Jahr NUR anhand vorheriger "
        "Jahre) und die daraus abgeleitete Risikosteuerung fuer Fremdkapitalkonten stehen im "
        "Tab **Walk-Forward & Equity**.",
        icon=":material/insights:",
    )
    st.warning(
        "**Standardmaessig AN** (Sidebar-Toggle), da Walk-Forward das Overlay in 6 von 8 "
        "Testjahren waehlt und nur die datenaermsten fruehen Jahre (2019/2020) bei Wick "
        "bleiben. Trade-off: weniger absolute Trade-Zahl (manche Fenster liefern ohne "
        "Pullback vor Sessionende gar keinen Trade mehr) - wer maximale Trade-Frequenz "
        "priorisiert, kann im Sidebar-Toggle auf Wick zurueckschalten.",
        icon=":material/warning:",
    )
    st.caption(
        "Reproduzierbar ueber `asian_range_breakout/execution_overlay.py::simulate_asian_breakout_overlay` "
        "+ `scripts/research_gold_execution_overlay.py` (Screening) + "
        "`scripts/research_gold_overlay_walkforward_risk.py` (Walk-Forward + Risikosizing). "
        "Der Overlay ist bewusst konservativ umgesetzt (M15-Bar-Close als Pullback-Proxy, kein "
        "separates Fast-Alpha-Signal aus Tick-Daten) - eine Verschlechterung koennte an der "
        "groben Aufloesung liegen, nicht zwingend am Konzept selbst."
    )

    st.markdown("### Drei weitere Kandidaten -- getestet, keiner uebernommen (2026-08-09)")
    st.caption(
        "Alle drei auf der aktuellen Produktionskonfiguration getestet (Overlay + ADX + Trend + "
        "Delay + Silber). Bucket-Vergleich + IS/OOS + Ausreisser-Check, bei Jump-Activity "
        "zusaetzlich ein volles Walk-Forward (gleiche Methodik wie beim ADX-Filter oben)."
    )
    st.warning(
        "**Cross-Pair-Confirmation** (wiederverwendet aus `strategy/cls_advanced.py`, der "
        "CLS-Advanced-Seite unter \"Strategie Bestandteile\" - dort real, aber nicht selbst "
        "monetarisierbar): war der VORTAG's 06:00-09:00-Move der 6 FX-Majors ein breiter, "
        "mehrheitlich bestaetigter Dollar-Move oder ein isolierter Einzelpaar-Move? Angehaengt "
        "an Golds eigene Trades (kein Lookahead, nur der bereits geschlossene Vortag). Ergebnis: "
        "**broad**-Tage PF 2.412 (n=116, robust auch ohne besten Trade: 2.292), **isolated**-Tage "
        "PF nur 0.611 (n=19) - kollabiert ohne besten Trade auf 0.389. Richtung stimmt, aber "
        "die Bucket ist mit nur 19 Trades (10.7% der Stichprobe) zu duenn fuer echtes Vertrauen - "
        "**nicht uebernommen**, aber ein Kandidat, den man mit mehr Jahren/Daten nochmal pruefen "
        "koennte.",
        icon=":material/warning:",
    )
    st.warning(
        "**Jump-Activity** (generische Bipower-Variation-Sprungquote, RJ=(RV-BV)/RV - **keine** "
        "Nachbildung von \"Hizmeri et al.\", das Paper selbst liegt hier nicht vor, sondern die "
        "Standard-Barndorff-Nielsen-&-Shephard-Zerlegung mit demselben Zweck): war der Vortag "
        "von wenigen grossen Spruengen dominiert (hohe Sprungquote) statt glatter Diffusion? Ein "
        "erster naiver Bucket-Vergleich sah stark aus (Tertile: PF 2.71 / 2.91 / **1.02** fuer "
        "hohe Sprungquote), **haelt aber dem sauberen No-Lookahead-Walk-Forward NICHT stand**: "
        "nur 5/8 Testjahre bestaetigen den Filter beim Training, davon nur 4/8 mit PF>1.0 im "
        "Test - 2021 etwa wird auf Trainingsdaten bestaetigt, kollabiert dann aber selbst im Test "
        "(PF 2.44 ungefiltert -> 0.71 gefiltert). Ein statischer Full-Sample-Filter macht die "
        "Produktionsmetrik sogar **schlechter** (PF 1.804 -> 1.735). Mitursache: der erste, "
        "schnelle Screening-Lauf hat den Vortag ueber exaktes Kalenderdatum gesucht statt (wie "
        "ueberall sonst in diesem Repo, `filters.py::_attach_prior_day_series`) den letzten "
        "echten Handelstag vorwaerts zu tragen - dadurch fielen alle Montags-Breakouts (Vortag "
        "= Sonntag, keine Daten) unbemerkt ganz aus der Stichprobe. Reproduzierbar ueber "
        "`asian_range_breakout/jump_activity.py` + `filters.py::attach_jump_activity` + "
        "`walkforward.py::run_jump_activity_walk_forward` + "
        "`scripts/research_gold_asb_new_filters.py` - **nicht uebernommen**.",
        icon=":material/warning:",
    )
    st.warning(
        "**LVN/HVN-Volumenprofil** (wiederverwendet aus `auction_playbook/indicators.py::"
        "volume_profile`, Dukascopys eigenes Tick-Volumen als Proxy, kein echter Orderflow - "
        "gleicher Vorbehalt wie beim Auction Playbook selbst): liegt der gerade gebrochene "
        "Level (Fenster-eigenes Volumenprofil, kein Lookahead) neben einem duennen (LVN) oder "
        "dicht gehandelten (HVN) Bereich? Ergebnis: **LVN** PF 2.032 (n=93, ohne besten Trade "
        "1.886) vs. **Normal** PF 1.490 (n=82, ohne besten Trade 1.388) - Richtung passt zur "
        "Hypothese (duenner Bereich = weniger Widerstand), aber der Effekt ist deutlich "
        "schwaecher als bei den anderen beiden Kandidaten, und die dritte Kategorie **HVN** ist "
        "mit nur 3 Trades praktisch unbrauchbar (am Fenster-Rand ist eine dichte Kongestionszone "
        "strukturell selten). Deckt sich mit dem eigenen \"kein robuster Edge\"-Befund des "
        "Auction Playbook fuer dieselbe Volumenprofil-Methode - **nicht uebernommen**.",
        icon=":material/warning:",
    )
    st.caption(
        "Alle drei Kandidaten stammten aus einer Bestandsaufnahme offener Ideen aus einer "
        "frueheren Session (cls_advanced-Wiederverwendung, Auction-Playbook-Wiederverwendung, "
        "generische Sprungquote statt einer nicht verfuegbaren Paper-Quelle) - konsequent "
        "gegengeprueft statt uebernommen, weil keiner den etablierten Massstab (robust ueber "
        "Ausreisser-Check UND Walk-Forward) erreicht hat."
    )

# =============================================================================
# Tab: Backtest
# =============================================================================
def _render_tab_backtest():
    st.markdown("## :material/wb_twilight: XAUUSD -- interaktiver Backtest")

    trades = load_trades(stop_frac, tp_r_mult, be_trigger_r, spread_price, slippage_price, use_overlay_entry)
    if use_adx_filter:
        trades = apply_adx_filter(trades, adx_min=15)
    if use_trend_filter:
        trades = apply_trend_bias_filter(trades, load_daily_close(), sma_window=TREND_SMA_WINDOW)
    if use_delay_filter:
        trades = apply_entry_delay_filter(trades, max_delay_bars=3)
    if use_silver_filter:
        trades = apply_silver_alignment_filter(trades, load_daily_close_silver(), window=SILVER_ALIGNMENT_WINDOW)
    if use_liquidity_filter:
        trades = apply_gold_liquidity_filter_causal(
            trades, load_gold_friction(), quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS
        )
    df = load_data()
    stats = summarize(trades, df.index)

    with st.container(horizontal=True):
        st.metric("Trades", stats["n_trades"], border=True)
        st.metric("Win-Rate", f"{stats['win_rate']:.1%}" if stats["n_trades"] else "–", border=True)
        st.metric("Profit Factor", f"{stats['profit_factor']:.2f}" if stats["n_trades"] else "–", border=True)
        st.metric("Sharpe", f"{stats['sharpe']:.2f}" if stats["n_trades"] else "–", border=True)
        st.metric("Max Drawdown", f"{stats['max_drawdown']:.1%}" if stats["n_trades"] else "–", border=True)

    st.space("medium")

    if not trades.empty:
        equity = (1 + trades.sort_values("exit_time")["return_pct"]).cumprod()
        equity.index = trades.sort_values("exit_time")["exit_time"]
        with st.container(border=True):
            st.markdown("**Equity-Kurve (pro Trade, nicht kalendertäglich)**")
            st.line_chart(equity)

        st.space("medium")

        yearly = trades.copy()
        yearly["year"] = yearly["entry_time"].dt.year
        yearly_stats = yearly.groupby("year").apply(
            lambda g: pd.Series(
                {
                    "n_trades": len(g),
                    "win_rate": (g["return_pct"] > 0).mean(),
                    "profit_factor": trade_stats(g)["profit_factor"],
                    "total_return_pct": g["return_pct"].sum(),
                }
            ),
            include_groups=False,
        )
        with st.container(border=True):
            st.markdown("**Jahresaufschlüsselung**")
            st.dataframe(
                yearly_stats,
                column_config={
                    "n_trades": st.column_config.NumberColumn("Trades"),
                    "win_rate": st.column_config.NumberColumn("Win-Rate", format="%.1f%%"),
                    "profit_factor": st.column_config.NumberColumn("Profit Factor", format="%.2f"),
                    "total_return_pct": st.column_config.NumberColumn("Summe Return%", format="%.2f%%"),
                },
            )

        st.space("medium")

        with st.container(border=True):
            st.markdown("**Trade-Log (letzte 200)**")
            display = trades.sort_values("entry_time", ascending=False).head(200)
            st.dataframe(
                display,
                hide_index=True,
                column_config={
                    "entry_time": st.column_config.DatetimeColumn("Entry"),
                    "exit_time": st.column_config.DatetimeColumn("Exit"),
                    "entry_price": st.column_config.NumberColumn("Entry-Preis", format="%.2f"),
                    "exit_price": st.column_config.NumberColumn("Exit-Preis", format="%.2f"),
                    "sl": st.column_config.NumberColumn("SL", format="%.2f"),
                    "return_pct": st.column_config.NumberColumn("Return", format="%.2f%%"),
                },
            )
    else:
        st.info("Keine Trades für diese Parameterkombination.", icon=":material/info:")

# =============================================================================
# Tab: Live Entry-Signal
# =============================================================================
def _render_tab_live():
    st.markdown("## :material/candlestick_chart: Live Entry-Signal")
    st.caption(
        "Zeigt visuell, wo die Strategie ein-/ausgestiegen wäre - Range-Box (grau), "
        "Buy-Stop/Sell-Stop-Linien (gestrichelt), Entry (Dreieck, Farbe = Richtung), "
        "Exit (Raute, Farbe = Exit-Grund). Datenquelle: **yfinance GC=F (Gold-Future)**, "
        "NICHT Dukascopy wie im Backtest - Dukascopys eigene Daten liefen beim Test "
        "(2026-08-05) selbst frisch abgerufen >10h hinter der Realzeit her, ein Anbieter-"
        "Limit. GC=F ist der Future, nicht Spot-XAUUSD (kleine Preisabweichung durch "
        "Cost-of-Carry möglich) - trotzdem kein Live-MT5-Zugriff auf ein echtes Konto."
    )
    st.page_link(
        "app_pages/gold_asb_live_log.py",
        label="Zum Gold ASB Live Log (echter Bot-State + TradingView-Chart mit Entry/SL)",
        icon=":material/rss_feed:",
    )

    latest_df = load_live_data()
    setup = get_latest_setup(latest_df, stop_frac=stop_frac)

    if setup is None:
        st.warning("Kein abgeschlossenes Range-Fenster in den geladenen Daten gefunden.", icon=":material/warning:")
    else:
        status_icon = {
            "wartet auf Füllung": ":material/hourglass_empty:",
            "gefüllt (Long)": ":material/trending_up:",
            "gefüllt (Short)": ":material/trending_down:",
            "abgelaufen (kein Fill)": ":material/block:",
        }.get(setup["status"], ":material/info:")

        st.info(
            f"**Letztes Range-Fenster**: {setup['window_start']:%Y-%m-%d %H:%M} - "
            f"{setup['window_end']:%H:%M} NY | **Range**: {setup['range_low']:.2f} - "
            f"{setup['range_high']:.2f} (Breite {setup['range_high']-setup['range_low']:.2f}) | "
            f"**Stop-Distanz**: {setup['stop_distance']:.2f} | **Status**: {setup['status']}"
            + (f" @ {setup['entry_price']:.2f}" if setup["entry_price"] else ""),
            icon=status_icon,
        )
        st.caption(
            f"Letzter geladener Kurs: {setup['last_price']:.2f} um {setup['last_bar_time']:%Y-%m-%d %H:%M} NY "
            f"(yfinance GC=F, üblicherweise ~15-20 Min. Verzug - kein Live-Tick-Feed)."
        )

    st.space("medium")
    n_days = st.slider("Zeitraum für den Chart (Tage zurück)", 5, 120, 30, 5)
    window_end_ts = latest_df.index.max()
    window_start_ts = window_end_ts - timedelta(days=n_days)
    price_window = latest_df.loc[window_start_ts:window_end_ts]

    all_trades = load_trades(stop_frac, tp_r_mult, be_trigger_r, spread_price, slippage_price, use_overlay_entry)
    if use_adx_filter:
        all_trades = apply_adx_filter(all_trades, adx_min=15)
    if use_trend_filter:
        all_trades = apply_trend_bias_filter(all_trades, load_daily_close(), sma_window=TREND_SMA_WINDOW)
    if use_delay_filter:
        all_trades = apply_entry_delay_filter(all_trades, max_delay_bars=3)
    if use_silver_filter:
        all_trades = apply_silver_alignment_filter(all_trades, load_daily_close_silver(), window=SILVER_ALIGNMENT_WINDOW)
    if use_liquidity_filter:
        all_trades = apply_gold_liquidity_filter_causal(
            all_trades, load_gold_friction(), quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS
        )
    trades_window = all_trades[
        (all_trades["entry_time"] >= window_start_ts) & (all_trades["entry_time"] <= window_end_ts)
    ]

    st.altair_chart(build_entry_chart(price_window, trades_window), width="stretch")
    st.caption(f"{len(trades_window)} Trade(s) im gezeigten Zeitraum ({n_days} Tage), Filter/Parameter wie in der Sidebar.")

# =============================================================================
# Tab: Walk-Forward & Equity
# =============================================================================
def _render_tab_walkforward():
    st.markdown("## :material/timeline: Walk-Forward-Test & Equity-Simulation")

    st.markdown("### Walk-Forward-Validierung des ADX-Filters")
    st.caption(
        "Expanding-Window: für jedes Testjahr wird NUR mit Trades VOR diesem Jahr geprüft, ob "
        "ADX<15 weiterhin der schwächste Bucket ist (mind. 30 Trades je Bucket). Nur wenn das "
        "Training das bestätigt, wird der Filter in diesem Jahr angewendet - kein Blick auf die "
        "Zukunft, keine Rückwirkung aus dem Gesamtsample."
    )

    wf_base_trades = load_trades(1.0, None, None, 0.30, 0.10)
    wf_table = run_walk_forward(wf_base_trades, start_test_year=2019, end_test_year=2026)

    st.dataframe(
        wf_table,
        hide_index=True,
        column_config={
            "test_year": st.column_config.NumberColumn("Testjahr"),
            "train_n_trades": st.column_config.NumberColumn("Trainings-Trades"),
            "filter_confirmed_on_train": st.column_config.CheckboxColumn("Filter bestätigt (nur Training)"),
            "n_trades_unfiltered": st.column_config.NumberColumn("Trades ungefiltert"),
            "pf_unfiltered": st.column_config.NumberColumn("PF ungefiltert", format="%.3f"),
            "n_trades_walkforward": st.column_config.NumberColumn("Trades Walk-Forward"),
            "pf_walkforward": st.column_config.NumberColumn("PF Walk-Forward", format="%.3f"),
            "win_rate_walkforward": st.column_config.NumberColumn("Win-Rate WF", format="%.1f%%"),
        },
    )

    n_positive_wf = (wf_table["pf_walkforward"] > 1.0).sum()
    st.info(
        f"**{n_positive_wf} von {len(wf_table)} Testjahren** mit PF>1.0 im Walk-Forward "
        "(2019/2020: Filter kann noch nicht bestätigt werden, zu wenig Trainingsdaten - erst "
        "ab 2021 greift er durchgehend). 2023 bleibt auch mit bestätigtem Filter schwach "
        "(PF 0.93) - eine echte Out-of-Sample-Delle, die der Filter nicht auffängt. Insgesamt "
        "stützt das die Robustheit des Filters, ist aber kein Beweis, dass er jedes Jahr hilft.",
        icon=":material/insights:",
    )

    st.markdown("### Walk-Forward-Validierung: Wick vs. Execution-Overlay")
    st.caption(
        "Gleiche Expanding-Window-Logik, diesmal nicht für einen Filter-Schwellenwert sondern "
        "für die Wahl der Füllregel: pro Testjahr wird NUR anhand des Profit Factor auf Jahren "
        "VOR diesem Jahr entschieden, ob Wick oder Execution-Overlay eingesetzt wird - beide "
        "Varianten laufen durch denselben Produktions-Filterstack (ADX+Trend+Delay+Silber+Liquidität)."
    )

    def _apply_production_stack(base_trades: pd.DataFrame) -> pd.DataFrame:
        t = apply_adx_filter(base_trades, adx_min=15)
        t = apply_trend_bias_filter(t, load_daily_close(), sma_window=TREND_SMA_WINDOW)
        t = apply_entry_delay_filter(t, max_delay_bars=3)
        t = apply_silver_alignment_filter(t, load_daily_close_silver(), window=SILVER_ALIGNMENT_WINDOW)
        t = apply_gold_liquidity_filter_causal(
            t, load_gold_friction(), quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS
        )
        return t.sort_values("entry_time").reset_index(drop=True)

    wf_wick_stack = _apply_production_stack(load_trades(1.0, None, None, 0.30, 0.10, use_overlay=False))
    wf_overlay_stack = _apply_production_stack(load_trades(1.0, None, None, 0.30, 0.10, use_overlay=True))

    mode_summary, wf_mode_trades = run_execution_mode_walk_forward(
        {"wick": wf_wick_stack, "overlay": wf_overlay_stack},
        default_mode="wick", start_test_year=2019, end_test_year=2026, min_train_trades=30,
    )
    st.dataframe(
        mode_summary,
        hide_index=True,
        column_config={
            "test_year": st.column_config.NumberColumn("Testjahr"),
            "chosen_mode": st.column_config.TextColumn("Gewählter Modus"),
            "train_pf": st.column_config.NumberColumn("Trainings-PF", format="%.3f"),
            "n_trades_default": st.column_config.NumberColumn("Trades (Wick-Default)"),
            "pf_default": st.column_config.NumberColumn("PF (Wick-Default)", format="%.3f"),
            "n_trades_walkforward": st.column_config.NumberColumn("Trades Walk-Forward"),
            "pf_walkforward": st.column_config.NumberColumn("PF Walk-Forward", format="%.3f"),
        },
    )
    n_overlay_years = int((mode_summary["chosen_mode"] == "overlay").sum())
    st.info(
        f"Overlay wird in **{n_overlay_years}/{len(mode_summary)}** Testjahren gewählt (train-only, "
        "kein Lookahead) - nur 2019/2020 bleiben bei Wick, weil dort noch zu wenige Trainings-"
        "Trades vorliegen (< 30). Bestätigt, dass der Overlay-Vorteil kein reines "
        "Gesamtsample-Artefakt ist. Diese gestitchte Walk-Forward-Sequenz (`wf_mode_trades`) ist "
        "die Grundlage für den Risikomanagement-Abschnitt weiter unten.",
        icon=":material/insights:",
    )

    st.markdown("### Equity-Simulation")
    st.caption(
        "Fixes Bruchteil-Risiko pro Trade (wie beim OU-Modell-Bot: risk_amount = Equity x "
        "risk_pct), R-Multiple-basiert (nicht der rohe Kurs-Return) - eine Position, die mehr "
        "riskiert hat (breitere Nacht-Range), gewinnt/verliert dadurch nicht automatisch mehr "
        "in Dollar."
    )
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        starting_equity = st.number_input("Start-Kapital (USD)", 1_000.0, 10_000_000.0, 100_000.0, 1_000.0)
    with col_eq2:
        risk_pct_input = st.slider(
            "Risiko pro Trade (%)", 0.1, 3.0, 1.0, 0.1,
            help="Standardwert 1.0% = empfohlene Obergrenze für ein TTP-Fremdkapitalkonto "
            "(3% Tages-/7% Gesamt-Drawdown-Limit) - siehe Risikomanagement-Abschnitt unten. "
            "Ungedeckeltes Fixed-Fractional-Sizing (kein 100%-Notional-Deckel), setzt "
            "entsprechenden Hebel auf Gold voraus.",
        ) / 100

    eq_trades = load_trades(stop_frac, tp_r_mult, be_trigger_r, spread_price, slippage_price, use_overlay_entry)
    if use_adx_filter:
        eq_trades = apply_adx_filter(eq_trades, adx_min=15)
    if use_trend_filter:
        eq_trades = apply_trend_bias_filter(eq_trades, load_daily_close(), sma_window=TREND_SMA_WINDOW)
    if use_delay_filter:
        eq_trades = apply_entry_delay_filter(eq_trades, max_delay_bars=3)
    if use_silver_filter:
        eq_trades = apply_silver_alignment_filter(eq_trades, load_daily_close_silver(), window=SILVER_ALIGNMENT_WINDOW)
    if use_liquidity_filter:
        eq_trades = apply_gold_liquidity_filter_causal(
            eq_trades, load_gold_friction(), quantile=LIQUIDITY_QUANTILE, min_periods=LIQUIDITY_MIN_PERIODS
        )
    equity_df = simulate_equity(eq_trades, starting_equity=starting_equity, risk_pct=risk_pct_input)

    if not equity_df.empty:
        running_max = equity_df["equity"].cummax()
        drawdown = (equity_df["equity"] - running_max) / running_max

        with st.container(horizontal=True):
            st.metric("End-Equity", f"${equity_df['equity'].iloc[-1]:,.0f}", border=True)
            st.metric(
                "Gesamtrendite",
                f"{(equity_df['equity'].iloc[-1] / starting_equity - 1):+.1%}",
                border=True,
            )
            st.metric("Max Drawdown", f"{drawdown.min():.1%}", border=True)
            st.metric(
                "Größter Einzel-Verlust",
                f"${equity_df['pnl_dollar'].min():,.0f}",
                border=True,
            )

        with st.container(border=True):
            st.markdown(f"**Equity-Kurve** (Start: ${starting_equity:,.0f}, {risk_pct_input:.1%} Risiko/Trade)")
            plot_df = equity_df.set_index("exit_time")["equity"]
            st.line_chart(plot_df)

        st.space("medium")

        st.markdown("### Monte-Carlo-Simulation (Trade-Sequence-Bootstrap)")
        n_sims = st.slider("Anzahl Simulationen", 500, 10000, 3000, 500)
        st.caption(
            f"Die {len(eq_trades)} historischen Trades (R-Multiples) werden zufällig mit "
            f"Zurücklegen neu gemischt - {n_sims} alternative Reihenfolgen derselben Trade-"
            "Ergebnisse. Zeigt, wie stark Drawdown/Rendite vom **Zufall der Reihenfolge** "
            "abhängen, nicht nur vom einen tatsächlich eingetretenen historischen Pfad. Ergänzt "
            "den Walk-Forward-Test (der prüft, ob die Kante über die Zeit stabil war), NICHT "
            "ersetzt ihn."
        )

        mc = run_monte_carlo(eq_trades, n_simulations=n_sims, starting_equity=starting_equity, risk_pct=risk_pct_input)
        mc_summary = summarize_monte_carlo(mc, starting_equity)

        with st.container(horizontal=True):
            st.metric("Median Rendite", f"{mc_summary['return_p50']:+.1%}", border=True)
            st.metric(
                "Rendite-Spanne (5.-95. Perzentil)",
                f"{mc_summary['return_p5']:+.0%} bis {mc_summary['return_p95']:+.0%}",
                border=True,
            )
            st.metric("Median Max-Drawdown", f"{mc_summary['dd_p50']:.1%}", border=True)
            st.metric("Schlechtester simulierter Drawdown", f"{mc_summary['dd_worst']:.1%}", border=True)

        col_mc1, col_mc2 = st.columns(2)
        with col_mc1:
            with st.container(border=True):
                st.markdown("**Rendite-Verteilung**")
                hist_ret = (
                    alt.Chart(mc)
                    .mark_bar(color="#1565c0")
                    .encode(
                        x=alt.X("total_return_pct:Q", bin=alt.Bin(maxbins=40), title="Gesamtrendite"),
                        y=alt.Y("count():Q", title="Anzahl Simulationen"),
                        tooltip=[alt.Tooltip("count():Q", title="Anzahl")],
                    )
                    .properties(height=280)
                )
                st.altair_chart(hist_ret, width="stretch")
        with col_mc2:
            with st.container(border=True):
                st.markdown("**Max-Drawdown-Verteilung**")
                hist_dd = (
                    alt.Chart(mc)
                    .mark_bar(color="#c62828")
                    .encode(
                        x=alt.X("max_drawdown:Q", bin=alt.Bin(maxbins=40), title="Max Drawdown"),
                        y=alt.Y("count():Q", title="Anzahl Simulationen"),
                        tooltip=[alt.Tooltip("count():Q", title="Anzahl")],
                    )
                    .properties(height=280)
                )
                st.altair_chart(hist_dd, width="stretch")

        st.warning(
            f"**Risiko-Kennzahlen aus {mc_summary['n_simulations']} Simulationen**: "
            f"P(Drawdown schlechter als -30%) = **{mc_summary['prob_dd_worse_30']:.1%}**, "
            f"P(schlechter als -40%) = {mc_summary['prob_dd_worse_40']:.1%}, "
            f"P(schlechter als -50%) = {mc_summary['prob_dd_worse_50']:.1%}. "
            f"P(Netto-Verlust nach {len(eq_trades)} Trades) = {mc_summary['prob_net_loss']:.1%}. "
            f"95. Perzentil der längsten Verlustserie: {mc_summary['streak_p95']:.0f} Trades in Folge. "
            f"**Der tatsächliche historische Max-Drawdown ({drawdown.min():.1%}) liegt UNTER dem "
            f"Median der Simulationen ({mc_summary['dd_p50']:.1%})** - die reale Historie war beim "
            f"Drawdown tendenziell eher günstig, nicht der typische Fall.",
            icon=":material/warning:",
        )

        st.markdown("**Wie lange dauert es statistisch bis +10% Gesamtrendite?**")
        st.caption(
            "Nicht die Rendite NACH fester Trade-Zahl (das macht die Simulation oben), sondern "
            "die umgekehrte Frage: wie viele Trades braucht dieselbe Bootstrap-Methode im "
            "Schnitt, BIS zum ersten Mal +10% erreicht sind - dann über die historische "
            "Trade-Frequenz in Kalenderzeit umgerechnet."
        )
        tt = simulate_time_to_target(
            eq_trades, target_return=0.10, n_simulations=n_sims, risk_pct=risk_pct_input, max_trades=400
        )
        reached = tt["trades_to_target"].dropna()
        years_span = (eq_trades["exit_time"].max() - eq_trades["exit_time"].min()).days / 365.25
        trades_per_year = len(eq_trades) / years_span if years_span > 0 else float("nan")
        if len(reached) and trades_per_year > 0:
            median_trades = reached.median()
            p25_trades = reached.quantile(0.25)
            p75_trades = reached.quantile(0.75)
            pct_reached = len(reached) / len(tt)
            with st.container(horizontal=True):
                st.metric("Median: Trades bis +10%", f"{median_trades:.0f}", border=True)
                st.metric("Median: Kalenderzeit bis +10%", f"~{median_trades / trades_per_year * 12:.0f} Monate", border=True)
                st.metric(
                    "Spanne (25.-75. Perzentil)",
                    f"{p25_trades / trades_per_year * 12:.0f}-{p75_trades / trades_per_year * 12:.0f} Monate",
                    border=True,
                )
                st.metric("Erreicht innerhalb 400 Trades", f"{pct_reached:.0%}", border=True)
            st.caption(
                f"Basierend auf {trades_per_year:.0f} Trades/Jahr im historischen Schnitt "
                f"({len(eq_trades)} Trades über {years_span:.1f} Jahre) bei {risk_pct_input:.1%} "
                "Risiko/Trade. Kalenderzeit ist eine Näherung über die durchschnittliche "
                "Trade-Frequenz (Trades sind nicht perfekt gleichmäßig übers Jahr verteilt, "
                "siehe Jahresaufschlüsselung im Backtest-Tab) - keine eigene Zeitachsen-"
                "Simulation."
            )
        else:
            st.info(
                f"In {n_sims} Simulationen wurde +10% innerhalb von 400 Trades in keinem Fall "
                "erreicht - bei diesem Risiko/Trade zu langsam für eine sinnvolle Aussage.",
                icon=":material/info:",
            )
    else:
        st.info("Keine Trades für diese Parameterkombination.", icon=":material/info:")

    st.markdown("### Risikomanagement für Fremdkapitalkonten (TTP: 3% Tages-/7% Gesamt-Drawdown)")
    st.caption(
        "Nutzt NICHT die Sidebar-Parameter, sondern die Walk-Forward-Sequenz von oben (Wick/"
        "Overlay je Jahr wie tatsächlich vorher entscheidbar gewesen wäre) mit echtem, "
        "ungedeckeltem Fixed-Fractional-Sizing (kein 100%-Notional-Deckel, setzt entsprechenden "
        "Hebel auf Gold voraus - üblich bei CFD-Fremdkapitalkonten, aber vor echtem Einsatz "
        "gegen die Margin-Regeln des jeweiligen Kontos zu prüfen)."
    )
    wf_sign = wf_mode_trades["direction"].map({"long": 1, "short": -1})
    wf_r_multiple = wf_sign * (wf_mode_trades["exit_price"] - wf_mode_trades["entry_price"]) / wf_mode_trades["stop_distance"]
    risk_trades = wf_mode_trades.copy()
    risk_trades["return_pct"] = wf_r_multiple * RECOMMENDED_RISK_PCT
    risk_index = load_data().index
    risk_stats = summarize(risk_trades, risk_index)
    daily_ret = trades_to_daily_returns(risk_trades, risk_index)
    worst_day = daily_ret.min()
    total_dd = max_drawdown(daily_ret)
    n_breach_daily = int((daily_ret < -TTP_MAX_DAILY_DD).sum())
    daily_ok = worst_day > -TTP_MAX_DAILY_DD
    total_ok = total_dd > -TTP_MAX_TOTAL_DD

    with st.container(horizontal=True):
        st.metric(f"CAGR ({RECOMMENDED_RISK_PCT:.0%} Risiko/Trade)", f"{risk_stats['cagr']:+.2%}", border=True)
        st.metric("Schlechtester Einzeltag", f"{worst_day:.2%}", border=True, help=f"TTP-Limit: -{TTP_MAX_DAILY_DD:.0%}")
        st.metric("Max. Gesamt-Drawdown", f"{total_dd:.2%}", border=True, help=f"TTP-Limit: -{TTP_MAX_TOTAL_DD:.0%}")
        st.metric("TTP-konform", "JA" if (daily_ok and total_ok) else "NEIN", border=True)

    if daily_ok and total_ok:
        st.success(
            f"Bei {RECOMMENDED_RISK_PCT:.0%} Risiko/Trade bleibt die Walk-Forward-Sequenz mit "
            f"deutlichem Abstand innerhalb beider TTP-Limits ({n_breach_daily} Tage mit "
            "Tages-Grenzbruch) - CAGR und Sicherheitsabstand zu den Limits gleichzeitig im "
            "Blick behalten, nicht nur die Renditeseite.",
            icon=":material/check_circle:",
        )
    else:
        st.error(
            f"Bei {RECOMMENDED_RISK_PCT:.0%} Risiko/Trade verletzt die Walk-Forward-Sequenz "
            "mindestens eines der beiden TTP-Limits - siehe Risiko-Sweep unten für eine "
            "konforme Alternative.",
            icon=":material/error:",
        )

    st.markdown("**Risiko-Sweep: wie viel Spielraum ist bis zu den TTP-Limits noch da?**")
    sweep_rows = []
    for rp in [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04]:
        rt = wf_mode_trades.copy()
        rt["return_pct"] = wf_r_multiple * rp
        s = summarize(rt, risk_index)
        d = trades_to_daily_returns(rt, risk_index)
        w = d.min()
        t = max_drawdown(d)
        sweep_rows.append(
            {
                "risiko_pct": rp,
                "cagr": s["cagr"],
                "sharpe": s["sharpe"],
                "gesamt_dd": t,
                "schlechtester_tag": w,
                "ttp_konform": (w > -TTP_MAX_DAILY_DD) and (t > -TTP_MAX_TOTAL_DD),
            }
        )
    sweep_df = pd.DataFrame(sweep_rows)
    st.dataframe(
        sweep_df,
        hide_index=True,
        column_config={
            "risiko_pct": st.column_config.NumberColumn("Risiko/Trade", format=".1%"),
            "cagr": st.column_config.NumberColumn("CAGR", format="+.2%"),
            "sharpe": st.column_config.NumberColumn("Sharpe", format="%.2f"),
            "gesamt_dd": st.column_config.NumberColumn("Gesamt-DD", format=".2%"),
            "schlechtester_tag": st.column_config.NumberColumn("Schlechtester Tag", format=".2%"),
            "ttp_konform": st.column_config.CheckboxColumn("TTP-konform"),
        },
    )
    st.warning(
        f"**Empfehlung: {RECOMMENDED_RISK_PCT:.0%} Risiko/Trade** als praktische Obergrenze - "
        "spürbar mehr CAGR als bei 0.5%, aber noch mit echtem Sicherheitsabstand zu beiden "
        "TTP-Limits. Ab 1.5% bricht der Gesamt-Drawdown das 7%-Limit. Der nötige Hebel steigt "
        "mit dem Risiko-Prozentsatz ungefähr proportional mit (die ASB hat eine sehr enge "
        "Stop-Distanz, im Schnitt ~0.45% des Einstiegspreises) - unbedingt gegen die "
        "tatsächlichen Hebel-/Margin-Spezifikationen des jeweiligen Kontos für Gold prüfen, "
        "bevor das eingesetzt wird.",
        icon=":material/warning:",
    )
    st.caption(
        "Reproduzierbar über `scripts/research_gold_overlay_walkforward_risk.py`. "
        "`stop_distance` (Range-Breite x stop_frac) definiert hier direkt die Risikodistanz - "
        "kein separater ATR-Stop nötig wie beim Gold-Bitcoin-Modell, die ASB hat schon einen "
        "echten Preis-Stop im Regelwerk."
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
# Sidebar widgets (stop_frac, use_adx_filter, ...) execute unconditionally above,
# outside any tab, so all four render functions can read them regardless of which
# tab is open.
for _tab, _render in [
    (tab_components, _render_tab_components),
    (tab_backtest, _render_tab_backtest),
    (tab_live, _render_tab_live),
    (tab_walkforward, _render_tab_walkforward),
]:
    if _tab.open:
        with _tab:
            _render()
