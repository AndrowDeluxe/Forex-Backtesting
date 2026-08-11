import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Strategie Bestandteile -- Übersicht", page_icon=":material/extension:", layout="wide")

render_section(
    icon=":material/extension:",
    title="Strategie Bestandteile",
    items=[
        {
            "page": "app_pages/cls_advanced.py",
            "title": "CLS Strategie",
            "icon": ":material/timeline:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/kalman_filter.py",
            "title": "Kalman-Filter",
            "icon": ":material/filter_alt:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/adx_vwap_writeup.py",
            "title": "ADX-VWAP Bausteine",
            "icon": ":material/candlestick_chart:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/triple_ma.py",
            "title": "Triple Moving Average",
            "icon": ":material/stacked_line_chart:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/execution_overlay_writeup.py",
            "title": "Execution-Overlay",
            "icon": ":material/timer:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/gap_fade_writeup.py",
            "title": "Gap-Fade EUR/USD",
            "icon": ":material/south_east:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/orb_writeup.py",
            "title": "Opening Range Breakout",
            "icon": ":material/bolt:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/risk_management.py",
            "title": "Risk Management",
            "icon": ":material/shield:",
            "tag": "BAUSTEIN",
        },
        {
            "page": "app_pages/fx_liquidity_filter.py",
            "title": "FX-Liquiditaetsfilter",
            "icon": ":material/water_drop:",
            "tag": "FILTER",
        },
        {
            "page": "app_pages/cb_event_window_filter.py",
            "title": "Notenbank-Event-Window",
            "icon": ":material/event:",
            "tag": "FILTER",
        },
    ],
)
