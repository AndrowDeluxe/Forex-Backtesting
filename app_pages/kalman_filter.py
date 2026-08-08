"""Strategie Bestandteile -- Kalman-Filter Preprocessing.

Reine Baustein-/Demo-Seite fuer `strategy/kalman_filter.py`, bewusst
getrennt von jeder konkreten Strategie (insb. ADX-VWAP) -- dieser Filter
stammt aus einem komplett anderen Paper als die ADX-VWAP-These und soll
nicht mit ihr vermischt werden. Zeigt den Baustein isoliert an echten/
synthetischen Kursen, kein Backtest, keine Performance-Behauptung.

Quelle: Kili, Raouyane, Rachdi, Bellafkih (2025), "Kalman-Enhanced Deep
Reinforcement Learning for Noise-Resilient Algorithmic Trading in Volatile
Gold Markets", IJACSA Vol. 16, No. 11. Volle Einordnung inkl. Kritik an den
(nicht nachvollzogenen) Performance-Zahlen: siehe Paper-Research-Eintrag
"kili2025-kalman-drl-gold-xauusd".
"""

import altair as alt
import dukascopy_python
import pandas as pd

import streamlit as st
from strategy.data import PAIRS, generate_synthetic_ohlcv
from strategy.kalman_filter import kalman_smooth, rolling_zscore
from strategy.real_data import fetch_pair_history

st.set_page_config(
    page_title="Kalman-Filter -- Strategiebestandteile",
    page_icon=":material/filter_alt:",
    layout="wide",
)

REAL_DATA_START, REAL_DATA_END = "2016-07-28", "2026-07-28"
SYNTHETIC_START, SYNTHETIC_END, FREQ_MINUTES, SEED_BASE = "2023-01-01", "2026-01-01", 15, 42

SOURCE_REAL = "Real (Dukascopy H1, 2016-2026)"
SOURCE_SYNTHETIC = "Synthetic (validiert nur die Filter-Mechanik)"


@st.cache_data(ttl="1h", show_spinner="Lade Kursdaten...")
def load_raw(pair: str, source: str) -> pd.DataFrame:
    if source == SOURCE_REAL:
        return fetch_pair_history(pair, REAL_DATA_START, REAL_DATA_END, interval=dukascopy_python.INTERVAL_HOUR_1)
    return generate_synthetic_ohlcv(
        pair, start=SYNTHETIC_START, end=SYNTHETIC_END, freq_minutes=FREQ_MINUTES,
        seed=SEED_BASE + PAIRS.index(pair),
    )


@st.cache_data(ttl="1h", show_spinner="Wende Kalman-Filter an...")
def load_filtered(pair: str, source: str, measurement_noise_fraction: float) -> pd.DataFrame:
    df = load_raw(pair, source)
    out = df.copy()
    out["close_kalman"] = kalman_smooth(df["close"], measurement_noise_fraction=measurement_noise_fraction)
    out["daily_return"] = df["close"].pct_change()
    out["return_zscore"] = rolling_zscore(out["daily_return"], window=252)
    return out


st.markdown("## :material/filter_alt: Kalman-Filter -- Strategiebestandteile")
st.caption(
    "Quelle: Kili, Raouyane, Rachdi, Bellafkih (2025). \"Kalman-Enhanced Deep Reinforcement "
    "Learning for Noise-Resilient Algorithmic Trading in Volatile Gold Markets.\" IJACSA, "
    "16(11), 829-850."
)

st.warning(
    "**Dieses Paper wird NICHT als validierte Strategie nachgebaut.** Die berichteten Zahlen "
    "(Sharpe 10-13, Max-Drawdown <1,5%, 244-822% Performance-Verbesserung ueber nur 621 "
    "Out-of-Sample-Tage) sind fuer eine echte systematische Strategie unplausibel -- starker "
    "Verdacht auf Leakage/Overfitting, kein Raw-vs-Filtered-Ablationstest, IJACSA ist ein "
    "Journal mit niedriger Eingangshuerde. Die volle DQN/PPO/RPPO-Pipeline (48-72 GPU-Stunden "
    "pro Algorithmus laut Paper) wurde deshalb bewusst NICHT nachgebaut. Diese Seite extrahiert "
    "nur den sauberen, eigenstaendig pruefbaren Teil: die Kalman-Filter-Vorverarbeitung als "
    "Signal-Processing-Baustein, isoliert von jeder Handelsregel. Details: Paper-Research-Seite, "
    "Eintrag \"kili2025-kalman-drl-gold-xauusd\".",
    icon=":material/warning:",
)

st.markdown("### Die Idee, einfach erklaert")
st.markdown(
    "Jeder Kurs besteht aus zwei Teilen: einer echten Bewegung und kurzfristigem Rauschen "
    "(Bid/Ask-Geflacker, kleine zufaellige Ausschlaege). Der Kalman-Filter versucht, diese "
    "beiden Teile zu trennen. Bei jeder neuen Kerze fragt er sich: *\"Passt der neue Kurs zu "
    "meiner bisherigen Einschaetzung, oder ist das eher Rauschen?\"* -- und gewichtet die neue "
    "Beobachtung entsprechend. Stimmt der neue Kurs gut mit dem bisherigen Verlauf ueberein, "
    "vertraut er ihm stark; weicht er stark ab, verlaesst er sich mehr auf seine bisherige "
    "Schaetzung. Diese Gewichtung passt sich automatisch an: in ruhigen Phasen reagiert der "
    "Filter schneller, in nervoesen Phasen glaettet er staerker."
)
st.markdown(
    "Wichtig fuer den Einsatz in einer Strategie: der Filter schaut **nie in die Zukunft** -- "
    "jeder geglaettete Wert basiert nur auf Kursen bis zu diesem Zeitpunkt, genau wie ein "
    "gleitender Durchschnitt (nur intelligenter in der Gewichtung)."
)

st.info(
    "**Ein Regler steuert die Glaettungsstaerke:** `measurement_noise_fraction` (unten "
    "einstellbar). Nahe 1 = der Filter unterstellt viel Rauschen und glaettet stark. Nahe 0 = "
    "der Filter vertraut fast jedem neuen Kurs und glaettet kaum. Das Paper schaetzt diesen "
    "Wert mit einem aufwendigen statistischen Verfahren; dieser Baustein nutzt einen simplen, "
    "direkt nachvollziehbaren Regler statt einer Blackbox-Optimierung.",
    icon=":material/info:",
)

st.markdown("### Live-Demo: Rohkurs vs. gefilterter Kurs")

with st.sidebar:
    st.markdown("### Konfiguration")
    source = st.radio("Datenquelle", [SOURCE_REAL, SOURCE_SYNTHETIC], index=0)
    pair = st.selectbox("Pair", PAIRS, index=0)
    noise_fraction = st.slider(
        "Measurement-noise-fraction", 0.05, 0.95, 0.5, 0.05,
        help="Nahe 1 -> aggressive Glaettung (fast alle Varianz gilt als Rauschen). "
        "Nahe 0 -> Filter glaettet kaum.",
    )
    n_days = st.slider("Anzuzeigende Tage (Chart)", 5, 180, 30)

filtered = load_filtered(pair, source, noise_fraction)

raw_diff_var = filtered["close"].diff().var()
filtered_diff_var = filtered["close_kalman"].diff().var()
variance_reduction = 1 - (filtered_diff_var / raw_diff_var) if raw_diff_var else float("nan")
correlation = filtered["close"].corr(filtered["close_kalman"])

with st.container(horizontal=True):
    st.metric(
        "Rauschen reduziert um", f"{variance_reduction:.0%}", border=True,
        help="Wie viel Bar-zu-Bar-Schwankung der Filter herausgenommen hat.",
    )
    st.metric(
        "Aehnlichkeit zum Rohkurs", f"{correlation:.2f}", border=True,
        help="1.0 = identisch mit dem Rohkurs, 0 = kein Zusammenhang mehr. Bleibt meist nahe 1.",
    )

window = filtered.tail(int(n_days * (24 if source == SOURCE_REAL else 24 * 60 / FREQ_MINUTES))).reset_index(names="time")

with st.container(border=True):
    chart = (
        alt.Chart(window)
        .transform_fold(["close", "close_kalman"], as_=["series", "value"])
        .mark_line()
        .encode(
            x=alt.X("time:T", title="Zeit"),
            y=alt.Y("value:Q", title="Preis", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title="Serie",
                scale=alt.Scale(domain=["close", "close_kalman"], range=["#999999", "#f58518"]),
            ),
        )
        .properties(height=380)
    )
    st.altair_chart(chart)
    st.caption(
        "Grau = Rohkurs, Orange = Kalman-gefiltert. Kausale Glaettung -- kein Blick in die "
        "Zukunft, aber auch keine kostenlose Vorhersage: der Filter reagiert immer erst *nach* "
        "einer Bewegung."
    )

st.markdown("### Baustein 2: Rolling Z-Score Normalisierung")
st.markdown(
    "Zweiter, unabhaengiger Baustein: rechnet einen beliebigen Wert (z.B. eine Rendite oder "
    "einen Indikator) in \"wie ungewoehnlich ist das gerade, verglichen mit den letzten 252 "
    "Tagen\" um. Ein Wert von +2 heisst \"deutlich hoeher als ueblich\", -2 heisst \"deutlich "
    "niedriger\". Nuetzlich fuer Schwellenwerte, die in ruhigen und nervoesen Marktphasen "
    "gleichermassen sinnvoll bleiben sollen, statt in ruhigen Phasen zu eng und in nervoesen "
    "Phasen zu weit zu sein."
)
with st.container(border=True):
    zscore_chart = (
        alt.Chart(window)
        .mark_line(color="#4c78a8")
        .encode(
            x=alt.X("time:T", title="Zeit"),
            y=alt.Y("return_zscore:Q", title="Z-Score der Tagesrendite", scale=alt.Scale(zero=False)),
            tooltip=["time:T", alt.Tooltip("return_zscore:Q", format=".2f")],
        )
        .properties(height=260)
    )
    st.altair_chart(zscore_chart)
    st.caption("Beispiel: Tagesrendite von close, rollierend z-normalisiert (Fenster 252 Bars).")

st.markdown("### Wie diesen Baustein in einer eigenen Strategie nutzen")
st.code(
    "from strategy.kalman_filter import kalman_smooth, rolling_zscore\n\n"
    "df['close_kalman'] = kalman_smooth(df['close'], measurement_noise_fraction=0.5)\n"
    "df['feature_z'] = rolling_zscore(df['some_indicator'], window=252)",
    language="python",
)
st.warning(
    "**Wichtige Regel, egal in welcher Strategie:** der gefilterte Wert darf nur in die "
    "*Signal*-Bedingung einfliessen, niemals in die tatsaechliche Order-Ausfuehrung (Entry-/"
    "Exit-Preis, Stop, Target). Sonst simuliert der Backtest Fills gegen einen synthetischen "
    "Kurs, den es am echten Markt nie gab -- ein Realitaetsbruch, der genau in die Richtung "
    "geht, die die im Quell-Paper berichteten Zahlen unplausibel macht.",
    icon=":material/report:",
)

st.markdown("### Bereits getestet: ADX-VWAP Refined-Config")
st.error(
    "**`scripts/research_kalman_filter_adx_vwap.py`** hat genau das gemacht -- Kalman-"
    "gefilterte vs. rohe VWAP-Deviation, sonst identisches Setup, per jaehrlichem "
    "Walk-Forward (9 Jahres-Folds x 6 Paare) auf der besten bekannten ADX-VWAP-"
    "Konfiguration. **Ergebnis: keine Verbesserung, tendenziell schlechter mit staerkerer "
    "Glaettung** (Mean-Sharpe 0.235 roh vs. 0.215/0.228/0.096 bei noise_fraction "
    "0.3/0.5/0.7). Volle Zahlen und Einordnung: Strategie Bestandteile -> "
    "**ADX-VWAP Bausteine**. Ein Baustein, der in der Theorie sinnvoll klingt, ist keine "
    "automatische Verbesserung -- genau deshalb bleibt er hier eigenstaendig und muss "
    "pro Strategie separat nachgewiesen werden.",
    icon=":material/science:",
)

st.info(
    "**Naechster Schritt:** kein Backtest auf dieser Seite selbst -- bewusst getrennt "
    "gehalten von jeder konkreten Strategie. Wer den Filter in einer anderen Strategie "
    "(Auction Playbook, Checklist o.ae.) ausprobieren will, importiert "
    "`strategy.kalman_filter` direkt in die jeweilige Signal-Pipeline und vergleicht "
    "Backtest-Metriken mit/ohne Filter separat -- nicht auf dieser Seite vermischt.",
    icon=":material/hourglass_empty:",
)
