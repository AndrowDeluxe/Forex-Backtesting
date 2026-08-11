"""Strategie Bestandteile -- Notenbank-Event-Window-Filter.

Baustein-/Demo-Seite fuer `bond_yield_indicator.calendar`, isoliert von jeder
konkreten Strategie -- entstanden als Nebenprodukt des Bond-Yield-Spread-
Indikator-Projekts (siehe knowledge/projects/bond-yield-spread-indikator.md),
aber dieser Baustein haengt an keiner Bond-Yield-Zeitreihe, nur an den
Notenbank-Kalendern -- eigenstaendig nutzbar.

Kein Backtest hier, keine Performance-Behauptung -- reiner Baustein, siehe
Kalman-Filter-Seite fuer das gleiche Prinzip."""

import altair as alt
import pandas as pd

import streamlit as st
from bond_yield_indicator.calendar import BANKS, event_window_dummy, get_meetings

st.set_page_config(
    page_title="Notenbank-Event-Window -- Strategiebestandteile",
    page_icon=":material/event:",
    layout="wide",
)

st.markdown("## :material/event: Notenbank-Event-Window-Filter -- Strategiebestandteile")
st.caption(
    "Quelle: Yildirim (2024/2025, SSRN 6353258), Section 4-5 -- die eigentliche Kernaussage "
    "dieses Papers, unabhaengig vom (inkonklusiven) Bond-Yield-Spread-Indikator-Ergebnis: "
    "3-Tage-Fenster um Notenbank-Ankuendigungen erklaeren einen ueberproportionalen Anteil der "
    "Bewegung; ausserhalb der Fenster 'washen Renditeaenderungen aus' (transitorisch)."
)

st.markdown("### Die Idee, einfach erklaert")
st.markdown(
    "`D_bank_t` ist eine simple Dummy-Variable: 1 am Tag vor, am Tag von und am Tag nach einer "
    "Notenbank-Sitzung, sonst 0. Das Paper zeigt fuer Staatsanleihe-Renditen: fast die gesamte "
    "langfristige Bewegung passiert in genau diesen schmalen Fenstern, nicht gleichmaessig "
    "verteilt ueber die Zeit. Als Timing-Filter fuer eine Handelsstrategie lassen sich daraus "
    "zwei GEGENSAETZLICHE Hypothesen ableiten, die beide eine eigene Backtest-Pruefung "
    "verdienen:"
)
st.markdown(
    "- **Meiden**: Trades in den Fenstern aussetzen (News-Risk-Vermeidung -- klassische Logik: "
    "Spreads weiten sich, Slippage steigt, Ausschlaege sind schwerer zu handeln).\n"
    "- **Bevorzugen**: Breakouts INNERHALB der Fenster hoeher gewichten, weil laut Paper genau "
    "dort die 'echte', nicht mean-reversion-anfaellige Bewegung stattfindet."
)

st.info(
    "**Kein neuer Datenbedarf fuer die Kalenderdaten selbst:** 1483 Termine (FOMC + ECB/BoE/"
    "BoJ/BoC/SNB/RBA) liegen als statische, git-versionierte CSVs in "
    "`bond_yield_indicator/calendars/` -- unabhaengig von den (fuer 6 von 7 Laendern nur "
    "monatlichen) Anleihe-Renditedaten, die den Rest des Projekts eingeschraenkt haben.",
    icon=":material/info:",
)

st.markdown("### Live-Demo: Termine je Notenbank")

cols = st.columns(len(BANKS))
for col, bank in zip(cols, BANKS):
    meetings = get_meetings(bank)
    with col:
        st.metric(bank, len(meetings), border=True,
                   help=f"{meetings.min().date()} .. {meetings.max().date()}" if len(meetings) else "keine Daten")

st.caption(
    "Bekannte Luecke: die 6 auslaendischen Kalender enden 2024 (Paper-Appendix-Stand), FOMC "
    "reicht bis Ende 2026 (separat gescraped). Fortschreiben = Zeilen an die CSVs anhaengen, "
    "kein Code-Aenderung."
)

window_start, window_end = "2024-01-01", "2026-12-31"
grid = pd.date_range(window_start, window_end, freq="D")
rows = []
for bank in BANKS:
    dummy = event_window_dummy(bank, grid, window_days=1)
    for d in dummy[dummy == 1].index:
        rows.append({"bank": bank, "date": d})
rug = pd.DataFrame(rows)

with st.container(border=True):
    chart = (
        alt.Chart(rug)
        .mark_tick(thickness=2, height=18)
        .encode(
            x=alt.X("date:T", title="Datum", scale=alt.Scale(domain=[window_start, window_end])),
            y=alt.Y("bank:N", title="Notenbank", sort=BANKS),
            color=alt.Color("bank:N", legend=None),
            tooltip=["bank:N", "date:T"],
        )
        .properties(height=220)
    )
    st.altair_chart(chart)
    st.caption(f"3-Tage-Event-Fenster je Notenbank, {window_start} .. {window_end}.")

st.markdown("### Wie diesen Baustein in einer eigenen Strategie nutzen")
st.code(
    "from bond_yield_indicator.calendar import event_window_dummy\n\n"
    "# trades: DataFrame mit 'entry_time' (o.ae.), date_index = trades['entry_time'].dt.normalize()\n"
    "is_event = event_window_dummy('FOMC', date_index, window_days=1)\n"
    "# Variante A (meiden):     trades = trades[~is_event.to_numpy()]\n"
    "# Variante B (bevorzugen): trades = trades[is_event.to_numpy()]",
    language="python",
)

st.error(
    "**Getestet an der Gold Asian-Range Breakout (2026-08-11): kein Edge.** Gegen den vollen "
    "Produktions-Stack (ADX+Trend-Bias+Delay+Silver), FOMC-3-Tage-Fenster, beide Richtungen "
    "(meiden UND bevorzugen) -- Structure-Preserving-Randomisierung ergibt in beiden Faellen "
    "p=0.42-0.62 unter Rotation UND Run-Permutation, klar nicht von einem beliebigen "
    "gleich-foermigen Platzierungsmuster unterscheidbar. Nur 24 von 310 Trades fallen ueberhaupt "
    "in ein FOMC-Fenster -- moeglicherweise auch ein Power-Problem bei so kleiner Stichprobe, "
    "nicht zwingend Beweis der Nullhypothese. Details: "
    "`scripts/research_gold_liquidity_event_filters.py`. Zum Vergleich: der "
    "Liquiditaetsfilter auf der Nachbarseite bestand denselben Test klar (p=0.000).",
    icon=":material/cancel:",
)
st.info(
    "**Fuer andere Strategien weiterhin ein ungetesteter Kandidat.** Naheliegend fuer andere "
    "Breakout-Strategien (ORB, Presettle-Breakout) mit groesserer Trade-Anzahl -- gleiche Regel "
    "wie beim Kalman-Filter: separat pro Strategie nachweisen.",
    icon=":material/science:",
)
