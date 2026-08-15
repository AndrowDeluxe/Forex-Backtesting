"""Portfolio Management -- Hauptthema-Seite (Platzhalter).

Sammelt spaeter die Kombination aller Einzelstrategien (BTC-EMA9/21,
Gold Asian-Range Breakout, CLS Practical/EURUSD, OU-Modell/S&P 500, plus
zwei noch offene Strategien) zu einem Portfolio mit gemeinsamer
Kapitalallokation. Architektur-Entscheidung (siehe
knowledge/resources/trend-following-momentum.md, Nachtrag 2026-08-15):
Kapital-Allokation statt Risiko-Verwebung -- jede Strategie behaelt ihre
eigene validierte, unveraenderte Logik auf einem festen Kapitalanteil,
die $-Equity-Kurven werden summiert. Kein Eingriff in die live laufende
OU-Modell-Engine.

Pausiert bis die zwei weiteren Strategien feststehen -- noch keine
Unterseiten/Kacheln, daher kein render_section-Grid, sondern ein reiner
Status-Hinweis.
"""

import streamlit as st

st.set_page_config(page_title="Portfolio Management -- Übersicht", page_icon=":material/account_balance_wallet:", layout="wide")

st.caption("SECTION")
st.markdown("## :material/account_balance_wallet: Portfolio Management")
st.caption("Kombination aller fertigen Einzelstrategien zu einem gemeinsamen Portfolio")
st.divider()

st.info(
    "**Noch im Aufbau.** Hier entsteht die Kombination der bisherigen Einzelstrategien "
    "(BTC-EMA9/21, Gold Asian-Range Breakout, CLS Practical/EUR-USD, OU-Modell/S&P 500) "
    "plus zwei weiterer, noch offener Strategien zu einem gemeinsamen Portfolio. "
    "Pausiert, bis die zwei zusaetzlichen Strategien feststehen.",
    icon=":material/hourglass_empty:",
)

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

st.markdown("### Bisher identifizierte Bausteine")
cols = st.columns(2)
with cols[0]:
    st.markdown(
        "- **BTC-EMA9/21** (Krypto, Daily) -- getestet, noch keine Streamlit-Seite\n"
        "- **Gold Asian-Range Breakout** + ADX>=15-Filter -- bereits als eigene "
        "Fertige-Strategie-Seite vorhanden\n"
    )
with cols[1]:
    st.markdown(
        "- **CLS Practical (EUR/USD)** -- bereits als eigene Fertige-Strategie-Seite vorhanden\n"
        "- **OU-Modell (S&P 500)** -- laeuft live, eigene Fertige-Strategie-Seite vorhanden\n"
        "- *(zwei weitere Strategien offen)*\n"
    )
