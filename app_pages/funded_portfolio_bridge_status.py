"""Live-Status Funded-Portfolio-Bridge (2026-09-02) -- ECHTES GELD, TTP
(Konto 2, Demo-Challenge mit echtem Regelwerk) + IQ Markets/BeyondIQCapital
(Demo-Challenge). 6 Beine je Konto: Gold ASB, CLS Practical, Trend Pullback,
CTNL Edge, OU-Modell, NY-Open ORB. Liest nur den vom Bridge-Watchdog
committeten Snapshot, ruft nie selbst MT5/die Bridge auf."""

import streamlit as st

from app_pages._bridge_status_data import load_snapshot, render_bridge_section, render_generated_at

st.set_page_config(page_title="Funded-Portfolio-Bridge -- Status", page_icon=":material/account_balance_wallet:", layout="wide")

st.page_link("app_pages/section_live_logs.py", label="Zurück zur Portfolio-Übersicht", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/account_balance_wallet: Funded-Portfolio-Bridge")
st.error(
    "**LIVE — echtes Geld/Challenge-Kapital**, DRY_RUN=False. Zwei Konten mit identischem Signal-Strom, "
    "unterschiedlichem Regelwerk: TTP (Tageslimit -3%, Gesamt-DD -7%) und IQ Markets (kein Tageslimit, "
    "Gesamt-DD -6%).",
    icon=":material/warning:",
)

snapshot = load_snapshot()
if snapshot is None:
    st.info("Noch kein Status-Snapshot vorhanden — der Bridge-Watchdog läuft alle 30 Min.", icon=":material/hourglass_empty:")
    st.stop()

render_generated_at(snapshot)
st.divider()

entry = snapshot["bridges"].get("Funded-Portfolio-Bridge")
if entry is None:
    st.warning("Diese Bridge ist nicht im Snapshot enthalten.", icon=":material/error:")
    st.stop()

render_bridge_section("Funded-Portfolio-Bridge", entry)

st.divider()
st.caption(
    "Log: `C:\\Users\\andre\\Funded-Portfolio-Bridge\\logs\\task_run.log` (lokal). "
    "Reproduzierbar/Logik: `Funded-Portfolio-Bridge/run_once.py` + `challenge_portfolio/paper_bot.py`."
)
