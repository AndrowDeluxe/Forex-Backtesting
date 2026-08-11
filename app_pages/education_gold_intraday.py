"""Education-Track: Gold-Intraday-Strategie aus SSRN-Papers.

Ausgelagert aus `education.py` (2026-08-10), das jetzt eine Hub-Seite mit
Kacheln ist. Einziger Track bisher: eine Gold-Intraday-Strategie ausgehend
von SSRN-Papers aufbauen, mit derselben Disziplin wie der Rest des Repos
(Paper Research Pipeline, echte Daten, Out-of-Sample-Check, Kosten-
Sensitivitaet, ehrlicher Befund). Fortschritt (angehakte Schritte) wird in
`education_state/checklist_state.json` gespeichert (gitignored, rein lokal),
damit die Liste ueber mehrere Sessions/Tage hinweg erhalten bleibt -- kein
Multi-User-Zustand, nur ein einfacher Fortschritts-Spiegel auf Platte.
"""

import json
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="Education -- Gold-Intraday-Strategie", page_icon=":material/candlestick_chart:", layout="wide"
)

STATE_DIR = Path("education_state")
STATE_FILE = STATE_DIR / "checklist_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def on_check_change(item_key: str) -> None:
    state = load_state()
    state[item_key] = st.session_state[item_key]
    save_state(state)


st.page_link("app_pages/education.py", label="Zurueck zu Education", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/candlestick_chart: Gold-Intraday-Strategie aus SSRN-Papers")
st.caption(
    "Ziel: von einer SSRN-Literaturrecherche zu einem ehrlich getesteten "
    "Gold-Intraday-Signal kommen, nach demselben Muster wie die anderen "
    "Strategien in diesem Repo (siehe `asian_range_breakout/`, `paper_research/`)."
)

st.space("medium")

with st.expander(":material/search: Referenz: SSRN-Suchbegriffe (Schritt 1)", icon=":material/search:"):
    st.markdown(
        """
**Intraday-Saisonalitaet / Handelszeiten-Effekte**
- `"gold intraday seasonality"`
- `"time of day effect" gold futures`
- `"London fixing" gold return predictability`
- `"overnight return" gold "intraday return"`
- `COMEX gold trading session effects`

**Order Flow / Market Microstructure**
- `"order flow" gold futures microstructure`
- `"price discovery" gold COMEX London`
- `"informed trading" precious metals futures`
- `VWAP execution gold futures`

**Makro-News-Reaktion (event-driven)**
- `gold price reaction FOMC announcement`
- `"macroeconomic news" gold intraday volatility`
- `nonfarm payrolls gold futures reaction`
- `real yields gold intraday relationship`
- `"surprise index" gold price response`

**Cross-Asset / verknuepfte Signale**
- `DXY dollar index gold intraday lead-lag`
- `"safe haven" flows gold equity volatility VIX`
- `gold silver ratio intraday mean reversion`
- `real interest rates TIPS gold short-term dynamics`

**Mean-Reversion / Momentum**
- `"intraday momentum" commodity futures`
- `"mean reversion" gold futures high frequency`
- `"opening range breakout" futures strategy`
- `overnight-intraday momentum spillover commodities`

**Volatilitaet / Timing**
- `"volatility clustering" gold intraday`
- `realized volatility gold futures forecasting`
- `"intraday seasonality" volatility precious metals`

**Suchtipps:** Filter "Financial Economics" -> "Market Microstructure" oder
"Futures & Derivatives"; sortieren nach "Recently Added" oder "Downloads";
Begriffe kombinieren, z.B. `"gold" AND "intraday" AND ("momentum" OR "mean reversion")`.
Da SSRN keine offizielle API hat, PDFs manuell in `paper_dropbox/` ablegen --
die Pipeline verarbeitet sie identisch zu arXiv-Funden.
        """
    )

st.space("small")

PHASES: list[tuple[str, str, list[tuple[str, str]]]] = [
    (
        "phase1",
        ":material/search: Phase 1 -- Recherche",
        [
            ("p1_1", "Alle 6 Suchbegriff-Kategorien oben auf SSRN durchgehen"),
            ("p1_2", "Pro Kategorie 2-3 vielversprechende Paper sammeln (Titel/Abstract/Link notieren)"),
            ("p1_3", "PDFs herunterladen"),
        ],
    ),
    (
        "phase2",
        ":material/upload_file: Phase 2 -- Papers teilen & sichten",
        [
            ("p2_1", "Papers direkt im Chat teilen, pro Themenkategorie (PDF/Link/Textauszug)"),
            ("p2_2", "Claude liest sie direkt in der Session -- keine `research_paper_pipeline.py`/API-Key noetig"),
            ("p2_3", "Pro Paper: Kernthese, Regeln, Timeframe, behauptete Performance kurz zusammenfassen"),
        ],
    ),
    (
        "phase3",
        ":material/filter_alt: Phase 3 -- Erstes Screening",
        [
            ("p3_1", "Pro Paper einordnen: einfaches Signal (AND-Bedingungen) vs. echte State-Machine"),
            ("p3_2", "Plausibilitaet der Kernthese fuer Gold-Intraday grob abschaetzen (vor jedem Code)"),
            ("p3_3", "Vielversprechendste 2-3 Kandidaten auswaehlen -- nicht alle parallel vertiefen"),
            ("p3_4", "Duennes/unklares Extraktionsmaterial aussortieren, bevor Zeit in den Nachbau geht"),
        ],
    ),
    (
        "phase4",
        ":material/construction: Phase 4 -- Vertiefung je Kandidat",
        [
            ("p4_1", "Eigenes Backend-Package anlegen (Muster: `asian_range_breakout/`)"),
            ("p4_2", "Echte Gold-Daten nutzen (Dukascopy XAUUSD, nicht nur den Screening-Proxy)"),
            ("p4_3", "Regeln 1:1 aus dem Paper umsetzen -- keine frei erfundenen Parameter"),
        ],
    ),
    (
        "phase5",
        ":material/merge: Phase 5 -- Kombination mit vorhandenen Bausteinen",
        [
            ("p5_1", "Kalman-Filter (`strategy/kalman_filter.py`) testen -- hilft/schadet?"),
            ("p5_2", "ADX-Filter / VWAP-Deviation aus `strategy/indicators.py` pruefen"),
            ("p5_3", "EMA200-Regimefilter (aus `ou_paper_backtest/`) als Marktregime-Gate testen"),
            ("p5_4", "Session-/Uhrzeit-Filter testen (Muster: CLS-Squeeze, Asian-Range-Breakout)"),
        ],
    ),
    (
        "phase6",
        ":material/verified: Phase 6 -- Robustheit",
        [
            ("p6_1", "Walk-Forward oder echter Out-of-Sample-Split (anderer Zeitraum als beim Fitting!)"),
            ("p6_2", "Monte-Carlo-Bootstrap der Trade-Sequenz (Muster: `ou_paper_backtest/monte_carlo.py`)"),
            ("p6_3", "Kosten-Sensitivitaet: Spread/Slippage bis zum Breakeven sweepen"),
            ("p6_4", "Mehrere Jahre/Marktregime pruefen, nicht nur ein gutes Jahr"),
        ],
    ),
    (
        "phase7",
        ":material/fact_check: Phase 7 -- Dokumentation & Dashboard",
        [
            ("p7_1", "Ehrlichen Befund festhalten -- auch wenn negativ"),
            ("p7_2", "Bei robustem Fund: eigene `app_pages/*.py`-Seite + Karte auf `home.py`"),
            ("p7_3", "Vor jedem Commit/Push mit dem User abstimmen (Repo-Konvention)"),
        ],
    ),
    (
        "phase8",
        ":material/pause_circle: Phase 8 -- Danach (separat, erst auf Zuruf)",
        [
            ("p8_1", "Live-/Demo-Vorbereitung -- eigenes Thema, nicht Teil dieses Checklisten-Flows"),
        ],
    ),
]

state = load_state()

all_keys = [key for _, _, items in PHASES for key, _ in items]
done_count = sum(1 for key in all_keys if state.get(key, False))
st.progress(done_count / len(all_keys), text=f"{done_count} / {len(all_keys)} Schritte erledigt")

st.space("small")

for phase_id, phase_title, items in PHASES:
    phase_done = sum(1 for key, _ in items if state.get(key, False))
    with st.container(border=True):
        st.markdown(f"#### {phase_title} ({phase_done}/{len(items)})")
        for key, label in items:
            st.checkbox(
                label,
                value=state.get(key, False),
                key=key,
                on_change=on_check_change,
                args=(key,),
            )
    st.space("small")

st.caption(
    "Fortschritt wird lokal in `education_state/checklist_state.json` gespeichert "
    "(nicht committet) -- bleibt ueber Neustarts hinweg erhalten."
)
