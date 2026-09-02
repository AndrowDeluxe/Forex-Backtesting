"""Portfolio-Übersicht (2026-09-02, neu fokussiert auf die drei echten
Portfolio-Bridges statt einzelner Strategie-Live-Logs -- Nutzerauftrag:
"wir fokussieren uns jetzt erstmal nur noch auf die portfolio Arbeit").
Zeigt eine Status-Kachel je Bridge direkt hier, mit Link zur Detailseite."""

import streamlit as st

from app_pages._bridge_status_data import load_snapshot, render_generated_at, status_pill

st.set_page_config(page_title="Portfolio-Bridges -- Übersicht", page_icon=":material/account_balance_wallet:", layout="wide")

st.markdown("## :material/account_balance_wallet: Portfolio-Bridges -- Live-Status")
st.caption(
    "Die drei laufenden Portfolio-Bridges auf einen Blick. Ein lokaler Bridge-Watchdog (alle 30 Min.) "
    "prüft die Logs und pusht einen Status-Snapshot ins Repo -- diese Seite ruft nie selbst MT5/eine "
    "Bridge auf."
)

snapshot = load_snapshot()
if snapshot is None:
    st.info("Noch kein Status-Snapshot vorhanden — der Bridge-Watchdog läuft alle 30 Min.", icon=":material/hourglass_empty:")
    st.stop()

render_generated_at(snapshot)
st.divider()

TILES = [
    {
        "name": "EK-Portfolio-Bridge",
        "page": "app_pages/ek_portfolio_bridge_status.py",
        "subtitle": "Tickmill -- LIVE, echtes Geld",
        "tag": "ECHTGELD",
    },
    {
        "name": "Funded-Portfolio-Bridge",
        "page": "app_pages/funded_portfolio_bridge_status.py",
        "subtitle": "TTP + IQ Markets -- LIVE, Challenge-Kapital",
        "tag": "ECHTGELD",
    },
    {
        "name": "FKInstantFunding-MT5-Bridge",
        "page": "app_pages/fk_instant_funding_bridge_status.py",
        "subtitle": "BeyondIQCapital -- DRY_RUN",
        "tag": "PAPIER",
    },
]

cols = st.columns(len(TILES))
for col, tile in zip(cols, TILES):
    entry = snapshot["bridges"].get(tile["name"], {})
    status = entry.get("status", "unknown")
    minutes = entry.get("minutes_since_last_run")
    with col:
        with st.container(border=True):
            badge = ":red[ECHTGELD]" if tile["tag"] == "ECHTGELD" else ":orange[PAPIER]"
            st.markdown(f"**{tile['name']}**  {badge}")
            st.caption(tile["subtitle"])
            st.metric("Status", status_pill(status))
            if minutes is not None:
                st.caption(f"Letzter Lauf vor {minutes:.0f} Min.")
            st.page_link(tile["page"], label="Details öffnen", icon=":material/arrow_forward:")
