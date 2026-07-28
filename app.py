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

page = st.navigation([home, adx_vwap, ema_sr])
page.run()
