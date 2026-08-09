import streamlit as st

from app_pages._section_ui import render_section

st.set_page_config(page_title="Erkenntnisse -- Übersicht", page_icon=":material/auto_stories:", layout="wide")

render_section(
    icon=":material/auto_stories:",
    title="Erkenntnisse",
    items=[
        {
            "page": "app_pages/paper151.py",
            "title": "151 Trading Strategies",
            "icon": ":material/auto_stories:",
            "tag": "PAPER",
        },
        {
            "page": "app_pages/goldi_papers_202608.py",
            "title": "Neue Papers (Aug. 2026)",
            "icon": ":material/library_books:",
            "tag": "PAPER",
        },
        {
            "page": "app_pages/fx_papers_202608.py",
            "title": "FX-Papers (Aug. 2026)",
            "icon": ":material/currency_exchange:",
            "tag": "PAPER",
        },
    ],
)
