"""Strategie Bestandteile -- FX-Liquiditaetsfilter (Corwin-Schultz).

Baustein-/Demo-Seite fuer `bond_yield_indicator.friction`, isoliert von jeder
konkreten Strategie -- entstanden als Nebenprodukt des Bond-Yield-Spread-
Indikator-Projekts (dessen eigentliches Ergebnis inkonklusiv war, siehe
knowledge/projects/bond-yield-spread-indikator.md), aber dieser Baustein
haengt an KEINER Bond-Yield-Datenquelle und ist deshalb eigenstaendig nutzbar.

Kein Backtest hier, keine Performance-Behauptung -- reiner Baustein, siehe
Kalman-Filter-Seite fuer das gleiche Prinzip."""

import altair as alt
import pandas as pd

import streamlit as st
from bond_yield_indicator.friction import fetch_fx_friction

st.set_page_config(
    page_title="FX-Liquiditaetsfilter -- Strategiebestandteile",
    page_icon=":material/water_drop:",
    layout="wide",
)

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
START, END = "2016-01-01", "2026-08-07"


@st.cache_data(ttl="6h", show_spinner="Berechne Corwin-Schultz-Spread...")
def load_friction(pair: str) -> pd.Series:
    return fetch_fx_friction(pair, START, END)


st.markdown("## :material/water_drop: FX-Liquiditaetsfilter -- Strategiebestandteile")
st.caption(
    "Quelle: Corwin, S.A. & Schultz, P. (2012), \"A Simple Way to Estimate Bid-Ask Spreads "
    "From Daily High and Low Prices\", Journal of Finance 67(2). Genutzt in Yildirim (2024/2025, "
    "SSRN 6353258) als FX-Friktionsproxy fuer geldpolitische Spillover-Regressionen -- hier als "
    "eigenstaendiger Baustein extrahiert."
)

st.markdown("### Die Idee, einfach erklaert")
st.markdown(
    "Echte Geld-Brief-Spannen (Bid-Ask-Spreads) sind meist nicht direkt gespeichert -- die "
    "Datenhistorie hat nur OHLC-Kerzen. Corwin & Schultz zeigen: man kann den Spread trotzdem "
    "gut schaetzen, allein aus taeglichem High und Low. Die Intuition: das Tageshoch ist "
    "tendenziell eher ein Kauf-zum-Briefkurs, das Tagestief eher ein Verkauf-zum-Geldkurs -- die "
    "Handelsspanne enthaelt also selbst schon Spread-Information, kein Blick in echte Quotes "
    "noetig."
)
st.markdown(
    "Ein hoher Wert heisst: hohe Transaktionskosten, duennes Orderbuch, schlechte Liquiditaet "
    "gerade jetzt. Als Filter genutzt: Trades meiden (oder kleiner dimensionieren), wenn der "
    "Markt gerade in einem ungewoehnlich illiquiden Zustand ist -- unabhaengig vom eigentlichen "
    "Handelssignal."
)

st.info(
    "**Kein neuer Datenbedarf:** rechnet nur auf den ohnehin schon gecachten FX-D1-Kursen "
    "(`combined_strategy.data`) -- im Gegensatz zum Rest des Bond-Yield-Spread-Projekts, das an "
    "fehlenden taeglichen Anleihe-Renditen fuer 6 der 7 Laender haengt.",
    icon=":material/info:",
)

st.markdown("### Live-Demo: gemessene Friktion pro Paar")

pair = st.selectbox("Pair", PAIRS, index=0)
n_days = st.slider("Anzuzeigende Tage", 60, 750, 250)

spread = load_friction(pair).dropna()
window = spread.tail(n_days).reset_index()
window.columns = ["date", "spread"]

roll_median = spread.rolling(250, min_periods=60).median().iloc[-1]

with st.container(horizontal=True):
    st.metric(
        "Aktueller Wert (letzter Tag)", f"{spread.iloc[-1]:.4%}", border=True,
        help="Proportionaler Bid-Ask-Spread, geschaetzt aus dem letzten verfuegbaren Tag.",
    )
    st.metric(
        "Rollierender Median (250 Tage)", f"{roll_median:.4%}", border=True,
        help="Typisches Friktionsniveau der letzten ~1 Jahr -- Referenzwert fuer 'normal'.",
    )

with st.container(border=True):
    chart = (
        alt.Chart(window)
        .mark_line(color="#4c78a8")
        .encode(
            x=alt.X("date:T", title="Datum"),
            y=alt.Y("spread:Q", title="Corwin-Schultz Spread (proportional)", axis=alt.Axis(format="%")),
            tooltip=["date:T", alt.Tooltip("spread:Q", format=".4%")],
        )
        .properties(height=320)
    )
    rule = alt.Chart(pd.DataFrame({"y": [roll_median]})).mark_rule(color="#999", strokeDash=[4, 4]).encode(y="y:Q")
    st.altair_chart(chart + rule)
    st.caption(
        "Blau = taegliche geschaetzte Friktion. Graue Linie = rollierender 250-Tage-Median als "
        "Referenz fuer 'normales' Niveau."
    )

st.markdown("### Wie diesen Baustein in einer eigenen Strategie nutzen")
st.code(
    "from bond_yield_indicator.friction import fetch_fx_friction\n\n"
    "friction = fetch_fx_friction('EURUSD', start, end)\n"
    "roll_max = friction.rolling(250, min_periods=60).max()\n"
    "roll_min = friction.rolling(250, min_periods=60).min()\n"
    "friction_norm = ((friction - roll_min) / (roll_max - roll_min)).clip(0, 1)\n"
    "# Trades meiden/kleiner dimensionieren, wenn friction_norm hoch ist (z.B. > 0.8)\n"
    "gate = (1 - friction_norm)  # Gewichtsfaktor 0..1, wie im Composite-Indikator genutzt",
    language="python",
)

st.success(
    "**Validiert an der Gold Asian-Range Breakout (2026-08-11).** Gegen den vollen "
    "Produktions-Stack (ADX+Trend-Bias+Delay+Silver) getestet -- besteht BEIDE Rigor-Checks, "
    "die auch die 4 bestehenden Produktionsfilter durchlaufen mussten: Structure-Preserving-"
    "Randomisierung (p=0.000 unter Rotation UND Run-Permutation, n=1000 Shuffles je Methode) "
    "und expandierendes Walk-Forward (in 6/6 Testjahren 2021-2026 auf Train-Only-Daten "
    "bestaetigt, mittlere Profit-Factor-Anhebung 1.463 -> 2.267). Staerkster validierter "
    "Filterkandidat aus dem gesamten Bond-Yield-Spread-Indikator-Projekt -- staerker als 2 der "
    "4 aktuellen Produktionsfilter. Baustein liegt bereits in `asian_range_breakout/filters.py"
    "::attach_gold_liquidity`/`apply_gold_liquidity_filter`, ist aber noch NICHT in den "
    "angezeigten Produktions-Stack verdrahtet -- offene Entscheidung. Details: "
    "`scripts/research_gold_liquidity_event_filters.py`.",
    icon=":material/verified:",
)
st.info(
    "**Fuer andere Strategien weiterhin ein ungetesteter Kandidat.** Naheliegend fuer jede "
    "FX-Strategie im Repo (z.B. Gap-Fade, Triple-MA, ORB), aber noch nicht dort durchgerechnet "
    "-- gleiche Regel wie beim Kalman-Filter: separat pro Strategie nachweisen.",
    icon=":material/science:",
)
