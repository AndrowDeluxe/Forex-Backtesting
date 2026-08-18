"""Portfolio Management -- Hauptthema-Seite.

Sammelt die Kombination aller validierten Einzelstrategien (BTC-EMA9/21,
Gold Asian-Range Breakout, CLS Practical/EURUSD, OU-Modell/S&P 500,
Trend Pullback, Gold-Bitcoin Dual Momentum, ORB) zu drei Portfolios: der
kombinierte Backtest aller 7, ein EK-Portfolio (Eigenkapital, Max-Sharpe)
und ein FK-Portfolio (Fremdkapital/Prop-Firm, Monte-Carlo-optimiert auf
Regelkonformitaet) -- siehe app_pages/portfolio_construction.py.
Architektur-Entscheidung (siehe knowledge/resources/
trend-following-momentum.md, Nachtrag 2026-08-15): Kapital-Allokation
statt Risiko-Verwebung -- jede Strategie behaelt ihre eigene validierte,
unveraenderte Logik auf einem festen Kapitalanteil, die $-Equity-Kurven
werden kombiniert. Kein Eingriff in die live laufenden Bots.
"""

import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Portfolio Management -- Übersicht", page_icon=":material/account_balance_wallet:", layout="wide")

render_section(
    icon=":material/account_balance_wallet:",
    title="Portfolio Management",
    items=[
        {
            "page": "app_pages/portfolio_construction.py",
            "title": "Portfolio-Konstruktion -- EK/FK",
            "icon": ":material/account_balance_wallet:",
            "tag": "PORTFOLIO",
        },
    ],
)

st.divider()
st.markdown("### Architektur-Entscheidung (bereits getroffen)")
st.markdown(
    """
**Kapital-Allokation statt Risiko-Verwebung.** Das OU-Modell haelt bis zu ~147 Positionen
gleichzeitig mit einem eigenen internen Aggregat-Risiko-Deckel (15%) und laeuft **live**
auf Konto 2 -- eine echte Verwebung aller Strategien in EINEN gemeinsamen Risiko-Pool
wuerde Eingriffe in diese Live-Engine erfordern.

Stattdessen: jede Strategie bekommt einen festen Anteil des Gesamtkapitals und laeuft mit
ihrer eigenen, unveraenderten, bereits validierten Logik. Die einzelnen $-Equity-Kurven
werden am Ende summiert -- echte Trades pro Strategie, kein Eingriff in produktiven Code.

Details und Zwischenstand: `knowledge/resources/trend-following-momentum.md`
(Nachtrag 2026-08-15).
"""
)

st.markdown("### Die 7 Bausteine (Stand 2026-08-18)")
cols = st.columns(2)
with cols[0]:
    st.markdown(
        "- **OU-Modell (S&P 500 only)** -- laeuft live (TTP + Tickmill)\n"
        "- **CLS Practical (EUR/USD)** -- Demo-Bot (CLS-Practical-Bridge)\n"
        "- **BTC EMA9/21** -- Dry-Run-Bot, Symbol auf Prop-Konto verifiziert\n"
        "- **Gold Asian-Range Breakout** -- laeuft live (GoldASB-MT5-Bridge)\n"
    )
with cols[1]:
    st.markdown(
        "- **Trend Pullback** (5 Maerkte) -- Demo-Bots FK1/FK2\n"
        "- **Gold-Bitcoin Dual Momentum** -- nur EK, Backtest-only (Konzentrationsrisiko)\n"
        "- **ORB** (long+ADX, NDX/SP500) -- nur EK, Demo-Forward-Test\n"
    )
st.caption(
    "FK-Portfolio nutzt nur 5 der 7 (OU-Modell S&P500-only mit TTP-handelbarer Teilmenge, "
    "CLS Practical, BTC EMA9/21, Gold ASB, Trend Pullback bei FK1-Risikostufe) -- ORB und "
    "Gold-Bitcoin Dual Momentum sind nicht realistisch FK-tauglich, siehe Vorbehalte-Tab "
    "auf der Portfolio-Konstruktion-Seite."
)
