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
Parameter-Reglern. Beide sind ehrlich dokumentiert — inklusive der Stellen,
wo die Strategie **keinen** robusten Edge zeigt.
"""

st.space("medium")

col1, col2 = st.columns(2, border=True)

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

st.space("medium")
st.caption(
    "Beide Strategien sind Forschungs-/Lernprojekte, keine Anlageberatung. "
    "Backtests sind kein Beweis für zukünftige Performance."
)
