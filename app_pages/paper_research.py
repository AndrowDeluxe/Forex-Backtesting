"""Paper Research -- automatisch gefundene/eingereichte Strategie-Papers,
extrahierte Regeln und (wo moeglich) Auto-Backtest-Ergebnisse.

Liest NUR aus `paper_research_cache/` (befuellt von
`scripts/research_paper_pipeline.py`, manuell gestartet) -- kein Live-API-Call
beim Laden dieser Seite, damit kein ANTHROPIC_API_KEY im Cloud-Deploy noetig
ist. Wenn die Pipeline noch nie gelaufen ist, ist der Cache leer und die Seite
zeigt nur einen Hinweis dazu.
"""

import pandas as pd
import streamlit as st

from paper_research import store

st.set_page_config(page_title="Paper Research", page_icon=":material/travel_explore:", layout="wide")

st.markdown("## :material/travel_explore: Paper Research")
st.caption(
    "Automatisch per arXiv-API gefundene Strategie-Papers (q-fin.TR/ST/PM) plus manuell "
    "in `paper_dropbox/` abgelegte PDFs (z.B. von SSRN, wo es keine offizielle API gibt) -- "
    "von Claude strukturiert extrahiert, einfache Signal-Strategien automatisch gebacktestet."
)

records = store.load_all_records()

if not records:
    st.info(
        "Noch keine Papers verarbeitet. Lokal `python scripts/research_paper_pipeline.py` "
        "ausfuehren (braucht `ANTHROPIC_API_KEY` als Umgebungsvariable) -- Ergebnisse landen "
        "in `paper_research_cache/` und erscheinen danach hier.",
        icon=":material/hourglass_empty:",
    )
    st.stop()

single_records = [r for r in records if r.spec.source != "combo"]
combo_records = [r for r in records if r.spec.source == "combo"]

overview_rows = []
for rec in single_records:
    row = {
        "Titel": rec.spec.title,
        "Quelle": rec.spec.source,
        "Komplexitaet": rec.spec.complexity,
        "Asset-Klasse": rec.spec.asset_class,
        "Timeframe": rec.spec.timeframe,
    }
    if rec.backtest_metrics:
        row["Trades"] = rec.backtest_metrics.get("n_trades")
        row["Sharpe"] = rec.backtest_metrics.get("sharpe")
        row["Profit Factor"] = rec.backtest_metrics.get("profit_factor")
    elif rec.backtest_error:
        row["Trades"] = None
        row["Sharpe"] = None
        row["Profit Factor"] = None
    overview_rows.append(row)

st.markdown(f"### Uebersicht ({len(single_records)} verarbeitete Papers)")
st.dataframe(pd.DataFrame(overview_rows), width="stretch", hide_index=True)

st.markdown("### Details pro Paper")
for rec in single_records:
    spec = rec.spec
    with st.expander(f"{spec.title} ({spec.source}:{spec.source_id})"):
        col_spec, col_result = st.columns(2)

        with col_spec:
            st.markdown("**Extrahierte Regeln**")
            st.markdown(f"- Asset-Klasse: {spec.asset_class or '-'}")
            st.markdown(f"- Timeframe: {spec.timeframe or '-'}")
            st.markdown(f"- Indikatoren: {', '.join(spec.indicators) if spec.indicators else '-'}")
            st.markdown(f"- Richtung: {spec.direction}")
            st.markdown(f"- Entry: {spec.entry_rule_text or '-'}")
            st.markdown(f"- Exit: {spec.exit_rule_text or '-'}")
            st.markdown(f"- Risk: {spec.risk_rule_text or '-'}")
            if spec.session_filter:
                st.markdown(f"- Session-Filter: {spec.session_filter}")
            if spec.claimed_performance:
                st.markdown(f"- Im Paper berichtete Performance: {spec.claimed_performance}")
            if spec.notes:
                st.caption(spec.notes)

        with col_result:
            st.markdown("**Auto-Backtest**")
            if spec.complexity != "simple_signal":
                st.warning(
                    "Als 'stateful' eingestuft -- braucht manuelle Rekonstruktion "
                    "(wie Auction Playbook, CLS Advanced etc. bisher), kein automatischer "
                    "Backtest moeglich.",
                    icon=":material/build:",
                )
            elif rec.backtest_metrics:
                m = rec.backtest_metrics
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Trades", m.get("n_trades"))
                mc2.metric("Sharpe", f"{m.get('sharpe', 0):.2f}" if m.get("sharpe") is not None else "-")
                mc3.metric(
                    "Profit Factor",
                    f"{m.get('profit_factor', 0):.2f}" if m.get("profit_factor") is not None else "-",
                )
                st.caption(
                    "Generischer ATR-Stop/Target-Backtest auf EUR/USD M15 (2016-2026) als "
                    "Screening-Proxy -- nicht zwingend das im Paper genannte Asset/Timeframe. "
                    "Ehrlich einordnen, nicht als validierte Edge ueberverkaufen."
                )
            elif rec.backtest_error:
                st.warning(f"Kein Auto-Backtest moeglich: {rec.backtest_error}", icon=":material/block:")

st.markdown(f"### Stufe 2: Kombinationsvorschlaege ({len(combo_records)})")
st.caption(
    "Kombiniert je einen Entry-Baustein aus zwei verschiedenen Papers (gleiche Richtung, "
    "unterschiedlicher Indikator) und backtestet die Kombination automatisch -- nur moeglich "
    "fuer Papers, die als 'simple_signal' eingestuft wurden, da nur deren Regeln strukturiert "
    "vorliegen."
)
if not combo_records:
    st.info(
        "Noch keine Kombinationsvorschlaege -- braucht mindestens 2 als 'simple_signal' "
        "eingestufte Papers aus unterschiedlichen Quellen.",
        icon=":material/hourglass_empty:",
    )
else:
    combo_rows = []
    for rec in combo_records:
        row = {"Kombination": rec.spec.title, "Entry-Regel": rec.spec.entry_rule_text}
        if rec.backtest_metrics:
            row["Trades"] = rec.backtest_metrics.get("n_trades")
            row["Sharpe"] = rec.backtest_metrics.get("sharpe")
            row["Profit Factor"] = rec.backtest_metrics.get("profit_factor")
        else:
            row["Trades"] = row["Sharpe"] = row["Profit Factor"] = None
        combo_rows.append(row)
    st.dataframe(pd.DataFrame(combo_rows), width="stretch", hide_index=True)
