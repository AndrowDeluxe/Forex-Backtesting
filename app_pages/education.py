"""Education -- Hub-Seite mit Kacheln zu den einzelnen Lern-Tracks.

Kein Backtest-Dashboard, sondern der Einstiegspunkt fuer alle persoenlichen
Lern-/Vorgehens-Inhalte. Jeder Track ist eine eigene Seite unter
`app_pages/education_*.py` (hidden in der Sidebar, nur ueber die Kacheln
hier erreichbar) -- Muster identisch zu den `section_*.py`-Hub-Seiten
(siehe `_section_ui.py`).
"""

import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Education", page_icon=":material/school:", layout="wide")

render_section(
    icon=":material/school:",
    title="Education",
    items=[
        {
            "page": "app_pages/education_gold_intraday.py",
            "title": "Gold-Intraday-Strategie aus SSRN-Papers",
            "icon": ":material/candlestick_chart:",
            "tag": "TRACK",
        },
        {
            "page": "app_pages/education_book_chan.py",
            "title": "Buch: Quantitative Trading (Chan)",
            "icon": ":material/menu_book:",
            "tag": "BUCH",
        },
        {
            "page": "app_pages/education_kelly.py",
            "title": "Kelly-Formel & Risk Management",
            "icon": ":material/calculate:",
            "tag": "TRACK",
        },
    ],
)
