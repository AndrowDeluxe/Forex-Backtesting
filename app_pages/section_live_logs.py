import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Live Logs -- Übersicht", page_icon=":material/rss_feed:", layout="wide")

render_section(
    icon=":material/rss_feed:",
    title="Live Logs",
    items=[
        {
            "page": "app_pages/ou_modell.py",
            "title": "OU-Modell -- Live-Trading-Log",
            "icon": ":material/monitoring:",
            "tag": "LIVE",
        },
        {
            "page": "app_pages/orb_forward_test.py",
            "title": "ORB Forward-Test",
            "icon": ":material/bolt:",
            "tag": "LIVE",
        },
        {
            "page": "app_pages/cls_practical_live_log.py",
            "title": "CLS Practical -- Live Log",
            "icon": ":material/rss_feed:",
            "tag": "LIVE",
        },
    ],
)
