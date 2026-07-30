"""Entry point: routes between the landing page and each strategy dashboard.

Each page module (app_pages/*.py) sets its own st.set_page_config and is a
direct script (not wrapped in a function), per Streamlit multi-page
conventions -- only the active page's module actually executes per run.
"""

import streamlit as st

home = st.Page("app_pages/home.py", title="Übersicht", icon=":material/home:", default=True)
adx_vwap = st.Page(
    "app_pages/adx_vwap.py", title="ADX-VWAP FX-Strategie", icon=":material/candlestick_chart:"
)
ema_sr = st.Page("app_pages/ema_sr.py", title="EMA S/R-Strategie", icon=":material/show_chart:")
ema_combined = st.Page("app_pages/ema_combined.py", title="EMA kombiniert", icon=":material/merge:")
cls_squeeze = st.Page("app_pages/cls_squeeze.py", title="CLS-Squeeze", icon=":material/schedule:")
cls_advanced = st.Page("app_pages/cls_advanced.py", title="CLS Strategie", icon=":material/timeline:")
checklist = st.Page("app_pages/checklist.py", title="Checklist-Strategie", icon=":material/checklist:")
auction_playbook = st.Page("app_pages/auction_playbook.py", title="Auction Market Playbook", icon=":material/gavel:")
ou_modell = st.Page("app_pages/ou_modell.py", title="OU-Modell", icon=":material/monitoring:")
orb_writeup = st.Page("app_pages/orb_writeup.py", title="Opening Range Breakout", icon=":material/bolt:")

page = st.navigation(
    {
        "": [home],
        "Live Logs": [ou_modell],
        "Backtests": [adx_vwap, ema_sr, ema_combined, cls_squeeze, checklist, auction_playbook],
        "Strategie Bestandteile": [cls_advanced, orb_writeup],
    }
)
page.run()
