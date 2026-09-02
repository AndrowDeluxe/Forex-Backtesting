"""Live-Status FKInstantFunding-MT5-Bridge (2026-09-02) -- DRY_RUN, kein
echtes Geld (BeyondIQCapital, Konto 17764, Instant-Funding-Challenge).
Verbindet echtes MT5-Konto, plant Orders, sendet aber nichts (echte
Order-Ausführung "noch nicht implementiert"). Liest nur den vom
Bridge-Watchdog committeten Snapshot, ruft nie selbst MT5/die Bridge auf."""

import streamlit as st

from app_pages._bridge_status_data import load_snapshot, render_bridge_section, render_generated_at

st.set_page_config(page_title="FK Instant Funding -- Status", page_icon=":material/account_balance_wallet:", layout="wide")

st.page_link("app_pages/section_live_logs.py", label="Zurück zur Portfolio-Übersicht", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/account_balance_wallet: FKInstantFunding-MT5-Bridge")
st.warning(
    "**DRY_RUN — kein echtes Geld.** Verbindet ein echtes MT5-Konto (BeyondIQCapital, IQIF100K-144048) "
    "und plant Orders auf Basis der 6 echten Signal-Engines, sendet aber nichts an den Broker. "
    "(Für die reine Paper-Simulation ohne MT5-Verbindung siehe `fk_instant_funding/paper_bot.py`.)",
    icon=":material/science:",
)

snapshot = load_snapshot()
if snapshot is None:
    st.info("Noch kein Status-Snapshot vorhanden — der Bridge-Watchdog läuft alle 30 Min.", icon=":material/hourglass_empty:")
    st.stop()

render_generated_at(snapshot)
st.divider()

entry = snapshot["bridges"].get("FKInstantFunding-MT5-Bridge")
if entry is None:
    st.warning("Diese Bridge ist nicht im Snapshot enthalten.", icon=":material/error:")
    st.stop()

render_bridge_section("FKInstantFunding-MT5-Bridge", entry)

st.divider()
st.caption("Log: `C:\\Users\\andre\\FKInstantFunding-MT5-Bridge\\logs\\task_run.log` (lokal). Reproduzierbar/Logik: `FKInstantFunding-MT5-Bridge/run_once.py`.")
