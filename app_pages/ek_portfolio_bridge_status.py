"""Live-Status EK-Portfolio-Bridge (2026-09-02) -- ECHTES GELD, Tickmill
(Konto 55918977). Liest nur den vom Bridge-Watchdog committeten Snapshot,
ruft nie selbst MT5/die Bridge auf."""

import streamlit as st

from app_pages._bridge_status_data import load_snapshot, render_bridge_section, render_generated_at

st.set_page_config(page_title="EK-Portfolio-Bridge -- Status", page_icon=":material/account_balance_wallet:", layout="wide")

st.page_link("app_pages/section_live_logs.py", label="Zurück zur Portfolio-Übersicht", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/account_balance_wallet: EK-Portfolio-Bridge")
st.error(
    "**LIVE — echtes Geld** (Tickmill, Konto 55918977). 13 Beine, darunter NY-Open ORB, "
    "OU-Modell, Gold ASB, CLS Practical, CTNL Edge, Trend Pullback.",
    icon=":material/warning:",
)

snapshot = load_snapshot()
if snapshot is None:
    st.info("Noch kein Status-Snapshot vorhanden — der Bridge-Watchdog läuft alle 30 Min.", icon=":material/hourglass_empty:")
    st.stop()

render_generated_at(snapshot)
st.divider()

entry = snapshot["bridges"].get("EK-Portfolio-Bridge")
if entry is None:
    st.warning("Diese Bridge ist nicht im Snapshot enthalten.", icon=":material/error:")
    st.stop()

render_bridge_section("EK-Portfolio-Bridge", entry)

st.divider()
st.caption("Log: `C:\\Users\\andre\\EK-Portfolio-Bridge\\logs\\task_run.log` (lokal). Reproduzierbar/Logik: `EK-Portfolio-Bridge/run_once.py` + `legs/`.")
