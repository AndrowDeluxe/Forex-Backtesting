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
cls_advanced = st.Page("app_pages/cls_advanced.py", title="CLS Advanced", icon=":material/timeline:")
checklist = st.Page("app_pages/checklist.py", title="Checklist-Strategie", icon=":material/checklist:")

page = st.navigation({"": [home], "Backtests": [adx_vwap, ema_sr, ema_combined, cls_squeeze, cls_advanced, checklist]})
page.run()
