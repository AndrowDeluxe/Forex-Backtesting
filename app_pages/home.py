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

tab_live, tab_backtests, tab_components, tab_paper151 = st.tabs(
    ["Live Logs", "Backtests", "Strategie Bestandteile", "151 Trading Strategies"]
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
                "Sessionuebergaenge gehandelt wird. Mit den beiden mittlerweile "
                "walk-forward-validierten Filtern (ADX-Regime + Gold-Trend-Bias, "
                "SMA200) steigt PF auf 1.18 und Max Drawdown sinkt von -18.5% auf "
                "-9.4%, bei etwa halb so vielen Trades."
            )
        st.page_link("app_pages/asian_range_breakout.py", label="Dashboard öffnen", icon=":material/arrow_forward:")

# =============================================================================
# Strategie Bestandteile
# =============================================================================
with tab_components:
    col_a, _spacer1, _spacer2 = st.columns(3, border=False)
    with col_a:
        with st.container(border=True):
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

    col_tma, _spacer3, _spacer4 = st.columns(3, border=False)
    with col_tma:
        with st.container(border=True):
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

st.space("medium")
st.caption(
    "Alle Backtest-Strategien sind Forschungs-/Lernprojekte, keine Anlageberatung. "
    "Backtests sind kein Beweis für zukünftige Performance."
)
