"""Landing page: overview and entry point for all strategy dashboards,
grouped into the same three top-level categories as app.py's navigation
(Live Logs / Backtests / Strategie Bestandteile) so the overview mirrors
the sidebar instead of listing every page flat."""

import streamlit as st

st.set_page_config(
    page_title="Trading-Strategie-Backtests",
    page_icon=":material/insights:",
    layout="wide",
)

"""
# :material/insights: Trading-Strategie-Backtests

Ein Ort für alle Backtests und Live-Logs: jede Karte unten ist eine
eigenständige, interaktive Strategie mit ihren eigenen Kennzahlen, Charts
und Parameter-Reglern. Alle sind ehrlich dokumentiert — inklusive der
Stellen, wo eine Strategie **keinen** robusten Edge zeigt.
"""

st.space("medium")

tab_live, tab_backtests, tab_components, tab_paper151, tab_new_papers = st.tabs(
    ["Live Logs", "Backtests", "Strategie Bestandteile", "151 Trading Strategies", "Neue Papers"]
)

# =============================================================================
# Live Logs
# =============================================================================
with tab_live:
    col_live, _spacer1, _spacer2 = st.columns(3, border=False)
    with col_live:
        with st.container(border=True):
            st.markdown("### :material/monitoring: OU-Modell — Live-Trading-Log")
            st.caption("Live-Konto, echtes Geld — read-only Log, kein Backtest")
            st.markdown(
                "Ein gehosteter OU-Modell-Signal-Scanner sendet Long-Setups automatisch "
                "an ein MT5-Live-Konto (Windows Task Scheduler, drei Scans/Tag). Diese "
                "Seite zeigt nur committete Tageswerte — kein Live-Zugriff auf MT5 von hier aus."
            )
            with st.container(border=True):
                st.markdown("**Status**")
                st.caption(
                    "Erster Live-Handelstag: 29.07.2026. Noch keine Auswertung/Verdict — "
                    "das kommt erst nach ~einem Monat gesammelter Tage, dieselbe Disziplin "
                    "wie bei jedem Backtest in diesem Projekt."
                )
            st.page_link("app_pages/ou_modell.py", label="Log öffnen", icon=":material/arrow_forward:")

# =============================================================================
# Backtests
# =============================================================================
with tab_backtests:
    col1, col2, col3 = st.columns(3, border=True)

    with col1:
        st.markdown("### :material/candlestick_chart: ADX-VWAP FX-Strategie")
        st.caption("Momentum Exhaustion & Fair Value Reversion (Working Paper)")
        st.markdown(
            "Intraday-Mean-Reversion an Vortages-Extremen, konditioniert auf "
            "VWAP-Abweichung und abflachenden ADX. 6 FX-Majors, wahlweise "
            "synthetische Daten (Pipeline-Validierung) oder 10 Jahre echte "
            "Dukascopy-Historie (M15)."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Auf 10 Jahren echten Daten kein robuster Edge auf allen 6 Paaren "
                "(Sharpe negativ). Ein verfeinerter Kandidat (H1, ADX-Deckel) sieht "
                "vielversprechender aus, beruht aber auf zu wenigen Trades, um "
                "belastbar zu sein."
            )
        st.page_link(
            "app_pages/adx_vwap.py", label="Dashboard öffnen", icon=":material/arrow_forward:"
        )

    with col2:
        st.markdown("### :material/show_chart: EMA S/R-Strategie")
        st.caption("Multi-Timeframe EMA-Rejection (EUR/USD, Gold, S&P 500)")
        st.markdown(
            "Weekly/Daily-EMA-Bias mit Rejection-Einstieg auf H4 (oder H12 bei "
            "den V2-Varianten). Drei Presets (Baseline, V2, V2-Trail) plus eine "
            "eigene In-Sample/Out-of-Sample-Grid-Suche. Live-Daten von Yahoo "
            "Finance."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Die In-Sample-optimierten Parameter brechen Out-of-Sample bei "
                "EUR/USD und S&P 500 deutlich ein — klassisches Overfitting bei "
                "begrenzter Historie. Auch der rekalibrierte Trailing-Stop (V2-Trail) "
                "zeigt keinen verlässlichen Vorteil gegenüber der einfacheren V2-Variante."
            )
        st.page_link("app_pages/ema_sr.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    with col3:
        st.markdown("### :material/merge: EMA kombiniert")
        st.caption("EMA S/R + 3 Ideen aus dem ADX-VWAP-Paper, 11 Instrumente")
        st.markdown(
            "Testet drei aus dem ADX-VWAP-Paper übertragene Ideen (VWAP-"
            "Überdehnungsfilter, Session-Extreme-Konfluenz, ADX-Erschöpfungs-Exit) "
            "einzeln und kombiniert. Echte Dukascopy-Historie (H4/D1/W1, ~10 Jahre) "
            "über die 6 FX-Paare plus Gold, Silber, S&P 500, Nasdaq-100 und Öl."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Keine der drei Erweiterungen überzeugt einzeln Out-of-Sample. "
                "Wichtiger: gegen Buy & Hold gerechnet liegt die Strategie auf "
                "Gold/Silber/Indizes 40-125 Prozentpunkte zurück — die hohe "
                "Rohrendite dort ist Beta (steigender Markt), nicht Skill."
            )
        st.page_link("app_pages/ema_combined.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    st.space("small")
    col4, col5, col6 = st.columns(3, border=True)

    with col4:
        st.markdown("### :material/schedule: CLS-Squeeze")
        st.caption("CLS-Settlement-Cutoff + VWAP-Reversion/Momentum, London-Open")
        st.markdown(
            "Testet die Praktiker-Hypothese, dass CLS-Settlement-Orderflow vor "
            "dem täglichen Cutoff (06:00-07:00 UTC) Preise mechanisch verdrängt, "
            "die dann Richtung VWAP zurückkehren (oder weiterlaufen) sollen, "
            "sobald London-Liquidität einsetzt. Reversion und Momentum wählbar."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Keine etablierte akademische Grundlage (anders als beim ADX-VWAP-"
                "Paper) — als Hypothese getestet. Reversion ist klar negativ "
                "(Sharpe -0.84 bei EUR/USD, 863 Trades). Momentum ist deutlich "
                "weniger schlecht (+0.21), aber kein robuster Edge."
            )
        st.page_link("app_pages/cls_squeeze.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    with col5:
        st.markdown("### :material/checklist: Checklist-Strategie")
        st.caption("4-Indikator-Setup (Nutzer-Idee), EUR/USD M15")
        st.markdown(
            "Nadaraya-Watson Envelope (Durchbruch) → RSI Multi-Length [LuxAlgo] "
            "(Bestätigung) → RSI(14)+SMA(14)-Kreuzung (Entry). ATR-Stop, festes "
            "1:2 R:R, Breakeven bei 1:1. Erlaubt mehrere gleichzeitig offene "
            "Positionen. Optionaler Regime-Filter (ADX/Volatilität)."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Baseline: 1265 Trades, Sharpe -0.14, Win-Rate 24% (bräuchte ~33% "
                "für Break-even). Regime-Filter \"ADX<25\" reduziert auf nur 30 "
                "Trades — sieht gepoolt gut aus, ist aber zu dünn, um zu vertrauen "
                "(Ø Jahres-Sharpe tatsächlich -0.09)."
            )
        st.page_link("app_pages/checklist.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    with col6:
        st.markdown("### :material/gavel: Auction Market Playbook")
        st.caption("Fabio Valentini Playbook: Trend Continuation + Mean Reversion, Krypto & Futures")
        st.markdown(
            "Eine vereinheitlichte State-Machine (Value-Area-Breakout haelt → Trend, "
            "scheitert → Reversion) auf zwei Datenwelten: BTCUSDT/ETHUSDT (Binance, "
            "echte Order-Flow-Aggression) und SP500/NASDAQ (Dukascopy E-mini-Proxy, "
            "die tatsaechlich im Paper genannten Futures-Assets, Aggression genaehert)."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Kein robuster Edge in keiner der drei getesteten Versionen. Median-R "
                "ist fast ueberall -1.00, Profit Factor >1.0 verschwindet meist beim "
                "Entfernen des einen besten Trades — Ausreisser-Effekt, keine Kante. "
                "Futures-Assets (paper-treuer) sind tendenziell noch fragiler als Krypto."
            )
        st.page_link("app_pages/auction_playbook.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    col7, _spacer3, _spacer4 = st.columns(3, border=True)
    with col7:
        st.markdown("### :material/wb_twilight: Gold Asian-Range Breakout")
        st.caption("XAUUSD: Range-Bruch der Asien-Session, geritten bis zum Zeit-Exit")
        st.markdown(
            "Asien-Range (21:00-01:00 NY) bilden, im Moment des Fenster-Schlusses "
            "Buy-Stop/Sell-Stop OCO an den Raendern scharfschalten, kein Kursziel, "
            "Flat-by-Time-Exit um 11:00 NY. Quelle: user-bereitgestellte "
            "TradeStation-EasyLanguage-Spezifikation, kein akademisches Paper."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Ohne Parameter-Fitting ueber 10,5 Jahre positiv (PF 1.09), 9/11 Jahre "
                "netto positiv, haelt sich grob ueber beide Zeitraum-Haelften. Aber "
                "duenn: Break-even-Spread liegt bei nur ~0.54 USD Round-Trip - genau "
                "der Bereich realistischer Retail-Gold-Spreads, besonders da rund um "
                "Sessionuebergaenge gehandelt wird. Mit den mittlerweile vier "
                "walk-forward-validierten Filtern (ADX-Regime + Gold-Trend-Bias SMA200 + "
                "Fuellverzoegerung max. 3 Bars + Silber-Alignment) steigt PF auf 1.43, "
                "Sharpe auf 0.61 und Max Drawdown sinkt von -18.5% auf -4.0%, bei knapp "
                "60% weniger Trades als die urspruengliche Konfiguration."
            )
        st.page_link("app_pages/asian_range_breakout.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

# =============================================================================
# Strategie Bestandteile
# =============================================================================
with tab_components:
    col_a, col_b, col_c = st.columns(3, border=True)
    with col_a:
        st.markdown("### :material/timeline: CLS Strategie")
        st.caption("Settlement-Fenster-Entscheidungsbaum (06:00-12:00), Break-Hold-Test")
        st.markdown(
            "Multi-Fenster-Framework (Pre-Settle/Settle/Test/Post-Settle, deutsche Zeit): "
            "haelt der 06:00-09:00-Move den 09:15-Test, bestaetigt durch eine breite "
            "Dollar-Bewegung über die anderen 5 Majors? Zwei Modelle: Continuation "
            "(gehaltener Break) und Reversal (Fade eines gescheiterten Breaks). Eigener "
            "Tab \"Strategiebestandteile\" erklaert das Framework im Detail."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Auf 10 Jahren/6 Paaren haelt die Kernthese: bestaetigte Breaks halten "
                "konsistent oefter (~53-59%) als unbestaetigte (~40-53%). Als mechanische "
                "Handelsregel aber kein Edge (Profit Factor 0.91-0.96, nach Kosten leicht "
                "negativ) — der \"Rates\"-Teil der Quelle ist mangels Datenquelle nicht getestet."
            )
        st.page_link("app_pages/cls_advanced.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

    with col_b:
        st.markdown("### :material/filter_alt: Kalman-Filter")
        st.caption("Signal-Processing-Baustein (fremdes Paper, Gold/XAU-USD-DRL)")
        st.markdown(
            "Kausaler Kalman-Smoother zur Rauschunterdrueckung plus rollierende "
            "Z-Score-Normalisierung -- als eigenstaendiger, importierbarer Baustein "
            "gehalten, bewusst getrennt von jeder konkreten Strategie (nicht mit "
            "ADX-VWAP vermischt)."
        )
        with st.container(border=True):
            st.markdown("**Einordnung**")
            st.caption(
                "Das Quell-Paper behauptet Sharpe 10-13 bei <1,5% Max-Drawdown -- "
                "unplausibel, nicht nachgebaut oder validiert. Hier nur der isolierte, "
                "eigenstaendig pruefbare Filter-Baustein, kein Backtest."
            )
        st.page_link("app_pages/kalman_filter.py", label="Baustein ansehen", icon=":material/arrow_forward:")

    with col_c:
        st.markdown("### :material/candlestick_chart: ADX-VWAP Bausteine")
        st.caption("Die vier Einzelbausteine hinter dem Composite-Signal (Eq. 14)")
        st.markdown(
            "Session-VWAP-Deviation, Vortages-Extreme, ADX-Momentum-Decay und "
            "adaptive Theta-Schwelle -- einzeln erklaert und importierbar, getrennt "
            "von den Backtest-Zahlen der ADX-VWAP FX-Strategie."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Pure-These (Eq. 14 woertlich) ist auf 10 Jahren echten Daten auf allen "
                "6 Paaren negativ. Verfeinerte Variante (Walk-Forward-Screen) ist bester "
                "Kandidat, aber unbestaetigt -- duenne Stichprobe."
            )
        st.page_link("app_pages/adx_vwap_writeup.py", label="Bausteine ansehen", icon=":material/arrow_forward:")

    col_tma, col_overlay, col_gap = st.columns(3, border=True)
    with col_tma:
        st.markdown("### :material/stacked_line_chart: Triple Moving Average")
        st.caption("TEMA/TSMA + GMM-Regime-Cluster + ATR-SL/TP -- Bausteine, noch keine Kante")
        st.markdown(
            "Triple-nested EMA/SMA (n=252, \"12 Monate\") long/flat, plus eine "
            "20/30/50-Tage \"Three Triple\"-Crossover-Variante. Gaussian-Mixture-"
            "Regime-Cluster (wahlweise als Entry-Filter) und ein optionales "
            "ATR-Stop/Kursziel-Risikomanagement stehen als eigenständige, "
            "wiederverwendbare Bausteine bereit. FX-Majors, Gold/Silber/Indizes/"
            "Öl (Dukascopy) sowie BTC (Binance)."
        )
        with st.container(border=True):
            st.markdown("**Ehrlicher Befund**")
            st.caption(
                "Alle Grundvarianten sind vor Kosten durchweg profitabel (Profit "
                "Factor 1.6-2.7), liegen aber deutlich hinter Buy & Hold zurück. "
                "Weder Regime-Entry-Filter noch ATR-Stop/Kursziel verbessern das "
                "robust -- noch keine eigenständige Kante, aber solide Bausteine "
                "(TEMA/TSMA, GMM-Regimes, Risiko-Engine) für die nächste Iteration."
            )
        st.page_link("app_pages/triple_ma.py", label="Bausteine ansehen", icon=":material/arrow_forward:")

    with col_overlay:
        st.markdown("### :material/timer: Execution-Overlay")
        st.caption("Fast Alpha als Timing-Filter (Zarattini & Pagani 2026) -- noch kein Backtest")
        st.markdown(
            "Ein 5-Min-Mean-Reversion-Signal, das als Solo-Strategie an Kosten stirbt "
            "(netto CAGR -0,7%), aber als reiner Timing-Filter für eine ATR-Breakout-"
            "Trendstrategie den Einstiegspreis verbessert -- verändert nie das Signal, "
            "nur den Ausführungszeitpunkt."
        )
        with st.container(border=True):
            st.markdown("**Im Original (SPY, netto)**")
            st.caption(
                "Ohne Overlay CAGR 13,2% / Sharpe 0,86 -> mit Overlay CAGR 15,3% / "
                "Sharpe 0,99. Noch nicht auf FX getestet."
            )
        st.page_link("app_pages/execution_overlay_writeup.py", label="Baustein ansehen", icon=":material/arrow_forward:")

    with col_gap:
        st.markdown("### :material/south_east: Gap-Fade EUR/USD")
        st.caption("Wochenend-Gap-Anomalie (Caporale & Plastun 2016) -- noch kein Backtest")
        st.markdown(
            "Von sechs getesteten Gap-Hypothesen über FX/Rohstoffe/Aktien bleibt nur in "
            "EUR/USD und GBP/USD ein signifikanter, mechanisch handelbarer Effekt: "
            "positive Montags-Gaps faden, EOD glattstellen."
        )
        with st.container(border=True):
            st.markdown("**Im Original (2000-2015)**")
            st.caption(
                "EUR/USD 63,5% Trefferquote / 148 Trades, GBP/USD 60,0% / 221 Trades, "
                "beide z>1,96. Sample endet 2015 -- Out-of-Sample-Nachweis noch offen."
            )
        st.page_link("app_pages/gap_fade_writeup.py", label="Baustein ansehen", icon=":material/arrow_forward:")


# =============================================================================
# 151 Trading Strategies
# =============================================================================
with tab_paper151:
    col_p151, _spacer5, _spacer6 = st.columns(3, border=True)
    with col_p151:
        st.markdown("### :material/auto_stories: 151 Trading Strategies")
        st.caption("Kakushadze & Serur (2018) — Paper-Destillat, Sammelseite")
        st.markdown(
            "Eigenständig aus dem Paper destillierte Grundlagen, Strategiebausteine "
            "je Asset-Klasse, ein Gold-fokussierter Auszug und priorisierte "
            "Verknüpfungsideen mit bestehenden Strategien hier im Repo."
        )
        with st.container(border=True):
            st.markdown("**Status**")
            st.caption(
                "Reine Sammelseite, noch kein Backtest — Sortierung und Verschieben "
                "einzelner Bausteine nach \"Strategie Bestandteile\" bzw. in einen "
                "Backtest folgt erst nach gemeinsamer Durchsicht."
            )
        st.page_link("app_pages/paper151.py", label="Seite öffnen", icon=":material/arrow_forward:")

# =============================================================================
# Neue Papers (Aug. 2026)
# =============================================================================
with tab_new_papers:
    col_np, col_np2, _spacer8 = st.columns(3, border=True)
    with col_np:
        st.markdown("### :material/library_books: Fünf neue Papers (Gold)")
        st.caption("User-Upload, 2026-08-08 — Foreign Flow, GEX, Lead-Lag, Forecaster-Grading, COT-Sentiment")
        st.markdown(
            "Fünf SSRN-Papers, ein Tab pro Paper: extrahierte Strategiebestandteile/Filter/Modelle "
            "mit ehrlicher Machbarkeits-Einschätzung. Nur zwei der fünf sind mit vorhandenen Daten "
            "direkt testbar (Gold-Silber-BTC-Lead-Lag, COT-Sentiment) — beide werden im Anschluss "
            "gegen den Gold Asian-Range Breakout getestet."
        )
        with st.container(border=True):
            st.markdown("**Status**")
            st.caption(
                "Sammelseite mit Machbarkeits-Verdikt pro Paper. GEX und Korea-Foreign-Flow sind "
                "dokumentiert, aber ohne Optionsdaten bzw. Korea-Marktdaten nicht umsetzbar."
            )
        st.page_link("app_pages/goldi_papers_202608.py", label="Seite öffnen", icon=":material/arrow_forward:")
    with col_np2:
        st.markdown("### :material/currency_exchange: Fünf FX-Papers")
        st.caption("User-Upload, 2026-08-09 — Marktstruktur, Fibonacci/VWAP-Theorie, Intraday-Momentum, WMR-Fix")
        st.markdown(
            "Fünf weitere Papers, gleiches Tab-pro-Paper-Muster, ausführlicher analysiert. "
            "**Besonderer Fund:** ein Paper ist mit sehr hoher Wahrscheinlichkeit die bisher "
            "nicht attributierte theoretische Quelle von `strategy/adx_vwap.py` selbst "
            "(Formeln, Abschnittsnummern und ein Code-Docstring stimmen exakt überein). Zwei "
            "weitere Papers (Intraday-Momentum London Open, WMR-Fix-Kollusion) wurden "
            "inzwischen mit eigenen 14,5-Jahre-Backtests getestet."
        )
        with st.container(border=True):
            st.markdown("**Status**")
            st.caption(
                "Sammelseite mit Quellenfund + Machbarkeits-Verdikt pro Paper. Intraday-Momentum "
                "(Tab 3) repliziert NICHT auf eigenen Daten (JPY-Amplifikation und der "
                "behauptete USD/JPY-Edge kehren sich sogar um). WMR-Fix-Sanity-Check (Tab 4) "
                "gemischt: Monatsende-Effekt real, Reform-Erklärung nur bei 3/5 Paaren bestätigt."
            )
        st.page_link("app_pages/fx_papers_202608.py", label="Seite öffnen", icon=":material/arrow_forward:")

st.space("medium")
st.caption(
    "Alle Backtest-Strategien sind Forschungs-/Lernprojekte, keine Anlageberatung. "
    "Backtests sind kein Beweis für zukünftige Performance."
)
