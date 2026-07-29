"""Landing page: overview and entry point for both strategy dashboards."""

import streamlit as st

st.set_page_config(
    page_title="Trading-Strategie-Backtests",
    page_icon=":material/insights:",
    layout="wide",
)

"""
# :material/insights: Trading-Strategie-Backtests

Ein Ort für alle Backtests: jede Karte unten ist eine eigenständige,
interaktive Strategie mit ihren eigenen Kennzahlen, Charts und
Parameter-Reglern. Alle fünf sind ehrlich dokumentiert — inklusive der
Stellen, wo die Strategie **keinen** robusten Edge zeigt.
"""

st.space("medium")

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
    st.markdown("### :material/timeline: CLS Advanced")
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

with col6:
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

st.space("medium")
st.caption(
    "Alle fünf Strategien sind Forschungs-/Lernprojekte, keine Anlageberatung. "
    "Backtests sind kein Beweis für zukünftige Performance."
)
