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
asian_range_breakout = st.Page(
    "app_pages/asian_range_breakout.py", title="Gold Asian-Range Breakout", icon=":material/wb_twilight:"
)
triple_ma = st.Page(
    "app_pages/triple_ma.py", title="Triple Moving Average", icon=":material/stacked_line_chart:"
)
ou_modell = st.Page("app_pages/ou_modell.py", title="OU-Modell", icon=":material/monitoring:")
orb_forward_test = st.Page("app_pages/orb_forward_test.py", title="ORB Forward-Test", icon=":material/bolt:")
orb_writeup = st.Page("app_pages/orb_writeup.py", title="Opening Range Breakout", icon=":material/bolt:")
orb_strategy_page = st.Page("app_pages/orb_strategy.py", title="ORB Strategie", icon=":material/bolt:")
paper_research = st.Page(
    "app_pages/paper_research.py", title="Paper Research", icon=":material/travel_explore:"
)
ou_paper_backtest = st.Page(
    "app_pages/ou_paper_backtest.py", title="OU-Modell Paper-Backtest", icon=":material/science:"
)
fertige_strategien = st.Page(
    "app_pages/fertige_strategien.py", title="OU-Modell (finale Konfiguration)", icon=":material/military_tech:"
)
ou_scanner = st.Page(
    "app_pages/ou_scanner.py", title="OU-Modell Live-Signale (Scanner)", icon=":material/radar:"
)
gold_bitcoin_dual_momentum = st.Page(
    "app_pages/gold_bitcoin_dual_momentum.py", title="Gold-Bitcoin Dual Momentum", icon=":material/currency_bitcoin:"
)
education = st.Page("app_pages/education.py", title="Education", icon=":material/school:")
risk_management = st.Page("app_pages/risk_management.py", title="Risk Management", icon=":material/shield:")
paper151 = st.Page("app_pages/paper151.py", title="151 Trading Strategies", icon=":material/auto_stories:")
goldi_papers_202608 = st.Page(
    "app_pages/goldi_papers_202608.py", title="Neue Papers (Aug. 2026)", icon=":material/library_books:"
)
fx_papers_202608 = st.Page(
    "app_pages/fx_papers_202608.py", title="FX-Papers (Aug. 2026)", icon=":material/currency_exchange:"
)
execution_overlay_writeup = st.Page(
    "app_pages/execution_overlay_writeup.py", title="Execution-Overlay", icon=":material/timer:"
)
gap_fade_writeup = st.Page(
    "app_pages/gap_fade_writeup.py", title="Gap-Fade EUR/USD", icon=":material/south_east:"
)

page = st.navigation(
    {
        "": [home],
        "Live Logs": [ou_modell, orb_forward_test],
        "Fertige Strategien": [fertige_strategien, ou_scanner, gold_bitcoin_dual_momentum],
        "Backtests": [
            adx_vwap, ema_sr, ema_combined, cls_squeeze, checklist, auction_playbook,
            asian_range_breakout, orb_strategy_page, ou_paper_backtest,
        ],
        "Strategie Bestandteile": [
            cls_advanced, orb_writeup, triple_ma, risk_management,
            execution_overlay_writeup, gap_fade_writeup,
        ],
        "150 Strategien Paper": [paper151],
        "Neue Papers": [goldi_papers_202608, fx_papers_202608],
        "Paper Research": [paper_research],
        "Education": [education],
    }
)
page.run()
