import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Fertige Strategien -- Übersicht", page_icon=":material/military_tech:", layout="wide")

render_section(
    icon=":material/military_tech:",
    title="Fertige Strategien",
    items=[
        {
            "page": "app_pages/fertige_strategien.py",
            "title": "OU-Modell (finale Konfiguration)",
            "icon": ":material/military_tech:",
            "tag": "STRATEGIE",
        },
        {
            "page": "app_pages/cls_practical_strategy.py",
            "title": "CLS Practical (EUR/USD)",
            "icon": ":material/military_tech:",
            "tag": "STRATEGIE",
        },
        {
            "page": "app_pages/ou_scanner.py",
            "title": "OU-Modell Live-Signale (Scanner)",
            "icon": ":material/radar:",
            "tag": "SCANNER",
        },
        {
            "page": "app_pages/gold_bitcoin_dual_momentum.py",
            "title": "Gold-Bitcoin Dual Momentum",
            "icon": ":material/currency_bitcoin:",
            "tag": "STRATEGIE",
        },
        {
            "page": "app_pages/asian_range_breakout.py",
            "title": "Gold Asian-Range Breakout",
            "icon": ":material/wb_twilight:",
            "tag": "STRATEGIE",
        },
        {
            "page": "app_pages/mt5_trend_pullback.py",
            "title": "Trend Pullback",
            "icon": ":material/smart_toy:",
            "tag": "STRATEGIE",
        },
    ],
)
