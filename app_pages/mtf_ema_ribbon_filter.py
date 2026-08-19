"""Strategie Bestandteile -- Multi-Timeframe EMA Ribbon Trendfilter.

Baustein-/Demo-Seite fuer `strategy/mtf_ema_ribbon.py`, isoliert von jeder
konkreten Strategie -- gleiches Prinzip wie die Kalman-Filter-Seite: reine
Anzeige des Bausteins an echten Kursen, kein Backtest, keine
Performance-Behauptung.

Quelle: vom Nutzer bereitgestelltes TradingView-Pine-Script-v6-Indikator
("Custom MTF EMA Ribbon") -- vier EMAs auf hoeheren Zeitrahmen als der
Chart (Standard: 4H-50, 1D-50, 1W-50, 1D-200), per
`request.security(..., lookahead=barmerge.lookahead_off)`. Die
Richtungs-Filter-Logik (`ribbon_bias`/`apply_mtf_ribbon_filter`) ist eine
hier hinzugefuegte Interpretation, nicht Teil des Original-Scripts, das
selbst nur die vier Linien plottet.
"""

import altair as alt
import dukascopy_python
import pandas as pd

import streamlit as st
from strategy.data import PAIRS
from strategy.mtf_ema_ribbon import DEFAULT_LEVELS, attach_mtf_ema_ribbon, ribbon_bias
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="MTF EMA Ribbon -- Strategiebestandteile",
    page_icon=":material/multiline_chart:",
    layout="wide",
)

START, END = "2016-07-28", "2026-07-28"

LEVEL_COLORS = {
    "ema_4h_50": "#eeca3b",
    "ema_1d_50": "#f58518",
    "ema_1w_50": "#b279a2",
    "ema_1d_200": "#e45756",
}
LEVEL_TITLES = {
    "ema_4h_50": "EMA 1 -- 4H-50",
    "ema_1d_50": "EMA 2 -- 1D-50",
    "ema_1w_50": "EMA 3 -- 1W-50",
    "ema_1d_200": "EMA 4 -- 1D-200",
}
BIAS_LABELS = {1: "Bullisch (Kurs > alle EMAs)", -1: "Baerisch (Kurs < alle EMAs)", 0: "Gemischt / keine Bias"}
BIAS_COLORS = {1: "#54a24b", -1: "#e45756", 0: "#b0b0b0"}


@st.cache_data(ttl="6h", show_spinner="Lade H1-Kurse und berechne Ribbon...")
def load_ribbon(pair: str) -> pd.DataFrame:
    raw = fetch_pair_history(pair, START, END, interval=dukascopy_python.INTERVAL_HOUR_1)
    df = attach_mtf_ema_ribbon(raw[["close"]], levels=DEFAULT_LEVELS)
    df["bias"] = ribbon_bias(df, levels=DEFAULT_LEVELS)
    return df


st.markdown("## :material/multiline_chart: MTF EMA Ribbon -- Strategiebestandteile")
st.caption(
    "Quelle: vom Nutzer bereitgestelltes TradingView Pine-Script-v6-Indikator "
    "(\"Custom MTF EMA Ribbon\") -- vier EMAs auf hoeheren Zeitrahmen als der Chart, "
    "Standardwerte 4H-50 / 1D-50 / 1W-50 / 1D-200."
)

st.markdown("### Die Idee, einfach erklaert")
st.markdown(
    "Statt eines EMA auf dem eigenen Chart-Zeitrahmen legt dieser Baustein mehrere EMAs "
    "von **hoeheren** Zeitrahmen uebereinander -- die \"Ribbon\" (Band) genannte Optik "
    "zeigt auf einen Blick, ob sich der Markt kurz-, mittel- und langfristig im selben "
    "Trend befindet oder ob die Zeitebenen widersprechen. Jede EMA wird auf ihrem eigenen "
    "Zeitrahmen berechnet (z.B. die 1W-EMA nur aus Wochenkerzen) und dann auf den "
    "Chart-Zeitrahmen projiziert -- aber nur mit dem Wert der zuletzt **abgeschlossenen** "
    "HTF-Kerze, nie mit einer noch laufenden. Das entspricht `barmerge.lookahead_off` im "
    "Original-Script und wird hier ueber ein no-lookahead `merge_asof`-Backward-Join "
    "nachgebaut (gleiches Muster wie `ema_strategy.data.attach_htf_bias`, nur fuer vier "
    "Zeitebenen gleichzeitig statt einer)."
)
st.markdown(
    "Als Filter genutzt: **long nur, wenn der Kurs ueber allen vier EMAs steht** (voll "
    "bullischer Stack), **short nur, wenn er unter allen vier steht** -- widersprechen "
    "sich die Zeitebenen (Kurs liegt zwischen den Linien), gilt das als neutral und der "
    "Filter blockiert Trades in beide Richtungen. Diese Lesart stammt nicht aus dem "
    "Original-Script (das nur die Linien plottet), sondern ist eine naheliegende, aber "
    "eigene Ergaenzung, genau wie beim Kalman-Filter-Baustein."
)

st.info(
    "**Kein neuer Datenbedarf:** rechnet direkt auf den ohnehin gecachten FX-H1-Kursen "
    "(`strategy.real_data`) -- die hoeheren Zeitrahmen werden per Pandas-Resampling "
    "daraus abgeleitet, kein zusaetzlicher Datenfeed noetig.",
    icon=":material/info:",
)

st.markdown("### Live-Demo: Ribbon + Bias auf echten Kursen")

with st.sidebar:
    st.markdown("### Konfiguration")
    pair = st.selectbox("Pair", PAIRS, index=0)
    visible_levels = st.multiselect(
        "Angezeigte EMAs", list(LEVEL_TITLES.keys()),
        default=list(LEVEL_TITLES.keys()), format_func=lambda k: LEVEL_TITLES[k],
    )
    n_days = st.slider("Anzuzeigende Tage (Chart)", 30, 730, 180)

df = load_ribbon(pair)
window = df.tail(n_days * 24).reset_index(names="time")

current_bias = int(df["bias"].iloc[-1])
bias_counts = df["bias"].value_counts(normalize=True)

with st.container(horizontal=True):
    st.metric(
        "Aktuelle Bias (letzter H1-Bar)", BIAS_LABELS[current_bias], border=True,
        help="Basierend auf dem letzten abgeschlossenen H1-Schlusskurs relativ zu allen vier Ribbon-EMAs.",
    )
    st.metric(
        "Bullisch (Anteil Historie)", f"{bias_counts.get(1, 0.0):.0%}", border=True,
        help="Anteil der H1-Bars seit 2016, an denen der Kurs ueber allen vier EMAs stand.",
    )
    st.metric(
        "Baerisch (Anteil Historie)", f"{bias_counts.get(-1, 0.0):.0%}", border=True,
        help="Anteil der H1-Bars seit 2016, an denen der Kurs unter allen vier EMAs stand.",
    )

with st.container(border=True):
    base = alt.Chart(window).encode(x=alt.X("time:T", title="Zeit"))
    price_line = base.mark_line(color="#999999", strokeWidth=1.5).encode(
        y=alt.Y("close:Q", title="Preis", scale=alt.Scale(zero=False)),
        tooltip=["time:T", alt.Tooltip("close:Q", format=".5f")],
    )
    ema_lines = [
        base.mark_line(color=LEVEL_COLORS[col], strokeWidth=2).encode(
            y=alt.Y(f"{col}:Q", scale=alt.Scale(zero=False)),
            tooltip=["time:T", alt.Tooltip(f"{col}:Q", format=".5f", title=LEVEL_TITLES[col])],
        )
        for col in visible_levels
    ]
    chart = price_line
    for line in ema_lines:
        chart = chart + line
    st.altair_chart(chart.properties(height=420))
    legend_parts = ["Grau = Kurs"] + [f"{c} = {LEVEL_TITLES[col]}" for col, c in LEVEL_COLORS.items() if col in visible_levels]
    st.caption(" -- ".join(legend_parts))

with st.container(border=True):
    bias_chart = (
        alt.Chart(window)
        .mark_area(interpolate="step-after", opacity=0.7)
        .encode(
            x=alt.X("time:T", title="Zeit"),
            y=alt.Y("bias:Q", title="Bias", scale=alt.Scale(domain=[-1, 1])),
            color=alt.Color(
                "bias:N", title="Bias",
                scale=alt.Scale(domain=[-1, 0, 1], range=[BIAS_COLORS[-1], BIAS_COLORS[0], BIAS_COLORS[1]]),
                legend=None,
            ),
            tooltip=["time:T", "bias:N"],
        )
        .properties(height=120)
    )
    st.altair_chart(bias_chart)
    st.caption("Gruen = bullischer Stack (+1), Rot = baerischer Stack (-1), Grau = gemischt/keine Bias (0).")

st.markdown("### Wie diesen Baustein in einer eigenen Strategie nutzen")
st.code(
    "from strategy.mtf_ema_ribbon import (\n"
    "    attach_mtf_ema_ribbon, ribbon_bias, apply_mtf_ribbon_filter,\n"
    ")\n\n"
    "# df braucht eine 'close'-Spalte und einen DatetimeIndex (z.B. H1)\n"
    "df = attach_mtf_ema_ribbon(df)          # + ema_4h_50, ema_1d_50, ema_1w_50, ema_1d_200\n"
    "bias = ribbon_bias(df)                  # -1 / 0 / +1 je Bar\n\n"
    "# position: eigene Signal-Positionsserie (-1/0/1) VOR dem Filter\n"
    "position = apply_mtf_ribbon_filter(position, bias)  # blockt Trades gegen die Ribbon-Bias",
    language="python",
)
st.warning(
    "**Genuegend HTF-Historie einplanen:** die 1W-50-EMA braucht ~50 Wochen, die 1D-200-EMA "
    "~200 Handelstage, bevor sie sich eingeschwungen hat -- `ribbon_bias` liefert vorher "
    "einfach 0 (neutral, kein Trade), aber ein Backtest sollte diese Anlaufphase nicht als "
    "echte Trade-Ablehnung des Filters fehlinterpretieren.",
    icon=":material/report:",
)

st.info(
    "**Noch ungetesteter Kandidat.** Diese Seite zeigt nur den Baustein isoliert an echten "
    "Kursen -- noch nicht gegen eine konkrete Strategie im Repo durchgerechnet. Gleiche Regel "
    "wie beim Kalman-Filter und den beiden anderen Filter-Bausteinen: separat pro Strategie "
    "per Backtest (idealerweise mit Structure-Preserving-Randomisierung und Walk-Forward, "
    "siehe Nachbarseiten) nachweisen, bevor er produktiv verdrahtet wird.",
    icon=":material/science:",
)
