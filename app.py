"""Entry point: routes between the landing page and each strategy dashboard.

Each page module (app_pages/*.py) sets its own st.set_page_config and is a
direct script (not wrapped in a function), per Streamlit multi-page
conventions -- only the active page's module actually executes per run.

Sidebar is a flat, single-level list of Hauptthemen (Home + one row per
section_*.py page) -- no groups, no visible "hub" strategy page. Every
individual strategy/Baustein page is registered here too but with
visibility="hidden", so it stays routable (via the tiles on its
section_*.py page) without cluttering the sidebar.
"""

import streamlit as st

home = st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True)

section_live_logs = st.Page(
    "app_pages/section_live_logs.py", title="Live Logs", icon=":material/rss_feed:"
)
section_fertige_strategien = st.Page(
    "app_pages/section_fertige_strategien.py", title="Fertige Strategien", icon=":material/military_tech:"
)
section_backtests = st.Page(
    "app_pages/section_backtests.py", title="Backtests", icon=":material/bar_chart:"
)
section_components = st.Page(
    "app_pages/section_components.py", title="Strategie Bestandteile", icon=":material/extension:"
)
section_erkenntnisse = st.Page(
    "app_pages/section_erkenntnisse.py", title="Erkenntnisse", icon=":material/auto_stories:"
)
paper_research = st.Page(
    "app_pages/paper_research.py", title="Paper Research", icon=":material/travel_explore:"
)
education = st.Page("app_pages/education.py", title="Education", icon=":material/school:")

education_gold_intraday = st.Page(
    "app_pages/education_gold_intraday.py", title="Gold-Intraday-Strategie",
    icon=":material/candlestick_chart:", visibility="hidden",
)
education_book_chan = st.Page(
    "app_pages/education_book_chan.py", title="Quantitative Trading (Chan)",
    icon=":material/menu_book:", visibility="hidden",
)

# Individual strategy/Baustein pages -- hidden from the sidebar, reachable
# only via the tiles on their section_*.py page.
ou_modell = st.Page(
    "app_pages/ou_modell.py", title="OU-Modell", icon=":material/monitoring:", visibility="hidden"
)
orb_forward_test = st.Page(
    "app_pages/orb_forward_test.py", title="ORB Forward-Test", icon=":material/bolt:", visibility="hidden"
)
fertige_strategien = st.Page(
    "app_pages/fertige_strategien.py", title="OU-Modell (finale Konfiguration)",
    icon=":material/military_tech:", visibility="hidden",
)
ou_scanner = st.Page(
    "app_pages/ou_scanner.py", title="OU-Modell Live-Signale (Scanner)", icon=":material/radar:",
    visibility="hidden",
)
gold_bitcoin_dual_momentum = st.Page(
    "app_pages/gold_bitcoin_dual_momentum.py", title="Gold-Bitcoin Dual Momentum",
    icon=":material/currency_bitcoin:", visibility="hidden",
)
asian_range_breakout = st.Page(
    "app_pages/asian_range_breakout.py", title="Gold Asian-Range Breakout", icon=":material/wb_twilight:",
    visibility="hidden",
)
presettle_breakout = st.Page(
    "app_pages/presettle_breakout.py", title="Pre-Settle Range Breakout", icon=":material/wb_twilight:",
    visibility="hidden",
)
adx_vwap = st.Page(
    "app_pages/adx_vwap.py", title="ADX-VWAP FX-Strategie", icon=":material/candlestick_chart:",
    visibility="hidden",
)
ema_sr = st.Page(
    "app_pages/ema_sr.py", title="EMA S/R-Strategie", icon=":material/show_chart:", visibility="hidden"
)
ema_combined = st.Page(
    "app_pages/ema_combined.py", title="EMA kombiniert", icon=":material/merge:", visibility="hidden"
)
cls_squeeze = st.Page(
    "app_pages/cls_squeeze.py", title="CLS-Squeeze", icon=":material/schedule:", visibility="hidden"
)
checklist = st.Page(
    "app_pages/checklist.py", title="Checklist-Strategie", icon=":material/checklist:", visibility="hidden"
)
auction_playbook = st.Page(
    "app_pages/auction_playbook.py", title="Auction Market Playbook", icon=":material/gavel:",
    visibility="hidden",
)
orb_strategy_page = st.Page(
    "app_pages/orb_strategy.py", title="ORB Strategie", icon=":material/bolt:", visibility="hidden"
)
ou_paper_backtest = st.Page(
    "app_pages/ou_paper_backtest.py", title="OU-Modell Paper-Backtest", icon=":material/science:",
    visibility="hidden",
)
cls_advanced = st.Page(
    "app_pages/cls_advanced.py", title="CLS Strategie", icon=":material/timeline:", visibility="hidden"
)
kalman_filter = st.Page(
    "app_pages/kalman_filter.py", title="Kalman-Filter", icon=":material/filter_alt:", visibility="hidden"
)
adx_vwap_writeup = st.Page(
    "app_pages/adx_vwap_writeup.py", title="ADX-VWAP Bausteine", icon=":material/candlestick_chart:",
    visibility="hidden",
)
triple_ma = st.Page(
    "app_pages/triple_ma.py", title="Triple Moving Average", icon=":material/stacked_line_chart:",
    visibility="hidden",
)
execution_overlay_writeup = st.Page(
    "app_pages/execution_overlay_writeup.py", title="Execution-Overlay", icon=":material/timer:",
    visibility="hidden",
)
gap_fade_writeup = st.Page(
    "app_pages/gap_fade_writeup.py", title="Gap-Fade EUR/USD", icon=":material/south_east:",
    visibility="hidden",
)
orb_writeup = st.Page(
    "app_pages/orb_writeup.py", title="Opening Range Breakout", icon=":material/bolt:", visibility="hidden"
)
risk_management = st.Page(
    "app_pages/risk_management.py", title="Risk Management", icon=":material/shield:", visibility="hidden"
)
paper151 = st.Page(
    "app_pages/paper151.py", title="151 Trading Strategies", icon=":material/auto_stories:",
    visibility="hidden",
)
goldi_papers_202608 = st.Page(
    "app_pages/goldi_papers_202608.py", title="Neue Papers (Aug. 2026)", icon=":material/library_books:",
    visibility="hidden",
)
fx_papers_202608 = st.Page(
    "app_pages/fx_papers_202608.py", title="FX-Papers (Aug. 2026)", icon=":material/currency_exchange:",
    visibility="hidden",
)
fx_liquidity_filter = st.Page(
    "app_pages/fx_liquidity_filter.py", title="FX-Liquiditaetsfilter", icon=":material/water_drop:",
    visibility="hidden",
)
cb_event_window_filter = st.Page(
    "app_pages/cb_event_window_filter.py", title="Notenbank-Event-Window", icon=":material/event:",
    visibility="hidden",
)

page = st.navigation(
    [
        home,
        section_live_logs,
        section_fertige_strategien,
        section_backtests,
        section_components,
        section_erkenntnisse,
        paper_research,
        education,
        # hidden pages -- must still be registered so they stay routable
        education_gold_intraday, education_book_chan,
        ou_modell, orb_forward_test,
        fertige_strategien, ou_scanner, gold_bitcoin_dual_momentum, asian_range_breakout,
        presettle_breakout,
        adx_vwap, ema_sr, ema_combined, cls_squeeze, checklist, auction_playbook,
        orb_strategy_page, ou_paper_backtest,
        cls_advanced, kalman_filter, adx_vwap_writeup, triple_ma, risk_management,
        execution_overlay_writeup, gap_fade_writeup, orb_writeup,
        paper151, goldi_papers_202608, fx_papers_202608,
        fx_liquidity_filter, cb_event_window_filter,
    ]
)
page.run()
