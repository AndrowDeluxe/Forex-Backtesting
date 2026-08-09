import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Backtests -- Übersicht", page_icon=":material/bar_chart:", layout="wide")

render_section(
    icon=":material/bar_chart:",
    title="Backtests",
    items=[
        {
            "page": "app_pages/adx_vwap.py",
            "title": "ADX-VWAP FX-Strategie",
            "icon": ":material/candlestick_chart:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/ema_sr.py",
            "title": "EMA S/R-Strategie",
            "icon": ":material/show_chart:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/ema_combined.py",
            "title": "EMA kombiniert",
            "icon": ":material/merge:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/cls_squeeze.py",
            "title": "CLS-Squeeze",
            "icon": ":material/schedule:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/checklist.py",
            "title": "Checklist-Strategie",
            "icon": ":material/checklist:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/auction_playbook.py",
            "title": "Auction Market Playbook",
            "icon": ":material/gavel:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/orb_strategy.py",
            "title": "ORB Strategie",
            "icon": ":material/bolt:",
            "tag": "BACKTEST",
        },
        {
            "page": "app_pages/ou_paper_backtest.py",
            "title": "OU-Modell Paper-Backtest",
            "icon": ":material/science:",
            "tag": "BACKTEST",
        },
    ],
)
