"""Landing page: short welcome + a compact tile per Hauptthema.

The sidebar (app.py) is now a flat, single-level list of Hauptthemen --
no grouped sub-items, no visible "hub" page underneath. Clicking a
Hauptthema in the sidebar opens its own section_*.py page, which shows
the actual grid of individual strategies/Bausteine as small tiles (see
app_pages/_section_ui.py). This page is just the entry point + directory."""

import streamlit as st

st.set_page_config(
    page_title="Trading-Strategie-Backtests",
    page_icon=":material/insights:",
    layout="wide",
)

"""
# :material/insights: Trading-Strategie-Backtests

Ein Ort für alle Backtests und Live-Logs: jede Strategie ist eigenständig
und interaktiv, mit eigenen Kennzahlen, Charts und Parameter-Reglern.
Alle sind ehrlich dokumentiert — inklusive der Stellen, wo eine Strategie
**keinen** robusten Edge zeigt.

Die einzige Strategie mit einer bisher validierten, robusten Kante:
**Gold Asian-Range Breakout** (unter *Fertige Strategien*) — mit den vier
walk-forward-validierten Filtern PF 1.43, Sharpe 0.61, Max Drawdown -4.0%.

Wähle links ein Hauptthema, um die zugehörigen Strategien zu sehen.
"""

st.divider()
st.caption("HAUPTTHEMEN")

sections = [
    {
        "page": "app_pages/section_live_logs.py",
        "title": "Live Logs",
        "icon": ":material/rss_feed:",
        "desc": "Read-only Logs zweier Live-/Demo-Konten, kein Backtest.",
    },
    {
        "page": "app_pages/section_fertige_strategien.py",
        "title": "Fertige Strategien",
        "icon": ":material/military_tech:",
        "desc": "Fest verriegelte Konfigurationen, keine Tuning-Regler.",
    },
    {
        "page": "app_pages/section_backtests.py",
        "title": "Backtests",
        "icon": ":material/bar_chart:",
        "desc": "Interaktive Backtest-Dashboards, teils mit Tuning-Reglern.",
    },
    {
        "page": "app_pages/section_components.py",
        "title": "Strategie Bestandteile",
        "icon": ":material/extension:",
        "desc": "Einzelne, wiederverwendbare Bausteine aus Research-Papers.",
    },
    {
        "page": "app_pages/section_erkenntnisse.py",
        "title": "Erkenntnisse",
        "icon": ":material/auto_stories:",
        "desc": "Paper-Destillate und Machbarkeits-Einschätzungen.",
    },
    {
        "page": "app_pages/paper_research.py",
        "title": "Paper Research",
        "icon": ":material/travel_explore:",
        "desc": "Automatisierte Paper-Recherche-Pipeline.",
    },
    {
        "page": "app_pages/education.py",
        "title": "Education",
        "icon": ":material/school:",
        "desc": "Lern-Checklisten, z.B. zur Gold-SSRN-Strategie.",
    },
]

cols = st.columns(3)
for i, s in enumerate(sections):
    with cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{s['icon']} {s['title']}**")
            st.caption(s["desc"])
            st.page_link(s["page"], label="Öffnen", icon=":material/arrow_forward:")

st.divider()
st.caption(
    "Alle Backtest-Strategien sind Forschungs-/Lernprojekte, keine Anlageberatung. "
    "Backtests sind kein Beweis für zukünftige Performance."
)
